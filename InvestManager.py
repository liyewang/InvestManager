import os
import pandas as pd
from tabView import QApplication
from txnTab import txnTabView
from detailPanel import detailPanel
from homePanel import homePanel
from db import db

if __name__ == '__main__':
    app = QApplication()

    txn = txnTabView()
    txn.show()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')

    app.exec()
