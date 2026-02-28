"""FFB Racing Sim — Desktop Companion App"""
import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FFB Companion")
    app.setOrganizationName("FFB_Project")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
