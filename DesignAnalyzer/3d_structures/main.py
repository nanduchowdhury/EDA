
import sys
import os
import pdfplumber

import numpy as np

import logging
import math
import csv

from sklearn.linear_model import LinearRegression

# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI
from main_menu import MenuItemAbstract, ToolBarItemAbstract

from predicates import Predicates, PredicateBase

class LoadDataToolItem(ToolBarItemAbstract):
    def __init__(self, all_input_tabs, drawArea):
        super().__init__("Load data")

        self.all_input_tabs = all_input_tabs
        self.drawArea = drawArea

        self.source = None

    def onClick(self):

        logging.info("Loading STL data started.")

        stlList = self.all_input_tabs["STL"].getAllItemsInList()

        for stl_file in stlList:
            logging.info(f"Reading STL file: {stl_file}")
            self.source = self.drawArea.read_stl_ascii(stl_file)
            self.drawArea.init_vtk_scene(self.source)
            logging.info(f"STL file {stl_file} read successfully.")
        logging.info("Loading STL data done.")


class ComputePCA(PredicateBase):
    def __init__(self, loadDataObj, drawArea):
        super().__init__()

        self.loadDataObj = loadDataObj
        self.drawArea = drawArea

        self.args = {
        }

    def run(self):
        result = []

        r = self.drawArea.estimate_cylinder_parameters(self.loadDataObj.source)

        result.append(r)

        self.setOutputObject("result", result)  # Store result as a list
        logging.info(f"PCA computation done : result = {result}")

        return result

class FindVolume(PredicateBase):
    def __init__(self, loadDataObj):
        super().__init__()
        self.loadDataObj = loadDataObj

        self.args = {
            'radius': 0.9,
            'height': 0.9,
        }

    def run(self):
        result = []
        radius = int(self.args['radius'])
        height = int(self.args['height'])

        volume = math.pi * radius ** 2 * height
        result.append(volume)

        self.setOutputObject("result", result)  # Store result as a list
        logging.info(f"Volume computation done.")

        return result
    
class StructuresUI(MainUI):
    def __init__(self):
        super().__init__(PLOT_OR_DRAW="VTK")
        self.setWindowTitle("Structures Analyzerr")

        self.bottomArea.create_input_tab("STL")

        self.loadDataToolbarItem = LoadDataToolItem(self.bottomArea.all_input_tabs, 
                                                    self.drawArea)
        
        self.menu.createToolbarItem(self.loadDataToolbarItem)

        self.removeGenericPredicate()

        pca = ComputePCA(self.loadDataToolbarItem, self.drawArea)
        self.all_predicates.addPredicate("compute PCA - standard parameters", [], pca)

        findVolume = FindVolume(self.loadDataToolbarItem)
        self.all_predicates.addPredicate("volume - based on radius & height", ["radius", "height"], findVolume)





if __name__ == "__main__":
    run_BluePayload(StructuresUI)


