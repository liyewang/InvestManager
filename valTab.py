import requests
import pandas as pd
import sys
from PySide6.QtCore import Signal
from basTab import *
from txnTab import (
    txnTab,
    COL_DT as TXN_COL_DT,
    COL_BS as TXN_COL_BS,
    COL_SS as TXN_COL_SS,
    COL_HS as TXN_COL_HS,
    COL_HP as TXN_COL_HP,
)
from db import (
    GRP_FUND,
    GRP_DICT,
)

URL_API = 'http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode='
HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'}

TAG_DT_RAW = 'fld_enddate'

TAG_DT = 'Date'
TAG_UV = 'Unit Net Value'
TAG_NV = 'Net Value'
TAG_HA = 'Holding Amount'
TAG_HP = 'Holding Price'
TAG_TS = 'Transaction Share'

COL_DT = 0
COL_UV = 1
COL_NV = 2
COL_HA = 3
COL_HP = 4
COL_TS = 5

COL_TAG = [
    TAG_DT,
    TAG_UV,
    TAG_NV,
    TAG_HA,
    TAG_HP,
    TAG_TS,
]

class valTab:
    def __init__(self, group: str | None = None, txn: pd.DataFrame | None = None, val: pd.DataFrame | None = None) -> None:
        self.__code = ''
        self.__name = ''
        self.__tab = pd.DataFrame(columns=COL_TAG)
        self.__nul = pd.DataFrame(columns=COL_TAG[COL_HA:])
        self.__update(group, txn, val)
        return

    def __repr__(self) -> str:
        return self.__tab.to_string()

    def __update(self, group: str | None = None, txn: pd.DataFrame | None = None, val: pd.DataFrame | None = None) -> None:
        if group is not None:
            typ = GRP_DICT.get(group[0], None)
            code = group[1:]
            if typ == GRP_FUND:
                try:
                    df = pd.read_xml(requests.get(f'{URL_API}{code}', headers=HEADER).text)
                    code_new = f'{df.iat[0, 0]:06.0f}'
                    self.__code = code_new
                    self.__name = df.iat[1, 1]
                    self.__tab = df.iloc[2:, 2:5].astype({TAG_DT_RAW:'datetime64[ns]'}).drop_duplicates(ignore_index=True).sort_values(TAG_DT_RAW, ascending=False, ignore_index=True)
                    rows = self.__tab.index.size
                    self.__nul = pd.DataFrame([[0., float('nan'), 0.]], index=range(rows), columns=COL_TAG[COL_HA:])
                    self.__tab = pd.concat([self.__tab, self.__nul], axis=1)
                    self.__tab.columns = COL_TAG
                except:
                    if code_new != code:
                        raise ValueError(f'Code does not match ({code_new} is not {code}).')
                    raise RuntimeError(f'Fail to load Net Value data: {sys.exc_info()[1].args}')
            else:
                raise ValueError(f'Asset type [{typ}] is not supported.')
        elif val is not None:
            self.__tab = val
        if txn is not None and self.__tab.index.size > 0 and txnTab().isValid(txn):
            self.__tab.iloc[:, COL_HA:] = self.__nul
            txnShr = txn.iloc[:, TXN_COL_BS].fillna(0.) - txn.iloc[:, TXN_COL_SS].fillna(0.)
            row_HS = 0
            row_HP = 0
            for i in range(txn.index.size - 1, -1, -1):
                df = self.__tab.loc[self.__tab.iloc[:, COL_DT] == txn.iat[i, TXN_COL_DT]]
                if df.index.size == 0:
                    raise ValueError('Transaction date does not exist.', {(TXN_COL_DT, i, 1, 1)})
                self.__tab.iloc[row_HS:df.index[-1] + 1, COL_HA] = self.__tab.iloc[row_HS:df.index[-1] + 1, COL_NV] \
                    * (txn.iat[i, TXN_COL_HS] * df.iat[0, COL_UV] / df.iat[0, COL_NV])
                self.__tab.iat[df.index[-1], COL_TS] = txnShr.iat[i]
                row_HS = df.index[-1] + 1
                if txnShr.iat[i] > 0:
                    self.__tab.iloc[row_HP:df.index[-1] + 1, COL_HP] = self.__tab.iloc[row_HP:df.index[-1] + 1, COL_NV] - self.__tab.iloc[row_HP:df.index[-1] + 1, COL_UV] + txn.iat[i, TXN_COL_HP]
                    row_HP = df.index[-1] + 1
                elif not txn.iat[i, TXN_COL_HS]:
                    row_HP = df.index[-1] + 1
        return

    def get_code(self) -> str:
        return self.__code

    def get_name(self) -> str:
        return self.__name

    def table(self, group: str | None = None, txn: pd.DataFrame | None = None, val: pd.DataFrame | None = None) -> pd.DataFrame:
        if not (group is None and txn is None and val is None):
            self.__update(group, txn, val)
        return self.__tab

class valTabMod(valTab, basTabMod):
    __err_sig = Signal(tuple)
    def __init__(self, group: str | None = None, txn: pd.DataFrame | None = None, val: pd.DataFrame | None = None) -> None:
        try:
            valTab.__init__(self, group, txn, val)
            self.__tab = valTab.table(self)
            basTabMod.__init__(self, self.__tab)
        except:
            self.__tab = valTab.table(self)
            basTabMod.__init__(self, self.__tab)
            self.__err_sig.emit(sys.exc_info()[1].args)
        self.view.setColumnHidden(COL_HP, True)
        self.view.setColumnHidden(COL_TS, True)
        self.view.setMinimumWidth(500)
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
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
            if col == COL_DT and type(v) is pd.Timestamp:
                return v.strftime(r'%Y/%m/%d')
            elif col == COL_HA:
                return f'{v:,.2f}'
            else:
                return f'{v:,.4f}'
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_DT:
                return int(Qt.AlignCenter)
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return basTabMod.data(self, index, role)

    def table(self, group: str | None = None, txn: pd.DataFrame | None = None, val: pd.DataFrame | None = None) -> pd.DataFrame:
        if not (group is None and txn is None and val is None):
            try:
                self.__tab = valTab.table(self, group, txn, val)
            except:
                self.__err_sig.emit(sys.exc_info()[1].args)
            self.beginResetModel()
            basTabMod.table(self, self.__tab)
            self.endResetModel()
        return self.__tab
    
    def get_signal(self) -> Signal:
        return self.__err_sig


if __name__ == '__main__':
    app = QApplication()
    txn = txnTab()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    val = valTabMod('F519697', txn.table())
    val.show()
    print(val.get_code())
    print(val.get_name())
    print(val.table())
    app.exec()
