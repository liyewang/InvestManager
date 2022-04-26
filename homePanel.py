from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Slot
from PySide6.QtGui import QKeyEvent
from detailPanel import detailPanel

class homePanel(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.__main = QWidget()
        self.setCentralWidget(self.__main)

        return