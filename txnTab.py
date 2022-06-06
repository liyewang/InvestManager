import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QContextMenuEvent
import sys
from db import *
from basTab import *

TAG_DT = 'Date'
TAG_BA = 'Buying Amount'
TAG_BS = 'Buying Share'
TAG_SA = 'Selling Amount'
TAG_SS = 'Selling Share'
TAG_HS = 'Holding Share'
TAG_HP = 'Holding Price'
TAG_RR = 'Rate of Return'

COL_DT = 0
COL_BA = 1
COL_BS = 2
COL_SA = 3
COL_SS = 4
COL_HS = 5
COL_HP = 6
COL_RR = 7

COL_TAG = [
    TAG_DT,
    TAG_BA,
    TAG_BS,
    TAG_SA,
    TAG_SS,
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
    TAG_HS: 'float64',
    TAG_HP: 'float64',
    TAG_RR: 'float64',
}

def getAmtMat(df: pd.DataFrame) -> pd.DataFrame:
    rows = df.index.size
    Shr = df.iloc[:, COL_BS] - df.iloc[:, COL_SS]
    AmtMat = pd.DataFrame(data=0, index=range(rows), columns=range(rows), dtype=float)
    row_0 = 0
    BuyShrExp = 0
    ShrBal = 0
    for col in range(rows):
        ShrBal += Shr.iat[col]
        if ShrBal < 0:
            raise ValueError(f'Share balance cannot be negative ({ShrBal})', {(COL_SS, col, 1, 1)})
        elif df.iat[col, COL_SS] > 0:
            SelShrRes = df.iat[col, COL_SS]
            for row in range(row_0, col + 1):
                BuyShr = df.iat[row, COL_BS]
                if BuyShr > 0:
                    if SelShrRes > BuyShr - BuyShrExp:
                        BuyShrExp = BuyShr - BuyShrExp
                        AmtMat.iat[row, col] = df.iat[row, COL_BA] * BuyShrExp / BuyShr
                        SelShrRes -= BuyShrExp
                        BuyShrExp = 0
                        row_0 = row + 1
                    elif SelShrRes == BuyShr - BuyShrExp:
                        AmtMat.iat[row, col] = df.iat[row, COL_BA] * SelShrRes / BuyShr
                        BuyShrExp = SelShrRes
                        row_0 = row + 1
                        break
                    else:
                        AmtMat.iat[row, col] = df.iat[row, COL_BA] * SelShrRes / BuyShr
                        BuyShrExp += SelShrRes
                        row_0 = row
                        break
    return AmtMat

def getAmtRes(df: pd.DataFrame, AmtMat: pd.DataFrame, Rate: float) -> float:
    if Rate < -1:
        RateSign = -1
    else:
        RateSign = 1
    AmtRes = 0.
    for col in df[df.iloc[:, COL_SS] > 0].index:
        AmtRes += df.iat[col, COL_SA]
        for row in AmtMat[AmtMat.iloc[:, col] != 0].index:
            if AmtMat.iat[row, col] != 0:
                AmtRes -= AmtMat.iat[row, col] * (RateSign * abs(1 + Rate) ** ((df.iat[col, COL_DT] - df.iat[row, COL_DT]).days / 365))
            elif df.iat[row, COL_BA] != 0:
                break
    return AmtRes

class Tab:
    def __init__(self, data: pd.DataFrame | None = None) -> None:
        self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = None
        self.__grp = None
        self.__avg = NAN
        self.config()
        if data is not None:
            self.__calcTab(data)
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
        v = pd.Series(data.index != range(rows))
        if v.any():
            raise ValueError('Index error.', {(-1, v[v].index[0], 1, 1)})
        df = data.fillna(0.)

        if df.dtypes[COL_DT] != 'datetime64[ns]':
            for row in range(rows):
                if type(df.iat[row, COL_DT]) is not pd.Timestamp:
                    rects.add((COL_DT, row, 1, 1))
            if rects:
                raise TypeError('Date type is required.', rects)
            else:
                raise TypeError('Date type is required.', {(COL_DT, 0, 1, rows)})

        for col in range(COL_BA, len(COL_TAG)):
            if df.dtypes[col] != 'float64':
                for row in range(rows):
                    if type(df.iat[row, col]) is not float:
                        rects.add((col, row, 1, 1))
                if rects:
                    raise ValueError('Numeric type is required.', rects)
                else:
                    raise ValueError('Numeric type is required.', {(col, 0, 1, rows)})
            v = df.iloc[:, col].isin([float('inf'), NAN])
            for row in v[v].index:
                rects.add((col, row, 1, 1))
            if rects:
                raise ValueError('A finite number is required.', rects)

        v = ((df.iloc[:, COL_BA] != 0) | (df.iloc[:, COL_BS] != 0)) & ((df.iloc[:, COL_SA] != 0) | (df.iloc[:, COL_SS] != 0))
        for row in v[v].index:
            rects.add((COL_BA, row, 4, 1))
        if rects:
            raise ValueError('Buying and Selling data must be in separated rows.', rects)

        for col in {COL_BS, COL_SS}:
            v = df.iloc[:, col] < 0
            for row in v[v].index:
                rects.add((col, row, 1, 1))
            if rects:
                raise ValueError('Negative Share is not allowed.', rects)

        for col in {(COL_BA, COL_BS), (COL_SA, COL_SS)}:
            v = data.iloc[:, col[0]].isna() & ~data.iloc[:, col[1]].isna()
            for row in v[v].index:
                rects.add((col[0], row, 1, 1))
            if rects:
                raise ValueError('Amount data is missing.', rects)
            v = (df.iloc[:, col[0]] / df.iloc[:, col[1]]).isin([float('inf')])
            for row in v[v].index:
                rects.add((col[0], row, 2, 1))
            if rects:
                raise ValueError('Amount/Share must be finite.', rects)

        v = (df.iloc[:, COL_BS] == 0) & (df.iloc[:, COL_SS] == 0)
        for row in v[v].index:
            rects.add((COL_BA, row, COL_SS - COL_DT, 1))
        if rects:
            raise ValueError('Transaction data is required.', rects)

        if (df.iloc[:, COL_DT].sort_values(ignore_index=True) != df.iloc[:, COL_DT]).any():
            dt_0 = pd.to_datetime(0)
            for row in range(rows):
                dt = pd.to_datetime(df.iat[row, COL_DT])
                if dt < dt_0:
                    raise ValueError('Date data must be ascending.', {(COL_DT, row, 1, 1)})
                dt_0 = dt

        return

    def __calcTab(self, data: pd.DataFrame) -> None:
        self.__verify(data)
        rows = data.index.size
        _data = data.copy()
        df = data.fillna(0.)

        Shr = df.iloc[:, COL_BS] - df.iloc[:, COL_SS]
        HoldShrRes = 0
        Amt = 0
        HoldMat = pd.DataFrame(index=range(rows), columns=range(2), dtype=float)
        for row in range(rows):
            HoldShrRes += Shr.iat[row]
            HoldMat.iat[row, 0] = HoldShrRes
            if HoldShrRes < 0:
                _data.iloc[:, COL_HS:COL_RR] = HoldMat
                raise ValueError('Overselling is not allowed.', {(COL_SS, row, 1, 1)})
            if df.iat[row, COL_BS]:
                Amt += df.iat[row, COL_BA]
            else:
                Amt *= HoldShrRes / (df.iat[row, COL_SS] + HoldShrRes)
            if HoldShrRes:
                HoldMat.iat[row, 1] = Amt / HoldShrRes
        _data.iloc[:, COL_HS:COL_RR] = HoldMat
        df.iloc[:, COL_HS:COL_RR] = HoldMat.fillna(0.)

        AmtMat = getAmtMat(df)

        RateMat = pd.Series(index=range(rows), dtype=float)
        RateSz = 0
        AmtResPrev = 0.
        RatePrev = 0.
        for col in df[df.iloc[:, COL_SS] > 0].index:
            Rate = df.iat[col, COL_RR]
            for count in range(self.__MaxCount):
                if Rate < -1:
                    RateSign = -1
                else:
                    RateSign = 1
                AmtRes = df.iat[col, COL_SA]
                for row in AmtMat[AmtMat.iloc[:, col] != 0].index:
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
        _data.iloc[:, COL_RR] = RateMat

        if RateSz == 0:
            _avg = NAN
        elif RateSz == 1:
            _avg = Rate
        elif RateSz > 1:
            AmtResPrev = 0.
            RatePrev = 0.
            if pd.isna(self.__avg):
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
            self.__db.save()
        self.__tab = _data
        self.__avg = _avg
        return

    def config(self, MaxCount=256, dRate=0.1, MaxAmtResErr=1e-10) -> None:
        MaxCount = pd.to_numeric(MaxCount, errors='coerce')
        if MaxCount <= 0:
            raise ValueError('MaxCount must be positive')
        self.__MaxCount = MaxCount
        dRate = pd.to_numeric(dRate, errors='coerce')
        if dRate <= 0 or dRate >= 1:
            raise ValueError('dRate must be in the range of (0,1).')
        self.__dRate = dRate
        MaxAmtResErr = pd.to_numeric(MaxAmtResErr, errors='coerce')
        if MaxAmtResErr <= 0:
            raise ValueError('MaxAmtResErr must be positive.')
        self.__MaxAmtResErr = MaxAmtResErr
        return

    def isValid(self, data: pd.DataFrame) -> bool:
        try:
            self.__verify(data)
        except:
            return False
        return True

    def load(self, data: db, group: str, update: bool = True) -> pd.DataFrame:
        tab = data.get(group, KEY_TXN)
        if tab is None:
            tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = data
        self.__grp = group
        if update:
            self.__calcTab(tab)
        else:
            self.__tab = tab
        return self.__tab.copy()

    def table(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        if data is not None:
            self.__calcTab(data)
        return self.__tab.copy()

    def avgRate(self, data: pd.DataFrame | None = None) -> float:
        if data is not None:
            self.__calcTab(data)
        return self.__avg

    def read_csv(self, file: str, update: bool = True) -> pd.DataFrame:
        tab = pd.read_csv(file).astype(COL_TYP)
        if update:
            self.__calcTab(tab)
        else:
            self.__tab = tab
        return self.__tab.copy()

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
        if action == act_del:
            print('Delete')
            print(idx.row())
            if self.__func_del:
                self.__func_del(idx.row())
        return super().contextMenuEvent(event)

    def setDelete(self, func) -> None:
        self.__func_del = func
        return
    
class Mod(Tab, basMod):
    __txn_update = Signal()
    def __init__(self, data: pd.DataFrame | None = None) -> None:
        Tab.__init__(self)
        basMod.__init__(self, Tab.table(self), View)
        self.__nul = pd.DataFrame(NAN, [0], COL_TAG).astype(COL_TYP)
        if data is None:
            self.__update(Tab.table(self))
        else:
            self.__update(data)
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
            if pd.isna(v):
                return ''
            if type(v) is str:
                return v
            col = index.column()
            if col == COL_DT and type(v) is pd.Timestamp:
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

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if index.isValid() and role == Qt.EditRole:
            if value == '':
                value = 'nan'
            if index.column() == COL_DT:
                self.__tab.iat[index.row(), index.column()] = pd.to_datetime(value, errors='ignore')
            else:
                try:
                    self.__tab.iat[index.row(), index.column()] = float(value)
                except:
                    self.__tab.iat[index.row(), index.column()] = value
            self.__update(scroll=False)
            return True
        return False

    def __update(self, data: pd.DataFrame | None = None, scroll: bool = True) -> None:
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
                if (self.__tab.iloc[:, COL_DT] != df.iloc[:, COL_DT]).any() and self.isValid(df):
                    self.__tab = df
                    mute = False
                elif data is not None:
                    mute = False
                else:
                    mute = True
                try:
                    self.__tab = Tab.table(self, self.__tab)
                except:
                    v = sys.exc_info()[1].args
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
                    self.__tab = pd.concat([self.__tab, self.__nul], ignore_index=True)
            else:
                try:
                    self.__tab.iloc[:-1] = Tab.table(self, self.__tab.iloc[:-1])
                except:
                    basMod.table(self, self.__tab)
                    self._raise(sys.exc_info()[1].args)
        else:
            self.__tab = self.__nul.copy()
        if not self.error:
            basMod.table(self, self.__tab)
            if scroll:
                self.view.scrollToBottom()
            self.__txn_update.emit()
        return

    def load(self, data: db, group: str) -> pd.DataFrame | None:
        try:
            tab = Tab.load(self, data, group, False)
        except:
            self._raise(sys.exc_info()[1].args)
            return None
        else:
            self.__update(tab)
        return Tab.table(self)

    def delete(self, row: int) -> None:
        self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
        self.__update(scroll=False)
        return

    def table(self, data: pd.DataFrame | None = None, view: bool = False) -> pd.DataFrame:
        if data is not None:
            self.__update(data)
        if view:
            return self.__tab.copy()
        return Tab.table(self)

    def read_csv(self, file: str) -> pd.DataFrame | None:
        try:
            tab = Tab.read_csv(self, file, False)
        except:
            self._raise(sys.exc_info()[1].args)
            return None
        else:
            self.__update(tab)
        return Tab.table(self)

    def get_signal(self) -> Signal:
        return self.__txn_update

if __name__ == '__main__':
    d = db(R'C:\Users\51730\Desktop\dat')
    group = list(d.get(key=KEY_INF).keys())[0]

    app = QApplication()
    t = Mod()
    t.show()
    t.load(d, group)
    # t.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    print(group)
    print(t.table())
    print(t.avgRate())
    app.exec()
