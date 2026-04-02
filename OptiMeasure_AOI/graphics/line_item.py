"""
line_item.py
直線圖形物件

參數：(x1, y1)，(x2, y2)（Scene 座標）
選取時顯示端點控制點（可拖曳調整位置）
"""
import math
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from graphics.base_item import BaseShapeItem


HANDLE_RADIUS = 5


class LineItem(BaseShapeItem):
    """
    直線圖形。
    - self.pos() 為起點 (x1, y1) 在 Scene 的位置
    - _end_local 為終點相對於起點的本地偏移量

    設計原則：以起點作為 item 原點，終點以本地座標儲存，
    這樣拖曳整條線時只需移動 pos()，端點相對位置不變。
    """

    def __init__(self, x1: float, y1: float, x2: float, y2: float,
                 color: QColor = None, line_width: int = 2, parent=None):
        super().__init__(color, line_width, parent)

        # 起點設為 item 的 pos（Scene 座標）
        self.setPos(x1, y1)
        # 終點為相對起點的本地偏移
        self._end_local = QPointF(x2 - x1, y2 - y1)

        # 端點控制點拖曳狀態：'start'/'end' 或 None
        self._active_handle: str | None = None

    # ──────────────────────────────────────────────
    # 參數存取
    # ──────────────────────────────────────────────

    def get_start_scene(self) -> QPointF:
        return self.pos()

    def get_end_scene(self) -> QPointF:
        return self.pos() + self._end_local

    def get_length(self) -> float:
        """計算直線長度"""
        return math.sqrt(self._end_local.x() ** 2 + self._end_local.y() ** 2)

    # ──────────────────────────────────────────────
    # QGraphicsItem 必要方法
    # ──────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        """bounding rect 包含線段本體與端點控制點"""
        margin = HANDLE_RADIUS + 2
        x1, y1 = 0, 0
        x2, y2 = self._end_local.x(), self._end_local.y()
        min_x = min(x1, x2) - margin
        min_y = min(y1, y2) - margin
        max_x = max(x1, x2) + margin
        max_y = max(y1, y2) + margin
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def paint(self, painter: QPainter, option, widget=None):
        if self.isSelected():
            painter.setPen(self._get_selected_pen())
        else:
            painter.setPen(self._get_pen())

        # 繪製直線（起點為本地原點，終點為 _end_local）
        painter.drawLine(QPointF(0, 0), self._end_local)

        if self.isSelected():
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter):
        """繪製兩端點控制點"""
        handle_pen = QPen(QColor(255, 200, 0), 1)
        handle_pen.setCosmetic(True)
        painter.setPen(handle_pen)
        painter.setBrush(QBrush(QColor(255, 200, 0)))

        for hx, hy in [(0, 0), (self._end_local.x(), self._end_local.y())]:
            painter.drawRect(QRectF(hx - HANDLE_RADIUS, hy - HANDLE_RADIUS,
                                    HANDLE_RADIUS * 2, HANDLE_RADIUS * 2))

    # ──────────────────────────────────────────────
    # 端點控制點互動
    # ──────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            handle = self._hit_handle(pos)
            if handle:
                self._active_handle = handle
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._active_handle:
            pos = event.pos()
            self.prepareGeometryChange()

            if self._active_handle == 'start':
                # 拖曳起點：需要更新 pos() 並反向調整 _end_local
                # 新的起點 Scene 座標 = 舊起點 + 拖曳偏移
                old_pos = self.pos()
                # pos() 的本地座標始終是 (0,0)，所以拖曳偏移就是 event.pos()
                new_pos = old_pos + pos  # pos 是本地偏移
                delta = pos  # 起點移動的量
                self._end_local = self._end_local - delta
                self.setPos(new_pos)
            elif self._active_handle == 'end':
                # 拖曳終點：只更新 _end_local
                self._end_local = QPointF(pos.x(), pos.y())

            if self._shape_model:
                self._shape_model.notify_shape_updated(self)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._active_handle = None
        super().mouseReleaseEvent(event)

    def _hit_handle(self, pos: QPointF) -> str | None:
        """判斷是否命中端點控制點"""
        # 起點（本地 0,0）
        if math.sqrt(pos.x() ** 2 + pos.y() ** 2) <= HANDLE_RADIUS * 2:
            return 'start'
        # 終點
        dx = pos.x() - self._end_local.x()
        dy = pos.y() - self._end_local.y()
        if math.sqrt(dx ** 2 + dy ** 2) <= HANDLE_RADIUS * 2:
            return 'end'
        return None

    # ──────────────────────────────────────────────
    # 參數介面
    # ──────────────────────────────────────────────

    def _center_offset(self) -> QPointF:
        """Line 的 pos() 為起點，中心為線段中點"""
        return QPointF(self._end_local.x() / 2, self._end_local.y() / 2)

    def get_params(self) -> dict:
        start = self.get_start_scene()
        end = self.get_end_scene()
        return {
            'type': self.get_type_name(),
            'x1': round(start.x(), 2),
            'y1': round(start.y(), 2),
            'x2': round(end.x(), 2),
            'y2': round(end.y(), 2),
            'length': round(self.get_length(), 2),
        }

    def get_type_name(self) -> str:
        return 'Line'
