import os
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, QMenu,
                                QHBoxLayout, QVBoxLayout, QLabel, QTableWidget, QSlider)
from PySide6.QtCore import Qt, Slot, QThread
from PySide6.QtGui import QKeyEvent, QAction
from db import *
from basTab import *
import homWid as hom

class Win(QMainWindow):
    def __init__(self, data: db | None = None) -> None:
        super().__init__()
        self.setMinimumSize(1366, 768)
        if data is None:
            self.__db = db()
        else:
            self.__db = data
        self.__menu = self.menuBar()
        self.__menu.addAction(QAction('Home', self, triggered=self.home))
        self.setCentralWidget(hom.Wid(self.__db, self.open))
        self.show()
        return

    def home(self) -> None:
        _home = hom.Wid(self.__db, self.open)
        # _home = hom.Wid(self.__db, self.open, False)
        self.setCentralWidget(_home)
        # _home.update()
        return

    @Slot()
    def open(self, widget: QWidget) -> None:
        self.setCentralWidget(widget)
        widget.show()
        return


if __name__ == '__main__':
    app = QApplication()
    file = R'C:\Users\51730\Desktop\dat'
    d = db(file)
    print(d)
    w = Win(d)
    app.exec()
