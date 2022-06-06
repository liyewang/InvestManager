import os
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout,
                                QHBoxLayout, QVBoxLayout, QLabel, QTableWidget, QSlider)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeyEvent
from db import *
from basTab import *
import infTab as inf

class Win(QMainWindow):
    def __init__(self, data: db | None = None) -> None:
        super().__init__()
        if data is None:
            self.__db = db()
        else:
            self.__db = data
        home = inf.Mod(self.__db)
        home.get_signal().connect(self.open)
        self.setCentralWidget(home.view)
        self.show()
        return

    @Slot()
    def open(self, Widget: QWidget) -> None:
        self.setCentralWidget(Widget)
        return


if __name__ == '__main__':
    app = QApplication()
    file = R'C:\Users\51730\Desktop\dat'
    d = db(file)
    print(d)
    w = Win(d)
    app.exec()
