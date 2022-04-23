from PySide6.QtWidgets import QWidget, QGridLayout, QApplication
from txnTab import txnTabView
from valTab import valTabView

class detPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()

        txn = txnTabView()
        txn.read_csv(R'C:\Users\51730\Desktop\dat.csv')

        val = valTabView('519697', txn.table())
        val.view.setMinimumWidth(480)

        main_layout = QGridLayout()
        main_layout.addWidget(val.view, 1, 0)
        main_layout.addWidget(txn.view, 1, 1)
        main_layout.setColumnStretch(1, 1)
        main_layout.setColumnStretch(0, 0)
        main_layout.SetMinimumSize
        self.setLayout(main_layout)

if __name__ == '__main__':
    app = QApplication()
    det = detPanel()
    det.show()
    app.exec()