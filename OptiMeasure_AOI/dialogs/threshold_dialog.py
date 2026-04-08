"""
threshold_dialog.py
Threshold 對話框（非模態，狀態持續）

包含：
- HistogramWidget：QPainter 自繪 256-bin histogram，標示 Low/High 垂直線
- ThresholdDialog：Low/High QSlider + QSpinBox 雙向同步，「顯示閥值」勾選項
"""
import numpy as np
import cv2

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QSlider, QSpinBox, QCheckBox, QPushButton,
                                QWidget)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPainter, QColor, QPen


class HistogramWidget(QWidget):
    """QPainter-based 256-bin histogram with Low/High marker lines."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(512, 180)
        self._hist = None   # np.ndarray shape (256,)
        self._low = 0
        self._high = 255

    def set_image(self, img: np.ndarray):
        """Compute histogram from image (converts to grayscale if needed)."""
        if img is None:
            self._hist = None
            self.update()
            return
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self._hist, _ = np.histogram(gray.ravel(), bins=256, range=(0, 256))
        self.update()

    def set_range(self, low: int, high: int):
        self._low = low
        self._high = high
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(240, 240, 240))

        if self._hist is None:
            return

        w = self.width()
        h = self.height()
        max_val = max(1, int(self._hist.max()))
        bar_w = w / 256.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(60, 60, 60))
        for i, count in enumerate(self._hist):
            bar_h = int(count / max_val * h)
            x = int(i * bar_w)
            painter.drawRect(x, h - bar_h, max(1, int(bar_w + 0.5)), bar_h)

        # Low and High marker lines (red)
        pen = QPen(QColor(220, 0, 0), 2)
        painter.setPen(pen)
        low_x = int(self._low * bar_w)
        painter.drawLine(low_x, 0, low_x, h)
        high_x = int(self._high * bar_w)
        painter.drawLine(high_x, 0, high_x, h)


class ThresholdDialog(QDialog):
    """Non-modal threshold dialog. State persists after close."""

    threshold_changed = Signal(int, int, bool)  # low, high, enabled

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Threshold")
        # Tool window stays on top of parent but doesn't block it
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Tool)
        # Prevent Qt from destroying the object when user closes the window
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._build_ui()
        self._connect_signals()

    # ──────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Histogram
        self._histogram = HistogramWidget()
        layout.addWidget(self._histogram)

        # Low threshold row
        low_row = QHBoxLayout()
        low_row.addWidget(QLabel("Low:"))
        self._low_slider = QSlider(Qt.Orientation.Horizontal)
        self._low_slider.setRange(0, 255)
        self._low_slider.setValue(0)
        self._low_spin = QSpinBox()
        self._low_spin.setRange(0, 255)
        self._low_spin.setValue(0)
        self._low_spin.setFixedWidth(60)
        low_row.addWidget(self._low_slider)
        low_row.addWidget(self._low_spin)
        layout.addLayout(low_row)

        # High threshold row
        high_row = QHBoxLayout()
        high_row.addWidget(QLabel("High:"))
        self._high_slider = QSlider(Qt.Orientation.Horizontal)
        self._high_slider.setRange(0, 255)
        self._high_slider.setValue(255)
        self._high_spin = QSpinBox()
        self._high_spin.setRange(0, 255)
        self._high_spin.setValue(255)
        self._high_spin.setFixedWidth(60)
        high_row.addWidget(self._high_slider)
        high_row.addWidget(self._high_spin)
        layout.addLayout(high_row)

        # Show threshold checkbox
        self._show_checkbox = QCheckBox("顯示閥值")
        layout.addWidget(self._show_checkbox)

        # Close button
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)

    def _connect_signals(self):
        # Slider ↔ SpinBox bidirectional sync (no infinite loop: setValue doesn't
        # emit valueChanged when value is unchanged)
        self._low_slider.valueChanged.connect(self._low_spin.setValue)
        self._low_spin.valueChanged.connect(self._low_slider.setValue)
        self._low_spin.valueChanged.connect(self._on_params_changed)

        self._high_slider.valueChanged.connect(self._high_spin.setValue)
        self._high_spin.valueChanged.connect(self._high_slider.setValue)
        self._high_spin.valueChanged.connect(self._on_params_changed)

        self._show_checkbox.stateChanged.connect(self._on_params_changed)

    # ──────────────────────────────────────────────
    # Slots
    # ──────────────────────────────────────────────

    def _on_params_changed(self):
        low = self._low_spin.value()
        high = self._high_spin.value()
        enabled = self._show_checkbox.isChecked()
        self._histogram.set_range(low, high)
        self.threshold_changed.emit(low, high, enabled)

    # ──────────────────────────────────────────────
    # Public API (called by Controller)
    # ──────────────────────────────────────────────

    def set_image(self, img: np.ndarray):
        """Load image for histogram computation."""
        self._histogram.set_image(img)

    def reset(self):
        """Reset to Low=0, High=255, unchecked. Emits threshold_changed once."""
        for w in [self._low_slider, self._low_spin,
                  self._high_slider, self._high_spin, self._show_checkbox]:
            w.blockSignals(True)
        self._low_slider.setValue(0)
        self._low_spin.setValue(0)
        self._high_slider.setValue(255)
        self._high_spin.setValue(255)
        self._show_checkbox.setChecked(False)
        for w in [self._low_slider, self._low_spin,
                  self._high_slider, self._high_spin, self._show_checkbox]:
            w.blockSignals(False)
        self._histogram.set_range(0, 255)
        self.threshold_changed.emit(0, 255, False)
