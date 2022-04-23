import pandas as pd

from PySide6.QtWidgets import QTableView, QApplication
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
import sys
import numpy as np


class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe """

    def __init__(self, dataframe: pd.DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        """ Override method from QAbstractTableModel

        Return row count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe)

        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

        Return column count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        """Override method from QAbstractTableModel

        Return data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return str(self._dataframe.iloc[index.row(), index.column()])

        return None

    def setData(self, index, value, role) -> bool:
        self._dataframe.iloc[index.row(), index.column()] = value
        return True

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])

        return None

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def select(self, row: int | None = None, col: int | None = None) -> None:
        if row != None and col != None:
            view.setCurrentIndex(model.index(row, col))
        elif row != None:
            view.selectRow(row)
        elif col != None:
            view.selectColumn(col)
        else:
            view.selectAll()
        return


if __name__ == "__main__":

    app = QApplication(sys.argv)

    # df = pd.read_csv("iris.csv")
    dt = pd.to_datetime('2022-04-10', format='%Y/%m/%d')
    # dt = pd.DatetimeIndex(['2022-04-11'])
    # dt = pd.to_datetime('2022-04-10asd', errors='coerce')
    df = pd.DataFrame(data={'Date':dt,'A':[4,3,2,np.float64('nan')],'B':[1,1,0,0]}, index=[2,3,4,1], columns=['Date', 'A', 'B'])
    # df = df.fillna(0.0)
    # df = df.replace(np.float64('nan'),0.0)

    view = QTableView()
    view.resize(800, 500)
    view.horizontalHeader().setStretchLastSection(True)
    view.setAlternatingRowColors(True)
    # view.setSelectionBehavior(QTableView.SelectRows)

    model = PandasModel(df)
    view.setModel(model)
    view.show()
    # view.selectRow(1)
    # view.setCurrentIndex(model.index(90, 1))


    # print(type(df.dtypes[1]) is type(np.dtype('float64')))
    # print(dt)
    # print(type(dt))
    # print(np.isfinite(df.iloc[:,1].to_numpy()).sum())
    # print(df)
    # print(df.iat[0,0])
    # print(type(df.iat[3,0]) is pd.Timestamp)
    # print(pd.Timestamp)
    # print(df.dtypes[0])
    # print(df.dtypes[0] == 'datetime64[ns]')
    # print(type(df.dtypes[0]) is not type(np.dtype('datetime64')))
    # s = df.iloc[:,1] == df.iloc[:,1]
    # print(df.where(s == True))
    # print(len(df.where(s == True)))
    # print(df.sort_values('B'))
    # print(df.dtypes)
    # a = (df['A']/df['B']).isin([np.float64('inf'), np.float64('nan')])
    # print(a & ~a)
    # print(s.where(s.dtype == 'float64'))

    app.exec()