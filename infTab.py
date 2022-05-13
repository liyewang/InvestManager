import pandas as pd
import sys
from basTab import *
from txnTab import (
    txnTab,
    COL_BA as TXN_COL_BA,
    COL_BS as TXN_COL_BS,
    COL_SA as TXN_COL_SA,
    COL_SS as TXN_COL_SS,
    COL_HS as TXN_COL_HS,
    COL_HP as TXN_COL_HP,
)
from valTab import (
    valTab,
    COL_DT as VAL_COL_DT,
    COL_HA as VAL_COL_HA,
)
from db import (
    KEY_INF,
    KEY_TXN,
    KEY_VAL,
    GRP_DICT,
    KEY_DICT,
)

TAG_AG = 'Asset Group'
TAG_AT = 'Asset Type'
TAG_AC = 'Asset Code'
TAG_AN = 'Asset Name'
TAG_IA = 'Invest Amount'
TAG_PA = 'Profit Amount'
TAG_HA = 'Holding Amount'
TAG_PR = 'Profit Rate'
TAG_AR = 'Average Rate'

COL_AG = 0
COL_AT = 1
COL_AC = 2
COL_AN = 3
COL_IA = 4
COL_PA = 5
COL_HA = 6
COL_PR = 7
COL_AR = 8

COL_TAG = [
    TAG_AG,
    TAG_AT,
    TAG_AC,
    TAG_AN,
    TAG_IA,
    TAG_PA,
    TAG_HA,
    TAG_PR,
    TAG_AR,
]

FORE_GOOD = 0x00bf00
BACK_GOOD = 0xdfffdf
COLOR_GOOD = (FORE_GOOD, BACK_GOOD)

class infTab:
    def __init__(self, db: dict | None = None) -> None:
        self.__tab = pd.DataFrame(columns=COL_TAG)
        if db:
            self.load(db)
        return

    def __repr__(self) -> str:
        return self.__tab.to_string()

    def __verify(self, data: pd.DataFrame) -> None:
        if type(data) is not pd.DataFrame:
            raise TypeError('Unsupported data type.')
        for row in range(data.index.size):
            group = data.iat[0, COL_AG]
            if GRP_DICT.get(group[0], None) != data.iat[0, COL_AT]:
                raise ValueError('Asset group does not match the asset type.', {(COL_AG, row, 2, 1)})
            if group[1:] != data.iat[0, COL_AC]:
                raise ValueError('Asset group does not match the asset code.', {(COL_AG, row, 1, 1), (COL_AC, row, 1, 1)})
        return

    def load(self, db: dict) -> None:
        for group, val in db.items():
            if GRP_DICT.get(group[0], None):
                self.__tab = pd.concat([self.__tab, val[KEY_INF]], ignore_index=True)
        self.__tab.sort_values(TAG_HA, ascending=False, ignore_index=True, inplace=True)
        self.__verify(self.__tab)
        return

    def set(self, group: str, name: str, txn: pd.DataFrame, val: pd.DataFrame) -> pd.DataFrame:
        df = pd.DataFrame(columns=COL_TAG)
        df.iat[0, COL_AG] = group
        df.iat[0, COL_AT] = GRP_DICT.get(group[0], None)
        df.iat[0, COL_AC] = group[1:]
        df.iat[0, COL_AN] = name
        if txn and txn.index.size:
            for i in range(txn.index.size):
                Amt = txn.iat[i, TXN_COL_HP] * txn.iat[i, TXN_COL_HS]
                if df.iat[0, COL_IA] < Amt:
                    df.iat[0, COL_IA] = Amt
            df.iat[0, COL_PA] = val.iat[0, VAL_COL_HA] + txn.iloc[:, TXN_COL_SA].sum() - txn.iloc[:, TXN_COL_BA].sum()
            df.iat[0, COL_HA] = val.iat[0, VAL_COL_HA]
            df.iat[0, COL_PR] = df.iat[0, COL_PA] / df.iat[0, COL_IA]
            if txn.iat[-1, TXN_COL_HS]:
                df.iat[0, COL_AR] = txnTab(pd.concat([txn, pd.DataFrame([[val.iat[0, VAL_COL_DT],
                    float('nan'), float('nan'), val.iat[0, VAL_COL_HA], txn.iat[-1, TXN_COL_HS],
                    float('nan'), float('nan'), float('nan')]], columns=txn.columns)], ignore_index=True)).avgRate()
            else:
                df.iat[0, COL_AR] = txnTab(txn).avgRate()
        v = self.__tab.iloc[:, COL_AG] == group
        if v.any():
            self.__tab.loc[v] = df
        else:
            self.__tab = pd.concat([self.__tab, df])
        self.__tab.sort_values(TAG_HA, ascending=False, ignore_index=True, inplace=True)
        return df

    def get(self, group: str | None = None) -> pd.DataFrame:
        if group:
            return self.__tab.loc[self.__tab.iloc[:, COL_AG] == group]
        return self.__tab

    def remove(self, group: str | None = None) -> None:
        if group:
            row = self.__tab.loc[self.__tab.iloc[:, COL_AG] == group].index
        else:
            row = self.__tab.index
        self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
        return

    def read_csv(self, file: str) -> pd.DataFrame:
        self.__tab = pd.read_csv(file)
        self.__tab.sort_values(TAG_HA, ascending=False, ignore_index=True, inplace=True)
        self.__verify(self.__tab)
        return self.__tab

class infTabView(QTableView):

    def __init__(self, parent: QWidget | None = None) -> None:
        QTableView.__init__(self, parent)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setAlternatingRowColors(True)
        self.setAutoScroll(False)
        return

class infTabMod(infTab, basTabMod):
    def __init__(self, db: dict | None = None) -> None:
        infTab.__init__(self)
        basTabMod.__init__(self, self.get(), infTabView)
        self.__nul = pd.DataFrame([['', '', '', '', float('nan'), float('nan'), float('nan'), float('nan'), float('nan')]], [0], COL_TAG)
        self.load(self, db)
        self.view.setColumnHidden(COL_AG, True)
        self.view.setMinimumWidth(866)
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.row() == self.__tab.index.size:
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
            self.__update(index=row)
            return True
        return False

    def __update(self, tab: pd.DataFrame | None = None, index: int | None = None) -> None:
        self.error = ()
        self.setColor(FORE, COLOR[LV_CRIT][FORE])
        self.setColor(BACK, COLOR[LV_CRIT][BACK])
        self.setColor(FORE, COLOR[LV_WARN][FORE])
        self.setColor(BACK, COLOR[LV_WARN][BACK])
        self.setColor(FORE, COLOR_GOOD[FORE])
        self.setColor(BACK, COLOR_GOOD[BACK])
        if tab is not None:
            self.__tab = tab
        rows = self.__tab.index.size
        self.beginResetModel()
        if rows:
            if index is None:
                _range = range(rows - 1)
            elif index < rows - 1 and index > 0:
                _range = (index,)
            else:
                _range = ()
            for row in _range:
                group = self.__tab.iat[row, COL_AG]
                if not group:
                    self._raise((f'Unsupported asset group [{group}].', {(0, row, self.__tab.columns.size, 1)}))
                if self.__db.get[group, None]:
                    try:
                        txn = self.__db[group][KEY_TXN]
                        if txn.index.size:
                            try:
                                val = valTab(group, txn)
                                infTab.set(self, group, val.get_name(), txn, val.table())
                            except:
                                val = valTab(None, txn, self.__db[group][KEY_VAL])
                                name = self.__db[group][KEY_INF].iat[row, COL_AN]
                                infTab.set(self, group, name, txn, val.table())
                                self._raise((sys.exc_info()[1].args[0], {(0, row, self.__tab.columns.size, 1)}), LV_WARN, msgBox=False)
                            else:
                                self.setColor(FORE, COLOR_GOOD[FORE], 0, row, self.__tab.columns.size, 1)
                                self.setColor(BACK, COLOR_GOOD[BACK], 0, row, self.__tab.columns.size, 1)
                        else:
                            self.__tab.iloc[row, TAG_IA:] = 0.
                    except:
                        self._raise((f'DB error [{sys.exc_info()[1].args}].', {(0, row, self.__tab.columns.size, 1)}))
                else:
                    self.__tab.iloc[row, TAG_IA:] = 0.
            self.__tab.iloc[:-1, :] = self.get()
            typ = self.__tab.iat[-1, COL_AT]
            key = KEY_DICT.get(typ, None)
            if key and code:
                code = self.__tab.iat[-1, COL_AC]
                group = f'{key}{code}'
                self.__tab.iat[-1, COL_AG] = group
                txn = txnTab()
                try:
                    val = valTab(group)
                    infTab.set(self, group, val.get_name(), txn, val.table())
                except:
                    self._raise((sys.exc_info()[1].args[0], {(0, rows - 1, self.__tab.columns.size, 1)}))
                else:
                    self.setColor(FORE, COLOR_GOOD[FORE], 0, rows - 1, self.__tab.columns.size, 1)
                    self.setColor(BACK, COLOR_GOOD[BACK], 0, rows - 1, self.__tab.columns.size, 1)
                    self.__tab = pd.concat([infTab.get(self), self.__nul], ignore_index=True)
            elif key:
                self._raise(('Asset code is required.', {(COL_AC, rows - 1, 1, 1)}), msgBox=False)
            elif code:
                self._raise(('Asset type is invalid.', {(COL_AT, rows - 1, 1, 1)}), msgBox=False)
            elif self.__tab.iat[-1, COL_AN] or not self.__tab.iloc[-1, COL_IA:].isna().all():
                self.__tab.iloc[-1, :] = self.__nul
        else:
            self.__tab = self.__nul
        basTabMod.table(self, self.__tab)
        self.endResetModel()
        return

    def load(self, db: dict) -> None:
        try:
            infTab.load(self, db)
        except:
            self._raise(sys.exc_info()[1].args)
        self.__db = db
        self.__update(self.get())
        return

    def table(self, view: bool | None = False) -> pd.DataFrame:
        if type(view) is bool and view:
            return self.__tab
        return infTab.get(self)

    def read_csv(self, file: str) -> pd.DataFrame:
        try:
            tab = infTab.read_csv(self, file)
        except:
            tab = None
            self._raise(sys.exc_info()[1].args)
        else:
            self.__update(tab)
        return tab

if __name__ == '__main__':
    app = QApplication()
    app.exec()