from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QFileDialog
)
from PyQt5.QtCore import Qt
import os
import psutil
import threading

class BottomArea():

    def __init__(self, _mainLayout, _windowHeight, _layoutHeight):
        self.mainLayout = _mainLayout
        self.windowHeight = _windowHeight
        self.layoutHeight = _layoutHeight
        self.create_bottom_area()


    def create_bottom_area(self):

        self.bottomArea = QWidget()

        self.bottomArea.setStyleSheet("border: 1px solid black;")
        
        # self.bottomArea.setMinimumHeight(self.windowHeight - self.layoutHeight)
        # self.bottomArea.setStyleSheet("background-color: #fce4ec; border: 1px solid black;")

        splitLayout = QHBoxLayout(self.bottomArea)

        # Left Panel (1/3 width): LEF/DEF
        lefDefWidget = QWidget()
        lefDefLayout = QVBoxLayout(lefDefWidget)
        lefDefTabs = QTabWidget()

        # LEF/DEF Tab
        lefDefTab = QWidget()
        lefDefTabLayout = QHBoxLayout(lefDefTab)

        # === LEF section ===
        lefVertical = QVBoxLayout()
        self.lefButton = QPushButton("Select LEF")
        self.clearLefButton = QPushButton("Clear LEF")
        lefVertical.addWidget(self.lefButton)
        lefVertical.addWidget(self.clearLefButton)
        self.lefListWidget = QListWidget()
        lefHLayout = QHBoxLayout()
        lefHLayout.addLayout(lefVertical)
        lefHLayout.addWidget(self.lefListWidget)

        # === DEF section ===
        defVertical = QVBoxLayout()
        self.defButton = QPushButton("Select DEF")
        self.clearDefButton = QPushButton("Clear DEF")
        defVertical.addWidget(self.defButton)
        defVertical.addWidget(self.clearDefButton)
        self.defListWidget = QListWidget()
        defHLayout = QHBoxLayout()
        defHLayout.addLayout(defVertical)
        defHLayout.addWidget(self.defListWidget)

        # Add both LEF and DEF to main horizontal layout
        lefDefTabLayout.addLayout(lefHLayout)
        lefDefTabLayout.addLayout(defHLayout)
        lefDefTab.setLayout(lefDefTabLayout)

        lefDefTabs.addTab(lefDefTab, "LEF/DEF")
        lefDefLayout.addWidget(lefDefTabs)

        # Right Panel (2/3 width): Existing TabWidget
        rightPanelWidget = QWidget()
        rightPanelLayout = QVBoxLayout(rightPanelWidget)
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
        index = self.tabWidget.addTab(self.logsTab, "Logs")
        self.tabWidget.setCurrentIndex(index)

        rightPanelLayout.addWidget(self.tabWidget)

        # Add both panels to bottom area
        splitLayout.addWidget(lefDefWidget, 1)
        splitLayout.addWidget(rightPanelWidget, 2)

        self.mainLayout.addWidget(self.bottomArea, stretch=1)

        # Connect button actions
        self.lefButton.clicked.connect(self.selectLefFiles)
        self.clearLefButton.clicked.connect(self.clearLefFiles)
        self.defButton.clicked.connect(self.selectDefFiles)
        self.clearDefButton.clicked.connect(self.clearDefFiles)

        self.appendSystemInfo()

    def appendDesignInfo(self, info):
        self.designInfoText.append(info)

    def appendLog(self, date, log):
        row = self.logTable.rowCount()
        self.logTable.insertRow(row)
        self.logTable.setItem(row, 0, QTableWidgetItem(date))
        self.logTable.setItem(row, 1, QTableWidgetItem(log))
        self.logTable.resizeColumnsToContents()

    def appendSystemInfo(self):
        process = psutil.Process(os.getpid())
        mem_used = process.memory_info().rss / (1024 * 1024)
        mem_available = psutil.virtual_memory().available / (1024 * 1024)
        num_cpus = os.cpu_count()
        num_threads = threading.active_count()

        self.appendDesignInfo(f"Memory Used: {mem_used:.2f} MB")
        self.appendDesignInfo(f"Memory Available: {mem_available:.2f} MB")
        self.appendDesignInfo(f"CPUs Available: {num_cpus}")
        self.appendDesignInfo(f"Threads Running: {num_threads}")

    def selectLefFiles(self):
        files, _ = QFileDialog.getOpenFileNames(None, "Select LEF Files", "", "LEF Files (*.lef *.LEF);;All Files (*)")
        if files:
            self.lefListWidget.addItems(files)

    def clearLefFiles(self):
        self.lefListWidget.clear()

    def selectDefFiles(self):
        files, _ = QFileDialog.getOpenFileNames(None, "Select DEF Files", "", "DEF Files (*.def *.DEF);;All Files (*)")
        if files:
            self.defListWidget.addItems(files)

    def clearDefFiles(self):
        self.defListWidget.clear()
