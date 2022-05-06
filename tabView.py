from PySide6.QtWidgets import QTableView, QApplication, QHeaderView
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QRect
from PySide6.QtGui import QColor
import pandas as pd

FORE = 0
BACK = 1

FORE_CRIT = 0xbf0000
BACK_CRIT = 0xffdfdf
COLOR_CRIT = (FORE_CRIT, BACK_CRIT)
FORE_WARN = 0xbf0000
BACK_WARN = 0xffffdf
COLOR_WARN = (FORE_WARN, BACK_WARN)
FORE_INFO = 0x00bfbf
BACK_INFO = 0xdfffff
COLOR_INFO = (FORE_INFO, BACK_INFO)

class tabView(QAbstractTableModel):

    def __init__(self, data: pd.DataFrame, parent=None) -> None:
        QAbstractTableModel.__init__(self, parent)
        self.__tab = data
        self.view = QTableView()
        self.view.setModel(self)
        # self.view.resize(1280, 720)
        # self.view.horizontalHeader().setStretchLastSection(True)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.view.setAlternatingRowColors(True)
        # self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setAutoScroll(False)
        self.__ForeColor = {COLOR_CRIT[FORE]: set(), COLOR_WARN[FORE]: set(), COLOR_INFO[FORE]: set()}
        self.__BackColor = {COLOR_CRIT[BACK]: set(), COLOR_WARN[BACK]: set(), COLOR_INFO[BACK]: set()}
        return

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def rowCount(self, parent = QModelIndex()) -> int:
        if parent == QModelIndex():
            return self.__tab.index.size
        return 0

    def columnCount(self, parent = QModelIndex()) -> int:
        if parent == QModelIndex():
            return self.__tab.columns.size
        return 0

    def __colorMap(self, colorMap: dict, row: int, col: int) -> QColor:
        for color, rects in colorMap.items():
            for rect in rects:
                if type(rect) is QRect:
                    if rect.contains(col, row):
                        return QColor(color)

    def data(self, index: QModelIndex, role: int) -> str | None:
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            v = self.__tab.iat[index.row(), index.column()]
            if pd.isna(v):
                return ''
            return str(v)
        elif role == Qt.ForegroundRole:
            return self.__colorMap(self.__ForeColor, index.row(), index.column())
        elif role == Qt.BackgroundRole:
            return self.__colorMap(self.__BackColor, index.row(), index.column())
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int) -> str | None:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.__tab.columns[section])
            if orientation == Qt.Vertical:
                return str(self.__tab.index[section] + 1)
        elif role == Qt.ForegroundRole:
            if orientation == Qt.Vertical:
                return self.__colorMap(self.__ForeColor, section, -1)
            if orientation == Qt.Horizontal:
                return self.__colorMap(self.__ForeColor, -1, section)
        elif role == Qt.BackgroundRole:
            if orientation == Qt.Vertical:
                return self.__colorMap(self.__BackColor, section, -1)
            if orientation == Qt.Horizontal:
                return self.__colorMap(self.__BackColor, -1, section)
        return None

    def setData(self, index, value, role: int = Qt.EditRole) -> bool:
        if index.isValid() and role == Qt.EditRole:
            self.__tab.iat[index.row(), index.column()] = float(value)
            return True
        return False

    def table(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        if data is not None:
            self.__tab = data
        return self.__tab

    def select(self, row: int | None = None, col: int | None = None) -> None:
        if row >= 0 and col >= 0:
            self.view.setCurrentIndex(self.index(row, col))
        elif row >= 0:
            self.view.selectRow(row)
        elif col >= 0:
            self.view.selectColumn(col)
        else:
            self.view.selectAll()
        return

    def setColor(
        self,
        item: int,
        color: int,
        left: int | None = 0,
        top: int | None = 0,
        width: int | None = 0,
        height: int | None = 0
        ) -> None:
        if item == FORE:
            colorMap = self.__ForeColor
        elif item == BACK:
            colorMap = self.__BackColor
        rect = QRect(left, top, width, height)
        if rect.isValid():
            if color in colorMap:
                colorMap[color].add(rect)
            else:
                colorMap[color] = {rect}
        elif color in colorMap:
            colorMap[color].clear()
        return

    def show(self) -> None:
        self.view.show()
        return


if __name__ == '__main__':

    app = QApplication()

    # df = pd.read_csv('iris.csv')
    dt = pd.to_datetime('2022-04-10', format=r'%Y/%m/%d')
    # dt = pd.DatetimeIndex(['2022-04-11'])
    # dt = pd.to_datetime('2022-04-10asd', errors='coerce')
    df = pd.DataFrame(data={'Date':dt,'A':[4,3,2,float('nan')],'B':[1,1,0,0]}, index=[2,3,4,1], columns=['Date', 'A', 'B'])
    # df = df.fillna(0.0)
    # df = df.replace(np.float64('nan'),0.0)
    
    tv = tabView(df)
    tv.show()
    tv.select(1,1)

    app.exec()