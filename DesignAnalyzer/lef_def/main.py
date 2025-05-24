import sys
import os

import re

# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from predicates import Predicates, PredicateBase

from global_name_index import gname_index

from design_data import DesignData

from def_parser import DefParserImplement
from lef_parser import LefParserImplement


class LefDefPredicate(PredicateBase):
    def __init__(self, _defParserImplement, _lefParserImplement, design_data):
        super().__init__()

        self.defParserImplement = _defParserImplement
        self.lefParserImplement = _lefParserImplement
        self.design_data = design_data


class GetViasForLayer(LefDefPredicate):
    def __init__(self, _defParserImplement, _lefParserImplement, design_data):
        super().__init__(_defParserImplement, _lefParserImplement, design_data)

        self.args = {
            'layer': None,  # Layer name to search for vias
        }

    def run(self):
        layerName = self.args['layer']

        result = self.defParserImplement.get_via_names(layerName)

        self.setOutputObject("result", result)  # Store result as a list
        return result

class GetInstanceCoords(LefDefPredicate):
    def __init__(self, _defParserImplement, _lefParserImplement, design_data):
        super().__init__(_defParserImplement, _lefParserImplement, design_data)

        self.args = {
            'name': None,  # Regular expression to match instance names
        }

        # Ensure the design data is resolved before running this predicate
        self.design_data.resolveCompToInst()

    def run(self):
        name_regex = self.args["name"]

        # all_inst = list(self.design_data.instData.instance_data)
    
        result = []
        compiled_regex = re.compile(name_regex)
        components = self.defParserImplement.get_components()
        for comp in components:
            instance_name = gname_index.getName(comp.inst_name_id)
            if compiled_regex.search(instance_name):
                result.append(comp.inst_name_id)

        self.setOutputObject("inst", result)
        
        return result
    


class LoadDesignToolItem(ToolBarItemAbstract):
    def __init__(self, all_input_tabs,
                    defParserImplement, lefParserImplement, designData,
                    drawManager):
        super().__init__("Load Design")

        self.all_input_tabs = all_input_tabs

        self.lefListWidget = self.all_input_tabs["LEF"].get_file_list_widget()
        self.defListWidget = self.all_input_tabs["DEF"].get_file_list_widget()

        self.lefParserImplement = lefParserImplement
        self.defParserImplement = defParserImplement

        self.design_data = designData
        self.drawManager = drawManager

    def onClick(self):
        self.loadLefDef()
        
        
    def loadLefDef(self):

        lef_list = [self.lefListWidget.item(i).text() for i in range(self.lefListWidget.count())]
        def_list = [self.defListWidget.item(i).text() for i in range(self.defListWidget.count())]

        for l in lef_list:
            self.lefParserImplement.parse(l)

        for d in def_list:
            self.defParserImplement.parse(d)

        self.defParserImplement.def_parser_finished_signal.connect(self.slotDefParserFinished)

    def slotDefParserFinished(self, message):
        self.design_data.resolveCompToInst()
        
        self.drawManager.set_scale(self.design_data.inst_bbox)
        self.drawManager.load_design_instances(self.design_data.inst_rtree, 
                            self.design_data.instData)
        

class LefDefUI(MainUI):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LefDef UI")


        self.bottomArea.create_input_tab("LEF")
        self.bottomArea.create_input_tab("DEF")

        self.defParserImplement = DefParserImplement()
        self.lefParserImplement = LefParserImplement()

        self.design_data = DesignData(self.lefParserImplement, self.defParserImplement)

        self.loadDesignToolbarItem = LoadDesignToolItem(self.bottomArea.all_input_tabs,
                                self.defParserImplement, self.lefParserImplement,
                                self.design_data,
                                self.drawManager)
        
        self.menu.createToolbarItem(self.loadDesignToolbarItem)
        
        self.registerLefDefPredicates()
        

    def registerLefDefPredicates(self):

        viaObj = GetViasForLayer(self.defParserImplement, self.lefParserImplement,
                                 self.design_data)
        self.all_predicates.addPredicate("via - search based on layer etc", ["layer"], viaObj)

        instObj = GetInstanceCoords(self.defParserImplement, self.lefParserImplement,
                                    self.design_data)
        self.all_predicates.addPredicate("instances - search by name regexp, location etc", ["name"], instObj)



if __name__ == "__main__":
    run_BluePayload(LefDefUI)

