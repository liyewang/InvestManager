import pandas as pd
import sys
from db import *
from basTab import *
import txnTab as txn
import valTab as val

TAG_DT = 'Date'
TAG_IA = 'Invest Amount'
TAG_HA = 'Holding Amount'
TAG_AP = 'Accum. Profit'
TAG_AR = 'Average Rate'

COL_DT = 0
COL_IA = 1
COL_HA = 2
COL_AP = 3
COL_AR = 4

COL_TAG = [
    TAG_DT,
    TAG_IA,
    TAG_HA,
    TAG_AP,
    TAG_AR,
]

COL_TYP = {
    TAG_DT:'datetime64[ns]',
    TAG_IA:'float64',
    TAG_HA:'float64',
    TAG_AP:'float64',
    TAG_AR:'float64',
}

class Tab:
    def __init__(self, data: db | None = None) -> None:
        self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.config()
        if data is None:
            self.__db = db()
            self.__db.set(GRP_HOME, KEY_GRO, self.__tab)
        else:
            self.load(data)
        return

    def __repr__(self) -> str:
        return self.__tab.to_string()

    def __calcRate(self, start: pd.Timestamp | None = None, end: pd.Timestamp | None = None, Rate: float = 0.) -> float:
        dfs = []
        AmtMats = []
        for group, df in self.__db.get(key=KEY_TXN).items():
            if df is None:
                continue
            if (df.columns != txn.COL_TAG).any():
                raise ValueError(f'DB error in {group}/{KEY_TXN}\n{df}')
            df = df.fillna(0.)
            if start is None:
                start = df.iat[0, txn.COL_DT]
            if end is None:
                end = df.iat[-1, txn.COL_DT]
            if start > end:
                raise ValueError(f'Rate period error. start: [{start}], end: [{end}]')
            head = df.iloc[:, txn.COL_DT] >= start
            tail = df.iloc[:, txn.COL_DT] <= end
            df = df.loc[(head & tail)]
            val_tab = self.__db.get(group, KEY_VAL)
            if val_tab is None:
                continue
            v = val_tab.iloc[:, val.COL_DT] >= start
            if v.any():
                v = val_tab.loc[v].iloc[-1, :]
                if v.iat[val.COL_HS]:
                    df = pd.concat([pd.DataFrame([[
                        v.iat[val.COL_DT], v.iat[val.COL_HA], v.iat[val.COL_HS], 0., 0., 0., 0., 0.
                    ]], columns=txn.COL_TAG), df], ignore_index=True).astype(txn.COL_TYP)
            v = val_tab.iloc[:, val.COL_DT] <= end
            if v.any():
                v = val_tab.loc[v].iloc[0, :]
                if v.iat[val.COL_HS]:
                    df = pd.concat([df, pd.DataFrame([[
                        v.iat[val.COL_DT], 0., 0., v.iat[val.COL_HA], v.iat[val.COL_HS], 0., 0., 0.
                    ]], columns=txn.COL_TAG)], ignore_index=True).astype(txn.COL_TYP)
            if df.index.size:
                dfs.append(df)
                AmtMats.append(txn.getAmtMat(df))
        if not dfs:
            return NAN
        elif pd.isna(Rate):
            Rate = 0.
        for count in range(self.__MaxCount):
            RatePrev = 0.
            AmtRes = 0.
            AmtResPrev = 0.
            for i in range(len(dfs)):
                AmtRes += txn.getAmtRes(dfs[i], AmtMats[i], Rate)
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
        return Rate

    def update(self, start: pd.Timestamp | None = None) -> None:
        val_tab = pd.DataFrame(columns=val.COL_TAG).astype(val.COL_TYP)
        for group, df in self.__db.get(key=KEY_VAL).items():
            if df is None:
                continue
            if (df.columns != val.COL_TAG).any():
                raise ValueError(f'DB error in {group}/{KEY_VAL}\n{df}')
            val_tab = pd.concat([val_tab, df], ignore_index=True)
        if val_tab.empty:
            self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
            return
        dates = val_tab.iloc[:, val.COL_DT].drop_duplicates().sort_values(ignore_index=True)
        _tab = self.__tab.sort_values(TAG_DT, ignore_index=True)
        if start is None or _tab.iloc[0, COL_DT] >= start or dates.align(_tab.iloc[:, COL_DT])[0].isna().any():
            self.__tab = pd.DataFrame(index=dates.index, columns=COL_TAG).astype(COL_TYP)
            idx = 0
            Amt = 0
            Rate = NAN
        else:
            dates = dates.loc[dates >= start]
            _tab = _tab.loc[_tab.iloc[:, COL_DT] < start]
            idx = _tab.index.size
            Amt = _tab.iloc[-1, COL_AP] - _tab.iloc[-1, COL_HA] + _tab.iloc[-1, COL_IA]
            Rate = _tab.iloc[-1, COL_AR]
            self.__tab = pd.DataFrame(index=dates.index, columns=COL_TAG).astype(COL_TYP)
            self.__tab = pd.concat([_tab, self.__tab], ignore_index=True)
        for date in dates:
            tab = val_tab.loc[val_tab.iloc[:, val.COL_DT] == date]
            HoldAmt = tab.iloc[:, val.COL_HA].sum()
            IvstAmt = (tab.iloc[:, val.COL_UP] * tab.iloc[:, val.COL_HS]).sum()
            v = tab.loc[tab.iloc[:, val.COL_TS] < 0]
            # p = tab.loc[tab.iloc[:, val.COL_TS] > 0].iloc[:, val.COL_UP]
            Amt += (v.iloc[:, val.COL_TS] * (v.iloc[:, val.COL_UP] - v.iloc[:, val.COL_UV])).sum()
            AccuAmt = Amt + HoldAmt - IvstAmt
            # if tab.iloc[:, val.COL_HS].sum():
            #     v = _tab.iloc[:, COL_DT] == date
            #     if v.any():
            #         Rate = self.__calcRate(end=date, Rate=_tab.loc[v].iat[COL_AR])
            #     else:
            #         Rate = self.__calcRate(end=date)
            self.__tab.iloc[idx, :] = date, IvstAmt, HoldAmt, AccuAmt, Rate
            idx += 1
        self.__tab = self.__tab.sort_index(ascending=False, ignore_index=True)
        self.__db.set(GRP_HOME, KEY_GRO, self.__tab)
        self.__db.save()
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

    def load(self, data: db) -> pd.DataFrame:
        tab = data.get(GRP_HOME, KEY_GRO)
        self.__db = data
        if tab is None:
            self.update()
        else:
            self.__tab = tab
            self.update()
        return self.__tab.copy()

    def table(self) -> pd.DataFrame:
        return self.__tab.copy()

class Mod(Tab, basTabMod):
    def __init__(self, data: db | None = None) -> None:
        Tab.__init__(self)
        basTabMod.__init__(self, self.table())
        if data is not None:
            self.load(data)
        self.view.setMinimumWidth(500)
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index: QModelIndex, role: int) -> str | None:
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            v = self.table().iat[index.row(), index.column()]
            if pd.isna(v):
                return ''
            if type(v) is str:
                return v
            col = index.column()
            if col == COL_DT and type(v) is pd.Timestamp:
                return v.strftime(r'%Y/%m/%d')
            elif col == COL_AR:
                return f'{v * 100:,.2f}%'
            else:
                return f'{v:,.2f}'
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_DT:
                return int(Qt.AlignCenter)
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return super().data(index, role)

    def load(self, data: db) -> pd.DataFrame | None:
        try:
            Tab.load(self, data)
        except:
            basTabMod.table(self, self.table())
            self._raise(sys.exc_info()[1].args)
            return None
        else:
            basTabMod.table(self, self.table())
        return self.table()

if __name__ == '__main__':
    app = QApplication()
    # g = Tab()
    g = Mod()
    g.show()
    d = db(R'C:\Users\51730\Desktop\dat')
    g.load(d)
    print(g.table())
    app.exec()