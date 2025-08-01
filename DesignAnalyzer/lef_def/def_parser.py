
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot, pyqtSignal

import json
import re

import os
import threading
import logging

import pandas as pd

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import re

from global_name_index import gname_index


@dataclass
class Units:
    distance_id: int
    microns: int

@dataclass
class DieArea:
    points: List[Tuple[int, int]] = field(default_factory=list)

@dataclass
class PropertyDefinition:
    obj_type: str         # e.g., DESIGN, REGION, GROUP, COMPONENT, etc.
    prop_name: str        # e.g., strprop, intprop, etc.
    data_type: str        # STRING, INTEGER, REAL
    range: Optional[Tuple[float, float]] = None  # (min, max) if RANGE is present
    default: Optional[str] = None               # Default value if present

@dataclass
class Row:
    name_id: int
    site_id: int
    orig_x: int
    orig_y: int
    site_orient_id: int
    do_x: Optional[int] = None
    by_y: Optional[int] = None
    step_x: Optional[int] = None
    step_y: Optional[int] = None
    properties: Dict[str, str] = field(default_factory=dict)

@dataclass
class Track:
    direction_id: int
    step: int
    layer_id: int

@dataclass
class NetConnection:
    comp_name_id: Optional[int] = None  # None if PIN or VPIN
    pin_name_id: Optional[int] = None
    is_pin: bool = False
    is_vpin: bool = False
    vpin_name_id: Optional[int] = None
    synthesized: bool = False

@dataclass
class NetVPin:
    vpin_name_id: int
    layer_name_id: Optional[int] = None
    pt1: Optional[Tuple[int, int]] = None
    pt2: Optional[Tuple[int, int]] = None
    placed: Optional[Tuple[int, int, str]] = None
    fixed: Optional[Tuple[int, int, str]] = None
    cover: Optional[Tuple[int, int, str]] = None

@dataclass
class NetWire:
    wire_type: str  # e.g. "ROUTED", "FIXED", "COVER", "NOSHIELD"
    layer: Optional[int] = None
    points: List[Tuple[int, int]] = field(default_factory=list)
    vias: List[str] = field(default_factory=list)
    mask: Optional[int] = None
    rects: List[Tuple[int, int, int, int]] = field(default_factory=list)
    raw: str = ""  # Store the raw line for advanced/rare features

@dataclass
class NetSubnet:
    subnet_name_id: int
    connections: List[NetConnection] = field(default_factory=list)
    wires: List[NetWire] = field(default_factory=list)
    nondefaultrule: Optional[str] = None
    # Add regularWiring fields as needed

@dataclass
class Net:
    connections: List[NetConnection] = field(default_factory=list)
    mustjoin: List[Tuple[int, int]] = field(default_factory=list)  # List of (comp_name_id, pin_name_id)
    shieldnets: List[int] = field(default_factory=list)
    vpins: List[NetVPin] = field(default_factory=list)
    subnets: List[NetSubnet] = field(default_factory=list)
    xtalk_class: Optional[str] = None
    nondefaultrule: Optional[str] = None
    source: Optional[str] = None
    fixedbump: bool = False
    wires: List[NetWire] = field(default_factory=list)
    frequency: Optional[float] = None
    original_net_id: Optional[int] = None
    use: Optional[str] = None
    pattern: Optional[str] = None
    estcap: Optional[float] = None
    weight: Optional[float] = None
    properties: Dict[str, str] = field(default_factory=dict)
    # Add regularWiring fields as needed

@dataclass
class ViaRect:
    layer_name_id: int
    pt1: Tuple[int, int]
    pt2: Tuple[int, int]

@dataclass
class ViaPolygon:
    layer_name_id: int
    points: List[Tuple[int, int]]

@dataclass
class Via:
    via_rule_id: Optional[int] = None
    cut_size: Optional[Tuple[int, int]] = None
    layer_ids: List[int] = field(default_factory=list)
    cut_spacing: Optional[Tuple[int, int]] = None
    enclosure: Optional[Tuple[int, int, int, int]] = None
    row_col: Optional[Tuple[int, int]] = None
    origin: Optional[Tuple[int, int]] = None
    offset: Optional[Tuple[int, int, int, int]] = None
    pattern: Optional[str] = None
    rects: List[ViaRect] = field(default_factory=list)
    polygons: List[ViaPolygon] = field(default_factory=list)

@dataclass
class Region:
    name_id: int
    coordinates: List[Tuple[int, int]] = field(default_factory=list)
    region_type: Optional[str] = None  # "FENCE" or "GUIDE"
    properties: Dict[str, str] = field(default_factory=dict)

@dataclass
class Component:
    cell_name_id: int
    eeqmaster_id: Optional[int] = None
    source: Optional[str] = None
    placed: Optional[Tuple[int, int, str]] = None
    fixed: Optional[Tuple[int, int, str]] = None
    cover: Optional[Tuple[int, int, str]] = None
    unplaced: bool = False
    halo: Optional[Tuple[bool, int, int, int, int]] = None  # (soft, left, bottom, right, top)
    routehalo: Optional[Tuple[int, str, str]] = None        # (haloDist, minLayer, maxLayer)
    weight: Optional[float] = None
    region_id: Optional[int] = None
    properties: Dict[str, str] = field(default_factory=dict)
    type_id: Optional[int] = None
    location: Optional[Tuple[int, int]] = None


@dataclass
class PinPortLayer:
    layer_name_id: int
    spacing: Optional[int] = None
    designrulewidth: Optional[int] = None
    rects: List[Tuple[int, int]] = field(default_factory=list)
    polygons: List[List[Tuple[int, int]]] = field(default_factory=list)
    vias: List[Dict] = field(default_factory=list)  # Each: {'via_id': int, 'pt': Tuple[int, int]}

@dataclass
class PinPort:
    layers: List[PinPortLayer] = field(default_factory=list)
    cover: Optional[Tuple[int, int, str]] = None
    fixed: Optional[Tuple[int, int, str]] = None
    placed: Optional[Tuple[int, int, str]] = None

@dataclass
class PinAntenna:
    type: str
    value: float
    layer_name_id: Optional[int] = None

@dataclass
class Pin:
    net_id: Optional[int] = None
    special: bool = False
    direction_id: Optional[int] = None
    netexpr: Optional[str] = None
    supply_sensitivity: Optional[int] = None
    ground_sensitivity: Optional[int] = None
    use_id: Optional[int] = None
    antenna: List[PinAntenna] = field(default_factory=list)
    antenna_model: Optional[str] = None
    ports: List[PinPort] = field(default_factory=list)

@dataclass
class Blockage:
    blockage_type: Optional[str] = None  # "LAYER" or "PLACEMENT"
    layer_name_id: Optional[int] = None
    component_name_id: Optional[int] = None
    slots: bool = False
    fills: bool = False
    pushdown: bool = False
    exceptpgnet: bool = False
    spacing: Optional[int] = None
    designrulewidth: Optional[int] = None
    soft: bool = False
    partial_max_density: Optional[float] = None
    rects: List[Tuple[int, int, int, int]] = field(default_factory=list)
    polygons: List[List[Tuple[int, int]]] = field(default_factory=list)

@dataclass
class SpecialNetConnection:
    comp_name_id: Optional[int] = None  # None if PIN
    pin_name_id: int = 0
    is_pin: bool = False
    synthesized: bool = False

@dataclass
class SpecialNet:
    connections: List[SpecialNetConnection] = field(default_factory=list)
    voltage: Optional[float] = None
    source: Optional[str] = None
    fixedbump: bool = False
    original_net_id: Optional[int] = None
    use: Optional[str] = None
    pattern: Optional[str] = None
    estcap: Optional[float] = None
    weight: Optional[float] = None
    properties: Dict[str, str] = field(default_factory=dict)
    # You can add specialWiring fields as needed

@dataclass
class DefData:
    version_id: Optional[int] = None
    design_name_id: Optional[int] = None
    units: Optional[Units] = None
    diearea: Optional[DieArea] = None
    rows: List[Row] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    nets: Dict[int, Net] = field(default_factory=dict)
    vias: Dict[int, Via] = field(default_factory=dict)
    regions: List[Region] = field(default_factory=list)
    components: Dict[int, Component] = field(default_factory=dict)
    pins: Dict[int, Pin] = field(default_factory=dict)
    blockages: List[Blockage] = field(default_factory=list)
    specialnets: Dict[int, SpecialNet] = field(default_factory=dict)
    property_definitions: Dict[int, int] = field(default_factory=dict)

class DefParser:
    def __init__(self):
        self.def_data = DefData()

    def parse_version(self, line: str):
        if line.startswith("VERSION"):
            version = line.split()[1]
            self.def_data.version_id = gname_index.set(version)

    def parse_design_name(self, line: str):
        if line.startswith("DESIGN"):
            design = line.split()[1].strip(";")
            self.def_data.design_name_id = gname_index.set(design)

    def parse_units(self, line: str):
        line = line.rstrip(';').strip()
        if line.startswith("UNITS") and "MICRONS" in line:
            parts = line.split()
            distance_id = gname_index.set("MICRONS")
            self.def_data.units = Units(distance_id=distance_id, microns=int(parts[-1]))

    def parse_diearea(self, line: str):
        try:
            # Example: DIEAREA ( 0 0 ) ( 1000 2000 ) ;
            coords = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line)
            points = [tuple(map(int, pt)) for pt in coords]
            self.def_data.diearea = DieArea(points=points)
        except Exception as e:
            print(f"Error DEF parsing diearea: line: {line} error: {e}")


    def parse_row(self, line: str):
        try:
            # Remove trailing ';' if present
            line = line.rstrip(';').strip()
            parts = line.split()
            name_id = gname_index.set(parts[1])
            site_id = gname_index.set(parts[2])
            orig_x = int(parts[3])
            orig_y = int(parts[4])
            site_orient_id = gname_index.set(parts[5])

            do_x = by_y = step_x = step_y = None
            properties = {}

            # Look for DO ... BY ... [STEP ...]
            if "DO" in parts:
                do_idx = parts.index("DO")
                do_x = int(parts[do_idx + 1])
                by_y = int(parts[do_idx + 3])
                if "STEP" in parts:
                    step_idx = parts.index("STEP")
                    step_x = int(parts[step_idx + 1])
                    step_y = int(parts[step_idx + 2])

            # Look for + PROPERTY
            if "+PROPERTY" in line or "+ PROPERTY" in line:
                prop_parts = line.split("+ PROPERTY")
                if len(prop_parts) > 1:
                    props = prop_parts[1].strip().split()
                    for i in range(0, len(props), 2):
                        if i+1 < len(props):
                            properties[props[i]] = props[i+1]

            self.def_data.rows.append(Row(
                name_id=name_id,
                site_id=site_id,
                orig_x=orig_x,
                orig_y=orig_y,
                site_orient_id=site_orient_id,
                do_x=do_x,
                by_y=by_y,
                step_x=step_x,
                step_y=step_y,
                properties=properties
            ))

        except Exception as e:
            print(f"Error DEF parsing row: line: {line} error: {e}")

    def parse_track(self, line: str):
        try:
            parts = line.split()
            direction_id = gname_index.set(parts[1])
            step = int(parts[6])
            layer_id = gname_index.set(parts[-1])
            self.def_data.tracks.append(Track(direction_id, step, layer_id))

        except Exception as e:
            print(f"Error DEF parsing track: line: {line} error: {e}")

    def parse_via(self, lines: List[str]):
        try:
            lines = self.clean_lines(lines)
            (header, lines) = self.create_new_lines_list(lines)


            name_id = gname_index.set(header.split()[0])
            via = Via()
            for line in lines:
                line = line.strip()
                if line.startswith("+ VIARULE"):
                    via.via_rule_id = gname_index.set(line.split()[2])
                elif line.startswith("+ CUTSIZE"):
                    nums = list(map(int, re.findall(r'-?\d+', line)))
                    if len(nums) == 2:
                        via.cut_size = tuple(nums)
                elif line.startswith("+ LAYERS"):
                    tokens = line.split()
                    # skip "+ LAYERS", then get all layer names
                    via.layer_ids = [gname_index.set(t) for t in tokens[2:]]
                elif line.startswith("+ CUTSPACING"):
                    nums = list(map(int, re.findall(r'-?\d+', line)))
                    if len(nums) == 2:
                        via.cut_spacing = tuple(nums)
                elif line.startswith("+ ENCLOSURE"):
                    nums = list(map(int, re.findall(r'-?\d+', line)))
                    if len(nums) == 4:
                        via.enclosure = tuple(nums)
                elif line.startswith("+ ROWCOL"):
                    nums = list(map(int, re.findall(r'-?\d+', line)))
                    if len(nums) == 2:
                        via.row_col = tuple(nums)
                elif line.startswith("+ ORIGIN"):
                    nums = list(map(int, re.findall(r'-?\d+', line)))
                    if len(nums) == 2:
                        via.origin = tuple(nums)
                elif line.startswith("+ OFFSET"):
                    nums = list(map(int, re.findall(r'-?\d+', line)))
                    if len(nums) == 4:
                        via.offset = tuple(nums)
                elif line.startswith("+ PATTERN"):
                    via.pattern = line.split()[2]
                elif line.startswith("+ RECT"):
                    tokens = line.split()
                    layer_name_id = gname_index.set(tokens[2])
                    pts = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line)
                    if len(pts) == 2:
                        pt1 = tuple(map(int, pts[0]))
                        pt2 = tuple(map(int, pts[1]))
                        via.rects.append(ViaRect(layer_name_id=layer_name_id, pt1=pt1, pt2=pt2))
                elif line.startswith("+ POLYGON"):
                    tokens = line.split()
                    layer_name_id = gname_index.set(tokens[2])
                    pts = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line)
                    points = [tuple(map(int, pt)) for pt in pts]
                    if points:
                        via.polygons.append(ViaPolygon(layer_name_id=layer_name_id, points=points))
            
            self.def_data.vias[name_id] = via

        except Exception as e:
            print(f"Error DEF parsing via: lines: {lines} error: {e}")

    def clean_lines(self, lines: list) -> list:
        """
        Strips leading '-', trailing ';', and whitespace from each line.
        Returns a list of cleaned lines (skips empty lines).
        """
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.endswith(";"):
                line = line[:-1].strip()
            if line.startswith("-"):
                line = line[1:].strip()
            if line:  # skip empty lines
                cleaned.append(line)
        return cleaned

    def create_new_lines_list(self, lines: list):
        """
        1. Concatenate all lines in 'lines' into a single string.
        2. Split the string at each '+' (keeping the '+') to create multiple lines.
        Each resulting line (except the first) will start with '+'.
        3. Return (header, attr_lines) where header is the first line (stripped)
        and attr_lines is a list of lines starting with '+' (stripped).
        """
        # Step 1: Concatenate all lines into a single string
        single_line = ' '.join(lines)
        # Step 2: Split at each '+' (but keep the '+')
        split_lines = re.split(r'(?=\+)', single_line)
        # Step 3: Strip whitespace from each line
        split_lines = [l.strip() for l in split_lines if l.strip()]
        # Step 4: First line is header, rest are attribute lines
        header = split_lines[0]
        attr_lines = split_lines[1:]

        return (header, attr_lines)

    def parse_component(self, lines: List[str]):
        try:
            lines = self.clean_lines(lines)
            (header, lines) = self.create_new_lines_list(lines)

            parts = header.split()

            inst_id = gname_index.set(parts[0])
            cell_id = gname_index.set(parts[1])

            comp = Component(cell_name_id=cell_id)

            for line in lines:
                line = line.strip()

                if line.startswith("+ EEQMASTER"):
                    comp.eeqmaster_id = gname_index.set(line.split()[2])
                elif line.startswith("+ SOURCE"):
                    comp.source = line.split()[2]
                elif line.startswith("+ FIXED"):
                    nums = re.findall(r'-?\d+', line)
                    pt = (int(nums[0]), int(nums[1]))
                    orient = line.split()[-1]
                    comp.fixed = (*pt, orient)
                    comp.location = pt
                elif line.startswith("+ COVER"):
                    nums = re.findall(r'-?\d+', line)
                    pt = (int(nums[0]), int(nums[1]))
                    orient = line.split()[-1]
                    comp.cover = (*pt, orient)
                    comp.location = pt
                elif line.startswith("+ PLACED"):
                    nums = re.findall(r'-?\d+', line)
                    pt = (int(nums[0]), int(nums[1]))
                    orient = line.split()[-1]
                    comp.placed = (*pt, orient)
                    comp.location = pt
                elif line.startswith("+ UNPLACED"):
                    comp.unplaced = True
                elif line.startswith("+ HALO"):
                    tokens = line.split()
                    soft = "SOFT" in tokens
                    nums = [int(x) for x in re.findall(r'-?\d+', line)]
                    if len(nums) == 4:
                        comp.halo = (soft, *nums)
                elif line.startswith("+ ROUTEHALO"):
                    tokens = line.split()
                    haloDist = int(tokens[2])
                    minLayer = tokens[3]
                    maxLayer = tokens[4]
                    comp.routehalo = (haloDist, minLayer, maxLayer)
                elif line.startswith("+ WEIGHT"):
                    comp.weight = float(line.split()[2])
                elif line.startswith("+ REGION"):
                    comp.region_id = gname_index.set(line.split()[2])
                elif line.startswith("+ PROPERTY"):
                    props = line.split()[2:]
                    for i in range(0, len(props), 2):
                        if i+1 < len(props):
                            comp.properties[props[i]] = props[i+1]

            self.def_data.components[inst_id] = comp

        except Exception as e:
            print(f"Error DEF parsing component: lines: {lines} error: {e}")

    def parse_pin(self, lines: List[str]):
        try:
            lines = self.clean_lines(lines)
            (header, lines) = self.create_new_lines_list(lines)

        
            parts = header.split()
            name_id = gname_index.set(parts[0])
            net_id = gname_index.set(parts[3]) if "+NET" in header or "+NET" in parts else 0

            pin = Pin()

            current_port = None
            current_layer = None

            for line in lines:
                line = line.strip()
                if line.startswith("+ NET"):
                    pin.net_id = gname_index.set(line.split()[2])
                elif line.startswith("+ SPECIAL"):
                    pin.special = True
                elif line.startswith("+ DIRECTION"):
                    pin.direction_id = gname_index.set(line.split()[2])
                elif line.startswith("+ NETEXPR"):
                    pin.netexpr = line.split('"')[1] if '"' in line else None
                elif line.startswith("+ SUPPLYSENSITIVITY"):
                    pin.supply_sensitivity = gname_index.set(line.split()[2])
                elif line.startswith("+ GROUNDSENSITIVITY"):
                    pin.ground_sensitivity = gname_index.set(line.split()[2])
                elif line.startswith("+ USE"):
                    pin.use_id = gname_index.set(line.split()[2])
                elif line.startswith("+ ANTENNAMODEL"):
                    pin.antenna_model = line.split()[2]
                elif line.startswith("+ ANTENNA"):
                    tokens = line.split()
                    ant_type = tokens[1]
                    value = float(tokens[2])
                    layer_name_id = None
                    if "LAYER" in tokens:
                        layer_name_id = gname_index.set(tokens[-1])
                    pin.antenna.append(PinAntenna(type=ant_type, value=value, layer_name_id=layer_name_id))
                elif line.startswith("+ PORT"):
                    current_port = PinPort()
                    pin.ports.append(current_port)
                elif line.startswith("+ LAYER"):
                    tokens = line.split()
                    layer_name_id = gname_index.set(tokens[2])
                    current_layer = PinPortLayer(layer_name_id=layer_name_id)
                    if current_port is not None:
                        current_port.layers.append(current_layer)
                elif line.startswith("SPACING"):
                    if current_layer:
                        current_layer.spacing = int(line.split()[1])
                elif line.startswith("DESIGNRULEWIDTH"):
                    if current_layer:
                        current_layer.designrulewidth = int(line.split()[1])
                elif re.match(r'^\(\s*-?\d+', line):  # RECT or point
                    coords = tuple(map(int, re.findall(r'-?\d+', line)))
                    if current_layer:
                        current_layer.rects.append(coords)
                elif line.startswith("+ POLYGON"):
                    tokens = line.split()
                    layer_name_id = gname_index.set(tokens[2])
                    pts = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line)
                    if pts and current_layer:
                        current_layer.polygons.append([tuple(map(int, pt)) for pt in pts])
                elif line.startswith("+ VIA"):
                    tokens = line.split()
                    via_id = gname_index.set(tokens[2])
                    pt = tuple(map(int, re.findall(r'-?\d+', line)))
                    if current_layer:
                        current_layer.vias.append({'via_id': via_id, 'pt': pt})
                elif line.startswith("+ COVER"):
                    tokens = line.split()
                    pt = tuple(map(int, re.findall(r'-?\d+', line)))
                    orient = tokens[-1]
                    if current_port:
                        current_port.cover = (*pt, orient)
                elif line.startswith("+ FIXED"):
                    tokens = line.split()
                    pt = tuple(map(int, re.findall(r'-?\d+', line)))
                    orient = tokens[-1]
                    if current_port:
                        current_port.fixed = (*pt, orient)
                elif line.startswith("+ PLACED"):
                    tokens = line.split()
                    pt = tuple(map(int, re.findall(r'-?\d+', line)))
                    orient = tokens[-1]
                    if current_port:
                        current_port.placed = (*pt, orient)
                # ... handle other attributes as needed

            self.def_data.pins[name_id] = pin

        except Exception as e:
            print(f"Error DEF parsing pin: lines: {lines} error: {e}")

    def parse_blockage(self, lines: List[str]):
        try:
            lines = self.clean_lines(lines)
            (header, lines) = self.create_new_lines_list(lines)
            
        
            blockage_type = header[0]
            blockage = Blockage(blockage_type=blockage_type)

            if blockage_type == "LAYER":
                blockage.layer_name_id = gname_index.set(header[1])
            elif blockage_type == "PLACEMENT":
                pass  # No layer for PLACEMENT

            for line in lines:
                line = line.strip()
                if line.startswith("+ COMPONENT"):
                    blockage.component_name_id = gname_index.set(line.split()[2])
                elif line.startswith("+ SLOTS"):
                    blockage.slots = True
                elif line.startswith("+ FILLS"):
                    blockage.fills = True
                elif line.startswith("+ PUSHDOWN"):
                    blockage.pushdown = True
                elif line.startswith("+ EXCEPTPGNET"):
                    blockage.exceptpgnet = True
                elif line.startswith("+ SPACING"):
                    blockage.spacing = int(re.findall(r'\d+', line)[0])
                elif line.startswith("+ DESIGNRULEWIDTH"):
                    blockage.designrulewidth = int(re.findall(r'\d+', line)[0])
                elif line.startswith("+ SOFT"):
                    blockage.soft = True
                elif line.startswith("+ PARTIAL"):
                    blockage.partial_max_density = float(line.split()[2])
                elif line.startswith("RECT"):
                    nums = list(map(int, re.findall(r'-?\d+', line)))
                    if len(nums) == 4:
                        blockage.rects.append(tuple(nums))
                elif line.startswith("POLYGON"):
                    pts = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line)
                    if pts:
                        blockage.polygons.append([tuple(map(int, pt)) for pt in pts])

            self.def_data.blockages.append(blockage)

        except Exception as e:
            print(f"Error DEF parsing blockage: lines: {lines} error: {e}")

    def parse_property_definition(self, lines: List[str]):
        """
        Parses PROPERTYDEFINITIONS section from DEF.
        Stores results in self.def_data.property_definitions as a list of PropertyDefinition.
        """

        try:
            self.def_data.property_definitions = []

            for line in lines:
                line = line.strip().rstrip(';')
                if not line or line.startswith("PROPERTYDEFINITIONS") or line.startswith("END PROPERTYDEFINITIONS"):
                    continue

                # Example: DESIGN strprop STRING "aString"
                # Example: DESIGN intrangeprop INTEGER RANGE 1 100 25
                tokens = line.split()
                obj_type = tokens[0]
                prop_name = tokens[1]
                data_type = tokens[2]
                prop_range = None
                default = None

                if "RANGE" in tokens:
                    idx = tokens.index("RANGE")
                    min_val = float(tokens[idx+1])
                    max_val = float(tokens[idx+2])
                    prop_range = (min_val, max_val)
                    # Default value may follow
                    if len(tokens) > idx+3:
                        default = tokens[idx+3]
                elif len(tokens) > 3:
                    # Default value for STRING, INTEGER, REAL
                    default = tokens[3].strip('"')

                self.def_data.property_definitions.append(
                    PropertyDefinition(
                        obj_type=obj_type,
                        prop_name=prop_name,
                        data_type=data_type,
                        range=prop_range,
                        default=default
                    )
                )
            
        except Exception as e:
            print(f"Error DEF parsing property definitions: lines: {lines} error: {e}")

    def parse_specialnet(self, lines: List[str]):
        try:
            lines = self.clean_lines(lines)
            (header, lines) = self.create_new_lines_list(lines)

        
            name_id = gname_index.set(header.split()[0])
            specialnet = SpecialNet()

            lines = [header] + lines  # Include header in lines for processing

            for line in lines:
                line = line.strip()
                # Connections: ( compName pinName ) or ( PIN pinName )
                conn_match = re.findall(r'\(\s*(.*?)\s*\)', line)
                for conn in conn_match:
                    tokens = conn.split()
                    if not tokens:
                        continue
                    if tokens[0] == "PIN":
                        pin_name_id = gname_index.set(tokens[1])
                        synthesized = "+ SYNTHESIZED" in line
                        specialnet.connections.append(SpecialNetConnection(
                            comp_name_id=None, pin_name_id=pin_name_id, is_pin=True, synthesized=synthesized
                        ))
                    else:
                        comp_name_id = gname_index.set(tokens[0])
                        pin_name_id = gname_index.set(tokens[1])
                        synthesized = "+ SYNTHESIZED" in line
                        specialnet.connections.append(SpecialNetConnection(
                            comp_name_id=comp_name_id, pin_name_id=pin_name_id, is_pin=False, synthesized=synthesized
                        ))
                if line.startswith("+ VOLTAGE"):
                    specialnet.voltage = float(line.split()[2])
                elif line.startswith("+ SOURCE"):
                    specialnet.source = line.split()[2]
                elif line.startswith("+ FIXEDBUMP"):
                    specialnet.fixedbump = True
                elif line.startswith("+ ORIGINAL"):
                    specialnet.original_net_id = gname_index.set(line.split()[2])
                elif line.startswith("+ USE"):
                    specialnet.use = line.split()[2]
                elif line.startswith("+ PATTERN"):
                    specialnet.pattern = line.split()[2]
                elif line.startswith("+ ESTCAP"):
                    specialnet.estcap = float(line.split()[2])
                elif line.startswith("+ WEIGHT"):
                    specialnet.weight = float(line.split()[2])
                elif line.startswith("+ PROPERTY"):
                    # Handles multiple properties in one line
                    props = line.split()[2:]
                    for i in range(0, len(props), 2):
                        if i+1 < len(props):
                            specialnet.properties[props[i]] = props[i+1]
                # You can add parsing for specialWiring here if needed

            self.def_data.specialnets[name_id] = specialnet

        except Exception as e:
            print(f"Error DEF parsing specialnet: lines: {lines} error: {e}")

    def parse_region(self, lines: List[str]):
        try:
            lines = self.clean_lines(lines)
            (header, lines) = self.create_new_lines_list(lines)


            parts = header.split()
            name_id = gname_index.set(parts[0])
            coords = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', header)
            coordinates = [tuple(map(int, pt)) for pt in coords]

            region = Region(name_id=name_id, coordinates=coordinates)

            for line in lines:
                line = line.strip()
                if line.startswith("+ TYPE"):
                    region.region_type = line.split()[2]
                elif line.startswith("+ PROPERTY"):
                    props = line.split()[2:]
                    for i in range(0, len(props), 2):
                        if i+1 < len(props):
                            region.properties[props[i]] = props[i+1]

            self.def_data.regions.append(region)

        except Exception as e:
            print(f"Error DEF parsing region: lines: {lines} error: {e}")


    def parse_net(self, lines: List[str]):
        #try:
            lines = self.clean_lines(lines)
            header, attr_lines = self.create_new_lines_list(lines)

            name_id = gname_index.set(header.split()[0])
            net = Net()

            # Parse connections from header
            conn_match = re.findall(r'\(\s*(.*?)\s*\)', header)
            for conn in conn_match:
                tokens = conn.split()
                if not tokens:
                    continue
                if tokens[0] == "PIN":
                    pin_name_id = gname_index.set(tokens[1])
                    net.connections.append(NetConnection(
                        comp_name_id=None, pin_name_id=pin_name_id, is_pin=True
                    ))
                elif tokens[0] == "VPIN":
                    vpin_name_id = gname_index.set(tokens[1])
                    net.connections.append(NetConnection(
                        comp_name_id=None, pin_name_id=None, is_pin=False, is_vpin=True, vpin_name_id=vpin_name_id
                    ))
                else:
                    comp_name_id = gname_index.set(tokens[0])
                    pin_name_id = gname_index.set(tokens[1])
                    net.connections.append(NetConnection(
                        comp_name_id=comp_name_id, pin_name_id=pin_name_id, is_pin=False
                    ))

            i = 0
            n = len(attr_lines)
            while i < n:
                line = attr_lines[i].strip()

                # Shieldnets
                if line.startswith("+ SHIELDNET"):
                    net.shieldnets.append(gname_index.set(line.split()[2]))

                # VPINs
                elif line.startswith("+ VPIN"):
                    tokens = line.split()
                    vpin_name_id = gname_index.set(tokens[2])
                    layer_name_id = None
                    pt1 = pt2 = None
                    placed = fixed = cover = None

                    # LAYER
                    m = re.search(r'LAYER\s+(\S+)', line)
                    if m:
                        layer_name_id = gname_index.set(m.group(1))

                    # Points
                    pts = re.findall(r'\(\s*(-?\d+)\s+(-?\d+)\s*\)', line)
                    if len(pts) >= 2:
                        pt1 = tuple(map(int, pts[0]))
                        pt2 = tuple(map(int, pts[1]))
                    elif len(pts) == 1:
                        pt1 = tuple(map(int, pts[0]))

                    # PLACED, FIXED, COVER (with orientation)
                    m = re.search(r'PLACED\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*([A-Z]+)', line)
                    if m:
                        placed = (int(m.group(1)), int(m.group(2)), m.group(3))
                    m = re.search(r'FIXED\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*([A-Z]+)', line)
                    if m:
                        fixed = (int(m.group(1)), int(m.group(2)), m.group(3))
                    m = re.search(r'COVER\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*([A-Z]+)', line)
                    if m:
                        cover = (int(m.group(1)), int(m.group(2)), m.group(3))

                    net.vpins.append(NetVPin(
                        vpin_name_id=vpin_name_id,
                        layer_name_id=layer_name_id,
                        pt1=pt1,
                        pt2=pt2,
                        placed=placed,
                        fixed=fixed,
                        cover=cover
                    ))

                # Subnets
                elif line.startswith("+ SUBNET"):
                    subnet_name_id = gname_index.set(line.split()[2])
                    subnet = NetSubnet(subnet_name_id=subnet_name_id)
                    i += 1
                    while i < n:
                        subline = attr_lines[i].strip()
                        if subline.startswith("+ NONDEFAULTRULE"):
                            subnet.nondefaultrule = subline.split()[1]
                        elif re.match(r'\(\s*(.*?)\s*\)', subline):
                            conn_match = re.findall(r'\(\s*(.*?)\s*\)', subline)
                            for conn in conn_match:
                                tokens = conn.split()
                                if not tokens:
                                    continue
                                if tokens[0] == "PIN":
                                    pin_name_id = gname_index.set(tokens[1])
                                    subnet.connections.append(NetConnection(
                                        comp_name_id=None, pin_name_id=pin_name_id, is_pin=True
                                    ))
                                elif tokens[0] == "VPIN":
                                    vpin_name_id = gname_index.set(tokens[1])
                                    subnet.connections.append(NetConnection(
                                        comp_name_id=None, pin_name_id=None, is_pin=False, is_vpin=True, vpin_name_id=vpin_name_id
                                    ))
                                else:
                                    comp_name_id = gname_index.set(tokens[0])
                                    pin_name_id = gname_index.set(tokens[1])
                                    subnet.connections.append(NetConnection(
                                        comp_name_id=comp_name_id, pin_name_id=pin_name_id, is_pin=False
                                    ))
                        elif subline.startswith("NONDEFAULTRULE"):
                            subnet.nondefaultrule = subline.split()[1]
                        elif subline.startswith("ROUTED") or subline.startswith("FIXED") or subline.startswith("COVER"):
                            # Use similar logic as above to parse and append to subnet.wires
                            tokens = subline.split()
                            wire_type = tokens[0]
                            idx = 1
                            layer_id = None
                            mask = None
                            points = []
                            vias = []
                            rects = []
                            if idx < len(tokens) and tokens[idx] == "MASK":
                                mask = int(tokens[idx+1])
                                idx += 2
                            if idx < len(tokens):
                                layer_id = gname_index.set(tokens[idx])
                                idx += 1
                            while idx < len(tokens):
                                t = tokens[idx]
                                if t == "MASK":
                                    mask = int(tokens[idx+1])
                                    idx += 2
                                elif t == "RECT":
                                    rect = tuple(map(int, tokens[idx+1:idx+5]))
                                    rects.append(rect)
                                    idx += 5
                                elif re.match(r'^-?\d+$', t) and idx+1 < len(tokens) and re.match(r'^-?\d+$', tokens[idx+1]):
                                    pt = (int(tokens[idx]), int(tokens[idx+1]))
                                    points.append(pt)
                                    idx += 2
                                elif t.isidentifier():
                                    vias.append(t)
                                    idx += 1
                                else:
                                    idx += 1
                            subnet.wires.append(NetWire(
                                wire_type=wire_type,
                                layer=layer_id,
                                points=points,
                                vias=vias,
                                mask=mask,
                                rects=rects,
                                raw=subline
                            ))
                        elif subline.startswith("+") or subline == ";":
                            break
                        i += 1
                    net.subnets.append(subnet)

                # MUSTJOIN
                elif "MUSTJOIN" in line:
                    mj_match = re.findall(r'MUSTJOIN\s*\(\s*(\S+)\s+(\S+)\s*\)', line)
                    for comp, pin in mj_match:
                        comp_id = gname_index.set(comp)
                        pin_id = gname_index.set(pin)
                        net.mustjoin.append((comp_id, pin_id))

                # XTALK
                elif line.startswith("+ XTALK"):
                    net.xtalk_class = line.split()[2]

                # NONDEFAULTRULE
                elif line.startswith("+ NONDEFAULTRULE"):
                    net.nondefaultrule = line.split()[2]

                # SOURCE
                elif line.startswith("+ SOURCE"):
                    net.source = line.split()[2]

                # FIXEDBUMP
                elif line.startswith("+ FIXEDBUMP"):
                    net.fixedbump = True

                # FREQUENCY
                elif line.startswith("+ FREQUENCY"):
                    net.frequency = float(line.split()[2])

                # ORIGINAL
                elif line.startswith("+ ORIGINAL"):
                    net.original_net_id = gname_index.set(line.split()[2])

                # USE
                elif line.startswith("+ USE"):
                    net.use = line.split()[2]

                # PATTERN
                elif line.startswith("+ PATTERN"):
                    net.pattern = line.split()[2]

                # ESTCAP
                elif line.startswith("+ ESTCAP"):
                    net.estcap = float(line.split()[2])

                # WEIGHT
                elif line.startswith("+ WEIGHT"):
                    net.weight = float(line.split()[2])

                # PROPERTY (can be multiple in one line)
                elif line.startswith("+ PROPERTY"):
                    props = line.split()[2:]
                    for j in range(0, len(props), 2):
                        if j+1 < len(props):
                            net.properties[props[j]] = props[j+1]

                # ROUTED, FIXED, COVER, NOSHIELD, etc. (wiring info)
                elif line.startswith("+ ROUTED") or \
                    line.startswith("+ FIXED") or \
                    line.startswith("+ COVER") or \
                    line.startswith("+ NOSHIELD"):
                    # Parse wiring segment
                    tokens = line[1:].strip().split()  # Remove leading '+'
                    wire_type = tokens[0]
                    idx = 1
                    layer_id = None
                    mask = None
                    points = []
                    vias = []
                    rects = []
                    # Parse optional MASK
                    if idx < len(tokens) and tokens[idx] == "MASK":
                        mask = int(tokens[idx+1])
                        idx += 2
                    # Parse layer
                    if idx < len(tokens):
                        layer_id = gname_index.set(tokens[idx])
                        idx += 1
                    # Parse rest: points, vias, rects
                    while idx < len(tokens):
                        t = tokens[idx]
                        if t == "MASK":
                            mask = int(tokens[idx+1])
                            idx += 2
                        elif t == "RECT":
                            # RECT x1 y1 x2 y2
                            # Remove parentheses from tokens before converting to int
                            rect_tokens = [t for t in tokens[idx+1:idx+5] if t not in ('(', ')')]
                            rect = tuple(map(int, rect_tokens))
                            rects.append(rect)
                            idx += 5
                        elif re.match(r'^-?\d+$', t) and idx+1 < len(tokens) and re.match(r'^-?\d+$', tokens[idx+1]):
                            # Point (x y)
                            pt = (int(tokens[idx]), int(tokens[idx+1]))
                            points.append(pt)
                            idx += 2
                        elif t.isidentifier():
                            # VIA or VIRTUAL or other keyword
                            vias.append(t)
                            idx += 1
                        else:
                            idx += 1
                    net.wires.append(NetWire(
                        wire_type=wire_type,
                        layer=layer_id,
                        points=points,
                        vias=vias,
                        mask=mask,
                        rects=rects,
                        raw=line
                    ))

                i += 1

            self.def_data.nets[name_id] = net

        #except Exception as e:
        #    print(f"Error parsing net definition: {e}")


    def parse(self, def_file_content: str):
        lines = def_file_content.splitlines()
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue

            # Single-line sections
            if line.startswith("VERSION"):
                self.parse_version(line)
                i += 1
            elif line.startswith("DESIGN"):
                self.parse_design_name(line)
                i += 1
            elif line.startswith("UNITS"):
                self.parse_units(line)
                i += 1
            elif line.startswith("DIEAREA"):
                self.parse_diearea(line)
                i += 1
            elif line.startswith("ROW"):
                self.parse_row(line)
                i += 1
            elif line.startswith("TRACK"):
                self.parse_track(line)
                i += 1

            # Multi-line PROPERTYDEFINITIONS
            elif line.startswith("PROPERTYDEFINITIONS"):
                propdef_lines = []
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END PROPERTYDEFINITIONS"):
                        break
                    propdef_lines.append(l)
                    i += 1
                self.parse_property_definition(propdef_lines)
                i += 1

            # Multi-line sections
            elif line.startswith("VIAS"):
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END VIAS"):
                        break
                    if l.startswith("-"):
                        via_lines = []
                        while i < n:
                            l = lines[i].strip()
                            via_lines.append(l)
                            if l.endswith(";"):
                                break
                            i += 1
                        self.parse_via(via_lines)
                    i += 1
                i += 1

            elif line.startswith("COMPONENTS"):
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END COMPONENTS"):
                        break
                    if l.startswith("-"):
                        comp_lines = []
                        while i < n:
                            l = lines[i].strip()
                            comp_lines.append(l)
                            if l.endswith(";"):
                                break
                            i += 1
                        self.parse_component(comp_lines)
                    i += 1
                i += 1

            elif line.startswith("PINS"):
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END PINS"):
                        break
                    if l.startswith("-"):
                        pin_lines = []
                        while i < n:
                            l = lines[i].strip()
                            pin_lines.append(l)
                            if l.endswith(";"):
                                break
                            i += 1
                        self.parse_pin(pin_lines)
                    i += 1
                i += 1

            elif line.startswith("BLOCKAGES"):
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END BLOCKAGES"):
                        break
                    if l.startswith("-"):
                        blockage_lines = []
                        while i < n:
                            l = lines[i].strip()
                            blockage_lines.append(l)
                            if l.endswith(";"):
                                break
                            i += 1
                        self.parse_blockage(blockage_lines)
                    i += 1
                i += 1

            elif line.startswith("SPECIALNETS"):
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END SPECIALNETS"):
                        break
                    if l.startswith("-"):
                        specialnet_lines = []
                        while i < n:
                            l = lines[i].strip()
                            specialnet_lines.append(l)
                            if l.endswith(";"):
                                break
                            i += 1
                        self.parse_specialnet(specialnet_lines)
                    i += 1
                i += 1

            elif line.startswith("REGIONS"):
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END REGIONS"):
                        break
                    if l.startswith("-"):
                        region_lines = []
                        while i < n:
                            l = lines[i].strip()
                            region_lines.append(l)
                            if l.endswith(";"):
                                break
                            i += 1
                        self.parse_region(region_lines)
                    i += 1
                i += 1

            elif line.startswith("NETS"):
                i += 1
                while i < n:
                    l = lines[i].strip()
                    if l.startswith("END NETS"):
                        break
                    if l.startswith("-"):
                        net_lines = []
                        while i < n:
                            l = lines[i].strip()
                            net_lines.append(l)
                            if l.endswith(";"):
                                break
                            i += 1
                        self.parse_net(net_lines)
                    i += 1
                i += 1

            else:
                i += 1


class ParseWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

        self.num_threads = 10

    def merge_def_data(self, def_data_list):
        merged = DefData()

        for data in def_data_list:
            if merged.version_id is None and data.version_id is not None:
                merged.version_id = data.version_id
            if merged.design_name_id is None and data.design_name_id is not None:
                merged.design_name_id = data.design_name_id
            if merged.units is None and data.units is not None:
                merged.units = data.units
            if merged.diearea is None and data.diearea is not None:
                merged.diearea = data.diearea

            merged.rows.extend(data.rows)
            merged.tracks.extend(data.tracks)
            merged.nets.extend(data.nets)
            merged.vias.extend(data.vias)
            merged.regions.extend(data.regions)

            print(f"Merging {len(data.components)} components...")
            merged.components.extend(data.components)


            merged.pins.extend(data.pins)
            merged.blockages.extend(data.blockages)
            merged.specialnets.extend(data.specialnets)

            for k, v in data.property_definitions.items():
                if k not in merged.property_definitions:
                    merged.property_definitions[k] = v

        return merged


    @pyqtSlot()
    def run(self):
        with open(self.file_path, 'r') as def_file:
            def_file_content = def_file.read()

        if os.environ.get("DEF_READ_MT"):
            chunks = self.create_chunks(def_file_content, num_threads=self.num_threads)
            parsers = self.parse_in_threads(chunks)
            combined_parser = self.merge_parsers(parsers)
        else:
            print("Running DEF parser single thread...")
            parser = DefParser()
            parser.parse(def_file_content)
            combined_parser = parser

        self.finished.emit({
            "file_path": self.file_path,
            "parser": combined_parser
        })

    def create_chunks(self, def_file_content: str, num_threads: int) -> list:
        lines = def_file_content.splitlines()
        total_lines = len(lines)
        chunk_size = (total_lines + num_threads - 1) // num_threads

        section_keywords = ["COMPONENTS", "REGIONS", "SPECIALNETS", "NETS"]
        line_chunks = [
            lines[i * chunk_size:(i + 1) * chunk_size]
            for i in range(num_threads)
            if i * chunk_size < total_lines
        ]

        for i in range(1, len(line_chunks)):
            prev_chunk = line_chunks[i - 1]
            for line in reversed(prev_chunk):
                for section in section_keywords:
                    if section in line and not line.strip().startswith(f"END {section}"):
                        line_chunks[i].insert(0, section)
                        break
                else:
                    continue
                break

        return ['\n'.join(chunk) for chunk in line_chunks]

    def parse_in_threads(self, chunks: list) -> list:
        parsers = [DefParser() for _ in range(len(chunks))]
        threads = []

        def parse_chunk(index):
            parsers[index].parse(chunks[index])
            print(f"DEF parser {index} finished...")

        for i in range(len(chunks)):
            thread = threading.Thread(target=parse_chunk, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return parsers

    def merge_parsers(self, parsers: list):
        combined_parser = DefParser()
        combined_parser.def_data = self.merge_def_data([p.def_data for p in parsers])
        return combined_parser


    
class DefParserImplement(QObject):
    
    def_parser_finished_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        self.parser_dict = {}

        self.all_workers = []
        self.all_threads = []

    def parse(self, file_path):
        if file_path:
            worker = ParseWorker(file_path)
            thread = QThread()

            self.all_workers.append(worker)
            self.all_threads.append(thread)

            worker.moveToThread(thread)
            thread.started.connect(worker.run)

            worker.finished.connect(self.on_parse_finished)
            worker.finished.connect(thread.quit)
            thread.finished.connect(thread.deleteLater)
            thread.start()

            logging.info(f"Parse DEF {file_path} started...")

    def on_parse_finished(self, result):
        file_path = result["file_path"]
        parser = result["parser"]

        self.parser_dict[file_path] = parser

        logging.info(f"Parse DEF {file_path} finished.")

        self.def_parser_finished_signal.emit("DEF parser finished.")


    def get_via_names(self, layer):

        vnames = []
        venclosures = []

        for d, parser in self.parser_dict.items():
            vias = parser.def_data.vias

            for via in vias:

                if layer is None or layer in via.layer_ids:
                    vnames.append(via.name)
                    venclosures.append(via.enclosure)

        return {
            "name": vnames,
            "enclosure": venclosures
        }
    
    def get_unit(self):

        unit = 2000

        for d, parser in self.parser_dict.items():
            unit = parser.def_data.units.microns

        return unit
    
    def convert_to_micron(self, x, y):

        unit = self.get_unit()
        x = int(x)
        x_um = x / unit
        y = int(y)
        y_um = y / unit

        return (x_um, y_um)

    def get_components(self):
        all_components = {}
        for d, parser in self.parser_dict.items():
            components = parser.def_data.components
            all_components.update(components)
        return all_components
    
    def get_nets(self):
        all_nets = {}
        for d, parser in self.parser_dict.items():
            nets = parser.def_data.nets
            all_nets.update(nets)
        return all_nets

    def get_wires_of_net(self, net_name, layer_id=None):
        wires = []
        for d, parser in self.parser_dict.items():
            net = parser.def_data.nets.get(net_name)
            if net:
                for wire in net.wires:
                    if layer_id is None or wire.layer == layer_id:
                        wires.append(wire)
        return wires


    def get_layers_of_net(self, net_name):
        layers = set()
        for d, parser in self.parser_dict.items():
            net = parser.def_data.nets.get(net_name)
            if net:
                for wire in net.wires:
                    if wire.layer is not None:
                        layers.add(wire.layer)
        return list(layers)

    def get_wire_rects(self, wire):
        rects = []
        rects.extend(wire.rects)

        #for rect in rects:
        #    (x1, y1, x2, y2) = rect
        #    x1, y1 = self.convert_to_micron(x1, y1)
        #    x2, y2 = self.convert_to_micron(x2, y2)
        #    rects[rects.index(rect)] = (x1, y1, x2, y2)

        return rects
    


