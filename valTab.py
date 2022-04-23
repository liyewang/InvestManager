import requests
import pandas as pd
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
from tabView import *
from txnTab import txnTab, COL_HS as TXN_COL_HS

URL_API = 'http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode='
HEADER = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'}

TAG_DT = 'Date'
TAG_UV = 'Unit Net Value'
TAG_NV = 'Net Value'
TAG_HA = 'Holding Amount'

COL_DT = 0
COL_UV = 1
COL_NV = 2
COL_HA = 3

COL_TAG = [
    TAG_DT,
    TAG_UV,
    TAG_NV,
    TAG_HA,
]

class valTab:
    def __init__(self, code: str, txn: pd.DataFrame | None = None) -> None:
        try:
            df = pd.read_xml(requests.get(f'{URL_API}{code}', headers=HEADER).text)
        except:
            self.__code = ''
            self.__name = ''
            self.__tab = pd.DataFrame(columns=COL_TAG)
            return
        self.__code = f'{df.iat[0, 0]:06.0f}'
        if self.__code != code:
            raise ValueError(f'Code does not match ({code} : {self.__code}).')
        self.__name = df.iat[1, 1]
        self.__tab = df.iloc[2:, 2:5].astype({'fld_enddate':'datetime64[ns]'}).drop_duplicates(ignore_index=True)
        rows = self.__tab.index.size
        self.__tab = pd.concat([self.__tab, pd.Series(0., index=range(rows))], axis=1)
        self.__tab.columns = COL_TAG
        self.table(txn)

    def code(self) -> str:
        return self.__code

    def name(self) -> str:
        return self.__name

    def table(self, txn: pd.DataFrame | None = None) -> pd.DataFrame:
        if txn is not None and txnTab().isValid(txn):
            row = 0
            for i in range(txn.index.size - 1, -1, -1):
                df = self.__tab.loc[self.__tab.iloc[:, COL_DT] == txn.iat[i, COL_DT]]
                self.__tab.iloc[row:df.index[-1] + 1, COL_HA] = self.__tab.iloc[row:df.index[-1] + 1, COL_NV] \
                    * (txn.iat[i, TXN_COL_HS] * df.iat[0, COL_UV] / df.iat[0, COL_NV])
                row = df.index[-1] + 1
        return self.__tab

class valTabView(valTab, tabView):
    def __init__(self, code: str, txn: pd.DataFrame | None = None) -> None:
        valTab.__init__(self, code, txn)
        self.__tab = valTab.table(self)
        tabView.__init__(self, self.__tab)

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

class valPlot(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.__fig = Figure(figsize=(5, 3))
        self.__canvas = FigureCanvas(self.__fig)
        llayout = QVBoxLayout()
        llayout.addWidget(self.__canvas)
        self.setLayout(llayout)


if __name__ == '__main__':
    app = QApplication()
    txn = txnTab()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    val = valTabView('519697', txn.table())
    val.show()
    plt.plot(val.table().iloc[:, COL_DT].tolist(), val.table().iloc[:, COL_UV].tolist(), val.table().iloc[:, COL_DT].tolist(), val.table().iloc[:, COL_NV].tolist())
    plt.show(block=False)
    print(val.code())
    print(val.name())
    print(val.table())
    app.exec()
