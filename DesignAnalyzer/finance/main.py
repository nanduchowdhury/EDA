
import sys
import os
import pdfplumber

import numpy as np

import logging


# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from predicates import Predicates, PredicateBase

class LoadPdfToolItem(ToolBarItemAbstract):
    def __init__(self, drawArea):
        super().__init__("Load Pdf")
        self.drawArea = drawArea

    def onClick(self):
        # self.read_pdf()

        logging.info("Loading waveform data started.")

        data = [(30, "Jan"), (45, "Feb"), (25, "Mar"), (50, "Apr"), (40, "May")]
        self.drawArea.plotBar(data, "Months", "Expenses")
        # self.drawArea.plotPie(data)
        # self.drawArea.plotWaveform([1, 2, 3, 4], [10, 30, 20, 25], "Iterations", "Estimate")

        logging.info("Loading waveform data done.")



    def plotDummyData(self):
        
        # x = np.linspace(0, 2 * np.pi, 1000)
        # y = np.sin(5 * x)

        x = np.linspace(0, 100, 100)         # 1000 points from 0 to 100
        y = np.random.uniform(0, 100, 100)   # 1000 random values in [0, 100)

        self.drawArea.plotWaveform(x, y)


    def read_pdf(self):

        logging.getLogger("pdfminer").setLevel(logging.WARNING)
        logging.getLogger("pdfplumber").setLevel(logging.WARNING)

        with pdfplumber.open("statement.pdf") as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        print(row)

class FindOutlier(PredicateBase):
    def __init__(self):
        super().__init__()

        self.args = {
            'component': None,  # Component name to search for outliers
        }

    def run(self):
        result = []
        component = self.args['component']
        if component:
            # Simulate finding outliers in the component data
            # In a real scenario, you would analyze the component data to find outliers
            result = [f"Outlier found in {component}"]
        else:
            result = ["No component specified for outlier search"]

        self.setOutputObject("result", result)  # Store result as a list
        logging.info(f"Outlier search done.")

        return result
    
class FinanceUI(MainUI):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Financials Analyzerr")

        self.loadPdfToolbarItem = LoadPdfToolItem(self.drawArea)
        
        self.menu.createToolbarItem(self.loadPdfToolbarItem)

        self.removeGenericPredicate()

        findOutlier = FindOutlier()
        self.all_predicates.addPredicate("outlier - find AI based", ["component"], findOutlier)



if __name__ == "__main__":
    run_BluePayload(FinanceUI)


