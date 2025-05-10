from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget, QTabWidget,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit,
    QAction, QFileDialog, QMessageBox, QHeaderView
)

from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot

from PyQt5.QtCore import Qt
import sys

import json

import os
import psutil
import threading

import logging
from datetime import datetime


class BottomArea():
        
    def __init__(self, _mainLayout, _windowHeight, _layoutHeight):

        self.mainLayout = _mainLayout
        self.windowHeight = _windowHeight
        self.layoutHeight = _layoutHeight

        self.create_bottom_area()

    def create_bottom_area(self):
        self.bottomArea = QWidget()
        self.bottomArea.setMinimumHeight(self.windowHeight - self.layoutHeight)
        self.bottomArea.setStyleSheet("background-color: #fce4ec; border: 1px solid black;")
        
        layout = QVBoxLayout(self.bottomArea)
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
        
        # Make logs selected default.
        self.tabWidget.setCurrentIndex(index)

        layout.addWidget(self.tabWidget)
        self.mainLayout.addWidget(self.bottomArea)

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
        mem_used = process.memory_info().rss / (1024 * 1024)  # in MB
        mem_available = psutil.virtual_memory().available / (1024 * 1024)  # in MB
        num_cpus = os.cpu_count()
        num_threads = threading.active_count()

        self.appendDesignInfo(f"Memory Used: {mem_used:.2f} MB")
        self.appendDesignInfo(f"Memory Available: {mem_available:.2f} MB")
        self.appendDesignInfo(f"CPUs Available: {num_cpus}")
        self.appendDesignInfo(f"Threads Running: {num_threads}")

