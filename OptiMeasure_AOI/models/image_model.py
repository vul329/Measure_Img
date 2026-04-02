"""
image_model.py
影像資料模型（Model 層）

職責：
- 維護「原始影像 (original_image)」與「顯示影像 (display_image)」兩份 numpy array
- 原始影像：唯讀，用於 StatusBar 查詢真實像素值
- 顯示影像：套用 Gamma / 線性縮放等增強效果後的版本，用於主畫布顯示
- 自動偵測灰階（2D）或彩色（3D）
"""
import numpy as np
import cv2
from PySide6.QtCore import QObject, Signal


class ImageModel(QObject):
    # 信號：影像成功載入時發射，帶有寬度與高度
    image_loaded = Signal(int, int)
    # 信號：顯示影像更新時發射（增強參數改變）
    display_image_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_image: np.ndarray | None = None  # 原始影像，永不修改
        self._display_image: np.ndarray | None = None   # 顯示影像，可套用增強

    # ──────────────────────────────────────────────
    # 屬性存取
    # ──────────────────────────────────────────────

    @property
    def original_image(self) -> np.ndarray | None:
        return self._original_image

    @property
    def display_image(self) -> np.ndarray | None:
        return self._display_image

    @property
    def is_loaded(self) -> bool:
        return self._original_image is not None

    @property
    def is_grayscale(self) -> bool:
        """True = 灰階（2D array）；False = 彩色（3D array）"""
        if self._original_image is None:
            return True
        return self._original_image.ndim == 2

    @property
    def width(self) -> int:
        if self._original_image is None:
            return 0
        return self._original_image.shape[1]

    @property
    def height(self) -> int:
        if self._original_image is None:
            return 0
        return self._original_image.shape[0]

    # ──────────────────────────────────────────────
    # 載入影像
    # ──────────────────────────────────────────────

    def load_image(self, file_path: str) -> bool:
        """
        從檔案路徑載入影像。
        使用 cv2.IMREAD_UNCHANGED 讀取，保留原始通道數（灰階/彩色）。
        回傳 True 表示載入成功。
        """
        # imdecode + frombuffer 支援含中文路徑（Windows 相容）
        try:
            raw = np.fromfile(file_path, dtype=np.uint8)
            img = cv2.imdecode(raw, cv2.IMREAD_UNCHANGED)
        except Exception:
            return False

        if img is None:
            return False

        # 若為 16bit 影像，轉換為 8bit 顯示
        if img.dtype != np.uint8:
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # 若為 4 通道 (BGRA)，去除 Alpha 通道
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        self._original_image = img
        self._display_image = img.copy()  # 顯示影像初始為原始影像的複本

        self.image_loaded.emit(self.width, self.height)
        return True

    # ──────────────────────────────────────────────
    # 更新顯示影像（由影像增強 Dialog 呼叫）
    # ──────────────────────────────────────────────

    def update_display_image(self, enhanced: np.ndarray):
        """
        接收影像增強後的結果，更新顯示影像並發射信號通知畫布重繪。
        注意：original_image 始終不被修改。
        """
        self._display_image = enhanced
        self.display_image_updated.emit()

    def reset_display_image(self):
        """重置顯示影像為原始影像（增強效果全部清除）"""
        if self._original_image is not None:
            self._display_image = self._original_image.copy()
            self.display_image_updated.emit()

    # ──────────────────────────────────────────────
    # 像素值查詢（永遠從原始影像讀取）
    # ──────────────────────────────────────────────

    def get_pixel_value(self, x: int, y: int):
        """
        查詢原始影像在 (x, y) 位置的像素值。
        - 灰階：回傳 int
        - 彩色：回傳 (B, G, R) tuple

        座標：x = 欄 (column)，y = 列 (row)
        """
        if self._original_image is None:
            return None
        h, w = self._original_image.shape[:2]
        if x < 0 or x >= w or y < 0 or y >= h:
            return None

        val = self._original_image[y, x]
        if self.is_grayscale:
            return int(val)
        else:
            # OpenCV 為 BGR 順序
            return (int(val[0]), int(val[1]), int(val[2]))
