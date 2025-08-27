
import re
from PyQt6.QtWidgets import (
    QMainWindow, QPushButton, QMenuBar, QToolBar,
    QMenu, QApplication, QStyle, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt
from abc import ABC, abstractmethod

import pandas as pd
from torch import layout

from common import global_signals


class ToolBarItemAbstract(ABC):
    # Mapping label keywords to QStyle.StandardPixmap enums
    ICON_MAP = {
        # Zoom in/out: small lens / large lens approximations
        'zoom in': QStyle.StandardPixmap.SP_FileIcon,     # looks like magnifier
        'zoom out': QStyle.StandardPixmap.SP_FileDialogDetailedView,
        'zoom fit': QStyle.StandardPixmap.SP_DialogResetButton,        # another magnifier style

        "up": QStyle.StandardPixmap.SP_ArrowUp,  # generic up arrow
        "down": QStyle.StandardPixmap.SP_ArrowDown,  # generic down arrow
        'left': QStyle.StandardPixmap.SP_ArrowBack,  # generic left arrow
        'right': QStyle.StandardPixmap.SP_ArrowForward,  # generic right arrow

        # Others as before
        'save': QStyle.StandardPixmap.SP_DialogSaveButton,
        'clear': QStyle.StandardPixmap.SP_TrashIcon,
        'delete': QStyle.StandardPixmap.SP_TrashIcon,
        'reset': QStyle.StandardPixmap.SP_DialogResetButton,
        'apply': QStyle.StandardPixmap.SP_DialogApplyButton,
        'close': QStyle.StandardPixmap.SP_DialogCloseButton,
        'exit': QStyle.StandardPixmap.SP_DialogCloseButton,
        'help': QStyle.StandardPixmap.SP_DialogHelpButton,
        'settings': QStyle.StandardPixmap.SP_FileDialogDetailedView,
        'info': QStyle.StandardPixmap.SP_MessageBoxInformation,
        'warning': QStyle.StandardPixmap.SP_MessageBoxWarning,
        'error': QStyle.StandardPixmap.SP_MessageBoxCritical,
    }

    def __init__(self, label: str):
        self.button = QPushButton()
        self.button.setToolTip(label)
        icon = self.get_icon_for_label(label)
        if icon is not None:
            self.button.setIcon(QApplication.style().standardIcon(icon))
        elif "load" in label.lower():
            self.button.setText("⏫")
        elif "show mesh" in label.lower():
            self.button.setText("🔳")
        elif "hide mesh" in label.lower():
            self.button.setText("⬛")
        elif "tile tabs" in label.lower():
            self.button.setText("🔲")
        elif "regular tabs" in label.lower():
            self.button.setText("📑")
        else:
            self.button.setText(label)  # fallback to text if no icon found

        self.button.setFixedSize(20, 20)  # square buttons

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

    def invoke_results(self, results_tab_name, tab_tool_tip, outputs):
        
        output_list = list(self._iterateOutputs(outputs))

        global_signals.signal_fire_results_tab.emit(
            results_tab_name, tab_tool_tip, output_list, pd.DataFrame(output_list), None
        )

    def _iterateOutputs(self, outputs):
        for name, values in outputs.items():
            yield name, values


class MainMenuAndTBar:
    def __init__(self, window):
        self.window = window
        self.menu_bar = QMenuBar(window)
        window.setMenuBar(self.menu_bar)

        self.toolbar = QToolBar()
        window.addToolBar(self.toolbar)

        self.top_menus = {}

    def createMenuItem(self, topItemName, childItemName, itemObj):
        if topItemName not in self.top_menus:
            self.top_menus[topItemName] = QMenu(topItemName, self.window)
            self.menu_bar.addMenu(self.top_menus[topItemName])

        action = QAction(childItemName, self.window)
        action.triggered.connect(itemObj.onClick)
        self.top_menus[topItemName].addAction(action)

    def createToolbarItem(self, itemObj):
        self.toolbar.addWidget(itemObj.getButton())

    def createToolbarGroupItems(self, group_name: str, item_objs: list):
        group_widget = QWidget()
        layout = QHBoxLayout(group_widget)
        
        layout.setContentsMargins(2, 1, 2, 1)  # no margin
        layout.setSpacing(0)                   # no spacing between buttons

        for item_obj in item_objs:
            btn = item_obj.getButton()
            btn.setCheckable(True)
            layout.addWidget(btn)

        # Style: Add border to the group
        group_widget.setStyleSheet("""
            QWidget {
                border: 1px solid gray;
                border-radius: 6px;
                background-color: #f9f9f9;
            }

            QWidget:hover {
                background-color: #e0e0ff;
                border: 1px solid #6666cc;
            }
        """)

        # Add the group with spacing
        self.toolbar.addWidget(group_widget)

        # Optional: add spacer after group to separate from next group
        spacer = QWidget()
        spacer.setFixedWidth(6)
        self.toolbar.addWidget(spacer)
