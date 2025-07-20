from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QLabel, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal


import os
import psutil
import threading

import time

import json

from common import CustomListWidget, PlaceholderTextEdit, TabWidget, TabWidgetRmbPopOut
from llm_manager import global_LLM_manager


class BottomArea(QObject):

    DUMMY_INPUT_TAB = "input file"


    def __init__(self, _mainLayout, _sentralControl, 
                 _windowWidth, _windowHeight, 
                 _layoutWidth, _layoutHeight):
        
        super().__init__()

        self.mainLayout = _mainLayout
        self.sentralControl = _sentralControl

        self.windowWidth = _windowWidth
        self.windowHeight = _windowHeight
        self.layoutWidth = _layoutWidth
        self.layoutHeight = _layoutHeight

        self.process_start_time = psutil.Process(os.getpid()).create_time()

        self.create_bottom_area()


    def get_tab_by_name(self, tab_name):
        if tab_name in self.all_input_tabs:
            return self.all_input_tabs[tab_name]
        else:
            raise ValueError(f"No tab found by name {tab_name}")

    def create_input_tab(self, tab_name):
        
        if self.DUMMY_INPUT_TAB in self.all_input_tabs:
            dummy_tab_index = self.all_input_tabs[self.DUMMY_INPUT_TAB].tab_index
            self.leftPanelTabs.setTabText(dummy_tab_index, tab_name)
            self.all_input_tabs[tab_name] = self.all_input_tabs[self.DUMMY_INPUT_TAB]
            del self.all_input_tabs[self.DUMMY_INPUT_TAB]
        else:
            tab = InputTab(parent=self, sentralControl=self.sentralControl, tab_widget_container=self.leftPanelTabs)
            tab.create_tab(tab_name)
            self.all_input_tabs[tab_name] = tab

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
        self.leftPanelTabs = QTabWidget()
        
        tab = InputTab(parent=self, sentralControl=self.sentralControl, tab_widget_container=self.leftPanelTabs)
        tab.create_tab(self.DUMMY_INPUT_TAB)
        self.all_input_tabs = {self.DUMMY_INPUT_TAB: tab}

        leftPanelLayout.addWidget(self.leftPanelTabs)
        return leftPanelWidget


    def create_right_panel(self):
        # Right 2/3 Panel: split horizontally into tabWidget and system info
        rightPanelWidget = QWidget()
        rightPanelLayout = QHBoxLayout(rightPanelWidget)

        # --- Left side: QTabWidget (Data Info, Logs, Assistant) ---
        self.tabWidget = TabWidget()
        self.tabWidget.addRmbMenu([TabWidgetRmbPopOut(self.windowWidth, self.windowHeight)])
        self.tabWidget.setTabPosition(QTabWidget.West)

        # Data Info tab
        self.designInfoTab = QWidget()
        self.designInfoText = QTextEdit()
        self.designInfoText.setReadOnly(True)
        designLayout = QVBoxLayout()
        designLayout.addWidget(self.designInfoText)
        self.designInfoTab.setLayout(designLayout)
        self.tabWidget.addTab(self.designInfoTab, "Data Info")

        # Logs tab
        self.logsTab = QWidget()
        self.logTable = QTableWidget(0, 2)
        self.logTable.setHorizontalHeaderLabels(["Date", "Log"])
        logLayout = QVBoxLayout()
        logLayout.addWidget(self.logTable)
        self.logsTab.setLayout(logLayout)
        self.tabWidget.addTab(self.logsTab, "Logs")

        # Assistant tab
        self.assistantManager = AssistantManager()
        self.assistantTab = self.assistantManager.getTab()
        index = self.tabWidget.addTab(self.assistantTab, "Assistant")
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

    def _handleAssistantQuery(self):
        query = self.assistantInput.toPlainText().strip()
        if not query:
            return

        # Append user input
        self.assistantOutput.append(f"<b>You:</b> {query}")

        # Generate assistant reply (mock or real logic)
        command, args = self._generateMockAssistantReply(query)

        # Append assistant response
        resp = f"<b>Assistant:</b> Use following action or analysis:\n \
                \t\t <b>{command}</b> \n\
            \t with arguments: \n\
                \t\t <b>{args}</b>"
        
        self.assistantOutput.append(resp)

        self.assistantOutput.append("")  # spacing

        # Auto-scroll to bottom
        self.assistantOutput.verticalScrollBar().setValue(
            self.assistantOutput.verticalScrollBar().maximum()
        )

        self.assistantInput.clear()



    def _generateMockAssistantReply(self, query: str) -> str:
        
        command, args = global_LLM_manager.query(query)

        self.signal_update_command.emit(command, args)

        return command, args


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
    def __init__(self, parent, sentralControl, 
                 tab_widget_container: QTabWidget):
        
        self.parent = parent
        self.sentralControl = sentralControl

        self.tab_widget_container = tab_widget_container
        self.tab_widget = QWidget()

        self.list_widget = None
        self.tab_index = None

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

        self.tab_index = self.tab_widget_container.addTab(self.tab_widget, tab_name)


    def select_callback(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a file")

        if file_path:
            self._addItem(file_path)

    def _addItem(self, file_path):
        base_name = os.path.basename(file_path)
        existing_items = [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
        if base_name not in existing_items:
            item = QListWidgetItem(base_name)
            item.setToolTip(file_path)
            self.list_widget.addItem(item)

            self.sentralControl.addEntryForFile(base_name)


    def addItems(self, file_paths):
        for file_path in file_paths:
            self._addItem(file_path)

    def getAllItemsInList(self):
        return [
            self.list_widget.item(i).toolTip()
            for i in range(self.list_widget.count())
        ]

    def clear_callback(self):
        self.list_widget.clear()



class AssistantManager(QObject):

    signal_update_command = pyqtSignal(str, dict)

    def __init__(self, parent=None):

        super().__init__()

        self.assistantTab = QWidget(parent)
        assistantLayout = QVBoxLayout(self.assistantTab)

        # Output area
        self.assistantOutput = QTextEdit()
        self.assistantOutput.setReadOnly(True)
        self.assistantOutput.setPlaceholderText("Assistant Output")
        self.assistantOutput.setStyleSheet("background-color: #f9f9f9;")
        self.assistantOutput.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Input + Send Button row
        inputRow = QHBoxLayout()
        self.assistantInput = PlaceholderTextEdit()
        self.assistantInput.setPlaceholderText("Ask about what analysis or action you want to perform on your data...")
        self.assistantInput.setFixedHeight(60)

        self.sendButton = QPushButton("▶")
        self.sendButton.setFixedWidth(80)

        # Trigger query on 'Enter' press or button-press
        self.sendButton.clicked.connect(self._handleAssistantQuery)
        self.assistantInput.on_enter_pressed(self._handleAssistantQuery)

        inputRow.addWidget(self.assistantInput)
        inputRow.addWidget(self.sendButton)

        # Layout assembly
        assistantLayout.addWidget(self.assistantOutput)
        assistantLayout.addLayout(inputRow)

    def getTab(self):
        return self.assistantTab

    def _handleAssistantQuery(self):
        query = self.assistantInput.toPlainText().strip()

        if not query:
            return
        
        self.assistantInput.addHistory(query)

        # Append user input
        self.assistantOutput.append(f"<b>You:</b> {query}")
        self.assistantInput.clear()

        # Get LLM response
        try:
            json_llm_response = global_LLM_manager.query(query)
        except Exception as e:
            self.assistantOutput.append(f"<span style='color:red;'>Error: {str(e)}</span>")
            return

        # Dispatch response based on type
        response_type = json_llm_response.get("ResultMode")
        if response_type == "LLM_OWN_RESPONSE":
            self._handleOwnResponse(json_llm_response.get("output", {}))
        elif response_type == "SQL_COLUMN_ANALYSIS":
            self._handleSQLColumnAnalysis(json_llm_response.get("output", {}))
        elif response_type == "COMMAND_OR_ACTION_RUN":
            self._handleCommandOrActionRun(json_llm_response.get("output", {}))
        else:
            self.assistantOutput.append("<i>Unknown response type received.</i>")


        # Put a newline and auto-scroll to bottom
        self.assistantOutput.append("")
        self.assistantOutput.verticalScrollBar().setValue(
            self.assistantOutput.verticalScrollBar().maximum()
        )

    def _handleOwnResponse(self, output):

        llm_own_resp = output.get("llm_own_answer", "")
        self.assistantOutput.append(f"<b>Assistant:</b> {llm_own_resp}")

    def _handleSQLColumnAnalysis(self, result):

        sql_query = result.get("sql_query", "")

        command = "execute sql query"
        args = {"actual_query": sql_query}

        self.signal_update_command.emit(command, args)

        resp = f"Check the relevant data in results table."
        self.assistantOutput.append(f"<b>Assistant:</b> {resp}")
        

    def _handleCommandOrActionRun(self, output):

        command = output.get("command_name")
        args = output.get("args", [])

        self.signal_update_command.emit(command, args)

        resp = f"<b>Assistant:</b> Use following action or analysis:\n \
                \t\t <b>{command}</b> \n\
            \t with arguments: \n\
                \t\t <b>{args}</b>"
        
        self.assistantOutput.append(resp)
        


