from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from pandas import concat
from sys import exc_info
from db import *
from basTab import *
from dfIO import *
import assWid as ass
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

DUP_ERR = 'Duplicated asset is not allowed.'

class Tab:
    def __init__(self, data: db | None = None, upd: bool = True, online: bool = True) -> None:
        self.__tab = DataFrame(columns=COL_TAG).astype(COL_TYP)
        if data is None:
            self.__db = db()
        else:
            self.load(data, upd, online)
        return

    def __str__(self) -> str:
        return self.__tab.to_string()

    def __verify(self, data: DataFrame) -> None:
        if type(data) is not DataFrame:
            raise TypeError(f'Unsupported data type [{type(data)}].')
        rects = set()
        sz = min(data.columns.size, len(COL_TAG))
        v = Series(data.columns[:sz] != COL_TAG[:sz])
        if v.any():
            for i in v[v].index:
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
        v = Series(data.index != range(rows))
        if v.any():
            raise ValueError('Index error.', {(-1, v[v].index[0], 1, 1)})

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
            if data.iat[row, COL_AT] not in CLS_ASSET:
                raise ValueError('Unsupported asset type.', {(COL_AT, row, 1, 1)})
            if not data.iat[row, COL_AC]:
                raise ValueError('Empty asset code.', {(COL_AC, row, 1, 1)})

        v = data.duplicated([TAG_AT, TAG_AC], 'last')
        if v.any():
            for row in v[v].index:
                rects.add((0, row, data.columns.size, 1))
            raise ValueError(DUP_ERR, rects)
        return

    def __calc(self, group: str, txn_tab: DataFrame | None = None, val_tab: DataFrame | None = None) -> Series:
        typ, code, name = group_info(group)
        if typ not in CLS_ASSET:
            raise ValueError(f'Unsupported asset type [{typ}].')
        s = Series([typ, code, name, 0., 0., NAN, 0., NAN], COL_TAG)
        if not (txn_tab is None or val_tab is None or txn_tab.empty):
            s.iat[COL_IA] = val_tab.iat[0, val.COL_HS] * val_tab.iat[0, val.COL_UP]
            if isna(s.iat[COL_IA]):
                s.iat[COL_IA] = 0.
            s.iat[COL_HA] = val_tab.iat[0, val.COL_HA]
            s.iat[COL_AP] = val_tab.iat[0, val.COL_HA] + txn_tab[txn.TAG_SA].sum() - txn_tab[txn.TAG_BA].sum()
            if txn_tab.iat[-1, txn.COL_HS]:
                t = txn.Tab(concat([txn_tab, DataFrame([[
                    val_tab.iat[0, val.COL_DT], val_tab.iat[0, val.COL_HA], txn_tab.iat[-1, txn.COL_HS]
                ]], columns=[txn.TAG_DT, txn.TAG_SA, txn.TAG_SS])], ignore_index=True))
                s.iat[COL_CR] = t.table().iat[-1, txn.COL_RR]
                s.iat[COL_AR] = t.avgRate()
            else:
                s.iat[COL_CR] = NAN
                s.iat[COL_AR] = txn.Tab(txn_tab).avgRate()
        return s

    def __update(self, idx: int | None = None, online: bool = True) -> None:
        if idx is None:
            _range = range(self.__tab.index.size)
        else:
            _range = (idx,)
        self.__verify(self.__tab)
        for row in _range:
            group = group_make(self.__tab.iat[row, COL_AT], self.__tab.iat[row, COL_AC], self.__tab.iat[row, COL_AN])
            g = self.__db.get(group)
            if g:
                if online:
                    v = val.Tab(self.__db, group)
                    val_tab = v.table()
                    self.__tab.iat[row, COL_AT] = v.get_type()
                    self.__tab.iat[row, COL_AN] = v.get_name()
                    group = v.get_group()
                else:
                    val_tab = val.Tab(self.__db, group, False).table()
                self.__tab.iloc[row] = self.__calc(group, g.get(KEY_TXN, None), val_tab)
                self.__db.set(group, KEY_INF, DataFrame([self.__tab.iloc[row, COL_IA:]], [0]))
            else:
                if online:
                    v = val.Tab(self.__db, group)
                    self.__tab.iat[row, COL_AT] = v.get_type()
                    self.__tab.iat[row, COL_AN] = v.get_name()
                    group = v.get_group()
                self.__tab.iloc[row, [COL_IA, COL_HA, COL_AP]] = 0.
                self.__db.set(group, KEY_INF, DataFrame([self.__tab.iloc[row, COL_IA:]], [0]))
        self.__tab = self.__tab.sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        return

    def update(self, idx: int | None = None, online: bool = True) -> None:
        return self.__update(idx, online)

    def load(self, data: db, upd: bool = True, online: bool = True) -> DataFrame:
        self.__tab = DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = data
        for group, df in self.__db.get(key=KEY_INF).items():
            if (df.columns != COL_TAG[COL_IA:]).any():
                raise ValueError(f'DB error in {group}/{KEY_INF}\n{df}')
            df = concat([DataFrame([group_info(group)], [0], [TAG_AT, TAG_AC, TAG_AN]), df], axis=1)
            self.__tab = concat([self.__tab, df], ignore_index=True)
        self.__tab = self.__tab.sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        if upd:
            self.__update(online=online)
        return self.__tab.copy()

    def get(self, item: int | str | None = None) -> DataFrame | Series:
        if item is None:
            data = self.__tab.copy()
        elif type(item) is int:
            data = self.__tab.iloc[item]
        elif type(item) is str:
            typ, code = group_info(item)[:2]
            v = (self.__tab[TAG_AC] == code) & (self.__tab[TAG_AT] == typ)
            data = self.__tab[v]
        else:
            raise TypeError(f'Unsupported data type [{type(item)}].')
        return data

    def add(self, typ: str, code: str) -> None:
        tab = concat([self.__tab, DataFrame(
            [[typ, code, '']], columns=[TAG_AT, TAG_AC, TAG_AN]
        )], ignore_index=True)
        self.__verify(tab)
        self.__tab = tab
        self.__update(self.__tab.index[-1])
        return

    def delete(self, item: int | str | None = None) -> None:
        if type(item) is int:
            group = group_make(self.__tab.iat[item, COL_AT], self.__tab.iat[item, COL_AC], self.__tab.iat[item, COL_AN])
            self.__tab = self.__tab.drop(index=item).reset_index(drop=True)
            self.__db.remove(group)
        elif type(item) is str:
            typ, code = group_info(item)[:2]
            v = (self.__tab[TAG_AC] == code) & (self.__tab[TAG_AT] == typ)
            row = self.__tab[v].index
            self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
            self.__db.remove(item)
        elif item is None:
            self.__tab = self.__tab.drop(index=self.__tab.index).reset_index(drop=True)
            self.__db.remove()
        else:
            raise TypeError(f'Unsupported data type [{type(item)}].')
        return

    def import_table(self, file: str, upd: bool = True) -> DataFrame:
        tab = dfImport(file).astype(COL_TYP)
        self.__tab = concat(
            [self.__tab, tab[[TAG_AT, TAG_AC, TAG_AN]]], ignore_index=True
        ).drop_duplicates([TAG_AT, TAG_AC]).sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        if upd:
            self.__update()
        return self.__tab.copy()

    def export_table(self, file: str, data: bool = True) -> None:
        if data:
            tab = self.__tab
        else:
            tab = DataFrame(columns=COL_TAG).astype(COL_TYP)
        dfExport(tab, file)
        return

class View(QTableView):
    def __init__(self, parent: QWidget | None = None) -> None:
        QTableView.__init__(self, parent)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.__func_del = None
        self.__func_upd = None
        self.__func_open = None
        return

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        idx = self.indexAt(event.pos())
        flags = idx.flags()
        if flags == Qt.NoItemFlags:
            return
        menu = QMenu(self)
        en_upd = not flags & Qt.ItemIsEditable
        if en_upd:
            act_open = menu.addAction('Open')
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
        elif action == act_open:
            print('Open')
            print(idx.row())
            if self.__func_open:
                self.__func_open(idx.row())
        return super().contextMenuEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        idx = self.indexAt(event.position().toPoint())
        flags = idx.flags()
        if flags == Qt.ItemIsEnabled | Qt.ItemIsSelectable:
            print(f'Goto {idx.row()}')
            if self.__func_open:
                self.__func_open(idx.row())
        return super().mouseDoubleClickEvent(event)

    def setOpen(self, func) -> None:
        self.__func_open = func
        return

    def setUpdate(self, func) -> None:
        self.__func_upd = func
        return

    def setDelete(self, func) -> None:
        self.__func_del = func
        return

class Mod(Tab, basMod):
    __asset_open = Signal(QWidget)
    def __init__(self, data: db | None = None, upd: bool = True, online: bool = True) -> None:
        Tab.__init__(self)
        basMod.__init__(self, self.get(), View)
        self.__db = None
        if data is None:
            basMod.table(self, self.get())
        else:
            self.load(data, upd, online)
        self.view.setMinimumWidth(866)
        self.view.setDelete(self.delete)
        self.view.setUpdate(self.update)
        self.view.setOpen(self.open)
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index: QModelIndex, role: int) -> str | None:
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            v = self.get().iat[index.row(), index.column()]
            if isna(v):
                return ''
            col = index.column()
            if col == COL_AT:
                return DICT_ASSET_TAG[v]
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
        return basMod.data(self, index, role)

    def update(self, data: int | str | None = None, online: bool = True) -> None:
        if type(data) is str:
            typ, code = group_info(data)[:2]
            if not (typ in CLS_ASSET and code):
                self._raise(f'Group error [{data}].')
                return
            tab = self.get()
            v = (tab[TAG_AC] == code) & (tab[TAG_AT] == typ)
            if v.any():
                data  = v[v].index[0]
            else:
                return
        elif not (type(data) is int or data is None):
            self._raise(f'Unsupported data type [{type(data)}].')
            return
        tab = self.get()
        rows = tab.index.size
        cols = tab.columns.size
        if rows:
            if online or (len(self.error) > 0 and 'DB error' in self.error[0]):
                if data is None:
                    _range = range(rows)
                    self.error = ()
                    self.setColor()
                elif data >= 0 and data < rows - 1:
                    _range = (data,)
                    self.setColor(None, None, 0, data, cols, 1)
                else:
                    _range = ()
                for row in _range:
                    try:
                        Tab.update(self, row, True)
                    except:
                        try:
                            Tab.update(self, row, False)
                        except:
                            basMod.table(self, self.get())
                            self._raise((f'DB error [{exc_info()[1].args}].', {(0, row, cols, 1)}))
                            return
                        else:
                            self._raise((exc_info()[1].args[0], {(0, row, cols, 1)}), LV_WARN, msgBox=False)
                    else:
                        self.setColor(FORE, COLOR_INFO[FORE], 0, row, cols, 1)
                        self.setColor(BACK, COLOR_INFO[BACK], 0, row, cols, 1)
                    # basMod.table(self, self.get())
            else:
                if data is None:
                    _range = range(rows)
                    self.error = ()
                elif data >= 0 and data < rows - 1:
                    _range = (data,)
                else:
                    _range = ()
                for row in _range:
                    try:
                        Tab.update(self, row, False)
                    except:
                        basMod.table(self, self.get())
                        self._raise((f'DB error [{exc_info()[1].args}].', {(0, row, cols, 1)}))
                        return
        basMod.table(self, self.get())
        return

    def load(self, data: db, upd: bool = True, online: bool = True) -> DataFrame | None:
        try:
            Tab.load(self, data, False, False)
        except:
            self._raise(exc_info()[1].args)
            return None
        self.__db = data
        if upd:
            self.update(online=online)
        else:
            basMod.table(self, self.get())
        return self.get()

    def add(self, typ: str, code: str) -> None:
        try:
            Tab.add(self, typ, code)
        except:
            tab = self.get()
            rows = tab.index.size
            cols = tab.columns.size
            args = exc_info()[1].args
            if len(args) >= 2 and type(args[1]) is set:
                if args[0] == DUP_ERR:
                    self.select(args[1].pop()[1])
                    self._raise(args)
                else:
                    for rect in args[1].copy():
                        if rect[0] >= cols or rect[1] >= rows:
                            args[1].remove(rect)
                    self._raise(args)
            else:
                self.setColor(FORE, COLOR_WARN[FORE], 0, rows - 1, cols, 1)
                self.setColor(BACK, COLOR_WARN[BACK], 0, rows - 1, cols, 1)
                basMod.table(self, tab)
                self._raise(args, LV_WARN)
        else:
            tab = self.get()
            cols = tab.columns.size
            v = tab[TAG_AC] == code
            if v.any():
                row = v[v].index[0]
                self.adjColor(y0=row, y1=row + 1)
                self.setColor(FORE, COLOR_INFO[FORE], 0, row, cols, 1)
                self.setColor(BACK, COLOR_INFO[BACK], 0, row, cols, 1)
            basMod.table(self, tab)
        return

    def delete(self, data: int | str | None = None) -> None:
        if type(data) is str:
            typ, code = group_info(data)[:2]
            if not (typ in CLS_ASSET and code):
                self._raise(f'Group error [{data}].')
                return
            tab = self.get()
            v = (tab[TAG_AC] == code) & (tab[TAG_AT] == typ)
            if v.any():
                data  = v[v].index[0]
            else:
                return
        elif not (type(data) is int or data is None):
            self._raise(f'Unsupported data type [{type(data)}].')
            return
        tab = self.get()
        rows = tab.index.size
        if data >= 0 and data < rows:
            if tab.iloc[data, COL_IA:].sum():
                msg = 'Asset is not empty.\nContinue deleting?'
                if QMessageBox.warning(None, 'Warning', msg, QMessageBox.Yes, QMessageBox.No) != QMessageBox.Yes:
                    return
            try:
                Tab.delete(self, data)
            except:
                self._raise(exc_info()[1].args)
            else:
                self.adjColor(y0=data + 1, y1=data)
        basMod.table(self, self.get())
        return

    def import_table(self, file: str, upd: bool = True) -> DataFrame | None:
        try:
            Tab.import_table(self, file, False)
        except:
            self._raise(exc_info()[1].args)
            return None
        if upd:
            self.update()
        else:
            basMod.table(self, self.get())
        return self.get()

    def export_table(self, file: str, data: bool = True) -> None:
        try:
            Tab.export_table(self, file, data)
        except:
            self._raise(exc_info()[1].args)
        return

    def open(self, idx: int) -> None:
        tab = self.get()
        group = group_make(tab.iat[idx, COL_AT], tab.iat[idx, COL_AC], tab.iat[idx, COL_AN])
        if self.__db.get(group, KEY_VAL) is None:
            upd = True
        else:
            upd = False
        self.__asset_open.emit(ass.Wid(self.__db, group, upd))
        return

    def set_open(self, open_func) -> None:
        self.__asset_open.connect(open_func)
        return

if __name__ == '__main__':
    d = db(DB_PATH)

    app = QApplication()
    i = Mod(d)
    i.show()
    print(i)
    app.exec()

    # t = Tab(d)
    # print(t)

    d.save()