
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


class PdfChatPredicate(PredicateBase, QObject):
    def __init__(self, sentralControl, gemini_rag):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl
        self.gemini_rag = gemini_rag

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
        pages_text = drawArea.getPagesText()   

        pdf_base_name = drawArea.get_file_base_name()
        print(f"Processing PDF pages for RAG for PDF file: {pdf_base_name}")

        self.gemini_rag.set_doc_name(pdf_base_name)
        self.gemini_rag.load_from_list(pages_text, chunk_size=800, overlap=50)


        response = self.gemini_rag.ask(user_query, top_k=3)
        print(f"Response from Gemini RAG: {response}")

    
class GetTclCommands(PredicateBase, QObject):
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
        pages_text = drawArea.getPagesText()        

        
        result_cmds, result_args = self.ug_processor.getCommandsAndArgs(pages_text)

        self.setOutputObject("Commands", result_cmds)
        self.setOutputObject("Args", result_args)



        # Perform RAG using commands and args.
        print(f"Running RAG with {len(result_cmds)} commands and {len(result_args)} args...")

        pages_cmds_args = []
        for cmd, args in zip(result_cmds, result_args):
            pages_cmds_args.append(f"Command: {cmd}, Args: {args}")

        pdf_base_name = drawArea.get_file_base_name()

        self.gemini_tcl_rag.set_doc_name(pdf_base_name)
        self.gemini_tcl_rag.load_from_list(pages_cmds_args, chunk_size=800, overlap=50)


        response = self.gemini_tcl_rag.ask(user_query, top_k=3)
        print(f"Response from Gemini RAG: {response}")



        return True



class PdfUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="PDF")
        self.setWindowTitle("TCL commands Analyzerr")

        self.bottomArea.create_input_tab("PDF")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        self.gemini_rag = GeminiRAG()
        self.gemini_tcl_rag = GeminiTclRAG()
        self.ug_processor = UserGuideProcessor()

        self.hidePredicateGroup("PCA")
        self.hidePredicateGroup("SQL")
        self.hidePredicateGroup("charts")

        cmds = GetTclCommands(self.sentralControl, self.gemini_tcl_rag, self.ug_processor)
        self.all_predicates.addPredicate("EDA", "list all TCL commands referred in PDF", cmds)

        chat = PdfChatPredicate(self.sentralControl, self.gemini_rag)
        self.all_predicates.addPredicate("PDF", "chat with PDF to answer questions", chat)



if __name__ == "__main__":
    run_BluePayload(PdfUI)



