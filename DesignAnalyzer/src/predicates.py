from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

from abc import ABC, abstractmethod

import json
import re

from datetime import datetime
import logging

import sqlite3

from global_name_index import gname_index
from llm_manager import LLMManager, global_LLM_manager

from common import global_signals

from abc import ABC, abstractmethod

import pandas as pd

from layout_plot import BarChartView

from pca_analysis import DimensionalityReducer, KMeansClusterer

class PredicateBase():
    def __init__(self):
        self.predicate_name = ""  # Name of the predicate
        self.args = {}            # input arguments
        self.outputs = {}         # output data

        self.tableView = None

    def setPredicateName(self, name):
        self.predicate_name = name

    def setArg(self, name, value):
        self.args[name] = value

    def updateArgUserValue(self, arg_name, value):

        if arg_name not in self.args:
            raise ValueError(f"Argument '{arg_name}' not found in predicate '{self.predicate_name}'.")
        else:
            self.args[arg_name]['user_value'] = value

    def dump_args(self):
        """
        Returns a JSON string of the args dictionary.
        """
        return json.dumps(self.args, indent=4)

    def setUserValueArgs(self, args_dict):
        """
        Update only the 'user_value' fields in self.args
        for keys present in args_dict. Avoid nesting.
        """
        for key, value in args_dict.items():
            if key in self.args and isinstance(self.args[key], dict):
                # If value itself is a dict, extract its 'user_value' if exists
                if isinstance(value, dict) and 'user_value' in value:
                    self.args[key]['user_value'] = value['user_value']
                else:
                    self.args[key]['user_value'] = value



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
        timestamp = datetime.now().strftime('%d%b_%H%M%S')  # e.g., 05Jul_172302
    
        short_pred = self.predicate_name[:max_pred_len]
        val_parts = []
        for val in self.args.values():
            val_str = str(val)
            if len(val_str) > max_val_len:
                val_str = val_str[:max_val_len]
            val_parts.append(val_str)

        return f"{timestamp}_{short_pred}_{'_'.join(val_parts)}..."

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
        self.predicates = {}  # group_name -> {predicate_name -> predicate_object}
        self._hidden_groups = {}  # group_name -> True/False

    def setGroupHidden(self, group_name, hidden: bool):
        self._hidden_groups[group_name] = bool(hidden)

    def isGroupHidden(self, group_name):
        return self._hidden_groups.get(group_name, False)
    
    def addPredicate(self, group_name, name, predicateObj):
        """
        Add a predicate to a specified group.
        """
        predicateObj.setPredicateName(name)

        if group_name not in self.predicates:
            self.predicates[group_name] = {}

        self.predicates[group_name][name] = predicateObj

        global_LLM_manager.addCommandAndArgs(name, predicateObj.getArgs())

    def removePredicate(self, name):
        """
        Remove predicate by name from any group.
        """
        for group in self.predicates:
            if name in self.predicates[group]:
                del self.predicates[group][name]
                # Clean up group if empty
                if not self.predicates[group]:
                    del self.predicates[group]
                return
        raise ValueError(f"Remove predicate: '{name}' not found.")

    def getNumPredicates(self):
        return sum(len(preds) for preds in self.predicates.values())

    def getPredicateArgs(self, name):
        for group_preds in self.predicates.values():
            if name in group_preds:
                return group_preds[name].getArgs()
        raise ValueError(f"Predicate '{name}' not found.")

    def getAllGroupPredicates(self, group_name):
        """
        Returns dict: {predicate_name: predicate_object} for a specific group.
        """
        if group_name not in self.predicates:
            return {}
        return self.predicates[group_name].copy()

    def getAllGroups(self):
        """
        Returns a list of all group names.
        """
        return list(self.predicates.keys())

    def getPredicateObj(self, predicate_name):
        """
        Returns the predicate object corresponding to the given name.
        """
        for group_preds in self.predicates.values():
            if predicate_name in group_preds:
                return group_preds[predicate_name]
        raise ValueError(f"Predicate '{predicate_name}' not found.")


    def __iter__(self):
        """
        Allows iteration over all (name, predicate_obj) pairs across all groups.
        """
        for group_preds in self.predicates.values():
            for name, obj in group_preds.items():
                yield name, obj


class CreateBarChart(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.x_axis = None
        self.y_axis = None

        self.args = {
            'x_axis': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the X-axis',
                'example': 'example : Date or Category'
            },
            'y_axis': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Y-axis',
                'example': 'example : Sales or Profit'
            },
        }

    def run(self):

        self.x_axis = self.args['x_axis']['user_value']
        self.y_axis = self.args['y_axis']['user_value']

        drawArea = self.sentralControl.viewerTabs.addTabByType("BAR_CHART", 
                                    self.getShortName(),
                                    self.getCompleteNameWithArgs())

        df_list = self.sentralControl.getDataForSelectedEntity()

        df = df_list[0]

        drawArea.setXYColumn(self.x_axis, self.y_axis)
        drawArea.setDataFrame(df)

        drawArea.registerActionOnShowInTable(self.highlightInTable)

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



class CreateScatterPlot(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.x_axis = None
        self.y_axis = None

        self.args = {
            'x_axis': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the X-axis',
                'example': 'example : Date or Category'
            },
            'y_axis': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Y-axis',
                'example': 'example : Sales or Profit'
            },
        }

    def run(self):

        self.x_axis = self.args['x_axis']['user_value']
        self.y_axis = self.args['y_axis']['user_value']

        drawArea = self.sentralControl.viewerTabs.addTabByType("SCATTER_PLOT", 
                                    self.getShortName(),
                                    self.getCompleteNameWithArgs())

        df_list = self.sentralControl.getDataForSelectedEntity()

        df = df_list[0]

        drawArea.setXYColumn(self.x_axis, self.y_axis)
        drawArea.setDataFrame(df)

        # drawArea.registerActionOnShowInTable(self.highlightInTable)

        return True
    



class CreatePieChart(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.label_column = None
        self.value_column = None

        self.args = {
            'label_column': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Label',
                'example': 'example : Date or Category'
            },
            'value_column': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Column to be used for the Value',
                'example': 'example : Sales or Profit'
            }
        }

    def run(self):

        self.label_column = self.args['label_column']['user_value']
        self.value_column = self.args['value_column']['user_value']

        drawArea = self.sentralControl.viewerTabs.addTabByType("PIE_CHART", 
                                    self.getShortName(),
                                    self.getCompleteNameWithArgs())

        df_list = self.sentralControl.getDataForSelectedEntity()

        df = df_list[0]

        drawArea.setLabelAndValue(self.label_column, self.value_column)
        drawArea.setDataFrame(df)
        drawArea.showGrid(True)

        return True
    


class RunPCA(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.label_column = None
        self.value_column = None

        self.args = {
            'column list': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Columns to be used for PCA',
                'example': 'example : Column1, Column2, Column3'
            }
        }

    def run(self):

        # Split by "," and strip whitespace
        column_list = self.args['column list']['user_value'].split(',')
        column_list = [col.strip() for col in column_list if col.strip()]

        if not column_list:
            raise ValueError("No columns provided for PCA analysis.")

        print(f"Running PCA on columns: {column_list}")

        result = []

        df_list = self.sentralControl.getDataForSelectedEntity()

        if not df_list or len(df_list) == 0:
            raise ValueError("No data available for PCA analysis.")

        df = df_list[0]

        reducer = DimensionalityReducer(df, column_list)
        reducer.run_pca(n_components=2)
        result = reducer.get_pca_output()

        for col_name in result.columns:
            self.setOutputObject(col_name, result[col_name].tolist())
            
        return result



class RunKMeans(PredicateBase):
    def __init__(self, sentralControl):
        super().__init__()
        self.sentralControl = sentralControl

        self.label_column = None
        self.value_column = None

        self.args = {
            'column list': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Columns to be used for PCA',
                'example': 'example : Column1, Column2, Column3'
            },
            'number of clusters': {
                'user_value': '',
                'default': '3',
                'tool_tip': 'Number of clusters for K-means',
                'example': 'example : 4'
            }
        }

    def run(self):

        num_clusters = self.cleanArg(self.args['number of clusters']['user_value'])
        if num_clusters and not num_clusters.isdigit():
            raise ValueError("Number of clusters must be a positive integer.")
        if not num_clusters:
            num_clusters = self.args['number of clusters']['default']
        num_clusters = int(num_clusters)

        # Split by "," and strip whitespace
        column_list = self.args['column list']['user_value'].split(',')
        column_list = [col.strip() for col in column_list if col.strip()]

        if not column_list:
            raise ValueError("No columns provided for K-means analysis.")

        result = []

        # Get the table for which k-means need to run.
        df_list = self.sentralControl.getDataForSelectedEntity()

        if not df_list or len(df_list) == 0:
            raise ValueError("No data available for K-means analysis.")
        df = df_list[0]

        # Run k-means clustering
        clusterer = KMeansClusterer(df, column_list)
        result = clusterer.run_kmeans(n_clusters=num_clusters)

        result = clusterer.assign_cluster_colors(result)
        # result = clusterer.get_cluster_labels()

        # Show the k-means new table to user
        for col_name in result.columns:
            self.setOutputObject(col_name, result[col_name].tolist())


        # Run scatter plot to visualize the clusters
        if column_list and len(column_list) == 2:
            drawArea = self.sentralControl.viewerTabs.addTabByType("SCATTER_PLOT", 
                                        self.getShortName(),
                                        self.getCompleteNameWithArgs())

            drawArea.setXYColumn(column_list[0], column_list[1])
            drawArea.setColorColumn("Color")
            drawArea.setDataFrame(result)
            
        else:
            self.sentralControl.showMessage("K-means clustering scatter-plot requires exactly 2 columns for visualization.")

        return result




class SqlQueryPredicate(PredicateBase, QObject):
    def __init__(self, sentralControl):
        super().__init__()
        QObject.__init__(self)

        self.sentralControl = sentralControl

        self.args = {
            'sql_query': {
                'user_value': '',
                'default': '',
                'tool_tip': 'SQL query to be executed',
                'example': 'example : SELECT * FROM table WHERE <column_name> LIKE \'I2%\''
            }
        }

    def run(self):
        
        df_list = self.sentralControl.getDataForSelectedEntity()
        df = df_list[0]
        
        result = []

        actual_query = self.args['sql_query']['user_value']

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




