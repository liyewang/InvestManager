from os import path as os_path
from pandas import DataFrame, Series, HDFStore
from copy import deepcopy

DB_PATH = os_path.join(os_path.dirname(os_path.abspath(__file__)), 'db.h5')
# DB_PATH = ''.join(__file__.split('.')[:-1]) + '.h5'
# DB_PATH = os_path.join(os_path.dirname(os_path.abspath(__file__)), f'{__file__.split(".")[0]}.h5')

NAN = float('nan')

KEY_INF = 'INF'
KEY_TXN = 'TXN'
KEY_VAL = 'VAL'

KEY_GRO = 'GRO'
KEY_YRR = 'YRR'
KEY_QTR = 'QTR'

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
            with HDFStore(path) as hdf:
                self.__db = {
                    group:{
                        key:hdf.get(f'{group}/{key}')
                        for key in next(hdf.walk(f'/{group}'))[2]
                    }
                    for group in next(hdf.walk())[1]
                }
                self.__info = hdf.info()
        return

    def __str__(self) -> str:
        return self.__info

    def get(self, group: str | None = None, key: str | None = None) -> dict | DataFrame | Series | None:
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

    def set(self, group: str, key: str, data: DataFrame | Series) -> None:
        if group_info(group)[0] not in VALID_GRP:
            raise ValueError(f'Unsupported group type [{type(group)}].')
        if not (type(data) is DataFrame or type(data) is Series):
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
            with HDFStore(self.__path, 'w', self.__complvl) as hdf:
                for group, keys in self.__db.items():
                    for key, data in keys.items():
                        hdf.put(f'{group}/{key}', data)
                self.__info = hdf.info()
            self.__changed = False
        return


if __name__ == '__main__':
    from os import remove as os_remove
    import infTab as inf
    import txnTab as txn
    import valTab as val
    renew = True
    renew = False
    if renew:
        os_remove(DB_PATH)
    d = db(DB_PATH)
    # with HDFStore(DB_PATH) as hdf:
    #     for a in hdf.walk('/FUND_519697'):
    #         print(a)
    # d.remove()
    # d.remove('FUND_000001')
    if renew:
        t = txn.Tab()
        t.read_csv(os_path.join(os_path.dirname(os_path.abspath(__file__)), 'txn.csv'))
        v = val.Tab(t.table(), 'FUND_519697_')
        d.set('FUND_519697_', KEY_INF, DataFrame(NAN,[0],inf.COL_TAG[inf.COL_IA:], dtype='float64'))
        d.set('FUND_519697_', KEY_TXN, t.table())
        # d.set('FUND_519697_', KEY_VAL, v.table())
        # t = txn.Tab()
        # v = val.Tab()
        # d.set('FUND_519069_', KEY_INF, DataFrame(NAN,[0],inf.COL_TAG[inf.COL_IA:], dtype='float64'))
        # d.set('FUND_519069_', KEY_TXN, t.table())
        # d.set('FUND_519069_', KEY_VAL, v.table())
        # print(d.get('FUND_519697_', KEY_INF))
        # print(d.get('FUND_519069_', KEY_INF))
        # print(d.get('FUND_519069_', KEY_TXN))
        # print(d.get('FUND_519069_', KEY_VAL))
        d.save()
    print(d)
    # txns = d.get(key=KEY_TXN)
    # for t in txns.values():
    #     if type(t) is DataFrame:
    #         t.to_csv('dat.csv', index=False)