
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
from main_ui import MainUI
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from predicates import Predicates, PredicateBase

class LoadDataToolItem(ToolBarItemAbstract):
    def __init__(self, all_input_tabs, drawArea):
        super().__init__("Load data")

        self.all_input_tabs = all_input_tabs
        self.drawArea = drawArea

        self.data = None

    def onClick(self):

        logging.info("Loading CSV data started.")

        csvList = self.all_input_tabs["CSV"].getAllItemsInList()

        for csv_file in csvList:
            logging.info(f"Start reading CSV file: {csv_file}")
            self.read_csv(csv_file)
            logging.info(f"End reading CSV file: {csv_file}")

        # self.drawArea.plotBar(self.data, "Months", "Expenses")
        # self.drawArea.plotPie(data)
        # self.drawArea.plotWaveform([1, 2, 3, 4], [10, 30, 20, 25], "Iterations", "Estimate")

        # logging.info("Loading waveform data done.")

    def read_csv(self, csv_file):

        self.data = pd.read_csv(csv_file, low_memory=False)
        logging.info(f"DataFrame shape: {self.data.shape}")

        self.drawArea.loadFromDataFrame(self.data)
        logging.info("Data loaded into input area.")


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


class PredictNextMonths(PredicateBase):
    def __init__(self, loadDataObj):
        super().__init__()
        self.loadDataObj = loadDataObj

        self.args = {
            'num-months': 2,
        }

    def run(self):
        result = []
        num_months = self.args['num-months']
        if num_months:
            result = self.predict_next_months(self.loadDataObj.data, int(num_months))
            if not result:
                result = ["Prediction not found"]
        else:
            result = ["Num months not specified for prediction"]

        self.setOutputObject("result", result)  # Store result as a list
        logging.info(f"Prediction search done.")

        return result

    def predict_next_months(self, data, num_months):
        """
        Predicts values for the next `num_months` based on input time-series data.

        Args:
            data: List of (value, label) tuples, e.g., [(30, "Jan"), (45, "Feb"), ...]
            num_months: Number of future months to predict

        Returns:
            List of predicted float values, one for each future month.
        """
        if len(data) < 2:
            raise ValueError("Need at least 2 data points to make a prediction")

        # Prepare X as [[0], [1], ...] and y as [val1, val2, ...]
        X = np.array([[i] for i in range(len(data))])
        y = np.array([val for val, _ in data])

        # Fit linear regression model
        model = LinearRegression()
        model.fit(X, y)

        # Predict next months
        future_indices = np.array([[len(data) + i] for i in range(num_months)])
        predicted_values = model.predict(future_indices)

        return predicted_values.tolist()

class ExtractColumnsRows(PredicateBase):
    def __init__(self, loadDataObj):
        super().__init__()
        self.loadDataObj = loadDataObj

        self.args = {
            'column_name': "",
            'containing_string': "",
        }

    def run(self):
        df = self.loadDataObj.data
        result = []

        column_name = self.args['column_name']
        containing_string = self.args['containing_string']

        if column_name and containing_string:
            result = df[df[column_name].str.contains(containing_string, case=False, na=False)]
            if not result.empty:
                for col_name in result.columns:
                    col_data = result[col_name].tolist()  # Get list of values for this column
                    self.setOutputObject(col_name, col_data)
            else:
                result = ["No matching rows found for the specified column and row name"]
        else:
            result = ["No column or row name specified for extraction"]

        return result

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
        super().__init__(PLOT_OR_DRAW="TABLE")
        self.setWindowTitle("Financials Analyzerr")

        self.bottomArea.create_input_tab("CSV")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.all_input_tabs, 
                                                    self.drawArea)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        self.removeGenericPredicate()

        findOutlier = FindOutlier(self.loadDataToolbarItem)
        self.all_predicates.addPredicate("outlier - based on mean/std-dev", ["z-value"], findOutlier)

        predict = PredictNextMonths(self.loadDataToolbarItem)
        self.all_predicates.addPredicate("predict next months - linear regression", ["num-months"], predict)

        extract = ExtractColumnsRows(self.loadDataToolbarItem)
        self.all_predicates.addPredicate("extract data where specified column contains a string or name.", ["column_name", "containing_string"], extract)



if __name__ == "__main__":
    run_BluePayload(FinanceUI)


