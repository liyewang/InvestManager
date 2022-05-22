import pandas as pd
from copy import deepcopy

KEY_INF = 'INF'
KEY_TXN = 'TXN'
KEY_VAL = 'VAL'

GRP_FUND = 'FUND'
GRP_CONF = 'CONF'

VALID_GRP = {
    GRP_FUND,
    GRP_CONF,
}

ASSET_GRP = {
    GRP_FUND,
}

GRP_SEP = '_'

def group_info(group: str) -> list:
    data = group.split(GRP_SEP, 1)
    if len(data) != 2:
        raise ValueError(f'Group error. [{group}]')
    return data

def group_make(typ: str, code: str) -> str:
    return f'{typ}{GRP_SEP}{code}'

class db:
    def __init__(self, path: str | None = None, complevel: int | None = 1) -> None:
        if complevel < 0 or complevel > 9:
            raise ValueError('complevel must be within the range [0 - 9].')
        self.__path = path
        self.__complvl = complevel
        if path:
            with pd.HDFStore(path) as hdf:
                self.__db = {
                    group:{
                        key:hdf.get(f'{group}/{key}')
                        for key in next(hdf.walk(f'/{group}')[2])
                    }
                    for group in next(hdf.walk())[1]
                }
                self.__info = hdf.info()
        else:
            self.__db = {}
            self.__info = self.__db
        return

    def __repr__(self) -> str:
        return self.__info

    def get(self, group: str | None = None, key: str | None = None) -> dict | pd.DataFrame | pd.Series:
        data = {}
        if group is None and key is None:
            data = deepcopy(self.__db)
        elif group is None:
            for k, v in self.__db.items():
                if type(v) is dict and key in v:
                    data[k] = v[key].copy()
        elif len(group) == 1:
            for k, v in self.__db.items():
                if k[0] == group:
                    if key is None:
                        data[k] = deepcopy(v)
                    elif key in v:
                        data[k] = v[key].copy()
        elif group in self.__db:
            if key is None:
                data = deepcopy(self.__db[group])
            elif key in self.__db[group]:
                data = self.__db[group][key].copy()
        return data

    def set(self, group: str, key: str, data: pd.DataFrame | pd.Series) -> None:
        if group_info(group)[0] not in VALID_GRP:
            raise ValueError(f'Unsupported group type [{type(group)}].')
        if not (type(data) is pd.DataFrame or type(data) is pd.Series):
            raise TypeError(f'Unsupported data type [{type(data)}].')
        if group not in self.__db:
            self.__db[group] = {}
        self.__db[group][key] = data.copy()
        if self.__path:
            with pd.HDFStore(self.__path, complevel=self.__complvl) as hdf:
                hdf.put(f'{group}/{key}', self.__db[group][key])
                self.__info = hdf.info()
        return

    def remove(self, group: str | None = '/') -> None:
        if group == '/':
            self.__db.clear()
        elif group in self.__db:
            del self.__db[group]
        else:
            return
        if self.__path:
            with pd.HDFStore(self.__path) as hdf:
                hdf.remove(group)
                self.__info = hdf.info()
        return
