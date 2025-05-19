
import logging

from rtree import index

from global_name_index import gname_index

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

from sklearn.cluster import KMeans
import numpy as np
import random

from def_parser import DefParserImplement
from lef_parser import LefParserImplement

@dataclass
class Instance:
    cell_name_id: int
    type_id: int
    location: Tuple[int, int, int, int]

@dataclass
class InstanceMap:
    instance_data: Dict[int, Instance] = field(default_factory=dict)

class DesignData:
    def __init__(self, _lefParserImplement, _defParserImplement):
        self.lefParserImplement = _lefParserImplement
        self.defParserImplement = _defParserImplement

        self.inst_rtree = None
        self.inst_bbox = None

        self.instData = InstanceMap()


    def resolveCompToInst(self):
        if not self.defParserImplement or not self.lefParserImplement:
            logging.error("Missing DEF or LEF parser.")
            return

        # Step 1: Get DEF component data
        design_units = self.defParserImplement.get_unit()
        design_units = int(design_units)

        components = self.defParserImplement.get_components()
        if not isinstance(components, list):
            logging.error(f"'components' should be a list, got {type(components)}")
            return

        self.inst_rtree = index.Index()

        # Step 2: Get LEF macro data
        for comp in components:

            instance_name = gname_index.getName(comp.inst_name_id)
            cell_name = gname_index.getName(comp.cell_name_id)
            type = gname_index.getName(comp.type_id)
            location = comp.location

            if not instance_name or not cell_name or not location:
                logging.warning(f"Invalid component entry: {comp}")
                continue

            x_dbu, y_dbu = location
            x_dbu = int(x_dbu)
            y_dbu = int(y_dbu)

            x_um = x_dbu / design_units
            y_um = y_dbu / design_units

            macro = self.lefParserImplement.get_macro(cell_name)
            if not macro:
                logging.warning(f"Macro {cell_name} not found in LEF for instance {instance_name}.")
                continue

            width, height = macro.size

            bbox = [x_um, y_um, x_um + width, y_um + height]

            inst = Instance(cell_name_id=comp.cell_name_id, 
                                    type_id=comp.type_id, 
                                    location=bbox)
            self.instData.instance_data[comp.inst_name_id] = inst

            self.inst_rtree.insert(comp.inst_name_id, bbox)

        self.inst_bbox = self.inst_rtree.get_bounds()

        print(f"Resolved {len(self.instData.instance_data)} instances")


    def iterate_pruned_rtrees(original_rtree, numIter):
        all_objs = list(original_rtree.intersection(original_rtree.bounds, objects=True))
        total = len(all_objs)

        # Compute centroids for clustering
        centroids = [
            ((obj.bbox[0] + obj.bbox[2]) / 2, (obj.bbox[1] + obj.bbox[3]) / 2)
            for obj in all_objs
        ]

        # Cluster into numIter groups for even spatial distribution
        kmeans = KMeans(n_clusters=numIter, random_state=42)
        labels = kmeans.fit_predict(centroids)

        # Group objects by cluster
        clustered_objs = [[] for _ in range(numIter)]
        for i, obj in enumerate(all_objs):
            clustered_objs[labels[i]].append(obj)

        # Optional: shuffle each cluster to avoid spatial bias inside cluster
        for group in clustered_objs:
            random.shuffle(group)

        # Each iteration, create a new R-tree and process it
        for i in range(numIter):
            props = index.Property()
            new_rtree = index.Index(properties=props)
            for obj in clustered_objs[i]:
                new_rtree.insert(obj.id, obj.bbox, obj.object)

            work_on_pruned_rtree(new_rtree)
