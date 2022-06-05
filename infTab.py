from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QContextMenuEvent, QMouseEvent, QAction
import pandas as pd
import sys
from db import *
from basTab import *
import detailPanel as det
import txnTab as txn
import valTab as val

TAG_AT = 'Asset Type'
TAG_AC = 'Asset Code'
TAG_AN = 'Asset Name'
TAG_IA = 'Invest Amount'
TAG_HA = 'Holding Amount'
TAG_CR = 'Current Rate'
TAG_AP = 'Accum. Profit'
TAG_AR = 'Average Rate'

COL_AT = 0
COL_AC = 1
COL_AN = 2
COL_IA = 3
COL_HA = 4
COL_CR = 5
COL_AP = 6
COL_AR = 7

COL_TAG = [
    TAG_AT,
    TAG_AC,
    TAG_AN,
    TAG_IA,
    TAG_HA,
    TAG_CR,
    TAG_AP,
    TAG_AR,
]

COL_TYP = {
    TAG_AT:'str',
    TAG_AC:'str',
    TAG_AN:'str',
    TAG_IA:'float64',
    TAG_HA:'float64',
    TAG_CR:'float64',
    TAG_AP:'float64',
    TAG_AR:'float64',
}

FORE_GOOD = 0x00bf00
BACK_GOOD = 0xdfffdf
COLOR_GOOD = (FORE_GOOD, BACK_GOOD)

class Tab:
    def __init__(self, data: db | None = None) -> None:
        self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        if data is None:
            self.__db = db()
        else:
            self.load(data)
        return

    def __repr__(self) -> str:
        return self.__tab.to_string()

    def __verify(self, data: pd.DataFrame) -> None:
        if type(data) is not pd.DataFrame:
            raise TypeError(f'Unsupported data type [{type(data)}].')
        rects = set()
        sz = min(data.columns.size, len(COL_TAG))
        v = pd.Series(data.columns[:sz] != COL_TAG[:sz])
        if v.any():
            for i in v.loc[v].index:
                rects.add((i, -1, 1, 1))
            if sz < data.columns.size:
                rects.add((sz, -1, data.columns.size - sz, 1))
            raise ValueError('Column title error.', rects)
        elif sz < data.columns.size:
            raise ValueError('Column title error.', {(sz, -1, data.columns.size - sz, 1)})
        elif sz < len(COL_TAG):
            raise ValueError('Column title error.', {(0, -1, data.columns.size, 1)})
        if data.empty:
            return
        rows = data.index.size
        v = pd.Series(data.index != range(rows))
        if v.any():
            raise ValueError('Index error.', {(-1, v.loc[v].index[0], 1, 1)})

        for col in range(COL_IA, len(COL_TAG)):
            if data.dtypes[col] != 'float64':
                for row in range(rows):
                    if type(data.iat[row, col]) is not float:
                        rects.add((col, row, 1, 1))
                if rects:
                    raise ValueError('Numeric type is required.', rects)
                else:
                    raise ValueError('Numeric type is required.', {(col, 0, 1, rows)})

        for row in range(rows):
            for col in (COL_AT, COL_AC, COL_AN):
                if type(data.iat[row, col]) is not str:
                    rects.add((col, row, 1, 1))
            if rects:
                raise TypeError('String type is required.', rects)
            if data.iat[row, COL_AT] not in ASSET_GRP:
                raise ValueError('Unsupported asset type.', {(COL_AT, row, 1, 1)})
            if not data.iat[row, COL_AC]:
                raise ValueError('Empty asset code.', {(COL_AC, row, 1, 1)})

        v = data.duplicated([TAG_AT, TAG_AC])
        if v.any():
            for row in v.loc[v].index:
                rects.add((0, row, data.columns.size, 1))
            raise ValueError('No duplicated asset is allowed.', rects)
        return

    def __calc(self, group: str, txn_tab: pd.DataFrame | None = None, val_tab: pd.DataFrame | None = None) -> pd.Series:
        typ, code, name = group_info(group)
        if typ not in ASSET_GRP:
            raise ValueError(f'Unsupported asset type [{typ}].')
        s = pd.Series([typ, code, name, 0., 0., NAN, 0., NAN], COL_TAG)
        if not (txn_tab is None or val_tab is None or txn_tab.empty):
            s.iat[COL_IA] = val_tab.iat[0, val.COL_HS] * val_tab.iat[0, val.COL_UP]
            if pd.isna(s.iat[COL_IA]):
                s.iat[COL_IA] = 0.
            s.iat[COL_HA] = val_tab.iat[0, val.COL_HA]
            s.iat[COL_AP] = val_tab.iat[0, val.COL_HA] + txn_tab.iloc[:, txn.COL_SA].sum() - txn_tab.iloc[:, txn.COL_BA].sum()
            if txn_tab.iat[-1, txn.COL_HS]:
                t = txn.Tab(pd.concat([txn_tab, pd.DataFrame([[
                    val_tab.iat[0, val.COL_DT], val_tab.iat[0, val.COL_HA], txn_tab.iat[-1, txn.COL_HS]
                ]], columns=[txn.TAG_DT, txn.TAG_SA, txn.TAG_SS])], ignore_index=True))
                s.iat[COL_CR] = t.table().iat[-1, txn.COL_RR]
                s.iat[COL_AR] = t.avgRate()
            else:
                s.iat[COL_CR] = NAN
                s.iat[COL_AR] = txn.Tab(txn_tab).avgRate()
        return s

    def _update(self, idx: int | None = None, online: bool = True, save: bool = True) -> None:
        if idx is None:
            _range = range(self.__tab.index.size)
        else:
            _range = (idx,)
        self.__verify(self.__tab)
        for row in _range:
            group = group_make(self.__tab.iat[row, COL_AT], self.__tab.iat[row, COL_AC], self.__tab.iat[row, COL_AN])
            g = self.__db.get(group)
            if g:
                txn_tab = g.get(KEY_TXN, None)
                if online:
                    v = val.Tab(group, txn_tab)
                    val_tab = v.table()
                    _group = group_make(self.__tab.iat[row, COL_AT], self.__tab.iat[row, COL_AC], v.get_name())
                    if group != _group:
                        self.__db.move(group, _group)
                        group = _group
                else:
                    val_tab = val.Tab(g.get(KEY_VAL, None), txn_tab).table()
                self.__tab.iloc[row, :] = self.__calc(group, txn_tab, val_tab)
                self.__db.set(group, KEY_INF, pd.DataFrame([self.__tab.iloc[row, COL_IA:]], [0]))
            else:
                if online:
                    self.__tab.iat[row, COL_AN] = val.Tab(group).get_name()
                    group = group_make(self.__tab.iat[row, COL_AT], self.__tab.iat[row, COL_AC], self.__tab.iat[row, COL_AN])
                self.__tab.iloc[row, [COL_IA, COL_HA, COL_AP]] = 0.
                self.__db.set(group, KEY_INF, pd.DataFrame([self.__tab.iloc[row, COL_IA:]], [0]))
        if save:
            self.__db.save()
        self.__tab = self.__tab.sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        return

    def load(self, data: db, update: bool = True) -> pd.DataFrame:
        self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = data
        for group, df in self.__db.get(key=KEY_INF).items():
            if (df.columns != COL_TAG[COL_IA:]).any():
                raise ValueError(f'DB error in {group}/{KEY_INF}\n{df}')
            df = pd.concat([pd.DataFrame([group_info(group)], [0], [TAG_AT, TAG_AC, TAG_AN]), df], axis=1)
            self.__tab = pd.concat([self.__tab, df], ignore_index=True)
        self.__tab = self.__tab.sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        if update:
            self._update()
        return self.__tab.copy()

    def save(self) -> None:
        self.__db.save()
        return

    def get(self, item: int | str | None = None) -> pd.DataFrame | pd.Series:
        if item is None:
            data = self.__tab.copy()
        elif type(item) is int:
            data = self.__tab.iloc[item, :]
        elif type(item) is str:
            typ, code = group_info(item)[:2]
            v = (self.__tab.iloc[:, COL_AC] == code) & (self.__tab.iloc[:, COL_AT] == typ)
            data = self.__tab.loc[v]
        else:
            raise TypeError(f'Unsupported data type [{type(item)}].')
        return data

    def add(self, group: str) -> None:
        typ, code = group_info(group)[:2]
        self.__tab = pd.concat([self.__tab, pd.DataFrame(
            [[typ, code, '']], columns=[TAG_AT, TAG_AC, TAG_AN]
        )], ignore_index=True)
        self._update(self.__tab.index[-1])
        return

    def remove(self, item: int | str | None = None) -> None:
        if type(item) is int:
            group = group_make(self.__tab.iat[item, COL_AT], self.__tab.iat[item, COL_AC], self.__tab.iat[item, COL_AN])
            self.__tab = self.__tab.drop(index=item).reset_index(drop=True)
            self.__db.remove(group)
        elif type(item) is str:
            typ, code = group_info(item)[:2]
            v = (self.__tab.iloc[:, COL_AC] == code) & (self.__tab.iloc[:, COL_AT] == typ)
            row = self.__tab.loc[v].index
            self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
            self.__db.remove(item)
        elif item is None:
            self.__tab = self.__tab.drop(index=self.__tab.index).reset_index(drop=True)
            self.__db.remove()
        else:
            raise TypeError(f'Unsupported data type [{type(item)}].')
        self.__db.save()
        return

    def read_csv(self, file: str, update: bool = True) -> pd.DataFrame:
        self.__tab = pd.concat(
            [self.__tab, pd.read_csv(file).iloc[:, :COL_AN]], ignore_index=True
        ).drop_duplicates([TAG_AT, TAG_AC]).sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        if update:
            self._update()
        return self.__tab.copy()

class View(QTableView):
    def __init__(self, parent: QWidget | None = None) -> None:
        QTableView.__init__(self, parent)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        # self.setContextMenuPolicy(Qt.ActionsContextMenu)
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        # action = QAction('test2', self)
        # action.triggered.connect(self.test)
        # self.addAction(action)
        # self.customContextMenuRequested.connect(self.test)
        # header = self.horizontalHeader()
        # header.setContextMenuPolicy(Qt.CustomContextMenu)
        # header.addAction(action)
        # header.customContextMenuRequested.connect(self.test)
        self.__func_del = None
        self.__func_upd = None
        self.__func_ass = None
        return

    # def test(self, pos):
    #     menu = QMenu(self)
    #     act_del = menu.addAction('test2')
    #     action = menu.exec(self.mapToGlobal(pos))
    #     if action == act_del:
    #         print('test2')
    #         print(pos)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        idx = self.indexAt(event.pos())
        flags = idx.flags()
        if flags == Qt.NoItemFlags:
            return
        menu = QMenu(self)
        en_upd = not flags & Qt.ItemIsEditable
        if en_upd:
            act_upd = menu.addAction('Update')
        act_del = menu.addAction('Delete')
        action = menu.exec(event.globalPos())
        if action == act_del:
            print('Delete')
            print(idx.row())
            if self.__func_del:
                self.__func_del(idx.row())
        elif en_upd and action == act_upd:
            print('Update')
            print(idx.row())
            if self.__func_upd:
                self.__func_upd(idx.row())
        return super().contextMenuEvent(event)

    def setDelete(self, func) -> None:
        self.__func_del = func
        return

    def setUpdate(self, func) -> None:
        self.__func_upd = func
        return

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        idx = self.indexAt(event.position().toPoint())
        flags = idx.flags()
        if flags == Qt.ItemIsEnabled | Qt.ItemIsSelectable:
            print(f'Goto {idx.row()}')
            if self.__func_ass:
                self.__func_ass(idx.row())
        return super().mouseDoubleClickEvent(event)

    def setOpen(self, func) -> None:
        self.__func_ass = func
        return

class Mod(Tab, basTabMod):
    __asset_open = Signal(QWidget)
    def __init__(self, data: db | None = None) -> None:
        Tab.__init__(self)
        self.__tab = self.get()
        basTabMod.__init__(self, self.__tab, View)
        self.__nul = pd.DataFrame([['', '', '', NAN, NAN, NAN, NAN, NAN]], [0], COL_TAG).astype(COL_TYP)
        if data is None:
            self.update()
        else:
            self.load(data)
        self.view.setMinimumWidth(866)
        self.view.setDelete(self.remove)
        self.view.setUpdate(self.update)
        self.view.setOpen(self.open)
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.row() == self.__tab.index.size - 1:
            if index.column() <= COL_AC:
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
            else:
                return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index: QModelIndex, role: int) -> str | None:
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            v = self.__tab.iat[index.row(), index.column()]
            if pd.isna(v):
                return ''
            if type(v) is str:
                return v
            col = index.column()
            if col <= COL_AN:
                return str(v)
            elif col == COL_CR or col == COL_AR:
                return f'{v * 100:,.2f}%'
            else:
                return f'{v:,.2f}'
        elif role == Qt.TextAlignmentRole:
            if index.column() <= COL_AN:
                return int(Qt.AlignCenter)
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return basTabMod.data(self, index, role)

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if index.isValid() and role == Qt.EditRole:
            row = index.row()
            self.__tab.iat[row, index.column()] = str(value)
            self.update(row)
            return True
        return False

    def update(self, data: int | str | None = None) -> None:
        if type(data) is str:
            typ, code = group_info(data)[:2]
            if not (typ in ASSET_GRP and code):
                self._raise(f'Group error [{data}].')
                return
            tab = self.get()
            v = (tab.iloc[:, COL_AC] == code) & (tab.iloc[:, COL_AT] == typ)
            if v.any():
                data  = v.loc[v].index[0]
            else:
                return
        elif not (type(data) is int or data is None):
            self._raise(f'Unsupported data type [{type(data)}].')
            return
        rows = self.__tab.index.size
        cols = self.__tab.columns.size
        if rows:
            if data is None:
                _range = range(rows - 1)
                self.error = ()
                self.setColor()
            elif data < rows - 1 and data > 0:
                _range = (data,)
                self.setColor(None, None, 0, data, cols, 1)
            else:
                _range = ()
            for row in _range:
                try:
                    self._update(row, True, False)
                except:
                    try:
                        self._update(row, False, False)
                    except:
                        self.__tab.iloc[:-1, :] = self.get()
                        basTabMod.table(self, self.__tab)
                        self._raise((f'DB error [{sys.exc_info()[1].args}].', {(0, row, cols, 1)}))
                        return
                    else:
                        self._raise((sys.exc_info()[1].args[0], {(0, row, cols, 1)}), LV_WARN, msgBox=False)
                else:
                    self.setColor(FORE, COLOR_GOOD[FORE], 0, row, cols, 1)
                    self.setColor(BACK, COLOR_GOOD[BACK], 0, row, cols, 1)
                self.__tab.iloc[:-1, :] = self.get()
                basTabMod.table(self, self.__tab)
            if not (data is None or data == rows -1):
                return
            self.setColor(None, None, 0, rows - 1, cols, 1)
            typ = self.__tab.iat[-1, COL_AT]
            code = self.__tab.iat[-1, COL_AC]
            if typ and code:
                group = group_make(typ, code)
                try:
                    self.add(group)
                except:
                    basTabMod.table(self, self.__tab)
                    self._raise((sys.exc_info()[1].args[0], {(0, rows - 1, cols, 1)}))
                else:
                    self.setColor(FORE, COLOR_GOOD[FORE], 0, rows - 1, cols, 1)
                    self.setColor(BACK, COLOR_GOOD[BACK], 0, rows - 1, cols, 1)
                    self.__tab = pd.concat([self.get(), self.__nul], ignore_index=True)
            elif typ:
                self._raise(('Asset code is required.', {(COL_AC, rows - 1, 1, 1)}), msgBox=False)
            elif code:
                self._raise(('Asset type is invalid.', {(COL_AT, rows - 1, 1, 1)}), msgBox=False)
            elif self.__tab.iat[-1, COL_AN] or not self.__tab.iloc[-1, COL_IA:].isna().all():
                self.__tab.iloc[-1, :] = self.__nul.iloc[0, :]
        else:
            self.error = ()
            self.setColor()
            self.__tab = self.__nul.copy()
        basTabMod.table(self, self.__tab)
        self.save()
        return

    def load(self, data: db) -> pd.DataFrame | None:
        try:
            Tab.load(self, data, False)
        except:
            self._raise(sys.exc_info()[1].args)
            return None
        else:
            self.__tab = pd.concat([self.get(), self.__nul], ignore_index=True)
            self.update()
        return self.get()

    def remove(self, data: int | str | None = None) -> None:
        if type(data) is str:
            typ, code = group_info(data)[:2]
            if not (typ in ASSET_GRP and code):
                self._raise(f'Group error [{data}].')
                return
            tab = self.get()
            v = (tab.iloc[:, COL_AC] == code) & (tab.iloc[:, COL_AT] == typ)
            if v.any():
                data  = v.loc[v].index[0]
            else:
                return
        elif not (type(data) is int or data is None):
            self._raise(f'Unsupported data type [{type(data)}].')
            return
        rows = self.__tab.index.size
        if data == rows - 1:
            self.__tab.iloc[-1, :] = self.__nul.iloc[0, :]
            self.adjColor(y0=data + 1, y1=data)
        elif data > 0 and data < rows - 1:
            try:
                Tab.remove(self, data)
            except:
                self._raise(sys.exc_info()[1].args)
            else:
                self.__tab = pd.concat([self.get(), pd.DataFrame([self.__tab.iloc[-1, :]])], ignore_index=True)
                self.adjColor(y0=data + 1, y1=data)
        basTabMod.table(self, self.__tab)
        return

    def table(self, view: bool = False) -> pd.DataFrame:
        if view:
            return self.__tab
        return self.get()

    def read_csv(self, file: str) -> pd.DataFrame | None:
        try:
            Tab.read_csv(self, file, False)
        except:
            self._raise(sys.exc_info()[1].args)
            return None
        else:
            self.__tab = pd.concat([self.get(), self.__nul], ignore_index=True)
            self.update()
        return self.get()

    def open(self, idx: int) -> None:
        group = group_make(self.__tab.iat[idx, COL_AT], self.__tab.iat[idx, COL_AC], self.__tab.iat[idx, COL_AN])
        t = txn.Mod()
        v = val.Mod()
        p = det.panel(t, v)
        d = db(R'C:\Users\51730\Desktop\dat')
        v.load(d, group)
        t.load(d, group)
        self.__asset_open.emit(p)
        return

    def get_signal(self) -> Signal:
        return self.__asset_open

if __name__ == '__main__':
    d = db(R'C:\Users\51730\Desktop\dat')

    app = QApplication()
    i = Mod()
    i.show()
    i.load(d)
    print(i)
    app.exec()

    # t = Tab()
    # t.load(d)
    # print(t)