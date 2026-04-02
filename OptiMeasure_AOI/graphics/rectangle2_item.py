"""
rectangle2_item.py
旋轉矩形圖形物件（帶任意角度）

參數：center(x, y)，angle（度），half_width，half_height
繪製：以中心旋轉的空心矩形，選取時顯示旋轉把手 + 四邊中點縮放把手

─────────────────────────────────────────────
本地座標系說明（Qt setRotation 的關鍵優勢）
─────────────────────────────────────────────
Qt 的 setRotation() 讓 item 的本地座標系永遠是「未旋轉」的：
  - 本地 x 軸 = 矩形長軸方向（half_width 方向）
  - 本地 y 軸 = 矩形短軸方向（half_height 方向）
  - event.pos() 在 mouseMoveEvent 中已是本地座標

因此縮放把手的數學極為簡單：
  拖曳右側把手 → new_hw = abs(mouse.x)   （不需要任何旋轉計算）
  拖曳下側把手 → new_hh = abs(mouse.y)

旋轉把手位置（本地座標）：矩形上方正中央
  handle_local = (0, -half_height - HANDLE_OFFSET)
旋轉角度計算：
  drag_scene → center_scene 的 atan2，加 90° 修正
─────────────────────────────────────────────
"""
import math
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from graphics.base_item import BaseShapeItem


HANDLE_RADIUS = 5    # 縮放把手半徑（螢幕像素）
ROT_HANDLE_R  = 6    # 旋轉把手半徑（螢幕像素）
HANDLE_OFFSET = 25   # 旋轉把手距矩形上緣的距離（本地座標像素）

# 縮放把手名稱與對應的本地座標偏移（由 _get_resize_handles 動態計算）
_RESIZE_NAMES = ('right', 'left', 'bottom', 'top')


class Rectangle2Item(BaseShapeItem):
    """
    旋轉矩形。
    - self.pos()      → 矩形中心的 Scene 座標
    - self.rotation() → 旋轉角度（度，Qt 順時針為正）
    - _hw             → half_width（本地 x 軸方向）
    - _hh             → half_height（本地 y 軸方向）
    """

    def __init__(self, cx: float, cy: float, angle_deg: float,
                 half_width: float, half_height: float,
                 color: QColor = None, line_width: int = 2, parent=None):
        super().__init__(color, line_width, parent)

        self.setPos(cx, cy)
        self.setRotation(angle_deg)

        self._hw = max(1.0, half_width)
        self._hh = max(1.0, half_height)

        # 互動狀態
        self._rotating = False           # 旋轉模式
        self._resize_handle: str | None = None  # 縮放中的把手名稱

    # ──────────────────────────────────────────────
    # 參數存取
    # ──────────────────────────────────────────────

    @property
    def half_width(self) -> float:
        return self._hw

    @property
    def half_height(self) -> float:
        return self._hh

    @property
    def angle_deg(self) -> float:
        return self.rotation()

    def get_center_scene(self) -> QPointF:
        return self.pos()

    # ──────────────────────────────────────────────
    # QGraphicsItem 必要方法
    # ──────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        """包含旋轉把手與四邊縮放把手的 bounding rect"""
        margin = max(HANDLE_RADIUS, ROT_HANDLE_R) + 2
        top_extra = HANDLE_OFFSET + ROT_HANDLE_R + margin
        return QRectF(
            -self._hw - margin,
            -self._hh - top_extra,
            2 * (self._hw + margin),
            self._hh + top_extra + self._hh + margin
        )

    def paint(self, painter: QPainter, option, widget=None):
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))

        if self.isSelected():
            painter.setPen(self._get_selected_pen())
        else:
            painter.setPen(self._get_pen())

        painter.drawRect(QRectF(-self._hw, -self._hh,
                                2 * self._hw, 2 * self._hh))

        if self.isSelected():
            self._draw_handles(painter)

    def _draw_handles(self, painter: QPainter):
        """繪製旋轉把手（圓形）與四邊縮放把手（方形）"""
        handle_pen = QPen(QColor(255, 200, 0), 1)
        handle_pen.setCosmetic(True)
        painter.setPen(handle_pen)
        painter.setBrush(QBrush(QColor(255, 200, 0)))

        # ── 旋轉把手（上方圓形）──
        rot_y = -self._hh - HANDLE_OFFSET
        painter.drawLine(QPointF(0, -self._hh), QPointF(0, rot_y))
        painter.drawEllipse(QPointF(0, rot_y), ROT_HANDLE_R, ROT_HANDLE_R)

        # ── 四邊中點縮放把手（方形）──
        for hx, hy in self._get_resize_handle_positions():
            painter.drawRect(QRectF(hx - HANDLE_RADIUS, hy - HANDLE_RADIUS,
                                    HANDLE_RADIUS * 2, HANDLE_RADIUS * 2))

    def _get_resize_handle_positions(self) -> list[tuple[float, float]]:
        """四邊中點的本地座標（右、左、下、上）"""
        return [
            ( self._hw,  0),        # right
            (-self._hw,  0),        # left
            ( 0,  self._hh),        # bottom
            ( 0, -self._hh),        # top
        ]

    # ──────────────────────────────────────────────
    # 把手命中判斷
    # ──────────────────────────────────────────────

    def _hit_rotation_handle(self, local_pos: QPointF) -> bool:
        rot_handle = QPointF(0, -self._hh - HANDLE_OFFSET)
        dist = math.sqrt((local_pos.x() - rot_handle.x()) ** 2 +
                         (local_pos.y() - rot_handle.y()) ** 2)
        return dist <= ROT_HANDLE_R * 2

    def _hit_resize_handle(self, local_pos: QPointF) -> str | None:
        """
        判斷是否命中縮放把手，回傳把手名稱或 None。
        命中半徑放大為 HANDLE_RADIUS * 2 以利操作。
        """
        for (hx, hy), name in zip(self._get_resize_handle_positions(),
                                   _RESIZE_NAMES):
            dist = math.sqrt((local_pos.x() - hx) ** 2 +
                             (local_pos.y() - hy) ** 2)
            if dist <= HANDLE_RADIUS * 2:
                return name
        return None

    # ──────────────────────────────────────────────
    # 滑鼠事件
    # ──────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected():
            local = event.pos()

            # 優先判斷旋轉把手
            if self._hit_rotation_handle(local):
                self._rotating = True
                event.accept()
                return

            # 再判斷縮放把手
            handle = self._hit_resize_handle(local)
            if handle:
                self._resize_handle = handle
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # ── 旋轉模式 ──
        if self._rotating:
            drag_scene  = event.scenePos()
            center_scene = self.pos()
            dx = drag_scene.x() - center_scene.x()
            dy = drag_scene.y() - center_scene.y()
            # atan2 + 90° 修正（把手初始在正上方）
            angle_deg = math.degrees(math.atan2(dy, dx)) + 90.0
            self.setRotation(angle_deg)
            if self._shape_model:
                self._shape_model.notify_shape_updated(self)
            event.accept()
            return

        # ── 縮放模式 ──
        if self._resize_handle:
            # event.pos() 已是本地座標（Qt 自動逆旋轉），直接取用
            lx = event.pos().x()
            ly = event.pos().y()
            self.prepareGeometryChange()

            if self._resize_handle == 'right':
                # 拖曳右側把手：abs(lx) = 新的 half_width
                self._hw = max(1.0, abs(lx))
            elif self._resize_handle == 'left':
                # 拖曳左側把手：負方向，絕對值即 half_width
                self._hw = max(1.0, abs(lx))
            elif self._resize_handle == 'bottom':
                self._hh = max(1.0, abs(ly))
            elif self._resize_handle == 'top':
                self._hh = max(1.0, abs(ly))

            if self._shape_model:
                self._shape_model.notify_shape_updated(self)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._rotating = False
        self._resize_handle = None
        super().mouseReleaseEvent(event)

    # ──────────────────────────────────────────────
    # 參數介面
    # ──────────────────────────────────────────────

    def get_params(self) -> dict:
        center = self.pos()
        return {
            'type': self.get_type_name(),
            'cx': round(center.x(), 2),
            'cy': round(center.y(), 2),
            'angle': round(self.rotation(), 2),
            'half_width': round(self._hw, 2),
            'half_height': round(self._hh, 2),
        }

    def get_type_name(self) -> str:
        return 'Rect2'
