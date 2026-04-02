"""
base_item.py
圖形基類（Graphics Items 層）

所有幾何圖形（圓形、矩形、直線）共用的基礎行為：
- 選取狀態視覺回饋
- 鍵盤方向鍵像素級微調
- 右鍵選單刪除
- 空心繪製（Qt.NoBrush）
- 可自訂線色與線寬
- 圖形移動後通知 ShapeModel 更新表格
"""
from PySide6.QtWidgets import QGraphicsItem, QMenu
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor, QBrush


class BaseShapeItem(QGraphicsItem):
    """
    所有圖形的抽象基類。
    子類別必須實作：
      - boundingRect()
      - paint()
      - get_params() -> dict
      - get_type_name() -> str
    """

    def __init__(self, color: QColor = None, line_width: int = 2, parent=None):
        super().__init__(parent)

        # ── 圖形識別 ──
        self.shape_id: int = -1          # 由 ShapeModel.add_shape() 指派
        self._shape_model = None         # 由 Controller 在新增後設定

        # ── 外觀設定 ──
        self._color = color if color else QColor(0, 255, 0)  # 預設綠色
        self._line_width = line_width

        # ── 互動旗標 ──
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        # 接收鍵盤事件需要此旗標
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        # 位置改變時觸發 itemChange（用於通知 Model 更新）
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    # ──────────────────────────────────────────────
    # 外觀屬性
    # ──────────────────────────────────────────────

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, c: QColor):
        self._color = c
        self.update()

    @property
    def line_width(self) -> int:
        return self._line_width

    @line_width.setter
    def line_width(self, w: int):
        self._line_width = w
        self.update()

    def _get_pen(self) -> QPen:
        """建立繪製用的 QPen（正常狀態）"""
        pen = QPen(self._color, self._line_width)
        pen.setCosmetic(True)  # 固定螢幕像素寬度，不隨縮放改變
        return pen

    def _get_selected_pen(self) -> QPen:
        """選取狀態的 QPen（使用較亮的顏色 + 虛線）"""
        highlight = QColor(255, 200, 0)  # 金黃色高亮
        pen = QPen(highlight, self._line_width + 1)
        pen.setCosmetic(True)
        return pen

    # ──────────────────────────────────────────────
    # 鍵盤方向鍵微調
    # ──────────────────────────────────────────────

    def keyPressEvent(self, event):
        """
        方向鍵進行 1px 位置微調。
        圖形必須被選取且有 Focus 才會觸發。
        """
        delta = QPointF(0, 0)
        key = event.key()
        if key == Qt.Key.Key_Up:
            delta = QPointF(0, -1)
        elif key == Qt.Key.Key_Down:
            delta = QPointF(0, 1)
        elif key == Qt.Key.Key_Left:
            delta = QPointF(-1, 0)
        elif key == Qt.Key.Key_Right:
            delta = QPointF(1, 0)
        elif key == Qt.Key.Key_Delete:
            self._request_delete()
            return

        if delta != QPointF(0, 0):
            self.setPos(self.pos() + delta)
            event.accept()
        else:
            super().keyPressEvent(event)

    # ──────────────────────────────────────────────
    # 右鍵選單
    # ──────────────────────────────────────────────

    def contextMenuEvent(self, event):
        """右鍵選單：提供刪除選項"""
        menu = QMenu()
        delete_action = menu.addAction("刪除")
        action = menu.exec(event.screenPos().toPoint())
        if action == delete_action:
            self._request_delete()

    def _request_delete(self):
        """通知 ShapeModel 移除此圖形（由 Controller 處理實際刪除邏輯）"""
        if self._shape_model:
            self._shape_model.remove_shape(self)

    # ──────────────────────────────────────────────
    # 位置改變通知
    # ──────────────────────────────────────────────

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # ── 移動前攔截：確保圖形中心不超出影像範圍 ──
            # value 為提議的新 pos()（QPointF）
            scene = self.scene()
            if scene:
                rect = scene.sceneRect()   # sceneRect = 影像大小
                offset = self._center_offset()          # 中心相對 pos() 的偏移
                center = value + offset                  # 中心的預期 scene 座標
                # 夾緊中心到影像邊界
                cx = max(rect.left(), min(center.x(), rect.right()))
                cy = max(rect.top(),  min(center.y(), rect.bottom()))
                # 反推回 pos()
                return QPointF(cx - offset.x(), cy - offset.y())

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 移動完成後通知表格更新
            if self._shape_model:
                self._shape_model.notify_shape_updated(self)

        return super().itemChange(change, value)

    def _center_offset(self) -> QPointF:
        """
        回傳圖形幾何中心相對於 pos() 的本地偏移量。
        - Circle / Rect2：pos() 本身即中心，回傳 (0, 0)
        - Rect1：pos() 為左上角，中心需加上 (w/2, h/2)
        - Line：pos() 為起點，中心為線段中點
        子類別若有不同的 pos() 定義，應覆寫此方法。
        """
        return QPointF(0.0, 0.0)

    # ──────────────────────────────────────────────
    # 子類別必須實作的抽象方法
    # ──────────────────────────────────────────────

    def get_params(self) -> dict:
        """
        回傳此圖形的幾何參數字典，供表格顯示。
        例如圓形：{'type': 'Circle', 'cx': 100, 'cy': 200, 'radius': 50}
        """
        raise NotImplementedError

    def get_type_name(self) -> str:
        """回傳圖形類型名稱字串"""
        raise NotImplementedError
