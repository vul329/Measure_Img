"""
magnifier_dialog.py
局部放大鏡子視窗（Dialog 層）

功能：
- 顯示游標附近的局部放大影像
- 中心繪製 1x1px 紅色方框標示
- 「跟隨滑鼠」Checkbox 與放大倍率 Combobox
- 兩種更新模式：勾選跟隨→mouseMoveEvent觸發；取消→mousePressEvent觸發
"""
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QCheckBox, QComboBox, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from utils.image_utils import crop_roi, numpy_to_qimage


# 放大鏡擷取的原圖 ROI 半徑（像素）
ROI_HALF_SIZE = 50


class MagnifierDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("局部放大鏡")
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setMinimumSize(250, 320)
        self.resize(300, 380)

        # 目前追蹤的原始影像（由 Controller 設定）
        self._source_image: np.ndarray | None = None

        self._build_ui()

    # ──────────────────────────────────────────────
    # UI 建構
    # ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 控制列
        ctrl_layout = QHBoxLayout()
        self._follow_checkbox = QCheckBox("跟隨滑鼠")
        self._follow_checkbox.setChecked(True)
        ctrl_layout.addWidget(self._follow_checkbox)

        ctrl_layout.addWidget(QLabel("倍率:"))
        self._scale_combo = QComboBox()
        self._scale_combo.addItems(["100%", "150%", "200%", "300%"])
        self._scale_combo.setCurrentIndex(1)  # 預設 150%
        ctrl_layout.addWidget(self._scale_combo)

        layout.addLayout(ctrl_layout)

        # 影像顯示區
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumSize(200, 200)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._image_label.setStyleSheet("background-color: #1a1a1a; border: 1px solid #444;")
        layout.addWidget(self._image_label)

        # 座標顯示
        self._coord_label = QLabel("X: --  Y: --")
        self._coord_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._coord_label)

    # ──────────────────────────────────────────────
    # 公開介面（由 Controller 呼叫）
    # ──────────────────────────────────────────────

    def set_source_image(self, image: np.ndarray):
        """設定來源影像（original_image），放大鏡從此擷取 ROI"""
        self._source_image = image

    @property
    def follow_mouse(self) -> bool:
        return self._follow_checkbox.isChecked()

    def update_at(self, pixel_x: int, pixel_y: int):
        """
        更新放大鏡顯示：擷取 (pixel_x, pixel_y) 附近的 ROI 並放大顯示。
        此方法同時被 mouseMoveEvent（跟隨模式）和 mousePressEvent（點擊模式）呼叫。
        """
        if self._source_image is None:
            return

        self._coord_label.setText(f"X: {pixel_x}  Y: {pixel_y}")

        # 1. 從原始影像擷取 ROI（不複製整張圖）
        roi = crop_roi(self._source_image, pixel_x, pixel_y, ROI_HALF_SIZE)

        # 2. 取得放大倍率
        scale_text = self._scale_combo.currentText()
        scale = int(scale_text.replace('%', '')) / 100.0

        # 3. 計算放大後的顯示尺寸
        display_w = self._image_label.width()
        display_h = self._image_label.height()

        # ROI 實際邊長
        roi_side = ROI_HALF_SIZE * 2 + 1
        # 放大後的像素大小
        pixel_size = max(1, int((min(display_w, display_h) / roi_side) * scale))

        # 縮放後的 ROI 大小
        scaled_w = roi.shape[1] * pixel_size
        scaled_h = roi.shape[0] * pixel_size

        # 4. 轉為 QImage 並縮放
        qimage = numpy_to_qimage(roi)
        if qimage is None:
            return

        pixmap = QPixmap.fromImage(qimage)
        scaled_pixmap = pixmap.scaled(
            scaled_w, scaled_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )

        # 5. 在放大影像中心繪製 1x1 像素的紅色方框
        scaled_pixmap = self._draw_center_marker(scaled_pixmap, pixel_size)

        self._image_label.setPixmap(scaled_pixmap)

    def _draw_center_marker(self, pixmap: QPixmap, pixel_size: int) -> QPixmap:
        """
        在 pixmap 中心繪製高對比色方框，標示目前對準的像素。
        方框大小 = 一個放大後的像素大小（pixel_size x pixel_size）。
        """
        result = pixmap.copy()
        painter = QPainter(result)

        cx = result.width() // 2
        cy = result.height() // 2
        half = max(1, pixel_size // 2)

        # 紅色方框
        pen = QPen(QColor(255, 0, 0), 2)
        pen.setCosmetic(False)
        painter.setPen(pen)
        painter.drawRect(cx - half, cy - half, pixel_size, pixel_size)

        painter.end()
        return result
