# Color Persistence & Caliper Circle Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 實作顏色記憶（QSettings）與卡尺抓圓（射線卡尺 + RANSAC + 即時預覽）兩個功能。

**Architecture:** 顏色記憶在 ToolBar 讀寫 QSettings，Controller 啟動時同步 ImageView。卡尺抓圓遵循現有 MVC 架構：ImageView 負責拖曳繪製，Controller 開啟 CaliperCircleDialog，Dialog 每次參數改變重跑 `caliper_find_circle()`，Controller 管理 Scene 上的虛線預覽 Ellipse，OK 後建立正式 CircleItem。

**Tech Stack:** Python 3.10, PySide6 6.10, OpenCV 4.13, NumPy 2.2, pytest

---

## File Map

| 動作 | 路徑 | 職責 |
|------|------|------|
| 新增 | `tests/test_caliper.py` | `caliper_find_circle` 單元測試 |
| 修改 | `OptiMeasure_AOI/utils/image_utils.py` | 新增 `caliper_find_circle()` |
| 修改 | `OptiMeasure_AOI/views/toolbar.py` | 顏色記憶 + 卡尺抓圓按鈕 |
| 修改 | `OptiMeasure_AOI/views/image_view.py` | 新增 `ViewMode.CALIPER_CIRCLE` |
| 新增 | `OptiMeasure_AOI/dialogs/caliper_dialog.py` | `CaliperCircleDialog` |
| 修改 | `OptiMeasure_AOI/controllers/main_controller.py` | 卡尺流程 + 顏色同步 |

---

## Task 1: caliper_find_circle 演算法

**Files:**
- Modify: `OptiMeasure_AOI/utils/image_utils.py`
- Create: `tests/test_caliper.py`

- [ ] **Step 1: 建立測試檔，寫第一個失敗測試**

建立 `tests/__init__.py`（空檔），再建立 `tests/test_caliper.py`：

```python
# tests/test_caliper.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'OptiMeasure_AOI'))

import numpy as np
import cv2
import pytest
from utils.image_utils import caliper_find_circle


def _circle_image(cx=150, cy=150, r=80):
    """灰階影像，白色圓環，黑色背景（厚度 2px）"""
    img = np.zeros((300, 300), dtype=np.uint8)
    cv2.circle(img, (cx, cy), r, 255, 2)
    return img


def test_basic_detection():
    """精確圓應被正確擬合（誤差 < 2px）"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0)
    assert result['success'] is True
    assert abs(result['cx'] - 150) < 2
    assert abs(result['cy'] - 150) < 2
    assert abs(result['radius'] - 80) < 2
```

- [ ] **Step 2: 確認測試失敗**

```
cd C:\Users\vul32\Desktop\Claude\Measure_Img
pytest tests/test_caliper.py::test_basic_detection -v
```

預期輸出包含：`ImportError` 或 `cannot import name 'caliper_find_circle'`

- [ ] **Step 3: 實作 caliper_find_circle()**

在 `OptiMeasure_AOI/utils/image_utils.py` 末尾加入：

```python
def caliper_find_circle(
    image: np.ndarray,
    cx: float,
    cy: float,
    radius: float,
    n_rays: int = 36,
    band_ratio: float = 0.20,
    edge_dir: str = 'any',
    ransac_tol: float = 2.0,
) -> dict:
    """
    射線卡尺偵測圓形邊緣，最小二乘法 + RANSAC 擬合圓。

    Parameters
    ----------
    image      : 灰階或 BGR 彩色 numpy array
    cx, cy     : 近似圓心（像素座標）
    radius     : 近似半徑
    n_rays     : 射線數（預設 36）
    band_ratio : 搜尋帶半寬比例（預設 ±20%）
    edge_dir   : 'any' | 'dark_to_light' | 'light_to_dark'
    ransac_tol : RANSAC inlier 距離容忍（像素）

    Returns
    -------
    dict with keys: cx, cy, radius, inliers, total, success
    """
    # 轉灰階
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
    else:
        gray = image.astype(np.float32)

    h, w = gray.shape
    r_min = radius * (1.0 - band_ratio)
    r_max = radius * (1.0 + band_ratio)
    n_samples = max(20, int((r_max - r_min) * 2) + 10)

    angles = np.linspace(0.0, 2.0 * np.pi, n_rays, endpoint=False)
    edge_pts: list[tuple[float, float]] = []

    for angle in angles:
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        distances = np.linspace(r_min, r_max, n_samples)
        xs = np.clip(cx + distances * cos_a, 0, w - 1).astype(int)
        ys = np.clip(cy + distances * sin_a, 0, h - 1).astype(int)
        profile = gray[ys, xs]
        gradient = np.gradient(profile)

        if edge_dir == 'dark_to_light':
            idx = int(np.argmax(gradient))
        elif edge_dir == 'light_to_dark':
            idx = int(np.argmin(gradient))
        else:
            idx = int(np.argmax(np.abs(gradient)))

        edge_pts.append((cx + distances[idx] * cos_a,
                         cy + distances[idx] * sin_a))

    _FAIL = {'cx': cx, 'cy': cy, 'radius': radius,
             'inliers': 0, 'total': n_rays, 'success': False}

    if len(edge_pts) < 3:
        return _FAIL

    pts = np.array(edge_pts, dtype=np.float64)

    def _fit_circle(p: np.ndarray):
        """代數最小二乘法：(x-cx)²+(y-cy)²=r²"""
        x, y = p[:, 0], p[:, 1]
        A = np.column_stack([x, y, np.ones(len(x))])
        b_vec = -(x ** 2 + y ** 2)
        coef, _, _, _ = np.linalg.lstsq(A, b_vec, rcond=None)
        a, b, c = coef
        fit_cx, fit_cy = -a / 2.0, -b / 2.0
        val = fit_cx ** 2 + fit_cy ** 2 - c
        if val <= 0:
            return None
        return fit_cx, fit_cy, float(np.sqrt(val))

    # RANSAC
    rng = np.random.default_rng(42)
    best_mask = np.zeros(len(pts), dtype=bool)

    for _ in range(50):
        idx3 = rng.choice(len(pts), 3, replace=False)
        res = _fit_circle(pts[idx3])
        if res is None:
            continue
        fcx, fcy, fr = res
        dist = np.abs(np.sqrt((pts[:, 0] - fcx) ** 2 +
                               (pts[:, 1] - fcy) ** 2) - fr)
        mask = dist <= ransac_tol
        if mask.sum() > best_mask.sum():
            best_mask = mask

    if best_mask.sum() < 3:
        return _FAIL

    final = _fit_circle(pts[best_mask])
    if final is None:
        return _FAIL

    fcx, fcy, fr = final
    return {
        'cx': float(fcx), 'cy': float(fcy), 'radius': float(fr),
        'inliers': int(best_mask.sum()), 'total': n_rays,
        'success': True,
    }
```

- [ ] **Step 4: 執行全部測試，確認通過**

```
pytest tests/test_caliper.py::test_basic_detection -v
```

預期：`PASSED`

- [ ] **Step 5: 補齊其餘測試並通過**

在 `tests/test_caliper.py` 追加：

```python
def test_approx_offset():
    """近似值偏移 5px 仍應收斂（誤差 < 5px）"""
    img = _circle_image()
    result = caliper_find_circle(img, 155.0, 148.0, 75.0)
    assert result['success'] is True
    assert abs(result['cx'] - 150) < 5
    assert abs(result['cy'] - 150) < 5
    assert abs(result['radius'] - 80) < 5


def test_dark_to_light():
    """edge_dir='dark_to_light' 應成功偵測"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0,
                                  edge_dir='dark_to_light')
    assert result['success'] is True


def test_color_image():
    """BGR 彩色影像應自動轉灰階後偵測"""
    gray = _circle_image()
    color = np.stack([gray, gray, gray], axis=2)
    result = caliper_find_circle(color, 150.0, 150.0, 80.0)
    assert result['success'] is True


def test_return_keys():
    """回傳 dict 必須包含所有必要 key"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0)
    for key in ('cx', 'cy', 'radius', 'inliers', 'total', 'success'):
        assert key in result


def test_inliers_count():
    """inliers 不超過 total"""
    img = _circle_image()
    result = caliper_find_circle(img, 150.0, 150.0, 80.0)
    assert result['inliers'] <= result['total']
```

```
pytest tests/test_caliper.py -v
```

預期：全部 `PASSED`

- [ ] **Step 6: Commit**

```
git add OptiMeasure_AOI/utils/image_utils.py tests/
git commit -m "feat: add caliper_find_circle() with RANSAC circle fitting"
```

---

## Task 2: 顏色記憶（ToolBar + QSettings）

**Files:**
- Modify: `OptiMeasure_AOI/views/toolbar.py`

- [ ] **Step 1: 加入 QSettings import 並讀取顏色**

在 `toolbar.py` 開頭 import 區加入 `QSettings`：

```python
from PySide6.QtCore import Signal, Qt, QSettings
```

在 `ToolBar.__init__` 的 `self._current_color = QColor(0, 255, 0)` 這行**之後**插入：

```python
        # 從 QSettings 恢復上次顏色
        _settings = QSettings("OptiMeasure", "AOI")
        _saved = _settings.value("toolbar/color")
        if _saved:
            self._current_color = QColor(_saved)
```

- [ ] **Step 2: 選色後寫入 QSettings**

在 `_on_pick_color` 中，`self._current_color = color` 這行**之後**插入：

```python
            QSettings("OptiMeasure", "AOI").setValue("toolbar/color", color.name())
```

- [ ] **Step 3: 新增 current_color property**

在 `ToolBar` 類別末尾（`_build_tool_buttons` 方法之後）新增：

```python
    @property
    def current_color(self) -> QColor:
        return self._current_color
```

- [ ] **Step 4: 手動驗證**

啟動程式，選一個顏色（例如紅色），關閉，再啟動。工具列色塊應顯示上次選的顏色。

- [ ] **Step 5: Commit**

```
git add OptiMeasure_AOI/views/toolbar.py
git commit -m "feat: persist last selected color via QSettings"
```

---

## Task 3: 顏色同步 ImageView（MainController）

**Files:**
- Modify: `OptiMeasure_AOI/controllers/main_controller.py`

- [ ] **Step 1: 在 _connect_signals 末尾加入初始顏色同步**

在 `_connect_signals` 方法的最後一行（`right_panel.gen_line_requested.connect(self._gen_line)` 之後）加入：

```python
        # 啟動時將讀取到的顏色同步給 ImageView
        win.image_view.set_draw_color(toolbar.current_color)
```

- [ ] **Step 2: 手動驗證**

啟動程式，選一個顏色後關閉；再啟動並立即繪製一個圓，顏色應與上次選的一致。

- [ ] **Step 3: Commit**

```
git add OptiMeasure_AOI/controllers/main_controller.py
git commit -m "feat: sync restored color to ImageView on startup"
```

---

## Task 4: ViewMode.CALIPER_CIRCLE（ImageView）

**Files:**
- Modify: `OptiMeasure_AOI/views/image_view.py`

- [ ] **Step 1: 新增 CALIPER_CIRCLE 到 ViewMode enum**

在 `ViewMode` enum 的 `DRAW_LINE = auto()` 之後加入：

```python
    CALIPER_CIRCLE = auto()  # 卡尺抓圓
```

- [ ] **Step 2: 允許 CALIPER_CIRCLE 進入繪圖流程**

在 `mousePressEvent` 中，找到這一行：

```python
            elif self._mode in (ViewMode.DRAW_CIRCLE, ViewMode.DRAW_RECT1,
                                 ViewMode.DRAW_RECT2, ViewMode.DRAW_LINE):
```

改為：

```python
            elif self._mode in (ViewMode.DRAW_CIRCLE, ViewMode.DRAW_RECT1,
                                 ViewMode.DRAW_RECT2, ViewMode.DRAW_LINE,
                                 ViewMode.CALIPER_CIRCLE):
```

- [ ] **Step 3: 加入拖曳預覽（_create_preview_item）**

在 `_create_preview_item` 的 `elif self._mode == ViewMode.DRAW_LINE:` 區塊之後加入：

```python
        elif self._mode == ViewMode.CALIPER_CIRCLE:
            self._preview_item = self._scene.addEllipse(
                QRectF(start.x(), start.y(), 0, 0), pen)
```

- [ ] **Step 4: 加入拖曳更新（_update_preview_item）**

在 `_update_preview_item` 的 `elif self._mode == ViewMode.DRAW_CIRCLE:` 區塊（整段）之後，`elif self._mode == ViewMode.DRAW_RECT1:` 之前，加入：

```python
        elif self._mode == ViewMode.CALIPER_CIRCLE:
            radius = math.sqrt((current.x() - start.x()) ** 2 +
                               (current.y() - start.y()) ** 2)
            self._preview_item.setRect(
                QRectF(start.x() - radius, start.y() - radius,
                       2 * radius, 2 * radius))
```

- [ ] **Step 5: 加入繪製完成發射（_finalize_draw）**

在 `_finalize_draw` 的 `elif self._mode == ViewMode.DRAW_LINE:` 區塊之後加入：

```python
        elif self._mode == ViewMode.CALIPER_CIRCLE:
            radius = math.sqrt((end.x() - start.x()) ** 2 +
                               (end.y() - start.y()) ** 2)
            params = {'cx': start.x(), 'cy': start.y(), 'radius': radius}
            self.shape_drawn.emit('caliper_circle', params)
```

- [ ] **Step 6: Commit**

```
git add OptiMeasure_AOI/views/image_view.py
git commit -m "feat: add CALIPER_CIRCLE ViewMode to ImageView"
```

---

## Task 5: 卡尺抓圓工具列按鈕

**Files:**
- Modify: `OptiMeasure_AOI/views/toolbar.py`

- [ ] **Step 1: 加入卡尺抓圓到模式清單**

在 `_build_mode_buttons` 的 `modes` 清單中，`("直線", "Line", ViewMode.DRAW_LINE, False),` 之後加入：

```python
            ("卡尺抓圓", "CaliperCircle", ViewMode.CALIPER_CIRCLE, False),
```

- [ ] **Step 2: 手動驗證**

啟動程式，工具列應出現「卡尺抓圓」按鈕，點擊後游標應變為十字形。

- [ ] **Step 3: Commit**

```
git add OptiMeasure_AOI/views/toolbar.py
git commit -m "feat: add caliper circle button to toolbar"
```

---

## Task 6: CaliperCircleDialog

**Files:**
- Create: `OptiMeasure_AOI/dialogs/caliper_dialog.py`

- [ ] **Step 1: 建立 CaliperCircleDialog**

建立 `OptiMeasure_AOI/dialogs/caliper_dialog.py`：

```python
"""
caliper_dialog.py
卡尺抓圓參數設定對話框（Dialog 層）

功能：
- 顯示卡尺偵測可調參數（射線數、搜尋帶、梯度方向、RANSAC 容忍）
- 每次參數改變即重新偵測，即時發射 detection_updated 信號供 Controller 更新預覽
- 按確認後發射 detection_accepted 信號，由 Controller 建立正式 CircleItem
"""
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QSpinBox, QComboBox, QDoubleSpinBox,
                                QDialogButtonBox, QGroupBox)
from PySide6.QtCore import Signal

from utils.image_utils import caliper_find_circle


class CaliperCircleDialog(QDialog):
    # 即時預覽用：每次偵測完成後發射
    detection_updated = Signal(float, float, float)   # cx, cy, r
    # 使用者按確認後發射
    detection_accepted = Signal(float, float, float)  # cx, cy, r

    def __init__(self, image: np.ndarray,
                 cx: float, cy: float, radius: float,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("卡尺抓圓")
        self.setMinimumWidth(290)

        self._image = image
        self._approx_cx = cx
        self._approx_cy = cy
        self._approx_radius = radius
        self._last_result: dict = {
            'cx': cx, 'cy': cy, 'radius': radius,
            'inliers': 0, 'total': 0, 'success': False,
        }

        self._build_ui()
        self._run_detection()

    # ──────────────────────────────────────────────
    # UI 建構
    # ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── 參數群組 ──
        param_group = QGroupBox("偵測參數")
        pg = QVBoxLayout(param_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("射線數:"))
        self._rays_spin = QSpinBox()
        self._rays_spin.setRange(12, 72)
        self._rays_spin.setValue(36)
        self._rays_spin.setSingleStep(6)
        row1.addWidget(self._rays_spin)
        pg.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("搜尋帶 ±%:"))
        self._band_spin = QSpinBox()
        self._band_spin.setRange(5, 50)
        self._band_spin.setValue(20)
        row2.addWidget(self._band_spin)
        pg.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("梯度方向:"))
        self._edge_combo = QComboBox()
        self._edge_combo.addItems(["不限", "暗→亮", "亮→暗"])
        row3.addWidget(self._edge_combo)
        pg.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("RANSAC 容忍 (px):"))
        self._tol_spin = QDoubleSpinBox()
        self._tol_spin.setRange(1.0, 5.0)
        self._tol_spin.setValue(2.0)
        self._tol_spin.setSingleStep(0.5)
        row4.addWidget(self._tol_spin)
        pg.addLayout(row4)

        layout.addWidget(param_group)

        # ── 結果群組 ──
        result_group = QGroupBox("偵測結果")
        rg = QVBoxLayout(result_group)
        self._result_label = QLabel("偵測中...")
        self._result_label.setWordWrap(True)
        rg.addWidget(self._result_label)
        layout.addWidget(result_group)

        # ── 確認 / 取消 ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._on_accepted)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # ── 參數改變 → 重新偵測 ──
        self._rays_spin.valueChanged.connect(self._run_detection)
        self._band_spin.valueChanged.connect(self._run_detection)
        self._edge_combo.currentIndexChanged.connect(self._run_detection)
        self._tol_spin.valueChanged.connect(self._run_detection)

    # ──────────────────────────────────────────────
    # 偵測邏輯
    # ──────────────────────────────────────────────

    _EDGE_MAP = {0: 'any', 1: 'dark_to_light', 2: 'light_to_dark'}

    def _run_detection(self):
        result = caliper_find_circle(
            self._image,
            self._approx_cx, self._approx_cy, self._approx_radius,
            n_rays=self._rays_spin.value(),
            band_ratio=self._band_spin.value() / 100.0,
            edge_dir=self._EDGE_MAP[self._edge_combo.currentIndex()],
            ransac_tol=self._tol_spin.value(),
        )
        self._last_result = result

        if result['success']:
            self._result_label.setText(
                f"cx: {result['cx']:.1f}   cy: {result['cy']:.1f}\n"
                f"半徑: {result['radius']:.1f}   "
                f"吻合點: {result['inliers']} / {result['total']}"
            )
        else:
            self._result_label.setText(
                f"⚠ 偵測失敗（吻合點不足）\n"
                f"cx: {result['cx']:.1f}   cy: {result['cy']:.1f}\n"
                f"半徑: {result['radius']:.1f}"
            )

        self.detection_updated.emit(
            result['cx'], result['cy'], result['radius'])

    # ──────────────────────────────────────────────
    # 確認
    # ──────────────────────────────────────────────

    def _on_accepted(self):
        r = self._last_result
        self.detection_accepted.emit(r['cx'], r['cy'], r['radius'])
        self.accept()
```

- [ ] **Step 2: Commit**

```
git add OptiMeasure_AOI/dialogs/caliper_dialog.py
git commit -m "feat: add CaliperCircleDialog with live detection_updated signal"
```

---

## Task 7: MainController 卡尺流程連接

**Files:**
- Modify: `OptiMeasure_AOI/controllers/main_controller.py`

- [ ] **Step 1: 在 __init__ 加入狀態變數**

在 `self._magnifier_dialog = None` 之後加入：

```python
        self._caliper_dialog = None
        self._caliper_preview_item = None  # QGraphicsEllipseItem（預覽用）
```

- [ ] **Step 2: 在 _on_shape_drawn 加入 caliper_circle case**

在 `_on_shape_drawn` 的 `elif shape_type == 'line':` 區塊之後加入：

```python
        elif shape_type == 'caliper_circle':
            self._open_caliper_dialog(
                params['cx'], params['cy'], params['radius'])
```

- [ ] **Step 3: 新增 _open_caliper_dialog 方法**

在 `_open_magnifier_dialog` 方法之後新增：

```python
    def _open_caliper_dialog(self, cx: float, cy: float, radius: float):
        """開啟卡尺抓圓對話框，連接即時預覽與確認信號"""
        if self._image_model.original_image is None:
            return
        from dialogs.caliper_dialog import CaliperCircleDialog
        self._caliper_dialog = CaliperCircleDialog(
            self._image_model.original_image, cx, cy, radius, self._window)
        self._caliper_dialog.detection_updated.connect(self._on_caliper_updated)
        self._caliper_dialog.detection_accepted.connect(self._on_caliper_accepted)
        self._caliper_dialog.rejected.connect(self._on_caliper_rejected)
        self._caliper_dialog.exec()
```

- [ ] **Step 4: 新增 _on_caliper_updated 方法**

```python
    def _on_caliper_updated(self, cx: float, cy: float, r: float):
        """偵測結果更新 → 移除舊預覽 → 繪製新虛線橢圓"""
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPen
        from PySide6.QtCore import Qt
        scene = self._window.image_view.graphics_scene
        if self._caliper_preview_item is not None:
            scene.removeItem(self._caliper_preview_item)
            self._caliper_preview_item = None
        color = self._window.image_view._draw_color
        lw = self._window.image_view._draw_line_width
        pen = QPen(color, lw)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self._caliper_preview_item = scene.addEllipse(
            QRectF(cx - r, cy - r, 2.0 * r, 2.0 * r), pen)
```

- [ ] **Step 5: 新增 _on_caliper_accepted 與 _on_caliper_rejected 方法**

```python
    def _on_caliper_accepted(self, cx: float, cy: float, r: float):
        """使用者按確認 → 移除預覽 → 建立正式 CircleItem"""
        self._remove_caliper_preview()
        color = self._window.image_view._draw_color
        lw = self._window.image_view._draw_line_width
        self._create_circle(cx, cy, r, color, lw)

    def _on_caliper_rejected(self):
        """使用者取消 → 移除預覽"""
        self._remove_caliper_preview()

    def _remove_caliper_preview(self):
        if self._caliper_preview_item is not None:
            self._window.image_view.graphics_scene.removeItem(
                self._caliper_preview_item)
            self._caliper_preview_item = None
```

- [ ] **Step 6: 端對端手動驗證**

1. 啟動程式，載入任一影像
2. 點擊「卡尺抓圓」按鈕
3. 在影像上的圓形物件處拖曳畫出近似圓
4. 對話框應出現，畫布上應出現虛線預覽圓
5. 調整射線數或搜尋帶，預覽圓應即時更新
6. 按「確認」，虛線消失，正式圓形加入表格
7. 按「取消」，虛線消失，無新圓形

- [ ] **Step 7: Commit**

```
git add OptiMeasure_AOI/controllers/main_controller.py
git commit -m "feat: wire CaliperCircleDialog with live preview in MainController"
```
