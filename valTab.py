import requests
import pandas as pd
import sys
from PySide6.QtCore import Signal
from tabView import *
from txnTab import (
    txnTab,
    COL_DT as TXN_COL_DT,
    COL_BA as TXN_COL_BA,
    COL_SA as TXN_COL_SA,
    COL_HS as TXN_COL_HS,
)

URL_API = 'http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode='
HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'}

TAG_DT_RAW = 'fld_enddate'

TAG_DT = 'Date'
TAG_UV = 'Unit Net Value'
TAG_NV = 'Net Value'
TAG_HA = 'Holding Amount'
TAG_TA = 'Transaction Amount'

COL_DT = 0
COL_UV = 1
COL_NV = 2
COL_HA = 3
COL_TA = 4

COL_TAG = [
    TAG_DT,
    TAG_UV,
    TAG_NV,
    TAG_HA,
    TAG_TA,
]

class valTab:
    def __init__(self, code: str | None = None, txn: pd.DataFrame | None = None) -> None:
        self.__code = ''
        self.__name = ''
        self.__tab = pd.DataFrame(columns=COL_TAG)
        self.__zeros = pd.DataFrame(columns=COL_TAG[COL_HA:])
        self.__update(code, txn)
        return

    def __update(self, code: str | None = None, txn: pd.DataFrame | None = None) -> None:
        if code is not None:
            try:
                df = pd.read_xml(requests.get(f'{URL_API}{code}', headers=HEADER).text)
                code_new = f'{df.iat[0, 0]:06.0f}'
                if code_new != code:
                    raise ValueError(f'Code does not match ({code_new} is not {code}).')
                self.__code = code_new
                self.__name = df.iat[1, 1]
                self.__tab = df.iloc[2:, 2:5].astype({TAG_DT_RAW:'datetime64[ns]'}).drop_duplicates(ignore_index=True).sort_values(TAG_DT_RAW, ascending=False, ignore_index=True)
                rows = self.__tab.index.size
                self.__zeros = pd.DataFrame(0., index=range(rows), columns=COL_TAG[COL_HA:])
                self.__tab = pd.concat([self.__tab, self.__zeros], axis=1)
                self.__tab.columns = COL_TAG
            except:
                raise RuntimeError(f'Fail to load Net Value data: {sys.exc_info()[1].args}')
        if txn is not None and self.__tab.index.size > 0 and txnTab().isValid(txn):
            self.__tab.iloc[:, COL_HA:] = self.__zeros
            txnAmt = txn.iloc[:, TXN_COL_BA].fillna(0.) - txn.iloc[:, TXN_COL_SA].fillna(0.)
            row = 0
            for i in range(txn.index.size - 1, -1, -1):
                df = self.__tab.loc[self.__tab.iloc[:, COL_DT] == txn.iat[i, TXN_COL_DT]]
                if df.index.size == 0:
                    raise ValueError('Transaction date does not exist.', {(TXN_COL_DT, i, 1, 1)})
                self.__tab.iloc[row:df.index[-1] + 1, COL_HA] = self.__tab.iloc[row:df.index[-1] + 1, COL_NV] \
                    * (txn.iat[i, TXN_COL_HS] * df.iat[0, COL_UV] / df.iat[0, COL_NV])
                self.__tab.iat[df.index[-1], COL_TA] = txnAmt.iat[i]
                row = df.index[-1] + 1
        return

    def get_code(self) -> str:
        return self.__code

    def get_name(self) -> str:
        return self.__name

    def table(self, code: str | None = None, txn: pd.DataFrame | None = None) -> pd.DataFrame:
        if code is not None or txn is not None:
            self.__update(code, txn)
        return self.__tab

class valTabView(valTab, tabView):
    __err_sig = Signal(tuple)
    def __init__(self, code: str | None = None, txn: pd.DataFrame | None = None) -> None:
        try:
            valTab.__init__(self, code, txn)
            self.__tab = valTab.table(self).iloc[:, :COL_TA]
            tabView.__init__(self, self.__tab)
        except:
            self.__tab = valTab.table(self).iloc[:, :COL_TA]
            tabView.__init__(self, self.__tab)
            self.__err_sig.emit(sys.exc_info()[1].args)
        self.view.setMinimumWidth(500)
        return

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index: QModelIndex, role=Qt.ItemDataRole) -> str | None:
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
                return f'{v:.2f}'
            else:
                return f'{v:.4f}'
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_DT:
                return int(Qt.AlignCenter)
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return tabView.data(self, index, role)

    def table(self, code: str | None = None, txn: pd.DataFrame | None = None) -> pd.DataFrame:
        if code is not None or txn is not None:
            try:
                self.__tab = valTab.table(self, code, txn).iloc[:, :COL_TA]
            except:
                self.__err_sig.emit(sys.exc_info()[1].args)
            self.beginResetModel()
            tabView.table(self, self.__tab)
            self.endResetModel()
        return self.__tab
    
    def get_signal(self) -> Signal:
        return self.__err_sig


if __name__ == '__main__':
    app = QApplication()
    txn = txnTab()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    val = valTabView('519697', txn.table())
    val.show()
    print(val.get_code())
    print(val.get_name())
    print(val.table())
    app.exec()
