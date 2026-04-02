"""
rectangle1_item.py
正交矩形圖形物件（角度固定為 0 度）

參數：row1, col1, row2, col2（對角兩點，Scene 座標）
繪製：空心矩形，選取時顯示四邊中點控制點（可拖曳調整大小）
"""
import math
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from graphics.base_item import BaseShapeItem


HANDLE_RADIUS = 5


class Rectangle1Item(BaseShapeItem):
    """
    正交矩形（角度固定 0/90 度）。

    座標說明：
    - self.pos() 為矩形左上角在 Scene 中的位置
    - _width, _height 為矩形的寬高（Scene 單位）
    - 因此右下角 = pos() + QPointF(_width, _height)

    與 Halcon gen_rectangle1(row1, col1, row2, col2) 對應：
    - row1 → py（上方 y）, col1 → px（左方 x）
    - row2 → py+h,         col2 → px+w
    """

    def __init__(self, col1: float, row1: float, col2: float, row2: float,
                 color: QColor = None, line_width: int = 2, parent=None):
        super().__init__(color, line_width, parent)

        # 確保 (x1,y1) 為左上角，(x2,y2) 為右下角
        x1, x2 = min(col1, col2), max(col1, col2)
        y1, y2 = min(row1, row2), max(row1, row2)

        # 以左上角作為 item 原點（pos）
        self.setPos(x1, y1)
        self._width = max(1.0, x2 - x1)
        self._height = max(1.0, y2 - y1)

        # 控制點拖曳狀態：'top'/'bottom'/'left'/'right' 或 None
        self._active_handle: str | None = None
        self._drag_start_pos: QPointF | None = None

    # ──────────────────────────────────────────────
    # 參數存取
    # ──────────────────────────────────────────────

    def get_rect_scene(self) -> tuple[float, float, float, float]:
        """回傳 (col1, row1, col2, row2)：即左上角與右下角的 Scene 座標"""
        p = self.pos()
        return p.x(), p.y(), p.x() + self._width, p.y() + self._height

    def get_center_scene(self) -> QPointF:
        p = self.pos()
        return QPointF(p.x() + self._width / 2, p.y() + self._height / 2)

    # ──────────────────────────────────────────────
    # QGraphicsItem 必要方法
    # ──────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        margin = HANDLE_RADIUS + 2
        return QRectF(-margin, -margin,
                      self._width + 2 * margin, self._height + 2 * margin)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        if self.isSelected():
            painter.setPen(self._get_selected_pen())
        else:
            painter.setPen(self._get_pen())

        painter.drawRect(QRectF(0, 0, self._width, self._height))

        if self.isSelected():
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter):
        """繪製四邊中點控制點"""
        handle_pen = QPen(QColor(255, 200, 0), 1)
        handle_pen.setCosmetic(True)
        painter.setPen(handle_pen)
        painter.setBrush(QBrush(QColor(255, 200, 0)))

        for hx, hy in self._get_handle_positions():
            painter.drawRect(QRectF(hx - HANDLE_RADIUS, hy - HANDLE_RADIUS,
                                    HANDLE_RADIUS * 2, HANDLE_RADIUS * 2))

    def _get_handle_positions(self) -> list[tuple[float, float]]:
        """四邊中點的本地座標"""
        return [
            (self._width / 2, 0),              # 上中
            (self._width / 2, self._height),   # 下中
            (0, self._height / 2),             # 左中
            (self._width, self._height / 2),   # 右中
        ]

    def _get_handle_names(self) -> list[str]:
        return ['top', 'bottom', 'left', 'right']

    # ──────────────────────────────────────────────
    # 滑鼠事件（拖曳控制點調整大小）
    # ──────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            handle = self._hit_handle(pos)
            if handle:
                self._active_handle = handle
                self._drag_start_pos = event.scenePos()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._active_handle:
            self._resize_by_handle(event.pos())
            if self._shape_model:
                self._shape_model.notify_shape_updated(self)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._active_handle = None
        super().mouseReleaseEvent(event)

    def _hit_handle(self, pos: QPointF) -> str | None:
        """判斷點擊位置命中哪個控制點，回傳名稱或 None"""
        for (hx, hy), name in zip(self._get_handle_positions(), self._get_handle_names()):
            dist = math.sqrt((pos.x() - hx) ** 2 + (pos.y() - hy) ** 2)
            if dist <= HANDLE_RADIUS * 2:
                return name
        return None

    def _resize_by_handle(self, local_pos: QPointF):
        """依控制點拖曳位置調整矩形大小"""
        self.prepareGeometryChange()
        x, y = local_pos.x(), local_pos.y()
        scene_pos = self.pos()

        if self._active_handle == 'top':
            # 拖曳上邊：移動 y 座標，高度反向調整
            new_y = scene_pos.y() + y
            new_h = self._height - y
            if new_h > 1:
                self.setPos(scene_pos.x(), new_y)
                self._height = new_h
        elif self._active_handle == 'bottom':
            self._height = max(1.0, y)
        elif self._active_handle == 'left':
            new_x = scene_pos.x() + x
            new_w = self._width - x
            if new_w > 1:
                self.setPos(new_x, scene_pos.y())
                self._width = new_w
        elif self._active_handle == 'right':
            self._width = max(1.0, x)

        self.update()

    # ──────────────────────────────────────────────
    # 參數介面
    # ──────────────────────────────────────────────

    def _center_offset(self) -> QPointF:
        """Rect1 的 pos() 為左上角，中心偏移為 (w/2, h/2)"""
        return QPointF(self._width / 2, self._height / 2)

    def get_params(self) -> dict:
        col1, row1, col2, row2 = self.get_rect_scene()
        cx = (col1 + col2) / 2
        cy = (row1 + row2) / 2
        return {
            'type': self.get_type_name(),
            'col1': round(col1, 2),
            'row1': round(row1, 2),
            'col2': round(col2, 2),
            'row2': round(row2, 2),
            'cx': round(cx, 2),
            'cy': round(cy, 2),
            'width': round(self._width, 2),
            'height': round(self._height, 2),
        }

    def get_type_name(self) -> str:
        return 'Rect1'
