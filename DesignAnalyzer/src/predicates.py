from abc import ABC, abstractmethod

import json

from design_data import DesignData

class PredicateBase(ABC):
    def __init__(self, _defParserImplement, _lefParserImplement):
        self.defParserImplement = _defParserImplement
        self.lefParserImplement = _lefParserImplement

        self.args = {}            # input arguments
        self.outputs = {}         # output data

    def setArg(self, name, value):
        self.args[name] = value

    def setArgs(self, args_dict):
        self.args.update(args_dict)

    def setOutput(self, argName, valueList):
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


class MultiplyTwoNumbers(PredicateBase):
    def run(self):
        a = int(self.args["a"])
        b = int(self.args["b"])
        print(f"Value a & b : {a} {b}")
        result = a * b
        self.setOutput("result", [result])  # Store result as a list

        return result
    
class GetViasForLayer(PredicateBase):

    def run(self):
        layerName = self.args['layer']

        result = self.defParserImplement.get_via_names(layerName)

        self.setOutput("result", result)  # Store result as a list
        return result

class GetInstanceCoords(PredicateBase):

    def run(self):

        # Experiment code.
        design_data = DesignData(self.defParserImplement, self.lefParserImplement)
        design_data.execute()

        
        # result = self.defParserImplement.get_instances_coords()
        # self.setOutput("inst", result["inst"])
        # self.setOutput("coords", result["coords"])
        
        result = design_data.instances
        instance_names = list(result.keys())
        bboxes = [data["bbox"] for data in result.values()]
        self.setOutput("inst", instance_names)
        self.setOutput("coords", bboxes)
        
        return result
    