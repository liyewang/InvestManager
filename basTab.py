from PySide6.QtWidgets import QTableView, QApplication, QHeaderView, QWidget, QMessageBox
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QRect
from PySide6.QtGui import QColor
from pandas import DataFrame, isna

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

        # self.setContextMenuPolicy(Qt.ActionsContextMenu)
        # self.setContextMenuPolicy(Qt.CustomContextMenu)
        # action = QAction('test2', self)
        # action.triggered.connect(self.test)
        # self.addAction(action)
        # self.customContextMenuRequested.connect(self.test)
        # header = self.horizontalHeader()
        # header.setContextMenuPolicy(Qt.CustomContextMenu)
        # header.addAction(action)
        # header.customContextMenuRequested.connect(self.test)
        return

    # def test(self, pos):
    #     menu = QMenu(self)
    #     act_del = menu.addAction('test2')
    #     action = menu.exec(self.mapToGlobal(pos))
    #     if action == act_del:
    #         print('test2')
    #         print(pos)

class basMod(QAbstractTableModel):
    def __init__(self, data: DataFrame, tabView: QTableView | None = None, parent: QWidget | None = None) -> None:
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

    def data(self, index: QModelIndex, role: int) -> str | QColor | None:
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            v = self.__tab.iat[index.row(), index.column()]
            if isna(v):
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
        # self.beginResetModel()
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
        # self.endResetModel()
        topLeft = self.index(0, 0)
        bottomRight = self.index(self.__tab.index.size - 1, self.__tab.columns.size - 1)
        self.dataChanged.emit(topLeft, bottomRight, [Qt.ForegroundRole, Qt.BackgroundRole])
        if msgBox:
            if idx is not None:
                # self.view.scrollToBottom()
                self.view.scrollTo(idx)
            if type(args[0]) is str:
                MSG_BOX[level](None, MSG_TAG[level], args[0])
            else:
                MSG_BOX[level](None, MSG_TAG[level], str(args))
        return

    def table(self, data: DataFrame | None = None) -> DataFrame:
        if data is not None:
            # self.beginResetModel()
            self.layoutAboutToBeChanged.emit()
            self.__tab = data.copy()
            # self.endResetModel()
            self.layoutChanged.emit()
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

    def __colorMap(self, colorMap: dict[int, set[QRect]], row: int, col: int) -> QColor | None:
        for color, rects in colorMap.items():
            for rect in rects:
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
                    for rects in colorMap.values():
                        for _rect in rects.copy():
                            if rect.intersects(_rect):
                                rects.remove(_rect)
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
                rects_new = set()
                for rect in rects.copy():
                    rect1 = QRect(rect)
                    if x0 < x1:
                        if rect1.left() >= x0:
                            rect1.translate(x1 - x0, 0)
                        elif rect1.right() > x0:
                            rect2 = QRect(rect1)
                            rect1.setRight(x0)
                            rect2.setLeft(x0)
                            rect2.translate(x1 - x0, 0)
                            rects_new.add(rect2)
                    elif x0 > x1:
                        if rect1.left() >= x0:
                            rect1.translate(x1 - x0, 0)
                        elif rect1.left() >= x1:
                            rect1.setLeft(x0)
                            rect1.translate(x1 - x0, 0)
                        elif rect1.right() > x0:
                            rect1.setWidth(rect1.width() + x1 - x0)
                        elif rect1.right > x1:
                            rect1.setRight(x1)
                    if y0 < y1:
                        if rect1.top() >= y0:
                            rect1.translate(0, y1 - y0)
                        elif rect1.bottom() > y0:
                            rect2 = QRect(rect1)
                            rect1.setBottom(y0)
                            rect2.setTop(y0)
                            rect2.translate(0, y1 - y0)
                            rects_new.add(rect2)
                    elif y0 > y1:
                        if rect1.top() >= y0:
                            rect1.translate(0, y1 - y0)
                        elif rect1.top() >= y1:
                            rect1.setTop(y0)
                            rect1.translate(0, y1 - y0)
                        elif rect1.bottom() > y0:
                            rect1.setHeight(rect1.height() + y1 - y0)
                        elif rect1.bottom() > y1:
                            rect1.setBottom(y1)
                    if rect1.height() > 0 and rect1.width() > 0:
                        rects_new.add(rect1)
                colorMap[color] = rects_new
        return

    def show(self) -> None:
        self.view.show()
        return


if __name__ == '__main__':
    from pandas import to_datetime, read_csv

    app = QApplication()

    # df = read_csv('iris.csv')
    dt = to_datetime('2022-04-10', format=r'%Y/%m/%d')
    # dt = DatetimeIndex(['2022-04-11'])
    # dt = to_datetime('2022-04-10asd', errors='coerce')
    df = DataFrame(data={'Date':dt,'A':[4,3,2,1],'B':[1,1,0,0]}, index=[2,3,4,1], columns=['Date', 'A', 'B'])
    # df = df.fillna(0.0)
    # df = df.replace(np.float64('nan'),0.0)

    tv = basMod(df)
    tv.show()
    # tv.table(df.iloc[:2, :])

    app.exec()