from tabView import QApplication
from txnTab import txnTabView

if __name__ == '__main__':
    app = QApplication()

    txn = txnTabView()
    txn.show()
    txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')

    app.exec()
