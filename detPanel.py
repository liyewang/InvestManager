from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Slot
from PySide6.QtGui import QKeyEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.font_manager import FontProperties
from pandas import DataFrame
from txnTab import txnTabView
from valTab import (
    valTabView,
    COL_DT as VAL_COL_DT,
    COL_UV as VAL_COL_UV,
    COL_NV as VAL_COL_NV,
    COL_TA as VAL_COL_TA,
)

class detPanel(QMainWindow):
    def __init__(self, txn: txnTabView, val: valTabView) -> None:
        super().__init__()
        self.__txn = txn
        self.__val = val

        self.__txn.view.setMinimumWidth(800)
        self.__val.view.setMinimumWidth(500)

        self.__main = QWidget()
        self.setCentralWidget(self.__main)

        self.__fig = Figure()
        self.__canvas = FigureCanvas(self.__fig)
        self.__fig.set_canvas(self.__canvas)
        self.__ax = self.__canvas.figure.subplots()
        self.__font = FontProperties(fname=R'C:\Windows\Fonts\msyh.ttc')
        self.__plot()

        llayout = QVBoxLayout()
        llayout.addWidget(self.__canvas, 6)
        llayout.addWidget(self.__txn.view, 4)

        layout = QHBoxLayout(self.__main)
        layout.addLayout(llayout, 7)
        layout.addWidget(self.__val.view, 3)

        # main_layout = QGridLayout()
        # main_layout.addWidget(self.__val.view, 1, 0)
        # main_layout.addWidget(self.__txn.view, 1, 1)
        # main_layout.setColumnStretch(1, 1)
        # main_layout.setColumnStretch(0, 0)
        # main_layout.SetMinimumSize
        # self.setLayout(main_layout)

        self.__txn.signal().connect(self.__update)
        self.__val.signal().connect(self.__txn_error)

    def __plot(self) -> None:
        tab = super(valTabView, self.__val).table()
        v = tab.iloc[:, VAL_COL_TA] > 0
        txnBA = (
            tab.iloc[:, VAL_COL_DT].loc[v].tolist(),
            tab.iloc[:, VAL_COL_NV].loc[v].tolist(),
        )
        v = tab.iloc[:, VAL_COL_TA] < 0
        txnSA = (
            tab.iloc[:, VAL_COL_DT].loc[v].tolist(),
            tab.iloc[:, VAL_COL_NV].loc[v].tolist(),
        )
        self.__ax.clear()
        self.__ax.plot(
            tab.iloc[:, VAL_COL_DT].tolist(), tab.iloc[:, VAL_COL_NV].tolist(),
            txnBA[0], txnBA[1], 'ro',
            txnSA[0], txnSA[1], 'go',
            lw=0.5,
            ms=3,
        )
        self.__ax.set(xlabel='Date', ylabel='Net Value')
        self.__ax.set_title(f'{self.__val.name()} ({self.__val.code()})', fontsize=16, fontproperties=self.__font)
        # self.__ax.margins(0)
        self.__ax.grid(True)
        self.__canvas.draw()
        return

    @Slot()
    def __update(self) -> None:
        self.__val.table(txn=super(txnTabView, self.__txn).table())
        self.__plot()
        return

    @Slot()
    def __txn_error(self, args: tuple) -> None:
        self.__txn.show_error(args)
        return

    # def keyPressEvent(self, event: QKeyEvent) -> None:
    #     print(event)
    #     return super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication()
    txn = txnTabView()
    val = valTabView()
    det = detPanel(txn, val)
    det.setMinimumSize(1280, 720)
    det.show()
    val.table(code='519697')
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    app.exec()