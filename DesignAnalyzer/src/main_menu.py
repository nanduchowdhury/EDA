from PyQt5.QtWidgets import QMainWindow, QAction, QPushButton, QMenuBar, QToolBar, QMenu, QApplication

from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

from abc import ABC, abstractmethod
import sys

class ToolBarItemAbstract(ABC):
    def __init__(self, label: str):
        self.button = QPushButton(label)

        self.button.clicked.connect(self.onClick)

    def getButton(self) -> QPushButton:
        return self.button

    @abstractmethod
    def onClick(self):
        """Derived class implements this."""
        pass

class MenuItemAbstract(ABC):
    @abstractmethod
    def onClick(self):
        pass

class MainMenuAndTBar:
    def __init__(self, window):
        self.window = window
        self.menu_bar = QMenuBar(window)
        window.setMenuBar(self.menu_bar)

        self.toolbar = QToolBar()
        window.addToolBar(self.toolbar)

        self.top_menus = {}

    def createMenuItem(self, topItemName, childItemName, itemObj: MenuItemAbstract):
        if topItemName not in self.top_menus:
            self.top_menus[topItemName] = QMenu(topItemName, self.window)
            self.menu_bar.addMenu(self.top_menus[topItemName])

        action = QAction(childItemName, self.window)
        action.triggered.connect(itemObj.onClick)
        self.top_menus[topItemName].addAction(action)

    def createToolbarItem(self, itemObj: ToolBarItemAbstract):
        self.toolbar.addWidget(itemObj.getButton())

