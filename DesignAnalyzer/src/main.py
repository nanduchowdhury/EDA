from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget, QTabWidget, QGraphicsView,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit,
    QAction, QFileDialog, QMessageBox
)

from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot

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

from def_parser import DefParserImplement
from lef_parser import LefParserImplement

from layout_draw import LayoutView, LayoutAreaWithScales

from draw_manager import DrawManager

from predicates import Predicates, MultiplyTwoNumbers, GetViasForLayer, GetInstanceCoords

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
    def __init__(self, session, lefListWidget, defListWidget):
        self.session = session
        self.lefListWidget = lefListWidget
        self.defListWidget = defListWidget


    def onClick(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a session JSON file")

        if file_path:
            self.session.readSession(file_path)

            def_list = self.session.getAttr("DEF")
            for f in def_list:
                self.defListWidget.addItemIfNotExists(f)

            lef_list = self.session.getAttr("LEF")
            for f in lef_list:
                self.lefListWidget.addItemIfNotExists(f)

class WriteSessionMenuItem(MenuItemAbstract):
    def __init__(self, session, lefListWidget, defListWidget):
        self.session = session
        self.lefListWidget = lefListWidget
        self.defListWidget = defListWidget

    def onClick(self):

        items = [self.lefListWidget.item(i).text() for i in range(self.lefListWidget.count())]
        self.session.setAttr("LEF", items)
            
        items = [self.defListWidget.item(i).text() for i in range(self.defListWidget.count())]
        self.session.setAttr("DEF", items)

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
    def __init__(self, _drawManager):
        self.drawManager = _drawManager

    def onClick(self):
        self.drawManager.zoom_out()

class ZoomInMenuItem(MenuItemAbstract):
    def __init__(self, _drawManager):
        self.drawManager = _drawManager

    def onClick(self):
        self.drawManager.zoom_in()

class ZoomFitMenuItem(MenuItemAbstract):
    def __init__(self, _drawManager):
        self.drawManager = _drawManager

    def onClick(self):
        self.drawManager.fit_to_view()

class LoadDesignToolItem(ToolBarItemAbstract):
    def __init__(self, lefListWidget, defListWidget,
                    defParserImplement, lefParserImplement):
        super().__init__("Load Design")

        self.lefListWidget = lefListWidget
        self.defListWidget = defListWidget
        self.lefParserImplement = lefParserImplement
        self.defParserImplement = defParserImplement

    def onClick(self):
        self.loadLefDef()
        
        
    def loadLefDef(self):

        lef_list = [self.lefListWidget.item(i).text() for i in range(self.lefListWidget.count())]
        def_list = [self.defListWidget.item(i).text() for i in range(self.defListWidget.count())]

        for l in lef_list:
            self.lefParserImplement.parse(l)

        for d in def_list:
            self.defParserImplement.parse(d)
        

class MainUI(QMainWindow):
    # Coordinate/size constants
    WINDOW_WIDTH = 1800
    WINDOW_HEIGHT = 900

    LAYOUT_WIDTH = 800
    LAYOUT_HEIGHT = 800

    COMMAND_WIDTH = 900

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main UI")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self.apply_global_styles()

        self.session = Session()

        self.all_predicates = Predicates()

        self.menu = MainMenuAndTBar(self)

        self.defParserImplement = DefParserImplement()
        self.lefParserImplement = LefParserImplement()

        self.registerPredicates()

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.mainLayout = QVBoxLayout()
        self.centralWidget.setLayout(self.mainLayout)

        self.create_top_layout()

        self.bottomArea = BottomArea(self.mainLayout, 
                                self.WINDOW_HEIGHT, self.LAYOUT_HEIGHT)

        self.readSessionMenuObj = ReadSessionMenuItem(self.session, 
                                        self.bottomArea.lefListWidget, self.bottomArea.defListWidget)
        self.menu.createMenuItem("File", "Read Session", self.readSessionMenuObj)

        self.writeSessionMenuObj = WriteSessionMenuItem(self.session, 
                                        self.bottomArea.lefListWidget, self.bottomArea.defListWidget)
        self.menu.createMenuItem("File", "Write Session", self.writeSessionMenuObj)

        self.zoomOutMenuObj = ZoomOutMenuItem(self.drawManager)
        self.menu.createMenuItem("View", "Zoom Out", self.zoomOutMenuObj)

        self.zoomInMenuObj = ZoomInMenuItem(self.drawManager)
        self.menu.createMenuItem("View", "Zoom In", self.zoomInMenuObj)

        self.zoomFitMenuObj = ZoomFitMenuItem(self.drawManager)
        self.menu.createMenuItem("View", "Zoom Fit", self.zoomFitMenuObj)

        self.loadDesignToolbarItem = LoadDesignToolItem(self.bottomArea.lefListWidget, 
                                self.bottomArea.defListWidget,
                                self.defParserImplement, self.lefParserImplement)
        self.menu.createToolbarItem(self.loadDesignToolbarItem)
        

        self.setup_logging()

    def apply_global_styles(self):
        with open("main.qss", "r") as f:
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

        self.drawArea = LayoutAreaWithScales(width=self.LAYOUT_WIDTH, height=self.LAYOUT_HEIGHT)
        self.layoutView = self.drawArea.view
        self.drawManager = self.drawArea.drawManager

        self.create_command_area()

        topLayout.addWidget(self.drawArea)
        topLayout.addWidget(self.commandArea)

        self.mainLayout.addLayout(topLayout, stretch=2)


    
    def create_command_area(self):
        self.commandArea = QWidget()
        self.commandArea.setMinimumWidth(self.COMMAND_WIDTH)
        
        # self.commandArea.setStyleSheet("background-color: #f1f8e9; border: 1px solid black;")

        layout = QVBoxLayout()

        # Row 1: Label
        layout.addWidget(QLabel("Search action to perform"))

        # Row 2: TextEdit + OK Button
        row2 = QHBoxLayout()
        self.commandInput = QTextEdit()
        self.commandInput.setFixedHeight(30)
        okButton = QPushButton("OK")
        row2.addWidget(self.commandInput)
        row2.addWidget(okButton)
        layout.addLayout(row2)

        # Row 3: List + Column of Label+TextEdit
        row3 = QHBoxLayout()

        # Command List
        self.commandList = QListWidget()
        self.commandList.setSelectionMode(QAbstractItemView.SingleSelection)

        # Add only predicate names
        self.commandList.addItems(list(self.all_predicates.getAllPredicates().keys()))
        self.commandList.setMaximumWidth(300)
        self.commandList.itemSelectionChanged.connect(self.updateParamLabels)

        row3.addWidget(self.commandList)

        # Parameter Area
        paramWidget = QWidget()
        self.paramLayout = QVBoxLayout()
        self.paramEdits = []  # List of (label, lineEdit) tuples

        # Create enough editable rows (you can change the count as needed)
        for _ in range(5):
            hbox = QHBoxLayout()
            label = QLabel("Param")
            label.setMinimumWidth(80)
            edit = QLineEdit()
            hbox.addWidget(label)
            hbox.addWidget(edit)
            self.paramLayout.addLayout(hbox)
            self.paramEdits.append((label, edit))

        paramWidget.setLayout(self.paramLayout)
        row3.addWidget(paramWidget)

        layout.addLayout(row3)


        # Row 4: Execute Button
        self.runButton = QPushButton("Run Predicate")
        self.runButton.clicked.connect(self.runSelectedPredicate)
        layout.addWidget(self.runButton)

        # Row 5: Results Label + Table
        layout.addWidget(QLabel("Results"))

        self.commandTable = QTableWidget(0, 2)  # Start with 0 rows
        self.commandTable.setHorizontalHeaderLabels(["Arg Name", "Values"])
        layout.addWidget(self.commandTable)

        self.commandArea.setLayout(layout)


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

        # Set the number of columns based on output args
        num_columns = len(outputs)
        self.commandTable.setColumnCount(num_columns)

        # Set column headers as the output arg names
        column_headers = [arg_name for arg_name, _ in outputs]
        self.commandTable.setHorizontalHeaderLabels(column_headers)

        # Determine the maximum number of values in any column to set row count
        max_rows = max((len(values) for _, values in outputs), default=0)
        self.commandTable.setRowCount(max_rows)

        # Populate the table: each column corresponds to one output arg
        for col, (arg_name, values) in enumerate(outputs):
            for row, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                self.commandTable.setItem(row, col, item)

        # Build instance dict for drawManager
        instance_dict = {}
        inst_list = None
        bbox_list = None

        for name, values in outputs:
            if name == "inst":
                inst_list = values
                print(f"inst list len : {len(inst_list)}")
            elif name == "coords":
                bbox_list = values
                print(f"bbox list len : {len(bbox_list)}")

        # Check if both were found
        if inst_list and bbox_list and len(inst_list) == len(bbox_list):
            instance_dict = {
                inst: {"coords": bbox}
                for inst, bbox in zip(inst_list, bbox_list)
            }

            print(f"instance_dict len : {len(instance_dict)}")

            # Set the instance dict and draw them in layout
            if hasattr(self, "drawManager") and self.drawManager:
                
                print("Drawing cells now...")
                
                self.drawManager.setInstances(instance_dict)
                self.drawManager.drawInstances()


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
        
        multObj = MultiplyTwoNumbers(self.defParserImplement, self.lefParserImplement)
        self.all_predicates.addPredicate("multiply_2_numbers", ["a", "b"], multObj)

        viaObj = GetViasForLayer(self.defParserImplement, self.lefParserImplement)
        self.all_predicates.addPredicate("get_vias_for_layer", ["layer"], viaObj)

        instObj = GetInstanceCoords(self.defParserImplement, self.lefParserImplement)
        self.all_predicates.addPredicate("get_inst_and_coords", [], instObj)

        # Iterate
        for name, (args, obj) in self.all_predicates:
            print(f"{name} with args {args}")

        # Get args for specific predicate
        print("Args for 'multiply':", self.all_predicates.getPredicateArgs("multiply_2_numbers"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainUI()
    window.show()
    sys.exit(app.exec_())
