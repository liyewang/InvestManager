from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Slot
from PySide6.QtGui import QKeyEvent
from db import *
import infTab as inf
import groTab as gro

class homWid(QWidget):
    def __init__(self, data: db) -> None:
        super().__init__()
        self.setMinimumSize(1366, 768)
        self.__inf_mod = inf.Mod(data)
        self.__gro_mod = gro.Mod(data)
        self.__tab = self.__gro_mod.table()

        layout = QHBoxLayout()
        self.setLayout(layout)

        return