


import sys
import os
import pdfplumber

import numpy as np

import logging
import math
import csv

from sklearn.linear_model import LinearRegression

# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from predicates import Predicates, PredicateBase

class LoadDataToolItem(ToolBarItemAbstract):
    def __init__(self, inputTab, sentralControl):
        super().__init__("Load data")

        self.inputTab = inputTab
        self.sentralControl = sentralControl


    def onClick(self):

        self.sentralControl.showMessage("Loading PDF started.")

        pdfList = self.inputTab.getAllItemsInList("Files", "PDF")

        for pdf_file in pdfList:
            logging.info(f"Reading PDF file: {pdf_file}")

            drawArea = self.sentralControl.viewerTabs.getSelectedTabWidget()
            data = drawArea.loadPdf(pdf_file)
            # drawArea.init_vtk_scene(data)
            self.sentralControl.addDataForFileEntity(pdf_file, data)

            logging.info(f"PDF file {pdf_file} read successfully.")
        self.sentralControl.showMessage("Loading PDF data done.")


    
class PdfUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="PDF")
        self.setWindowTitle("Documents Analyzerr")

        self.bottomArea.create_input_tab("PDF")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        

if __name__ == "__main__":
    run_BluePayload(PdfUI)



