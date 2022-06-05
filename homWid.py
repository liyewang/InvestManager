from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Slot
from PySide6.QtGui import QKeyEvent

class homWid(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QHBoxLayout()
        self.setLayout(layout)

        return