"""
main_controller.py
主控制器（Controller 層）

職責：
- 連接 ImageModel、ShapeModel 與各 View / Dialog 的信號與槽
- 協調雙向連動邏輯（圖形 ↔ 表格）
- 管理影像增強與放大鏡的開啟/關閉
- 處理圖形的建立、加入 Scene 與 Model
"""
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor

from models.image_model import ImageModel
from models.shape_model import ShapeModel
from views.main_window import MainWindow
from views.image_view import ViewMode
from graphics.circle_item import CircleItem
from graphics.rectangle1_item import Rectangle1Item
from graphics.rectangle2_item import Rectangle2Item
from graphics.line_item import LineItem
from utils.image_utils import apply_enhancements


class MainController(QObject):
    def __init__(self):
        super().__init__()

        # ── Model ──
        self._image_model = ImageModel()
        self._shape_model = ShapeModel()

        # ── View ──
        self._window = MainWindow()

        # ── Dialogs（延遲建立，按需開啟）──
        self._enhancement_dialog = None
        self._magnifier_dialog = None

        # ── 連接所有信號 ──
        self._connect_signals()

        # ── 顯示視窗 ──
        self._window.show()

    # ──────────────────────────────────────────────
    # 信號連接
    # ──────────────────────────────────────────────

    def _connect_signals(self):
        win = self._window
        toolbar = win.toolbar
        image_view = win.image_view
        right_panel = win.right_panel

        # 工具列 → 操作模式
        toolbar.mode_changed.connect(image_view.set_mode)
        toolbar.color_changed.connect(self._on_color_changed)
        toolbar.line_width_changed.connect(self._on_line_width_changed)
        toolbar.enhancement_clicked.connect(self._open_enhancement_dialog)
        toolbar.magnifier_clicked.connect(self._open_magnifier_dialog)

        # ImageView → 影像載入
        image_view.image_dropped.connect(self._on_image_dropped)
        # ImageView → StatusBar 更新
        image_view.pixel_hovered.connect(self._on_pixel_hovered)
        # ImageView → 放大鏡（移動模式）
        image_view.pixel_hovered.connect(self._on_pixel_hovered_for_magnifier)
        # ImageView → 放大鏡（點擊模式）
        image_view.pixel_clicked.connect(self._on_pixel_clicked_for_magnifier)
        # ImageView → 繪圖完成
        image_view.shape_drawn.connect(self._on_shape_drawn)

        # ImageModel → ImageView 更新
        self._image_model.image_loaded.connect(self._on_image_loaded)
        self._image_model.display_image_updated.connect(self._on_display_image_updated)

        # ShapeModel → RightPanel 表格同步
        self._shape_model.shape_added.connect(right_panel.add_shape_row)
        self._shape_model.shape_removed.connect(self._on_shape_removed)
        self._shape_model.shape_updated.connect(right_panel.update_shape_row)

        # RightPanel 表格 → 畫布高亮
        right_panel.table_row_selected.connect(self._on_table_row_selected)
        # RightPanel 刪除按鈕 → 移除圖形
        right_panel.table_row_deleted.connect(self._on_table_row_deleted)
        # RightPanel 刪除所有按鈕
        right_panel.table_all_deleted.connect(self._on_delete_all_shapes)

        # RightPanel 參數輸入
        right_panel.gen_circle_requested.connect(self._gen_circle)
        right_panel.gen_rect1_requested.connect(self._gen_rect1)
        right_panel.gen_rect2_requested.connect(self._gen_rect2)
        right_panel.gen_line_requested.connect(self._gen_line)

        # 啟動時將讀取到的顏色同步給 ImageView
        image_view.set_draw_color(toolbar.current_color)

    # ──────────────────────────────────────────────
    # 影像載入
    # ──────────────────────────────────────────────

    def _on_image_dropped(self, file_path: str):
        """拖曳讀圖：載入影像並更新顯示"""
        success = self._image_model.load_image(file_path)
        if success:
            self._window.status_bar.show_message(
                f"已載入：{file_path.split('/')[-1]}")
        else:
            self._window.status_bar.show_message(f"載入失敗：{file_path}")

    def _on_image_loaded(self, width: int, height: int):
        """ImageModel 載入成功 → 更新畫布顯示"""
        self._window.image_view.set_image(self._image_model.display_image)
        # 若放大鏡已開啟，更新來源影像
        if self._magnifier_dialog:
            self._magnifier_dialog.set_source_image(self._image_model.original_image)

    def _on_display_image_updated(self):
        """display_image 更新（增強效果改變）→ 重繪畫布"""
        self._window.image_view.set_image(self._image_model.display_image)

    # ──────────────────────────────────────────────
    # StatusBar 像素資訊
    # ──────────────────────────────────────────────

    def _on_pixel_hovered(self, px: int, py: int):
        """滑鼠移動 → 從原始影像讀取像素值 → 更新 StatusBar"""
        pixel_value = self._image_model.get_pixel_value(px, py)
        self._window.status_bar.update_pixel_info(px, py, pixel_value)

    # ──────────────────────────────────────────────
    # 外觀設定同步
    # ──────────────────────────────────────────────

    def _on_color_changed(self, color: QColor):
        self._window.image_view.set_draw_color(color)

    def _on_line_width_changed(self, width: int):
        self._window.image_view.set_draw_line_width(width)

    # ──────────────────────────────────────────────
    # 圖形建立（來自 ImageView 繪製）
    # ──────────────────────────────────────────────

    def _on_shape_drawn(self, shape_type: str, params: dict):
        """ImageView 繪製完成 → 建立圖形物件並加入 Scene 與 Model"""
        color = self._window.image_view._draw_color
        lw = self._window.image_view._draw_line_width

        if shape_type == 'circle':
            self._create_circle(params['cx'], params['cy'], params['radius'], color, lw)
        elif shape_type == 'rect1':
            self._create_rect1(params['col1'], params['row1'],
                               params['col2'], params['row2'], color, lw)
        elif shape_type == 'rect2':
            self._create_rect2(params['cx'], params['cy'], params['angle'],
                               params['half_width'], params['half_height'], color, lw)
        elif shape_type == 'line':
            self._create_line(params['x1'], params['y1'],
                              params['x2'], params['y2'], color, lw)

    # ──────────────────────────────────────────────
    # 圖形建立（來自參數輸入面板 gen_xxx）
    # ──────────────────────────────────────────────

    def _gen_circle(self, cx: float, cy: float, radius: float):
        color = self._window.image_view._draw_color
        lw = self._window.image_view._draw_line_width
        self._create_circle(cx, cy, radius, color, lw)

    def _gen_rect1(self, col1: float, row1: float, col2: float, row2: float):
        color = self._window.image_view._draw_color
        lw = self._window.image_view._draw_line_width
        self._create_rect1(col1, row1, col2, row2, color, lw)

    def _gen_rect2(self, cx: float, cy: float, angle: float, hw: float, hh: float):
        color = self._window.image_view._draw_color
        lw = self._window.image_view._draw_line_width
        self._create_rect2(cx, cy, angle, hw, hh, color, lw)

    def _gen_line(self, x1: float, y1: float, x2: float, y2: float):
        color = self._window.image_view._draw_color
        lw = self._window.image_view._draw_line_width
        self._create_line(x1, y1, x2, y2, color, lw)

    # ──────────────────────────────────────────────
    # 內部建立圖形工廠
    # ──────────────────────────────────────────────

    def _add_shape(self, item):
        """共用流程：設定 Model 參考 → 加入 Scene → 加入 Model"""
        item._shape_model = self._shape_model
        self._window.image_view.graphics_scene.addItem(item)
        self._shape_model.add_shape(item)

    def _create_circle(self, cx, cy, radius, color, lw):
        item = CircleItem(cx, cy, radius, color, lw)
        self._add_shape(item)

    def _create_rect1(self, col1, row1, col2, row2, color, lw):
        item = Rectangle1Item(col1, row1, col2, row2, color, lw)
        self._add_shape(item)

    def _create_rect2(self, cx, cy, angle, hw, hh, color, lw):
        item = Rectangle2Item(cx, cy, angle, hw, hh, color, lw)
        self._add_shape(item)

    def _create_line(self, x1, y1, x2, y2, color, lw):
        item = LineItem(x1, y1, x2, y2, color, lw)
        self._add_shape(item)

    # ──────────────────────────────────────────────
    # 圖形刪除
    # ──────────────────────────────────────────────

    def _on_shape_removed(self, shape):
        """ShapeModel 通知圖形移除 → 從 Scene 移除 + 從表格移除"""
        scene = self._window.image_view.graphics_scene
        if shape.scene() == scene:
            scene.removeItem(shape)
        self._window.right_panel.remove_shape_row(shape)

    def _on_table_row_deleted(self, shape_id: int):
        """表格刪除按鈕 → 通知 ShapeModel 移除圖形（由 _on_shape_removed 接手後續）"""
        self._shape_model.remove_shape_by_id(shape_id)

    def _on_delete_all_shapes(self):
        """刪除所有圖形：清除 ShapeModel（各 shape_removed 信號會逐一清除 Scene 與表格）"""
        self._shape_model.clear_all()

    # ──────────────────────────────────────────────
    # 雙向連動：表格選取 ↔ 畫布高亮
    # ──────────────────────────────────────────────

    def _on_table_row_selected(self, shape_id: int):
        """點擊表格行 → 清除其他選取 → 選取並顯示對應圖形"""
        scene = self._window.image_view.graphics_scene
        scene.clearSelection()

        shape = self._shape_model.get_shape_by_id(shape_id)
        if shape:
            shape.setSelected(True)
            shape.setFocus()
            # 確保圖形可見
            self._window.image_view.ensureVisible(shape)

    # ──────────────────────────────────────────────
    # 放大鏡
    # ──────────────────────────────────────────────

    def _open_magnifier_dialog(self):
        from dialogs.magnifier_dialog import MagnifierDialog
        if self._magnifier_dialog is None:
            self._magnifier_dialog = MagnifierDialog(self._window)
        if self._image_model.original_image is not None:
            self._magnifier_dialog.set_source_image(self._image_model.original_image)
        self._magnifier_dialog.show()
        self._magnifier_dialog.raise_()

    def _on_pixel_hovered_for_magnifier(self, px: int, py: int):
        """滑鼠移動 → 更新放大鏡（跟隨模式）"""
        if (self._magnifier_dialog and
                self._magnifier_dialog.isVisible() and
                self._magnifier_dialog.follow_mouse):
            self._magnifier_dialog.update_at(px, py)

    def _on_pixel_clicked_for_magnifier(self, px: int, py: int):
        """滑鼠點擊 → 更新放大鏡（靜態模式）"""
        if (self._magnifier_dialog and
                self._magnifier_dialog.isVisible() and
                not self._magnifier_dialog.follow_mouse):
            self._magnifier_dialog.update_at(px, py)

    # ──────────────────────────────────────────────
    # 影像增強
    # ──────────────────────────────────────────────

    def _open_enhancement_dialog(self):
        from dialogs.enhancement_dialog import EnhancementDialog
        if self._enhancement_dialog is None:
            self._enhancement_dialog = EnhancementDialog(self._window)
            self._enhancement_dialog.params_changed.connect(self._on_enhancement_params_changed)
        self._enhancement_dialog.show()
        self._enhancement_dialog.raise_()

    def _on_enhancement_params_changed(self, gamma: float, gain: float, offset: float):
        """增強 Dialog 參數改變 → 套用增強 → 更新 display_image"""
        if not self._image_model.is_loaded:
            return
        enhanced = apply_enhancements(
            self._image_model.original_image, gamma, gain, offset)
        self._image_model.update_display_image(enhanced)
