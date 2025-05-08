from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QCheckBox, QComboBox, QTextEdit, QPushButton, QLabel,
    QListWidget,
    QAbstractItemView, QTableWidget, QTableWidgetItem, QSizePolicy, QLineEdit,
    QAction
)

from PyQt5.QtWidgets import QFileDialog

from PyQt5.QtCore import Qt
import sys

from main_menu import MainMenu
from main_menu import MenuItemAbstract

from def_parser import DefParser


class FileOpenMenuItem(MenuItemAbstract):
    def onClick(self):

        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select a file")
        if file_path:
            self.selectedFile = file_path
        
        parser = DefParser()
        json_def = parser.parse(self.selectedFile)

        print(json_def)


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
        self.mainLayout.addWidget(self.controlArea)

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

        self.commandList = QListWidget()
        self.commandList.setSelectionMode(QAbstractItemView.SingleSelection)
        self.commandList.addItems(["Option 1", "Option 2", "Option 3"])
        self.commandList.setMaximumWidth(100)

        row3.addWidget(self.commandList)

        paramWidget = QWidget()
        paramLayout = QVBoxLayout()
        self.paramEdits = []

        for labelText in ["Param 1", "Param 2", "Param 3"]:
            hbox = QHBoxLayout()
            label = QLabel(labelText)
            edit = QLineEdit()
            hbox.addWidget(label)
            hbox.addWidget(edit)
            paramLayout.addLayout(hbox)
            self.paramEdits.append(edit)

        paramWidget.setLayout(paramLayout)
        row3.addWidget(paramWidget)
        layout.addLayout(row3)

        # Row 4: Execute Button
        executeButton = QPushButton("Execute")
        layout.addWidget(executeButton)

        # Row 5: Results Label + Table
        layout.addWidget(QLabel("Results"))

        self.commandTable = QTableWidget(3, 2)
        self.commandTable.setHorizontalHeaderLabels(["Column A", "Column B"])
        self.commandTable.setItem(0, 0, QTableWidgetItem("Row0-Col0"))
        self.commandTable.setItem(0, 1, QTableWidgetItem("Row0-Col1"))

        layout.addWidget(self.commandTable)

        self.commandArea.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainUI()
    window.show()
    sys.exit(app.exec_())
