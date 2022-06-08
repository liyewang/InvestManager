from PySide6.QtWidgets import QApplication, QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QSlider, QLabel
from PySide6.QtCore import Qt, Slot, QThread
from PySide6.QtGui import QKeyEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.font_manager import FontProperties
from db import *
import infTab as inf
import groTab as gro

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
        llayout.addWidget(self.__canvas, 60)
        llayout.addWidget(self.__plot_start_title, 1)
        llayout.addLayout(self.__plot_start_layout, 1)
        llayout.addWidget(self.__plot_range_title, 1)
        llayout.addLayout(self.__plot_range_layout, 1)
        llayout.addWidget(self.__inf_mod.view, 30)

        layout = QHBoxLayout()
        layout.addLayout(llayout, 7)
        layout.addWidget(self.__gro_mod.view, 3)
        # layout.addLayout(rlayout, 3)
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

    def __plot(self) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            date = self.__date[head:tail]
            x = self.__tab.iloc[head:tail, gro.COL_HA]
            self.__ax.clear()
            self.__ax2.clear()
            self.__ax.plot(date, x, lw=0.5, ms=3)
            self.__ax.set(xlabel='Date', ylabel='Amount')
            self.__ax.set_title('Gross Assets')
            self.__ax.margins(x=0)
            if x.iat[0]:
                self.__ax2.set_ylim((self.__ax.set_ylim() / x.iat[0] - 1) * 100)
            else:
                self.__ax2.set_ylim(0, 100)
            self.__ax2.set_ylabel('Percent (%)')
        self.__ax.grid(True)
        self.__canvas.draw()
        return

    def update(self) -> None:
        self.__inf_mod.update()
        self.__gro_mod.update()
        self.__tab = self.__gro_mod.table().sort_index(ascending=False, ignore_index=True)
        self.__date = self.__tab.iloc[:, gro.COL_DT]
        self.__plot_start_update()
        self.__plot_range_update()
        self.__plot()
        return


if __name__ == '__main__':
    d = db(R'C:\Users\51730\Desktop\dat')

    app = QApplication()
    h = Wid(d)
    h.show()
    app.exec()