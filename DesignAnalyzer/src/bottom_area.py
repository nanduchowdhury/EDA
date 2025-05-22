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

        leftPanelWidget = self.create_left_panel()
        rightPanelWidget = self.create_right_panel()


        # Add both panels to bottom area
        splitLayout.addWidget(leftPanelWidget, 1)
        splitLayout.addWidget(rightPanelWidget, 2)

        self.mainLayout.addWidget(self.bottomArea, stretch=1)

        self.appendSystemInfo()

        # Start timer to update system info every 2 seconds
        self.sysInfoTimer = QTimer()
        self.sysInfoTimer.timeout.connect(self.appendSystemInfo)
        self.sysInfoTimer.start(2000)  # 2000 ms = 2 seconds


    def create_left_panel(self):
        
        # Left Panel (1/3 width):
        leftPanelWidget = QWidget()
        leftPanelLayout = QVBoxLayout(leftPanelWidget)
        leftPanelTabs = QTabWidget()
        
        self.lef_tab = InputTab(parent=self, tab_widget_container=leftPanelTabs)
        self.lef_tab.create_tab("LEF")

        self.def_tab = InputTab(parent=self, tab_widget_container=leftPanelTabs)
        self.def_tab.create_tab("DEF")

        leftPanelLayout.addWidget(leftPanelTabs)
        return leftPanelWidget


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



class InputTab:
    def __init__(self, parent, tab_widget_container: QTabWidget):
        self.parent = parent

        self.tab_widget_container = tab_widget_container
        self.tab_widget = QWidget()

        self.list_widget = None

    def get_file_list_widget(self):
        return self.list_widget

    def create_tab(self, tab_name):
        tab_layout = QHBoxLayout(self.tab_widget)

        vertical = QVBoxLayout()
        input_button = QPushButton("Select file")
        clear_button = QPushButton("Clear files")
        vertical.addWidget(input_button)
        vertical.addWidget(clear_button)

        self.list_widget = CustomListWidget()
        h_layout = QHBoxLayout()
        h_layout.addLayout(vertical)
        h_layout.addWidget(self.list_widget)

        input_button.clicked.connect(self.select_callback)
        clear_button.clicked.connect(self.clear_callback)

        tab_layout.addLayout(h_layout)
        self.tab_widget.setLayout(tab_layout)

        self.tab_widget_container.addTab(self.tab_widget, tab_name)


    def select_callback(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a file")

        if file_path:
            self.list_widget.addItemIfNotExists(file_path)

    def clear_callback(self):
        self.list_widget.clear()

