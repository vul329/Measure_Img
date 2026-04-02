"""
image_view.py
影像顯示核心（View 層）

繼承 QGraphicsView，負責：
1. Drag & Drop 讀圖
2. 滾輪縮放（以游標為錨點）
3. 狀態機：平移/選取模式、各種繪圖模式
4. 滑鼠移動時發射像素座標信號
5. 繪圖模式下建立圖形（rubber band 即時預覽）
"""
import math
from enum import Enum, auto

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPixmap, QColor, QTransform, QPen, QPolygonF

from utils.image_utils import numpy_to_qimage


class ViewMode(Enum):
    """畫布操作模式（狀態機）"""
    SELECT_PAN = auto()   # 選取/平移模式（預設）
    DRAW_CIRCLE = auto()  # 繪製圓形
    DRAW_RECT1 = auto()   # 繪製正交矩形
    DRAW_RECT2 = auto()   # 繪製旋轉矩形
    DRAW_LINE = auto()    # 繪製直線


class ImageView(QGraphicsView):
    # ── 信號 ──
    # 滑鼠在影像上移動時發射：(pixel_x, pixel_y)
    pixel_hovered = Signal(int, int)
    # 影像成功拖曳載入時發射：(file_path)
    image_dropped = Signal(str)
    # 繪圖完成時發射：(shape_type_str, params_dict)
    shape_drawn = Signal(str, dict)
    # 滑鼠點擊時發射（放大鏡用）：(pixel_x, pixel_y)
    pixel_clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # ── Scene 設定 ──
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None

        # ── 縮放設定 ──
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._zoom_factor = 1.0
        self._zoom_min = 0.02
        self._zoom_max = 50.0

        # ── Drag & Drop ──
        self.setAcceptDrops(True)

        # ── 狀態機 ──
        self._mode = ViewMode.SELECT_PAN
        self._is_panning = False
        self._pan_start = QPointF()

        # ── 繪圖暫存 ──
        self._draw_start: QPointF | None = None     # 繪圖起始點（Scene 座標）
        self._preview_item = None                    # 即時預覽圖形物件

        # ── 繪圖外觀設定（由工具列同步） ──
        self._draw_color = QColor(0, 255, 0)
        self._draw_line_width = 2

        # ── 渲染品質 ──
        self.setRenderHint(self.renderHints().__class__.Antialiasing, False)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)

    # ──────────────────────────────────────────────
    # 影像更新
    # ──────────────────────────────────────────────

    def set_image(self, image_np):
        """
        接收 numpy array（display_image），轉為 QPixmap 顯示在 Scene 中。
        中高解析度影像使用 FastTransformation 提升縮放效能。
        """
        qimage = numpy_to_qimage(image_np)
        if qimage is None:
            return

        pixmap = QPixmap.fromImage(qimage)

        if self._pixmap_item is None:
            # 第一次載入：加入 Scene 並自適應顯示
            self._pixmap_item = QGraphicsPixmapItem(pixmap)
            # 縮放時使用快速插值，避免大圖卡頓
            self._pixmap_item.setTransformationMode(
                Qt.TransformationMode.FastTransformation
            )
            self._scene.addItem(self._pixmap_item)
            self._fit_in_view()
        else:
            # 更新現有 pixmap（增強效果改變時）
            self._pixmap_item.setPixmap(pixmap)

        # Scene 邊界設為影像大小
        self._scene.setSceneRect(QRectF(pixmap.rect()))

    def _fit_in_view(self):
        """自適應縮放：讓影像完整顯示在視窗內"""
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def clear_image(self):
        """清除畫布"""
        self._scene.clear()
        self._pixmap_item = None

    # ──────────────────────────────────────────────
    # 模式切換
    # ──────────────────────────────────────────────

    def set_mode(self, mode: ViewMode):
        """切換操作模式，更新游標外觀"""
        self._mode = mode
        if mode == ViewMode.SELECT_PAN:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            # 繪圖模式：十字游標
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_draw_color(self, color: QColor):
        self._draw_color = color

    def set_draw_line_width(self, width: int):
        self._draw_line_width = width

    # ──────────────────────────────────────────────
    # 滾輪縮放
    # ──────────────────────────────────────────────

    def wheelEvent(self, event):
        """
        以滑鼠游標位置為錨點進行縮放。
        AnchorUnderMouse 已設定，此處只需計算縮放比例。
        """
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.15
        else:
            factor = 1.0 / 1.15

        new_zoom = self._zoom_factor * factor
        if self._zoom_min <= new_zoom <= self._zoom_max:
            self._zoom_factor = new_zoom
            self.scale(factor, factor)

    # ──────────────────────────────────────────────
    # Drag & Drop 讀圖
    # ──────────────────────────────────────────────

    def dragEnterEvent(self, event):
        """接受拖曳的圖片檔（JPG/PNG/BMP）"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if path.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        """拖放完成：發射 image_dropped 信號，由 Controller 處理載入"""
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff')):
                self.image_dropped.emit(path)
                break

    # ──────────────────────────────────────────────
    # 滑鼠事件（平移 + 繪圖 + 像素探測）
    # ──────────────────────────────────────────────

    # ──────────────────────────────────────────────
    # 座標夾緊（方案 B）
    # ──────────────────────────────────────────────

    def _clamp_to_image(self, scene_pos: QPointF) -> QPointF:
        """
        將 scene_pos 夾緊在影像範圍內。
        影像的 bounding rect 為 (0, 0, width, height)。
        超出邊界的座標會被吸附到最近的邊緣。
        """
        if self._pixmap_item is None:
            return scene_pos
        r = self._pixmap_item.boundingRect()
        x = max(r.left(), min(scene_pos.x(), r.right()))
        y = max(r.top(),  min(scene_pos.y(), r.bottom()))
        return QPointF(x, y)

    def _is_inside_image(self, scene_pos: QPointF) -> bool:
        """判斷 scene_pos 是否在影像範圍內"""
        if self._pixmap_item is None:
            return False
        return self._pixmap_item.boundingRect().contains(scene_pos)

    # ──────────────────────────────────────────────
    # 滑鼠事件（平移 + 繪圖 + 像素探測）
    # ──────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())

            if self._mode == ViewMode.SELECT_PAN:
                self._is_panning = True
                self._pan_start = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                px, py = int(scene_pos.x()), int(scene_pos.y())
                self.pixel_clicked.emit(px, py)

            elif self._mode in (ViewMode.DRAW_CIRCLE, ViewMode.DRAW_RECT1,
                                 ViewMode.DRAW_RECT2, ViewMode.DRAW_LINE):
                # 影像外不允許開始繪圖（方案 B）
                if not self._is_inside_image(scene_pos):
                    return
                # 若點擊到已有圖形，讓 super 處理選取/移動，不開始繪圖
                hit_items = [i for i in self.items(event.position().toPoint())
                             if i is not self._pixmap_item]
                if not hit_items:
                    self._draw_start = self._clamp_to_image(scene_pos)
                    self._create_preview_item(self._draw_start)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        px, py = int(scene_pos.x()), int(scene_pos.y())

        # 發射像素座標信號（StatusBar 更新）
        if self._pixmap_item and self._pixmap_item.contains(
                self._pixmap_item.mapFromScene(scene_pos)):
            self.pixel_hovered.emit(px, py)

        # 方案 D：繪圖模式下，游標在影像外顯示禁止圖示
        if self._mode != ViewMode.SELECT_PAN and not self._is_panning:
            if self._pixmap_item and not self._is_inside_image(scene_pos):
                self.setCursor(Qt.CursorShape.ForbiddenCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

        if self._is_panning and self._mode == ViewMode.SELECT_PAN:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y()))
            return

        if self._draw_start and self._mode != ViewMode.SELECT_PAN:
            # 方案 B：預覽終點夾緊在影像範圍內
            clamped = self._clamp_to_image(scene_pos)
            self._update_preview_item(self._draw_start, clamped)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_panning:
                self._is_panning = False
                self.setCursor(Qt.CursorShape.ArrowCursor)

            elif self._draw_start and self._mode != ViewMode.SELECT_PAN:
                scene_pos = self.mapToScene(event.position().toPoint())
                self._remove_preview_item()
                # 方案 B：終點夾緊在影像範圍內
                end_pos = self._clamp_to_image(scene_pos)
                dx = end_pos.x() - self._draw_start.x()
                dy = end_pos.y() - self._draw_start.y()
                if math.sqrt(dx * dx + dy * dy) > 3:
                    self._finalize_draw(self._draw_start, end_pos)
                self._draw_start = None

        super().mouseReleaseEvent(event)

    # ──────────────────────────────────────────────
    # 繪圖預覽（橡皮筋效果）
    # ──────────────────────────────────────────────

    def _create_preview_item(self, start: QPointF):
        """建立繪圖預覽物件（虛線外觀）"""
        self._remove_preview_item()

        pen = QPen(self._draw_color, self._draw_line_width)
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setCosmetic(True)

        if self._mode == ViewMode.DRAW_CIRCLE:
            self._preview_item = self._scene.addEllipse(
                QRectF(start.x(), start.y(), 0, 0), pen)
        elif self._mode == ViewMode.DRAW_RECT1:
            self._preview_item = self._scene.addRect(
                QRectF(start.x(), start.y(), 0, 0), pen)
        elif self._mode == ViewMode.DRAW_RECT2:
            # 旋轉矩形預覽使用 Polygon，才能顯示任意角度的旋轉外框
            self._preview_item = self._scene.addPolygon(QPolygonF(), pen)
        elif self._mode == ViewMode.DRAW_LINE:
            self._preview_item = self._scene.addLine(
                start.x(), start.y(), start.x(), start.y(), pen)

    def _update_preview_item(self, start: QPointF, current: QPointF):
        """更新預覽物件的外觀（隨滑鼠移動即時更新）"""
        if not self._preview_item:
            return

        if self._mode == ViewMode.DRAW_CIRCLE:
            # 圓形：以起點為圓心，距離為半徑
            radius = math.sqrt((current.x() - start.x()) ** 2 +
                               (current.y() - start.y()) ** 2)
            self._preview_item.setRect(
                QRectF(start.x() - radius, start.y() - radius,
                       2 * radius, 2 * radius))

        elif self._mode == ViewMode.DRAW_RECT1:
            x1, y1 = min(start.x(), current.x()), min(start.y(), current.y())
            x2, y2 = max(start.x(), current.x()), max(start.y(), current.y())
            self._preview_item.setRect(QRectF(x1, y1, x2 - x1, y2 - y1))

        elif self._mode == ViewMode.DRAW_RECT2:
            # ── 旋轉矩形預覽計算 ──
            # 拖曳向量 → 旋轉角 + half_width
            dx = current.x() - start.x()
            dy = current.y() - start.y()
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 1:
                return
            angle_rad = math.atan2(dy, dx)   # 拖曳方向角（弧度）
            hw = dist / 2                     # 半長軸 = 拖曳距離的一半
            hh = hw * 0.4                     # 半短軸 = 長軸的 40%
            cx = (start.x() + current.x()) / 2
            cy = (start.y() + current.y()) / 2
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            # 計算旋轉後的四個頂點（以中心為原點旋轉）
            corners = []
            for sx, sy in [(hw, hh), (-hw, hh), (-hw, -hh), (hw, -hh)]:
                rx = cos_a * sx - sin_a * sy + cx
                ry = sin_a * sx + cos_a * sy + cy
                corners.append(QPointF(rx, ry))
            self._preview_item.setPolygon(QPolygonF(corners))

        elif self._mode == ViewMode.DRAW_LINE:
            line = self._preview_item.line()
            self._preview_item.setLine(
                line.x1(), line.y1(), current.x(), current.y())

    def _remove_preview_item(self):
        """移除預覽物件"""
        if self._preview_item:
            self._scene.removeItem(self._preview_item)
            self._preview_item = None

    # ──────────────────────────────────────────────
    # 確認繪製：發射信號給 Controller
    # ──────────────────────────────────────────────

    def _finalize_draw(self, start: QPointF, end: QPointF):
        """
        繪製完成，計算參數並透過 shape_drawn 信號通知 Controller。
        Controller 負責建立實際的圖形物件並加入 Scene 與 Model。
        """
        if self._mode == ViewMode.DRAW_CIRCLE:
            radius = math.sqrt((end.x() - start.x()) ** 2 +
                               (end.y() - start.y()) ** 2)
            params = {'cx': start.x(), 'cy': start.y(), 'radius': radius}
            self.shape_drawn.emit('circle', params)

        elif self._mode == ViewMode.DRAW_RECT1:
            params = {'col1': start.x(), 'row1': start.y(),
                      'col2': end.x(), 'row2': end.y()}
            self.shape_drawn.emit('rect1', params)

        elif self._mode == ViewMode.DRAW_RECT2:
            # ── 旋轉矩形：拖曳方向決定旋轉角與長軸 ──
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            dist = math.sqrt(dx * dx + dy * dy)
            hw = dist / 2                              # 半長軸
            hh = max(1.0, hw * 0.4)                   # 半短軸（長軸 40%）
            cx = (start.x() + end.x()) / 2
            cy = (start.y() + end.y()) / 2
            # atan2 回傳弧度，轉為度數供 Qt setRotation 使用
            # Qt 的 rotation()：順時針為正，與 atan2 方向一致（Y 軸向下）
            angle_deg = math.degrees(math.atan2(dy, dx))
            params = {'cx': cx, 'cy': cy, 'angle': angle_deg,
                      'half_width': hw, 'half_height': hh}
            self.shape_drawn.emit('rect2', params)

        elif self._mode == ViewMode.DRAW_LINE:
            params = {'x1': start.x(), 'y1': start.y(),
                      'x2': end.x(), 'y2': end.y()}
            self.shape_drawn.emit('line', params)

    # ──────────────────────────────────────────────
    # 存取 Scene（供 Controller 加入圖形物件）
    # ──────────────────────────────────────────────

    @property
    def graphics_scene(self) -> QGraphicsScene:
        return self._scene
