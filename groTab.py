from pandas import Timestamp, concat, to_numeric
from sys import exc_info
from db import *
from basTab import *
import txnTab as txn
import valTab as val

TAG_DT = 'Date'
TAG_IA = 'Invest Amount'
TAG_HA = 'Holding Amount'
TAG_AP = 'Accum. Profit'
TAG_GR = 'Gross Rate'

COL_DT = 0
COL_IA = 1
COL_HA = 2
COL_AP = 3
COL_GR = 4

COL_TAG = [
    TAG_DT,
    TAG_IA,
    TAG_HA,
    TAG_AP,
    TAG_GR,
]

COL_TYP = {
    TAG_DT:'datetime64[ns]',
    TAG_IA:'float64',
    TAG_HA:'float64',
    TAG_AP:'float64',
    TAG_GR:'float64',
}

class Tab:
    def __init__(self, data: db | None = None, upd: bool = True) -> None:
        self.__nul = DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__tab = self.__nul.copy()
        self.__yr_rate = Series(dtype='float64')
        self.__qt_rate = Series(dtype='float64')
        self.config()
        if data is None:
            self.__db = db()
        else:
            self.load(data, upd)
        return

    def __str__(self) -> str:
        return self.__tab.to_string()

    def avgRate(self, start: Timestamp | None = None, end: Timestamp | None = None, Rate: float = 0.) -> float:
        dfs = []
        AmtMats = []
        for group, df in self.__db.get(key=KEY_TXN).items():
            if df is None:
                continue
            if (df.columns != txn.COL_TAG).any():
                raise ValueError(f'DB error in {group}/{KEY_TXN}\n{df}')
            df = df.fillna(0.)
            if start is None:
                _start = df.iat[0, txn.COL_DT]
            else:
                _start = start
            if end is None:
                _end = df.iat[-1, txn.COL_DT]
            else:
                _end = end
            if _start >= _end:
                continue
            head = df.iloc[:, txn.COL_DT] >= _start
            tail = df.iloc[:, txn.COL_DT] <= _end
            df = df[(head & tail)]
            val_tab = self.__db.get(group, KEY_VAL)
            if val_tab is None:
                continue
            v = val_tab.iloc[:, val.COL_DT] < _start
            if v.any() and not v.all():
                p = val_tab[v].iloc[0]
                s = val_tab[~v].iloc[-1]
                if p.iat[val.COL_HS]:
                    df = concat([DataFrame([[
                        s.iat[val.COL_DT], p.iat[val.COL_HS] * s.iat[val.COL_UP], p.iat[val.COL_HS], 0., 0., 0., 0., 0.
                    ]], columns=txn.COL_TAG), df], ignore_index=True).astype(txn.COL_TYP)
            v = val_tab.iloc[:, val.COL_DT] <= _end
            if v.any():
                v = val_tab[v].iloc[0]
                if v.iat[val.COL_HS]:
                    df = concat([df, DataFrame([[
                        v.iat[val.COL_DT], 0., 0., v.iat[val.COL_HA], v.iat[val.COL_HS], 0., 0., 0.
                    ]], columns=txn.COL_TAG)], ignore_index=True).astype(txn.COL_TYP)
            if df.index.size:
                dfs.append(df)
                AmtMats.append(txn.getAmtMat(df))
        if not dfs:
            return NAN
        elif isna(Rate):
            Rate = 0.
        RatePrev = 0.
        AmtResPrev = 0.
        for count in range(self.__MaxCount):
            AmtRes = 0.
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

    def __tab_upd(self, start: Timestamp | None = None) -> None:
        val_tab = DataFrame(columns=val.COL_TAG).astype(val.COL_TYP)
        for group, df in self.__db.get(key=KEY_VAL).items():
            if df is None:
                continue
            if (df.columns != val.COL_TAG).any():
                raise ValueError(f'DB error in {group}/{KEY_VAL}\n{df}')
            v = df.iloc[:, val.COL_HA] > 0
            if v.any():
                val_tab = concat([val_tab, df.iloc[:v[v].index[-1] + 1]], ignore_index=True)
        if val_tab.empty:
            self.__tab = DataFrame(columns=COL_TAG).astype(COL_TYP)
            return
        dates = val_tab.iloc[:, val.COL_DT].drop_duplicates().sort_values(ignore_index=True)
        _tab = self.__tab.sort_values(TAG_DT, ignore_index=True)
        if start is None or _tab.empty or _tab.iloc[0, COL_DT] >= start or dates.align(_tab.iloc[:, COL_DT])[0].isna().any():
            self.__tab = DataFrame(index=dates.index, columns=COL_TAG).astype(COL_TYP)
            idx = 0
            Amt = 0
            Rate = NAN
        else:
            dates = dates[dates >= start]
            _tab = _tab[_tab.iloc[:, COL_DT] < start]
            idx = _tab.index.size
            Amt = _tab.iloc[-1, COL_AP] - _tab.iloc[-1, COL_HA] + _tab.iloc[-1, COL_IA]
            Rate = _tab.iloc[-1, COL_GR]
            self.__tab = DataFrame(index=dates.index, columns=COL_TAG).astype(COL_TYP)
            self.__tab = concat([_tab, self.__tab], ignore_index=True)
        for date in dates:
            tab = val_tab[val_tab.iloc[:, val.COL_DT] == date]
            HoldAmt = tab.iloc[:, val.COL_HA].sum()
            IvstAmt = (tab.iloc[:, val.COL_UP] * tab.iloc[:, val.COL_HS]).sum()
            v = tab[tab.iloc[:, val.COL_TS] < 0]
            n = v[v.iloc[:, val.COL_UP].isna()]
            for i in n.index:
                v.at[i, val.TAG_UP] = val_tab.at[i + 1, val.TAG_UP]
            Amt += (v.iloc[:, val.COL_TS] * v.iloc[:, val.COL_UP] - v.iloc[:, val.COL_TA]).sum()
            AccuAmt = Amt + HoldAmt - IvstAmt
            if tab.iloc[:, val.COL_HS].any():
                v = _tab.iloc[:, COL_DT] == date
                if v.any():
                    Rate = self.avgRate(end=date, Rate=Rate)
                else:
                    Rate = self.avgRate(end=date)
            self.__tab.iloc[idx] = date, IvstAmt, HoldAmt, AccuAmt, Rate
            idx += 1
        self.__tab = self.__tab.sort_index(ascending=False, ignore_index=True)
        self.__db.set(group_make(GRP_HOME), KEY_GRO, self.__tab)
        return

    def __rate_upd(self) -> None:
        ts0 = self.__tab.iat[-1, COL_DT]
        ts1 = self.__tab.iat[0, COL_DT]
        yr = ts0.year
        yr1 = ts1.year
        if ts0.day_of_year % 91 < 31:
            qt = ts0.quarter
        else:
            qt = ts0.quarter + 1
            if qt > 4:
                qt = 1
                yr += 1
        if ts1.day_of_year % 91 > 60:
            qt1 = ts1.quarter
        else:
            qt1 = ts1.quarter - 1
            if qt1 < 1:
                qt1 = 4
                yr1 -= 1
        yrr = []
        yri = []
        qtr = []
        qti = []
        yr_start = False
        while yr < yr1 or (yr == yr1 and qt <= qt1):
            if qt == 1 or qt == 5:
                ts = Timestamp(yr, 3, 31)
                v = self.__qt_rate.index == ts
                if v.any():
                    qtr.append(self.avgRate(Timestamp(yr, 1, 1), ts, self.__qt_rate[v].iat[0]))
                else:
                    qtr.append(self.avgRate(Timestamp(yr, 1, 1), ts))
                qti.append(ts)
                yr_start = True
                qt = 2
            elif qt == 2:
                ts = Timestamp(yr, 6, 30)
                v = self.__qt_rate.index == ts
                if v.any():
                    qtr.append(self.avgRate(Timestamp(yr, 4, 1), ts, self.__qt_rate[v].iat[0]))
                else:
                    qtr.append(self.avgRate(Timestamp(yr, 4, 1), ts))
                qti.append(ts)
                qt = 3
            elif qt == 3:
                ts = Timestamp(yr, 9, 30)
                v = self.__qt_rate.index == ts
                if v.any():
                    qtr.append(self.avgRate(Timestamp(yr, 7, 1), ts, self.__qt_rate[v].iat[0]))
                else:
                    qtr.append(self.avgRate(Timestamp(yr, 7, 1), ts))
                qti.append(ts)
                qt = 4
            elif qt == 4:
                ts = Timestamp(yr, 12, 31)
                v = self.__qt_rate.index == ts
                if v.any():
                    qtr.append(self.avgRate(Timestamp(yr, 10, 1), ts, self.__qt_rate[v].iat[0]))
                else:
                    qtr.append(self.avgRate(Timestamp(yr, 10, 1), ts))
                qti.append(ts)
                if yr_start:
                    v = self.__yr_rate.index == ts
                    if v.any():
                        yrr.append(self.avgRate(Timestamp(yr, 1, 1), ts, self.__yr_rate[v].iat[0]))
                    else:
                        yrr.append(self.avgRate(Timestamp(yr, 1, 1), ts))
                    yri.append(ts)
                yr += 1
                qt = 5
        self.__yr_rate = Series(yrr, yri, dtype='float64')
        self.__qt_rate = Series(qtr, qti, dtype='float64')
        self.__db.set(group_make(GRP_HOME), KEY_YRR, self.__yr_rate)
        self.__db.set(group_make(GRP_HOME), KEY_QTR, self.__qt_rate)
        return

    def update(self, start: Timestamp | None = None) -> None:
        self.__tab_upd(start)
        self.__rate_upd()
        return

    def config(self, MaxCount=256, dRate=0.1, MaxAmtResErr=1e-10) -> None:
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

    def load(self, data: db, upd: bool = True) -> DataFrame:
        tab = data.get(group_make(GRP_HOME), KEY_GRO)
        yr_rate = data.get(group_make(GRP_HOME), KEY_YRR)
        qt_rate = data.get(group_make(GRP_HOME), KEY_QTR)
        self.__db = data
        if tab is None:
            if upd:
                self.update()
            else:
                self.__tab = self.__nul.copy()
                self.__yr_rate = Series(dtype='float64')
                self.__qt_rate = Series(dtype='float64')
        else:
            self.__tab = tab.copy()
            self.__yr_rate = yr_rate
            self.__qt_rate = qt_rate
            if upd:
                self.__tab_upd(tab.iat[0, COL_DT])
                v = self.__tab.iloc[:, COL_DT] == tab.iat[0, COL_DT]
                if not tab.iloc[0].equals(self.__tab[v].iloc[0]):
                    self.update()
        return self.__tab.copy()

    def table(self) -> DataFrame:
        return self.__tab.copy()

    @property
    def yrRate(self) -> Series:
        return self.__yr_rate

    @property
    def qtRate(self) -> Series:
        return self.__qt_rate

class Mod(Tab, basMod):
    def __init__(self, data: db | None = None, upd: bool = True) -> None:
        Tab.__init__(self)
        basMod.__init__(self, self.table())
        if data is not None:
            self.load(data, upd)
        self.view.setMinimumWidth(500)
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index: QModelIndex, role: int) -> str | None:
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            v = self.table().iat[index.row(), index.column()]
            if isna(v):
                return ''
            if type(v) is str:
                return v
            col = index.column()
            if col == COL_DT and type(v) is Timestamp:
                return v.strftime(r'%Y/%m/%d')
            elif col >= COL_GR:
                return f'{v * 100:,.2f}%'
            else:
                return f'{v:,.2f}'
        elif role == Qt.TextAlignmentRole:
            if index.column() == COL_DT:
                return int(Qt.AlignCenter)
            else:
                return int(Qt.AlignRight | Qt.AlignVCenter)
        return super().data(index, role)

    def load(self, data: db, upd: bool = True) -> DataFrame | None:
        try:
            Tab.load(self, data, upd)
        except:
            basMod.table(self, self.table())
            self._raise(exc_info()[1].args)
            return None
        else:
            basMod.table(self, self.table())
        return self.table()

if __name__ == '__main__':
    d = db(DB_PATH)

    app = QApplication()
    g = Mod(d)
    g.show()
    print(g)
    print(g.yrRate)
    print(g.qtRate)
    app.exec()

    # g = Tab(d)
    # print(g)
    # print(g.yrRate)
    # print(g.qtRate)

    d.save()