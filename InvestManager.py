import os
import pandas as pd
from PySide6.QtWidgets import QApplication
from txnTab import txnTabMod
from detailPanel import detailPanel
from homePanel import homePanel
from db import db

if __name__ == '__main__':
    app = QApplication()

    txn = txnTabMod()
    txn.show()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')

    app.exec()

# os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{__file__.split(".")[0]}.db')