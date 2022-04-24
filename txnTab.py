import pandas as pd
from tabView import *
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Signal
import sys

TAG_DT = 'Date'
TAG_BA = 'Buying Amount'
TAG_BS = 'Buying Share'
TAG_SA = 'Selling Amount'
TAG_SS = 'Selling Share'
TAG_HS = 'Holding Share'
TAG_RR = 'Rate of Return'
TAG_HA = 'Holding Amount'
TAG_AR = 'Average Rate'
TAG_UV = 'Unit Net Value'
TAG_VL = 'Valuation'

COL_DT = 0
COL_BA = 1
COL_BS = 2
COL_SA = 3
COL_SS = 4
COL_HS = 5
COL_RR = 6

COL_TAG = [
    TAG_DT,
    TAG_BA,
    TAG_BS,
    TAG_SA,
    TAG_SS,
    TAG_HS,
    TAG_RR,
]

class txnTab:
    def __init__(self, data: pd.DataFrame | None = None) -> None:
        self.config()
        self.__avgRate = float('nan')
        if data is None:
            self.__tab = pd.DataFrame(columns=COL_TAG)
        else:
            self.__verify(data)
            self.__tab = self.__calcTab(data)
        return

    def __repr__(self) -> str:
        return self.__tab.to_string()

    def __verify(self, data: pd.DataFrame) -> None:
        if type(data) is not pd.DataFrame:
            raise TypeError('Unsupported data type.')
        sz = min(data.columns.size, len(COL_TAG))
        v = pd.Series(data.columns[:sz] != COL_TAG[:sz])
        v = v.loc[v]
        if v.size:
            rects = set()
            for i in v.index:
                rects.add((i, -1, 1, 1))
            if sz < data.columns.size:
                rects.add((sz, -1, data.columns.size - sz, 1))
            raise ValueError('Column title error.', rects)
        elif sz < data.columns.size:
            raise ValueError('Column title error.', {(sz, -1, data.columns.size - sz, 1)})
        elif sz < len(COL_TAG):
            raise ValueError('Column title error.', {(0, -1, data.columns.size, 1)})
        rows = data.index.size
        if rows == 0:
            return
        v = pd.Series(data.index != range(rows))
        v = v.loc[v]
        if v.size:
            raise ValueError('Index error.', {(-1, v.index[0], 1, 1)})
        df = data.fillna(0.)

        if df.dtypes[COL_DT] != 'datetime64[ns]':
            for row in range(rows):
                if type(df.iat[row, COL_DT]) is not pd.Timestamp:
                    raise TypeError('Date type is required.', {(COL_DT, row, 1, 1)})

        for col in range(COL_BA, len(COL_TAG)):
            if df.dtypes[col] != 'float64':
                v = None
                for row in range(rows):
                    try:
                        float(df.iat[row, col])
                    except:
                        v = row
                        break
                raise ValueError('Numeric type is required.', {(col, v, 1, 1)})
            v = df.iloc[:, col].isin([float('inf'), float('nan')])
            v = v.loc[v]
            if v.size:
                raise ValueError('A finite number is required.', {(col, v.index[0], 1, 1)})

        v = ((df.iloc[:, COL_BA] != 0) | (df.iloc[:, COL_BS] != 0)) & ((df.iloc[:, COL_SA] != 0) | (df.iloc[:, COL_SS] != 0))
        v = v.loc[v]
        if v.size:
            raise ValueError('Buying and Selling data must be in separated rows.', {(COL_BA, v.index[0], 4, 1)})

        for col in {COL_BS, COL_SS}:
            v = df.iloc[:, col] < 0
            v = v.loc[v]
            if v.size:
                raise ValueError('Negative Share is not allowed.', {(col, v.index[0], 1, 1)})

        for col in {(COL_BA, COL_BS), (COL_SA, COL_SS)}:
            v = data.iloc[:, col[0]].isna() & ~data.iloc[:, col[1]].isna()
            v = v.loc[v]
            if v.size:
                raise ValueError('Amount data is missing.', {(col[0], v.index[0], 1, 1)})
            v = (df.iloc[:, col[0]] / df.iloc[:, col[1]]).isin([float('inf')])
            v = v.loc[v]
            if v.size:
                raise ValueError('Amount/Share must be finite.', {(col[0], v.index[0], 2, 1)})

        v = (df.iloc[:, COL_BS] == 0) & (df.iloc[:, COL_SS] == 0)
        v = v.loc[v]
        if v.size:
            raise ValueError('Transaction data is required.', {(COL_BA, v.index[0], COL_SS - COL_DT, 1)})

        if (df.iloc[:, COL_DT].sort_values(ignore_index=True) != df.iloc[:, COL_DT]).any():
            dt_0 = pd.to_datetime(0)
            for row in range(rows):
                dt = pd.to_datetime(df.iat[row, COL_DT])
                if dt < dt_0:
                    raise ValueError('Date data must be ascending.', {(COL_DT, row, 1, 1)})
                dt_0 = dt

        return

    def __calcTab(self, data: pd.DataFrame) -> pd.DataFrame:
        self.__verify(data)
        rows = data.index.size
        if rows == 0:
            return data
        _data = data.copy()
        df = data.fillna(0.)

        Shr = df.iloc[:, COL_BS] - df.iloc[:, COL_SS]
        HoldShrRes = 0
        HoldShrMat = pd.Series(index=range(rows), dtype=float)
        for row in range(rows):
            HoldShrRes += Shr.iat[row]
            HoldShrMat.iat[row] = HoldShrRes
            if HoldShrRes < 0:
                _data.iloc[:, COL_HS] = HoldShrMat
                raise ValueError('Overselling is not allowed.', {(COL_SS, row, 1, 1)})
        _data.iloc[:, COL_HS] = HoldShrMat
        df.iloc[:, COL_HS] = HoldShrMat

        AmtMat = pd.DataFrame(data=0, index=range(rows), columns=range(rows), dtype=float)
        row_0 = 0
        BuyShrExp = 0
        ShrBal = 0
        for col in range(rows):
            ShrBal = ShrBal + Shr.iat[col]
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

        RateMat = pd.Series(index=range(rows), dtype=float)
        RateSz = 0
        AmtHeadRow = 0
        AmtResPrev = 0
        RatePrev = 0
        for col in df.loc[df.iloc[:, COL_SS] > 0].index:
            Rate = df.iat[col, COL_RR]
            AmtTailRow = col
            for count in range(self.__MaxCount):
                if Rate < -1:
                    RateSign = -1
                else:
                    RateSign = 1
                AmtRes = df.iat[col, COL_SA]
                for row in range(AmtHeadRow, AmtTailRow + 1):
                    if AmtMat.iat[row, col]:
                        AmtRes -= AmtMat.iat[row, col] * (RateSign * abs(1 + Rate) ** ((df.iat[col, COL_DT] - df.iat[row, COL_DT]).days / 365))
                        AmtTailRow = row    # Will not change current FOR loop, but find the valid range for the next loop.
                    elif df.iat[row, COL_BA]:
                        break
                if abs(AmtRes) < self.__MaxAmtResErr:
                    count = 0
                    break
                if AmtRes == AmtResPrev or Rate == RatePrev:
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
            AmtHeadRow = AmtTailRow
        _data.iloc[:, COL_RR] = RateMat

        if RateSz == 0:
            self.__avgRate = float('nan')
        elif RateSz == 1:
            self.__avgRate = Rate
        elif RateSz > 1:
            AmtResPrev = 0
            RatePrev = 0
            # for idx in df.loc[df.iloc[:, COL_SS] > 0].index:
            idx = RateMat.loc[~RateMat.isna()].index[-1]
            if pd.isna(self.__avgRate):
                Rate = 0
            else:
                Rate = self.__avgRate
            for count in range(self.__MaxCount):
                if Rate < -1:
                    RateSign = -1
                else:
                    RateSign = 1
                AmtRes = 0
                AmtHeadRow = 0
                for col in range(idx + 1):
                    if df.iat[col, COL_SS] > 0:
                        AmtRes += df.iat[col, COL_SA]
                        for row in range(AmtHeadRow, col + 1):
                            if AmtMat.iat[row, col] != 0:
                                AmtRes -= AmtMat.iat[row, col] * (RateSign * abs(1 + Rate) ** ((df.iat[col, COL_DT] - df.iat[row, COL_DT]).days / 365))
                                AmtHeadRow = row    # Will not change current FOR loop, but find the valid range for the next loop.
                            elif df.iat[row, COL_BA] != 0:
                                break
                if abs(AmtRes) < self.__MaxAmtResErr:
                    count = 0
                    break
                if AmtRes == AmtResPrev or Rate == RatePrev:
                    RateNew = Rate + self.__dRate
                else:
                    RateNew = AmtRes / (AmtResPrev - AmtRes) * (Rate - RatePrev) + Rate
                RatePrev = Rate
                Rate = RateNew
                AmtResPrev = AmtRes
            if count > 0:
                raise RuntimeError(f'Cannot find the Average Rate of Return in {self.__MaxCount} rounds.')
            self.__avgRate = Rate

        return _data

    def avgRate(self, data: pd.DataFrame | None = None) -> float:
        if data is not None:
            self.__calcTab(data)
        return self.__avgRate

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

    def isValid(self, data=None) -> bool:
        try:
            self.__verify(data)
        except:
            return False
        return True

    def table(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        if data is not None:
            self.__tab = self.__calcTab(data)
        return self.__tab

    def read_csv(self, file: str) -> pd.DataFrame:
        self.__tab = self.__calcTab(pd.read_csv(file).astype({TAG_DT: 'datetime64[ns]'}))
        return self.__tab

class txnTabView(txnTab, tabView):
    __txn_update = Signal()
    def __init__(self, data: pd.DataFrame | None = None) -> None:
        self.__err = ()
        txnTab.__init__(self)
        tabView.__init__(self, txnTab.table(self))
        if data is None:
            self.__update(txnTab.table(self))
        else:
            self.__update(data)
        self.view.scrollToBottom()
        return

    def flags(self, index: QModelIndex):
        col = index.column()
        if col < COL_HS:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable


    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
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
            elif col == COL_RR:
                return f'{v * 100:.2f}%'
            else:
                return f'{v:.2f}'
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_DT:
                return int(Qt.AlignCenter)
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return tabView.data(self, index, role)

    def setData(self, index: QModelIndex, value, role=Qt.EditRole) -> bool:
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
            self.__update()
            return True
        return False

    def show_error(
        self, args: tuple,
        prt: bool | None = True,
        foreColor: bool | None = True,
        backColor: bool | None = True,
        msgBox: bool | None = True
        ) -> None:
        if type(args) is not tuple or len(args) == 0:
            return
        self.__err = args
        if prt:
            print(args[0])
        self.beginResetModel()
        tabView.table(self, self.__tab)
        if len(args) >= 2 and type(args[1]) is set:
            for v in args[1]:
                if type(v) is tuple and len(v) == 4:
                    if foreColor:
                        self.setColor(FORE, COLOR_CRIT[FORE], v[0], v[1], v[2], v[3])
                    if backColor:
                        self.setColor(BACK, COLOR_CRIT[BACK], v[0], v[1], v[2], v[3])
        self.endResetModel()
        if msgBox:
            if type(args[0]) is str:
                QMessageBox.critical(None, 'ERROR', args[0])
            else:
                QMessageBox.critical(None, 'ERROR', str(args))
        return

    def __update(self, newTab: pd.DataFrame | None = None) -> None:
        self.__err = ()
        self.setColor(FORE, COLOR_CRIT[FORE])
        self.setColor(BACK, COLOR_CRIT[BACK])
        if newTab is not None:
            self.__tab = newTab
        rows = self.__tab.index.size
        self.beginResetModel()
        if rows == 0:
            self.__tab = pd.concat([
                self.__tab,
                pd.DataFrame(float('nan'), [0], self.__tab.columns).astype({TAG_DT: 'datetime64[ns]'})],
                ignore_index=True)
        else:
            row = 0
            while row < rows - 1:
                if self.__tab.iloc[row, :COL_HS].isna().all():
                    self.__tab = self.__tab.drop(index=row).reset_index(drop=True)
                    rows = self.__tab.index.size
                else:
                    row += 1
            if not self.__tab.iloc[-1, :].isna().all():
                df = self.__tab.sort_values(by=self.__tab.columns[COL_DT], ignore_index=True)
                if (self.__tab.iloc[:, COL_DT] != df.iloc[:, COL_DT]).any() and self.isValid(df):
                    self.__tab = df
                    mute = False
                elif newTab is not None:
                    mute = False
                else:
                    mute = True
                try:
                    self.__tab = txnTab.table(self, self.__tab)
                except:
                    v = sys.exc_info()[1].args
                    if mute and self.isValid(self.__tab.iloc[:-1, :]):
                        if v[0] != 'Date data must be ascending.':
                            self.show_error(v, msgBox=False)
                    else:
                        self.show_error(v)
                else:
                    self.__tab = pd.concat([
                        self.__tab,
                        pd.DataFrame(float('nan'), [0], self.__tab.columns).astype({TAG_DT: 'datetime64[ns]'})],
                        ignore_index=True)
            else:
                try:
                    self.__tab.iloc[:-1, :] = txnTab.table(self, self.__tab.iloc[:-1, :])
                except:
                    self.show_error(sys.exc_info()[1].args)
        tabView.table(self, self.__tab)
        self.__txn_update.emit()
        self.endResetModel()
        return

    def table(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        if data is not None:
            self.__update(data)
            self.view.scrollToBottom()
        return self.__tab

    def error(self) -> tuple:
        return self.__err

    def signal(self) -> Signal:
        return self.__txn_update

    def read_csv(self, file: str) -> pd.DataFrame:
        try:
            self.__update(pd.read_csv(file).astype({TAG_DT: 'datetime64[ns]'}))
        except:
            self.show_error(sys.exc_info()[1].args)
        else:
            self.view.scrollToBottom()
        return self.__tab

if __name__ == '__main__':
    app = QApplication()
    txn = txnTabView()
    txn.show()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    print(txn.table())
    print(txn.avgRate())
    app.exec()
