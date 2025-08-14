
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

        return response

class PdfUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="PDF")

        self.sentralControl.product_vertical = "PDF_CHAT"

        self.setWindowTitle("Documents Analyzerr")

        self.bottomArea.create_input_tab("PDF")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        self.gemini_rag = GeminiRAG()

        self.hidePredicateGroup("PCA")
        self.hidePredicateGroup("SQL")
        self.hidePredicateGroup("charts")


        chat = PdfChatPredicate(self.sentralControl, self.gemini_rag)
        self.all_predicates.addPredicate("PDF", "chat with PDF to answer questions", chat)

        

if __name__ == "__main__":
    run_BluePayload(PdfUI)



