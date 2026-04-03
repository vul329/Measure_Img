# Design: Color Persistence & Caliper Circle Detection

**Date:** 2026-04-03  
**Status:** Approved

---

## 1. Color Persistence（顏色記憶）

### Goal
程式啟動時恢復上次使用者選擇的線條顏色，讓工具列色塊與 ImageView 繪圖顏色保持一致。

### Storage
使用 `QSettings(organization="OptiMeasure", application="AOI")`：
- Key: `toolbar/color`
- Value: `#rrggbb` hex 字串（`QColor.name()`）

Windows 實際儲存位置：`HKCU\Software\OptiMeasure\AOI`。

### Data Flow

```
程式啟動
  └─ ToolBar.__init__
       └─ QSettings 讀取 toolbar/color
            ├─ 有值 → _current_color = QColor(hex)
            └─ 無值 → 維持預設 QColor(0, 255, 0)

用戶選色
  └─ ToolBar._on_pick_color
       ├─ QColorDialog → 新顏色
       ├─ _current_color = 新顏色
       ├─ QSettings 寫入 toolbar/color
       └─ emit color_changed(新顏色)

啟動時同步 ImageView
  └─ MainController._connect_signals（末尾）
       └─ image_view.set_draw_color(toolbar.current_color)
```

### Modified Files
| 檔案 | 變更內容 |
|------|---------|
| `views/toolbar.py` | `__init__` 讀 QSettings；`_on_pick_color` 寫 QSettings；新增 `current_color` property |
| `controllers/main_controller.py` | `_connect_signals` 末尾同步 ImageView 顏色 |

---

## 2. Caliper Circle Detection（卡尺抓圓）

### Goal
在工具列新增「卡尺抓圓」模式。使用者拖曳畫出近似圓後，自動執行射線卡尺偵測與最小二乘圓擬合（含 RANSAC 去離群點），並在畫布即時預覽擬合結果，確認後建立正式 CircleItem。

### Architecture Overview

```
Toolbar (ViewMode.CALIPER_CIRCLE)
    ↓ mode_changed
ImageView
    ↓ shape_drawn('caliper_circle', {cx, cy, radius})
MainController
    ├─ caliper_find_circle()  ←  image_utils.py
    ├─ 開啟 CaliperCircleDialog（傳入 image + 近似圓參數）
    │     ↓ detection_updated(cx, cy, r)   [參數改變時]
    │     ↓ detection_accepted(cx, cy, r)  [按 OK]
    └─ 管理 Scene 上的預覽 QGraphicsEllipseItem
```

---

### 2.1 Algorithm：`caliper_find_circle()`

**函式簽名**
```python
def caliper_find_circle(
    image: np.ndarray,
    cx: float, cy: float, radius: float,
    n_rays: int = 36,
    band_ratio: float = 0.20,
    edge_dir: str = 'any',   # 'any' | 'dark_to_light' | 'light_to_dark'
    ransac_tol: float = 2.0,
) -> dict:
    # 回傳 {'cx': float, 'cy': float, 'radius': float,
    #        'inliers': int, 'total': int, 'success': bool}
```

**步驟**

1. **射線取樣**：沿 `n_rays` 條射線（每條間隔 `360/n_rays` 度），在搜尋帶
   `[radius*(1-band_ratio), radius*(1+band_ratio)]` 內以 `np.linspace` 等距取樣整數座標。

2. **梯度邊緣偵測**：對每條射線的像素剖面計算 `np.gradient()`：
   - `edge_dir='any'`：取 `abs(gradient)` 最大的位置
   - `edge_dir='dark_to_light'`：取 `gradient` 最大（最正）的位置
   - `edge_dir='light_to_dark'`：取 `gradient` 最小（最負）的位置

3. **代數最小二乘圓擬合**：
   展開圓方程 `(x-cx)²+(y-cy)²=r²` 為線性形式：
   ```
   A = [[x_i, y_i, 1], ...]
   b = [-(x_i²+y_i²), ...]
   解 [a, b, c] = lstsq(A, b_vec)
   cx = -a/2,  cy = -b/2,  r = sqrt(cx²+cy²-c)
   ```

4. **RANSAC**（迭代 50 次）：
   - 每次隨機取 3 個邊緣點擬合圓
   - 計算所有點到擬合圓的距離，`<= ransac_tol` 為 inlier
   - 保留 inlier 最多的模型
   - 用最終 inliers 重新擬合，得到精確結果

5. **回傳結果**：若 inlier 數 < 3 則 `success=False`，cx/cy/r 退回近似值。

**效能**：36 條射線 × 約 80 取樣點 = ~2880 個純 numpy 浮點操作，10MP 影像 < 5ms。

---

### 2.2 View：ImageView

- `ViewMode` 新增 `CALIPER_CIRCLE = auto()`
- 拖曳行為與 `DRAW_CIRCLE` 完全相同（中心 + 半徑）
- `set_mode(CALIPER_CIRCLE)` 使用十字游標
- `_finalize_draw` 新增 case：
  ```python
  elif self._mode == ViewMode.CALIPER_CIRCLE:
      params = {'cx': start.x(), 'cy': start.y(), 'radius': radius}
      self.shape_drawn.emit('caliper_circle', params)
  ```
- `mousePressEvent` 的「允許繪圖模式」集合加入 `CALIPER_CIRCLE`

---

### 2.3 View：ToolBar

在 `_build_mode_buttons` 的 `modes` 清單末尾新增：
```python
("卡尺抓圓", "CaliperCircle", ViewMode.CALIPER_CIRCLE, False),
```

---

### 2.4 Dialog：CaliperCircleDialog

**責任**：持有近似圓參數與來源影像，提供參數調整 UI，每次參數改變時重新偵測並發射結果信號。

**信號**
```python
detection_updated = Signal(float, float, float)   # cx, cy, r（即時預覽用）
detection_accepted = Signal(float, float, float)  # cx, cy, r（按 OK 後）
```

**UI 佈局**
```
┌─────────────────────────────────┐
│  射線數:    [SpinBox 12~72]      │
│  搜尋帶:    [SpinBox 5~50 %]     │
│  梯度方向:  [ComboBox]           │
│  RANSAC 容忍: [SpinBox 1~5 px]  │
├─────────────────────────────────┤
│  偵測結果                        │
│  cx: 123.4   cy: 456.7          │
│  半徑: 89.2  吻合點: 34 / 36    │
├─────────────────────────────────┤
│        [確認]    [取消]          │
└─────────────────────────────────┘
```

**行為**
- `__init__(image, cx, cy, radius, parent)` → 儲存參數並觸發初次偵測
- 任一參數控制值改變 → `_run_detection()` → 更新結果顯示 → `emit detection_updated`
- 按「確認」→ `emit detection_accepted` → `accept()`
- 按「取消」→ `reject()`
- 若 `success=False`，結果列顯示警告文字

---

### 2.5 Controller：MainController

**新增狀態**
```python
self._caliper_preview_item = None   # QGraphicsEllipseItem | None
```

**新增/修改方法**

| 方法 | 說明 |
|------|------|
| `_on_shape_drawn` | 新增 `caliper_circle` case → 呼叫 `_open_caliper_dialog` |
| `_open_caliper_dialog(cx, cy, radius)` | 建立 CaliperCircleDialog，連接信號，顯示 |
| `_on_caliper_updated(cx, cy, r)` | 移除舊預覽 → 建立新 QGraphicsEllipseItem（虛線） |
| `_on_caliper_accepted(cx, cy, r)` | 移除預覽 → `_create_circle(cx, cy, r, color, lw)` |
| `_on_caliper_rejected()` | 移除預覽 |

**預覽 item 規格**：`QPen(draw_color, draw_line_width, DashLine)`，`setCosmetic(True)`，不加入 ShapeModel。

---

### New / Modified Files Summary

| 動作 | 檔案 | 內容 |
|------|------|------|
| 新增 | `dialogs/caliper_dialog.py` | CaliperCircleDialog |
| 修改 | `utils/image_utils.py` | 新增 `caliper_find_circle()` |
| 修改 | `views/image_view.py` | 新增 `CALIPER_CIRCLE` ViewMode |
| 修改 | `views/toolbar.py` | 新增按鈕 + 顏色記憶 |
| 修改 | `controllers/main_controller.py` | 連接卡尺流程 + 顏色同步 |
