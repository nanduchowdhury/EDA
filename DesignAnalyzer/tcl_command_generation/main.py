
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal

import sys
import os
import pdfplumber

import numpy as np
import json

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
from RAG import GeminiRAG, GeminiTclRAG


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


class ShowAllTclCommandsAndArgsMenuItem(MenuItemAbstract):
    def __init__(self, sentralControl, ug_processor):

        self.sentralControl = sentralControl
        self.ug_processor = ug_processor

    def onClick(self):
        drawArea = self.sentralControl.viewerTabs.getSelectedTabWidget()

        pdf_base_name = drawArea.get_file_base_name()
        self.ug_processor.set_doc_name(pdf_base_name)

        pages_text = None
        if not self.ug_processor.is_cache_available():
            pages_text = drawArea.getPagesText()
        cmds_and_args = self.ug_processor.getCommandsAndArgs(pages_text)
        

        all_cmds = list(cmds_and_args.keys())
        all_args = [json.dumps(v, indent=2) for v in cmds_and_args.values()]

        outputs = {}
        outputs["Commands"] = all_cmds
        outputs["Args"] = all_args

        self.invoke_results("TCL Commands and Args", "TCL commands and their arguments extracted from PDF", outputs)

    
class VibeTclCoding(PredicateBase, QObject):
    def __init__(self, sentralControl, gemini_tcl_rag, ug_processor):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl
        self.gemini_tcl_rag = gemini_tcl_rag
        self.ug_processor = ug_processor

        self.args = {
            'user query': {
                'user_value': '',
                'default': '',
                'tool_tip': 'natural language input',
                'example': 'example : set multicycle path...'
            }
        }

    def run(self):
        
        result = []

        user_query = self.args['user query']['user_value']

        drawArea = self.sentralControl.viewerTabs.getSelectedTabWidget()

        pdf_base_name = drawArea.get_file_base_name()
        self.ug_processor.set_doc_name(pdf_base_name)

        pages_text = None
        if not self.ug_processor.is_cache_available():
            pages_text = drawArea.getPagesText()
        cmds_and_args = self.ug_processor.getCommandsAndArgs(pages_text)

        # Perform RAG using commands and args.
        print(f"Running RAG with {len(cmds_and_args)} commands and args...")

        self.gemini_tcl_rag.set_cmds_and_args(cmds_and_args)
        response = self.gemini_tcl_rag.ask(user_query)

        print(f"Response from Gemini RAG: {response}")

        return response


class PdfUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="PDF")
        self.setWindowTitle("TCL commands Analyzerr")

        self.sentralControl.product_vertical = "EDA_TCL_CMD_GENERATOR"

        self.predicateHolderWidget.hide()

        self.bottomArea.create_input_tab("PDF")


        self.gemini_tcl_rag = GeminiTclRAG()
        self.ug_processor = UserGuideProcessor()


        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        self.showAllTclCommandsAndArgsMenuItem = ShowAllTclCommandsAndArgsMenuItem(self.sentralControl, 
                                        self.ug_processor)

        self.menu.createMenuItem("Actions", "Show TCL Commands", self.showAllTclCommandsAndArgsMenuItem)

        

        self.hidePredicateGroup("PCA")
        self.hidePredicateGroup("SQL")
        self.hidePredicateGroup("charts")

        cmds = VibeTclCoding(self.sentralControl, self.gemini_tcl_rag, self.ug_processor)
        self.all_predicates.addPredicate("EDA", "vibe generate TCL commands based on PDF", cmds)





if __name__ == "__main__":
    run_BluePayload(PdfUI)



