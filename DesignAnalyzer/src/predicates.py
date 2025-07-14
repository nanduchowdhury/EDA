from abc import ABC, abstractmethod

import json
import re

import logging

from global_name_index import gname_index
from llm_manager import LLMManager, global_LLM_manager

from abc import ABC, abstractmethod

import pandas as pd

from layout_plot import BarChartView

class PredicateBase(ABC):
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
        predicate_name arg1 val1 arg2 val2 ...
        """
        parts = [self.predicate_name]
        for k, v in self.args.items():
            parts.append(f"{k} {v}")
        return " ".join(parts)

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

    @abstractmethod
    def run(self):
        """Override this method in subclasses."""
        pass



class Predicates:
    def __init__(self):
        self.predicates = {}  # name -> (arg_list, predicate_object)

    def addPredicate(self, name, list_of_args, predicateObj):
        """
        Adds a predicate.
        name: str
        list_of_args: list like ['arg1', 'arg2']
        predicateObj: instance of a class derived from PredicateBase
        """
        predicateObj.setPredicateName(name)
        self.predicates[name] = (list_of_args, predicateObj)

        global_LLM_manager.addCommandAndArgs(name, list_of_args)

    def executePredicate(self, name, *args):
        if name not in self.predicates:
            raise ValueError(f"Predicate '{name}' not found.")

        arg_names, predicate_obj = self.predicates[name]

        if len(args) != len(arg_names):
            raise ValueError(f"Expected {len(arg_names)} arguments, got {len(args)}")

        arg_dict = dict(zip(arg_names, args))
        predicate_obj.setArgs(arg_dict)

        return predicate_obj.run()

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
        return self.predicates[name][0]

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

        drawArea = self.sentralControl.viewerTabs.addTabByType("PLOT", "sample_plot")

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



