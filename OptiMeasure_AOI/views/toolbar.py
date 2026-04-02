"""
toolbar.py
工具列（View 層）

包含：
- 模式切換按鈕群組（互斥）
- 線條顏色選擇
- 線寬選擇（SpinBox 1~5）
- 影像增強按鈕
- 放大鏡按鈕
"""
from PySide6.QtWidgets import (QToolBar, QLabel, QSpinBox, QWidget,
                                QHBoxLayout, QColorDialog)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import (QColor, QIcon, QPixmap, QPainter,
                            QActionGroup, QAction)

from views.image_view import ViewMode


class ToolBar(QToolBar):
    # ── 信號 ──
    mode_changed = Signal(ViewMode)
    color_changed = Signal(QColor)
    line_width_changed = Signal(int)
    enhancement_clicked = Signal()
    magnifier_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__("工具列", parent)
        self.setMovable(False)

        self._current_color = QColor(0, 255, 0)

        self._build_mode_buttons()
        self.addSeparator()
        self._build_style_controls()
        self.addSeparator()
        self._build_tool_buttons()

    # ──────────────────────────────────────────────
    # 模式按鈕群組
    # ──────────────────────────────────────────────

    def _build_mode_buttons(self):
        """建立互斥的繪圖模式按鈕"""
        self._action_group = QActionGroup(self)
        self._action_group.setExclusive(True)

        modes = [
            ("選取/平移", "Select", ViewMode.SELECT_PAN, True),
            ("圓形", "Circle", ViewMode.DRAW_CIRCLE, False),
            ("正交矩形", "Rect1", ViewMode.DRAW_RECT1, False),
            ("旋轉矩形", "Rect2", ViewMode.DRAW_RECT2, False),
            ("直線", "Line", ViewMode.DRAW_LINE, False),
        ]

        for label, name, mode, is_default in modes:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(is_default)
            action.setData(mode)
            self._action_group.addAction(action)
            self.addAction(action)

        self._action_group.triggered.connect(self._on_mode_action_triggered)

    def _on_mode_action_triggered(self, action: QAction):
        self.mode_changed.emit(action.data())

    # ──────────────────────────────────────────────
    # 外觀控制（顏色 + 線寬）
    # ──────────────────────────────────────────────

    def _build_style_controls(self):
        """顏色選擇按鈕與線寬 SpinBox"""
        # 顏色按鈕（顯示目前顏色的色塊）
        self._color_action = QAction("線色", self)
        self._color_action.setToolTip("選擇圖形線條顏色")
        self._update_color_icon()
        self._color_action.triggered.connect(self._on_pick_color)
        self.addAction(self._color_action)

        # 線寬 SpinBox
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        layout.addWidget(QLabel("線寬:"))
        self._line_width_spin = QSpinBox()
        self._line_width_spin.setRange(1, 5)
        self._line_width_spin.setValue(2)
        self._line_width_spin.setFixedWidth(50)
        self._line_width_spin.valueChanged.connect(self.line_width_changed)
        layout.addWidget(self._line_width_spin)
        self.addWidget(container)

    def _on_pick_color(self):
        """開啟顏色選擇對話框"""
        color = QColorDialog.getColor(self._current_color, self, "選擇線條顏色")
        if color.isValid():
            self._current_color = color
            self._update_color_icon()
            self.color_changed.emit(color)

    def _update_color_icon(self):
        """更新顏色按鈕的色塊圖示"""
        pixmap = QPixmap(24, 24)
        pixmap.fill(self._current_color)
        self._color_action.setIcon(QIcon(pixmap))

    # ──────────────────────────────────────────────
    # 工具按鈕
    # ──────────────────────────────────────────────

    def _build_tool_buttons(self):
        enhancement_action = QAction("影像增強", self)
        enhancement_action.triggered.connect(self.enhancement_clicked)
        self.addAction(enhancement_action)

        magnifier_action = QAction("放大鏡", self)
        magnifier_action.triggered.connect(self.magnifier_clicked)
        self.addAction(magnifier_action)
