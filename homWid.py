from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QSlider,
                                QLabel, QComboBox, QLineEdit, QPushButton, QGridLayout)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeyEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from db import *
import infTab as inf
import groTab as gro

TAG_GV = 'Gross Value'
TAG_AP = gro.TAG_AP
TAG_AR = 'Annual Rate'
TAG_QR = 'Quart. Rate'

PLT_TAG = [
    TAG_GV,
    TAG_AP,
    TAG_AR,
    TAG_QR,
]

class Wid(QWidget):
    def __init__(self, data: db, open_func = None, upd: bool = True) -> None:
        super().__init__()
        # self.setMinimumSize(1366, 768)
        self.__inf_mod = inf.Mod(data, upd)
        self.__gro_mod = gro.Mod(data, upd)
        if open_func is not None:
            self.__inf_mod.set_open(open_func)
        self.__tab = self.__gro_mod.table().sort_index(ascending=False, ignore_index=True)
        self.__date = self.__tab.iloc[:, gro.COL_DT]

        self.__fig = Figure()
        self.__canvas = FigureCanvas(self.__fig)
        self.__fig.set_canvas(self.__canvas)
        self.__ax = self.__canvas.figure.subplots()
        self.__ax2 = self.__ax.twinx()

        self.__start_min = 0
        self.__start_max = 0
        self.__range_min = 0
        self.__range_max = 0
        self.__start = 0
        self.__range = 0
        self.__plot_start = QSlider(minimum=0, maximum=0, orientation=Qt.Horizontal)
        self.__plot_range = QSlider(minimum=0, maximum=0, orientation=Qt.Horizontal)
        self.__plot_start.valueChanged.connect(self.__plot_start_upd)
        self.__plot_range.valueChanged.connect(self.__plot_range_upd)
        self.__plot_start_min = QLabel()
        self.__plot_start_max = QLabel()
        self.__plot_range_min = QLabel()
        self.__plot_range_max = QLabel()
        self.__plot_start_title = QLabel()
        self.__plot_range_title = QLabel()

        self.__plt_opt = QComboBox()
        self.__plt_opt.addItems(PLT_TAG)
        self.__plt_opt.currentTextChanged.connect(self.__plot_opt_upd)
        self.__plot_opt_cfg(self.__plt_opt.currentText())
        self.__plot()

        plot_start_layout = QHBoxLayout()
        plot_start_layout.addWidget(self.__plot_start_min)
        plot_start_layout.addWidget(self.__plot_start)
        plot_start_layout.addWidget(self.__plot_start_max)

        plot_range_layout = QHBoxLayout()
        plot_range_layout.addWidget(self.__plot_range_min)
        plot_range_layout.addWidget(self.__plot_range)
        plot_range_layout.addWidget(self.__plot_range_max)

        self.__assetType = QComboBox()
        self.__assetType.addItems(ASSET_GRP)
        self.__assetCode = QLineEdit()
        self.__assetCode.setPlaceholderText(inf.TAG_AC)
        self.__assetCode.returnPressed.connect(self.__assAdd)
        assetAdd = QPushButton()
        assetAdd.setText('Add')
        assetAdd.clicked.connect(self.__assAdd)
        assetDel = QPushButton()
        assetDel.setText('Delete')
        assetDel.clicked.connect(self.__assDel)
        assetUpd = QPushButton()
        assetUpd.setText('Update')
        assetUpd.clicked.connect(self.__assUpd)
        assetOpen = QPushButton()
        assetOpen.setText('Open')
        assetOpen.clicked.connect(self.__assOpen)

        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(self.__assetType, 15)
        ctrl_layout.addWidget(self.__assetCode, 20)
        ctrl_layout.addWidget(assetAdd, 15)
        ctrl_layout.addSpacing(200)
        ctrl_layout.addWidget(assetDel, 15)
        ctrl_layout.addWidget(assetUpd, 15)
        ctrl_layout.addWidget(assetOpen, 15)

        llayout = QVBoxLayout()
        llayout.addWidget(self.__canvas, 55)
        llayout.addWidget(self.__plot_start_title, 1)
        llayout.addLayout(plot_start_layout, 1)
        llayout.addWidget(self.__plot_range_title, 1)
        llayout.addLayout(plot_range_layout, 1)
        llayout.addWidget(self.__inf_mod.view, 40)
        llayout.addLayout(ctrl_layout, 1)

        rlayout = QVBoxLayout()
        rlayout.addWidget(self.__plt_opt, 1)
        rlayout.addWidget(self.__gro_mod.view, 99)

        layout = QHBoxLayout()
        layout.addLayout(llayout, 7)
        layout.addLayout(rlayout, 3)
        self.setLayout(layout)
        return

    @Slot()
    def __plot_opt_upd(self, opt: str = TAG_GV) -> None:
        self.__plot_opt_cfg(opt)
        self.__plot()
        return

    def __plot_opt_cfg(self, opt: str) -> None:
        if opt == TAG_GV:
            self.__plot_size = self.__tab.index.size
            self.__range_min_opt = 20
            self.__ax2.set_axis_on()
            self.__plot = self.__plot_gv
        elif opt == TAG_AP:
            self.__plot_size = self.__tab.index.size
            self.__range_min_opt = 20
            self.__ax2.set_axis_on()
            self.__plot = self.__plot_ap
        elif opt == TAG_AR:
            self.__plot_size = self.__gro_mod.yrRate.index.size
            self.__range_min_opt = 5
            self.__ax2.set_axis_off()
            self.__plot = self.__plot_ar
        elif opt == TAG_QR:
            self.__plot_size = self.__gro_mod.qtRate.index.size
            self.__range_min_opt = 4
            self.__ax2.set_axis_off()
            self.__plot = self.__plot_qt
        self.__plot_title = opt
        self.__plot_start_cfg(self.__plot_start.value())
        self.__plot_range_cfg(self.__plot_range.value())
        return

    @Slot()
    def __plot_start_upd(self, start: int = 0) -> None:
        self.__plot_start_cfg(start)
        self.__plot()
        return

    def __plot_start_cfg(self, start: int = 0) -> None:
        if self.__plot_size:
            self.__start_min = 1
            self.__start_max = max(self.__start_min, self.__plot_size - self.__range_min_opt + 1)
            if start >= self.__start_min and start <= self.__start_max:
                self.__start = start
            elif self.__start < self.__start_min or self.__start > self.__start_max:
                self.__start = self.__start_min
            self.__range_max = self.__plot_size - self.__start + 1
            self.__range_min = min(self.__range_max, self.__range_min_opt)
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
        self.__plot_start.valueChanged.disconnect(self.__plot_start_upd)
        self.__plot_range.valueChanged.disconnect(self.__plot_range_upd)
        self.__plot_start.setRange(self.__start_min, self.__start_max)
        self.__plot_range.setRange(self.__range_min, self.__range_max)
        if self.__range < self.__range_min or self.__range > self.__range_max:
            self.__range = self.__range_max
            self.__plot_range.setValue(self.__range_max)
        self.__plot_start.valueChanged.connect(self.__plot_start_upd)
        self.__plot_range.valueChanged.connect(self.__plot_range_upd)
        self.__plot_start_title.setText(f'Start: {self.__start}')
        self.__plot_range_title.setText(f'Range: {self.__range}')
        return

    @Slot()
    def __plot_range_upd(self, range: int = 0) -> None:
        self.__plot_range_cfg(range)
        self.__plot()
        return

    def __plot_range_cfg(self, range: int = 0) -> None:
        if range >= self.__range_min and range <= self.__range_max:
            self.__range = range
        elif self.__range < self.__range_min or self.__range > self.__range_max:
            self.__range = self.__range_max
            self.__plot_range.valueChanged.disconnect(self.__plot_range_upd)
            self.__plot_range.setValue(self.__range_max)
            self.__plot_range.valueChanged.connect(self.__plot_range_upd)
        self.__plot_range_title.setText(f'Range: {self.__range}')
        return

    def __plot_gv(self) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            self.__ax.clear()
            date = self.__date[head:tail]
            ha = self.__tab.iloc[head:tail, gro.COL_HA]
            ia = self.__tab.iloc[head:tail, gro.COL_IA]
            self.__ax.plot(
                date, ha,
                date, ia, 'm-.',
                lw=0.5, ms=3)
            self.__ax.legend([gro.TAG_HA, gro.TAG_IA])
            self.__ax.set(xlabel='Date', ylabel='Amount')
            self.__ax.margins(x=0)
            if ha.iat[0]:
                self.__ax2.set_ylim((self.__ax.set_ylim() / ha.iat[0] - 1) * 100)
            else:
                self.__ax2.set_ylim(0, 100)
            self.__ax2.set_ylabel('Percent (%)')
            self.__ax.set_title(self.__plot_title)
        self.__ax.grid(True)
        self.__canvas.draw()
        return

    def __plot_ap(self) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            self.__ax.clear()
            date = self.__date[head:tail]
            ap = self.__tab.iloc[head:tail, gro.COL_AP]
            self.__ax.plot(date, ap, lw=0.5, ms=3)
            self.__ax.set(xlabel='Date', ylabel='Amount')
            self.__ax.margins(x=0)
            self.__ax.set_title(self.__plot_title)
        self.__ax.grid(True)
        self.__canvas.draw()
        return

    def __plot_ar(self) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            self.__ax.clear()
            ar = self.__gro_mod.yrRate.iloc[head:tail].fillna(0.)
            yr = [f'{ts.year}' for ts in ar.index]
            bc = self.__ax.bar(yr, ar, width=0.5)
            self.__ax.margins(y=0.1)
            self.__ax.bar_label(bc, fmt='%.2f%%', padding=1)
            self.__ax.set_title(self.__plot_title)
            self.__ax.set(xlabel='Year', ylabel='Rate (%)')
        self.__ax.grid(False)
        self.__canvas.draw()
        return

    def __plot_qt(self) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            self.__ax.clear()
            ar = self.__gro_mod.qtRate.iloc[head:tail].fillna(0.)
            qt = [f'{ts.year}-{ts.quarter}' for ts in ar.index]
            bc = self.__ax.bar(qt, ar, width=0.5)
            self.__ax.margins(y=0.1)
            self.__ax.bar_label(bc, fmt='%.2f%%', padding=1)
            self.__ax.set(xlabel='Quarter', ylabel='Rate (%)')
            self.__ax.set_title(self.__plot_title)
        self.__ax.grid(False)
        self.__canvas.draw()
        return

    def __plot_upd(self) -> None:
        self.__tab = self.__gro_mod.table().sort_index(ascending=False, ignore_index=True)
        self.__date = self.__tab.iloc[:, gro.COL_DT]
        self.__plot_opt_upd(self.__plt_opt.currentText())
        return

    @Slot()
    def __assAdd(self) -> None:
        print('Add')
        print(self.__assetType.currentText())
        print(self.__assetCode.text())
        self.__inf_mod.add(self.__assetType.currentText(), self.__assetCode.text())
        self.__assetCode.clear()
        return

    @Slot()
    def __assDel(self) -> None:
        print('Delete')
        print(self.__inf_mod.view.currentIndex().row())
        self.__inf_mod.delete(self.__inf_mod.view.currentIndex().row())
        self.__plot_upd()
        return

    @Slot()
    def __assUpd(self) -> None:
        print('Update')
        self.__inf_mod.update()
        self.__gro_mod.update()
        self.__plot_upd()
        return

    @Slot()
    def __assOpen(self) -> None:
        print('Open')
        print(self.__inf_mod.view.currentIndex().row())
        self.__inf_mod.open(self.__inf_mod.view.currentIndex().row())
        return

    def keyPressEvent(self, event: QKeyEvent) -> None:
        print(event)
        if event.key() == Qt.Key_Return:
            self.__assOpen()
        elif event.key() == Qt.Key_F5:
            self.__assUpd()
        elif event.key() == Qt.Key_Delete:
            self.__assDel()
        return super().keyPressEvent(event)

if __name__ == '__main__':
    d = db(DB_PATH)

    app = QApplication()
    h = Wid(d)
    h.show()
    app.exec()