from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget, QTabWidget, QGraphicsView, QListWidgetItem,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit,
    QAction, QFileDialog, QMessageBox, QFrame, QTableView
)

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject, pyqtSlot, QAbstractTableModel


from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

from PyQt5.QtCore import Qt
import sys

import json

import os
import psutil
import threading

from main_menu import MainMenuAndTBar
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from bottom_area import BottomArea

from session import Session


from predicates import Predicates, DummyPredicate

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

        
        
        self.registerPredicates()

        self.create_top_layout()
        

        self.bottomArea = BottomArea(self.mainLayout, 
                                self.WINDOW_HEIGHT, self.LAYOUT_HEIGHT)
        
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
        self.commandList.setMaximumWidth(300)
        self.commandList.itemSelectionChanged.connect(self.updateParamLabels)

        for predicate in self.all_predicates.getAllPredicates().keys():
            item = QListWidgetItem(predicate)
            item.setToolTip(f"<b>{predicate}</b>")
            self.commandList.addItem(item)

    

    def create_command_area(self):
        self.commandArea = QWidget()
        self.commandArea.setMinimumWidth(self.COMMAND_WIDTH)

        outerLayout = QHBoxLayout()

        # ----------------- LEFT HALF -----------------
        leftWidget = QWidget()
        leftLayout = QVBoxLayout()

        # Label: Search
        leftLayout.addWidget(QLabel("Search analysis to perform"))

        # TextEdit + OK Button
        row2 = QHBoxLayout()
        self.commandInput = QTextEdit()
        self.commandInput.setFixedHeight(30)
        self.okButton = QPushButton("Search")
        self.okButton.clicked.connect(self.runSearchAnalysis)
        row2.addWidget(self.commandInput)
        row2.addWidget(self.okButton)
        leftLayout.addLayout(row2)

        # Horizontal separator
        leftLayout.addWidget(self._hline())

        # Label: List of analyses
        leftLayout.addWidget(QLabel("List of analyses"))

        # Command list
        self.commandList = QListWidget()
        self.commandList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.commandList.setMinimumWidth(300)
        leftLayout.addWidget(self.commandList)

        # Horizontal separator
        leftLayout.addWidget(self._hline())

        # Param area
        self.paramLayout = QVBoxLayout()
        self.paramEdits = []

        for _ in range(5):
            hbox = QHBoxLayout()
            label = QLabel("Param")
            label.setMinimumWidth(80)
            edit = QLineEdit()
            hbox.addWidget(label)
            hbox.addWidget(edit)
            self.paramLayout.addLayout(hbox)
            self.paramEdits.append((label, edit))

        paramWidget = QWidget()
        paramWidget.setLayout(self.paramLayout)
        leftLayout.addWidget(paramWidget)

        # Horizontal separator
        leftLayout.addWidget(self._hline())

        # Run + Stop buttons
        buttonRow = QHBoxLayout()
        self.runButton = QPushButton("Run Analysis")
        self.runButton.clicked.connect(self.runSelectedPredicate)
        self.stopButton = QPushButton("Stop Analysis")
        # self.stopButton.clicked.connect(self.stopSelectedPredicate)  # Optional
        buttonRow.addWidget(self.runButton)
        buttonRow.addWidget(self.stopButton)
        leftLayout.addLayout(buttonRow)

        leftWidget.setLayout(leftLayout)

        # ----------------- RIGHT HALF -----------------
        rightWidget = QWidget()
        rightLayout = QVBoxLayout()

        rightLayout.addWidget(QLabel("Results"))

        # Create instance of ManageResultsTabs
        self.resultsManager = ManageResultsTabs()

        # Add the tab widget to right layout
        rightLayout.addWidget(self.resultsManager.getTabWidget())

        rightWidget.setLayout(rightLayout)

        # ----------------- Combine with Separator -----------------
        outerLayout.addWidget(leftWidget, 4)

        # Vertical separator
        vline = QFrame()
        vline.setFrameShape(QFrame.VLine)
        vline.setFrameShadow(QFrame.Sunken)
        outerLayout.addWidget(vline)

        outerLayout.addWidget(rightWidget, 6)

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

         # Build a dict of argument values from the paramEdits
        arg_values = {}
        for label, edit in self.paramEdits:
            if label.isVisible():
                arg_name = label.text()
                arg_values[arg_name] = edit.text()

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

        self.resultsManager.addNewTab(predicate.getShortName(), 
                                    predicate.getCompleteNameWithArgs())
        model = self.resultsManager.setOutputsForTab(predicate.getShortName(), outputs)


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
        for i, (label, edit) in enumerate(self.paramEdits):
            if i < len(arg_names):
                label.setText(arg_names[i])
                label.show()
                edit.show()
            else:
                label.hide()
                edit.hide()


    def registerPredicates(self):
        
        p = DummyPredicate()
        self.all_predicates.addPredicate("generic analysis - for demo purpose", ["arg1", "arg2"], p)
        

    def removeGenericPredicate(self):
        try:
            self.all_predicates.removePredicate("generic analysis - for demo purpose")
        except ValueError as e:
            print(f"Error removing predicate: {e}") 





