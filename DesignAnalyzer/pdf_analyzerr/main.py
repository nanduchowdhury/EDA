
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

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


    
class getPdfTablePredicate(PredicateBase, QObject):
    def __init__(self, sentralControl):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl

        self.args = {

        }

    def run(self):
        
        result = []

        drawArea = self.sentralControl.viewerTabs.getSelectedTabWidget()
        tables = drawArea.getAllTables()        

        if not tables:
            raise ValueError("No table found.")
            
        table = tables[0]

        for col_name in table.columns:
            self.setOutputObject(col_name, table[col_name].tolist())
            
        return result
        


class PdfUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="PDF")
        self.setWindowTitle("Documents Analyzerr")

        self.bottomArea.create_input_tab("PDF")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        pred = getPdfTablePredicate(self.sentralControl)
        self.all_predicates.addPredicate("PDF", "get tables from PDF", pred)

        

if __name__ == "__main__":
    run_BluePayload(PdfUI)



