from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget, QTabWidget, QGraphicsView, QListWidgetItem,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit,
    QAction, QFileDialog, QMessageBox, QFrame, QTableView, QGridLayout, 
    QStyleOptionComboBox, QStyle, QStylePainter, QScrollArea
)

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot, QAbstractTableModel


from PyQt5.QtGui import QBrush, QColor, QTextCharFormat, QCursor, QPen, QPainter, QFont, QStandardItemModel, QStandardItem

from PyQt5.QtCore import Qt, pyqtSlot

import sys

import json

import os
import psutil
import threading

from typing import Any, Dict
import pandas as pd

from main_menu import MainMenuAndTBar
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from bottom_area import BottomArea

from session import Session

from common import PlaceholderTextEdit, ScrollingLabel, global_signals

from predicates import Predicates, CreateBarChart, CreateScatterPlot, CreatePieChart, SqlQueryPredicate, RunPCA, RunKMeans

from llm_manager import LLMManager, global_LLM_manager

from viewer_manager import ManageViewerTabs, ManageResultsTabs

from error_log_manager import ErrorManager, UILogHandler


import logging
from datetime import datetime


class ReadSessionMenuItem(MenuItemAbstract):
    def __init__(self, session, inputTab):
        self.session = session
        self.inputTab = inputTab

    def onClick(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a session JSON file")

        if file_path:
            self.session.readSession(file_path)

            # Iterate over all keys in the session data
            for group in self.session._data.keys():
                sources = self.session.getAttr(group)
                for source in sources:
                    items = self.session.getAttr(group, source)
                    self.inputTab.addItems(group, source, items)


class WriteSessionMenuItem(MenuItemAbstract):
    def __init__(self, session, inputTab):
        self.session = session
        self.inputTab = inputTab

    def onClick(self):

        groups = self.inputTab.getAllGroups()
        for group in groups:
            group_dict = {}
            sources = self.inputTab.getAllGroupSources(group)
            for source in sources:
                items = self.inputTab.getAllItemsInList(group, source)
                group_dict[source] = items  # accumulate items for each source
            self.session.setAttr(group, group_dict)  # set once per group

        self.session.dump()

        filename, _ = QFileDialog.getSaveFileName(
            parent=None,
            caption="Create new session JSON File",
            directory=".",
            filter="Text Files (*.json);;All Files (*)"
        )

        if filename:
            self.session.writeSession(filename)


class ZoomOutMenuItem(MenuItemAbstract):
    def __init__(self, _drawArea):
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.zoomOut()

class ZoomInMenuItem(MenuItemAbstract):
    def __init__(self, _drawArea):
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.zoomIn()

class ZoomFitMenuItem(MenuItemAbstract):
    def __init__(self, _drawArea):
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.zoomFit()


class ZoomInToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Zoom In")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.zoomIn()

class ZoomOutToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Zoom Out")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.zoomOut()

class ZoomFitToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Zoom Fit")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.zoomFit()

class PanLeftToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Pan left")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.panLeft()


class PanRightToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Pan right")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.panRight()

class PanUpToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Pan up")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.panUp()

class PanDownToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Pan down")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.panDown()

class ShowMeshToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Show mesh")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.show_mesh()

class HideMeshToolBarItem(ToolBarItemAbstract):
    def __init__(self, _drawArea):
        super().__init__("Hide mesh")
        self.drawArea = _drawArea

    def onClick(self):
        self.drawArea.hide_mesh()

class RegularTabsToolBarItem(ToolBarItemAbstract):
    def __init__(self, _viewerTabs):
        super().__init__("Regular tabs")
        self.viewerTabs = _viewerTabs

    def onClick(self):
        self.viewerTabs.showRegularFormat()

class TileTabsToolBarItem(ToolBarItemAbstract):
    def __init__(self, _viewerTabs):
        super().__init__("Tile tabs")
        self.viewerTabs = _viewerTabs

    def onClick(self):
        self.viewerTabs.showTileFormat()



class MainUI(QMainWindow):
    # Coordinate/size constants
    WINDOW_WIDTH = 1800
    WINDOW_HEIGHT = 900

    LAYOUT_WIDTH = 800
    LAYOUT_HEIGHT = 550

    COMMAND_WIDTH = 900

    @pyqtSlot(str, dict)
    def on_signal_fire_predicate_run(self, command, args):

        print(f"Received command: {command}, args: {args}")

        pred = self.all_predicates.getPredicateObj(command)
        if not pred:
            raise ValueError(f"Analysis '{command}' got from LLM is not found.")
        
        for key, value in args.items():
            pred.updateArgUserValue(key, value)

        self.analysisActionPanel.selectItem(command)

        status = pred.execute()

        global_signals.signal_finish_predicate_run.emit(status)

    def __init__(self, PLOT_OR_DRAW="BAR_CHART"):
        
        super().__init__()

        self.PLOT_OR_DRAW = PLOT_OR_DRAW

        self.setWindowTitle("Analyzerr")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self.apply_global_styles()

        self.session = Session()

        self.all_predicates = Predicates()

        self.menu = MainMenuAndTBar(self)

        


        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.mainLayout = QVBoxLayout()
        self.centralWidget.setLayout(self.mainLayout)

        self.resultsManager = ManageResultsTabs(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self.create_top_layout()
        

        self.sentralControl = SentralControl(parent=self,
                                                window_width=self.WINDOW_WIDTH,
                                                window_height=self.WINDOW_HEIGHT,
                                                viewerTabs=self.viewerTabs,
                                                resultsManager=self.resultsManager,
                                                sourceDropDown=self.sourceDropDown)

        self.bottomArea = BottomArea(self.mainLayout, self.sentralControl,
                                self.WINDOW_WIDTH, self.WINDOW_HEIGHT, 
                                self.LAYOUT_WIDTH, self.LAYOUT_HEIGHT)

        self.bottomArea.assistantManager.signal_fire_predicate_run.connect(self.on_signal_fire_predicate_run)

        

        self.registerPredicates()

        self.setup_logging()


    def hidePredicateGroup(self, group_name):
        self.all_predicates.setGroupHidden(group_name, True)

    def create_GUI(self):

        self.readSessionMenuObj = ReadSessionMenuItem(self.session, 
                                        self.bottomArea.inputTab)
        
        self.menu.createMenuItem("File", "Read Session", self.readSessionMenuObj)

        self.writeSessionMenuObj = WriteSessionMenuItem(self.session, 
                                        self.bottomArea.inputTab)
        
        self.menu.createMenuItem("File", "Write Session", self.writeSessionMenuObj)

        self.zoomOutMenuObj = ZoomOutMenuItem(self.drawArea)
        self.menu.createMenuItem("View", "Zoom Out", self.zoomOutMenuObj)

        self.zoomInMenuObj = ZoomInMenuItem(self.drawArea)
        self.menu.createMenuItem("View", "Zoom In", self.zoomInMenuObj)

        self.zoomFitMenuObj = ZoomFitMenuItem(self.drawArea)
        self.menu.createMenuItem("View", "Zoom Fit", self.zoomFitMenuObj)


        # Create toolbar items        
        self.create_toolbar_items()

        self.push_predicates_to_command_area()

        

    def create_toolbar_items(self):

        self.zoomInToolBarItem = ZoomInToolBarItem(self.drawArea)
        self.zoomOutToolBarItem = ZoomOutToolBarItem(self.drawArea)
        self.zoomFitToolBarItem = ZoomFitToolBarItem(self.drawArea)

        self.menu.createToolbarGroupItems("zoom_items", 
                                          [self.zoomInToolBarItem,
                                          self.zoomOutToolBarItem,
                                          self.zoomFitToolBarItem])
        
        self.panLeftToolBarItem = PanLeftToolBarItem(self.drawArea)
        self.panRightToolBarItem = PanRightToolBarItem(self.drawArea)
        self.panUpToolBarItem = PanUpToolBarItem(self.drawArea)
        self.panDownToolBarItem = PanDownToolBarItem(self.drawArea)

        self.menu.createToolbarGroupItems("pan_items", 
                                          [self.panLeftToolBarItem,
                                           self.panRightToolBarItem,
                                           self.panUpToolBarItem,
                                           self.panDownToolBarItem])

        self.regularTabsToolBarItem = RegularTabsToolBarItem(self.viewerTabs)
        self.tileTabsToolBarItem = TileTabsToolBarItem(self.viewerTabs)

        self.menu.createToolbarGroupItems("tab_items", 
                                          [self.regularTabsToolBarItem,
                                          self.tileTabsToolBarItem])

        if self.PLOT_OR_DRAW == "VTK":
            self.showMeshToolBarItem = ShowMeshToolBarItem(self.drawArea)
            self.hideMeshToolBarItem = HideMeshToolBarItem(self.drawArea)
            self.menu.createToolbarGroupItems("mesh_items",
                                              [self.showMeshToolBarItem,
                                               self.hideMeshToolBarItem])



    def apply_global_styles(self):
        qss_path = os.path.join(os.path.dirname(__file__), "main.qss")

        with open(qss_path, "r") as f:
            self.setStyleSheet(f.read())

    def setup_logging(self):
        # Create logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # File and console handlers
        file_handler = logging.FileHandler('app.log')
        console_handler = logging.StreamHandler()

        # Format for logs
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Custom UI handler
        ui_handler = UILogHandler(self.bottomArea.appendLog)
        ui_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.addHandler(ui_handler)

        self.logger = logger  # Optional: store if you want to call directly

    def create_top_layout(self):
        topLayout = QHBoxLayout()

        self.viewerTabs = ManageViewerTabs(parent=self, 
                                        viewer_type=self.PLOT_OR_DRAW,
                                        windowWidth=self.WINDOW_WIDTH,
                                        windowHeight=self.WINDOW_HEIGHT,
                                        layoutWidth=self.LAYOUT_WIDTH,
                                        layoutHeight=self.LAYOUT_HEIGHT)
        
        # Access default view
        self.drawArea = self.viewerTabs.currentWidget()

        # Access the `.view` attribute only if exists
        self.layoutView = getattr(self.drawArea, "view", None)

        self.create_command_area()

        topLayout.addWidget(self.viewerTabs, stretch=4)
        topLayout.addWidget(self.commandArea, stretch=3)

        self.mainLayout.addLayout(topLayout, stretch=2)


    def push_predicates_to_command_area(self):
        
        self.analysisActionPanel.registerSelectionChangedSlot(self.updateParamLabels)

        for header in self.all_predicates.getAllGroups():
            
            if self.all_predicates.isGroupHidden(header):
                continue

            group_preds = self.all_predicates.getAllGroupPredicates(header)

            for predicate in group_preds:
                
                self.analysisActionPanel.addItem(header, predicate)
    

    def create_command_area(self):
        self.commandArea = QWidget()
        self.commandArea.setMinimumWidth(self.COMMAND_WIDTH)

        outerLayout = QHBoxLayout()
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.setSpacing(8)  # Small spacing between left and right

        # ----------------- LEFT HALF -----------------
        leftWidget = QWidget()
        leftLayout = QVBoxLayout()
        leftLayout.setContentsMargins(0, 0, 0, 0)

        # Source DropDown
        self.sourceDropDown = SourceDropDown()
        self.sourceDropDown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        leftLayout.addWidget(self.sourceDropDown)


        # leftLayout.addWidget(self._hline())

        self.analysisActionPanel = AnalysisActionPanel(self)
        leftLayout.addWidget(self.analysisActionPanel)

        # leftLayout.addWidget(self._hline())

        # Param area
        self.manageArgs = ManageArgs()
        self.manageArgs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        leftLayout.addWidget(self.manageArgs)

        # leftLayout.addWidget(self._hline())

        # Run + Stop buttons
        buttonRow = QHBoxLayout()
        self.runButton = QPushButton("Run Analysis")
        self.runButton.clicked.connect(self.runSelectedPredicate)

        self.stopButton = QPushButton("Stop Analysis")
        buttonRow.addWidget(self.runButton)
        buttonRow.addWidget(self.stopButton)
        leftLayout.addLayout(buttonRow)

        # Push everything upward
        leftLayout.addStretch()
        leftWidget.setLayout(leftLayout)

        # ----------------- RIGHT HALF -----------------
        rightWidget = QWidget()
        rightLayout = QVBoxLayout()
        rightLayout.setContentsMargins(0, 0, 0, 0)

        rightLayout.addWidget(QLabel("Results"))

        
        resultsTabs = self.resultsManager.getTabWidget()
        resultsTabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rightLayout.addWidget(resultsTabs, stretch=1)

        rightWidget.setLayout(rightLayout)

        # ----------------- Combine with Separator -----------------
        outerLayout.addWidget(leftWidget, stretch=1)

        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFrameShadow(QFrame.Sunken)
        outerLayout.addWidget(vline)

        outerLayout.addWidget(rightWidget, stretch=1)

        self.commandArea.setLayout(outerLayout)




    def _hline(self):
        """Returns a horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line


    def runSelectedPredicate(self):

        predicate_name = self.analysisActionPanel.getSelectedItem()
        try:
            # Get the expected argument names and the predicate object
            predicate = self.all_predicates.getPredicateObj(predicate_name)
        except KeyError:
            print(f"Predicate '{predicate_name}' not found.")
            return

        
        arg_values = self.manageArgs.getArgValues()

        # Set arguments and run the predicate
        predicate.setUserValueArgs(arg_values)

        # Execute the predicate
        try:
            result = predicate.execute()
            # print(f"Result of '{predicate_name}': {result}")
        except Exception as e:
            print(f"Error running predicate '{predicate_name}': {e}")
            raise

        # Fetch all output argument names and their corresponding values
        outputs = list(predicate.iterateOutputs())

        if outputs:
            unique_tab_name = predicate.getShortName()

            self.resultsManager.addNewTab(unique_tab_name, 
                                        predicate.getCompleteNameWithArgs(), _tableView=predicate.tableView)
            model = self.resultsManager.setOutputsForTab(unique_tab_name, outputs)

            self.sentralControl.addEntryForResults(unique_tab_name)
            self.sentralControl.addDataForResultsEntity(unique_tab_name, 
                                                        predicate.getDataFrame())


            predicate.onPostRun()



    def updateParamLabels(self):

        selected_name = self.analysisActionPanel.getSelectedItem()

        try:
            args_dict = self.all_predicates.getPredicateArgs(selected_name)
        except ValueError:
            args_dict = {}

        self.manageArgs.showHideArgsGuiItems(args_dict)


    def registerPredicates(self):
        
        barChartObj = CreateBarChart(self.sentralControl)
        self.all_predicates.addPredicate("charts", "create bar chart", barChartObj)

        scatterPlotObj = CreateScatterPlot(self.sentralControl)
        self.all_predicates.addPredicate("charts", "create scatter plot", scatterPlotObj)

        pieChartObj = CreatePieChart(self.sentralControl)
        self.all_predicates.addPredicate("charts", "create pie chart", pieChartObj)

        sqlQueryPredicate = SqlQueryPredicate(self.sentralControl)
        self.all_predicates.addPredicate("SQL", "execute sql query", sqlQueryPredicate)

        runPCAObj = RunPCA(self.sentralControl)
        self.all_predicates.addPredicate("PCA", "run PCA analysis", runPCAObj)

        kmeansClustererObj = RunKMeans(self.sentralControl)
        self.all_predicates.addPredicate("PCA", "run k-means clustering", kmeansClustererObj)




class SourceDropDown(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModel(QStandardItemModel(self))
        self.header_to_index = {}  # header -> index
        self.item_to_header = {}   # row index -> header

        self.setToolTip("Select a data source")  # Default tooltip for collapsed combo

        # Make border bold
        self.setStyleSheet("""
            QComboBox {
                border: 2px solid blue;
                padding: 4px;
                font-size: 16px;
            }
        """)

        self.currentIndexChanged.connect(self._updateSelectedItemBold)

    def addHeader(self, header):

        if header not in self.header_to_index:
            model = self.model()
            item = QStandardItem(header)
            item.setFlags(Qt.ItemIsEnabled)  # Non-selectable
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            model.appendRow(item)

            self.header_to_index[header] = model.indexFromItem(item).row()

    def addItem(self, header, name, selected=False):

        if header not in self.header_to_index:
            raise ValueError(f"Header '{header}' not found. Add it first with addHeader().")

        model = self.model()
        item = QStandardItem(f"  {name}")  # Indent for readability
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

        item.setToolTip(name)  # Tooltip on hover for full name
        model.appendRow(item)

        index = model.indexFromItem(item).row()
        self.item_to_header[index] = header

        # Initial font not bold for non-selected
        font = item.font()
        font.setBold(False)
        item.setFont(font)

        # ✅ Make the newly added item selected
        if selected:
            self.setCurrentIndex(index)


    def getSelected(self):
        index = self.currentIndex()
        model = self.model()
        item = model.item(index)

        if not item or not (item.flags() & Qt.ItemIsSelectable):
            return None, None  # If a header or invalid is selected

        name = item.text().strip()
        header = self.item_to_header.get(index, None)
        return header, name

    def _updateSelectedItemBold(self):
        """Make selected item bold, reset others."""
        model = self.model()
        for i in range(model.rowCount()):
            item = model.item(i)
            if item.flags() & Qt.ItemIsSelectable:
                font = item.font()
                font.setBold(i == self.currentIndex())
                item.setFont(font)

        self.update()

    
    def paintEvent(self, event):
        # Custom painter to draw selected item in bold in collapsed state
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        painter = QStylePainter(self)
        painter.drawComplexControl(QStyle.CC_ComboBox, opt)

        # Draw bold current text manually
        font = self.font()
        font.setBold(True)
        painter.setFont(font)

        text = self.currentText()
        alignment = Qt.AlignVCenter | Qt.TextSingleLine
        painter.drawItemText(opt.rect, alignment, self.palette(), self.isEnabled(), text)


class SentralControl:
    def __init__(self, parent, window_width, 
                 window_height, viewerTabs: ManageViewerTabs, 
                 resultsManager: ManageResultsTabs,
                 sourceDropDown: SourceDropDown):
        
        self.parent = parent
        self.window_width = window_width
        self.window_height = window_height
        self.viewerTabs = viewerTabs
        self.resultsManager = resultsManager
        self.sourceDropDown = sourceDropDown
        
        self.product_vertical = ""


        self.fileNameToData: Dict[str, Any] = {}

        self.global_error_manager = ErrorManager(self.parent, 
                                                 self.window_width,
                                                 self.window_height)

        self.DEF_RESOLVED_DESIGN = "DEF resolved design"

    def showMessage(self, msg: str) -> None:
        self.global_error_manager.showMessage(msg)

    def _detectFileTypeHeader(self, fileName: str) -> str:
        lower = fileName.lower()
        if lower.endswith('.csv'):
            return "CSV files"
        elif lower.endswith('.stl'):
            return "STL files"
        elif lower.endswith('.lef'):
            return "LEF files"
        elif lower.endswith('.def'):
            return self.DEF_RESOLVED_DESIGN
        else:
            return "UNKNOWN files"


    def addEntryForFile(self, fileName: str) -> None:
        fileName = os.path.basename(fileName)
        header = self._detectFileTypeHeader(fileName)

        if header == self.DEF_RESOLVED_DESIGN:
            self._setEntity(self.DEF_RESOLVED_DESIGN, self.DEF_RESOLVED_DESIGN)
        else:
            self._setEntity(header, fileName)

    def addEntryForResults(self, resultsTabName: str) -> None:
        header = "RESULTS"

        self._setEntity(header, resultsTabName)

    def _setEntity(self, header: str, name: str) -> None:
        if not header:
            raise ValueError("Header cannot be empty")

        if name in self.fileNameToData:
            return

        if header:
            self.sourceDropDown.addHeader(header)

            self.sourceDropDown.addItem(header, name)

            if header != 'RESULTS' and header != self.DEF_RESOLVED_DESIGN:
                self.sourceDropDown.addItem(header, f'all {header.lower()}', selected=True)

            self.fileNameToData[name] = None
        

    def addDataForFileEntity(self, fileName: str, data) -> None:
        fileName = os.path.basename(fileName)

        self._addDataForEntity(fileName, data)

    def addDataForResultsEntity(self, resultsTabName: str, data) -> None:

        self._addDataForEntity(resultsTabName, data)


    def _addDataForEntity(self, name: str, data) -> None:

        if name not in self.fileNameToData:
            raise ValueError(f"No entry found for file: {name}")

        self.fileNameToData[name] = data


    def getDataForSelectedEntity(self) -> list:
        """
        Returns a list of data corresponding to the selected entity.
        Handles single entities, 'all <header>' groups, and results grouping.
        """
        header, name = self.sourceDropDown.getSelected()
        if not header or not name:
            raise ValueError("No valid entity selected in the dropdown")

        if name.startswith('all ') and header != 'RESULTS':
            # Example: 'all CSV files'
            file_type_prefix = header  # e.g., "CSV files"
            matching_data = [
                data for fname, data in self.fileNameToData.items()
                if self._detectFileTypeHeader(fname) == file_type_prefix and data is not None
            ]
            return matching_data

        elif name == 'all results' or (header == 'RESULTS' and name.startswith('all ')):
            matching_data = [
                data for fname, data in self.fileNameToData.items()
                if self._detectFileTypeHeader(fname) != fname and  # crude way to filter non-file types
                fname in self.fileNameToData and data is not None and
                self._detectFileTypeHeader(fname) == 'UNKNOWN files'
            ]
            return matching_data

        else:
            # Single item selected
            if name not in self.fileNameToData:
                raise ValueError(f"No data found for entity: {name}")

            data = self.fileNameToData[name]
            return [data] if data is not None else []


    def showFileInTab(self, fileName: str,) -> None:
        fileName = os.path.basename(fileName)

        if fileName in self.fileNameToData:
            self.viewerTabs.setTableDataFrameInputTab(self.fileNameToData[fileName])

            #table = self.viewerTabs.getInputTabWidget()
            #if table:
            #    # h_vals = table.hilightColumnData("Units Sold", "> 500 and < 1000")
            #    h_vals = table.hilightColumnData("Units Sold", "equal to 934 or 413")


    def getSelectedTable(self):
        
        header, name = self.sourceDropDown.getSelected()

        table = self.resultsManager.getResultsTable(name)
        if not table:
            table = self.viewerTabs.getSelectedTabWidget()

        return table


class ManageArgs(QWidget):
    def __init__(self, parent=None, max_args=10):
        super().__init__(parent)

        self.max_args = max_args
        self.paramEdits = []

        # Main layout
        mainLayout = QVBoxLayout(self)

        # Scroll area
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        mainLayout.addWidget(self.scrollArea)

        # Container inside the scroll area
        self.scrollContent = QFrame()
        self.scrollArea.setWidget(self.scrollContent)

        # Grid layout inside scroll content
        self.paramGrid = QGridLayout(self.scrollContent)
        self.scrollContent.setLayout(self.paramGrid)

        font = QFont()
        font.setPointSize(7)
        label_width = 160

        for row in range(self.max_args):
            label = QLabel(f"Param {row + 1}")
            label.setFont(font)
            label.setFixedWidth(label_width)
            label.setToolTip(label.text())

            edit = QLineEdit()
            edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            label.hide()
            edit.hide()

            self.paramGrid.addWidget(label, row, 0)
            self.paramGrid.addWidget(edit, row, 1)

            self.paramEdits.append((label, edit))

    def showHideArgsGuiItems(self, args: dict):
        """
        Show arg-name + value as label-edit pairs using metadata:
        - Label text = arg name
        - Label tooltip = tool_tip
        - Edit text = default
        - Edit tooltip = example
        """

        # First hide everything.
        for j in range(0, self.max_args):
            label, edit = self.paramEdits[j]
            label.hide()
            edit.hide()

        i = 0
        for i, (key, meta) in enumerate(args.items()):
            if i >= self.max_args:
                break  # ignore excess

            label, edit = self.paramEdits[i]

            label.setText(key)
            label.setToolTip(meta.get('tool_tip', key))

            if meta.get('user_value') is not None:
                edit.setText(str(meta['user_value']))
            else:
                edit.setText(str(meta.get('default', '')))

            edit.setToolTip(meta.get('example', ''))

            label.show()
            edit.show()




    def getArgValues(self) -> dict:

        updated_args = {}

        for label, edit in self.paramEdits:
            if label.isVisible() and edit.isVisible():
                key = label.text()
                value = edit.text().strip()

                updated_args[key] = {
                    'user_value': value,
                }

        return updated_args



class AnalysisActionPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.group_items = {}  # group_name -> QListWidgetItem
        self.predicate_items = {}  # predicate_name -> QListWidgetItem
        self.group_to_predicates = {}  # group_name -> list of predicate_names

        layout = QVBoxLayout(self)

        # Search box
        self.searchBox = QTextEdit()
        self.searchBox.setPlaceholderText("Search for actions and analysis")
        self.searchBox.setFixedHeight(35)
        self.searchBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.searchBox)

        # List Widget
        self.listWidget = QListWidget()
        layout.addWidget(self.listWidget)

        self.listWidget.setSortingEnabled(False)
        self.listWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.searchBox.textChanged.connect(self._onSearch)

    def addItem(self, group_name, predicate_name):
        # Add group if not already present
        if group_name not in self.group_items:
            group_item = QListWidgetItem(group_name)
            group_font = QFont()
            group_font.setBold(True)
            group_item.setFont(group_font)
            
            # Set group item as non-selectable
            group_item.setFlags(Qt.ItemIsEnabled)
            group_item.setFlags(Qt.NoItemFlags)


            self.listWidget.addItem(group_item)
            self.group_items[group_name] = group_item
            self.group_to_predicates[group_name] = []

        # Avoid duplicates
        if predicate_name in self.predicate_items:
            return

        # Add predicate under group
        display_text = f"\t{predicate_name}"
        item = QListWidgetItem(display_text)
        item.setData(Qt.UserRole, predicate_name)
        item.setToolTip(f"<b>{predicate_name}</b>")

        group_item = self.group_items[group_name]  # assuming you stored it
        self.listWidget.insertItem(self.listWidget.row(group_item) + 1, item)

        self.predicate_items[predicate_name] = item
        self.group_to_predicates[group_name].append(predicate_name)


    def _onSearch(self):
        search_text = self.searchBox.toPlainText().strip().lower()
        self._resetHighlights()

        if not search_text:
            return

        # First match to scroll
        found_first = False

        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            pred_name = item.data(Qt.UserRole)
            if pred_name:
                lower_pred = pred_name.lower()
                if search_text in lower_pred:
                    item.setForeground(QColor("red"))
                    if not found_first:
                        self.listWidget.scrollToItem(item)
                        found_first = True
                else:
                    # Reset to original text
                    item.setForeground(QColor("black"))
                    # item.setText(f"\t{pred_name}")

    def _resetHighlights(self):
        for group, predicates in self.group_to_predicates.items():
            for pred_name in predicates:
                item = self.predicate_items.get(pred_name)
                if item:
                    item.setForeground(QColor("black"))


    def registerSelectionChangedSlot(self, slot_func):
        self.listWidget.itemSelectionChanged.connect(slot_func)

    def getSelectedItem(self):
        selected = self.listWidget.selectedItems()
        for item in selected:
            pred_name = item.data(Qt.UserRole)
            if pred_name:
                return pred_name
        return None

    def selectItem(self, predicate_name):
        item = self.predicate_items.get(predicate_name)
        if item:
            self.listWidget.setCurrentItem(item)
            self.listWidget.scrollToItem(item)
            self.listWidget.itemSelectionChanged.emit()
