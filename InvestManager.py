from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtCore import Slot
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
