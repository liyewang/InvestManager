import pandas as pd
from copy import deepcopy

KEY_INF = 'INF'
KEY_TXN = 'TXN'
KEY_VAL = 'VAL'
KEY_GRO = 'GRO'

GRP_FUND = 'FUND'
GRP_HOME = 'HOME'
GRP_CONF = 'CONF'

VALID_GRP = {
    GRP_FUND,
    GRP_HOME,
    GRP_CONF,
}

ASSET_GRP = {
    GRP_FUND,
}

GRP_SEP = '_'

def group_info(group: str) -> list:
    return group.split(GRP_SEP, 1)

def group_make(typ: str, code: str) -> str:
    return f'{typ}{GRP_SEP}{code}'

class db:
    def __init__(self, path: str | None = None, complevel: int = 1) -> None:
        if complevel < 0 or complevel > 9:
            raise ValueError('complevel must be within the range [0 - 9].')
        self.__path = path
        self.__complvl = complevel
        if path:
            with pd.HDFStore(path) as hdf:
                self.__db = {
                    group:{
                        key:hdf.get(f'{group}/{key}')
                        for key in next(hdf.walk(f'/{group}'))[2]
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

    def get(self, group: str | None = None, key: str | None = None) -> dict | pd.DataFrame | pd.Series | None:
        data = {}
        if group is None and key is None:
            data = deepcopy(self.__db)
        elif group is None:
            for k, v in self.__db.items():
                if type(v) is dict and key in v:
                    data[k] = v[key].copy()
        elif group in ASSET_GRP:
            for k, v in self.__db.items():
                if group_info(k)[0] == group:
                    if key is None:
                        data[k] = deepcopy(v)
                    elif key in v:
                        data[k] = v[key].copy()
        elif group in self.__db:
            if key is None:
                data = deepcopy(self.__db[group])
            elif key in self.__db[group]:
                data = self.__db[group][key].copy()
            else:
                data = None
        elif key is not None:
            data = None
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
            # with pd.HDFStore(self.__path, 'a', self.__complvl) as hdf:
            #     hdf.put(f'{group}/{key}', self.__db[group][key])
            #     self.__info = hdf.info()
            with pd.HDFStore(self.__path, 'w', self.__complvl) as hdf:
                for group, keys in self.__db.items():
                    for key, data in keys.items():
                        hdf.put(f'{group}/{key}', data)
                self.__info = hdf.info()
        return

    def remove(self, group: str = '/') -> None:
        if group == '/':
            if self.__path:
                with pd.HDFStore(self.__path) as hdf:
                    for grp in self.__db.keys():
                        hdf.remove(grp)
                    self.__info = hdf.info()
            self.__db.clear()
        elif group in self.__db:
            if self.__path:
                with pd.HDFStore(self.__path) as hdf:
                    hdf.remove(group)
                    self.__info = hdf.info()
            del self.__db[group]
        return
