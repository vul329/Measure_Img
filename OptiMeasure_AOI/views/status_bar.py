"""
status_bar.py
狀態列（View 層）

顯示游標位置的像素座標與原始影像灰階/RGB 值。
灰階影像：X: 100  Y: 200  |  Gray: 128
彩色影像：X: 100  Y: 200  |  B: 50  G: 120  R: 200
"""
from PySide6.QtWidgets import QStatusBar, QLabel
from PySide6.QtCore import Qt


class StatusBarWidget(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._coord_label = QLabel("X: --  Y: --")
        self._pixel_label = QLabel("Gray: --")

        # 永久顯示（不被 showMessage 覆蓋）
        self.addPermanentWidget(self._coord_label)
        self.addPermanentWidget(self._pixel_label)

    def update_pixel_info(self, x: int, y: int, pixel_value):
        """
        更新座標與像素值顯示。
        pixel_value：int（灰階）或 (B, G, R) tuple（彩色）
        """
        self._coord_label.setText(f"X: {x}  Y: {y}")

        if pixel_value is None:
            self._pixel_label.setText("Gray: --")
        elif isinstance(pixel_value, int):
            self._pixel_label.setText(f"Gray: {pixel_value}")
        else:
            b, g, r = pixel_value
            self._pixel_label.setText(f"B: {b}  G: {g}  R: {r}")

    def show_message(self, msg: str, timeout: int = 3000):
        """顯示臨時訊息（例如：影像載入成功）"""
        self.showMessage(msg, timeout)
