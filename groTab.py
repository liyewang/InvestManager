import pandas as pd
from basTab import basTabMod
from db import (
    KEY_INF,
    KEY_TXN,
    KEY_VAL,
)

TAG_IA = 'Invest Amount'
TAG_HA = 'Holding Amount'
TAG_PR = 'Profit Rate'
TAG_AP = 'Accumulated Profit'
TAG_AR = 'Annualized Rate'

COL_IA = 0
COL_HA = 1
COL_PR = 2
COL_AP = 3
COL_AR = 4

COL_TAG = [
    TAG_HA,
    TAG_IA,
    TAG_PR,
    TAG_AP,
    TAG_AR,
]

class groTab:
    def __init__(self, db: dict | None = None) -> None:
        self.__tab = pd.DataFrame(columns=COL_TAG)
        self.__update(db)
        return

    def __repr__(self) -> str:
        return self.__tab.to_string()

    def __update(self, data: dict | pd.DataFrame | None = None) -> None:
        if type(data) is dict:
            pass
        elif type(data) is pd.DataFrame:
            pass
        return

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