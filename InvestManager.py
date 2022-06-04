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
    renew = True
    renew = False
    # app = QApplication()
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
        v = val.Tab('FUND_519697_', t.table())
        d.set('FUND_519697_', KEY_INF, pd.DataFrame(NAN,[0],inf.COL_TAG[inf.COL_IA:],dtype=float))
        d.set('FUND_519697_', KEY_TXN, t.table())
        d.set('FUND_519697_', KEY_VAL, v.table())
        # print(time.time() - t0)
        # t = txn.Tab()
        # v = val.Tab()
        d.set('FUND_519069_', KEY_INF, pd.DataFrame(NAN,[0],inf.COL_TAG[inf.COL_IA:],dtype=float))
        # d.set('FUND_519069_', KEY_TXN, t.table())
        # d.set('FUND_519069_', KEY_VAL, v.table())
        # print(d.get('FUND_519697_', KEY_INF))
        # print(d.get('FUND_519069_', KEY_INF))
        # print(d.get('FUND_519069_', KEY_TXN))
        # print(d.get('FUND_519069_', KEY_VAL))
        d.save()
    print(d)
    # app.exec()

# os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{__file__.split(".")[0]}.db')