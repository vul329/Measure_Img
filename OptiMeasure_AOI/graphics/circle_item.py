"""
circle_item.py
圓形圖形物件

參數：center(x, y)（Scene 座標），radius
繪製：空心圓（Qt.NoBrush），選取時顯示中心十字與半徑控制點
"""
import math
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from graphics.base_item import BaseShapeItem


# 控制點半徑（螢幕像素）
HANDLE_RADIUS = 5


class CircleItem(BaseShapeItem):
    """
    圓形圖形。
    內部以「圓心座標 + 半徑」儲存參數。
    圓心對應 QGraphicsItem 的 pos()，半徑為相對長度。

    座標說明：
    - self.pos() 為圓心在 Scene 中的位置
    - _radius 為圓的半徑（Scene 單位 = 像素單位）
    """

    def __init__(self, cx: float, cy: float, radius: float,
                 color: QColor = None, line_width: int = 2, parent=None):
        super().__init__(color, line_width, parent)
        # 將圓心設為 item 的原點（pos），便於拖曳移動
        self.setPos(cx, cy)
        self._radius = max(1.0, radius)

        # 互動狀態：是否正在拖曳半徑控制點
        self._dragging_handle = False

    # ──────────────────────────────────────────────
    # 參數存取
    # ──────────────────────────────────────────────

    @property
    def radius(self) -> float:
        return self._radius

    @radius.setter
    def radius(self, r: float):
        self.prepareGeometryChange()
        self._radius = max(1.0, r)
        self.update()

    def get_center_scene(self) -> QPointF:
        """取得圓心的 Scene 座標"""
        return self.pos()

    # ──────────────────────────────────────────────
    # QGraphicsItem 必要方法
    # ──────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        """
        bounding rect 以圓心為原點，加上控制點大小的 margin。
        """
        margin = HANDLE_RADIUS + 2
        return QRectF(-self._radius - margin, -self._radius - margin,
                      2 * (self._radius + margin), 2 * (self._radius + margin))

    def paint(self, painter: QPainter, option, widget=None):
        """繪製圓形（空心）及選取狀態的控制點"""
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))  # 空心：不填色

        if self.isSelected():
            painter.setPen(self._get_selected_pen())
        else:
            painter.setPen(self._get_pen())

        # 繪製圓形（以原點為圓心）
        painter.drawEllipse(QPointF(0, 0), self._radius, self._radius)

        # 選取時繪製輔助元素
        if self.isSelected():
            self._draw_selected_decorations(painter)

    def _draw_selected_decorations(self, painter: QPainter):
        """選取狀態：繪製中心十字與半徑控制點"""
        handle_pen = QPen(QColor(255, 200, 0), 1)
        handle_pen.setCosmetic(True)
        painter.setPen(handle_pen)

        # 中心十字
        cross_size = 8
        painter.drawLine(QPointF(-cross_size, 0), QPointF(cross_size, 0))
        painter.drawLine(QPointF(0, -cross_size), QPointF(0, cross_size))

        # 半徑控制點（四個方向各一個小方框）
        painter.setBrush(QBrush(QColor(255, 200, 0)))
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            hx = dx * self._radius
            hy = dy * self._radius
            painter.drawRect(QRectF(hx - HANDLE_RADIUS, hy - HANDLE_RADIUS,
                                    HANDLE_RADIUS * 2, HANDLE_RADIUS * 2))

    # ──────────────────────────────────────────────
    # 滑鼠事件（拖曳控制點調整半徑）
    # ──────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 判斷是否點擊到半徑控制點
            pos = event.pos()
            if self._is_on_handle(pos):
                self._dragging_handle = True
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging_handle:
            # 計算游標到圓心的距離作為新半徑
            pos = event.pos()
            new_radius = math.sqrt(pos.x() ** 2 + pos.y() ** 2)
            self.radius = max(1.0, new_radius)
            if self._shape_model:
                self._shape_model.notify_shape_updated(self)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging_handle = False
        super().mouseReleaseEvent(event)

    def _is_on_handle(self, pos: QPointF) -> bool:
        """判斷點擊位置是否在任一控制點上"""
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            hx = dx * self._radius
            hy = dy * self._radius
            dist = math.sqrt((pos.x() - hx) ** 2 + (pos.y() - hy) ** 2)
            if dist <= HANDLE_RADIUS * 2:
                return True
        return False

    # ──────────────────────────────────────────────
    # 參數介面
    # ──────────────────────────────────────────────

    def get_params(self) -> dict:
        """回傳圓形幾何參數（Scene 座標）"""
        center = self.pos()
        return {
            'type': self.get_type_name(),
            'cx': round(center.x(), 2),
            'cy': round(center.y(), 2),
            'radius': round(self._radius, 2),
        }

    def get_type_name(self) -> str:
        return 'Circle'
