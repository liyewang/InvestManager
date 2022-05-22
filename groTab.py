from numpy import float64
import pandas as pd
from basTab import *
from db import *
from valTab import (
    COL_DT as VAL_COL_DT,
    COL_UV as VAL_COL_UV,
    COL_NV as VAL_COL_NV,
    COL_HA as VAL_COL_HA,
    COL_HS as VAL_COL_HS,
    COL_UP as VAL_COL_UP,
    COL_HP as VAL_COL_HP,
    COL_TAG as VAL_COL_TAG,
    COL_TYP as VAL_COL_TYP,
)

TAG_DT = 'Date'
TAG_IA = 'Invest Amount'
TAG_HA = 'Holding Amount'
TAG_PR = 'Profit Rate'
TAG_AP = 'Accumulated Profit'
TAG_AR = 'Annualized Rate'

COL_DT = 0
COL_IA = 1
COL_HA = 2
COL_PR = 3
COL_AP = 4
COL_AR = 5

COL_TAG = [
    TAG_DT,
    TAG_IA,
    TAG_HA,
    TAG_PR,
    TAG_AP,
    TAG_AR,
]

COL_TYP = {
    TAG_DT:'datetime64[ns]',
    TAG_HA:'float64',
    TAG_IA:'float64',
    TAG_PR:'float64',
    TAG_AP:'float64',
    TAG_AR:'float64',
}

class groTab:
    def __init__(self, data: db | None = None) -> None:
        self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        if data is None:
            self.__db = db()
        else:
            self.load(data)
        return

    def __repr__(self) -> str:
        return self.__tab.to_string()

    def __update(self, data: db | pd.DataFrame | None = None) -> None:
        if type(data) is dict:
            pass
        elif type(data) is pd.DataFrame:
            pass
        return

    def load(self, data: db) -> pd.DataFrame:
        self.__tab = pd.DataFrame(columns=COL_TAG).astype(COL_TYP)
        self.__db = data
        val_tab = pd.DataFrame(columns=VAL_COL_TAG).astype(VAL_COL_TYP)
        for group, df in self.__db.get(key=KEY_VAL).items():
            if df.index != VAL_COL_TAG:
                raise ValueError(f'DB error in {group}/{KEY_VAL}\n{df}')
            val_tab = pd.concat([val_tab, df], ignore_index=True)
        dates = val_tab.iloc[:, VAL_COL_DT].drop_duplicates().sort_index(ascending=False, ignore_index=True)
        for date in dates:
            tab = val_tab.loc[val_tab.iloc[:, VAL_COL_DT] == date]
            HoldAmt = tab.iloc[:, VAL_COL_HA].sum()
            IvstAmt = (tab.iloc[:, VAL_COL_UP] * tab.iloc[:, VAL_COL_HS]).sum()
            Rate = HoldAmt / IvstAmt - 1
            self.__tab = pd.concat([self.__tab, pd.DataFrame([[date, IvstAmt, HoldAmt, Rate, NAN, NAN]])], ignore_index=True)
        return self.__tab

    def table(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        if data:
            self.__update(gro=data)
        return self.__tab

    def read_csv(self, file: str) -> pd.DataFrame:
        self.__update(pd.read_csv(file))
        return self.__tab

class groTabMod(groTab, basTabMod):
    def __init__(self, db: dict | None = None) -> None:
        super().__init__(db)

if __name__ == '__main__':
    app = QApplication()
    gro = groTabMod()
    gro.show()
    app.exec()