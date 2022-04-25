from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QTableWidget
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeyEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.font_manager import FontProperties
import pandas as pd
from txnTab import (
    txnTabView,
    COL_BA as TXN_COL_BA,
    COL_SA as TXN_COL_SA,
    COL_HS as TXN_COL_HS,
)
from valTab import (
    valTabView,
    COL_DT as VAL_COL_DT,
    COL_UV as VAL_COL_UV,
    COL_NV as VAL_COL_NV,
    COL_HA as VAL_COL_HA,
    COL_TA as VAL_COL_TA,
)

FONT_PATH = R'C:\Windows\Fonts\msyh.ttc'

TAG_IA = 'Invest Amount'
TAG_PA = 'Profit Amount'
TAG_HA = 'Holding Amount'
TAG_PR = 'Profit Rate'
TAG_AR = 'Average Rate'

class detPanel(QMainWindow):
    def __init__(self, txn: txnTabView, val: valTabView) -> None:
        super().__init__()
        self.setMinimumSize(1280, 720)
        self.__txn = txn
        self.__val = val

        self.__fig = Figure()
        self.__canvas = FigureCanvas(self.__fig)
        self.__fig.set_canvas(self.__canvas)
        self.__ax = self.__canvas.figure.subplots()
        self.__font = FontProperties(fname=FONT_PATH)
        self.__plot()

        llayout = QVBoxLayout()
        llayout.addWidget(self.__canvas, 7)
        llayout.addWidget(self.__txn.view, 3)

        self.__stat = QLabel()
        self.__stat.setAlignment(Qt.AlignLeft)
        # self.__stat = QTableWidget()
        self.__show_stat()

        rlayout = QVBoxLayout()
        rlayout.addWidget(self.__stat, 1)
        rlayout.addWidget(self.__val.view, 9)

        self.__main = QWidget()
        self.setCentralWidget(self.__main)
        layout = QHBoxLayout(self.__main)
        layout.addLayout(llayout, 7)
        layout.addLayout(rlayout, 3)
        # layout.addWidget(self.__val.view, 3)

        self.__txn.get_signal().connect(self.__update)
        self.__val.get_signal().connect(self.__txn_error)
        return

    def __plot(self) -> None:
        tab = super(valTabView, self.__val).table().sort_index(ascending=False, ignore_index=True)
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
            tab.iloc[:, VAL_COL_DT].tolist(), tab.iloc[:, VAL_COL_NV].rolling(window=180, min_periods=1).mean().tolist(),
            tab.iloc[:, VAL_COL_DT].tolist(), tab.iloc[:, VAL_COL_NV].rolling(window=360, min_periods=1).mean().tolist(),
            txnBA[0], txnBA[1], 'ro',
            txnSA[0], txnSA[1], 'go',
            lw=0.5,
            ms=3,
        )
        self.__ax.set(xlabel='Date', ylabel='Net Value')
        self.__ax.set_title(f'{self.__val.get_name()} ({self.__val.get_code()})',
            fontsize=16, fontproperties=self.__font)
        self.__ax.legend(['Net Value','180 Avg,','360 Avg.','Buying','Selling'])
        self.__ax.set_ylim([0, 8])
        # self.__ax.margins(x=0.05, y=0.05)
        self.__ax.grid(True)
        self.__canvas.draw()
        return

    def get_stat(self) -> dict:
        txn = super(txnTabView, self.__txn).table()
        val = self.__val.table()
        stat = {TAG_IA:float('nan'), TAG_PA:float('nan'), TAG_HA:float('nan'),
                TAG_PR:float('nan'), TAG_AR:float('nan')}
        if txn.index.size:
            stat[TAG_IA] = txn.iloc[:, TXN_COL_BA].sum()
            if val.index.size:
                stat[TAG_PA] = txn.iloc[:, TXN_COL_SA].sum() + val.iat[0, VAL_COL_HA] - stat[TAG_IA]
                stat[TAG_HA] = val.iat[0, VAL_COL_HA]
                stat[TAG_PR] = stat[TAG_PA] / stat[TAG_IA]
                if txn.iat[-1, TXN_COL_HS]:
                    stat[TAG_AR] = self.__txn.avgRate(
                        pd.concat([txn, pd.DataFrame([[
                            val.iat[0, VAL_COL_DT],
                            float('nan'),
                            float('nan'),
                            val.iat[0, VAL_COL_HA],
                            txn.iat[-1, TXN_COL_HS],
                            float('nan'),
                            float('nan'),
                        ]], columns=txn.columns)], ignore_index=True)
                    )
                else:
                    stat[TAG_AR] = self.__txn.avgRate()
        return stat

    def __show_stat(self) -> None:
        d = self.get_stat()
        s  = f'{TAG_IA}\t{d[TAG_IA]:10.2f}\n'
        s += f'{TAG_PA}\t{d[TAG_PA]:10.2f}\n'
        s += f'{TAG_PR}\t{d[TAG_PR] * 100:9.2f}%\n'
        s += f'{TAG_AR}\t{d[TAG_AR] * 100:9.2f}%'
        self.__stat.setText(s)
        return

    @Slot()
    def __update(self) -> None:
        self.__val.table(txn=super(txnTabView, self.__txn).table())
        self.__plot()
        self.__show_stat()
        return

    @Slot()
    def __txn_error(self, args: tuple) -> None:
        self.__txn.raise_error(args)
        return

    # def keyPressEvent(self, event: QKeyEvent) -> None:
    #     print(event)
    #     return super().keyPressEvent(event)

if __name__ == '__main__':
    app = QApplication()
    txn = txnTabView()
    val = valTabView()
    det = detPanel(txn, val)
    det.show()
    val.table(code='519697')
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    app.exec()