
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot

import json
import re

import threading
import logging


from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import re

@dataclass
class Units:
    distance: str
    microns: int

@dataclass
class DieArea:
    ll_x: int
    ll_y: int
    ur_x: int
    ur_y: int

@dataclass
class Row:
    name: str
    type: str
    x: int
    y: int
    orientation: str
    step: Tuple[int, int, int]

@dataclass
class Track:
    direction: str
    step: int
    layer: str

@dataclass
class Connection:
    cell: Optional[str] = None
    pin: str = ""

@dataclass
class Net:
    name: str
    connections: List[Connection]

@dataclass
class Via:
    name: str
    via_rule: Optional[str] = None
    cut_size: Optional[Tuple[int, int]] = None
    layers: List[str] = field(default_factory=list)
    cut_spacing: Optional[Tuple[int, int]] = None
    enclosure: Optional[Tuple[int, int, int, int]] = None
    row_col: Optional[Tuple[int, int]] = None

@dataclass
class Region:
    name: str
    coordinates: List[Tuple[int, int]]

@dataclass
class Component:
    inst_name: str
    cell_name: str
    type: str
    location: Tuple[int, int]

@dataclass
class Pin:
    name: str
    net: str
    direction: str
    use: str

@dataclass
class Blockage:
    ll_x: int
    ll_y: int
    ur_x: int
    ur_y: int

@dataclass
class SpecialNet:
    name: str
    components: List[str]

@dataclass
class DefData:
    version: Optional[str] = None
    design_name: Optional[str] = None
    units: Optional[Units] = None
    diearea: Optional[DieArea] = None
    rows: List[Row] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    nets: List[Net] = field(default_factory=list)
    vias: List[Via] = field(default_factory=list)
    regions: List[Region] = field(default_factory=list)
    components: List[Component] = field(default_factory=list)
    pins: List[Pin] = field(default_factory=list)
    blockages: List[Blockage] = field(default_factory=list)
    specialnets: List[SpecialNet] = field(default_factory=list)
    property_definitions: Dict[str, str] = field(default_factory=dict)

class DefParser:
    def __init__(self):
        self.def_data = DefData()

    def parse_version(self, line: str):
        if line.startswith("VERSION"):
            self.def_data.version = line.split()[1]

    def parse_design_name(self, line: str):
        if line.startswith("DESIGN"):
            self.def_data.design_name = line.split()[1].strip(";")

    def parse_units(self, line: str):
        line = line.rstrip(';').strip()  # Remove trailing semicolon and surrounding whitespace
        if line.startswith("UNITS"):
            parts = line.split()
            if "MICRONS" in parts:
                self.def_data.units = Units(distance="MICRONS", microns=int(parts[-1]))

    def parse_diearea(self, line: str):
        if line.startswith("DIEAREA"):
            coords = list(map(int, re.findall(r'\d+', line)))
            self.def_data.diearea = DieArea(*coords)

    def parse_row(self, line: str):
        parts = line.split()
        name = parts[1]
        type = parts[2]
        x = int(parts[3])
        y = int(parts[4])
        orientation = parts[5]
        step = tuple(map(int, re.findall(r'\d+', ' '.join(parts[6:]))))
        self.def_data.rows.append(Row(name, type, x, y, orientation, step))

    def parse_track(self, line: str):
        parts = line.split()
        direction = parts[1]
        step = int(parts[6])
        layer = parts[-1]
        self.def_data.tracks.append(Track(direction, step, layer))

    def parse_via(self, lines: List[str]):
        name = lines[0].split()[1]
        via = Via(name)
        for line in lines[1:]:
            if line.startswith("+ CUT"):
                via.cut_size = tuple(map(int, re.findall(r'\d+', line)))
            elif line.startswith("+ LAYER"):
                via.layers.append(line.split()[2])
            elif line.startswith("+ SPACING"):
                via.cut_spacing = tuple(map(int, re.findall(r'\d+', line)))
            elif line.startswith("+ ENCLOSURE"):
                via.enclosure = tuple(map(int, re.findall(r'\d+', line)))
            elif line.startswith("+ ROWCOL"):
                via.row_col = tuple(map(int, re.findall(r'\d+', line)))
        self.def_data.vias.append(via)


    def parse_component(self, line: str):
        # Remove trailing semicolon if present
        line = line.rstrip(';')

        parts = line.split()
        inst_name = parts[1]
        cell_name = parts[2]
        placement_type = parts[3] if '+' not in parts[3] else parts[4]  # handle optional '+'

        # Extract the coordinates from the line using regex
        coords = re.findall(r'\(\s*(\d+)\s+(\d+)\s*\)', line)
        if coords:
            x, y = map(int, coords[0])
        else:
            x, y = 0, 0

        self.def_data.components.append(Component(inst_name, cell_name, placement_type, (x, y)))


    def parse_pin(self, line: str):
        parts = line.split()
        name = parts[1]
        net = parts[-1]
        direction = "INPUT"
        use = "SIGNAL"
        self.def_data.pins.append(Pin(name, net, direction, use))

    def parse_blockage(self, line: str):
        coords = list(map(int, re.findall(r'\d+', line)))
        if len(coords) == 4:
            self.def_data.blockages.append(Blockage(*coords))

    def parse_property_definition(self, line: str):
        match = re.match(r'PROPERTYDEFINITIONS\s+(\w+)\s+(\w+)', line)
        if match:
            self.def_data.property_definitions[match.group(1)] = match.group(2)

    def parse_specialnet(self, lines: List[str]):
        name = lines[0].split()[1]
        components = []
        for line in lines[1:]:
            comps = re.findall(r'\( (.*?) \)', line)
            components.extend(comps)
        self.def_data.specialnets.append(SpecialNet(name=name, components=components))

    def parse_region(self, line: str):
        match = re.findall(r'(\S+)\s+\(\s*(\d+)\s+(\d+)\s*\)', line)
        if match:
            name = match[0][0]
            coordinates = [(int(x), int(y)) for _, x, y in match]
            self.def_data.regions.append(Region(name=name, coordinates=coordinates))

    def parse_net(self, lines: List[str]):
        name = lines[0].split()[1]
        connections = []
        for line in lines[1:]:
            tokens = re.findall(r'\( (\S+) (\S+) \)', line)
            for cell, pin in tokens:
                connections.append(Connection(cell=cell, pin=pin))
        self.def_data.nets.append(Net(name=name, connections=connections))

    def parse(self, def_file_content: str):
        lines = def_file_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue

            if line.startswith("VERSION"):
                self.parse_version(line)
            elif line.startswith("DESIGN"):
                self.parse_design_name(line)
            elif line.startswith("UNITS"):
                self.parse_units(line)
            elif line.startswith("DIEAREA"):
                self.parse_diearea(line)
            elif line.startswith("ROW"):
                self.parse_row(line)
            elif line.startswith("TRACK"):
                self.parse_track(line)
            elif line.startswith("VIA"):
                via_lines = [line]
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("END"):
                    via_lines.append(lines[i].strip())
                    i += 1
                self.parse_via(via_lines)
            elif line.startswith("COMPONENTS"):
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith("END COMPONENTS"):
                        break
                    if line.startswith("-"):
                        self.parse_component(line)
                    i += 1
            elif line.startswith("PIN"):
                self.parse_pin(line)
            elif line.startswith("BLOCKAGE"):
                self.parse_blockage(line)
            elif line.startswith("PROPERTYDEFINITIONS"):
                self.parse_property_definition(line)
            elif line.startswith("SPECIALNETS"):
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith("END SPECIALNETS"):
                        break
                    if line.startswith("-"):
                        specialnet_lines = [line]
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith("+"):
                            specialnet_lines.append(lines[i].strip())
                            i += 1
                        self.parse_specialnet(specialnet_lines)
                    else:
                        i += 1
            elif line.startswith("REGIONS"):
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith("END REGIONS"):
                        break
                    self.parse_region(line)
                    i += 1
            elif line.startswith("NETS"):
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith("END NETS"):
                        break
                    if line.startswith("-"):
                        net_lines = [line]
                        i += 1
                        while i < len(lines) and not lines[i].strip().startswith("+"):
                            net_lines.append(lines[i].strip())
                            i += 1
                        self.parse_net(net_lines)
                    else:
                        i += 1

            i += 1


class ParseWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    @pyqtSlot()
    def run(self):
        with open(self.file_path, 'r') as def_file:
            def_file_content = def_file.read()

        parser = DefParser()
        parser.parse(def_file_content)
        
        # Emit a dictionary with keys for clarity
        self.finished.emit({"file_path": self.file_path, "parser": parser})

    
class DefParserImplement:
    def __init__(self):

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

    
    def get_via_names(self, layer):
        result = []

        for d, parser in self.parser_dict.items():
            vias = parser.def_data.vias

            for via in vias:
                if layer is None or layer in via.layers:
                    result.append(via.name)

        return result
    
    def get_unit(self):

        unit = 2000

        for d, parser in self.parser_dict.items():
            unit = parser.def_data.units.microns

        return unit

    def get_components(self):

        all_components = []
        for d, parser in self.parser_dict.items():
            components = parser.def_data.components

            all_components.extend(components)

        return all_components
    
    def get_instances_coords(self):

        inst_list = []
        coord_list = []

        for d, parser in self.parser_dict.items():
            components = parser.def_data.components

            i_list = [comp.inst_name for comp in components]
            c_list = [f"({comp.location[0]} {comp.location[1]})" for comp in components]

            inst_list.extend(i_list)
            coord_list.extend(c_list)

        return {
            "inst": inst_list,
            "coords": coord_list
        }



