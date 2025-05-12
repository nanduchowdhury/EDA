
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot

import json
import re

import threading
import logging


class DefParser:
    def __init__(self):
        self.design_data = {}

    def parse(self, def_file_content):
        lines = def_file_content.splitlines()
        current_section = None
        section_content = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines or comment lines
            if not line or line.startswith("#"):
                continue
            
            # Section parsing
            if line.startswith("VERSION"):
                self._parse_version(line)
            elif line.startswith("DESIGN"):
                self._parse_design(line)
            elif line.startswith("UNITS"):
                self._parse_units(line)
            elif line.startswith("PROPERTYDEFINITIONS"):
                current_section = "PROPERTYDEFINITIONS"
            elif line.startswith("DIEAREA"):
                self._parse_diearea(line)
            elif line.startswith("ROW"):
                self._parse_row(line)
            elif line.startswith("TRACKS"):
                self._parse_tracks(line)
            elif line.startswith("VIAS"):
                current_section = "VIAS"
            elif line.startswith("NETS"):
                current_section = "NETS"
            elif line.startswith("REGIONS"):
                current_section = "REGIONS"
            elif line.startswith("COMPONENTS"):
                current_section = "COMPONENTS"
            elif line.startswith("PINS"):
                current_section = "PINS"
            elif line.startswith("BLOCKAGES"):
                current_section = "BLOCKAGES"
            elif line.startswith("SPECIALNETS"):
                current_section = "SPECIALNETS"
            elif current_section:
                section_content.append(line)
            
            if line == "END PROPERTYDEFINITIONS":
                self._parse_property_definitions(section_content)
                section_content = []
            elif line == "END VIAS":
                self._parse_vias(section_content)
                section_content = []
            elif line == "END NETS":
                self._parse_nets(section_content)
                section_content = []
            elif line == "END REGIONS":
                self._parse_regions(section_content)
                section_content = []
            elif line == "END COMPONENTS":
                self._parse_components(section_content)
                section_content = []
            elif line == "END PINS":
                self._parse_pins(section_content)
                section_content = []
            elif line == "END BLOCKAGES":
                self._parse_blockages(section_content)
                section_content = []
            elif line == "END SPECIALNETS":
                self._parse_specialnets(section_content)
                section_content = []

        return self.design_data

    def _parse_version(self, line):
        self.design_data["version"] = line.split(" ")[1]

    def _parse_design(self, line):
        self.design_data["design_name"] = line.split(" ")[1]

    def _parse_units(self, line):
        units = line.split(" ")
        self.design_data["units"] = {"distance": units[2], "microns": int(units[3])}

    def _parse_diearea(self, line):
        diearea_coords = re.findall(r'\d+', line)
        self.design_data["diearea"] = {"ll_x": int(diearea_coords[0]), "ll_y": int(diearea_coords[1]),
                                       "ur_x": int(diearea_coords[2]), "ur_y": int(diearea_coords[3])}

    def _parse_row(self, line):

        try:
            row_data = re.split(r'\s+', line.strip())
            self.design_data.setdefault("rows", []).append({
                "name": row_data[1],
                "type": row_data[2],
                "x": int(row_data[3]),
                "y": int(row_data[4]),
                "orientation": row_data[5],
                "step": (int(row_data[7]), int(row_data[9]), int(row_data[11]))
            })

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_nets(self, section_content):
        try:
            nets = []
            current_net = None

            for line in section_content:
                line = line.strip()
                if line.startswith("- "):
                    if current_net:
                        nets.append(current_net)
                    net_name = line[2:].strip()
                    current_net = {"name": net_name, "connections": []}
                elif line.startswith("(") and current_net is not None:
                    matches = re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)', line)
                    for cell_pin in matches:
                        if cell_pin[0] == "PIN":
                            current_net["connections"].append({
                                "pin": cell_pin[1]
                            })
                        else:
                            current_net["connections"].append({
                                "cell": cell_pin[0],
                                "pin": cell_pin[1]
                            })
                elif line == ";" and current_net:
                    pass  # End of net definition

            if current_net:
                nets.append(current_net)

            self.design_data["nets"] = nets

        except Exception as e:
            logging.error(f"DEF parser error in NETS section: {e}")

    def _parse_tracks(self, line):

        try:
            track_data = re.split(r'\s+', line.strip())
            track = {
                "direction": track_data[1],
                "step": int(track_data[6]),
                "layer": track_data[8]
            }
            self.design_data.setdefault("tracks", []).append(track)

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_vias(self, section_content):

        line = ''
        try:
            vias = []
            current_via = {}
            
            for line in section_content:
                line = line.strip()
                if line.startswith("- "):
                    if current_via:
                        vias.append(current_via)
                    current_via = {"name": line[2:].strip()}
                elif line.startswith("+ "):
                    tokens = line[2:].strip().split()
                    if tokens[0] == "VIARULE":
                        current_via["via_rule"] = tokens[1]
                    elif tokens[0] == "CUTSIZE":
                        current_via["cut_size"] = (int(tokens[1]), int(tokens[2]))
                    elif tokens[0] == "LAYERS":
                        current_via["layers"] = tokens[1:]
                    elif tokens[0] == "CUTSPACING":
                        current_via["cut_spacing"] = (int(tokens[1]), int(tokens[2]))
                    elif tokens[0] == "ENCLOSURE":
                        current_via["enclosure"] = (int(tokens[1]), int(tokens[2]), int(tokens[3]), int(tokens[4]))
                    elif tokens[0] == "ROWCOL":
                        current_via["row_col"] = (int(tokens[1]), int(tokens[2]))

            if current_via:
                vias.append(current_via)

            self.design_data["vias"] = vias

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_regions(self, section_content):

        line = ''
        try:   
            regions = []
            
            for line in section_content:
                if line.startswith("- "):
                    region_data = re.findall(r'\d+', line)
                    region = {
                        "name": line[2:].split(" ")[0],
                        "coordinates": [(int(region_data[i]), int(region_data[i+1])) for i in range(0, len(region_data), 2)]
                    }
                    regions.append(region)

            self.design_data["regions"] = regions

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_components(self, section_content):

        line = ''
        try:
            components = []

            for line in section_content:
                if line.startswith("- "):
                    component_data = line[2:].split(" ")

                    inst_name = component_data[0]
                    cell_name = component_data[1]
                    type = ''
                    location_x = ''
                    location_y = ''

                    plus_data = line.split(" + ")

                    for item in plus_data:

                        type = ''
                        if item.startswith("COVER"):
                            type = "COVER"
                        elif item.startswith("FIXED"):
                            type = "FIXED"
                        elif item.startswith("PLACED"):
                            type = "PLACED"

                        if type:
                            tokens = item.split((" "))
                            location_x = tokens[2]
                            location_y = tokens[3]


                    component = {
                        "cell_name": cell_name,
                        "inst_name": inst_name,
                        "type": type,
                        "location": (location_x, location_y)
                    }
                    components.append(component)

            self.design_data["components"] = components

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_pins(self, section_content):

        line = ''
        try:
            pins = []
            
            for line in section_content:
                if line.startswith("- "):
                    pin_data = re.split(r'\s+', line[2:].strip())
                    pin = {
                        "name": pin_data[0],
                        "net": pin_data[2],
                        "direction": pin_data[4],
                        "use": pin_data[6]
                    }
                    pins.append(pin)

            self.design_data["pins"] = pins

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_blockages(self, section_content):

        line = ''
        try:
            blockages = []
            
            for line in section_content:
                if line.startswith("- "):
                    coords = re.findall(r'\d+', line)
                    blockage = {
                        "ll_x": int(coords[0]),
                        "ll_y": int(coords[1]),
                        "ur_x": int(coords[2]),
                        "ur_y": int(coords[3])
                    }
                    blockages.append(blockage)

            self.design_data["blockages"] = blockages

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_specialnets(self, section_content):

        line = ''
        try:
            specialnets = []
            
            for line in section_content:
                if line.startswith("- "):
                    net_data = re.findall(r'\S+', line[2:])
                    specialnet = {
                        "name": net_data[0],
                        "components": net_data[1:]
                    }
                    specialnets.append(specialnet)

            self.design_data["specialnets"] = specialnets
        
        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    def _parse_property_definitions(self, section_content):

        line = ''
        try:
            properties = {}
            
            for line in section_content:
                if line.startswith("DESIGN"):
                    parts = line.split(" ", 2)
                    properties[parts[1]] = parts[2]

            self.design_data["property_definitions"] = properties

        except Exception as e:
            logging.error("DEF parser error in line : {line}")
            logging.error({e})

    
class ParseWorker(QObject):
    finished = pyqtSignal(dict)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    @pyqtSlot()
    def run(self):
        parser = DefParser()

        with open(self.file_path, 'r') as def_file:
            def_file_content = def_file.read()

        def_dict = parser.parse(def_file_content)
        
        # json_data = json.dumps(def_dict, indent=4)
        # print(json_data)

        self.finished.emit(def_dict)

class DefParserImplement():
    def __init__(self):

        self.def_file_path = ''
        self.def_dict = {}

    def setDefFile(self, file_path):
        self.def_file_path = file_path

    def execute(self):

        if self.def_file_path:
            self.selectedFile = self.def_file_path

            self.worker = ParseWorker(self.def_file_path)
            self.thread = QThread()

            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)

            self.worker.finished.connect(self.on_parse_finished)
            self.worker.finished.connect(self.thread.quit)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.start()

            logging.info("DEF parser started...")


    def on_parse_finished(self, def_dict):

        self.def_dict = def_dict
        json_data = json.dumps(def_dict, indent=4)

        # print(json_data)
        # print(self.def_dict)
        logging.info("DEF parser finished.")

    def get_via_names(self, layer):

        result = []
        vias = self.def_dict.get("vias", [])
        if not layer:
            result = [via.get("name") for via in vias]
        result = [via.get("name") for via in vias if layer in via.get("layers", [])]

        return result
    
    def get_instances_coords(self):

        components = self.def_dict.get("components", [])

        inst_list = []
        coord_list = []

        for comp in components:
            inst_name = comp.get("inst_name")
            location = comp.get("location")

            if inst_name is not None and isinstance(location, (list, tuple)) and len(location) == 2:
                inst_list.append(inst_name)
                coord_list.append(f"({location[0]} {location[1]})")

        return {
            "inst": inst_list,
            "coords": coord_list
        }



