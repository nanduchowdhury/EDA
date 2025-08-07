
import logging

from rtree import index

from global_name_index import gname_index

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

from sklearn.cluster import KMeans
import numpy as np
import random

import pandas as pd
import re

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

        self.layer_color_map = {}

        self.instData = InstanceMap()


    def get_inst_ids_by_bbox(self, bbox=None):

        if not bbox:
            if len(self.design_data.inst_rtree) > 0:
                    bbox = self.design_data.inst_rtree.get_bounds()

        if not bbox:
            return []
        
        bbox_ids = list(self.inst_rtree.intersection(bbox))

        return bbox_ids

    def get_inst_ids_by_name(self, name_list=None):

        id_list = []

        if name_list:
            for name in name_list:
                inst_id = gname_index.get_id(name)
                if inst_id is None:
                    continue
                id_list.append(inst_id)

        return id_list

    def get_inst_ids_by_regex(self, inst_regex, cell_regex):

        inst_list = []
        inst_pattern = re.compile(inst_regex) if inst_regex else None
        cell_pattern = re.compile(cell_regex) if cell_regex else None

        for inst_id, inst in self.instData.instance_data.items():
            inst_name = gname_index.getName(inst_id)
            cell_name = gname_index.getName(inst.cell_name_id)

            # Apply regex filters
            inst_match = True if not inst_pattern else (inst_pattern.search(inst_name) if inst_name else False)
            cell_match = True if not cell_pattern else (cell_pattern.search(cell_name) if cell_name else False)

            if inst_match and cell_match:
                inst_list.append(inst_id)

        return inst_list


    def get_inst_df(self, inst_list):
        """
        Get a DataFrame of instances with their names and locations.
        """
        data = []
        for inst_id in inst_list:
            inst = self.instData.instance_data.get(inst_id)
            if inst:
                inst_name = gname_index.getName(inst_id)
                cell_name = gname_index.getName(inst.cell_name_id)
                type_name = gname_index.getName(inst.type_id)
                location = inst.location
                data.append({
                    "inst_name": inst_name,
                    "cell_name": cell_name,
                    "type": type_name,
                    "location": location
                })

        return pd.DataFrame(data)


    def apply_orient(self, bbox, orient):
        """
        Apply orientation to a bounding box.

        Parameters:
            bbox: list of [x1, y1, x2, y2]
            orient: str, one of 'N', 'FN', 'S', 'FS', 'E', 'FE', 'W', 'FW'

        Returns:
            Transformed bbox as list: [x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        # Translate to origin (centered around 0,0)
        corners = [(x1 - cx, y1 - cy), (x2 - cx, y2 - cy)]

        def flip_x(pt): return (-pt[0], pt[1])   # mirror over Y-axis
        def flip_y(pt): return (pt[0], -pt[1])   # mirror over X-axis
        def rotate_90(pt): return (pt[1], -pt[0])    # rotate +90 deg
        def rotate_270(pt): return (-pt[1], pt[0])   # rotate -90 deg
        def rotate_180(pt): return (-pt[0], -pt[1])

        if orient == 'N':
            transformed = corners
        elif orient == 'FN':
            transformed = [flip_x(p) for p in corners]
        elif orient == 'S':
            transformed = [rotate_180(p) for p in corners]
        elif orient == 'FS':
            transformed = [flip_x(rotate_180(p)) for p in corners]
        elif orient == 'E':
            transformed = [rotate_90(p) for p in corners]
        elif orient == 'FE':
            transformed = [flip_x(rotate_90(p)) for p in corners]
        elif orient == 'W':
            transformed = [rotate_270(p) for p in corners]
        elif orient == 'FW':
            transformed = [flip_x(rotate_270(p)) for p in corners]
        else:
            raise ValueError(f"Unsupported orientation: {orient}")

        # Translate back to original center
        tx1 = min(p[0] for p in transformed) + cx
        ty1 = min(p[1] for p in transformed) + cy
        tx2 = max(p[0] for p in transformed) + cx
        ty2 = max(p[1] for p in transformed) + cy

        return [tx1, ty1, tx2, ty2]


    def assign_layer_colors(self):
        self.layer_color_map = self.lefParserImplement.assign_layer_colors()

    def resolveCompToInst(self):
        if not self.defParserImplement or not self.lefParserImplement:
            logging.error("Missing DEF or LEF parser.")
            return

        # Step 1: Get DEF component data
        design_units = self.defParserImplement.get_unit()
        design_units = int(design_units)

        components = self.defParserImplement.get_components()

        self.inst_rtree = index.Index()

        location_missing_warning = 0

        # Step 2: Get LEF macro data
        for comp_id in components:

            comp = components[comp_id]

            instance_name = gname_index.getName(comp_id)
            cell_name = gname_index.getName(comp.cell_name_id)
            type = gname_index.getName(comp.type_id)
            location = comp.location
            orient = gname_index.getName(comp.orient) if comp.orient else None

            if not location:
                location_missing_warning += 1
                continue

            x_dbu, y_dbu = location

            (x_um, y_um) = self.defParserImplement.convert_to_micron(x_dbu, y_dbu)

            macros = self.lefParserImplement.get_macros(cell_name)
            if not macros:
                logging.warning(f"Macro {cell_name} not found in LEF for instance {instance_name}...skipping.")
                continue

            if len(macros) > 1:
                logging.warning(f"Multiple macros found for {cell_name} in LEF, using first one.")

            width, height = macros[0].size

            bbox = [x_um, y_um, x_um + width, y_um + height]

            bbox = self.apply_orient(bbox, orient) if orient else bbox

            for i in range(4):
                bbox[i] = int(bbox[i] * design_units)

            inst = Instance(cell_name_id=comp.cell_name_id, 
                                    type_id=comp.type_id, 
                                    location=bbox)
            self.instData.instance_data[comp_id] = inst

            self.inst_rtree.insert(comp_id, bbox)

        self.inst_bbox = self.inst_rtree.get_bounds()

        print(f"Resolved {len(self.instData.instance_data)} instances")

        if location_missing_warning > 0:
            logging.warning(f"Skipped {location_missing_warning} instances due to missing location data.")


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
