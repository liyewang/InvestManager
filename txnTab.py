from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QContextMenuEvent
from pandas import Timestamp, concat, to_numeric, to_datetime
from sys import exc_info
from db import *
from basTab import *
from dfIO import *

TAG_DT = 'Date'
TAG_BA = 'Buying Amount'
TAG_BS = 'Buying Share'
TAG_SA = 'Selling Amount'
TAG_SS = 'Selling Share'
TAG_DA = 'Dividend Amount'
TAG_DS = 'Dividend Share'
TAG_HS = 'Holding Share'
TAG_HP = 'Holding Price'
TAG_RR = 'Rate of Return'

COL_DT = 0
COL_BA = 1
COL_BS = 2
COL_SA = 3
COL_SS = 4
COL_DA = 5
COL_DS = 6
COL_HS = 7
COL_HP = 8
COL_RR = 9

COL_TAG = [
    TAG_DT,
    TAG_BA,
    TAG_BS,
    TAG_SA,
    TAG_SS,
    TAG_DA,
    TAG_DS,
    TAG_HS,
    TAG_HP,
    TAG_RR,
]

COL_TYP = {
    TAG_DT: 'datetime64[ns]',
    TAG_BA: 'float64',
    TAG_BS: 'float64',
    TAG_SA: 'float64',
    TAG_SS: 'float64',
    TAG_DA: 'float64',
    TAG_DS: 'float64',
    TAG_HS: 'float64',
    TAG_HP: 'float64',
    TAG_RR: 'float64',
}

TXN_DIGITS = 2

def getAmtMat(tab: DataFrame) -> DataFrame:
    df = tab.copy()
    rows = df.index.size
    AmtMat = DataFrame(data=0, index=range(rows), columns=range(rows), dtype='float64')
    row_0 = 0
    for col in range(rows):
        if df.iat[col, COL_SS] != 0:
            SelShrRes = df.iat[col, COL_SS]
            for row in range(row_0, col):
                BuyShr = df.iat[row, COL_BS]
                if BuyShr > 0:
                    if SelShrRes > BuyShr:
                        AmtMat.iat[row, col] = df.iat[row, COL_BA]
                        SelShrRes -= BuyShr
                        row_0 = row + 1
                    else:
                        BuyAmtExp = df.iat[row, COL_BA] * SelShrRes / BuyShr
                        AmtMat.iat[row, col] = BuyAmtExp
                        df.iat[row, COL_BA] -= BuyAmtExp
                        df.iat[row, COL_BS] -= SelShrRes
                        row_0 = row
                        break
        elif df.iat[col, COL_DS] != 0:
            DivShr = df.iat[col, COL_DS]
            BuyShrSum = df.iloc[row_0:col, COL_BS].sum()
            if df.iat[col, COL_DA] == 0:
                df.iloc[row_0:col, COL_BS] *= DivShr / BuyShrSum + 1
            else:
                BuyAmtExp = df.iloc[row_0:col, COL_BA] * (DivShr / (BuyShrSum + DivShr))
                AmtMat.iloc[row_0:col, col] = BuyAmtExp
                df.iloc[row_0:col, COL_BA] -= BuyAmtExp
    return AmtMat

def getAmtRes(df: DataFrame, AmtMat: DataFrame, Rate: float) -> float:
    if Rate < -1:
        RateSign = -1
    else:
        RateSign = 1
    AmtRes = 0.
    for col in df[(df[TAG_SS] != 0) | (df[TAG_DA] != 0)].index:
        AmtRes += df.iat[col, COL_SA] + df.iat[col, COL_DA]
        for row in AmtMat[AmtMat[col] != 0].index:
            if AmtMat.iat[row, col] != 0:
                AmtRes -= AmtMat.iat[row, col] * (RateSign * abs(1 + Rate) ** ((df.iat[col, COL_DT] - df.iat[row, COL_DT]).days / 365))
            elif df.iat[row, COL_BA] != 0:
                break
    return AmtRes

class Tab:
    def __init__(self, data: db | DataFrame | None = None, group: str | None = None) -> None:
        self.__tab = DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = None
        self.__grp = None
        self.__avg = NAN
        self.config()
        if type(data) is db and type(group) is str:
            self.load(data, group)
        elif type(data) is DataFrame and group is None:
            self.__calcTab(data)
        elif not (data is None and group is None):
            raise TypeError('Unsupported data type.')
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

        v = data[TAG_DT].isna()
        if data.dtypes[COL_DT] != 'datetime64[ns]' or v.any():
            for row in v[v].index:
                rects.add((COL_DT, row, 1, 1))
            for row in range(rows):
                if type(data.iat[row, COL_DT]) is not Timestamp:
                    rects.add((COL_DT, row, 1, 1))
            if rects:
                raise TypeError('Date type is required.', rects)
            else:
                raise TypeError('Date type is required.', {(COL_DT, 0, 1, rows)})

        for col in range(COL_BA, len(COL_TAG)):
            if data.dtypes[col] != 'float64':
                for row in range(rows):
                    if type(data.iat[row, col]) is not float:
                        rects.add((col, row, 1, 1))
                if rects:
                    raise ValueError('Numeric type is required.', rects)
                else:
                    raise ValueError('Numeric type is required.', {(col, 0, 1, rows)})
            v = data.iloc[:, col].isin([float('inf')])
            for row in v[v].index:
                rects.add((col, row, 1, 1))
            if rects:
                raise ValueError('A finite number is required.', rects)

        s = sum([data[t].isna().astype('int') for t in (TAG_BS, TAG_SS, TAG_DS)])
        v = s != 2
        for row in v[v].index:
            rects.add((COL_BA, row, COL_DS - COL_DT, 1))
        if rects:
            raise ValueError('Single transaction data is required.', rects)

        v = (~data[TAG_DA].isna()) & data[TAG_DS].isna()
        for row in v[v].index:
            rects.add((COL_DA, row, COL_DS - COL_SS, 1))
        if rects:
            raise ValueError('Share data is missing.', rects)

        for col in {(TAG_BA, TAG_BS), (TAG_SA, TAG_SS)}:
            v = data[col[0]].isna() ^ data[col[1]].isna()
            for row in v[v].index:
                rects.add((col[0], row, 2, 1))
            if rects:
                raise ValueError('Amount or Share data is missing.', rects)
            v = data[col[1]] <= 0
            for row in v[v].index:
                rects.add((col[1], row, 1, 1))
            if rects:
                raise ValueError('Share data must be positive.', rects)
            v = (data[col[0]] / data[col[1]]).isin([float('inf')])
            for row in v[v].index:
                rects.add((col[0], row, 2, 1))
            if rects:
                raise ValueError('Amount/Share must be finite.', rects)

        if not data[TAG_DT].equals(data[TAG_DT].sort_values(ignore_index=True)):
            dt_0 = to_datetime(0)
            for row in range(rows):
                dt = to_datetime(data.iat[row, COL_DT])
                if dt < dt_0:
                    raise ValueError('Dates must be ascending.', {(COL_DT, row, 1, 1)})
                dt_0 = dt

        return

    def __calcTab(self, data: DataFrame) -> None:
        self.__verify(data)
        rows = data.index.size
        _data = data.copy()
        df = data.fillna(0.)

        Shr = df[TAG_DS].copy()
        Shr[~data[TAG_DA].isna()] = 0
        Shr += df[TAG_BS] - df[TAG_SS]
        HoldShrRes = 0.
        Amt = 0.
        HoldMat = DataFrame(index=range(rows), columns=range(2), dtype='float64')
        for row in range(rows):
            HoldShrRes = round(HoldShrRes + Shr.iat[row], TXN_DIGITS)
            HoldMat.iat[row, 0] = HoldShrRes
            assert HoldShrRes >=0, ('Selling share exceeded.', {(COL_SS, row, 1, 1)})
            if df.iat[row, COL_BS]:
                Amt += df.iat[row, COL_BA]
            elif df.iat[row, COL_SS]:
                Amt *= HoldShrRes / (df.iat[row, COL_SS] + HoldShrRes)
            elif df.iat[row, COL_DA]:
                Amt -= df.iat[row, COL_DA]
                assert Amt > 0, ('Dividend amount exceeded.', {(COL_DA, row, 1, 1)})
            if HoldShrRes:
                HoldMat.iat[row, 1] = Amt / HoldShrRes
        _data[[TAG_HS, TAG_HP]] = HoldMat
        df[[TAG_HS, TAG_HP]] = HoldMat.fillna(0.)

        AmtMat = getAmtMat(df)

        RateMat = Series(index=range(rows), dtype='float64')
        RateSz = 0
        AmtResPrev = 0.
        RatePrev = 0.
        for col in df[(df[TAG_SS] != 0) | (df[TAG_DA] != 0)].index:
            Rate = df.iat[col, COL_RR]
            for count in range(self.__MaxCount):
                if Rate < -1:
                    RateSign = -1
                else:
                    RateSign = 1
                AmtRes = df.iat[col, COL_SA] + df.iat[col, COL_DA]
                for row in AmtMat[AmtMat[col] != 0].index:
                    if AmtMat.iat[row, col]:
                        AmtRes -= AmtMat.iat[row, col] * (RateSign * abs(1 + Rate) ** ((df.iat[col, COL_DT] - df.iat[row, COL_DT]).days / 365))
                    elif df.iat[row, COL_BA]:
                        break
                if abs(AmtRes) < self.__MaxAmtResErr:
                    count = 0
                    break
                elif AmtRes == AmtResPrev or Rate == RatePrev:
                    RateNew = Rate + self.__dRate
                else:
                    RateNew = AmtRes / (AmtResPrev - AmtRes) * (Rate - RatePrev) + Rate
                RatePrev = Rate
                Rate = RateNew
                AmtResPrev = AmtRes
            if count > 0:
                raise RuntimeError(f'Cannot find the Rate of Return in {self.__MaxCount} rounds.')
            RateMat.iat[col] = Rate
            RateSz += 1
        _data[TAG_RR] = RateMat

        if RateSz == 0:
            _avg = NAN
        elif RateSz == 1:
            _avg = Rate
        elif RateSz > 1:
            AmtResPrev = 0.
            RatePrev = 0.
            if isna(self.__avg):
                Rate = 0.
            else:
                Rate = self.__avg
            for count in range(self.__MaxCount):
                AmtRes = getAmtRes(df, AmtMat, Rate)
                if abs(AmtRes) < self.__MaxAmtResErr:
                    count = 0
                    break
                elif AmtRes == AmtResPrev or Rate == RatePrev:
                    RateNew = Rate + self.__dRate
                else:
                    RateNew = AmtRes / (AmtResPrev - AmtRes) * (Rate - RatePrev) + Rate
                RatePrev = Rate
                Rate = RateNew
                AmtResPrev = AmtRes
            if count > 0:
                raise RuntimeError(f'Cannot find the Average Rate of Return in {self.__MaxCount} rounds.')
            _avg = Rate
        if self.__db is not None:
            self.__db.set(self.__grp, KEY_TXN, _data)
        self.__tab = _data
        self.__avg = _avg
        return

    def config(self, MaxCount=4096, dRate=0.1, MaxAmtResErr=1e-10) -> None:
        MaxCount = to_numeric(MaxCount, errors='coerce')
        if MaxCount <= 0:
            raise ValueError('MaxCount must be positive')
        self.__MaxCount = MaxCount
        dRate = to_numeric(dRate, errors='coerce')
        if dRate <= 0 or dRate >= 1:
            raise ValueError('dRate must be in the range of (0,1).')
        self.__dRate = dRate
        MaxAmtResErr = to_numeric(MaxAmtResErr, errors='coerce')
        if MaxAmtResErr <= 0:
            raise ValueError('MaxAmtResErr must be positive.')
        self.__MaxAmtResErr = MaxAmtResErr
        return

    def isValid(self, data: DataFrame) -> bool:
        try:
            self.__verify(data)
        except:
            return False
        return True

    def load(self, data: db, group: str, update: bool = True) -> DataFrame:
        tab = data.get(group, KEY_TXN)
        if tab is None:
            tab = DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = data
        self.__grp = group
        if update:
            self.__calcTab(tab)
        else:
            self.__tab = tab
        return self.__tab.copy()

    def table(self, data: DataFrame | None = None) -> DataFrame:
        if data is not None:
            self.__calcTab(data)
        return self.__tab.copy()

    def avgRate(self, data: DataFrame | None = None) -> float:
        if data is not None:
            self.__calcTab(data)
        return self.__avg

    def import_table(self, file: str, update: bool = True) -> DataFrame:
        tab = dfImport(file).astype(COL_TYP)
        if update:
            self.__calcTab(tab)
        else:
            self.__tab = tab
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
        self.setAlternatingRowColors(True)
        self.setAutoScroll(False)
        self.__func_del = None
        return

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        idx = self.indexAt(event.pos())
        menu = QMenu(self)
        act_del = menu.addAction('Delete')
        action = menu.exec(event.globalPos())
        print(action.text())
        if action == act_del:
            print(idx.row())
            self.__func_del(idx.row())
        return super().contextMenuEvent(event)

    def setDelete(self, func) -> None:
        self.__func_del = func
        return

class Mod(Tab, basMod):
    __txn_update = Signal()
    def __init__(self, data: db | DataFrame | None = None, group: str | None = None) -> None:
        Tab.__init__(self)
        basMod.__init__(self, Tab.table(self), View)
        self.__nul = DataFrame(NAN, [0], COL_TAG).astype(COL_TYP)
        if type(data) is db and type(group) is str:
            self.load(data, group)
        elif type(data) is DataFrame and group is None:
            self.__update(data)
        elif data is None and group is None:
            self.__update(Tab.table(self))
        else:
            raise TypeError('Unsupported data type.')
        self.view.setMinimumWidth(866)
        self.view.setDelete(self.delete)
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if index.column() < COL_HS:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index: QModelIndex, role: int) -> str | None:
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            v = self.__tab.iat[index.row(), index.column()]
            if isna(v):
                return ''
            if type(v) is str:
                return v
            col = index.column()
            if col == COL_DT and type(v) is Timestamp:
                return v.strftime(r'%Y/%m/%d')
            elif col == COL_HP:
                return f'{v:,.4f}'
            elif col == COL_RR:
                return f'{v * 100:,.2f}%'
            else:
                return f'{v:,.2f}'
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_DT:
                return int(Qt.AlignCenter)
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return basMod.data(self, index, role)

    def setData(self, index: QModelIndex, value: str, role: int = Qt.EditRole) -> bool:
        if index.isValid() and role == Qt.EditRole:
            if index.column() == COL_DT:
                self.__tab.iat[index.row(), index.column()] = to_datetime(value, errors='ignore')
            else:
                if value == '':
                    self.__tab.iat[index.row(), index.column()] = NAN
                else:
                    try:
                        value = round(float(value.replace(',', '')), TXN_DIGITS)
                    finally:
                        self.__tab.iat[index.row(), index.column()] = value
            self.__update(scroll=False)
            return True
        return False

    def __update(self, data: DataFrame | None = None, scroll: bool = True) -> None:
        self.error = ()
        self.setColor()
        if data is not None:
            self.__tab = data.copy()
        rows = self.__tab.index.size
        if rows:
            row = 0
            while row < rows - 1:
                if self.__tab.iloc[row, :COL_HS].isna().all():
                    self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
                    rows = self.__tab.index.size
                else:
                    row += 1
            if not self.__tab.iloc[-1].isna().all():
                df = self.__tab.sort_values([TAG_DT, TAG_SS], ignore_index=True)
                if (self.__tab[TAG_DT] != df[TAG_DT]).any() and self.isValid(df):
                    self.__tab = df
                    mute = False
                elif data is not None:
                    mute = False
                else:
                    mute = True
                try:
                    self.__tab = Tab.table(self, self.__tab)
                except:
                    v = exc_info()[1].args
                    if mute and len(v) >= 2 and type(v[1]) is set:
                        for e in v[1]:
                            if type(e) is tuple and len(e) == 4 and e[1] != rows - 1:
                                mute = False
                    if mute:
                        if v[0] != 'Date data must be ascending.':
                            self._raise(v, msgBox=False)
                    else:
                        basMod.table(self, self.__tab)
                        self._raise(v)
                else:
                    self.__tab = concat([self.__tab, self.__nul], ignore_index=True)
            else:
                try:
                    self.__tab.iloc[:-1] = Tab.table(self, self.__tab.iloc[:-1])
                except:
                    basMod.table(self, self.__tab)
                    self._raise(exc_info()[1].args)
        else:
            self.__tab = self.__nul.copy()
        if not self.error:
            basMod.table(self, self.__tab)
            if scroll:
                self.view.scrollToBottom()
            self.__txn_update.emit()
        return

    def load(self, data: db, group: str) -> DataFrame | None:
        try:
            tab = Tab.load(self, data, group, False)
        except:
            self._raise(exc_info()[1].args)
            return None
        else:
            self.__update(tab)
        return Tab.table(self)

    def delete(self, row: int) -> None:
        self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
        self.__update(scroll=False)
        return

    def table(self, data: DataFrame | None = None, view: bool = False) -> DataFrame:
        if data is not None:
            self.__update(data)
        if view:
            return self.__tab.copy()
        return Tab.table(self)

    def import_table(self, file: str) -> DataFrame | None:
        try:
            tab = Tab.import_table(self, file, False)
        except:
            self._raise(exc_info()[1].args)
            return None
        else:
            self.__update(tab)
        return Tab.table(self)

    def export_table(self, file: str, data: bool = True) -> None:
        try:
            Tab.export_table(self, file, data)
        except:
            self._raise(exc_info()[1].args)
        return

    def set_update(self, upd_func) -> None:
        self.__txn_update.connect(upd_func)
        return

if __name__ == '__main__':
    d = db(DB_PATH)
    group = list(d.get(key=KEY_INF).keys())[0]

    app = QApplication()
    t = Mod(d, group)
    t.show()
    t.view.scrollToBottom()
    print(t)
    print(t.avgRate())
    app.exec()

    # t = Tab(d, group)
    # print(t)
    # print(t.avgRate())

    # count = 0
    # for grp, tab in d.get(key=KEY_TXN).items():
    #     assert type(tab) is DataFrame
    #     if tab.columns.tolist() == [TAG_DT,TAG_BA,TAG_BS,TAG_SA,TAG_SS,TAG_HS,TAG_HP,TAG_RR]:
    #         tab.insert(COL_DA, TAG_DA, NAN)
    #         tab.insert(COL_DS, TAG_DS, NAN)
    #         v = tab[TAG_BA].isna() & (~tab[TAG_BS].isna())
    #         for row in v[v].index:
    #             tab.loc[row, TAG_DS] = tab.loc[row, TAG_BS]
    #             tab.loc[row, TAG_BS] = NAN
    #         d.set(grp, KEY_TXN, tab)

    # d.save()
