from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget, QTabWidget,
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

from main_menu import MainMenu
from main_menu import MenuItemAbstract

from def_parser import DefParser

from predicates import Predicates, GetViasPredicate

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

class ParseWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    @pyqtSlot()
    def run(self):
        parser = DefParser()

        with open(self.file_path, 'r') as def_file:
            def_file_content = def_file.read()

        def_dict = parser.parse(def_file_content)

        self.finished.emit(def_dict)

class FileOpenMenuItem(MenuItemAbstract):
    def onClick(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a file")

        if file_path:
            self.selectedFile = file_path

            self.worker = ParseWorker(file_path)
            self.thread = QThread()

            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)  # ✅ Correct slot usage

            self.worker.finished.connect(self.on_parse_finished)
            self.worker.finished.connect(self.thread.quit)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

            logging.info("DEF parser started...")

    def on_parse_finished(self, def_dict):

        json_data = json.dumps(def_dict, indent=4)

        # print(json_data)
        logging.info("DEF parser finished.")


class MainUI(QMainWindow):
    # Coordinate/size constants
    WINDOW_WIDTH = 1800
    WINDOW_HEIGHT = 900

    LAYOUT_WIDTH = 700
    LAYOUT_HEIGHT = 700

    COMMAND_WIDTH = 800

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Main UI")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

        self.apply_global_styles()

        self.all_predicates = Predicates()

        self.setup_logging()

        self.registerPredicates()

        self.menu = MainMenu(self)

        self.fileOpenMenuObj = FileOpenMenuItem()
        self.menu.createItem("File", "Open", self.fileOpenMenuObj)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.mainLayout = QVBoxLayout()
        self.centralWidget.setLayout(self.mainLayout)

        self.create_top_layout()
        self.create_control_area()


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
        ui_handler = UILogHandler(self.appendLog)
        ui_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.addHandler(ui_handler)

        self.logger = logger  # Optional: store if you want to call directly

    def create_top_layout(self):
        topLayout = QHBoxLayout()

        self.create_layout_area()
        self.create_command_area()

        topLayout.addWidget(self.layoutArea)
        topLayout.addWidget(self.commandArea)

        self.mainLayout.addLayout(topLayout)

    def create_layout_area(self):
        self.layoutArea = QWidget()
        self.layoutArea.setMinimumSize(self.LAYOUT_WIDTH, self.LAYOUT_HEIGHT)
        self.layoutArea.setStyleSheet("background-color: #e3f2fd; border: 1px solid black;")
        self.layoutArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


    def create_control_area(self):
        self.controlArea = QWidget()
        self.controlArea.setMinimumHeight(self.WINDOW_HEIGHT - self.LAYOUT_HEIGHT)
        self.controlArea.setStyleSheet("background-color: #fce4ec; border: 1px solid black;")
        
        layout = QVBoxLayout(self.controlArea)
        self.tabWidget = QTabWidget()
        
        # Design Info tab
        self.designInfoTab = QWidget()
        self.designInfoText = QTextEdit()
        self.designInfoText.setReadOnly(True)
        designLayout = QVBoxLayout()
        designLayout.addWidget(self.designInfoText)
        self.designInfoTab.setLayout(designLayout)
        self.tabWidget.addTab(self.designInfoTab, "Design Info")
        
        # Logs tab
        self.logsTab = QWidget()
        self.logTable = QTableWidget(0, 2)
        self.logTable.setHorizontalHeaderLabels(["Date", "Log"])
        logLayout = QVBoxLayout()
        logLayout.addWidget(self.logTable)
        self.logsTab.setLayout(logLayout)
        self.tabWidget.addTab(self.logsTab, "Logs")
        
        layout.addWidget(self.tabWidget)
        self.mainLayout.addWidget(self.controlArea)

        self.appendSystemInfo()

    def appendDesignInfo(self, info):
        self.designInfoText.append(info)

    def appendLog(self, date, log):
        row = self.logTable.rowCount()
        self.logTable.insertRow(row)
        self.logTable.setItem(row, 0, QTableWidgetItem(date))
        self.logTable.setItem(row, 1, QTableWidgetItem(log))

    def appendSystemInfo(self):
        process = psutil.Process(os.getpid())
        mem_used = process.memory_info().rss / (1024 * 1024)  # in MB
        mem_available = psutil.virtual_memory().available / (1024 * 1024)  # in MB
        num_cpus = os.cpu_count()
        num_threads = threading.active_count()

        self.appendDesignInfo(f"Memory Used: {mem_used:.2f} MB")
        self.appendDesignInfo(f"Memory Available: {mem_available:.2f} MB")
        self.appendDesignInfo(f"CPUs Available: {num_cpus}")
        self.appendDesignInfo(f"Threads Running: {num_threads}")

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
            print(f"Result of '{predicate_name}': {result}")
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
        
        predObj = GetViasPredicate()
        self.all_predicates.addPredicate("get_vias", ["a", "b"], predObj)

        # Iterate
        for name, (args, obj) in self.all_predicates:
            print(f"{name} with args {args}")

        # Get args for specific predicate
        print("Args for 'multiply':", self.all_predicates.getPredicateArgs("get_vias"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainUI()
    window.show()
    sys.exit(app.exec_())
