
import sys
import os
import pdfplumber

import numpy as np

import logging 


import csv

import pandas as pd 

from sklearn.linear_model import LinearRegression

# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI, SourceDropDown, ManageViewerTabs
from main_menu import MenuItemAbstract, ToolBarItemAbstract
from predicates import Predicates, PredicateBase

from web_scrap import WebPageTableDataExtractor

class LoadDataToolItem(ToolBarItemAbstract):
    def __init__(self, inputTab, sentralControl):
        super().__init__("Load data")

        self.inputTab = inputTab
        self.sentralControl = sentralControl

        self.webExtractor = None

    def onClick(self):

        urlList = self.inputTab.webUrlEdit.toPlainText().splitlines()

        url_to_file_name = None

        for url in urlList:
            self.sentralControl.showMessage(f"Start reading url: {url}")

            self.webExtractor = WebPageTableDataExtractor(url)
            url_to_file_name = self.webExtractor.getFileNameForDataFrame()
            self.sentralControl.addEntryForFile(url_to_file_name)
            data = self.webExtractor.getDataFrame()
            self.sentralControl.addDataForFileEntity(url_to_file_name, data)

            self.sentralControl.showMessage(f"End reading url: {url}")

        self.sentralControl.showFileInTab(url_to_file_name)

    
class ReraUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="TABLE")
        self.setWindowTitle("RERA Analyzerr")

        self.bottomArea.create_input_tab("CSV")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab,
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)


if __name__ == "__main__":
    run_BluePayload(ReraUI)


