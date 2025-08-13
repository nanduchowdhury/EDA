
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

import sys
import os
import pdfplumber

import numpy as np


import re
import string


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

from ug_processor import UserGuideProcessor
from RAG import GeminiRAG


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


class TclCommandConversion(PredicateBase, QObject):
    def __init__(self, sentralControl):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl

        self.args = {
            'nlp': {
                'user_value': '',
                'default': '',
                'tool_tip': 'natural language input',
                'example': 'example : set multicycle path...'
            }
        }

    def run(self):
        
        result = []

        user_nlp = self.args['nlp']['user_value']

        drawArea = self.sentralControl.viewerTabs.getSelectedTabWidget()
        pages_text = drawArea.getPagesText()   

        print("Processing PDF pages for RAG...")


        rag = GeminiRAG()
        rag.load_from_list(pages_text, chunk_size=800, overlap=50)


        response = rag.ask(user_nlp, top_k=3)
        print(f"Response from Gemini RAG: {response}")

    
class GetTclCommands(PredicateBase, QObject):
    def __init__(self, sentralControl):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl

        self.args = {

        }

    def run(self):
        
        result = []

        drawArea = self.sentralControl.viewerTabs.getSelectedTabWidget()
        pages_text = drawArea.getPagesText()        

        ug_processor = UserGuideProcessor()
        result_cmds, result_args = ug_processor.getCommandsAndArgs(pages_text)

        self.setOutputObject("Commands", result_cmds)
        self.setOutputObject("Args", result_args)

        return True



class PdfUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="PDF")
        self.setWindowTitle("TCL commands Analyzerr")

        self.bottomArea.create_input_tab("PDF")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        self.hidePredicateGroup("PCA")
        self.hidePredicateGroup("SQL")
        self.hidePredicateGroup("charts")

        cmds = GetTclCommands(self.sentralControl)
        self.all_predicates.addPredicate("EDA", "list all TCL commands referred in PDF", cmds)

        conv = TclCommandConversion(self.sentralControl)
        self.all_predicates.addPredicate("EDA", "convert natural language to TCL commands", conv)



if __name__ == "__main__":
    run_BluePayload(PdfUI)



