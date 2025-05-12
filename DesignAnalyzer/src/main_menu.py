from PyQt5.QtWidgets import QMainWindow, QAction, QMenuBar, QMenu, QApplication
from abc import ABC, abstractmethod
import sys

class MenuItemAbstract(ABC):
    @abstractmethod
    def onClick(self):
        pass

class MainMenu:
    def __init__(self, window):
        self.window = window
        self.menu_bar = QMenuBar(window)
        window.setMenuBar(self.menu_bar)
        self.top_menus = {}

    def createItem(self, topItemName, childItemName, itemObj):
        if topItemName not in self.top_menus:
            self.top_menus[topItemName] = QMenu(topItemName, self.window)
            self.menu_bar.addMenu(self.top_menus[topItemName])

        action = QAction(childItemName, self.window)
        action.triggered.connect(itemObj.onClick)
        self.top_menus[topItemName].addAction(action)

