# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
cd OptiMeasure_AOI
python main.py
```

## Environment

- Python 3.10.11
- PySide6 6.10.2
- opencv-python 4.13.0
- numpy 2.2.6

**Note:** `QAction` and `QActionGroup` are in `PySide6.QtGui`, not `QtWidgets`. High-DPI attributes (`AA_EnableHighDpiScaling`) are removed in PySide6 6.x.

## Architecture (MVC)

```
OptiMeasure_AOI/
├── main.py                          # Entry point
├── controllers/main_controller.py   # Central hub: wires all signals/slots
├── models/
│   ├── image_model.py               # Dual-layer image (original + display numpy arrays)
│   └── shape_model.py               # Shape list with add/remove/update signals
├── views/
│   ├── main_window.py               # QMainWindow: left ImageView + right RightPanel splitter
│   ├── image_view.py                # QGraphicsView subclass (core canvas)
│   ├── right_panel.py               # Param input tabs + QTableWidget
│   ├── toolbar.py                   # Mode buttons, color picker, line width
│   └── status_bar.py                # Pixel coord + gray/RGB value display
├── dialogs/
│   ├── enhancement_dialog.py        # Gamma/Gain/Offset sliders (live preview)
│   └── magnifier_dialog.py          # ROI magnifier with follow-mouse toggle
├── graphics/
│   ├── base_item.py                 # Abstract base: selection, keyboard nudge, delete, move clamping
│   ├── circle_item.py
│   ├── rectangle1_item.py           # Axis-aligned rect
│   ├── rectangle2_item.py           # Rotated rect
│   └── line_item.py
└── utils/
    ├── image_utils.py               # apply_gamma, apply_linear, crop_roi, numpy_to_qimage
    └── coordinate_utils.py          # scene↔pixel coordinate helpers
```

## Key Design Decisions

### Dual-layer image
`ImageModel` holds `original_image` (never modified) and `display_image` (enhanced copy). StatusBar pixel queries always read `original_image`. Enhancement dialog writes to `display_image` via `update_display_image()`.

### Coordinate system
`QGraphicsScene` rect is set to the exact image size `(0, 0, w, h)`. Scene coordinates map 1:1 to pixel coordinates. `mapToScene()` → `int()` gives the pixel index.

### Shape items
All shapes inherit `BaseShapeItem` (QGraphicsItem). `pos()` is the shape's anchor:
- **Circle / Rect2**: `pos()` = geometric center
- **Rect1**: `pos()` = top-left corner; center offset = `(w/2, h/2)`
- **Line**: `pos()` = start point; center offset = `(dx/2, dy/2)`

Movement clamping uses `itemChange(ItemPositionChange)` in `base_item.py`, which reads `scene.sceneRect()` as the image boundary. Each subclass overrides `_center_offset()` if its anchor ≠ center.

### Drawing flow
`ImageView` handles mouse events and emits `shape_drawn(type_str, params_dict)`. `MainController` receives this signal and calls the appropriate factory method to create the graphics item, call `scene.addItem()`, and register with `ShapeModel`.

### Rect2 local coordinate advantage
Because `setRotation()` is used, `event.pos()` inside `Rectangle2Item.mouseMoveEvent` is already in unrotated local space. Resize handles use `abs(event.pos().x())` / `abs(event.pos().y())` directly as the new `half_width` / `half_height` — no trigonometry needed.

### Drawing boundary enforcement
`ImageView._clamp_to_image()` clamps scene positions to `_pixmap_item.boundingRect()`. Applied at press (prevents starting draw outside image), move (preview snaps to edge), and release (final shape stays within bounds).

### Table ↔ canvas bidirectional sync
- Shape added/moved → `ShapeModel` emits signal → `RightPanel.add_shape_row` / `update_shape_row`
- Table row clicked → `MainController._on_table_row_selected` → `shape.setSelected(True)`
- Table delete button → `MainController._on_table_row_deleted` → `ShapeModel.remove_shape_by_id` → `_on_shape_removed` removes from both scene and table
