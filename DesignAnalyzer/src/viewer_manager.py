

from PyQt5.QtWidgets import QTableView, QHeaderView
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import QMenu

import pandas as pd

from PyQt5.QtWidgets import QTabWidget, QLabel, QWidget, QVBoxLayout, QPushButton, QScrollArea, QGridLayout, QStackedLayout, QFrame
from PyQt5.QtCore import QAbstractTableModel, QVariant, QModelIndex, QSortFilterProxyModel

from layout_draw import PyQtGraphLayoutWithScales
from layout_plot import BasePlotView, BarChartView, ScatterPlotView, WorldMapWidget, PieChartView

from vtk_draw import VTKWidgetWrapper

from pdf_viewer import PDFViewer

from common import TabWidget, TabWidgetRmbPopOut

class ManageResultsTabs:
    def __init__(self, windowWidth=600, windowHeight=400):
        
        self.windowWidth = windowWidth
        self.windowHeight = windowHeight

        self.tabWidget = TabWidget()
        self.tabWidget.addRmbMenu([TabWidgetRmbPopOut(self.windowWidth, self.windowHeight)])

        self.tables = {}           # tabName -> ResultsTableView
        self.commands = {}         # tabName -> analysisCommand

        self.defaultResultsTabName = "Result"

        self.addNewTab(self.defaultResultsTabName, "Default analysis command")

    def addNewTab(self, tabName, analysisCommand, _tableView=None):
        if tabName in self.tables:
            return  # avoid duplicates

        self.removeTabByTitle(self.defaultResultsTabName)

        tab = QWidget()
        layout = QVBoxLayout()

        tableView = _tableView

        if _tableView == None:
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


class TableRmbMenuBase:
    def __init__(self, name):
        self.name = name

    def onClick(self, tableView):
        """Override in derived class to handle menu click."""
        pass

class TableRmbMenuSort(TableRmbMenuBase):
    def __init__(self, name="Sort", ascending=True):
        super().__init__(name)
        self.ascending = ascending

    def onClick(self, tableView):
        # Sort the clicked column ascending as an example
        tableView.sortColumn(tableView.rmb_clicked_col_index, self.ascending)


class TableView(QTableView):
    def __init__(self, _model=None, parent=None):
        super().__init__(parent)
        
        self.model = _model
        if _model == None:
            self.model = PandasTableModel()

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.setModel(self.proxy_model)


        # Everything related to RMB
        self._rmb_menu = None
        self._rmb_menu_items = []
        self.rmb_clicked_col_index = None
        self.rmb_clicked_column_name = None
        sort_l2h_menu_item = TableRmbMenuSort("Sort - low to high", True)
        sort_h2l_menu_item = TableRmbMenuSort("Sort - high to low", False)
        self.addRmbMenu(sort_l2h_menu_item)
        self.addRmbMenu(sort_h2l_menu_item)


        self._onItemClickCallback = None
        self._onItemSelectedCallback = None
        self._default_alignment = Qt.AlignLeft | Qt.AlignVCenter

        self.clicked.connect(self._handleClick)
        self.selectionModel().selectionChanged.connect(self._handleSelection)
        self.horizontalHeader().sectionClicked.connect(self._handleHeaderClick)


    def addRmbMenu(self, itemObj):
        if not hasattr(self, "_rmb_menu") or self._rmb_menu is None:
            self._rmb_menu = QMenu(self)
        self._rmb_menu_items.append(itemObj)
        action = self._rmb_menu.addAction(itemObj.name)
        # Connect the action to call the item's onClick with self as argument
        action.triggered.connect(lambda checked, obj=itemObj: obj.onClick(self))


    def contextMenuEvent(self, event):
        # Get the position of the click
        pos = event.pos()
        # Map to global position for menu
        global_pos = event.globalPos()
        # Get the column index at the click position
        col = self.columnAt(pos.x())
        col_name = None
        if col >= 0:
            col_name = self.model.headerData(col, Qt.Horizontal)
        # Optionally, pass col or col_name to your RMB menu items
        if hasattr(self, "_rmb_menu") and self._rmb_menu is not None:
            # Example: store for use in menu actions
            self.rmb_clicked_col_index = col
            self.rmb_clicked_column_name = col_name
            self._rmb_menu.exec_(global_pos)


    def applyColumnColorGradient(self, col_name: str, lowColor: str, highColor: str):
        """Apply a color gradient to a column based on its values."""

        if not pd.api.types.is_numeric_dtype(self.model._df[col_name]):
            raise ValueError(f"Column '{col_name}' is not numeric. Gradient coloring requires numeric data.")

        if col_name not in self.model._df.columns:
            raise ValueError(f"Column '{col_name}' not found.")
        if not QColor(lowColor).isValid() or not QColor(highColor).isValid():
            raise ValueError("Invalid color(s).")
        self.model.setColumnGradient(col_name, lowColor, highColor)
        self.viewport().update()


    def loadFromDataFrame(self, df: pd.DataFrame):
        self.model.setDataFrame(df)
        self.proxy_model.invalidateFilter()
        self.setModel(self.proxy_model)
        self.resizeAllColumns()

    def colorAlternateRows(self, color: str):
        """Color alternate rows with the given color and its lighter version."""
        base_color = QColor(color)
        if not base_color.isValid():
            raise ValueError(f"Invalid color: {color}")
        lighter_color = base_color.lighter(130)  # 130% lighter
        self.model.setAlternateRowColors((base_color.name(), lighter_color.name()))
        self.viewport().update()

    def sortColumn(self, column: int, ascending: bool = True):
        """Sorts the table based on column index."""
        order = Qt.AscendingOrder if ascending else Qt.DescendingOrder
        self.sortByColumn(column, order)

    def filterColumn(self, column: int, regExp: str):
        """Applies regex-based filtering to a specific column."""
        self.proxy_model.setFilterKeyColumn(column)
        self.proxy_model.setFilterRegularExpression(regExp)

    def getColumnIndexByName(self, column_name):
        """Return column index given column name, or -1 if not found."""
        if column_name in self.model._df.columns:
            return self.model._df.columns.get_loc(column_name)
        return -1

    def hilightColumnData(self, col_name: str, expression: str):
        """Highlights data in column where expression is true, like 'x > 900' or 'x == \"Tokyo\"'."""
        try:
            df = self.model._df
            series = df[col_name]
            mask = series.apply(lambda x: self._eval_expression(x, expression))
            highlight_values = series[mask].tolist()
            self.highlightData({col_name: highlight_values})
            return highlight_values

        except Exception as e:
            print(f"Highlight error: {e}")
            return []

    def _eval_expression(self, x, expr: str):
        """Safely evaluate an expression string using x as the value."""
        try:
            # Only allow safe names and operators
            allowed_names = {"x": x}
            allowed_builtins = {}

            # Compile the expression first for safety
            code = compile(expr, "<string>", "eval")

            # Check for disallowed names (e.g., __import__, etc.)
            for name in code.co_names:
                if name not in allowed_names:
                    raise NameError(f"Use of name '{name}' not allowed in expression")

            return eval(code, {"__builtins__": allowed_builtins}, allowed_names)

        except Exception as e:
            print(f"Eval error: {e}")
            return False


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
        self.model.setHighlightRules(data_dict)

    def resizeAllColumns(self):
        for i in range(self.model.columnCount()):
            self.resizeColumnToContents(i)

    def setFontStyle(self, font: str = None, size: int = None):
        f = self.font()
        if font:
            f.setFamily(font)
        if size:
            f.setPointSize(size)
        self.setFont(f)

    def setTextColor(self, color: str):
        if not QColor(color).isValid():
            raise ValueError(f"Invalid text color: {color}")
        self.setStyleSheet(self.styleSheet() + f"\nQTableView {{ color: {color}; }}")

    def setGridStyle(self, style: str):
        style = style.lower()
        if style not in ['none', 'horizontal', 'vertical', 'both']:
            raise ValueError("Grid must be one of 'horizontal', 'vertical', 'both', 'none'.")

        if style == 'none':
            self.setShowGrid(False)
        else:
            self.setShowGrid(True)
            self.setGridStyle(Qt.SolidLine)
            css = "\nQTableView::item {"
            if style in ['horizontal', 'both']:
                css += " border-top: 1px solid gray; border-bottom: 1px solid gray;"
            if style in ['vertical', 'both']:
                css += " border-left: 1px solid gray; border-right: 1px solid gray;"
            css += " }"
            self.setStyleSheet(self.styleSheet() + css)

    def setTextAlignment(self, alignment: str):
        align_map = {
            "left": Qt.AlignLeft | Qt.AlignVCenter,
            "center": Qt.AlignCenter,
            "right": Qt.AlignRight | Qt.AlignVCenter
        }
        self._default_alignment = align_map.get(alignment.lower(), Qt.AlignLeft | Qt.AlignVCenter)
        self.viewport().update()

    def setDataFormat(self, font=None, grid=None, alignment=None, textColor=None, textSize=None):
        if font or textSize:
            self.setFontStyle(font, int(textSize) if textSize else None)
        if textColor:
            self.setTextColor(textColor)
        if grid:
            self.setGridStyle(grid)
        if alignment:
            self.setTextAlignment(alignment)




class ResultsTableView(TableView):
    def __init__(self, _model=None, parent=None):
        super().__init__(_model, parent)

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
    def __init__(self, viewer_type="DRAW", 
                 windowWidth=600, windowHeight=400,
                 layoutWidth=600, layoutHeight=400, parent=None):
        super().__init__(parent)

        self.windowWidth = windowWidth
        self.windowHeight = windowHeight
        self.layoutWidth = layoutWidth
        self.layoutHeight = layoutHeight

        self.tab_counter = 1
        self.viewer_map = {}
        
        self.inputTabName = 'Input Data'
        self.inputTabToolTip = "Shows data from input"

        self.stackLayout = QStackedLayout(self)
        
        self.tabWidget = TabWidget()
        self.tabWidget.addRmbMenu([TabWidgetRmbPopOut(self.windowWidth, self.windowHeight)])
        
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
            tab_widget = VTKWidgetWrapper(width=self.layoutWidth, height=self.layoutHeight)
        elif viewer_type == "DRAW":
            tab_widget = PyQtGraphLayoutWithScales(width=self.layoutWidth, height=self.layoutHeight)
        elif viewer_type == "BAR_CHART":
            tab_widget = BarChartView()
        elif viewer_type == "PIE_CHART":
            tab_widget = PieChartView()
        elif viewer_type == "SCATTER_PLOT":
            tab_widget = ScatterPlotView()
        elif viewer_type == "TABLE":
            tab_widget = self._createTableWidget()
        elif viewer_type == "WORLD_MAP":
            tab_widget = WorldMapWidget()
        elif viewer_type == "PDF":
            tab_widget = PDFViewer(parent=self)

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
        self._highlight_rules = {}  # {col_name: [values]}
        self._sort_column = None
        self._sort_order = Qt.AscendingOrder
        self._alternate_row_colors = None
        self._column_gradient = None  # (col_name, lowColor, highColor)


    def setDataFrame(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df.copy()
        self._highlight_rules.clear()
        self.endResetModel()

    def setHighlightRules(self, highlight_dict: dict):
        """Save the highlight rules per column – no actual cell iteration."""
        self._highlight_rules = highlight_dict.copy()
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1),
            [Qt.BackgroundRole]
        )

    def rowCount(self, parent=QModelIndex()):
        return 0 if self._df is None else len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return 0 if self._df is None else len(self._df.columns)

    def setAlternateRowColors(self, color_tuple):
        """Set colors for alternate rows: (color, lighter_color)."""
        self._alternate_row_colors = color_tuple
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1),
            [Qt.BackgroundRole]
        )

    def setColumnGradient(self, col_name, lowColor, highColor):
        self._column_gradient = (col_name, lowColor, highColor)
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1),
            [Qt.BackgroundRole]
        )

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df is None:
            return QVariant()

        row, col = index.row(), index.column()

        if role == Qt.DisplayRole:
            return str(self._df.iat[row, col])

        elif role == Qt.TextAlignmentRole:
            return getattr(self.parent(), '_default_alignment', Qt.AlignLeft | Qt.AlignVCenter)

        elif role == Qt.BackgroundRole:
            # Gradient coloring
            grad_color = self._handleGradientColoring(row, col)
            if grad_color:
                return grad_color
            # Alternate row coloring
            alt_color = self._handleAlternateRowColoring(row)
            if alt_color:
                return alt_color
            # Highlight rules
            highlight_color = self._handleHighlightRules(row, col)
            if highlight_color:
                return highlight_color

        return QVariant()

    def _handleAlternateRowColoring(self, row):
        if self._alternate_row_colors:
            color, lighter_color = self._alternate_row_colors
            return QColor(color) if row % 2 == 0 else QColor(lighter_color)
        return None

    def _handleHighlightRules(self, row, col):
        col_name = self._df.columns[col]
        highlight_vals = self._highlight_rules.get(col_name, [])
        if str(self._df.iat[row, col]) in map(str, highlight_vals):
            return QColor('yellow')
        return None

    def _handleGradientColoring(self, row, col):
        if self._column_gradient:
            grad_col, lowColor, highColor = self._column_gradient
            if self._df.columns[col] == grad_col:
                values = pd.to_numeric(self._df[grad_col], errors='coerce')
                vmin, vmax = values.min(), values.max()
                val = values.iloc[row]
                if pd.isna(val) or vmin == vmax:
                    return QColor(lowColor)
                ratio = (val - vmin) / (vmax - vmin)
                c1 = QColor(lowColor)
                c2 = QColor(highColor)
                r = c1.red()   + ratio * (c2.red()   - c1.red())
                g = c1.green() + ratio * (c2.green() - c1.green())
                b = c1.blue()  + ratio * (c2.blue()  - c1.blue())
                return QColor(int(r), int(g), int(b))
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or self._df is None:
            return QVariant()
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        else:
            return str(section + 1)


