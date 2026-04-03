"""
main.py
Measure_Img — 程式入口

執行方式：
    cd Measure_Img
    python main.py
"""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from controllers.main_controller import MainController


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Measure_Img")
    app.setStyle("Fusion")  # 跨平台一致外觀

    # Controller 負責建立並顯示主視窗
    controller = MainController()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
