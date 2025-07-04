

from PyQt5.QtWidgets import QTableView, QHeaderView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt

import pandas as pd

from PyQt5.QtWidgets import QTabWidget, QWidget, QVBoxLayout
from PyQt5.QtCore import QAbstractTableModel, QVariant

from layout_draw import PyQtGraphLayoutWithScales
from layout_plot import PlotWithScales

from vtk_draw import VTKWidgetWrapper


class ManageResultsTabs:
    def __init__(self):
        self.tabWidget = QTabWidget()
        self.tables = {}           # tabName -> QTableView
        self.models = {}           # tabName -> ResultsTableModel
        self.commands = {}         # tabName -> analysisCommand

        self.addNewTab("Result", "Default analysis command")

    def addNewTab(self, tabName, analysisCommand):
        if tabName in self.tables:
            return  # Do not duplicate

        tab = QWidget()
        layout = QVBoxLayout()

        # Create TableView and its model
        tableView = QTableView()
        model = ResultsTableModel()  # initially empty
        tableView.setModel(model)

        layout.addWidget(tableView)
        tab.setLayout(layout)

        index = self.tabWidget.addTab(tab, tabName)
        self.tabWidget.setTabToolTip(index, analysisCommand)

        self.tables[tabName] = tableView
        self.models[tabName] = model
        self.commands[tabName] = analysisCommand

    def getResultsTable(self, tabName):
        """Returns the QTableView for a given tab."""
        return self.tables.get(tabName, None)

    def getResultsModel(self, tabName):
        """Returns the ResultsTableModel for a given tab."""
        return self.models.get(tabName, None)

    def getCommandLine(self, tabName):
        return self.commands.get(tabName, "")

    def deleteAllTabs(self):
        self.tabWidget.clear()
        self.tables.clear()
        self.models.clear()
        self.commands.clear()

    def isTabExist(self, tabName):
        return tabName in self.tables

    def getTabWidget(self):
        return self.tabWidget



class ResultsTableModel(QAbstractTableModel):
    def __init__(self, outputs=None, parent=None):
        super().__init__(parent)
        self.headers = []
        self.data_matrix = []  # List of lists (2D)

        if outputs:
            self.setDataFromOutputs(outputs)

    def setDataFromOutputs(self, outputs):
        """
        Takes outputs in form: [(col_name, [val1, val2, ...]), ...]
        and stores them in self.data_matrix and self.headers
        """
        self.beginResetModel()
        self.headers = [arg_name for arg_name, _ in outputs]
        max_rows = max((len(vals) for _, vals in outputs), default=0)
        self.data_matrix = []

        for row in range(max_rows):
            row_data = []
            for _, values in outputs:
                row_data.append(str(values[row]) if row < len(values) else "")
            self.data_matrix.append(row_data)
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self.data_matrix)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return self.data_matrix[index.row()][index.column()]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.headers[section]
        else:
            return str(section + 1)

    def addRow(self, row_data):
        """Appends a new row (as a list of strings)."""
        if len(row_data) != len(self.headers):
            raise ValueError("Row length must match number of columns.")
        self.beginInsertRows(self.createIndex(0, 0), self.rowCount(), self.rowCount())
        self.data_matrix.append(row_data)
        self.endInsertRows()

    def deleteRow(self, row):
        """Deletes row at index `row`."""
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(self.createIndex(0, 0), row, row)
            self.data_matrix.pop(row)
            self.endRemoveRows()

    def clear(self):
        self.beginResetModel()
        self.headers = []
        self.data_matrix = []
        self.endResetModel()



class ManageViewerTabs(QTabWidget):
    def __init__(self, viewer_type="DRAW", width=600, height=400, parent=None):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.tab_counter = 1
        self.viewer_map = {}  # tabName -> widget

        self.inputTabName = 'Input Data'

        self.addTabByType(viewer_type, self.inputTabName)

    def addTabByType(self, viewer_type, tab_name=None):
        tab_widget = None
        if viewer_type == "VTK":
            tab_widget = VTKWidgetWrapper(width=self.width, height=self.height)
        elif viewer_type == "DRAW":
            tab_widget = PyQtGraphLayoutWithScales(width=self.width, height=self.height)
        elif viewer_type == "PLOT":
            tab_widget = PlotWithScales(width=self.width, height=self.height)
        elif viewer_type == "TABLE":
            tab_widget = self._createTableWidget()

        if tab_widget:
            if not tab_name:
                tab_name = f"{viewer_type}-{self.tab_counter}"
                self.tab_counter += 1
            self.addTab(tab_widget, tab_name)
            self.viewer_map[tab_name] = tab_widget
            return tab_widget
        return None

    def _createTableWidget(self):
        view = TableView()
        return view
    
    def setTableDataFrameInputTab(self, df):
        input_tab = self.getInputTabWidget()
        if isinstance(input_tab, QTableView):
            input_tab.loadFromDataFrame(df)
        else:
            print("Input tab is not a QTableView instance.")


    def getSelectedTabWidget(self):
        """Returns the widget of the currently selected tab."""
        return self.tabWidget.currentWidget()


    def getTabWidgetByTabName(self, tabName):
        """Returns the widget corresponding to the given tab name, or None if not found."""
        for index in range(self.tabWidget.count()):
            if self.tabWidget.tabText(index) == tabName:
                return self.tabWidget.widget(index)
        return None
    
    def getInputTabWidget(self):
        return self.getTabWidgetByTabName(self.inputTabName)



class TableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = PandasTableModel()
        self.setModel(self.model)

        # Stretch columns to fill the view
        # self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.setAlternatingRowColors(True)
        # self.setSortingEnabled(True)

    def loadFromDataFrame(self, df: pd.DataFrame):
        """Load data from a pandas DataFrame."""
        self.model.setDataFrame(df)
        self.setModel(self.model)

        # Optionally, set column widths based on content
        for i in range(self.model.columnCount()):
            self.resizeColumnToContents(i)

    def clearTable(self):
        """Remove all data from the table."""
        self.model.removeRows(0, self.model.rowCount())

    def addRow(self, rowData):
        """Add a new row. Accepts a list of strings or values."""
        items = [QStandardItem(str(val)) for val in rowData]
        self.model.appendRow(items)

    def deleteRow(self, rowIndex):
        """Delete a specific row by index."""
        if 0 <= rowIndex < self.model.rowCount():
            self.model.removeRow(rowIndex)



class PandasTableModel(QAbstractTableModel):
    def __init__(self, df=None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    def setDataFrame(self, df):
        try:
            self._df = df
            self.layoutChanged.emit()
        except Exception as e:
            print(f"Failed to set DF: {e}")

    def rowCount(self, parent=None):
        return 0 if self._df is None else len(self._df)

    def columnCount(self, parent=None):
        return 0 if self._df is None else len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df is None:
            return QVariant()
        if role == Qt.DisplayRole:
            return str(self._df.iat[index.row(), index.column()])
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if self._df is None or role != Qt.DisplayRole:
            return QVariant()

        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        else:
            return str(section)
        
