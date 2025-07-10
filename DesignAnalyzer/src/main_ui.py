from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget, QTabWidget, QGraphicsView, QListWidgetItem,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit,
    QAction, QFileDialog, QMessageBox, QFrame, QTableView, QGridLayout, 
    QStyleOptionComboBox, QStyle, QStylePainter, QScrollArea
)


from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot, QAbstractTableModel


from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

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

from common import PlaceholderTextEdit, ScrollingLabel

from predicates import Predicates, CreateBarChart

from llm_manager import LLMManager, global_LLM_manager

from viewer_manager import ManageViewerTabs, ManageResultsTabs

import logging
from datetime import datetime

class UILogHandler(logging.Handler):
    def __init__(self, ui_log_callback):
        super().__init__()
        self.ui_log_callback = ui_log_callback

    def emit(self, record):
        log_entry = self.format(record)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.ui_log_callback(now, log_entry)


class ReadSessionMenuItem(MenuItemAbstract):
    def __init__(self, session, all_input_tabs):
        self.session = session
        self.all_input_tabs = all_input_tabs


    def onClick(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a session JSON file")

        if file_path:
            self.session.readSession(file_path)

            for tab_name, tab in self.all_input_tabs.items():
                
                list = self.session.getAttr(tab_name)
                tab.addItems(list)
                
                        



class WriteSessionMenuItem(MenuItemAbstract):
    def __init__(self, session, all_input_tabs):
        self.session = session
        self.all_input_tabs = all_input_tabs

    def onClick(self):

        for tab_name, tab in self.all_input_tabs.items():
            items = tab.getAllItemsInList()

            self.session.setAttr(tab_name, items)
            
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


class MainUI(QMainWindow):
    # Coordinate/size constants
    WINDOW_WIDTH = 1800
    WINDOW_HEIGHT = 900

    LAYOUT_WIDTH = 800
    LAYOUT_HEIGHT = 550

    COMMAND_WIDTH = 900

    @pyqtSlot(str, dict)
    def on_signal_update_command(self, command, args):

        print(f"Received command: {command}, args: {args}")

        matching_items = self.commandList.findItems(command, Qt.MatchExactly)
        if matching_items:
            self.commandList.setCurrentItem(matching_items[0])
            self.manageArgs.setArgValues(args)
        else:
            QMessageBox.warning(self, "Not Found", f"No predicate found matching: {command}")

    def __init__(self, PLOT_OR_DRAW="PLOT"):
        
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

        
        self.create_top_layout()
        
        self.sentralControl = SentralControl(self.viewerTabs, self.sourceDropDown)

        self.bottomArea = BottomArea(self.mainLayout, self.sentralControl, 
                                self.WINDOW_HEIGHT, self.LAYOUT_HEIGHT)
        
        self.bottomArea.signal_update_command.connect(self.on_signal_update_command)

        

        self.registerPredicates()

        self.setup_logging()


    def create_GUI(self):

        self.readSessionMenuObj = ReadSessionMenuItem(self.session, 
                                        self.bottomArea.all_input_tabs)
        
        self.menu.createMenuItem("File", "Read Session", self.readSessionMenuObj)

        self.writeSessionMenuObj = WriteSessionMenuItem(self.session, 
                                        self.bottomArea.all_input_tabs)
        
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

        self.viewerTabs = ManageViewerTabs(viewer_type=self.PLOT_OR_DRAW,
                                        width=self.LAYOUT_WIDTH,
                                        height=self.LAYOUT_HEIGHT)
        
        # Access default view
        self.drawArea = self.viewerTabs.currentWidget()

        # Access the `.view` attribute only if exists
        self.layoutView = getattr(self.drawArea, "view", None)

        self.create_command_area()

        topLayout.addWidget(self.viewerTabs, stretch=4)
        topLayout.addWidget(self.commandArea, stretch=3)

        self.mainLayout.addLayout(topLayout, stretch=2)


    def push_predicates_to_command_area(self):
        self.commandList.clear()  # Optional: clear existing items
        self.commandList.itemSelectionChanged.connect(self.updateParamLabels)

        for predicate in self.all_predicates.getAllPredicates().keys():
            item = QListWidgetItem(predicate)
            item.setToolTip(f"<b>{predicate}</b>")
            self.commandList.addItem(item)

    

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

        # TextEdit + OK Button row
        row2 = QHBoxLayout()
        self.commandInput = PlaceholderTextEdit("Enter command to search for analysis...")
        self.commandInput.setFixedHeight(30)
        self.commandInput.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.okButton = QPushButton("Search")
        self.okButton.clicked.connect(self.runSearchAnalysis)
        self.okButton.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        row2.addWidget(self.commandInput)
        row2.addWidget(self.okButton)
        leftLayout.addLayout(row2)

        leftLayout.addWidget(self._hline())
        leftLayout.addWidget(QLabel("Analyses & Actions"))

        # Command list
        self.commandList = QListWidget()
        self.commandList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.commandList.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        leftLayout.addWidget(self.commandList)

        leftLayout.addWidget(self._hline())

        # Param area
        self.manageArgs = ManageArgs()
        self.manageArgs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        leftLayout.addWidget(self.manageArgs)

        leftLayout.addWidget(self._hline())

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

        self.resultsManager = ManageResultsTabs()
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

    def runSearchAnalysis(self):
        command_text = self.commandInput.toPlainText()
        print(f"Command: {command_text}")

        response = global_LLM_manager.query(command_text)
        print(f"LLM response: {response}")

        matching_items = self.commandList.findItems(response, Qt.MatchExactly)
        if matching_items:
            self.commandList.setCurrentItem(matching_items[0])
        else:
            QMessageBox.warning(self, "Not Found", f"No predicate found matching: {response}")

    def runSelectedPredicate(self):
        selected_items = self.commandList.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "No predicate selected.")
            return

        predicate_name = selected_items[0].text()
        try:
            # Get the expected argument names and the predicate object
            arg_names, predicate = self.all_predicates.getAllPredicates()[predicate_name]
        except KeyError:
            print(f"Predicate '{predicate_name}' not found.")
            return


        arg_values = self.manageArgs.getArgValues()


        # Set arguments and run the predicate
        predicate.setArgs(arg_values)

        # Execute the predicate
        try:
            result = predicate.run()
            # print(f"Result of '{predicate_name}': {result}")
        except Exception as e:
            print(f"Error running predicate '{predicate_name}': {e}")
            raise

        # Fetch all output argument names and their corresponding values
        outputs = list(predicate.iterateOutputs())

        if outputs:
            self.resultsManager.addNewTab(predicate.getShortName(), 
                                        predicate.getCompleteNameWithArgs())
            model = self.resultsManager.setOutputsForTab(predicate.getShortName(), outputs)

            self.sentralControl.addEntryForResults(predicate.getCompleteNameWithArgs())
            self.sentralControl.addDataForResultsEntity(predicate.getCompleteNameWithArgs(), 
                                                        predicate.getDataFrame())

            inst_list = None

            for name, values in outputs:
                if name == "inst":
                    inst_list = values
                    print(f"inst list len : {len(inst_list)}")

                    self.drawManager.draw_instances(inst_list, QColor("white"))



    def updateParamLabels(self):
        selected_items = self.commandList.selectedItems()
        if not selected_items:
            return

        selected_name = selected_items[0].text()

        try:
            arg_names = self.all_predicates.getPredicateArgs(selected_name)
        except ValueError:
            arg_names = []

        # Update labels and visibility
        
        # Convert to dict with empty string values
        args_dict = {name: "" for name in arg_names}
        
        self.manageArgs.setArgValues(args_dict)


    def registerPredicates(self):
        
        p = CreateBarChart(self.sentralControl)
        self.all_predicates.addPredicate("create bar chart", ["x_axis", "y_axis"], p)
        


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem

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

    def addItem(self, header, name):
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
    def __init__(self, viewerTabs: ManageViewerTabs, sourceDropDown: SourceDropDown):
        self.viewerTabs = viewerTabs
        self.sourceDropDown = sourceDropDown
        self.fileNameToData: Dict[str, Any] = {}

    def _detectFileTypeHeader(self, fileName: str) -> str:
        lower = fileName.lower()
        if lower.endswith('.csv'):
            return "CSV files"
        elif lower.endswith('.stl'):
            return "STL files"
        elif lower.endswith('.lef'):
            return "LEF files"
        elif lower.endswith('.def'):
            return "DEF files"
        else:
            return "UNKNOWN files"


    def addEntryForFile(self, fileName: str) -> None:
        fileName = os.path.basename(fileName)
        header = self._detectFileTypeHeader(fileName)

        self._setEntity(header, fileName)

    def addEntryForResults(self, resultsTabName: str) -> None:
        header = "RESULTS"

        self._setEntity(header, resultsTabName)

    def _setEntity(self, header: str, name: str) -> None:
        if not header:
            raise ValueError("Header cannot be empty")

        if header:
            self.sourceDropDown.addHeader(header)
            self.sourceDropDown.addItem(header, name)

            if header != 'RESULTS':
                self.sourceDropDown.addItem(header, f'all {header.lower()}')

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
        label_width = 80

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

    def setArgValues(self, args: dict):
        """
        Show arg-name + value as label-edit pairs.
        """
        for i, (key, value) in enumerate(args.items()):
            if i >= self.max_args:
                break  # ignore excess
            label, edit = self.paramEdits[i]
            label.setText(key)
            label.setToolTip(key)
            edit.setText(str(value))

            label.show()
            edit.show()

        # Hide any remaining unused rows
        for j in range(i + 1, self.max_args):
            label, edit = self.paramEdits[j]
            label.hide()
            edit.hide()

    def getArgValues(self) -> dict:
        """
        Return dict of {arg_name: value} from visible rows.
        """
        result = {}
        for label, edit in self.paramEdits:
            if label.isVisible() and edit.isVisible():
                key = label.text()
                value = edit.text().strip()
                result[key] = value
        return result
