from pandas import Timestamp, concat, date_range, to_numeric
from hashlib import sha512
from sys import exc_info, byteorder
from db import *
from basTab import *
from dfIO import *
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
        self.__nul = {KEY_GRO: DataFrame(columns=COL_TAG).astype(COL_TYP),
                        KEY_YRR: Series(dtype='float64'),
                        KEY_QTR: Series(dtype='float64'),
                        KEY_DIG: Series(dtype='int64')}
        self.__dict = {}
        self.__vals = {}
        for cTag in DICT_CLS.keys():
            self.__dict[cTag] = self.__nul
            self.__vals[cTag] = {}
        self.__cls = TAG_CLS_DEF
        self.config()
        if data is None:
            self.__db = db()
        else:
            self.load(data, upd)
        return

    def __str__(self) -> str:
        tab = self.__dict[TAG_CLS_DEF][KEY_GRO]
        assert type(tab) is DataFrame
        return tab.to_string()

    def avgRate(
        self,
        Cls: set[str] = CLS_ASSET,
        Start: Timestamp | None = None,
        End: Timestamp | None = None,
        Rate: float = 0.
    ) -> float:
        dfs = []
        AmtMats = []
        for grp in Cls:
            for group, df in self.__db.get(grp, KEY_TXN).items():
                if df is None:
                    continue
                assert type(df) is DataFrame
                if (df.columns != txn.COL_TAG).any():
                    raise ValueError(f'DB error in {group}/{KEY_TXN}\n{df}')
                df = df.fillna(0.)
                if Start is None:
                    _start = df.iat[0, txn.COL_DT]
                else:
                    _start = Start
                if End is None:
                    _end = df.iat[-1, txn.COL_DT]
                else:
                    _end = End
                if _start >= _end:
                    continue
                head = df[txn.TAG_DT] >= _start
                tail = df[txn.TAG_DT] <= _end
                df = df[(head & tail)]
                val_tab = self.__db.get(group, KEY_VAL)
                if val_tab is None:
                    continue
                v = val_tab[val.TAG_DT] < _start
                if v.any() and not v.all():
                    p = val_tab[v].iloc[0]
                    s = val_tab[~v].iloc[-1]
                    if p.iat[val.COL_HS]:
                        df = concat([DataFrame([[
                            s.iat[val.COL_DT], p.iat[val.COL_HS] * s.iat[val.COL_UV], p.iat[val.COL_HS],
                            0., 0., 0., 0., 0., 0., 0.
                        ]], columns=txn.COL_TAG), df], ignore_index=True).astype(txn.COL_TYP)
                v = val_tab[val.TAG_DT] <= _end
                if v.any():
                    v = val_tab[v].iloc[0]
                    if v.iat[val.COL_HS]:
                        df = concat([df, DataFrame([[
                            v.iat[val.COL_DT], 0., 0., v.iat[val.COL_HA], v.iat[val.COL_HS],
                            0., 0., 0., 0., 0.
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

    def __calcTab(self, Cls: set[str], Tab: DataFrame, Vals: dict, Start: Timestamp) -> DataFrame:
        if len(Vals) == 0:
            return DataFrame(columns=COL_TAG).astype(COL_TYP)
        dates = set()
        for v in Vals.values():
            assert type(v) is DataFrame
            dates.update(v[val.TAG_DT])
        dates = sorted(dates)
        d1 = dates[-1]
        vals = DataFrame(columns=val.COL_TAG).astype(val.COL_TYP)
        for v in Vals.values():
            assert type(v) is DataFrame
            if v.empty:
                continue
            for i in v[(v[val.TAG_TS] < 0) & v[val.TAG_UP].isna()].index.sort_values(ascending=False):
                v.at[i, val.TAG_UP] = v.at[i + 1, val.TAG_UP]
            d0 = v.iat[0, val.COL_DT]
            if d0 < d1:
                vfill = v.iloc[0].copy()
                vfill[val.TAG_TA] = NAN
                vfill[val.TAG_TS] = NAN
                dfill = date_range(d1, d0, freq='-1D', inclusive='left')
                vfill = DataFrame([vfill], index=range(dfill.size))
                vfill[val.TAG_DT] = dfill
                v = concat([vfill, v], ignore_index=True)
            vals = concat([vals, v], ignore_index=True)
        _tab = Tab.sort_values(TAG_DT, ignore_index=True)
        dates_res1 = [d for d in dates if d < Start]
        dates_res2 = [d for d in Tab[TAG_DT] if d < Start]
        dates_res2.reverse()
        if Tab.empty or Start <= Tab.iat[-1, COL_DT] or dates_res1 != dates_res2:
            __tab = DataFrame(index=range(len(dates)), columns=COL_TAG).astype(COL_TYP)
            idx = 0
            Amt = 0
            Rate = NAN
        else:
            dates = [d for d in dates if d >= Start]
            _tab = _tab[_tab[TAG_DT] < Start]
            idx = _tab.index.size
            Amt = _tab.iat[-1, COL_AP] - _tab.iat[-1, COL_HA] + _tab.iat[-1, COL_IA]
            Rate = _tab.iat[-1, COL_GR]
            __tab = DataFrame(index=range(len(dates)), columns=COL_TAG).astype(COL_TYP)
            __tab = concat([_tab, __tab], ignore_index=True)
        for date in dates:
            assert type(date) is Timestamp
            _val = vals[vals[val.TAG_DT] == date]
            HoldAmt = _val[val.TAG_HA].sum()
            IvstAmt = (_val[val.TAG_UP] * _val[val.TAG_HS]).sum()
            v = _val[val.TAG_TS] < 0
            if v.any():
                v = _val[v]
                Amt += (v[val.TAG_TS] * v[val.TAG_UP] - v[val.TAG_TA]).sum()
            AccuAmt = Amt + HoldAmt - IvstAmt
            if _val[val.TAG_HS].any():
                # if date in _tab[TAG_DT].values:
                #     Rate = self.avgRate(Cls, End=date, Rate=Rate)
                # else:
                #     Rate = self.avgRate(Cls, End=date)
                Rate = 0.############### DEBUG ##################
            __tab.iloc[idx] = date, IvstAmt, HoldAmt, AccuAmt, Rate
            idx += 1
        return __tab.sort_index(ascending=False, ignore_index=True)

    def __calcRate(
        self,
        Cls: set[str],
        Tab: DataFrame,
        YrR: Series,
        QtR: Series,
        Start: Timestamp = TS_ORI
    ) -> tuple[Series, Series]:
        def ts2qt(ts0: Timestamp, ts1: Timestamp) -> tuple[int, int, int, int]:
            yr0 = ts0.year
            yr1 = ts1.year
            if ts0.day_of_year % 91 < 31:
                qt0 = ts0.quarter
            else:
                qt0 = ts0.quarter + 1
                if qt0 > 4:
                    qt0 = 1
                    yr0 += 1
            if ts1.day_of_year % 91 > 60:
                qt1 = ts1.quarter
            else:
                qt1 = ts1.quarter - 1
                if qt1 < 1:
                    qt1 = 4
                    yr1 -= 1
            return yr0, qt0, yr1, qt1
        def qt2ts(yr: int, qt: int) -> tuple[Timestamp, Timestamp]:
            sdate = Timestamp(yr, qt * 3 - 2, 1)
            if qt == 1 or qt == 4:
                edate = Timestamp(yr, qt * 3, 31)
            else:
                edate = Timestamp(yr, qt * 3, 30)
            return sdate, edate
        if Tab.empty:
            return Series([], dtype='float64'), Series([], dtype='float64')
        ts0 = Tab.iat[-1, COL_DT]
        ts1 = Tab.iat[0, COL_DT]
        yr0, qt0, yr1, qt1 = ts2qt(ts0, ts1)
        sdate = qt2ts(yr0, qt0)[0]
        edate = qt2ts(yr1, qt1)[1]
        yrr = {t:r for t, r in YrR.to_dict().items() if t >= sdate and t <= edate}
        qtr = {t:r for t, r in QtR.to_dict().items() if t >= sdate and t <= edate}
        if Start.year > TS_ORI.year:
            start = Start.replace(month=1, day=1)
        else:
            start = Start
        if start > ts0:
            ts0 = start
        yr0, qt0, yr1, qt1 = ts2qt(ts0, ts1)
        yr = yr0
        qt = qt0
        while yr < yr1 or (yr == yr1 and qt <= qt1):
            sdate, edate = qt2ts(yr, qt)
            qt += 1
            if qt > 4:
                qt = 1
                yr += 1
            if sdate in QtR:
                qtr[sdate] = self.avgRate(Cls, sdate, edate, QtR[sdate])
            else:
                qtr[sdate] = self.avgRate(Cls, sdate, edate)
        yr = yr0
        while yr <= yr1:
            sdate = Timestamp(yr, 1, 1)
            edate = Timestamp(yr, 12, 31)
            if sdate in YrR:
                yrr[sdate] = self.avgRate(Cls, sdate, edate, YrR[sdate])
            else:
                yrr[sdate] = self.avgRate(Cls, sdate, edate)
            yr += 1
        return Series(yrr, dtype='float64'), Series(qtr, dtype='float64')

    def update(self) -> None:
        cTags = []
        for cTag, cls in DICT_CLS.items():
            cTags.append(cTag)
            if cTag in self.__dict:
                start = TS_END
            else:
                start = TS_ORI
            vals = {}
            dig = 0
            for grp in cls:
                for group, df in self.__db.get(grp, KEY_VAL).items():
                    if df is None:
                        continue
                    assert type(df) is DataFrame
                    if (df.columns != val.COL_TAG).any():
                        raise ValueError(f'DB error in {group}/{KEY_VAL}\n{df}')
                    df = df.drop_duplicates(val.TAG_DT).sort_values(val.TAG_DT, ascending=False, ignore_index=True)
                    v = df[val.TAG_HA] > 0
                    if v.any():
                        df = df.iloc[:v[v].index[-1] + 1]
                        vals[group] = df
                        dig ^= int.from_bytes(sha512(df.to_string().encode()).digest(), byteorder)
                        if cTag in self.__dict:
                            if group in self.__vals[cTag]:
                                val_new = df
                                val_old = self.__vals[cTag][group]
                                assert type(val_old) is DataFrame
                                if not val_new.equals(val_old):
                                    if val_new.index.size > val_old.index.size:
                                        i = val_new.index.size - val_old.index.size
                                        val_new = val_new.iloc[i:].reset_index(drop=True)
                                    else:
                                        i = val_old.index.size - val_new.index.size
                                        val_old = val_old.iloc[i:].reset_index(drop=True)
                                    v = (val_new != val_old).any(axis=1)
                                    if any(v):
                                        i = v[v].index[-1]
                                        start = min(val_new.iat[i, val.COL_DT], val_old.iat[i, val.COL_DT])
                                    else:
                                        start = val_new.iat[0, val.COL_DT]
                            else:
                                d = df.iat[-1, val.COL_DT]
                                if d < start:
                                    start = d
            if start != TS_END:
                tab = self.__dict[cTag][KEY_GRO]
                yrr = self.__dict[cTag][KEY_YRR]
                qtr = self.__dict[cTag][KEY_QTR]
                tab = self.__calcTab(cls, tab, vals, start)
                yrr, qtr = self.__calcRate(cls, tab, yrr, qtr, start)
                self.__dict[cTag] = {KEY_GRO: tab, KEY_YRR: yrr, KEY_QTR: qtr}
                dig = Series([d for d in dig.to_bytes(64, byteorder)], dtype='uint8')
                self.__db.set(group_make(GRP_HOME, cTag), KEY_GRO, tab)
                self.__db.set(group_make(GRP_HOME, cTag), KEY_YRR, yrr)
                self.__db.set(group_make(GRP_HOME, cTag), KEY_QTR, qtr)
                self.__db.set(group_make(GRP_HOME, cTag), KEY_DIG, dig)
                self.__vals[cTag] = vals
        for cTag in self.__dict.keys():
            if cTag not in cTags:
                del self.__dict[cTag]
        return

    def config(self, MaxCount=4096, dRate=0.1, MaxAmtResErr=1e-10) -> None:
        MaxCount = to_numeric(MaxCount, errors='coerce')
        if MaxCount <= 0:
            raise ValueError('MaxCount must be positive.')
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
        for cTag, cls in DICT_CLS.items():
            d = data.get(group_make(GRP_HOME, cTag))
            if type(d) is dict and d.keys() == self.__nul.keys() and all([False for v in d.values() if v is None]):
                vals = {}
                dig = 0
                for grp in cls:
                    for group, df in data.get(grp, KEY_VAL).items():
                        if df is None:
                            continue
                        assert type(df) is DataFrame
                        if (df.columns != val.COL_TAG).any():
                            raise ValueError(f'DB error in {group}/{KEY_VAL}\n{df}')
                        df = df.drop_duplicates(val.TAG_DT).sort_values(val.TAG_DT, ascending=False, ignore_index=True)
                        v = df[val.TAG_HA] > 0
                        if v.any():
                            df = df.iloc[:v[v].index[-1] + 1]
                            vals[group] = df
                            dig ^= int.from_bytes(sha512(df.to_string().encode()).digest(), byteorder)
                dig = [d for d in dig.to_bytes(64, byteorder)]
                _dig = d[KEY_DIG]
                assert type(_dig) is Series
                if dig == _dig.tolist():
                    self.__dict[cTag] = d
                    self.__vals[cTag] = vals
                    continue
            self.__dict[cTag] = self.__nul
            self.__vals[cTag] = {}
        self.__db = data
        if upd:
            self.update()
        tab = self.__dict[TAG_CLS_DEF][KEY_GRO]
        assert type(tab) is DataFrame
        return tab.copy()

    def setClass(self, cls: str = TAG_CLS_DEF) -> None:
        assert cls in DICT_CLS.keys(), f'Invalid class [{cls}].'
        self.__cls = cls
        return

    def getClass(self) -> str:
        return self.__cls

    def value(self, cls: str = TAG_CLS_DEF, key: str = KEY_GRO) -> DataFrame | Series:
        assert cls in DICT_CLS.keys(), f'Invalid class [{cls}].'
        assert key in KEYS_HOME, f'Invalid key [{key}].'
        v = self.__dict[cls][key]
        assert type(v) is DataFrame or type(v) is Series
        return v.copy()

    def table(self) -> DataFrame:
        tab = self.__dict[self.__cls][KEY_GRO]
        assert type(tab) is DataFrame
        return tab.copy()

    @property
    def yrRate(self) -> Series:
        yrr = self.__dict[self.__cls][KEY_YRR]
        assert type(yrr) is Series
        return yrr.copy()

    @property
    def qtRate(self) -> Series:
        qtr = self.__dict[self.__cls][KEY_QTR]
        assert type(qtr) is Series
        return qtr.copy()

    def export_table(self, file: str) -> None:
        tab = self.__dict[self.__cls][KEY_GRO]
        assert type(tab) is DataFrame
        dfExport(tab, file)
        return

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

    def setClass(self, cls: str = TAG_CLS_DEF) -> None:
        try:
            Tab.setClass(self, cls)
        except:
            basMod.table(self, self.table())
            self._raise(exc_info()[1].args)
        else:
            basMod.table(self, self.table())
        return

    def export_table(self, file: str) -> None:
        try:
            Tab.export_table(self, file)
        except:
            self._raise(exc_info()[1].args)
        return

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