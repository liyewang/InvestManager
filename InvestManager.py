from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
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
        self.__menuData = self.__menu.addMenu('Data')
        self.__menu.addAction('About', QApplication.aboutQt)
        self.__tab = QTabWidget(self)
        self.__home = hom.Wid(self.__db, self.open)
        self.__home.setDataMenu(self.__menuData)
        self.__tab.addTab(self.__home, 'Home')
        self.__tab.currentChanged.connect(self.tabChange)
        self.setCentralWidget(self.__tab)
        self.show()
        return

    def tabChange(self) -> None:
        if self.__tab.currentIndex() == 0:
            wid = self.__tab.widget(1)
            assert type(wid) is ass.Wid
            grp = wid.group
            while self.__tab.count() > 1:
                self.__tab.removeTab(1)
            self.__home.refresh(grp, False)
        return

    @Slot()
    def open(self, wid: ass.Wid) -> None:
        self.__menuData.clear()
        wid.setDataMenu(self.__menuData)
        self.__tab.addTab(wid, 'Asset')
        self.__tab.setCurrentIndex(1)
        wid.show()
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
