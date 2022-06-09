from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, QComboBox,
                                QHBoxLayout, QVBoxLayout, QLabel, QTableWidget, QSlider)
from PySide6.QtCore import Qt, Slot, QThread
from PySide6.QtGui import QKeyEvent, QFont
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.font_manager import FontProperties
from db import *
import txnTab as txn
import valTab as val

FONT_PATH = R'C:\Windows\Fonts\msyh.ttc'

# TAG_IA = 'Invest Amount'
# TAG_PA = 'Profit Amount'
# TAG_HA = 'Holding Amount'
# TAG_PR = 'Profit Rate'
# TAG_AR = 'Average Rate'

TAG_VL = 'Value'
TAG_MA = 'Mean Average'

PLT_TAG = [
    TAG_VL,
    TAG_MA,
]

class Wid(QWidget):
    def __init__(self, data: db, group: str, upd: bool = True) -> None:
        super().__init__()
        # self.setMinimumSize(1366, 768)
        self.__db = data
        self.__grp = group
        self.__txn_mod = txn.Mod(data, group)
        self.__val_mod = val.Mod(data, group, upd)
        self.__tab = self.__val_mod.table().sort_index(ascending=False, ignore_index=True)
        self.__date = self.__tab.iloc[:, val.COL_DT]
        self.__avg125 = self.__tab.iloc[:, val.COL_NV].rolling(window=125, min_periods=1).mean()
        self.__avg250 = self.__tab.iloc[:, val.COL_NV].rolling(window=250, min_periods=1).mean()
        self.__avg500 = self.__tab.iloc[:, val.COL_NV].rolling(window=500, min_periods=1).mean()
        self.__txn_mod.set_update(self.__update)
        self.__val_mod.set_raise(self.__txn_raise)

        self.__fig = Figure()
        self.__canvas = FigureCanvas(self.__fig)
        self.__fig.set_canvas(self.__canvas)
        self.__ax = self.__canvas.figure.subplots()
        self.__ax2 = self.__ax.twinx()
        self.__font = FontProperties(fname=FONT_PATH)

        # self.__title = QLabel()
        # self.__title.setAlignment(Qt.AlignCenter)
        # font = QFont()
        # font.setPointSize(16)
        # font.setWeight(QFont.DemiBold)
        # self.__title.setFont(font)
        self.__start_min = 0
        self.__start_max = 0
        self.__range_min = 0
        self.__range_max = 0
        self.__start = 0
        self.__range = 0
        self.__plot_start = QSlider(minimum=0, maximum=0, orientation=Qt.Horizontal)
        self.__plot_range = QSlider(minimum=0, maximum=0, orientation=Qt.Horizontal)
        self.__plot_start.valueChanged.connect(self.__plot_start_update)
        self.__plot_range.valueChanged.connect(self.__plot_range_update)
        self.__plot_start_min = QLabel()
        self.__plot_start_max = QLabel()
        self.__plot_range_min = QLabel()
        self.__plot_range_max = QLabel()
        self.__plot_start_title = QLabel()
        self.__plot_range_title = QLabel()
        self.__plot_start_update()
        self.__plot_range_update()

        self.__plot_start_layout = QHBoxLayout()
        self.__plot_start_layout.addWidget(self.__plot_start_min)
        self.__plot_start_layout.addWidget(self.__plot_start)
        self.__plot_start_layout.addWidget(self.__plot_start_max)

        self.__plot_range_layout = QHBoxLayout()
        self.__plot_range_layout.addWidget(self.__plot_range_min)
        self.__plot_range_layout.addWidget(self.__plot_range)
        self.__plot_range_layout.addWidget(self.__plot_range_max)

        llayout = QVBoxLayout()
        # llayout.addWidget(self.__title, 5)
        llayout.addWidget(self.__canvas, 60)
        llayout.addWidget(self.__plot_start_title, 1)
        llayout.addLayout(self.__plot_start_layout, 1)
        llayout.addWidget(self.__plot_range_title, 1)
        llayout.addLayout(self.__plot_range_layout, 1)
        llayout.addWidget(self.__txn_mod.view, 30)

        # self.__stat = QLabel()
        # self.__stat.setAlignment(Qt.AlignLeft)
        # self.__stat = QTableWidget()
        # self.__show_stat()
        plt_opt = QComboBox()
        plt_opt.addItems(PLT_TAG)
        plt_opt.currentTextChanged.connect(self.__plot)

        rlayout = QVBoxLayout()
        # rlayout.addWidget(self.__stat, 1)
        rlayout.addWidget(plt_opt, 1)
        rlayout.addWidget(self.__val_mod.view, 99)

        layout = QHBoxLayout()
        layout.addLayout(llayout, 7)
        layout.addLayout(rlayout, 3)
        self.setLayout(layout)
        return

    @Slot()
    def __plot_start_update(self, start: int | None = None) -> None:
        size = self.__tab.index.size
        if size:
            self.__start_min = 1
            self.__start_max = size
            if start is not None and start >= self.__start_min and start <= self.__start_max:
                self.__start = start
            elif self.__start < self.__start_min or self.__start > self.__start_max:
                self.__start = self.__start_min
            self.__range_max = size - self.__start + 1
            self.__range_min = min(self.__range_max, 5)
        else:
            self.__start_min = 0
            self.__start_max = 0
            self.__range_min = 0
            self.__range_max = 0
            self.__start = 0
            self.__range = 0
        self.__plot_start_min.setText(str(self.__start_min))
        self.__plot_start_max.setText(str(self.__start_max))
        self.__plot_range_min.setText(str(self.__range_min))
        self.__plot_range_max.setText(str(self.__range_max))
        self.__plot_start.valueChanged.disconnect(self.__plot_start_update)
        self.__plot_range.valueChanged.disconnect(self.__plot_range_update)
        self.__plot_start.setRange(self.__start_min, self.__start_max)
        self.__plot_range.setRange(self.__range_min, self.__range_max)
        if self.__range < self.__range_min or self.__range > self.__range_max:
            self.__range = self.__range_max
            self.__plot_range.setValue(self.__range_max)
        self.__plot_start.valueChanged.connect(self.__plot_start_update)
        self.__plot_range.valueChanged.connect(self.__plot_range_update)
        self.__plot_start_title.setText(f'Start: {self.__start}')
        self.__plot_range_title.setText(f'Range: {self.__range}')
        if size:
            self.__plot()
        return

    @Slot()
    def __plot_range_update(self, range: int | None = None) -> None:
        if range is not None and range >= self.__range_min and range <= self.__range_max:
            self.__range = range
            self.__plot()
        elif self.__range < self.__range_min or self.__range > self.__range_max:
            self.__range = self.__range_max
            self.__plot_range.valueChanged.disconnect(self.__plot_range_update)
            self.__plot_range.setValue(self.__range_max)
            self.__plot_range.valueChanged.connect(self.__plot_range_update)
        self.__plot_range_title.setText(f'Range: {self.__range}')
        return

    def __plot(self, opt: str = PLT_TAG[0]) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            date = self.__date[head:tail]
            nv = self.__tab.iloc[head:tail, val.COL_NV]
            v = self.__tab.iloc[head:tail, val.COL_TS] > 0
            txnBA = (
                self.__tab.iloc[head:tail, val.COL_DT][v],
                nv[v],
            )
            v = self.__tab.iloc[head:tail, val.COL_TS] < 0
            txnSA = (
                self.__tab.iloc[head:tail, val.COL_DT][v],
                nv[v],
            )
            self.__ax.clear()
            self.__ax2.clear()
            self.__ax.plot(
                date, nv,
                date, self.__avg125[head:tail],
                date, self.__avg250[head:tail],
                date, self.__avg500[head:tail],
                txnBA[0], txnBA[1], 'bo',
                txnSA[0], txnSA[1], 'ro',
                date, self.__tab.iloc[head:tail, val.COL_HP], 'm-.',
                lw=0.5,
                ms=3,
            )
            self.__ax.set(xlabel='Date', ylabel='Net Value')
            self.__ax.set_title(f'{self.__val_mod.get_name()} ({self.__val_mod.get_code()})',
                fontsize=16, fontproperties=self.__font)
            r125 = (nv.iat[-1] / self.__avg125.iat[tail - 1] - 1) * 100
            r250 = (nv.iat[-1] / self.__avg250.iat[tail - 1] - 1) * 100
            r500 = (nv.iat[-1] / self.__avg500.iat[tail - 1] - 1) * 100
            self.__ax.legend(['Net Value', f'MA125 ({r125:+.1f}%)', f'MA250 ({r250:+.1f}%)', f'MA500 ({r500:+.1f}%)',
                'Buying', 'Selling', 'Holding Price'])
            self.__ax.margins(x=0)
            self.__ax2.set_ylim((self.__ax.set_ylim() / nv.iat[0] - 1) * 100)
            self.__ax2.set_ylabel('Profit Rate (%)')
        self.__ax.grid(True)
        self.__canvas.draw()
        return

    # def __show_stat(self) -> None:
    #     d = {TAG_IA:0, TAG_PA:0, TAG_PR:0, TAG_AR:0}
    #     s  = f'{TAG_IA}\t{d[TAG_IA]:12,.2f}\n'
    #     s += f'{TAG_PA}\t{d[TAG_PA]:12,.2f}\n'
    #     s += f'{TAG_PR}\t{d[TAG_PR] * 100:11,.2f}%\n'
    #     s += f'{TAG_AR}\t{d[TAG_AR] * 100:11,.2f}%'
    #     self.__stat.setText(s)
    #     return

    @Slot()
    def __update(self, online: bool = False) -> None:
        if online:
            self.__val_mod.table(self.__grp, self.__txn_mod.table())
        else:
            self.__val_mod.table(txn_tab=self.__txn_mod.table())
        self.__tab = self.__val_mod.table().sort_index(ascending=False, ignore_index=True)
        self.__date = self.__tab.iloc[:, val.COL_DT]
        self.__avg125 = self.__tab.iloc[:, val.COL_NV].rolling(window=125, min_periods=1).mean()
        self.__avg250 = self.__tab.iloc[:, val.COL_NV].rolling(window=250, min_periods=1).mean()
        self.__avg500 = self.__tab.iloc[:, val.COL_NV].rolling(window=500, min_periods=1).mean()
        # self.__title.setText(f'{self.__val_mod.get_name()}({self.__val_mod.get_code()})')
        self.__plot_start_update()
        self.__plot_range_update()
        self.__plot()
        # self.__show_stat()
        return

    @Slot()
    def __txn_raise(self, args: tuple) -> None:
        self.__txn_mod._raise(args)
        return

    def show(self) -> None:
        super().show()
        self.__txn_mod.view.scrollToBottom()
        return

    def keyPressEvent(self, event: QKeyEvent) -> None:
        print(event)
        if event.key() == Qt.Key_F5:
            print('Update')
            self.__update(True)
        return super().keyPressEvent(event)

if __name__ == '__main__':
    d = db(R'C:\Users\51730\Desktop\dat')
    group = list(d.get(key=KEY_INF).keys())[0]

    app = QApplication()
    a = Wid(d, group)
    a.show()
    # v.table(group)
    # t.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    app.exec()