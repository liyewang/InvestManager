from PySide6.QtWidgets import (QApplication, QWidget, QComboBox, QLabel, QSlider,
                                QMenu, QFileDialog, QHBoxLayout, QVBoxLayout)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QKeyEvent
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.font_manager import FontProperties
from db import *
from dfIO import *
import txnTab as txn
import valTab as val

FONT_PATH = R'C:\Windows\Fonts\msyh.ttc'

# TAG_IA = 'Invest Amount'
# TAG_PA = 'Profit Amount'
# TAG_HA = 'Holding Amount'
# TAG_PR = 'Profit Rate'
# TAG_AR = 'Average Rate'

LST_MA = [
    183,
    365,
    730,
]

TAG_VL = 'Net Value'
DICT_MA = {f'To-MA{n} Ratio':n for n in LST_MA}

PLT_TAG = [TAG_VL] + list(DICT_MA.keys())

class Wid(QWidget):
    def __init__(self, data: db, group: str, upd: bool = True) -> None:
        super().__init__()
        self.__txn_mod = txn.Mod(data, group)
        self.__val_mod = val.Mod(data, group, upd)
        self.__grp = self.__val_mod.get_group()
        self.__calcData()
        self.__txn_mod.set_update(self.__update)
        self.__val_mod.set_raise(self.__txn_raise)

        self.__fig = Figure()
        self.__canvas = FigureCanvas(self.__fig)
        self.__fig.set_canvas(self.__canvas)
        self.__ax = self.__canvas.figure.subplots()
        self.__ax2 = self.__ax.twinx()
        self.__font = FontProperties(fname=FONT_PATH)

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

        # self.__title = QLabel()
        # self.__title.setAlignment(Qt.AlignCenter)
        # font = QFont()
        # font.setPointSize(16)
        # font.setWeight(QFont.DemiBold)
        # self.__title.setFont(font)
        # self.__title.setText(f'{self.__val_mod.get_name()}({self.__val_mod.get_code()})')

        # self.__stat = QLabel()
        # self.__stat.setAlignment(Qt.AlignLeft)
        # self.__stat = QTableWidget()
        # self.__show_stat()

        self.__plt_opt = QComboBox()
        self.__plt_opt.addItems(PLT_TAG)
        self.__plt_opt.currentTextChanged.connect(self.__plot_opt_upd)
        self.__plot_opt_cfg(self.__plt_opt.currentText())
        self.__plot()

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
        llayout.addWidget(self.__txn_mod.view, 30)

        rlayout = QVBoxLayout()
        # rlayout.addWidget(self.__title, 5)
        # rlayout.addWidget(self.__stat, 1)
        rlayout.addWidget(self.__plt_opt, 1)
        rlayout.addWidget(self.__val_mod.view, 99)

        layout = QHBoxLayout()
        layout.addLayout(llayout, 7)
        layout.addLayout(rlayout, 3)
        self.setLayout(layout)
        return

    def __calcData(self) -> None:
        self.__tab = self.__val_mod.table().sort_index(ascending=False, ignore_index=True)
        self.__date = self.__tab[val.TAG_DT]
        self.__mas = {}
        self.__mrs = {}
        for n in LST_MA:
            ma = self.__tab[val.TAG_NV].rolling(window=n, min_periods=1).mean()
            mr = (self.__tab[val.TAG_NV] / ma - 1) * 100
            self.__mas[n] = ma
            self.__mrs[n] = mr
        return

    @Slot()
    def __plot_opt_upd(self, opt: str = TAG_VL) -> None:
        self.__plot_opt_cfg(opt)
        self.__plot()
        return

    def __plot_opt_cfg(self, opt: str) -> None:
        if opt == TAG_VL:
            self.__plot_size = self.__tab.index.size
            self.__range_min_opt = 20
            self.__ax2.set_axis_on()
            self.__plot = self.__plot_vl
        elif opt in DICT_MA:
            self.__plot_size = self.__tab.index.size
            self.__range_min_opt = 20
            self.__ax2.set_axis_off()
            self.__plot = self.__plot_mr
            self.__n = DICT_MA[opt]
        # self.__plot_title = opt
        self.__plot_title = f'{self.__val_mod.get_name()} ({self.__val_mod.get_code()})'
        self.__plot_start_cfg(self.__plot_start.value())
        self.__plot_range_cfg(self.__plot_range.value())
        return

    @Slot()
    def __plot_start_upd(self, start: int | None = None) -> None:
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

    def __plot_vl(self) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            date = self.__date[head:tail]
            nv = self.__tab.iloc[head:tail, val.COL_NV]
            ts = self.__tab.iloc[head:tail, val.COL_TS]
            dt = self.__tab.iloc[head:tail, val.COL_DT]
            v = ts > 0
            txnBA = (dt[v], nv[v])
            v = ts < 0
            txnSA = (dt[v], nv[v])
            self.__ax.clear()
            self.__ax2.clear()
            self.__ax.plot(
                date, nv,
                date, DataFrame(self.__mas)[head:tail],
                txnBA[0], txnBA[1], 'bo',
                txnSA[0], txnSA[1], 'ro',
                date, self.__tab.iloc[head:tail, val.COL_HP], 'm-.',
                lw=0.5,
                ms=3,
            )
            self.__ax.set(xlabel='Date', ylabel='Value')
            self.__ax.set_title(self.__plot_title, fontsize=16, fontproperties=self.__font)
            tags = ['Net Value']
            for n, ma in self.__mas.items():
                assert type(ma) is Series
                rate = (nv.iat[-1] / ma.iat[tail - 1] - 1) * 100
                tags += [f'MA{n} ({rate:+.1f}%)']
            tags += ['Buying', 'Selling', 'Holding Price']
            self.__ax.legend(tags)
            self.__ax.margins(x=0)
            self.__ax2.set_ylim((self.__ax.set_ylim() / nv.iat[0] - 1) * 100)
            self.__ax2.set_ylabel('Profit Rate (%)')
        self.__ax.grid(True)
        self.__canvas.draw()
        return

    def __plot_mr(self) -> None:
        head = self.__start - 1
        tail = head + self.__range
        if tail <= self.__tab.index.size and head >= 0 and tail - head > 0:
            date = self.__date[head:tail]
            assert self.__n in LST_MA, f'Unsupported MA option [{self.__n}].'
            mr = self.__mrs[self.__n][head:tail]
            assert type(mr) is Series
            mr_pos = sum(mr > mr.iat[-1]) / mr.size
            if mr_pos > 0.5:
                mr_pos = -mr_pos * 100
            else:
                mr_pos = (1 - mr_pos) * 100
            mr_avg = mr.mean()
            ts = self.__tab.iloc[head:tail, val.COL_TS]
            dt = self.__tab.iloc[head:tail, val.COL_DT]
            v = ts > 0
            txnBA = (dt[v], mr[v])
            v = ts < 0
            txnSA = (dt[v], mr[v])
            self.__ax.clear()
            self.__ax.plot(
                date, mr,
                date, Series(mr_avg, date.index), 'm-.',
                txnBA[0], txnBA[1], 'bo',
                txnSA[0], txnSA[1], 'ro',
                lw=0.5,
                ms=3,
            )
            self.__ax.set(xlabel='Date', ylabel='Ratio (%)')
            self.__ax.set_title(self.__plot_title, fontsize=16, fontproperties=self.__font)
            self.__ax.legend([f'To-MA{self.__n} ({mr_pos:+.2f}%)', f'Average ({mr_avg:+.2f}%)', 'Buying', 'Selling'])
            self.__ax.margins(x=0)
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
            self.__grp = self.__val_mod.get_group()
        else:
            self.__val_mod.table(txn_tab=self.__txn_mod.table())
        self.__calcData()
        self.__plot_opt_upd(self.__plt_opt.currentText())
        # self.__title.setText(f'{self.__val_mod.get_name()}({self.__val_mod.get_code()})')
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

    def import_txn(self) -> None:
        file = QFileDialog.getOpenFileName(self, None, '.', FLTR_DFIO_ALL)[0]
        if file:
            self.__txn_mod.import_table(file)
        return

    def export_txn(self) -> None:
        code = self.__val_mod.get_code()
        file = QFileDialog.getSaveFileName(self, None, f'./txn_{code}', FLTR_DFIO)[0]
        if file:
            self.__txn_mod.export_table(file, True)
        return

    def template_txn(self) -> None:
        file = QFileDialog.getSaveFileName(self, None, './txn_template', FLTR_DFIO)[0]
        if file:
            self.__txn_mod.export_table(file, False)
        return

    def import_val(self) -> None:
        file = QFileDialog.getOpenFileName(self, None, '.', FLTR_DFIO_ALL)[0]
        if file:
            self.__val_mod.import_table(file)
        return

    def export_val(self) -> None:
        code = self.__val_mod.get_code()
        file = QFileDialog.getSaveFileName(self, None, f'./val_{code}', FLTR_DFIO)[0]
        if file:
            self.__val_mod.export_table(file, True)
        return

    def template_val(self) -> None:
        file = QFileDialog.getSaveFileName(self, None, './val_template', FLTR_DFIO)[0]
        if file:
            self.__val_mod.export_table(file, False)
        return

    def setDataMenu(self, menu: QMenu) -> None:
        menu_imp = menu.addMenu('Import')
        menu_imp.addAction('Transaction', self.import_txn)
        menu_imp.addAction('Net Value', self.import_val)
        menu_exp = menu.addMenu('Export')
        menu_exp.addAction('Transaction', self.export_txn)
        menu_exp.addAction('Net Value', self.export_val)
        menu_tmp = menu.addMenu('Template')
        menu_tmp.addAction('Transaction', self.template_txn)
        menu_tmp.addAction('Net Value', self.template_val)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        print(event)
        if event.key() == Qt.Key_F5:
            print('Update')
            self.__update(True)
        return super().keyPressEvent(event)

    @property
    def group(self) -> str:
        return self.__grp

if __name__ == '__main__':
    d = db(DB_PATH)
    group = list(d.get(key=KEY_INF).keys())[0]

    app = QApplication()
    a = Wid(d, group)
    a.show()
    app.exec()