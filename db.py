import pandas as pd
from copy import deepcopy

NAN = float('nan')

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

def group_info(group: str) -> tuple:
    data = group.split(GRP_SEP)
    return data[0], data[1], bytes.fromhex(data[2]).decode()

def group_make(typ: str, code: str = '', name: str = '') -> str:
    return f'{typ}{GRP_SEP}{code}{GRP_SEP}{name.encode().hex()}'

class db:
    def __init__(self, path: str | None = None, complevel: int = 1) -> None:
        if complevel < 0 or complevel > 9:
            raise ValueError('complevel must be within the range [0 - 9].')
        self.__path = path
        self.__complvl = complevel
        self.__changed = False
        if self.__path:
            with pd.HDFStore(path) as hdf:
                self.__db = {
                    group:{
                        key:hdf.get(f'{group}/{key}')
                        for key in next(hdf.walk(f'/{group}'))[2]
                    }
                    for group in next(hdf.walk())[1]
                }
                self.__info = hdf.info()
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
        if data.empty:
            if group in self.__db and key in self.__db[group]:
                del self.__db[group][key]
                self.__changed = True
        elif group in self.__db:
            if not (key in self.__db[group] and data.equals(self.__db[group][key])):
                self.__db[group][key] = data.copy()
                self.__changed = True
        else:
            self.__db[group] = {}
            self.__db[group][key] = data.copy()
            self.__changed = True
        return

    def remove(self, group: str = '/') -> None:
        if self.__db:
            if group == '/':
                self.__db.clear()
            elif group in self.__db:
                del self.__db[group]
            self.__changed = True
        return

    def move(self, src: str, dst: str) -> None:
        if group_info(src)[0] not in VALID_GRP:
            raise ValueError(f'Unsupported group type [{type(src)}].')
        if group_info(dst)[0] not in VALID_GRP:
            raise ValueError(f'Unsupported group type [{type(dst)}].')
        if src not in self.__db:
            raise KeyError(f'Source group [{src}] does not exist.')
        if dst in self.__db:
            raise KeyError(f'Destination group [{dst}] already exists.')
        self.__db[dst] = self.__db[src]
        del self.__db[src]
        self.__changed = True
        return

    def save(self) -> None:
        if self.__path and self.__changed:
            with pd.HDFStore(self.__path, 'w', self.__complvl) as hdf:
                for group, keys in self.__db.items():
                    for key, data in keys.items():
                        hdf.put(f'{group}/{key}', data)
                self.__info = hdf.info()
            self.__changed = False
        return


if __name__ == '__main__':
    import os
    import infTab as inf
    import txnTab as txn
    import valTab as val
    import time
    renew = True
    renew = False
    file = R'C:\Users\51730\Desktop\dat'
    if renew:
        os.remove(file)
    d = db(file)
    # with pd.HDFStore(file) as hdf:
    #     for a in hdf.walk('/FUND_519697'):
    #         print(a)
    # d.remove()
    # d.remove('FUND_000001')
    # t0 = time.time()
    if renew:
        t = txn.Tab()
        t.read_csv(R'C:\Users\51730\Desktop\dat.csv')
        v = val.Tab(t.table(), 'FUND_519697_')
        d.set('FUND_519697_', KEY_INF, pd.DataFrame(NAN,[0],inf.COL_TAG[inf.COL_IA:],dtype=float))
        d.set('FUND_519697_', KEY_TXN, t.table())
        d.set('FUND_519697_', KEY_VAL, v.table())
        # print(time.time() - t0)
        # t = txn.Tab()
        # v = val.Tab()
        # d.set('FUND_519069_', KEY_INF, pd.DataFrame(NAN,[0],inf.COL_TAG[inf.COL_IA:],dtype=float))
        # d.set('FUND_519069_', KEY_TXN, t.table())
        # d.set('FUND_519069_', KEY_VAL, v.table())
        # print(d.get('FUND_519697_', KEY_INF))
        # print(d.get('FUND_519069_', KEY_INF))
        # print(d.get('FUND_519069_', KEY_TXN))
        # print(d.get('FUND_519069_', KEY_VAL))
        d.save()
    print(d)
# os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{__file__.split(".")[0]}.db')