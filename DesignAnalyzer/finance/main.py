
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
from main_ui import MainUI, SourceDropDown, ManageViewerTabs
from main_menu import MenuItemAbstract, ToolBarItemAbstract
from predicates import Predicates, PredicateBase

class LoadDataToolItem(ToolBarItemAbstract):
    def __init__(self, all_input_tabs, sentralControl):
        super().__init__("Load data")

        self.all_input_tabs = all_input_tabs
        self.sentralControl = sentralControl

    def onClick(self):

        csvList = self.all_input_tabs["CSV"].getAllItemsInList()

        for csv_file in csvList:
            self.sentralControl.showMessage(f"Start reading CSV file: {csv_file}")
            self.read_csv(csv_file)
            self.sentralControl.showMessage(f"End reading CSV file: {csv_file}")

        self.sentralControl.showFileInTab(csvList[0])

        # self.drawArea.plotBar(data, "Months", "Expenses")
        # self.drawArea.plotPie(data)
        # self.drawArea.plotWaveform([1, 2, 3, 4], [10, 30, 20, 25], "Iterations", "Estimate")


    def read_csv(self, csv_file):

        data = pd.read_csv(csv_file, low_memory=False)

        self.sentralControl.addDataForFileEntity(csv_file, data)


    def plotDummyData(self):
        
        # x = np.linspace(0, 2 * np.pi, 1000)
        # y = np.sin(5 * x)

        x = np.linspace(0, 100, 100)         # 1000 points from 0 to 100
        y = np.random.uniform(0, 100, 100)   # 1000 random values in [0, 100)

        # self.drawArea.plotWaveform(x, y)


    def read_pdf(self):

        logging.getLogger("pdfminer").setLevel(logging.WARNING)
        logging.getLogger("pdfplumber").setLevel(logging.WARNING)

        with pdfplumber.open("statement.pdf") as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        print(row)


class CreateWorldMap(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.cities = None

        self.args = {
            'column_name': ""
        }

    def run(self):

        column_name = self.args['column_name']

        drawArea = self.sentralControl.viewerTabs.addTabByType("WORLD_MAP", 
                                    self.getShortName(),
                                    self.getCompleteNameWithArgs())

        df_list = self.sentralControl.getDataForSelectedEntity()

        df = df_list[0]

        drawArea.setDataFrame(df)
        drawArea.setColumnName(column_name)
        drawArea.validateCities()
        drawArea.showCities()

        return True
    

class PredictNextMonths(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'column_name': '',
            'num-months': 2,
        }

    def run(self):
        result = []
        column_name = self.args['column_name']
        num_months = self.args['num-months']

        if num_months and column_name:

            df_list = self.sentralControl.getDataForSelectedEntity()
            df = df_list[0]

            if column_name not in df.columns:
                raise ValueError(f"Column '{column_name}' not found in DataFrame.")
            
            new_df = df[[column_name]].copy()
            result = self.predict_next_months(new_df, 
                                              int(num_months))
            if not result:
                result = ["Prediction not found"]
        else:
            result = ["Num months not specified for prediction"]

        self.setOutputObject("Amount next few months", result)  # Store result as a list
        self.sentralControl.showMessage(f"Prediction search done.")

        return result

    def predict_next_months(self, data: list[float], num_months: int) -> list[float]:
        """
        Predicts values for the next `num_months` based on input time-series data.

        Args:
            data: List of numeric values, e.g., [30, 45, 60, ...]
            num_months: Number of future months to predict

        Returns:
            List of predicted float values, one for each future month.
        """
        if len(data) < 2:
            raise ValueError("Need at least 2 data points to make a prediction")

        # Prepare X as [[0], [1], ...] and y as [val1, val2, ...]
        X = np.arange(len(data)).reshape(-1, 1)
        y = np.array(data)

        # Fit linear regression model
        model = LinearRegression()
        model.fit(X, y)

        # Predict for future months
        future_indices = np.arange(len(data), len(data) + num_months).reshape(-1, 1)
        predicted_values = model.predict(future_indices)

        return predicted_values.tolist()

class ExtractColumnsRows(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'column_name': "",
            'containing_string': "",
        }

    def run(self):
        
        df_list = self.sentralControl.getDataForSelectedEntity()
        df = df_list[0]
        
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
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'column_name': '',
            'z-value': 0.9
        }

    def run(self):
        result = []
        column_name = self.args['column_name']
        z_val = self.args['z-value']

        if z_val and column_name:

            df_list = self.sentralControl.getDataForSelectedEntity()
            df = df_list[0]

            if column_name not in df.columns:
                raise ValueError(f"Column '{column_name}' not found in DataFrame.")
            
            new_df = df[[column_name]].copy()
            results = self.find_outlier_months(new_df, float(z_val))
            if not results:
                result = ["Outlier not found"]
        else:
            result = ["Num months not specified for Outlier search"]

        self.setOutputObject(column_name, results[0])
        self.setOutputObject("outlier", results[1])

        self.sentralControl.showMessage(f"Outlier search done.")

        return result


    
    def find_outlier_months(self, data: list[float], threshold: float = 0.9) -> list[str]:
        """
        Identifies outlier values in a numeric time-series based on z-score.

        Args:
            data: List of numeric values, e.g., [30, 45, 60, 10, 200]
            threshold: Z-score threshold for detecting outliers

        Returns:
            List of 'yes' or 'no' for each data point indicating if it's an outlier.
        """
        if len(data) < 2:
            return ['no'] * len(data)

        values = np.array(data)
        mean = np.mean(values)
        std_dev = np.std(values)

        result1 = []
        result2 = []
        for value in values:
            z_score = (value - mean) / std_dev if std_dev > 0 else 0

            result1.append(value)
            result2.append('yes' if abs(z_score) > threshold else 'no')

        return (result1, result2)

    
class FinanceUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="TABLE")
        self.setWindowTitle("Financials Analyzerr")

        self.bottomArea.create_input_tab("CSV")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.all_input_tabs, 
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        findOutlier = FindOutlier(self.sentralControl)
        self.all_predicates.addPredicate("find outlier based on mean/std-dev", findOutlier)

        predict = PredictNextMonths(self.sentralControl)
        self.all_predicates.addPredicate("predict next months based on linear regression", predict)

        extract = ExtractColumnsRows(self.sentralControl)
        self.all_predicates.addPredicate("extract data where specified column contains a string or name", extract)

        worldMapObj = CreateWorldMap(self.sentralControl)
        self.all_predicates.addPredicate("create world map", worldMapObj)


if __name__ == "__main__":
    run_BluePayload(FinanceUI)


