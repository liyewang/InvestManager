import os
import pandas as pd
from tabView import QApplication
from txnTab import txnTabView
from detailPanel import detailPanel
from homePanel import homePanel

KEY_INF = 'INF'
KEY_TXN = 'TXN'
KEY_VAL = 'VAL'

COMP_LV = 9

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

def db_get(file: str) -> dict:
    with pd.HDFStore(file) as hdf:
        db = {
            group:{
                key:hdf.get(f'{group}/{key}')
                for key in next(hdf.walk(f'/{group}')[2])
            }
            for group in next(hdf.walk())[1]
        }
    return db

def db_set(file: str, db: dict) -> None:
    with pd.HDFStore(file, 'a', COMP_LV) as hdf:
        for group in db.keys():
            for key in db[group].keys():
                hdf.put(f'{group}/{key}', db[group][key])
    return

def db_del(file: str, nodes: tuple) -> None:
    with pd.HDFStore(file) as hdf:
        for node in nodes:
            hdf.remove(node)
    return

if __name__ == '__main__':
    app = QApplication()

    txn = txnTabView()
    txn.show()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')

    app.exec()
