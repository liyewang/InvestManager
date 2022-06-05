from PySide6.QtWidgets import QTableView, QApplication, QHeaderView, QWidget, QMessageBox, QAbstractItemView
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QRect
from PySide6.QtGui import QColor, QKeyEvent
import pandas as pd

FORE = 0
BACK = 1

FORE_CRIT = 0xbf0000
BACK_CRIT = 0xffdfdf
COLOR_CRIT = (FORE_CRIT, BACK_CRIT)
FORE_WARN = 0xbfbf00
BACK_WARN = 0xffffdf
COLOR_WARN = (FORE_WARN, BACK_WARN)
FORE_INFO = 0x00bfbf
BACK_INFO = 0xdfffff
COLOR_INFO = (FORE_INFO, BACK_INFO)

LV_CRIT = 0
LV_WARN = 1
LV_INFO = 2

COLOR = (COLOR_CRIT, COLOR_WARN, COLOR_INFO)
MSG_BOX = (QMessageBox.critical, QMessageBox.warning, QMessageBox.information)
MSG_TAG = ('CRITICAL', 'WARNING', 'INFORMATION')

class basView(QTableView):
    def __init__(self, parent: QWidget | None = None) -> None:
        QTableView.__init__(self, parent)
        # self.resize(1280, 720)
        # self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setAlternatingRowColors(True)
        # self.setSelectionBehavior(QTableView.SelectRows)
        self.setAutoScroll(False)
        return

class basMod(QAbstractTableModel):
    def __init__(self, data: pd.DataFrame, tabView: QTableView | None = None, parent: QWidget | None = None) -> None:
        QAbstractTableModel.__init__(self, parent)
        self.error = ()
        self.__tab = data.copy()
        if tabView:
            self.view = tabView()
        else:
            self.view = basView()
        self.view.setModel(self)
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
            self.__tab.iat[index.row(), index.column()] = value
            return True
        return False

    def _raise(
        self, args: tuple,
        level: int = LV_CRIT,
        prt: bool = True,
        foreColor: bool = True,
        backColor: bool = True,
        msgBox: bool = True
        ) -> None:
        if type(args) is not tuple or len(args) == 0:
            return
        self.error = args
        if prt:
            print(args[0])
        self.beginResetModel()
        idx = None
        if len(args) >= 2 and type(args[1]) is set:
            for v in args[1]:
                if type(v) is tuple and len(v) == 4:
                    if foreColor:
                        self.setColor(FORE, COLOR[level][FORE], v[0], v[1], v[2], v[3])
                    if backColor:
                        self.setColor(BACK, COLOR[level][BACK], v[0], v[1], v[2], v[3])
                    if idx is None:
                        for row in range(v[1], v[1] + v[3]):
                            if not self.view.isRowHidden(row):
                                for col in range(v[0], v[0] + v[2]):
                                    if not self.view.isColumnHidden(col):
                                        idx = self.index(row, col)
                                        break
                                break
        self.endResetModel()
        if msgBox:
            if idx is not None:
                self.view.scrollToBottom()
                self.view.scrollTo(idx)
            if type(args[0]) is str:
                MSG_BOX[level](None, MSG_TAG[level], args[0])
            else:
                MSG_BOX[level](None, MSG_TAG[level], str(args))
        return

    def table(self, data: pd.DataFrame | None = None) -> pd.DataFrame:
        if data is not None:
            self.beginResetModel()
            self.__tab = data.copy()
            self.endResetModel()
        return self.__tab.copy()

    def select(self, row: int = -1, col: int = -1) -> None:
        auto = self.view.hasAutoScroll()
        self.view.setAutoScroll(True)
        if row >= 0 and col >= 0:
            self.view.setCurrentIndex(self.index(row, col))
        elif row >= 0:
            self.view.selectRow(row)
        elif col >= 0:
            self.view.selectColumn(col)
        else:
            self.view.selectAll()
        self.view.setAutoScroll(auto)
        return

    def __colorMap(self, colorMap: dict, row: int, col: int) -> QColor | None:
        for color, rects in colorMap.items():
            for rect in rects:
                # if type(rect) is not QRect:
                #     continue
                if rect.contains(col, row):
                    return QColor(color)
        return None

    def setColor(
        self,
        item: int | None = None,
        color: int | None = None,
        left: int = 0,
        top: int = 0,
        width: int = 0,
        height: int = 0
        ) -> None:
        if item is None:
            colorMaps = (self.__ForeColor, self.__BackColor)
        elif item == FORE:
            colorMaps = (self.__ForeColor,)
        elif item == BACK:
            colorMaps = (self.__BackColor,)
        else:
            colorMaps = ()
        rect = QRect(left, top, width, height)
        for colorMap in colorMaps:
            if rect.isValid():
                if color is None:
                    for _color, rects in colorMap.items():
                        for _rect in rects.copy():
                            # if type(_rect) is not QRect:
                            #     continue
                            if _rect.intersects(rect):
                                colorMap[_color].remove(_rect)
                elif color in colorMap:
                    colorMap[color].add(rect)
                else:
                    colorMap[color] = {rect}
            elif color is None:
                for _color in colorMap.keys():
                    colorMap[_color].clear()
            elif color in colorMap:
                colorMap[color].clear()
        return

    def adjColor(self, x0: int = 0, y0: int = 0, x1: int = 0, y1: int = 0) -> None:
        for colorMap in (self.__ForeColor, self.__BackColor):
            for color, rects in colorMap.items():
                for rect in rects:
                    # if type(rect) is not QRect:
                    #     continue
                    if x0 < x1:
                        if rect.left() >= x0:
                            rect.translate(x1 - x0, 0)
                        elif rect.right() > x0:
                            rect2 = QRect(rect)
                            rect.setRight(x0)
                            rect2.setLeft(x0)
                            rect2.translate(x1 - x0, 0)
                            colorMap[color].add(rect2)
                    elif x0 > x1:
                        if rect.left() >= x0:
                            rect.translate(x1 - x0, 0)
                        elif rect.left() >= x1:
                            rect.setLeft(x0)
                            rect.translate(x1 - x0, 0)
                        elif rect.right() > x0:
                            rect.setWidth(rect.width() + x1 - x0)
                        elif rect.right > x1:
                            rect.setRight(x1)
                    if y0 < y1:
                        if rect.top() >= y0:
                            rect.translate(0, y1 - y0)
                        elif rect.bottom() > y0:
                            rect2 = QRect(rect)
                            rect.setBottom(y0)
                            rect2.setTop(y0)
                            rect2.translate(0, y1 - y0)
                            colorMap[color].add(rect2)
                    elif y0 > y1:
                        if rect.top() >= y0:
                            rect.translate(0, y1 - y0)
                        elif rect.top() >= y1:
                            rect.setTop(y0)
                            rect.translate(0, y1 - y0)
                        elif rect.bottom() > y0:
                            rect.setHeight(rect.height() + y1 - x0)
                        elif rect.bottom() > y1:
                            rect.setBottom(y1)
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
    df = pd.DataFrame(data={'Date':dt,'A':[4,3,2,1],'B':[1,1,0,0]}, index=[2,3,4,1], columns=['Date', 'A', 'B'])
    # df = df.fillna(0.0)
    # df = df.replace(np.float64('nan'),0.0)
    
    tv = basMod(df)
    tv.show()

    app.exec()