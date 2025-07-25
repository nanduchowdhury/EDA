
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

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

from draw_manager import DrawManager

from def_parser import DefParserImplement
from lef_parser import LefParserImplement


class LefDefPredicate(PredicateBase):
    def __init__(self, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__()

        self.defParserImplement = _defParserImplement
        self.lefParserImplement = _lefParserImplement
        self.drawManager = _drawManager
        self.sentralControl = _sentralControl


class GetViasForLayer(LefDefPredicate):
    def __init__(self, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.args = {
            'layer': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Layer name to search for vias',
                'example': 'example : VIA1'
            }
        }

    def run(self):
        layerName = self.args['layer']['user_value']

        result = self.defParserImplement.get_via_names(layerName)

        for key, values in result.items():
            self.setOutputObject(key, values)

        return result

class GetInstanceCoords(LefDefPredicate):
    def __init__(self, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.args = {
            'instance_name': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Name of the instance to search for',
                'example': 'example : U1*'
            }
        }


    def run(self):
        name_regex = self.args["instance_name"]["user_value"]

        # all_inst = list(design_data.instData.instance_data)
    
        result = self.defParserImplement.get_components_by_name(name_regex)

        self.setOutputObject("name", result)
        
        return result
    
    def onPostRun(self):

        table = self.sentralControl.resultsManager.getResultsTable(self.getShortName())
        table.registerOnItemClickCallback(self.onCellClicked)
        table.registerOnItemSelectedCallback(self.onCellClicked)

    def onCellClicked(self, data_dict):

        print("🟢 Cell clicked:")

        for column, values in data_dict.items():
            self.drawManager.draw_instances(values, QColor("white"))



class LoadDesignToolItem(ToolBarItemAbstract):
    def __init__(self, all_input_tabs,
                    defParserImplement, lefParserImplement, _sentralControl,
                    drawManager):
        super().__init__("Load Design")

        self.all_input_tabs = all_input_tabs

        self.lefParserImplement = lefParserImplement
        self.defParserImplement = defParserImplement

        self.sentralControl = _sentralControl
        self.drawManager = drawManager

    def onClick(self):
        self.loadLefDef()
        
        
    def loadLefDef(self):

        lefList = self.all_input_tabs["LEF"].getAllItemsInList()
        defList = self.all_input_tabs["DEF"].getAllItemsInList()

        for l in lefList:
            print(f"Loading LEF file: {l}")
            self.lefParserImplement.parse(l)
            self.sentralControl.addEntryForFile(l)

        for d in defList:
            print(f"Loading DEF file: {d}")
            self.defParserImplement.parse(d)

        self.defParserImplement.def_parser_finished_signal.connect(self.slotDefParserFinished)

    def slotDefParserFinished(self, message):

        design_data = DesignData(self.lefParserImplement, self.defParserImplement)

        design_data.resolveCompToInst()
        
        self.drawManager.load_design_instances(design_data.inst_rtree, 
                            design_data.instData)
        

class LefDefUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="DRAW")
        
        self.setWindowTitle("Post-layout Analyzerr")

        self.drawManager = DrawManager(self.drawArea)

        self.bottomArea.create_input_tab("LEF")
        self.bottomArea.create_input_tab("DEF")

        self.defParserImplement = DefParserImplement()
        self.lefParserImplement = LefParserImplement()

        self.loadDesignToolbarItem = LoadDesignToolItem(self.bottomArea.all_input_tabs,
                                self.defParserImplement, self.lefParserImplement,
                                self.sentralControl,
                                self.drawManager)
        
        self.menu.createToolbarItem(self.loadDesignToolbarItem)
        
        self.registerLefDefPredicates()
        

    def registerLefDefPredicates(self):

        viaObj = GetViasForLayer(self.defParserImplement, self.lefParserImplement, self.drawManager,
                                 self.sentralControl)
        self.all_predicates.addPredicate("design analysis", "search vias based on layer etc", viaObj)

        instObj = GetInstanceCoords(self.defParserImplement, self.lefParserImplement, self.drawManager,
                                    self.sentralControl)
        self.all_predicates.addPredicate("design analysis", "search instances by name regexp, location etc", instObj)



if __name__ == "__main__":
    run_BluePayload(LefDefUI)

