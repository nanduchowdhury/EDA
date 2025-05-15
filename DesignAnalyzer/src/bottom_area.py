from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QLabel
)
from PyQt5.QtCore import Qt, QTimer
import os
import psutil
import threading

import time

import json

from common import CustomListWidget

from design_data import DesignData

class BottomArea():

    def __init__(self, _mainLayout, _windowHeight, _layoutHeight):
        self.mainLayout = _mainLayout
        self.windowHeight = _windowHeight
        self.layoutHeight = _layoutHeight

        self.process_start_time = psutil.Process(os.getpid()).create_time()

        self.create_bottom_area()


    def create_bottom_area(self):

        self.bottomArea = QWidget()

        self.bottomArea.setStyleSheet("border: 1px solid black;")
        
        # self.bottomArea.setMinimumHeight(self.windowHeight - self.layoutHeight)
        # self.bottomArea.setStyleSheet("background-color: #fce4ec; border: 1px solid black;")

        splitLayout = QHBoxLayout(self.bottomArea)

        lefDefWidget = self.create_left_panel()
        rightPanelWidget = self.create_right_panel()


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

        # Start timer to update system info every 2 seconds
        self.sysInfoTimer = QTimer()
        self.sysInfoTimer.timeout.connect(self.appendSystemInfo)
        self.sysInfoTimer.start(2000)  # 2000 ms = 2 seconds


    def create_left_panel(self):
        
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
        self.lefListWidget = CustomListWidget()
        lefHLayout = QHBoxLayout()
        lefHLayout.addLayout(lefVertical)
        lefHLayout.addWidget(self.lefListWidget)

        # === DEF section ===
        defVertical = QVBoxLayout()
        self.defButton = QPushButton("Select DEF")
        self.clearDefButton = QPushButton("Clear DEF")
        defVertical.addWidget(self.defButton)
        defVertical.addWidget(self.clearDefButton)
        self.defListWidget = CustomListWidget()
        defHLayout = QHBoxLayout()
        defHLayout.addLayout(defVertical)
        defHLayout.addWidget(self.defListWidget)

        # Add both LEF and DEF to main horizontal layout
        lefDefTabLayout.addLayout(lefHLayout)
        lefDefTabLayout.addLayout(defHLayout)
        lefDefTab.setLayout(lefDefTabLayout)

        lefDefTabs.addTab(lefDefTab, "LEF/DEF")
        lefDefLayout.addWidget(lefDefTabs)

        return lefDefWidget


    def create_right_panel(self):
        # Right 2/3 Panel: split horizontally into tabWidget and system info
        rightPanelWidget = QWidget()
        rightPanelLayout = QHBoxLayout(rightPanelWidget)

        # --- Left side: QTabWidget (Design Info, Logs) ---
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

        # --- Right side: system info label ---
        self.sysInfoLabel = QLabel()
        self.sysInfoLabel.setStyleSheet("font-size: 16px; color: gray;")
        self.sysInfoLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.sysInfoLabel.setMinimumWidth(200)

        # Add both to horizontal layout
        rightPanelLayout.addWidget(self.tabWidget, stretch=3)
        rightPanelLayout.addWidget(self.sysInfoLabel, stretch=1)

        return rightPanelWidget


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

        # Memory
        mem_used = process.memory_info().rss / (1024 * 1024)
        mem_available = psutil.virtual_memory().available / (1024 * 1024)

        # CPU
        cpu_percent = process.cpu_percent(interval=0.1)  # small delay to sample
        num_cpus = os.cpu_count()

        # Threads
        num_threads = process.num_threads()

        # Uptime
        uptime_secs = time.time() - self.process_start_time
        hours, remainder = divmod(int(uptime_secs), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # PID
        pid = process.pid

        # (Optional) Peak memory on Unix-like systems
        try:
            peak_mem = process.memory_info().peak_wset / (1024 * 1024)  # Windows only
        except AttributeError:
            peak_mem = "N/A"

        # Format the output
        sys_info = (
            f"PID: {pid}\n"
            f"Uptime: {uptime_str}\n"
            f"Memory Used: {mem_used:.2f} MB\n"
            f"Memory Available: {mem_available:.2f} MB\n"
            f"CPU Usage: {cpu_percent:.1f}%\n"
            f"CPUs Available: {num_cpus}\n"
            f"Threads Running: {num_threads}\n"
            f"Peak Memory: {peak_mem if isinstance(peak_mem, str) else f'{peak_mem:.2f} MB'}"
        )

        self.sysInfoLabel.setText(sys_info)

    def selectLefFiles(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a LEF file")

        if file_path:
            self.lefListWidget.addItemIfNotExists(file_path)

    def clearLefFiles(self):
        self.lefListWidget.clear()

    def selectDefFiles(self):

        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a DEF file")

        if file_path:
            self.defListWidget.addItemIfNotExists(file_path)


    def clearDefFiles(self):
        self.defListWidget.clear()
