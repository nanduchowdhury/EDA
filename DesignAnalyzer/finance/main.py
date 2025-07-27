
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
    def __init__(self, inputTab, sentralControl):
        super().__init__("Load data")

        self.inputTab = inputTab
        self.sentralControl = sentralControl

    def onClick(self):

        csvList = self.inputTab.getAllItemsInList("Files", "CSV")

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
            'column_name': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Label',
                'example': 'example : Region or City'
            }
        }

    def run(self):

        column_name = self.args['column_name']['user_value']

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
            'column_name': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Label',
                'example': 'example : Date or Category'
            },
            'num_months': {
                'user_value': 2,
                'default': 2,
                'tool_tip': 'Number of months to predict',
                'example': 'example : 3'
            }
        }

    def run(self):
        result = []
        column_name = self.args['column_name']['user_value']
        num_months = self.args['num_months']['user_value']

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

class HighlightTableColumnDataConditional(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'column_name': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Label',
                'example': 'example : Date or Category'
            },
            'python_syntax_condition': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Python syntax condition for highlighting',
                'example': 'example : x > 800 & x < 900    x == \'Orchid\''
            }
        }

    def run(self):
        
        column_name = self.args['column_name']['user_value']
        python_syntax_condition = self.args['python_syntax_condition']['user_value']

        # df_list = self.sentralControl.getDataForSelectedEntity()
        # df = df_list[0]
        
        result = []

        table = self.sentralControl.getSelectedTable()
        h_vals = table.hilightColumnData(column_name, python_syntax_condition)

        return result

class TableAlternateRowsColor(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'color': {
                'user_value': '',
                'default': 'light green',
                'tool_tip': 'Color for alternate rows',
                'example': 'example : light blue'
            }
        }

    def run(self):

        color = self.args['color']['user_value']

        result = []

        table = self.sentralControl.getSelectedTable()
        table.colorAlternateRows(color)

        return result


class TableApplyColumnColorGradient(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'column_name': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to apply gradient',
                'example': 'example : Sales'
            },
            'low_color': {
                'user_value': '',
                'default': 'green',
                'tool_tip': 'Low color for gradient',
                'example': 'example : green'
            },
            'high_color': {
                'user_value': '',
                'default': 'red',
                'tool_tip': 'High color for gradient',
                'example': 'example : red'
            }
        }

    def run(self):

        column_name = self.args['column_name']['user_value']
        low_color = self.args['low_color']['user_value']
        high_color = self.args['high_color']['user_value']

        result = []

        table = self.sentralControl.getSelectedTable()
        table.applyColumnColorGradient(column_name, low_color, high_color)

        return result



class FormatTable(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'font': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Font type for the table',
                'example': 'example : Arial'
            },
            'grid': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Grid style for the table',
                'example': 'example : vertical or horizontal'
            },
            'alignment': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Text alignment in the table',
                'example': 'example : center or left or right'
            },
            'textColor': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Text color in the table',
                'example': 'example : red'
            },
            'textSize': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Text size in the table',
                'example': 'example : 12'
            }
        }

    def run(self):
        
        font = self.cleanArg(self.args['font']['user_value'])
        grid = self.cleanArg(self.args['grid']['user_value'])
        alignment = self.cleanArg(self.args['alignment']['user_value'])
        textColor = self.cleanArg(self.args['textColor']['user_value'])
        textSize = self.cleanArg(self.args['textSize']['user_value'])

        # df_list = self.sentralControl.getDataForSelectedEntity()
        # df = df_list[0]
        
        result = []

        table = self.sentralControl.getSelectedTable()

        table.setDataFormat(
            font=font,
            grid=grid,
            alignment=alignment,
            textColor=textColor,
            textSize=textSize
        )

        return result
        

class FindOutlier(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.args = {
            'column_name': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Label',
                'example': 'example : Date or Category'
            },
            'z-value': {
                'user_value': '',
                'default': 0.9,
                'tool_tip': 'Z-value for outlier detection',
                'example': 'example : 0.9 1.9'
            }
        }

    def run(self):
        result = []
        column_name = self.args['column_name']['user_value']
        z_val = self.args['z-value']['user_value']

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

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.inputTab,
                                                    self.sentralControl)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        findOutlier = FindOutlier(self.sentralControl)
        self.all_predicates.addPredicate("financial analysis", "find outlier based on mean/std-dev", findOutlier)

        predict = PredictNextMonths(self.sentralControl)
        self.all_predicates.addPredicate("financial analysis", "predict next months based on linear regression", predict)

        highlight = HighlightTableColumnDataConditional(self.sentralControl)
        self.all_predicates.addPredicate("table formatting", "highlight table column data based on python syntax condition", highlight)

        formatTable = FormatTable(self.sentralControl)
        self.all_predicates.addPredicate("table formatting", "format table", formatTable)

        applyColumnColorGradient = TableApplyColumnColorGradient(self.sentralControl)
        self.all_predicates.addPredicate("table formatting", "apply column color gradient", applyColumnColorGradient)

        alternateRows = TableAlternateRowsColor(self.sentralControl)
        self.all_predicates.addPredicate("table formatting", "color alternate rows", alternateRows)


        worldMapObj = CreateWorldMap(self.sentralControl)
        self.all_predicates.addPredicate("world map analysis", "create world map", worldMapObj)


if __name__ == "__main__":
    run_BluePayload(FinanceUI)


