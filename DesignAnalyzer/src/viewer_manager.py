

from PyQt5.QtWidgets import QTableView, QHeaderView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt5.QtCore import Qt


import pandas as pd

from PyQt5.QtWidgets import QTabWidget, QLabel, QWidget, QVBoxLayout, QPushButton, QScrollArea, QGridLayout, QStackedLayout, QFrame
from PyQt5.QtCore import QAbstractTableModel, QVariant, QModelIndex

from layout_draw import PyQtGraphLayoutWithScales
from layout_plot import BasePlotView, BarChartView, WorldMapWidget

from vtk_draw import VTKWidgetWrapper



class ManageResultsTabs:
    def __init__(self):
        self.tabWidget = QTabWidget()
        self.tables = {}           # tabName -> ResultsTableView
        self.commands = {}         # tabName -> analysisCommand

        self.defaultResultsTabName = "Result"

        self.addNewTab(self.defaultResultsTabName, "Default analysis command")

    def addNewTab(self, tabName, analysisCommand):
        if tabName in self.tables:
            return  # avoid duplicates

        self.removeTabByTitle(self.defaultResultsTabName)

        tab = QWidget()
        layout = QVBoxLayout()

        tableView = ResultsTableView()
        layout.addWidget(tableView)
        tab.setLayout(layout)

        index = self.tabWidget.addTab(tab, tabName)
        self.tabWidget.setTabToolTip(index, analysisCommand)
        self.tabWidget.setCurrentIndex(index)

        self.tables[tabName] = tableView
        self.commands[tabName] = analysisCommand

    def removeTabByTitle(self, tabName: str):
        for i in range(self.tabWidget.count()):
            if self.tabWidget.tabText(i) == tabName:
                self.tabWidget.removeTab(i)
                return True
        return False


    def getResultsTable(self, tabName):
        return self.tables.get(tabName, None)

    def getCommandLine(self, tabName):
        return self.commands.get(tabName, "")

    def getTabWidget(self):
        return self.tabWidget

    def deleteAllTabs(self):
        self.tabWidget.clear()
        self.tables.clear()
        self.commands.clear()

    def isTabExist(self, tabName):
        return tabName in self.tables

    def setOutputsForTab(self, tabName, outputs):
        tableView = self.tables.get(tabName)
        if tableView:
            tableView.setOutputs(outputs)

    def getDataFrameForTab(self, tabName):
        tableView = self.tables.get(tabName)
        if tableView:
            return tableView.getDataFrame()
        return None


class TableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = PandasTableModel()
        self.setModel(self.model)

        self._onItemClickCallback = None
        self._onItemSelectedCallback = None

        self.clicked.connect(self._handleClick)
        self.selectionModel().selectionChanged.connect(self._handleSelection)

        self.horizontalHeader().sectionClicked.connect(self._handleHeaderClick)

    def loadFromDataFrame(self, df: pd.DataFrame):
        self.model.setDataFrame(df)
        self.setModel(self.model)
        self.resizeAllColumns()

    def registerOnItemClickCallback(self, callback):
        self._onItemClickCallback = callback

    def registerOnItemSelectedCallback(self, callback):
        self._onItemSelectedCallback = callback

    def _handleClick(self, index):
        """Called when a cell is clicked."""
        if self._onItemClickCallback and index.isValid():
            col_name = self.model.headerData(index.column(), Qt.Horizontal)
            value = self.model.data(index, Qt.DisplayRole)
            self._onItemClickCallback({col_name: [value]})

    def _handleSelection(self, selected, deselected):
        """Called when one or more cells are selected."""
        if not self._onItemSelectedCallback:
            return

        result = {}
        for index in selected.indexes():
            if not index.isValid():
                continue
            col_name = self.model.headerData(index.column(), Qt.Horizontal)
            value = self.model.data(index, Qt.DisplayRole)
            result.setdefault(col_name, []).append(value)

        if result:
            self._onItemSelectedCallback(result)

    def _handleHeaderClick(self, logicalIndex):
        """Called when a column header is clicked."""
        if not self._onItemSelectedCallback:
            return

        col_name = self.model.headerData(logicalIndex, Qt.Horizontal)
        column_data = self.model._df.iloc[:, logicalIndex].astype(str).tolist()
        self._onItemSelectedCallback({col_name: column_data})

    def clearTable(self):
        self.model.setDataFrame(pd.DataFrame())

    def addRow(self, rowData):
        self.model.appendRow(rowData)

    def deleteRow(self, rowIndex):
        self.model.removeRow(rowIndex)

    def getDataFrame(self):
        return self.model._df.copy()

    def highlightData(self, data_dict):
        """Highlight matching cells based on {column_name: [list_of_values]}."""
        self.model.highlightCells(data_dict)

    def resizeAllColumns(self):
        for i in range(self.model.columnCount()):
            self.resizeColumnToContents(i)



class ResultsTableView(TableView):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setOutputs(self, outputs):
        """
        Converts: [(col_name, [val1, val2, ...]), ...]
        To: pandas DataFrame and loads it.
        """
        try:
            data = {}
            max_len = max((len(values) for _, values in outputs), default=0)
            for col_name, values in outputs:
                padded = values + [''] * (max_len - len(values))
                data[col_name] = padded
            df = pd.DataFrame(data)
            self.loadFromDataFrame(df)
        except Exception as e:
            print(f"Failed to load outputs: {e}")



class ManageViewerTabs(QWidget):
    def __init__(self, viewer_type="DRAW", width=600, height=400, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.tab_counter = 1
        self.viewer_map = {}
        
        self.inputTabName = 'Input Data'
        self.inputTabToolTip = "Shows data from input"

        self.stackLayout = QStackedLayout(self)
        self.tabWidget = QTabWidget()
        self.stackLayout.addWidget(self.tabWidget)

        self._createTileView()
        self.stackLayout.addWidget(self.tileScrollArea)
        self.stackLayout.setCurrentIndex(0)  # Start in regular tab view

        self.addTabByType(viewer_type, self.inputTabName, self.inputTabToolTip)

    def currentWidget(self):
        return self.tabWidget.currentWidget()

    def _createTileView(self):
        self.tileContainer = QWidget()
        self.tileLayout = QGridLayout(self.tileContainer)

        self.tileScrollArea = QScrollArea()
        self.tileScrollArea.setWidgetResizable(True)
        self.tileScrollArea.setWidget(self.tileContainer)

    def showTileFormat(self):
        while self.tileLayout.count():
            item = self.tileLayout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        for index in range(self.tabWidget.count()):
            tab_widget = self.tabWidget.widget(index)
            tab_name = self.tabWidget.tabText(index)

            # Create a tile frame
            frame = QFrame()
            frame.setFrameShape(QFrame.Box)
            frame.setStyleSheet("QFrame { background-color: #f5f5f5; }")
            frame.setFixedSize(300, 200)
            frame_layout = QVBoxLayout(frame)

            # Add a title label
            label = QLabel(tab_name)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold;")
            frame_layout.addWidget(label)

            # Create a visual preview (readonly clone or label saying "Preview Unavailable")
            preview = self._createWidgetPreview(tab_widget)
            frame_layout.addWidget(preview)

            # Allow click to select
            def make_handler(i=index):
                def handler(event):
                    self._selectTabFromTile(i)
                return handler

            frame.mousePressEvent = make_handler()
            self.tileLayout.addWidget(frame, index // 2, index % 2)

        self.stackLayout.setCurrentWidget(self.tileScrollArea)

    def showRegularFormat(self):
        self.stackLayout.setCurrentWidget(self.tabWidget)

    def _selectTabFromTile(self, index):
        self.tabWidget.setCurrentIndex(index)
        self.showRegularFormat()

    def _createWidgetPreview(self, widget):
        # Take a snapshot (works even if not visible, but better if visible)
        pixmap = widget.grab()

        # Resize to a smaller thumbnail size
        thumbnail = pixmap.scaled(280, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Set into QLabel
        label = QLabel()
        label.setPixmap(thumbnail)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("background-color: white; border: 1px solid #ccc;")
        return label


    def addTabByType(self, viewer_type, tab_name='', tool_tip=''):
        tab_widget = None
        if viewer_type == "VTK":
            tab_widget = VTKWidgetWrapper(width=self.width, height=self.height)
        elif viewer_type == "DRAW":
            tab_widget = PyQtGraphLayoutWithScales(width=self.width, height=self.height)
        elif viewer_type == "PLOT":
            tab_widget = BarChartView()
        elif viewer_type == "TABLE":
            tab_widget = self._createTableWidget()
        elif viewer_type == "WORLD_MAP":
            tab_widget = WorldMapWidget()

        if tab_widget:
            if not tab_name:
                tab_name = f"{viewer_type}-{self.tab_counter}"
                self.tab_counter += 1
            index = self.tabWidget.addTab(tab_widget, tab_name)
            self.tabWidget.setCurrentIndex(index)
            self.tabWidget.setTabToolTip(index, tool_tip)
            
            self.viewer_map[tab_name] = tab_widget
            return tab_widget
        return None

    def _createTableWidget(self):
        return TableView()

    def setTableDataFrameInputTab(self, df):
        input_tab = self.getInputTabWidget()
        if isinstance(input_tab, QTableView):
            input_tab.loadFromDataFrame(df)

    def getSelectedTabWidget(self):
        return self.tabWidget.currentWidget()

    def getTabWidgetByTabName(self, tabName):
        for index in range(self.tabWidget.count()):
            if self.tabWidget.tabText(index) == tabName:
                return self.tabWidget.widget(index)
        return None

    def getInputTabWidget(self):
        return self.getTabWidgetByTabName(self.inputTabName)



class PandasTableModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()
        self._highlight = {}  # {(row, col): QColor}

    def setDataFrame(self, df):
        self._df = df
        self._highlight = {}
        self.layoutChanged.emit()

    def highlightCells(self, highlight_dict):
        """Highlight all cells where column value matches one of the listed values."""
        self._highlight.clear()

        if self._df is None or self._df.empty:
            return

        for col_name, values in highlight_dict.items():
            if col_name not in self._df.columns:
                continue
            col_index = self._df.columns.get_loc(col_name)
            for row in range(len(self._df)):
                if str(self._df.iat[row, col_index]) in values:
                    self._highlight[(row, col_index)] = QColor('yellow')

        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount(), self.columnCount()))

    def rowCount(self, parent=None):
        return 0 if self._df is None else len(self._df)

    def columnCount(self, parent=None):
        return 0 if self._df is None else len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df is None:
            return QVariant()

        if role == Qt.DisplayRole:
            return str(self._df.iat[index.row(), index.column()])
        elif role == Qt.BackgroundRole:
            return self._highlight.get((index.row(), index.column()), QVariant())

        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or self._df is None:
            return QVariant()
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        else:
            return str(section + 1)
