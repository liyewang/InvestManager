import os
import pandas as pd
from PySide6.QtWidgets import QApplication
from db import *
from basTab import *
import infTab as inf
import txnTab as txn
import valTab as val
import time

if __name__ == '__main__':
    # app = QApplication()
    # t = txn.Tab()
    # t.read_csv(R'C:\Users\51730\Desktop\dat.csv')
    # v = val.Tab('FUND_519697', t.table())
    d = db(R'C:\Users\51730\Desktop\dat')
    # with pd.HDFStore(R'C:\Users\51730\Desktop\dat') as hdf:
    #     for a in hdf.walk('/FUND_519697'):
    #         print(a)
    # d.remove()
    # d.remove('FUND_000001')
    # t0 = time.time()
    # d.set('FUND_519697', KEY_INF, pd.DataFrame([['FUND','519697','',NAN,NAN,NAN,NAN,NAN]],[0],inf.COL_TAG).astype(inf.COL_TYP))
    # d.set('FUND_519697', KEY_TXN, t.table())
    # d.set('FUND_519697', KEY_VAL, v.table())
    # print(time.time() - t0)
    # d.set('FUND_519069', KEY_INF, pd.DataFrame([['FUND','519069','',NAN,NAN,NAN,NAN,NAN]],[0],inf.COL_TAG).astype(inf.COL_TYP))
    # print(d.get('FUND_519697', KEY_INF))
    # print(d.get('FUND_519069', KEY_INF))
    print(d)
    # app.exec()

# os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{__file__.split(".")[0]}.db')