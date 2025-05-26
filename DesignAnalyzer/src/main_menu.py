
import re
from PyQt5.QtWidgets import (
    QMainWindow, QAction, QPushButton, QMenuBar, QToolBar,
    QMenu, QApplication, QStyle
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from abc import ABC, abstractmethod


class ToolBarItemAbstract(ABC):
    # Mapping label keywords to QStyle.StandardPixmap enums
    ICON_MAP = {
        # Zoom in/out: small lens / large lens approximations
        'zoom in': QStyle.SP_FileDialogContentsView,     # looks like magnifier
        'zoom out': QStyle.SP_FileDialogDetailedView,
        'zoom fit': QStyle.SP_FileDialogListView,        # another magnifier style
        
        "up": QStyle.SP_ArrowUp,  # generic up arrow
        "down": QStyle.SP_ArrowDown,  # generic down arrow
        'left': QStyle.SP_ArrowBack,  # generic left arrow
        'right': QStyle.SP_ArrowForward,  # generic right arrow

        # Others as before
        'save': QStyle.SP_DialogSaveButton,
        'clear': QStyle.SP_TrashIcon,
        'delete': QStyle.SP_TrashIcon,
        'reset': QStyle.SP_DialogResetButton,
        'apply': QStyle.SP_DialogApplyButton,
        'close': QStyle.SP_DialogCloseButton,
        'exit': QStyle.SP_DialogCloseButton,
        'help': QStyle.SP_DialogHelpButton,
        'settings': QStyle.SP_FileDialogDetailedView,
        'info': QStyle.SP_MessageBoxInformation,
        'warning': QStyle.SP_MessageBoxWarning,
        'error': QStyle.SP_MessageBoxCritical,
    }

    def __init__(self, label: str):
        self.button = QPushButton()
        self.button.setToolTip(label)
        icon = self.get_icon_for_label(label)
        if icon is not None:
            self.button.setIcon(QApplication.style().standardIcon(icon))
        elif "load" in label.lower():
            self.button.setText("⏫")
        else:
            self.button.setText(label)  # fallback to text if no icon found

        self.button.setFixedSize(32, 32)  # square buttons

        self.button.setStyleSheet("""
            QPushButton {
                background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 1,
                                                fx: 0.5, fy: 0.5,
                                                stop: 0 #1E90FF, stop: 1 #F0F0F0);
                color: black;
                border: 2px solid #ADD8E6;
                border-radius: 6px;
                padding: 4px;
                text-align: center;
                white-space: normal;
            }
            QPushButton:hover {
                background-color: qradialgradient(cx: 0.5, cy: 0.5, radius: 1,
                                                fx: 0.5, fy: 0.5,
                                                stop: 0 #0000FF, stop: 1 #D3D3D3);
                border: 2px solid #5CACEE;
            }
        """)

        self.button.clicked.connect(self.onClick)

    def get_icon_for_label(self, label: str):
        label = label.lower()
        # Search keys with regex match on label string
        for key in self.ICON_MAP:
            # Use regex word boundary match to avoid partials inside other words
            if re.search(r'\b' + re.escape(key) + r'\b', label):
                return self.ICON_MAP[key]
        return None

    def getButton(self) -> QPushButton:
        return self.button

    @abstractmethod
    def onClick(self):
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
