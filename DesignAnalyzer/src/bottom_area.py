from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QLabel, QListWidgetItem, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, pyqtSlot


import os
import psutil
import threading

import time

import json

from common import CustomListWidget, PlaceholderTextEdit, TabWidget, TabWidgetRmbPopOut
from common import global_signals, TimeKeeper

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


    def create_input_tab(self, tab_name):
        self.inputTab.createFilesSurceTab("Files", tab_name)

    def create_bottom_area(self):

        self.bottomArea = QWidget()

        # self.bottomArea.setStyleSheet("border: 1px solid black;")
        
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
        
        self.inputTab = InputTab(sentralControl=self.sentralControl)

        leftPanelLayout.addWidget(self.inputTab)
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
        self.assistantManager = AssistantManager(self.sentralControl)
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




class InputTab(QTabWidget):
    def __init__(self, sentralControl, parent=None):
        super().__init__(parent)

        self.parent = parent
        self.sentralControl = sentralControl
        self.group_tabs = {}  # group_name -> QTabWidget
        self.list_widgets = {}  # (group_name, source_name) -> QListWidget

        # Add default groups and sources
        self.createSourceGroupTab("Files")

        self.createSourceGroupTab("Cloud")
        self.createGoogleCloudSourceTab("Cloud", "Google Cloud Storage")
        self.createSnowflakeSourceTab("Cloud", "Snowflake")

    def createSourceGroupTab(self, group_name):
        """Create a new group tab that holds source tabs, with a label above."""
        group_widget = QWidget()
        group_layout = QVBoxLayout(group_widget)

        label = QLabel(f"Select {group_name} sources")
        label.setAlignment(Qt.AlignLeft)
        group_layout.addWidget(label)

        group_tab = QTabWidget()
        group_layout.addWidget(group_tab)

        self.addTab(group_widget, group_name)
        self.group_tabs[group_name] = group_tab

    def createFilesSurceTab(self, group_name, source_name):
        """Create a new source tab under an existing group."""
        if group_name not in self.group_tabs:
            raise ValueError(f"Group '{group_name}' not found. Call createSourceGroupTab() first.")

        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)

        # Buttons and list
        button_layout = QVBoxLayout()
        input_button = QPushButton("Select file")
        clear_button = QPushButton("Clear files")
        button_layout.addWidget(input_button)
        button_layout.addWidget(clear_button)

        list_widget = CustomListWidget()
        self.list_widgets[(group_name, source_name)] = list_widget

        input_button.clicked.connect(lambda: self.select_callback(group_name, source_name))
        clear_button.clicked.connect(lambda: self.clear_callback(group_name, source_name))

        # Assemble the tab layout
        content_layout = QHBoxLayout()
        content_layout.addLayout(button_layout)
        content_layout.addWidget(list_widget)
        tab_layout.addLayout(content_layout)

        # Add the source tab
        self.group_tabs[group_name].addTab(tab_widget, source_name)


    def createSnowflakeSourceTab(self, group_name, source_name):
        if group_name not in self.group_tabs:
            raise ValueError(f"Group '{group_name}' not found. Call createSourceGroupTab() first.")

        tab_widget = QWidget()
        grid_layout = QGridLayout(tab_widget)

        # Row 0: Username & Password
        label_user = QLabel("Username")
        self.snowflakeUsername = QTextEdit()
        self.snowflakeUsername.setFixedHeight(30)
        label_pass = QLabel("Password")
        self.snowflakePassword = QTextEdit()
        self.snowflakePassword.setFixedHeight(30)
        grid_layout.addWidget(label_user, 0, 0)
        grid_layout.addWidget(self.snowflakeUsername, 0, 1)
        grid_layout.addWidget(label_pass, 0, 2)
        grid_layout.addWidget(self.snowflakePassword, 0, 3)

        # Row 1: Account & Warehouse
        label_account = QLabel("Account")
        self.snowflakeAccount = QTextEdit()
        self.snowflakeAccount.setFixedHeight(30)
        label_warehouse = QLabel("Warehouse")
        self.snowflakeWarehouse = QTextEdit()
        self.snowflakeWarehouse.setFixedHeight(30)
        grid_layout.addWidget(label_account, 1, 0)
        grid_layout.addWidget(self.snowflakeAccount, 1, 1)
        grid_layout.addWidget(label_warehouse, 1, 2)
        grid_layout.addWidget(self.snowflakeWarehouse, 1, 3)

        # Row 2: Database & Schema
        label_db = QLabel("Database")
        self.snowflakeDatabase = QTextEdit()
        self.snowflakeDatabase.setFixedHeight(30)
        label_schema = QLabel("Schema")
        self.snowflakeSchema = QTextEdit()
        self.snowflakeSchema.setFixedHeight(30)
        grid_layout.addWidget(label_db, 2, 0)
        grid_layout.addWidget(self.snowflakeDatabase, 2, 1)
        grid_layout.addWidget(label_schema, 2, 2)
        grid_layout.addWidget(self.snowflakeSchema, 2, 3)

        self.group_tabs[group_name].addTab(tab_widget, source_name)


    def createGoogleCloudSourceTab(self, group_name, source_name):
        if group_name not in self.group_tabs:
            raise ValueError(f"Group '{group_name}' not found. Call createSourceGroupTab() first.")

        tab_widget = QWidget()
        grid_layout = QGridLayout(tab_widget)

        label_json = QLabel("GConsole JSON File")
        self.gCloudJsonFile = QTextEdit()
        self.gCloudJsonFile.setFixedHeight(30)
        grid_layout.addWidget(label_json, 0, 0)
        grid_layout.addWidget(self.gCloudJsonFile, 0, 1)

        label_blob = QLabel("Blob name")
        self.gCloudBlobName = QTextEdit()
        self.gCloudBlobName.setFixedHeight(30)
        grid_layout.addWidget(label_blob, 1, 0)
        grid_layout.addWidget(self.gCloudBlobName, 1, 1)

        self.group_tabs[group_name].addTab(tab_widget, source_name)


    def getGConsoleJson(self):
        """Return the text from the GConsole JSON File text edit."""
        return self.gCloudJsonFile.toPlainText() if hasattr(self, 'gCloudJsonFile') else None

    def getGCloudBlobName(self):
        """Return the text from the Blob name text edit."""
        return self.gCloudBlobName.toPlainText() if hasattr(self, 'gCloudBlobName') else None

    def select_callback(self, group_name, source_name):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a file")

        if file_path:
            self._addItem(group_name, source_name, file_path)

    def _addItem(self, group_name, source_name, file_path):
        list_widget = self.list_widgets[(group_name, source_name)]
        base_name = os.path.basename(file_path)
        existing_items = [list_widget.item(i).text() for i in range(list_widget.count())]
        if base_name not in existing_items:
            item = QListWidgetItem(base_name)
            item.setToolTip(file_path)
            list_widget.addItem(item)

            self.sentralControl.addEntryForFile(base_name)

    def addItems(self, group_name, source_name, file_paths):
        for file_path in file_paths:
            self._addItem(group_name, source_name, file_path)

    def getAllItemsInList(self, group_name, source_name):
        list_widget = self.list_widgets[(group_name, source_name)]
        return [
            list_widget.item(i).toolTip()
            for i in range(list_widget.count())
        ]

    def clear_callback(self, group_name, source_name):
        list_widget = self.list_widgets[(group_name, source_name)]
        list_widget.clear()

    def getAllGroups(self):
        """Return a list of all group names."""
        return list(self.group_tabs.keys())

    def getAllGroupSources(self, group):
        """Return all source names for a given group."""
        sources = []
        for (group_name, source_name) in self.list_widgets.keys():
            if group_name == group:
                sources.append(source_name)
        return sources



class AssistantManager(QObject):

    signal_update_command = pyqtSignal(str, dict)

    def __init__(self, sentralControl, parent=None):

        super().__init__()

        self.sentralControl = sentralControl

        global_signals.signal_update_sql_run_status.connect(self.on_signal_update_sql_run_status)

        self.timeKeeer = TimeKeeper()

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

    def getCurrentAndElapsedTimeStr(self):
        
        data = self.timeKeeer.stop()
        current = data.get("current", "")
        elapsed = data.get("elapsed", "")

        return f"[{elapsed}]"
    
    def getCurrentTimeStr(self):
        data = self.timeKeeer.start()

        return f"[{data}]"

    def _handleAssistantQuery(self):
        query = self.assistantInput.toPlainText().strip()

        if not query:
            return
        
        self.assistantInput.addHistory(query)

        # Append user input
        current_time = self.getCurrentTimeStr()
        self.assistantOutput.append(f"{current_time} <b>You:</b> {query}")
        self.assistantInput.clear()

        # Get LLM response
        try:
            json_llm_response = global_LLM_manager.query(query)
        except Exception as e:
            self.assistantOutput.append(f"<span style='color:red;'>Error: {str(e)}</span>")
            self.sentralControl.showMessage(f"Error: {str(e)}")
            return

        if not json_llm_response:
            self.assistantOutput.append(f"<span style='color:red;'>Error: No response from LLM.</span>")
            self.sentralControl.showMessage(f"Error: No response from LLM.")
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
        args = {"sql_query": sql_query}

        self.signal_update_command.emit(command, args)


    @pyqtSlot(dict)
    def on_signal_update_sql_run_status(self, result):
        
        if self.timeKeeer.isStarted():
            elapsed_time = self.getCurrentAndElapsedTimeStr()

            self.assistantOutput.append(f"{elapsed_time} <b>Assistant:</b> {result.get('message')}")
            if result.get("result") is not None:
                self.assistantOutput.append(f" {result.get('result')}")
        

    def _handleCommandOrActionRun(self, output):

        command = output.get("command_name")
        args = output.get("args", [])

        self.signal_update_command.emit(command, args)

        resp = f"<b>Assistant:</b> Use following action or analysis:\n \
                \t\t <b>{command}</b> \n\
            \t with arguments: \n\
                \t\t <b>{args}</b>"
        
        self.assistantOutput.append(resp)
        


