from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

from abc import ABC, abstractmethod

import json
import re

import logging

import sqlite3

from global_name_index import gname_index
from llm_manager import LLMManager, global_LLM_manager

from common import global_signals

from abc import ABC, abstractmethod

import pandas as pd

from layout_plot import BarChartView

class PredicateBase():
    def __init__(self):
        self.predicate_name = ""  # Name of the predicate
        self.args = {}            # input arguments
        self.outputs = {}         # output data

    def setPredicateName(self, name):
        self.predicate_name = name

    def setArg(self, name, value):
        self.args[name] = value

    def setArgs(self, args_dict):
        self.args.update(args_dict)

    def getArgs(self):
        return self.args

    def cleanArg(self, argName):
        if isinstance(argName, str) and argName.strip() == "":
            return None
        elif argName.lower() == "none":
            return None
        
        return argName

    def setOutputObject(self, argName, valueList):
        """Sets the output values for a given argument name."""
        if not isinstance(valueList, list):
            raise ValueError("Output value must be a list.")
        self.outputs[argName] = valueList

    def getNumOutputArgs(self):
        """Returns the number of output arguments set."""
        return len(self.outputs)

    def getArgOutput(self, argName):
        """Gets the list of output values for the given argument name."""
        return self.outputs.get(argName, [])

    def iterateOutputs(self):
        for name, values in self.outputs.items():
            yield name, values

    def getDataFrame(self) -> pd.DataFrame:
        """
        Returns the outputs as a pandas DataFrame.
        Each key in outputs becomes a column.
        """
        # Ensure all output lists are of the same length
        lengths = [len(v) for v in self.outputs.values()]
        if len(set(lengths)) > 1:
            raise ValueError("All output lists must be of the same length to form a DataFrame.")
        return pd.DataFrame(self.outputs)


    def getCompleteNameWithArgs(self):
        """
        Returns the full command string like:
        predicate_name
        <i><u>arg1</u></i>     <b>val1</b>
        <i><u>arg2</u></i>     <b>val2</b>
        ...
        """
        lines = [self.predicate_name]
        for k, v in self.args.items():
            lines.append(f"<i><u>{k}</u></i>&emsp;<b>{v}</b>")
        return "<br>".join(lines)


    def getShortName(self, max_pred_len=6, max_val_len=10):
        """
        Returns a short string like:
        pred_val1_val2...
        Truncates predicate name and values if needed.
        """
        short_pred = self.predicate_name[:max_pred_len]
        val_parts = []
        for val in self.args.values():
            val_str = str(val)
            if len(val_str) > max_val_len:
                val_str = val_str[:max_val_len]
            val_parts.append(val_str)
        return f"{short_pred}_{'_'.join(val_parts)}..."

    def onPostRun(self):
        pass

    def run(self):
        """Override this method in subclasses."""
        pass

    def execute(self):
        try:
            result = self.run()
            return result
        except Exception as e:
            self.sentralControl.showMessage(f"Error executing '{self.predicate_name}': {e}")


class Predicates:
    def __init__(self):
        self.predicates = {}  # name -> (arg_list, predicate_object)

    def addPredicate(self, name, predicateObj):

        predicateObj.setPredicateName(name)
        self.predicates[name] = predicateObj

        global_LLM_manager.addCommandAndArgs(name, predicateObj.getArgs())


    def removePredicate(self, name):
        if name in self.predicates:
            del self.predicates[name]
        else:
            raise ValueError(f"Remove predicate : '{name}' not found.")

    def getNumPredicates(self):
        return len(self.predicates)

    def getPredicateArgs(self, name):
        if name not in self.predicates:
            raise ValueError(f"Predicate '{name}' not found.")
        return self.predicates[name].getArgs()

    def getAllPredicates(self):
        """
        Returns a dictionary of all predicates: {name: (arg_list, predicate_object)}
        """
        return self.predicates.copy()

    def __iter__(self):
        """
        Allows: for name, (args, obj) in predicates_instance:
        """
        return iter(self.predicates.items())


class CreateBarChart(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.x_axis = None
        self.y_axis = None

        self.args = {
            'x_axis': "",
            'y_axis': "",
        }

    def run(self):

        self.x_axis = self.args['x_axis']
        self.y_axis = self.args['y_axis']

        drawArea = self.sentralControl.viewerTabs.addTabByType("BAR_CHART", 
                                    self.getShortName(),
                                    self.getCompleteNameWithArgs())

        df_list = self.sentralControl.getDataForSelectedEntity()

        df = df_list[0]

        drawArea.setXYColumn(self.x_axis, self.y_axis)
        drawArea.setDataFrame(df)

        drawArea.registerActionOnShowInTable(self.highlightInTable)
        # self.highlightInTable()

        # drawArea.plotBar(dataList, x_axis, y_axis)
        # drawArea.plotBar(dataList, "COUNTRY", "2026")
        # drawArea.plotPie(dataList)

        return True
    
    def highlightInTable(self, label):

        x, y = label.split(":")
        x = x.strip()
        y = y.strip()

        highlight_dict = {
            self.x_axis: [x],
            self.y_axis: [y]
        }

        input_table = self.sentralControl.viewerTabs.getInputTabWidget()
        input_table.highlightData(highlight_dict)


class CreatePieChart(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.label_column = None
        self.value_column = None

        self.args = {
            'label_column': "",
            'value_column': "",
        }

    def run(self):

        self.label_column = self.args['label_column']
        self.value_column = self.args['value_column']

        drawArea = self.sentralControl.viewerTabs.addTabByType("PIE_CHART", 
                                    self.getShortName(),
                                    self.getCompleteNameWithArgs())

        df_list = self.sentralControl.getDataForSelectedEntity()

        df = df_list[0]

        drawArea.setLabelAndValue(self.label_column, self.value_column)
        drawArea.setDataFrame(df)

        return True
    


class SqlQueryPredicate(PredicateBase, QObject):
    def __init__(self, sentralControl):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl

        self.args = {
            'actual_query': ""
        }

    def run(self):
        
        df_list = self.sentralControl.getDataForSelectedEntity()
        df = df_list[0]
        
        result = []

        actual_query = self.args['actual_query']

        print(f"Executing SQL query: {actual_query}")

        try:

            manager = SqlManager()
            manager.loadDataFrame(df)

            result = manager.executeSql(actual_query)

            if result.shape == (1, 1):
                global_signals.signal_update_sql_run_status.emit({
                    "status": "success",
                    "message": "The result is...",
                    "result": result.iloc[0, 0]
                })
            elif result.empty:
                global_signals.signal_update_sql_run_status.emit({
                    "status": "success",
                    "message": "No result found.",
                    "result": None
                })
            else:
                global_signals.signal_update_sql_run_status.emit({
                    "status": "success",
                    "message": "Check result tabs...",
                    "result": None
                })

                for col_name in result.columns:
                    self.setOutputObject(col_name, result[col_name].tolist())
            
            return result
        
        except Exception as e:

            self.sentralControl.showMessage(f"Execution error: {e}")

            global_signals.signal_update_sql_run_status.emit({
                "status": "error",
                "message": f"{str(e)}",
                "result": None
            })
            return None

        
    


class SqlManager():

    def __init__(self):

        self.conn = sqlite3.connect(":memory:")
        self.df = None
        self.table_name = "csv_data"

    def loadDataFrame(self, df: pd.DataFrame):
        self.df = df
        df.to_sql(self.table_name, self.conn, if_exists="replace", index=False)

    def executeSql(self, sql: str) -> pd.DataFrame:
        try:
            # Replace 'table' in sql with the actual table name
            sql = sql.replace("table", self.table_name)

            result_df = pd.read_sql_query(sql, self.conn)

            return result_df
        
        except Exception as e:
            raise ValueError(f"{e}")




