from abc import ABC, abstractmethod

import json
import re

import logging

from global_name_index import gname_index
from llm_manager import LLMManager, global_LLM_manager

class PredicateBase(ABC):
    def __init__(self):

        self.args = {}            # input arguments
        self.outputs = {}         # output data

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
        self.predicates[name] = (list_of_args, predicateObj)

        global_LLM_manager.set_context_line(name)

    def executePredicate(self, name, *args):
        if name not in self.predicates:
            raise ValueError(f"Predicate '{name}' not found.")

        arg_names, predicate_obj = self.predicates[name]

        if len(args) != len(arg_names):
            raise ValueError(f"Expected {len(arg_names)} arguments, got {len(args)}")

        arg_dict = dict(zip(arg_names, args))
        predicate_obj.setArgs(arg_dict)

        return predicate_obj.run()

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


class DummyPredicate(PredicateBase):

    def run(self):
        # Dummy implementation
        logging.info("Dummy predicate cannot be run - implement predicates and register from your application.")
        return True

