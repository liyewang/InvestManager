import os
import pandas as pd
from PySide6.QtWidgets import QApplication
from detailPanel import detailPanel
from homePanel import homePanel
from db import *

if __name__ == '__main__':
    # app = QApplication()
    dat = db(R'C:\Users\51730\Desktop\dat')
    print(dat.get('FUND_519697', KEY_INF))
    # app.exec()

# os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{__file__.split(".")[0]}.db')