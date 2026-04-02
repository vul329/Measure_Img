"""
shape_model.py
圖形資料模型（Model 層）

職責：
- 維護畫布上所有幾何圖形物件的清單
- 提供新增、刪除、更新介面
- 透過信號通知 View 層（表格）同步更新
"""
from PySide6.QtCore import QObject, Signal


class ShapeModel(QObject):
    # 信號：新增圖形，帶入圖形物件
    shape_added = Signal(object)
    # 信號：移除圖形，帶入圖形物件
    shape_removed = Signal(object)
    # 信號：圖形參數更新，帶入圖形物件
    shape_updated = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 圖形清單：儲存 BaseShapeItem 子類別實例
        self._shapes: list = []
        # 自動遞增 ID
        self._next_id = 1

    # ──────────────────────────────────────────────
    # 圖形管理
    # ──────────────────────────────────────────────

    def add_shape(self, shape) -> int:
        """
        新增圖形至清單，指派唯一 ID，並發射 shape_added 信號。
        回傳指派的 ID。
        """
        shape.shape_id = self._next_id
        self._next_id += 1
        self._shapes.append(shape)
        self.shape_added.emit(shape)
        return shape.shape_id

    def remove_shape(self, shape) -> bool:
        """
        從清單移除指定圖形，並發射 shape_removed 信號。
        回傳 True 表示成功移除。
        """
        if shape in self._shapes:
            self._shapes.remove(shape)
            self.shape_removed.emit(shape)
            return True
        return False

    def remove_shape_by_id(self, shape_id: int) -> bool:
        """依 ID 移除圖形"""
        shape = self.get_shape_by_id(shape_id)
        if shape:
            return self.remove_shape(shape)
        return False

    def notify_shape_updated(self, shape):
        """
        當圖形被拖曳或修改後，由圖形物件呼叫此方法通知 Model。
        Model 再發射 shape_updated 信號，讓表格同步更新。
        """
        self.shape_updated.emit(shape)

    def clear_all(self):
        """清除所有圖形"""
        shapes_copy = self._shapes.copy()
        for shape in shapes_copy:
            self.remove_shape(shape)

    # ──────────────────────────────────────────────
    # 查詢
    # ──────────────────────────────────────────────

    def get_shape_by_id(self, shape_id: int):
        """依 ID 查詢圖形物件"""
        for shape in self._shapes:
            if shape.shape_id == shape_id:
                return shape
        return None

    @property
    def shapes(self) -> list:
        return self._shapes

    @property
    def count(self) -> int:
        return len(self._shapes)
