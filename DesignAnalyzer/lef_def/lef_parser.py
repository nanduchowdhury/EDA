import json

import logging

import re
from collections import defaultdict

from collections import defaultdict
import re

# Define compact __slots__ structs

class Foreign:
    __slots__ = ('name', 'coords')
    def __init__(self, name, coords):
        self.name = name
        self.coords = coords

class PinPort:
    __slots__ = ('layer_rects',)
    def __init__(self, layer_rects):
        self.layer_rects = layer_rects

class Antenna:
    __slots__ = ('type', 'value', 'layer')
    def __init__(self, type, value, layer):
        self.type = type
        self.value = value
        self.layer = layer

class Pin:
    __slots__ = ('direction', 'use', 'antenna', 'groundsensitivity', 'supplysensitivity', 'ports')
    def __init__(self):
        self.direction = None
        self.use = None
        self.antenna = []
        self.groundsensitivity = None
        self.supplysensitivity = None
        self.ports = []

class Macro:
    __slots__ = ('name', 'raw', 'class_', 'origin', 'foreign', 'size', 'symmetry', 'site', 'pins', 'obs')
    def __init__(self, name, raw):
        self.name = name
        self.raw = raw
        self.class_ = None
        self.origin = []
        self.foreign = None
        self.size = []
        self.symmetry = []
        self.site = None
        self.pins = {}  # pin_name -> Pin
        self.obs = {}  # layer -> list of rects

class LefParser:
    def __init__(self, lef_text):
        self.text = lef_text
        self.sites = {}  # site_name -> raw block
        self.macros = {}  # macro_name -> Macro
        self.layers = {}  # layer_name -> raw block
        self.vias = {}  # via_name -> {raw, layers}
        self.via_rules = {}  # rule_name -> raw block
        self.property_definitions = {}
        self._parse()

    def _parse(self):
        self._parse_sites()
        self._parse_macros()
        self._parse_layers()
        self._parse_vias()
        self._parse_via_rules()
        self._parse_property_definitions()

    def _extract_blocks(self, keyword):
        pattern = re.compile(rf'{keyword} .*?END {keyword}', re.DOTALL | re.IGNORECASE)
        return pattern.findall(self.text)

    def _parse_sites(self):
        for block in self._extract_blocks("SITE"):
            site_name = block.strip().splitlines()[0].split()[1]
            self.sites[site_name] = block

    def _parse_macros(self):
        pattern = re.compile(r'MACRO (.*?)\n(.*?)END\s+\1', re.DOTALL | re.IGNORECASE)
        for match in pattern.finditer(self.text):
            name, content = match.group(1).strip(), match.group(2).strip()
            macro = Macro(name, content)
            macro.class_ = self._extract_macro_field(content, "CLASS")
            macro.origin = self._extract_macro_coords(content, "ORIGIN")
            macro.foreign = self._extract_macro_foreign(content)
            macro.size = self._extract_macro_size(content)
            macro.symmetry = self._extract_macro_list_field(content, "SYMMETRY")
            macro.site = self._extract_macro_field(content, "SITE")
            macro.pins = self._parse_macro_pins(content)
            macro.obs = self._parse_macro_obs(content)
            self.macros[name] = macro

    def _extract_macro_field(self, content, keyword):
        match = re.search(rf'{keyword} (.*?);', content)
        return match.group(1).strip() if match else None

    def _extract_macro_coords(self, content, keyword):
        match = re.search(rf'{keyword} (-?\d+\.?\d*) (-?\d+\.?\d*) ;', content)
        return list(map(float, match.groups())) if match else []

    def _extract_macro_foreign(self, content):
        match = re.search(r'FOREIGN (\S+) (-?\d+\.?\d*) (-?\d+\.?\d*) ;', content)
        if match:
            return Foreign(match.group(1), [float(match.group(2)), float(match.group(3))])
        return None

    def _extract_macro_size(self, content):
        match = re.search(r'SIZE (-?\d+\.?\d*) BY (-?\d+\.?\d*) ;', content)
        return list(map(float, match.groups())) if match else []

    def _extract_macro_list_field(self, content, keyword):
        match = re.search(rf'{keyword} (.*?);', content)
        return match.group(1).strip().split() if match else []

    def _parse_macro_pins(self, content):
        pins = {}
        pin_pattern = re.compile(r'PIN (.*?)\n(.*?)END\s+\1', re.DOTALL | re.IGNORECASE)
        for match in pin_pattern.finditer(content):
            pin_name, pin_content = match.group(1).strip(), match.group(2).strip()
            pin = self._parse_pin_block(pin_content)
            pins[pin_name] = pin
        return pins

    def _parse_pin_block(self, content):
        pin = Pin()
        pin.direction = self._extract_macro_field(content, "DIRECTION")
        pin.use = self._extract_macro_field(content, "USE")
        pin.groundsensitivity = self._extract_macro_field(content, "GROUNDSENSITIVITY")
        pin.supplysensitivity = self._extract_macro_field(content, "SUPPLYSENSITIVITY")

        for line in content.splitlines():
            if line.startswith("ANTENNA"):
                tokens = line.strip(';').split()
                if len(tokens) >= 3:
                    pin.antenna.append(Antenna(tokens[0], float(tokens[1]), tokens[-1]))

        port_pattern = re.compile(r'PORT\s*(.*?)END', re.DOTALL | re.IGNORECASE)
        for port_match in port_pattern.finditer(content):
            port_data = self._extract_layer_rects(port_match.group(1))
            pin.ports.append(PinPort(port_data))

        return pin

    def _parse_macro_obs(self, content):
        match = re.search(r'OBS\s*(.*?)END', content, re.DOTALL | re.IGNORECASE)
        return self._extract_layer_rects(match.group(1).strip()) if match else {}

    def _extract_layer_rects(self, content):
        layer_blocks = defaultdict(list)
        current_layer = None
        for line in content.splitlines():
            if line.startswith("LAYER"):
                current_layer = line.split()[1]
            elif line.startswith("RECT") and current_layer:
                coords = list(map(float, re.findall(r'-?\d+\.?\d*', line)))
                layer_blocks[current_layer].append(coords)
        return dict(layer_blocks)

    def _parse_layers(self):
        for block in self._extract_blocks("LAYER"):
            layer_name = block.strip().splitlines()[0].split()[1]
            self.layers[layer_name] = block

    def _parse_vias(self):
        for block in self._extract_blocks("VIA"):
            lines = block.strip().splitlines()
            via_name = lines[0].split()[1]
            self.vias[via_name] = {
                "raw": block,
                "layers": self._extract_layer_rects("\n".join(lines[1:]))
            }

    def _parse_via_rules(self):
        for block in self._extract_blocks("VIARULE"):
            rule_name = block.strip().splitlines()[0].split()[1]
            self.via_rules[rule_name] = block

    def _parse_property_definitions(self):
        match = re.search(r'PROPERTYDEFINITIONS(.*?)END PROPERTYDEFINITIONS', self.text, re.DOTALL | re.IGNORECASE)
        if match:
            for line in match.group(1).strip().splitlines():
                tokens = line.strip().split()
                if len(tokens) >= 3:
                    key = f"{tokens[0]} {tokens[1]}"
                    value = " ".join(tokens[2:])
                    self.property_definitions[key] = value

    # Accessors
    def get_sites(self): return self.sites
    def get_macros(self): return self.macros
    def get_layers(self): return self.layers
    def get_vias(self): return self.vias
    def get_via_rules(self): return self.via_rules
    def get_property_definitions(self): return self.property_definitions

    

class LefParserImplement:
    def __init__(self):

        self.parser_dict = {}

    def parse(self, file_path):
        if file_path:
            with open(file_path, 'r') as f:
                lef_text = f.read()
                lefParser = LefParser(lef_text)
                self.parser_dict[file_path] = lefParser

    def get_macro(self, cell_name):
        for l, parser in self.parser_dict.items():
            macros = parser.get_macros()
            if cell_name in macros:
                return macros[cell_name]
            
        return None
    


