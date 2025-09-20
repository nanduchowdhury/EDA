
from PySide6.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont
from PySide6.QtCore import Qt

import sys
import os

import re

# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from viewer_manager import ResultsTableWithFilter, PandasTableModel

from predicates import Predicates, PredicateBase

from global_name_index import gname_index

from design_data import DesignData

from draw_manager import DrawManager

from def_parser import DefParserImplement
from lef_parser import LefParserImplement


class LefDefPandasTableModel(PandasTableModel):
    def __init__(self, df=None):
        super().__init__(df)


    def data(self, index, role=Qt.ItemDataRole.DisplayRole):

        if not index.isValid() or self._df is None:
            return None

        row, col = index.row(), index.column()
        col_name = self._df.columns[col]

        # Call parent data() first
        base_result = super().data(index, role)

        ##############################################
        # Do something extra on data here.
        ##############################################

        return base_result
    

class LefDefTableWithFilter(ResultsTableWithFilter):
    def __init__(self, parent=None):
        super().__init__(LefDefPandasTableModel(), parent)

    


class LefDefPredicate(PredicateBase):
    def __init__(self, _design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__()

        self.design_data = _design_data
        self.defParserImplement = _defParserImplement
        self.lefParserImplement = _lefParserImplement
        self.drawManager = _drawManager
        self.sentralControl = _sentralControl

        self.tableWithFilter = LefDefTableWithFilter()


class GetLefLayers(LefDefPredicate):
    def __init__(self, _design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.args = {
            'metal or via': {
                'user_value': '',
                'default': '',
                'tool_tip': 'Layers present in LEF',
                'example': 'example : metal or via'
            }

        }

    def run(self):
        metal_or_via = self.args['metal or via']['user_value']

        layers = self.lefParserImplement.get_layers(metal_or_via)


        self.setOutputObject("name", [gname_index.getName(l.name_id) for l in layers])
        self.setOutputObject("type", [l.type for l in layers])
        self.setOutputObject("pitch", [l.pitch for l in layers])
        self.setOutputObject("width", [l.width for l in layers])
        self.setOutputObject("minwidth", [l.minwidth for l in layers])
        self.setOutputObject("maxwidth", [l.maxwidth for l in layers])

        return True


class GetLefVias(LefDefPredicate):
    def __init__(self, _design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.args = {
            
        }

    def run(self):

        vias = self.lefParserImplement.get_vias()


        self.setOutputObject("name", [gname_index.getName(v.name_id) for v in vias])
        self.setOutputObject("generated", [v.generated for v in vias])

        return True
    
class GetLefMacros(LefDefPredicate):
    def __init__(self, _design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.args = {
            
        }

    def run(self):

        macros = self.lefParserImplement.get_macros()

        self.setOutputObject("name", [gname_index.getName(m.name_id) for m in macros])
        self.setOutputObject("class type", [m.class_type for m in macros])
        self.setOutputObject("size", [m.size for m in macros])

        return True


class ListVias(LefDefPredicate):
    def __init__(self, _design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

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

        return "success"



class SelectObjects(LefDefPredicate):
    def __init__(self, _design_data,
                 _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.arg_inst_name = "instance name"
        self.arg_cell_name = "cell name"

        self.args = {
            self.arg_inst_name: {
                'user_value': '',
                'default': '',
                'tool_tip': 'Name of the instance to search for',
                'example': 'example : ^I0.*'
            },
            self.arg_cell_name: {
                'user_value': '',
                'default': '',
                'tool_tip': 'Name of the cell to search for',
                'example': 'example : ^BUFF.*'
            }
        }


    def run(self):

        inst_regex = self.args[self.arg_inst_name]["user_value"]
        cell_regex = self.args[self.arg_cell_name]["user_value"]

        ids = self.design_data.get_inst_ids_by_regex(inst_regex=inst_regex, cell_regex=cell_regex)
        self.drawManager.select_unselect_draw_inst_ids(id_list=ids, do_what="SELECT")

        return True
    

class ClearSelection(LefDefPredicate):
    def __init__(self, _design_data,
                 _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.args = {
            
        }

    def run(self):

        self.drawManager.clear_selection()

        return True
    

class ZoomObjects(LefDefPredicate):
    def __init__(self, _design_data,
                 _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.arg_inst_name = "instance name"
        self.arg_cell_name = "cell name"

        self.args = {
            self.arg_inst_name: {
                'user_value': '',
                'default': '',
                'tool_tip': 'Name of the instance to search for',
                'example': 'example : ^I0.*'
            },
            self.arg_cell_name: {
                'user_value': '',
                'default': '',
                'tool_tip': 'Name of the cell to search for',
                'example': 'example : ^BUFF.*'
            }
        }


    def run(self):

        inst_regex = self.args[self.arg_inst_name]["user_value"]
        cell_regex = self.args[self.arg_cell_name]["user_value"]

        ids = self.design_data.get_inst_ids_by_regex(inst_regex=inst_regex, cell_regex=cell_regex)
        self.drawManager.select_unselect_draw_inst_ids(id_list=ids, do_what="SELECT")
        self.drawManager.zoom_instances(ids)

        return True



class ListInstances(LefDefPredicate):
    def __init__(self, _design_data,
                 _defParserImplement, _lefParserImplement, _drawManager, _sentralControl):
        super().__init__(_design_data, _defParserImplement, _lefParserImplement, _drawManager, _sentralControl)

        self.arg_inst_name = "instance name"
        self.arg_cell_name = "cell name"

        self.args = {
            self.arg_inst_name: {
                'user_value': '',
                'default': '',
                'tool_tip': 'Name of the instance to search for',
                'example': 'example : ^I0.*'
            },
            self.arg_cell_name: {
                'user_value': '',
                'default': '',
                'tool_tip': 'Name of the cell to search for',
                'example': 'example : ^BUFF.*'
            }
        }


    def run(self):

        inst_regex = self.args[self.arg_inst_name]["user_value"]
        cell_regex = self.args[self.arg_cell_name]["user_value"]

        ids = self.design_data.get_inst_ids_by_regex(inst_regex=inst_regex, cell_regex=cell_regex)
        df = self.design_data.get_inst_df(ids)

        for col_name in df.columns:
            self.setOutputObject(col_name, df[col_name].tolist())

        return True
    
    def onPostRun(self):

        table = self.sentralControl.resultsManager.getResultsTable(self.getShortName())
        table.registerOnItemClickCallback(self.onCellClicked)
        table.registerOnItemSelectedCallback(self.onCellClicked)

    def onCellClicked(self, data_dict):

        print("🟢 Cell clicked:")

        for column, values in data_dict.items():
            ids = self.design_data.get_inst_ids_by_name(name_list=values)
            self.drawManager.select_unselect_draw_inst_ids(id_list=ids, do_what="SELECT")



class LoadDesignToolItem(ToolBarItemAbstract):
    def __init__(self, inputTab, design_data,
                    defParserImplement, lefParserImplement, _sentralControl,
                    drawManager):
        super().__init__("Load Design")

        self.inputTab = inputTab

        self.design_data = design_data

        self.lefParserImplement = lefParserImplement
        self.defParserImplement = defParserImplement

        self.sentralControl = _sentralControl
        self.drawManager = drawManager

    def onClick(self):
        self.loadLefDef()
        
        
    def loadLefDef(self):

        lefList = self.inputTab.getAllItemsInList("Files", "LEF")
        defList = self.inputTab.getAllItemsInList("Files", "DEF")

        for l in lefList:
            print(f"Loading LEF file: {l}")
            self.lefParserImplement.parse(l)
            self.sentralControl.addEntryForFile(l)

        for d in defList:
            print(f"Loading DEF file: {d}")
            self.defParserImplement.parse(d)

        self.defParserImplement.def_parser_finished_signal.connect(self.slotDefParserFinished)

    def slotDefParserFinished(self, message):

        self.design_data.resolveCompToInst()

        bbox = self.defParserImplement.get_diearea()

        if bbox is None:
            self.sentralControl.showMessage("No die area found in DEF file.")
            return

        self.drawManager.set_scale(bbox)

        self.design_data.assign_layer_colors()

        ids = self.design_data.get_inst_ids_by_bbox(bbox=bbox)
        self.drawManager.select_unselect_draw_inst_ids(id_list=ids, do_what="DRAW")

        self.drawManager.draw_nets()
        

class LefDefUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="DRAW")
        
        self.setWindowTitle("Post-layout Analyzerr")

        self.bottomArea.create_input_tab("LEF")
        self.bottomArea.create_input_tab("DEF")

        self.lefParserImplement = LefParserImplement()
        self.defParserImplement = DefParserImplement(self.lefParserImplement)
        

        self.design_data = DesignData(self.lefParserImplement, self.defParserImplement)

        self.drawManager = DrawManager(self.drawArea, self.design_data)


        self.loadDesignToolbarItem = LoadDesignToolItem(self.bottomArea.inputTab,
                                                        self.design_data,
                                self.defParserImplement, self.lefParserImplement,
                                self.sentralControl,
                                self.drawManager)
        
        self.menu.createToolbarItem(self.loadDesignToolbarItem)
        
        self.registerLefDefPredicates()
        

    def registerLefDefPredicates(self):

        listVias = ListVias(self.design_data,
                                 self.defParserImplement, self.lefParserImplement, self.drawManager,
                                 self.sentralControl)
        self.all_predicates.addPredicate("design analysis", "list vias", listVias)

        listInstances = ListInstances(self.design_data,
                                    self.defParserImplement, self.lefParserImplement, self.drawManager,
                                    self.sentralControl)
        self.all_predicates.addPredicate("design analysis", "list instances", listInstances)

        selectUnselectObj = SelectObjects(self.design_data,
                                                  self.defParserImplement, self.lefParserImplement, self.drawManager,
                                                  self.sentralControl)
        self.all_predicates.addPredicate("design analysis", "select objects", selectUnselectObj)

        clearSelectionObj = ClearSelection(self.design_data,
                                           self.defParserImplement, self.lefParserImplement, self.drawManager,
                                           self.sentralControl)
        self.all_predicates.addPredicate("design analysis", "clear selection", clearSelectionObj)

        zoomObj = ZoomObjects(self.design_data,
                              self.defParserImplement, self.lefParserImplement, self.drawManager,
                              self.sentralControl)
        self.all_predicates.addPredicate("design analysis", "zoom objects", zoomObj)

        layersObj = GetLefLayers(self.design_data,
                                 self.defParserImplement, self.lefParserImplement, self.drawManager,
                                 self.sentralControl)
        self.all_predicates.addPredicate("LEF analysis", "list layers", layersObj)

        viasObj = GetLefVias(self.design_data,
                                          self.defParserImplement, self.lefParserImplement, self.drawManager,
                                          self.sentralControl)
        self.all_predicates.addPredicate("LEF analysis", "list vias", viasObj)

        macrosObj = GetLefMacros(self.design_data,
                                 self.defParserImplement, self.lefParserImplement, self.drawManager,
                                 self.sentralControl)
        self.all_predicates.addPredicate("LEF analysis", "list macros", macrosObj)

if __name__ == "__main__":
    run_BluePayload(LefDefUI)

