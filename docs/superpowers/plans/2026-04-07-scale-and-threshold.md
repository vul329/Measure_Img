# Scale & Threshold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a global scale (倍率) field to the toolbar that converts pixel measurements to real-world lengths in the table, and a non-modal Threshold dialog with histogram visualization and live overlay.

**Architecture:** Feature 1 adds a module-level pure function `compute_real_length` (testable without Qt) and wires it through Toolbar → Controller → RightPanel. Feature 2 extracts `apply_threshold_overlay` to `image_utils.py` (testable without Qt), adds threshold state to `ImageModel`, and builds a non-modal `ThresholdDialog`. Both features share the existing `display_image_updated` signal pathway.

**Tech Stack:** Python 3.10, PySide6 6.10.2, OpenCV 4.13, NumPy 2.2, pytest

---

## File Map

| Action | File | Change |
|--------|------|--------|
| Modify | `OptiMeasure_AOI/views/right_panel.py` | Add `compute_real_length` module-level fn; add 8th table column; add `set_scale`, `refresh_real_length_column` |
| Modify | `OptiMeasure_AOI/views/toolbar.py` | Add scale `QLineEdit` + `scale_changed` signal; add threshold button + `threshold_clicked` signal |
| Modify | `OptiMeasure_AOI/controllers/main_controller.py` | Wire scale + threshold signals; update display slots to call `get_visible_image()` |
| Modify | `OptiMeasure_AOI/utils/image_utils.py` | Add `apply_threshold_overlay` |
| Modify | `OptiMeasure_AOI/models/image_model.py` | Add threshold state; add `set_threshold`, `set_overlay_color`, `get_visible_image` |
| Create | `OptiMeasure_AOI/dialogs/threshold_dialog.py` | `HistogramWidget` + `ThresholdDialog` |
| Create | `tests/test_scale.py` | Tests for `compute_real_length` |
| Create | `tests/test_threshold_overlay.py` | Tests for `apply_threshold_overlay` |

---

## Task 1: `compute_real_length` utility function

**Files:**
- Modify: `OptiMeasure_AOI/views/right_panel.py` (top of file, before class)
- Create: `tests/test_scale.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_scale.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'OptiMeasure_AOI'))

from views.right_panel import compute_real_length


def test_scale_zero_returns_dashes():
    params = {'type': 'Circle', 'radius': 50.0}
    assert compute_real_length(params, 0.0) == '--'


def test_scale_empty_returns_dashes():
    params = {'type': 'Circle', 'radius': 50.0}
    assert compute_real_length(params, 0.0) == '--'


def test_circle_real_length():
    params = {'type': 'Circle', 'radius': 12.5}
    assert compute_real_length(params, 0.8) == '10.000'


def test_line_real_length():
    params = {'type': 'Line', 'length': 100.0}
    assert compute_real_length(params, 0.1) == '10.000'


def test_rect_always_dashes():
    params = {'type': 'Rect1', 'width': 50.0, 'height': 30.0}
    assert compute_real_length(params, 2.0) == '--'


def test_three_decimal_precision():
    params = {'type': 'Circle', 'radius': 10.0}
    assert compute_real_length(params, 1.2345) == '12.345'
```

- [ ] **Step 2: Run test to verify it fails**

```
cd c:\Users\vul32\Desktop\Claude\Measure_Img
pytest tests/test_scale.py -v
```

Expected: FAIL with `ImportError: cannot import name 'compute_real_length'`

- [ ] **Step 3: Add `compute_real_length` to `right_panel.py`**

Add this block immediately after the imports, before the `class RightPanel` line:

```python
def compute_real_length(params: dict, scale: float) -> str:
    """
    Convert pixel measurement to real-world length using scale factor.
    Returns '--' when scale is 0 or shape type is not Circle/Line.
    """
    if scale <= 0:
        return '--'
    shape_type = params.get('type', '')
    if shape_type == 'Circle':
        return f"{params.get('radius', 0.0) * scale:.3f}"
    if shape_type == 'Line':
        return f"{params.get('length', 0.0) * scale:.3f}"
    return '--'
```

- [ ] **Step 4: Run test to verify it passes**

```
cd c:\Users\vul32\Desktop\Claude\Measure_Img
pytest tests/test_scale.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add OptiMeasure_AOI/views/right_panel.py tests/test_scale.py
git commit -m "feat: add compute_real_length utility with tests"
```

---

## Task 2: Toolbar — scale field

**Files:**
- Modify: `OptiMeasure_AOI/views/toolbar.py`

- [ ] **Step 1: Add `scale_changed` signal and QSettings-persisted scale input**

In `toolbar.py`, make the following changes:

1. Add signal after `bg_color_changed`:
```python
scale_changed = Signal(float)
```

2. In `_build_style_controls`, after the line_width block (after `self.addWidget(container)`), add:

```python
        # 倍率輸入
        scale_container = QWidget()
        scale_layout = QHBoxLayout(scale_container)
        scale_layout.setContentsMargins(4, 0, 4, 0)
        scale_layout.setSpacing(4)
        scale_layout.addWidget(QLabel("倍率:"))
        self._scale_edit = QLineEdit()
        self._scale_edit.setPlaceholderText("1.000")
        self._scale_edit.setFixedWidth(70)
        self._scale_edit.setValidator(QDoubleValidator(0.0, 99999.0, 6))
        # Restore persisted value
        _saved_scale = _settings.value("toolbar/scale", "")
        if _saved_scale:
            self._scale_edit.setText(str(_saved_scale))
        self._scale_edit.textChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self._scale_edit)
        self.addWidget(scale_container)
```

3. Add the slot method after `_on_pick_color`:

```python
    def _on_scale_changed(self, text: str):
        try:
            value = float(text)
        except ValueError:
            value = 0.0
        QSettings("OptiMeasure", "AOI").setValue("toolbar/scale", text)
        self.scale_changed.emit(value)

    @property
    def scale(self) -> float:
        try:
            return float(self._scale_edit.text())
        except ValueError:
            return 0.0
```

4. Add `QDoubleValidator` to the imports at the top:
```python
from PySide6.QtGui import (QColor, QIcon, QPixmap, QPainter,
                            QActionGroup, QAction, QDoubleValidator)
```

- [ ] **Step 2: Verify manually**

Run the app: `cd OptiMeasure_AOI && python main.py`

Verify:
- "倍率:" label and input appear in toolbar after line width
- Entering a number does not crash
- Restarting the app restores the last entered value

- [ ] **Step 3: Commit**

```bash
git add OptiMeasure_AOI/views/toolbar.py
git commit -m "feat: add scale input field to toolbar with QSettings persistence"
```

---

## Task 3: RightPanel — 8th column + scale wiring

**Files:**
- Modify: `OptiMeasure_AOI/views/right_panel.py`

- [ ] **Step 1: Extend table to 8 columns**

In `_build_table_group`, change:

```python
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["ID", "類型", "參數1", "參數2", "參數3", "參數4", "參數5"])
```
to:
```python
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(
            ["ID", "類型", "參數1", "參數2", "參數3", "參數4", "參數5", "實際長度"])
```

After the existing `for col in range(2, 7):` block, add:
```python
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(7, 100)
```

- [ ] **Step 2: Add `_scale` member and new methods**

In `__init__`, after `self._row_to_id: dict[int, int] = {}`, add:
```python
        self._scale: float = 0.0
```

After the `_on_delete_all` method, add:

```python
    def set_scale(self, value: float):
        self._scale = value
        self.refresh_real_length_column()

    def refresh_real_length_column(self):
        for row in range(self._table.rowCount()):
            type_item = self._table.item(row, 1)
            if type_item is None:
                continue
            shape_type = type_item.text()
            # Reconstruct minimal params dict from displayed cells
            params = {'type': shape_type}
            if shape_type == 'Circle':
                r_item = self._table.item(row, 4)
                if r_item:
                    try:
                        params['radius'] = float(r_item.text().replace('r=', ''))
                    except ValueError:
                        pass
            elif shape_type == 'Line':
                len_item = self._table.item(row, 6)
                if len_item:
                    try:
                        params['length'] = float(len_item.text().replace('len=', ''))
                    except ValueError:
                        pass
            self._set_cell(row, 7, compute_real_length(params, self._scale))
```

- [ ] **Step 3: Fill column 7 in `_fill_row`**

At the end of `_fill_row`, before the method closes, add:

```python
        self._set_cell(row, 7, compute_real_length(params, self._scale))
```

- [ ] **Step 4: Verify manually**

Run the app, draw a circle and a line. Verify column "實際長度" appears and shows `--`.

- [ ] **Step 5: Commit**

```bash
git add OptiMeasure_AOI/views/right_panel.py
git commit -m "feat: add real-length column to measurement table"
```

---

## Task 4: Controller — wire scale

**Files:**
- Modify: `OptiMeasure_AOI/controllers/main_controller.py`

- [ ] **Step 1: Connect scale signal and sync initial state**

In `_connect_signals`, after `toolbar.bg_color_changed.connect(image_view.set_background_color)`, add:

```python
        toolbar.scale_changed.connect(right_panel.set_scale)
```

After the existing `image_view.set_draw_color(toolbar.current_color)` line at the bottom of `_connect_signals`, add:

```python
        # Sync initial scale value from toolbar (restored from QSettings)
        right_panel.set_scale(toolbar.scale)
```

- [ ] **Step 2: Verify end-to-end**

Run the app:
1. Enter `2.0` in the倍率 field
2. Draw a circle with radius ~50px → "實際長度" column shows `100.000`
3. Draw a line of length ~100px → shows `200.000`
4. Change scale to `0` → both show `--`
5. Restart app → scale value is restored, drawn shapes show `--` (no shapes persist)

- [ ] **Step 3: Commit**

```bash
git add OptiMeasure_AOI/controllers/main_controller.py
git commit -m "feat: wire scale signal from toolbar to right panel"
```

---

## Task 5: `apply_threshold_overlay` utility + test

**Files:**
- Modify: `OptiMeasure_AOI/utils/image_utils.py`
- Create: `tests/test_threshold_overlay.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_threshold_overlay.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'OptiMeasure_AOI'))

import numpy as np
from utils.image_utils import apply_threshold_overlay


def test_outside_range_keeps_gray():
    """Pixels outside [low, high] keep their grayscale value as BGR."""
    gray = np.array([[50]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (0, 255, 0))
    assert result.shape == (1, 1, 3)
    assert result[0, 0, 0] == 50  # B
    assert result[0, 0, 1] == 50  # G
    assert result[0, 0, 2] == 50  # R


def test_inside_range_gets_overlay_color():
    """Pixels in [low, high] are replaced with overlay_bgr."""
    gray = np.array([[150]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (0, 255, 0))
    assert result[0, 0, 0] == 0    # B
    assert result[0, 0, 1] == 255  # G
    assert result[0, 0, 2] == 0    # R


def test_boundary_pixels_are_inside():
    """Boundary values (exactly low or high) are inside the range."""
    gray = np.array([[100, 200]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (255, 0, 0))
    assert result[0, 0, 0] == 255  # low boundary → overlay
    assert result[0, 1, 0] == 255  # high boundary → overlay


def test_mixed_row():
    """Three pixels: below, inside, above range."""
    gray = np.array([[50, 150, 250]], dtype=np.uint8)
    result = apply_threshold_overlay(gray, 100, 200, (0, 0, 255))
    # pixel 0 (50) outside → gray
    assert result[0, 0, 2] == 50
    # pixel 1 (150) inside → R=255
    assert result[0, 1, 2] == 255
    # pixel 2 (250) outside → gray
    assert result[0, 2, 2] == 250


def test_output_is_bgr_uint8():
    gray = np.zeros((10, 10), dtype=np.uint8)
    result = apply_threshold_overlay(gray, 0, 255, (100, 150, 200))
    assert result.dtype == np.uint8
    assert result.ndim == 3
    assert result.shape[2] == 3
```

- [ ] **Step 2: Run test to verify it fails**

```
cd c:\Users\vul32\Desktop\Claude\Measure_Img
pytest tests/test_threshold_overlay.py -v
```

Expected: FAIL with `ImportError: cannot import name 'apply_threshold_overlay'`

- [ ] **Step 3: Add `apply_threshold_overlay` to `image_utils.py`**

Add after the `apply_enhancements` function:

```python
def apply_threshold_overlay(
    gray: np.ndarray,
    low: int,
    high: int,
    overlay_bgr: tuple,
) -> np.ndarray:
    """
    Returns a BGR image where pixels in [low, high] are colored with overlay_bgr;
    pixels outside retain their grayscale value in all three channels.

    gray        : 2D uint8 ndarray (grayscale)
    overlay_bgr : (B, G, R) tuple of ints 0-255
    """
    bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    mask = (gray >= low) & (gray <= high)
    bgr[mask] = overlay_bgr
    return bgr
```

- [ ] **Step 4: Run test to verify it passes**

```
cd c:\Users\vul32\Desktop\Claude\Measure_Img
pytest tests/test_threshold_overlay.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add OptiMeasure_AOI/utils/image_utils.py tests/test_threshold_overlay.py
git commit -m "feat: add apply_threshold_overlay utility with tests"
```

---

## Task 6: ImageModel — threshold state

**Files:**
- Modify: `OptiMeasure_AOI/models/image_model.py`

- [ ] **Step 1: Add imports and threshold state**

At the top of `image_model.py`, add to imports:
```python
from utils.image_utils import apply_threshold_overlay
```

In `__init__`, after `self._display_image`, add:

```python
        self._threshold_enabled: bool = False
        self._threshold_low: int = 0
        self._threshold_high: int = 255
        self._overlay_bgr: tuple = (0, 255, 0)  # default green (B, G, R)
```

- [ ] **Step 2: Add threshold methods**

After the `reset_display_image` method, add:

```python
    def set_threshold(self, low: int, high: int, enabled: bool):
        """Update threshold state and notify canvas to redraw."""
        self._threshold_low = low
        self._threshold_high = high
        self._threshold_enabled = enabled
        self.display_image_updated.emit()

    def set_overlay_color(self, color):
        """
        Update the overlay color used for threshold highlighting.
        color: QColor instance
        Only triggers redraw if threshold is currently enabled.
        """
        from PySide6.QtGui import QColor
        if isinstance(color, QColor):
            self._overlay_bgr = (color.blue(), color.green(), color.red())
        if self._threshold_enabled:
            self.display_image_updated.emit()

    def get_visible_image(self) -> np.ndarray | None:
        """
        Returns the image to display on canvas.
        - threshold disabled: returns display_image as-is
        - threshold enabled: returns BGR image with overlay color on [low, high] pixels
        """
        if self._display_image is None:
            return None
        if not self._threshold_enabled:
            return self._display_image
        # Ensure grayscale for masking
        if self._display_image.ndim == 3:
            gray = cv2.cvtColor(self._display_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = self._display_image
        return apply_threshold_overlay(
            gray, self._threshold_low, self._threshold_high, self._overlay_bgr)
```

- [ ] **Step 3: Commit**

```bash
git add OptiMeasure_AOI/models/image_model.py
git commit -m "feat: add threshold state and get_visible_image to ImageModel"
```

---

## Task 7: Controller — use `get_visible_image()`

**Files:**
- Modify: `OptiMeasure_AOI/controllers/main_controller.py`

- [ ] **Step 1: Update `_on_image_loaded` and `_on_display_image_updated`**

Change `_on_image_loaded`:

```python
    def _on_image_loaded(self, width: int, height: int):
        """ImageModel 載入成功 → 更新畫布顯示"""
        self._window.image_view.set_image(self._image_model.get_visible_image())
        if self._magnifier_dialog:
            self._magnifier_dialog.set_source_image(self._image_model.original_image)
```

Change `_on_display_image_updated`:

```python
    def _on_display_image_updated(self):
        """display_image 更新（增強效果改變或閥值改變）→ 重繪畫布"""
        self._window.image_view.set_image(self._image_model.get_visible_image())
```

- [ ] **Step 2: Verify overlay color initial sync**

In `_connect_signals`, after `image_view.set_draw_color(toolbar.current_color)`, add:

```python
        # Sync initial overlay color for threshold
        self._image_model.set_overlay_color(toolbar.current_color)
```

- [ ] **Step 3: Connect color change to overlay color**

In `_on_color_changed`:

```python
    def _on_color_changed(self, color: QColor):
        self._window.image_view.set_draw_color(color)
        self._image_model.set_overlay_color(color)
```

- [ ] **Step 4: Verify app still works**

Run app, load an image, verify display is unchanged (threshold disabled by default).

- [ ] **Step 5: Commit**

```bash
git add OptiMeasure_AOI/controllers/main_controller.py
git commit -m "refactor: route display updates through get_visible_image; wire overlay color"
```

---

## Task 8: ThresholdDialog

**Files:**
- Create: `OptiMeasure_AOI/dialogs/threshold_dialog.py`

- [ ] **Step 1: Create `threshold_dialog.py`**

Create `OptiMeasure_AOI/dialogs/threshold_dialog.py`:

```python
"""
threshold_dialog.py
Threshold 對話框（非模態，狀態持續）

包含：
- HistogramWidget：QPainter 自繪 256-bin histogram，標示 Low/High 垂直線
- ThresholdDialog：Low/High QSlider + QSpinBox 雙向同步，「顯示閥值」勾選項
"""
import numpy as np
import cv2

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QSlider, QSpinBox, QCheckBox, QPushButton,
                                QWidget)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QColor, QPen


class HistogramWidget(QWidget):
    """QPainter-based 256-bin histogram with Low/High marker lines."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(512, 180)
        self._hist = None   # np.ndarray shape (256,)
        self._low = 0
        self._high = 255

    def set_image(self, img: np.ndarray):
        """Compute histogram from image (converts to grayscale if needed)."""
        if img is None:
            self._hist = None
            self.update()
            return
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self._hist, _ = np.histogram(gray.ravel(), bins=256, range=(0, 256))
        self.update()

    def set_range(self, low: int, high: int):
        self._low = low
        self._high = high
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240, 240, 240))

        if self._hist is None:
            return

        w = self.width()
        h = self.height()
        max_val = max(1, int(self._hist.max()))
        bar_w = w / 256.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(60, 60, 60))
        for i, count in enumerate(self._hist):
            bar_h = int(count / max_val * h)
            x = int(i * bar_w)
            painter.drawRect(x, h - bar_h, max(1, int(bar_w + 0.5)), bar_h)

        # Low and High marker lines (red)
        pen = QPen(QColor(220, 0, 0), 2)
        painter.setPen(pen)
        low_x = int(self._low * bar_w)
        painter.drawLine(low_x, 0, low_x, h)
        high_x = int(self._high * bar_w)
        painter.drawLine(high_x, 0, high_x, h)


class ThresholdDialog(QDialog):
    """Non-modal threshold dialog. State persists after close."""

    threshold_changed = Signal(int, int, bool)  # low, high, enabled

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Threshold")
        # Tool window stays on top of parent but doesn't block it
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Tool)
        # Prevent Qt from destroying the object when user closes the window
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._build_ui()
        self._connect_signals()

    # ──────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Histogram
        self._histogram = HistogramWidget()
        layout.addWidget(self._histogram)

        # Low threshold row
        low_row = QHBoxLayout()
        low_row.addWidget(QLabel("Low:"))
        self._low_slider = QSlider(Qt.Orientation.Horizontal)
        self._low_slider.setRange(0, 255)
        self._low_slider.setValue(0)
        self._low_spin = QSpinBox()
        self._low_spin.setRange(0, 255)
        self._low_spin.setValue(0)
        self._low_spin.setFixedWidth(60)
        low_row.addWidget(self._low_slider)
        low_row.addWidget(self._low_spin)
        layout.addLayout(low_row)

        # High threshold row
        high_row = QHBoxLayout()
        high_row.addWidget(QLabel("High:"))
        self._high_slider = QSlider(Qt.Orientation.Horizontal)
        self._high_slider.setRange(0, 255)
        self._high_slider.setValue(255)
        self._high_spin = QSpinBox()
        self._high_spin.setRange(0, 255)
        self._high_spin.setValue(255)
        self._high_spin.setFixedWidth(60)
        high_row.addWidget(self._high_slider)
        high_row.addWidget(self._high_spin)
        layout.addLayout(high_row)

        # Show threshold checkbox
        self._show_checkbox = QCheckBox("顯示閥值")
        layout.addWidget(self._show_checkbox)

        # Close button
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)

    def _connect_signals(self):
        # Slider ↔ SpinBox bidirectional sync (no infinite loop: setValue doesn't
        # emit valueChanged when value is unchanged)
        self._low_slider.valueChanged.connect(self._low_spin.setValue)
        self._low_spin.valueChanged.connect(self._low_slider.setValue)
        self._low_spin.valueChanged.connect(self._on_params_changed)

        self._high_slider.valueChanged.connect(self._high_spin.setValue)
        self._high_spin.valueChanged.connect(self._high_slider.setValue)
        self._high_spin.valueChanged.connect(self._on_params_changed)

        self._show_checkbox.stateChanged.connect(self._on_params_changed)

    # ──────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────

    def _on_params_changed(self):
        low = self._low_spin.value()
        high = self._high_spin.value()
        enabled = self._show_checkbox.isChecked()
        self._histogram.set_range(low, high)
        self.threshold_changed.emit(low, high, enabled)

    # ──────────────────────────────────────────────
    # Public API (called by Controller)
    # ──────────────────────────────────────────────

    def set_image(self, img: np.ndarray):
        """Load image for histogram computation."""
        self._histogram.set_image(img)

    def reset(self):
        """Reset to Low=0, High=255, unchecked. Emits threshold_changed once."""
        for w in [self._low_slider, self._low_spin,
                  self._high_slider, self._high_spin, self._show_checkbox]:
            w.blockSignals(True)
        self._low_slider.setValue(0)
        self._low_spin.setValue(0)
        self._high_slider.setValue(255)
        self._high_spin.setValue(255)
        self._show_checkbox.setChecked(False)
        for w in [self._low_slider, self._low_spin,
                  self._high_slider, self._high_spin, self._show_checkbox]:
            w.blockSignals(False)
        self._histogram.set_range(0, 255)
        self.threshold_changed.emit(0, 255, False)
```

- [ ] **Step 2: Verify import works**

```
cd c:\Users\vul32\Desktop\Claude\Measure_Img\OptiMeasure_AOI
python -c "from dialogs.threshold_dialog import ThresholdDialog; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add OptiMeasure_AOI/dialogs/threshold_dialog.py
git commit -m "feat: add ThresholdDialog with HistogramWidget"
```

---

## Task 9: Toolbar threshold button + Controller wiring

**Files:**
- Modify: `OptiMeasure_AOI/views/toolbar.py`
- Modify: `OptiMeasure_AOI/controllers/main_controller.py`

- [ ] **Step 1: Add threshold button to Toolbar**

In `toolbar.py`, add signal after `bg_color_changed`:
```python
threshold_clicked = Signal()
```

In `_build_tool_buttons`, after the `addSeparator()` and `_bg_action` block (at the end of the method), add:

```python
        self.addSeparator()

        threshold_action = QAction("閥值", self)
        threshold_action.triggered.connect(self.threshold_clicked)
        self.addAction(threshold_action)
```

- [ ] **Step 2: Wire threshold in Controller**

In `main_controller.py`:

1. Add `self._threshold_dialog = None` in `__init__` after `self._caliper_viz_items = []`.

2. In `_connect_signals`, after `toolbar.bg_color_changed.connect(image_view.set_background_color)`:
```python
        toolbar.threshold_clicked.connect(self._on_threshold_clicked)
```

3. Add the handler method after `_open_enhancement_dialog`:

```python
    def _on_threshold_clicked(self):
        from dialogs.threshold_dialog import ThresholdDialog
        if self._threshold_dialog is None:
            self._threshold_dialog = ThresholdDialog(self._window)
            self._threshold_dialog.threshold_changed.connect(
                self._on_threshold_changed)
        if self._image_model.is_loaded:
            self._threshold_dialog.set_image(self._image_model.display_image)
        self._threshold_dialog.show()
        self._threshold_dialog.raise_()
        self._threshold_dialog.activateWindow()

    def _on_threshold_changed(self, low: int, high: int, enabled: bool):
        self._image_model.set_threshold(low, high, enabled)
```

4. In `_on_image_loaded`, after `self._window.image_view.set_image(...)`, add:
```python
        # Reset threshold on new image load
        self._image_model.set_threshold(0, 255, False)
        if self._threshold_dialog is not None:
            self._threshold_dialog.reset()
            self._threshold_dialog.set_image(self._image_model.display_image)
```

5. In `_on_enhancement_params_changed`, after `self._image_model.update_display_image(enhanced)`, add:
```python
        # Update threshold dialog histogram when enhancement changes
        if self._threshold_dialog is not None:
            self._threshold_dialog.set_image(self._image_model.display_image)
```

- [ ] **Step 3: Full end-to-end verification**

Run `cd OptiMeasure_AOI && python main.py` and verify:

1. "閥值" button appears in toolbar
2. Click "閥値" → dialog opens showing empty histogram
3. Load an image → histogram auto-updates; drag Low/High sliders → red lines move on histogram
4. Check "顯示閥值" → canvas highlights pixels in range with toolbar line color (default green)
5. Uncheck → canvas returns to normal
6. Close dialog → if checkbox was checked, canvas keeps showing threshold
7. Reopen dialog → state (low/high/checked) is preserved
8. Change toolbar line color while threshold shown → overlay color changes live
9. Load a new image → threshold resets to 0/255 unchecked; histogram updates
10. Apply image enhancement → histogram updates

- [ ] **Step 4: Run all tests to confirm no regression**

```
cd c:\Users\vul32\Desktop\Claude\Measure_Img
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add OptiMeasure_AOI/views/toolbar.py OptiMeasure_AOI/controllers/main_controller.py
git commit -m "feat: add threshold button to toolbar and wire ThresholdDialog in controller"
```

---

## Self-Review Notes

- **Spec coverage:** All requirements covered: scale field (Task 1–4), threshold histogram + sliders (Task 8), non-modal persistent state (Task 9 step 2), overlay color from toolbar (Task 7), reset on new image load (Task 9 step 2), StatusBar unaffected (no changes to `get_pixel_value`).
- **Type consistency:** `compute_real_length(params, scale)` used consistently in Task 1 + 3. `apply_threshold_overlay(gray, low, high, overlay_bgr)` used in Task 5 + 6. `get_visible_image()` used in Task 6 + 7.
- **No placeholders:** All steps have complete code.
- **QSettings key:** `toolbar/scale` is new; existing `toolbar/color` key unchanged.
- **overlay_bgr default:** `(0, 255, 0)` = green, matches default toolbar color.
