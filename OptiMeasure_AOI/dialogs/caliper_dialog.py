"""
caliper_dialog.py
卡尺抓圓參數設定對話框（Dialog 層）

功能：
- 顯示卡尺偵測可調參數（射線數、搜尋帶、梯度方向、RANSAC 容忍）
- 每次參數改變即重新偵測，即時發射 detection_updated 信號供 Controller 更新預覽
- 按確認後發射 detection_accepted 信號，由 Controller 建立正式 CircleItem
"""
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QSpinBox, QComboBox, QDoubleSpinBox,
                                QDialogButtonBox, QGroupBox)
from PySide6.QtCore import Signal, Qt

from utils.image_utils import caliper_find_circle


class CaliperCircleDialog(QDialog):
    # 即時預覽用：每次偵測完成後發射
    detection_updated = Signal(float, float, float)   # cx, cy, r
    # 使用者按確認後發射
    detection_accepted = Signal(float, float, float)  # cx, cy, r

    def __init__(self, image: np.ndarray,
                 cx: float, cy: float, radius: float,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("卡尺抓圓")
        self.setMinimumWidth(290)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._image = image
        self._approx_cx = cx
        self._approx_cy = cy
        self._approx_radius = radius
        self._last_result: dict = {
            'cx': cx, 'cy': cy, 'radius': radius,
            'inliers': 0, 'total': 0, 'success': False,
        }

        self._build_ui()
        self._run_detection()

    # ──────────────────────────────────────────────
    # UI 建構
    # ──────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── 參數群組 ──
        param_group = QGroupBox("偵測參數")
        pg = QVBoxLayout(param_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("射線數:"))
        self._rays_spin = QSpinBox()
        self._rays_spin.setRange(12, 72)
        self._rays_spin.setValue(36)
        self._rays_spin.setSingleStep(6)
        row1.addWidget(self._rays_spin)
        pg.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("搜尋帶 ±%:"))
        self._band_spin = QSpinBox()
        self._band_spin.setRange(5, 50)
        self._band_spin.setValue(20)
        row2.addWidget(self._band_spin)
        pg.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("梯度方向:"))
        self._edge_combo = QComboBox()
        self._edge_combo.addItems(["不限", "暗→亮", "亮→暗"])
        row3.addWidget(self._edge_combo)
        pg.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("RANSAC 容忍 (px):"))
        self._tol_spin = QDoubleSpinBox()
        self._tol_spin.setRange(1.0, 5.0)
        self._tol_spin.setValue(2.0)
        self._tol_spin.setSingleStep(0.5)
        row4.addWidget(self._tol_spin)
        pg.addLayout(row4)

        layout.addWidget(param_group)

        # ── 結果群組 ──
        result_group = QGroupBox("偵測結果")
        rg = QVBoxLayout(result_group)
        self._result_label = QLabel("偵測中...")
        self._result_label.setWordWrap(True)
        rg.addWidget(self._result_label)
        layout.addWidget(result_group)

        # ── 確認 / 取消 ──
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._on_accepted)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # ── 參數改變 → 重新偵測 ──
        self._rays_spin.valueChanged.connect(self._run_detection)
        self._band_spin.valueChanged.connect(self._run_detection)
        self._edge_combo.currentIndexChanged.connect(self._run_detection)
        self._tol_spin.valueChanged.connect(self._run_detection)

    # ──────────────────────────────────────────────
    # 偵測邏輯
    # ──────────────────────────────────────────────

    _EDGE_MAP = {0: 'any', 1: 'dark_to_light', 2: 'light_to_dark'}

    def _run_detection(self):
        result = caliper_find_circle(
            self._image,
            self._approx_cx, self._approx_cy, self._approx_radius,
            n_rays=self._rays_spin.value(),
            band_ratio=self._band_spin.value() / 100.0,
            edge_dir=self._EDGE_MAP[self._edge_combo.currentIndex()],
            ransac_tol=self._tol_spin.value(),
        )
        self._last_result = result

        if result['success']:
            self._result_label.setText(
                f"cx: {result['cx']:.1f}   cy: {result['cy']:.1f}\n"
                f"半徑: {result['radius']:.1f}   "
                f"吻合點: {result['inliers']} / {result['total']}"
            )
        else:
            self._result_label.setText(
                f"⚠ 偵測失敗（吻合點不足）\n"
                f"cx: {result['cx']:.1f}   cy: {result['cy']:.1f}\n"
                f"半徑: {result['radius']:.1f}"
            )

        if result['success']:
            self.detection_updated.emit(
                result['cx'], result['cy'], result['radius'])

    # ──────────────────────────────────────────────
    # 確認
    # ──────────────────────────────────────────────

    def _on_accepted(self):
        r = self._last_result
        self.detection_accepted.emit(r['cx'], r['cy'], r['radius'])
        self.accept()
