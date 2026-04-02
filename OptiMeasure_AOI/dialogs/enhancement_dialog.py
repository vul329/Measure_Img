"""
enhancement_dialog.py
影像增強子視窗（Dialog 層）

提供 Gamma 校正、線性縮放（Gain/Offset）的即時預覽控制。
僅修改 display_image，不改動 original_image。
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QSlider, QPushButton, QDoubleSpinBox, QGroupBox,
                                QFormLayout)
from PySide6.QtCore import Qt, Signal


class EnhancementDialog(QDialog):
    # 信號：參數改變時發射，由 Controller 套用增強並更新 display_image
    params_changed = Signal(float, float, float)  # gamma, gain, offset

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("影像增強")
        self.setMinimumWidth(360)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._building = True  # 避免初始化時觸發信號
        self._build_ui()
        self._building = False

    # ──────────────────────────────────────────────
    # UI 建構
    # ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Gamma 校正
        gamma_group = QGroupBox("Gamma 校正")
        gamma_layout = QFormLayout(gamma_group)

        self._gamma_slider = self._make_slider(10, 300, 100)  # 0.1 ~ 3.0，內部 *100
        self._gamma_label = QLabel("1.00")
        self._gamma_label.setMinimumWidth(40)
        self._gamma_slider.valueChanged.connect(self._on_gamma_changed)

        row = QHBoxLayout()
        row.addWidget(self._gamma_slider)
        row.addWidget(self._gamma_label)
        gamma_layout.addRow("Gamma:", row)
        layout.addWidget(gamma_group)

        # 線性縮放
        linear_group = QGroupBox("線性縮放 (Gain / Offset)")
        linear_layout = QFormLayout(linear_group)

        self._gain_slider = self._make_slider(10, 300, 100)   # 0.1 ~ 3.0
        self._gain_label = QLabel("1.00")
        self._gain_label.setMinimumWidth(40)
        self._gain_slider.valueChanged.connect(self._on_gain_changed)

        self._offset_slider = self._make_slider(-128, 128, 0)  # -128 ~ 128
        self._offset_label = QLabel("0")
        self._offset_label.setMinimumWidth(40)
        self._offset_slider.valueChanged.connect(self._on_offset_changed)

        row_gain = QHBoxLayout()
        row_gain.addWidget(self._gain_slider)
        row_gain.addWidget(self._gain_label)
        linear_layout.addRow("Gain:", row_gain)

        row_offset = QHBoxLayout()
        row_offset.addWidget(self._offset_slider)
        row_offset.addWidget(self._offset_label)
        linear_layout.addRow("Offset:", row_offset)

        layout.addWidget(linear_group)

        # 按鈕
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("重置")
        reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)

    def _make_slider(self, min_val: int, max_val: int, default: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default)
        return slider

    # ──────────────────────────────────────────────
    # Slider 事件
    # ──────────────────────────────────────────────

    def _on_gamma_changed(self, value: int):
        gamma = value / 100.0
        self._gamma_label.setText(f"{gamma:.2f}")
        if not self._building:
            self._emit_params()

    def _on_gain_changed(self, value: int):
        gain = value / 100.0
        self._gain_label.setText(f"{gain:.2f}")
        if not self._building:
            self._emit_params()

    def _on_offset_changed(self, value: int):
        self._offset_label.setText(str(value))
        if not self._building:
            self._emit_params()

    def _emit_params(self):
        """發射目前的增強參數"""
        self.params_changed.emit(
            self._gamma_slider.value() / 100.0,
            self._gain_slider.value() / 100.0,
            float(self._offset_slider.value())
        )

    def _on_reset(self):
        """重置所有參數為預設值"""
        self._building = True
        self._gamma_slider.setValue(100)
        self._gain_slider.setValue(100)
        self._offset_slider.setValue(0)
        self._building = False
        self._emit_params()

    # ──────────────────────────────────────────────
    # 取得目前參數值
    # ──────────────────────────────────────────────

    def get_params(self) -> tuple[float, float, float]:
        """回傳 (gamma, gain, offset)"""
        return (
            self._gamma_slider.value() / 100.0,
            self._gain_slider.value() / 100.0,
            float(self._offset_slider.value())
        )
