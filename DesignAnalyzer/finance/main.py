
import sys
import os
import pdfplumber

import numpy as np

import logging

import csv

# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from predicates import Predicates, PredicateBase

class LoadDataToolItem(ToolBarItemAbstract):
    def __init__(self, all_input_tabs, drawArea):
        super().__init__("Load data")

        self.all_input_tabs = all_input_tabs
        self.drawArea = drawArea

        self.data = []  # Initialize data as an empty list

    def onClick(self):

        logging.info("Loading CSV data started.")

        csvList = self.all_input_tabs["CSV"].getAllItemsInList()

        for csv_file in csvList:
            logging.info(f"Reading CSV file: {csv_file}")
            self.data = self.read_csv(csv_file)
            logging.info(f"Data read from {csv_file}: {self.data}")

        self.drawArea.plotBar(self.data, "Months", "Expenses")
        # self.drawArea.plotPie(data)
        # self.drawArea.plotWaveform([1, 2, 3, 4], [10, 30, 20, 25], "Iterations", "Estimate")

        logging.info("Loading waveform data done.")


    def read_csv(self, csv_file):
        data = []
        with open(csv_file, mode="r") as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    amount = int(row[0])
                    month = row[1]
                    data.append((amount, month))
        return data


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
    def __init__(self, loadDataObj):
        super().__init__()
        self.loadDataObj = loadDataObj

        self.args = {
            'z-value': 0.9,
        }

    def run(self):
        result = []
        z_val = self.args['z-value']
        if z_val:
            result = self.find_outlier_months()
            if not result:
                result = ["No outliers found"]
        else:
            result = ["No z-value specified for outlier search"]

        self.setOutputObject("result", result)  # Store result as a list
        logging.info(f"Outlier search done.")

        return result
    
    def find_outlier_months(self, threshold=0.9):
        """
        data: List of tuples (value, label)
        threshold: Z-score threshold to detect outliers (default=2.0)
        Returns: List of (label, value, z_score) for outliers
        """
        data = self.loadDataObj.data

        values = np.array([value for value, _ in data])
        labels = [label for _, label in data]

        mean = np.mean(values)
        std_dev = np.std(values)

        outliers = []

        for i, value in enumerate(values):
            z_score = (value - mean) / std_dev if std_dev > 0 else 0
            if abs(z_score) > threshold:
                # outliers.append((labels[i], value, z_score))
                outliers.append((labels[i]))

        return outliers
    
class FinanceUI(MainUI):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Financials Analyzerr")

        self.bottomArea.create_input_tab("CSV")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.all_input_tabs, 
                                                    self.drawArea)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        self.removeGenericPredicate()

        findOutlier = FindOutlier(self.loadDataToolbarItem)
        self.all_predicates.addPredicate("outlier - based on mean/std-dev", ["z-value"], findOutlier)



if __name__ == "__main__":
    run_BluePayload(FinanceUI)


