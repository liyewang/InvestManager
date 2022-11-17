from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Slot
from PySide6.QtGui import QKeyEvent
from db import *
from basTab import *
import homWid as hom
import assWid as ass

class Win(QMainWindow):
    def __init__(self, data: db | None = None) -> None:
        super().__init__()
        self.setMinimumSize(1600, 900)
        if data is None:
            self.__db = db()
        else:
            self.__db = data
        self.__menu = self.menuBar()
        self.__menu.addAction('Home', self.home)
        self.__menuData = self.__menu.addMenu('Data')
        self.home()
        self.show()
        return

    def home(self) -> None:
        self.__menuData.clear()
        _home = hom.Wid(self.__db, self.open)
        _home.setDataMenu(self.__menuData)
        # _home = hom.Wid(self.__db, self.open, False)
        self.setCentralWidget(_home)
        # _home.update()
        return

    @Slot()
    def open(self, wid: ass.Wid) -> None:
        self.__menuData.clear()
        wid.setDataMenu(self.__menuData)
        self.setCentralWidget(wid)
        wid.show()
        self.__db.save()
        return

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.text() == '\u0013':
            print('Save')
            self.__db.save()
        return super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication()
    d = db(DB_PATH)
    print(d)
    w = Win(d)
    app.exec()
    d.save()
