from PySide6.QtCore import Signal, Slot
import pandas as pd
import sys
from basTab import *
from txnTab import (
    txnTab,
    TAG_DT as TXN_TAG_DT,
    TAG_SA as TXN_TAG_SA,
    TAG_SS as TXN_TAG_SS,
    COL_BA as TXN_COL_BA,
    COL_SA as TXN_COL_SA,
    COL_HS as TXN_COL_HS,
    COL_HP as TXN_COL_HP,
    COL_TAG as TXN_COL_TAG,
)
from valTab import (
    valTab,
    COL_DT as VAL_COL_DT,
    COL_HA as VAL_COL_HA,
    COL_TAG as VAL_COL_TAG,
)
from db import *

TAG_AT = 'Asset Type'
TAG_AC = 'Asset Code'
TAG_AN = 'Asset Name'
TAG_IA = 'Invest Amount'
TAG_PA = 'Profit Amount'
TAG_HA = 'Holding Amount'
TAG_PR = 'Profit Rate'
TAG_AR = 'Average Rate'

COL_AT = 0
COL_AC = 1
COL_AN = 2
COL_IA = 3
COL_PA = 4
COL_HA = 5
COL_PR = 6
COL_AR = 7

COL_TAG = [
    TAG_AT,
    TAG_AC,
    TAG_AN,
    TAG_IA,
    TAG_PA,
    TAG_HA,
    TAG_PR,
    TAG_AR,
]

COL_TYP = {
    TAG_AT:'str',
    TAG_AC:'str',
    TAG_AN:'str',
    TAG_IA:'float64',
    TAG_PA:'float64',
    TAG_HA:'float64',
    TAG_PR:'float64',
    TAG_AR:'float64',
}

FORE_GOOD = 0x00bf00
BACK_GOOD = 0xdfffdf
COLOR_GOOD = (FORE_GOOD, BACK_GOOD)

class infTab:
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

    def __set(self, group: str, name: str, txn_tab: pd.DataFrame, val_tab: pd.DataFrame) -> None:
        typ, code = group_info(group)
        if typ not in ASSET_GRP:
            raise ValueError(f'Unsupported asset type [{typ}].')
        df = pd.DataFrame(NAN, [0], COL_TAG).astype(COL_TYP)
        df.iat[0, COL_AT] = typ
        df.iat[0, COL_AC] = code
        df.iat[0, COL_AN] = name
        if txn_tab.index.size:
            for i in range(txn_tab.index.size):
                Amt = txn_tab.iat[i, TXN_COL_HP] * txn_tab.iat[i, TXN_COL_HS]
                if df.iat[0, COL_IA] < Amt:
                    df.iat[0, COL_IA] = Amt
            df.iat[0, COL_PA] = val_tab.iat[0, VAL_COL_HA] + txn_tab.iloc[:, TXN_COL_SA].sum() - txn_tab.iloc[:, TXN_COL_BA].sum()
            df.iat[0, COL_HA] = val_tab.iat[0, VAL_COL_HA]
            df.iat[0, COL_PR] = df.iat[0, COL_PA] / df.iat[0, COL_IA]
            if txn_tab.iat[-1, TXN_COL_HS]:
                df.iat[0, COL_AR] = txnTab(pd.concat([txn_tab, pd.DataFrame([[
                    val_tab.iat[0, VAL_COL_DT], val_tab.iat[0, VAL_COL_HA], txn_tab.iat[-1, TXN_COL_HS]
                ]], columns=[TXN_TAG_DT, TXN_TAG_SA, TXN_TAG_SS])], ignore_index=True)).avgRate()
            else:
                df.iat[0, COL_AR] = txnTab(txn_tab).avgRate()
        v = (self.__tab.iloc[:, COL_AC] == code) & (self.__tab.iloc[:, COL_AT] == typ)
        if v.any():
            self.__tab.loc[v] = df
        else:
            self.__tab = pd.concat([self.__tab, df])
        self.__tab = self.__tab.sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        return

    def update(self, idx: int | None = None, online: bool = True) -> None:
        if idx is None:
            _range = range(self.__tab.index.size)
        else:
            _range = (idx,)
        self.__verify(self.__tab)
        tab = self.__tab.copy()
        for row in _range:
            group = group_make(self.__tab.iat[row, COL_AT], self.__tab.iat[row, COL_AC])
            g = self.__db.get(group)
            if g:
                txn_tab = g[KEY_TXN]
                if txn_tab.empty:
                    self.__tab.iloc[row, COL_IA:] = 0.
                else:
                    if online:
                        val = valTab(group, txn_tab)
                        val_tab = val.table()
                        name = val.get_name()
                    else:
                        val_tab = valTab(g[KEY_VAL], txn_tab).table()
                        name = self.__tab.iat[row, COL_AN]
                        if not name:
                            name = g[KEY_INF].iat[COL_AN]
                    self.__set(group, name, txn_tab, val_tab)
            else:
                if online:
                    self.__tab.iat[row, COL_AN] = valTab(group).get_name()
                self.__tab.iloc[row, COL_IA:] = 0.
                self.__db.set(group, KEY_INF, self.__tab.iloc[row, :])
                self.__db.set(group, KEY_TXN, pd.DataFrame(columns=TXN_COL_TAG))
                self.__db.set(group, KEY_VAL, pd.DataFrame(columns=VAL_COL_TAG))
            if (self.__tab.iloc[row, :] != tab.iloc[row, :]).any():
                self.__db.set(group, KEY_INF, self.__tab.iloc[row, :])
        return

    def load(self, data: db) -> pd.DataFrame:
        self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = data
        for group, s in self.__db.get(key=KEY_INF).items():
            if s.index != COL_TAG:
                raise ValueError(f'DB error in {group}/{KEY_INF}\n{s}')
            self.__tab = pd.concat([self.__tab, pd.DataFrame([s])], ignore_index=True)
        self.__tab = self.__tab.sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        self.update()
        return self.__tab

    def get(self, group: str | None = None) -> pd.DataFrame:
        if group:
            typ, code = group_info(group)
            v = (self.__tab.iloc[:, COL_AC] == code) & (self.__tab.iloc[:, COL_AT] == typ)
            return self.__tab.loc[v]
        return self.__tab.copy()

    def add(self, group: str) -> None:
        typ, code = group_info(group)
        self.__tab = pd.concat([self.__tab, pd.DataFrame(
            [[typ, code, '']], columns=[TAG_AT,TAG_AC, TAG_AN]
        )], ignore_index=True)
        self.update(self.__tab.index[-1])
        return

    def remove(self, group: str | None = None) -> None:
        if group is None:
            row = self.__tab.index
        else:
            typ, code = group_info(group)
            v = (self.__tab.iloc[:, COL_AC] == code) & (self.__tab.iloc[:, COL_AT] == typ)
            row = self.__tab.loc[v].index
        self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
        self.__db.remove(group)
        return

    def read_csv(self, file: str) -> pd.DataFrame:
        self.__tab = pd.concat(
            [self.__tab, pd.read_csv(file).iloc[:, :COL_AN]], ignore_index=True
        ).drop_duplicates([TAG_AT, TAG_AC]).sort_values([TAG_HA, TAG_AT, TAG_AC], ascending=False, ignore_index=True)
        self.update()
        return self.__tab.copy()

class infTabView(QTableView):
    def __init__(self, parent: QWidget | None = None) -> None:
        QTableView.__init__(self, parent)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setAlternatingRowColors(True)
        return

class infTabMod(infTab, basTabMod):
    def __init__(self, data: db | None = None) -> None:
        infTab.__init__(self)
        basTabMod.__init__(self, self.get(), infTabView)
        self.__nul = pd.DataFrame([['', '', '', NAN, NAN, NAN, NAN, NAN]], [0], COL_TAG)
        if data is None:
            self.__update(infTab.get(self))
        else:
            self.load(data)
        self.view.setMinimumWidth(866)
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
            elif col >= COL_PR:
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
            self.__update(idx=row)
            return True
        return False

    def __update(self, tab: pd.DataFrame | None = None, idx: int | None = None) -> None:
        self.error = ()
        self.setColor(FORE, COLOR[LV_CRIT][FORE])
        self.setColor(BACK, COLOR[LV_CRIT][BACK])
        self.setColor(FORE, COLOR[LV_WARN][FORE])
        self.setColor(BACK, COLOR[LV_WARN][BACK])
        self.setColor(FORE, COLOR_GOOD[FORE])
        self.setColor(BACK, COLOR_GOOD[BACK])
        if tab is not None:
            self.__tab = tab.copy()
        rows = self.__tab.index.size
        if rows:
            if idx is None:
                _range = range(rows - 1)
            elif idx < rows - 1 and idx > 0:
                _range = (idx,)
            else:
                _range = ()
            for row in _range:
                try:
                    self.update(row)
                except:
                    try:
                        self.update(row, False)
                    except:
                        self.__tab.iloc[:-1, :] = self.get()
                        basTabMod.table(self, self.__tab)
                        self._raise((f'DB error [{sys.exc_info()[1].args}].', {(0, row, self.__tab.columns.size, 1)}))
                        return
                    else:
                        self._raise((sys.exc_info()[1].args[0], {(0, row, self.__tab.columns.size, 1)}), LV_WARN, msgBox=False)
                else:
                    self.setColor(FORE, COLOR_GOOD[FORE], 0, row, self.__tab.columns.size, 1)
                    self.setColor(BACK, COLOR_GOOD[BACK], 0, row, self.__tab.columns.size, 1)
                self.__tab.iloc[:-1, :] = self.get()
                basTabMod.table(self, self.__tab)
            typ = self.__tab.iat[-1, COL_AT]
            code = self.__tab.iat[-1, COL_AC]
            if typ and code:
                group = group_make(typ, code)
                try:
                    self.add(group)
                except:
                    basTabMod.table(self, self.__tab)
                    self._raise((sys.exc_info()[1].args[0], {(0, rows - 1, self.__tab.columns.size, 1)}))
                else:
                    self.setColor(FORE, COLOR_GOOD[FORE], 0, rows - 1, self.__tab.columns.size, 1)
                    self.setColor(BACK, COLOR_GOOD[BACK], 0, rows - 1, self.__tab.columns.size, 1)
                    self.__tab = pd.concat([self.get(), self.__nul], ignore_index=True)
            elif typ:
                self._raise(('Asset code is required.', {(COL_AC, rows - 1, 1, 1)}), msgBox=False)
            elif code:
                self._raise(('Asset type is invalid.', {(COL_AT, rows - 1, 1, 1)}), msgBox=False)
            elif self.__tab.iat[-1, COL_AN] or not self.__tab.iloc[-1, COL_IA:].isna().all():
                self.__tab.iloc[-1, :] = self.__nul
        else:
            self.__tab = self.__nul.copy()
        basTabMod.table(self, self.__tab)
        return

    def load(self, data: db) -> None:
        try:
            infTab.load(self, data)
        except:
            self._raise(sys.exc_info()[1].args)
        self.__update(self.get())
        return

    def table(self, view: bool | None = False) -> pd.DataFrame:
        if view:
            return self.__tab
        return self.get()

    def read_csv(self, file: str) -> pd.DataFrame | None:
        try:
            tab = infTab.read_csv(self, file)
        except:
            self._raise(sys.exc_info()[1].args)
            return None
        else:
            self.__update(tab)
        return self.get()

if __name__ == '__main__':
    app = QApplication()
    inf = infTabMod()
    inf.show()
    app.exec()