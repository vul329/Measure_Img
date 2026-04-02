"""
coordinate_utils.py
座標轉換工具：處理 QGraphicsView scene 座標與影像像素座標之間的對應。
"""
from PySide6.QtCore import QPointF


def scene_to_pixel(scene_pos: QPointF) -> tuple[int, int]:
    """
    將 QGraphicsScene 座標轉換為影像像素座標（整數）。
    Scene 座標與像素座標的對應：Scene(x, y) → Pixel(col=x, row=y)。
    """
    return int(scene_pos.x()), int(scene_pos.y())


def pixel_to_scene(px: int, py: int) -> QPointF:
    """
    將影像像素座標轉換為 QGraphicsScene 座標。
    """
    return QPointF(float(px), float(py))


def clamp_to_image(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """
    將座標限制在影像邊界內，防止越界存取。
    """
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))
    return x, y
