from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget, QTabWidget, QGraphicsView,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit,
    QAction, QFileDialog, QMessageBox
)

from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot

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


from layout_draw import LayoutView, LayoutAreaWithScales


from draw_manager import DrawManager

from predicates import Predicates, DummyPredicate

from llm_manager import LLMManager, global_LLM_manager

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
                
                list_widget = tab.get_file_list_widget()

                list = self.session.getAttr(tab_name)
                for f in list:
                    list_widget.addItemIfNotExists(f)



class WriteSessionMenuItem(MenuItemAbstract):
    def __init__(self, session, all_input_tabs):
        self.session = session
        self.all_input_tabs = all_input_tabs

    def onClick(self):

        for tab_name, tab in self.all_input_tabs.items():
            list_widget = tab.get_file_list_widget()

            items = [list_widget.item(i).text() for i in range(list_widget.count())]
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

class DummyToolBarItem(ToolBarItemAbstract):
    def __init__(self):
        super().__init__("Dummy")

    def onClick(self):
        logging.info("Dummy ToolBar item non-functional - implement in your application.")


class MainUI(QMainWindow):
    # Coordinate/size constants
    WINDOW_WIDTH = 1800
    WINDOW_HEIGHT = 900

    LAYOUT_WIDTH = 800
    LAYOUT_HEIGHT = 800

    COMMAND_WIDTH = 900

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataAnalyzer")
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

        self.drawManager = DrawManager(self.drawArea.view, 
                            self.drawArea.bottomScale, self.drawArea.rightScale)
        
        

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

        self.zoomOutMenuObj = ZoomOutMenuItem(self.drawManager)
        self.menu.createMenuItem("View", "Zoom Out", self.zoomOutMenuObj)

        self.zoomInMenuObj = ZoomInMenuItem(self.drawManager)
        self.menu.createMenuItem("View", "Zoom In", self.zoomInMenuObj)

        self.zoomFitMenuObj = ZoomFitMenuItem(self.drawManager)
        self.menu.createMenuItem("View", "Zoom Fit", self.zoomFitMenuObj)

        
        toolBarItem = DummyToolBarItem()
        self.menu.createToolbarItem(toolBarItem)

        self.push_predicates_to_command_area()

        

        

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

        self.drawArea = LayoutAreaWithScales(width=self.LAYOUT_WIDTH, height=self.LAYOUT_HEIGHT)
        self.layoutView = self.drawArea.view

        self.create_command_area()

        topLayout.addWidget(self.drawArea)
        topLayout.addWidget(self.commandArea)

        self.mainLayout.addLayout(topLayout, stretch=2)

    def push_predicates_to_command_area(self):
        self.commandList.addItems(list(self.all_predicates.getAllPredicates().keys()))
        self.commandList.setMaximumWidth(300)
        self.commandList.itemSelectionChanged.connect(self.updateParamLabels)

    
    def create_command_area(self):
        self.commandArea = QWidget()
        self.commandArea.setMinimumWidth(self.COMMAND_WIDTH)
        
        # self.commandArea.setStyleSheet("background-color: #f1f8e9; border: 1px solid black;")

        layout = QVBoxLayout()

        # Row 1: Label
        layout.addWidget(QLabel("Search analysis to perform"))

        # Row 2: TextEdit + OK Button
        row2 = QHBoxLayout()
        self.commandInput = QTextEdit()
        self.commandInput.setFixedHeight(30)
        self.okButton = QPushButton("Search")
        self.okButton.clicked.connect(self.runSearchAnalysis)
        row2.addWidget(self.commandInput)
        row2.addWidget(self.okButton)
        layout.addLayout(row2)

        # Row 3: List + Column of Label+TextEdit
        row3 = QHBoxLayout()

        # Command List
        self.commandList = QListWidget()
        self.commandList.setSelectionMode(QAbstractItemView.SingleSelection)


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
        self.runButton = QPushButton("Run Analysis")
        self.runButton.clicked.connect(self.runSelectedPredicate)
        layout.addWidget(self.runButton)

        # Row 5: Results Label + Table
        layout.addWidget(QLabel("Results"))

        self.commandTable = QTableWidget(0, 2)  # Start with 0 rows
        self.commandTable.setHorizontalHeaderLabels(["Arg Name", "Values"])
        layout.addWidget(self.commandTable)

        self.commandArea.setLayout(layout)


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
        self.all_predicates.addPredicate("dummy predicate - for demo purpose", ["arg1", "arg2"], p)
        






