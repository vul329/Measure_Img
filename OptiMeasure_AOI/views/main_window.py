"""
main_window.py
主視窗（View 層）

QMainWindow 佈局：
- 工具列（ToolBar）在上方
- 左右分割（QSplitter）：左側 ImageView / 右側 RightPanel
- 狀態列（StatusBarWidget）在下方
"""
from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

from views.image_view import ImageView
from views.right_panel import RightPanel
from views.toolbar import ToolBar
from views.status_bar import StatusBarWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Measure_Img")
        self.setMinimumSize(1024, 680)
        self.resize(1400, 900)

        # ── 建立元件 ──
        self.toolbar = ToolBar(self)
        self.image_view = ImageView(self)
        self.right_panel = RightPanel(self)
        self.status_bar = StatusBarWidget(self)

        # ── 工具列 ──
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # ── 中央區域：左右分割 ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.image_view)
        splitter.addWidget(self.right_panel)
        # 左側佔 70%，右側佔 30%
        splitter.setSizes([700, 300])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        # ── 狀態列 ──
        self.setStatusBar(self.status_bar)
