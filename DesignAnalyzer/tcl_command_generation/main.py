
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

import sys
import os
import pdfplumber

import numpy as np


import re
import string

import spacy

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


    
class getTclCommands(PredicateBase, QObject):
    def __init__(self, sentralControl):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl


        ##################################################################
        #
        # Make sure to download the vocabulary-model using following command:
        #
        #           ..\..\..\AppData\Local\Programs\Python\Python311\python.exe -m spacy download en_core_web_sm
        #
        #  Alternatively you can also download following:
        #
        #            en_core_web_md → medium (better accuracy, bigger vectors)
        #            en_core_web_lg → large (best accuracy, most memory use)
        #
        #
        ##################################################################

        self.nlp = spacy.load("en_core_web_sm")

        self.args = {

        }

    def run(self):
        
        result = []

        drawArea = self.sentralControl.viewerTabs.getSelectedTabWidget()
        pages_text = drawArea.getPagesText()        

        print("Extracting commands from PDF...")

        commands = set()
        for page_num, text in enumerate(pages_text):
            if text.strip():
                cmds = self.extract_commands(text)
                commands.update(cmds)

        result = list(commands)

        print(f"Extracted {len(result)} commands from PDF.")
                
        self.setOutputObject("Commands", result)
                
        return result



    def extract_commands(self, page_text, check_n_pre_post_words=3):
        """
        Extracts unique command words from page_text that:
        1. Contain '_' and only letters/underscores.
        2. Have the word 'command' within N words before or after.
        
        Args:
            page_text (str): The text to process.
            check_n_pre_post_words (int): Number of words before/after to check for 'command'.
        Returns:
            list[str]: Unique matching commands.
        """
        doc = self.nlp(page_text)
        commands = set()

        for i, token in enumerate(doc):
            word = token.text
            # Match words containing '_' and only letters/underscores
            if '_' in word and re.fullmatch(r'[A-Za-z_]+', word):
                # Collect surrounding words in lowercase
                pre_words = [t.text.lower() for t in doc[max(0, i - check_n_pre_post_words):i]]
                post_words = [t.text.lower() for t in doc[i + 1:i + 1 + check_n_pre_post_words]]
                context = pre_words + post_words

                # Check if any context word contains "command"
                if any("command" in w for w in context):
                    commands.add(word)

        return list(commands)


class PdfUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="PDF")
        self.setWindowTitle("TCL commands Analyzerr")

        self.bottomArea.create_input_tab("PDF")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        pred = getTclCommands(self.sentralControl)
        self.all_predicates.addPredicate("PDF", "get TCL commands from PDF", pred)

        

if __name__ == "__main__":
    run_BluePayload(PdfUI)



