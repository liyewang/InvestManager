import os
import pandas as pd

KEY_INF = 'INF'
KEY_TXN = 'TXN'
KEY_VAL = 'VAL'

GRP_FUND = 'FUND'
KEY_FUND = 'F'
GRP_DICT = {
    KEY_FUND:GRP_FUND
}
KEY_DICT = {
    GRP_FUND:KEY_FUND
}

class db:
    def __init__(self, path: str | None = None, complevel: int | None = 1) -> None:
        if complevel < 0 or complevel > 9:
            raise ValueError('complevel must be within the range [0 - 9].')
        self.__complvl = complevel
        if path:
            self.__path = path
        else:
            self.__path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{__file__.split(".")[0]}.db')
        with pd.HDFStore(self.__path) as hdf:
            self.__db = {
                group:{
                    key:hdf.get(f'{group}/{key}')
                    for key in next(hdf.walk(f'/{group}')[2])
                }
                for group in next(hdf.walk())[1]
            }
            self.__info = hdf.info()
        return

    def __repr__(self) -> str:
        return self.__info

    def get(self, group: str | None = None, key: str | None = None) -> dict | pd.DataFrame:
        data = self.__db
        if group:
            data = data.get(group, {})
            if key:
                data = data.get(key, {})
        elif key:
            raise ValueError(f'No group specified for the key [{key}].')
        return data

    def set(self, group: str | None = None, key: str | None = None, data: pd.DataFrame | None = None) -> None:
        if group and key and data:
            if group not in self.__db.keys():
                self.__db[group] = {}
            self.__db[group][key] = data
            with pd.HDFStore(self.__path, complevel=self.__complvl) as hdf:
                hdf.put(f'{group}/{key}', self.__db[group][key])
        elif not (group or key or data):
            with pd.HDFStore(self.__path, complevel=self.__complvl) as hdf:
                for group in self.__db.keys():
                    for key in self.__db[group].keys():
                        hdf.put(f'{group}/{key}', self.__db[group][key])
        else:
            raise ValueError(f'Incomplete arguments [group: {group}, key: {key}, data: {data}].')
        return

    def remove(self, group: str | None = '/') -> None:
        with pd.HDFStore(self.__path) as hdf:
            hdf.remove(group)
        return
