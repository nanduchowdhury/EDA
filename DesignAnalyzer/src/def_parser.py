
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot, pyqtSignal

import json
import re

import os
import threading
import logging


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
    ll_x: int
    ll_y: int
    ur_x: int
    ur_y: int

@dataclass
class Row:
    name_id: int
    type_id: int
    x: int
    y: int
    orientation_id: int
    step: Tuple[int, int, int]

@dataclass
class Track:
    direction_id: int
    step: int
    layer_id: int

@dataclass
class Connection:
    cell_id: Optional[int] = None
    pin_id: int = 0

@dataclass
class Net:
    name_id: int
    connections: List[Connection]

@dataclass
class Via:
    name_id: int
    via_rule_id: Optional[int] = None
    cut_size: Optional[Tuple[int, int]] = None
    layer_ids: List[int] = field(default_factory=list)
    cut_spacing: Optional[Tuple[int, int]] = None
    enclosure: Optional[Tuple[int, int, int, int]] = None
    row_col: Optional[Tuple[int, int]] = None

@dataclass
class Region:
    name_id: int
    coordinates: List[Tuple[int, int]]

@dataclass
class Component:
    inst_name_id: int
    cell_name_id: int
    type_id: int
    location: Tuple[int, int]

@dataclass
class Pin:
    name_id: int
    net_id: int
    direction_id: int
    use_id: int

@dataclass
class Blockage:
    ll_x: int
    ll_y: int
    ur_x: int
    ur_y: int

@dataclass
class SpecialNet:
    name_id: int
    component_ids: List[int]

@dataclass
class DefData:
    version_id: Optional[int] = None
    design_name_id: Optional[int] = None
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
        coords = list(map(int, re.findall(r'\d+', line)))
        self.def_data.diearea = DieArea(*coords)

    def parse_row(self, line: str):
        parts = line.split()
        name_id = gname_index.set(parts[1])
        type_id = gname_index.set(parts[2])
        x, y = int(parts[3]), int(parts[4])
        orientation_id = gname_index.set(parts[5])
        step = tuple(map(int, re.findall(r'\d+', ' '.join(parts[6:]))))
        self.def_data.rows.append(Row(name_id, type_id, x, y, orientation_id, step))

    def parse_track(self, line: str):
        parts = line.split()
        direction_id = gname_index.set(parts[1])
        step = int(parts[6])
        layer_id = gname_index.set(parts[-1])
        self.def_data.tracks.append(Track(direction_id, step, layer_id))

    def parse_via(self, lines: List[str]):
        name_id = gname_index.set(lines[0].split()[1])
        via = Via(name_id)
        for line in lines[1:]:
            if line.startswith("+ CUT"):
                via.cut_size = tuple(map(int, re.findall(r'\d+', line)))
            elif line.startswith("+ LAYER"):
                via.layer_ids.append(gname_index.set(line.split()[2]))
            elif line.startswith("+ SPACING"):
                via.cut_spacing = tuple(map(int, re.findall(r'\d+', line)))
            elif line.startswith("+ ENCLOSURE"):
                via.enclosure = tuple(map(int, re.findall(r'\d+', line)))
            elif line.startswith("+ ROWCOL"):
                via.row_col = tuple(map(int, re.findall(r'\d+', line)))
        self.def_data.vias.append(via)

    def parse_component(self, line: str):
        try:

            line = line.rstrip(';')
            parts = line.split()
            inst_id = gname_index.set(parts[1])
            cell_id = gname_index.set(parts[2])
            type_str = parts[3] if '+' not in parts[3] else parts[4]
            type_id = gname_index.set(type_str)
            coords = re.findall(r'\(\s*(\d+)\s+(\d+)\s*\)', line)
            x, y = map(int, coords[0]) if coords else (0, 0)
            self.def_data.components.append(Component(inst_id, cell_id, type_id, (x, y)))

        except Exception as e:
            print(f"Error DEF parsing : line : {line}")

    def parse_pin(self, line: str):
        parts = line.split()
        name_id = gname_index.set(parts[1])
        net_id = gname_index.set(parts[-1])
        direction_id = gname_index.set("INPUT")
        use_id = gname_index.set("SIGNAL")
        self.def_data.pins.append(Pin(name_id, net_id, direction_id, use_id))

    def parse_blockage(self, line: str):
        coords = list(map(int, re.findall(r'\d+', line)))
        if len(coords) == 4:
            self.def_data.blockages.append(Blockage(*coords))

    def parse_property_definition(self, line: str):
        match = re.match(r'PROPERTYDEFINITIONS\s+(\w+)\s+(\w+)', line)
        if match:
            key_id = gname_index.set(match.group(1))
            value_id = gname_index.set(match.group(2))
            self.def_data.property_definitions[key_id] = value_id

    def parse_specialnet(self, lines: List[str]):
        name_id = gname_index.set(lines[0].split()[1])
        component_ids = []
        for line in lines[1:]:
            comps = re.findall(r'\( (.*?) \)', line)
            component_ids.extend(gname_index.set(c) for c in comps)
        self.def_data.specialnets.append(SpecialNet(name_id=name_id, component_ids=component_ids))

    def parse_region(self, line: str):
        match = re.findall(r'(\S+)\s+\(\s*(\d+)\s+(\d+)\s*\)', line)
        if match:
            name_id = gname_index.set(match[0][0])
            coordinates = [(int(x), int(y)) for _, x, y in match]
            self.def_data.regions.append(Region(name_id=name_id, coordinates=coordinates))

    def parse_net(self, lines: List[str]):
        name_id = gname_index.set(lines[0].split()[1])
        connections = []
        for line in lines[1:]:
            tokens = re.findall(r'\( (\S+) (\S+) \)', line)
            for cell, pin in tokens:
                cell_id = gname_index.set(cell)
                pin_id = gname_index.set(pin)
                connections.append(Connection(cell_id, pin_id))
        self.def_data.nets.append(Net(name_id=name_id, connections=connections))

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

            i_list = [gname_index.getName(comp.inst_name_id) for comp in components]
            c_list = [f"({comp.location[0]} {comp.location[1]})" for comp in components]

            inst_list.extend(i_list)
            coord_list.extend(c_list)

        return {
            "inst": inst_list,
            "coords": coord_list
        }



