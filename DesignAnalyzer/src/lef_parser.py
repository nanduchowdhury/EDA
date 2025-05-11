import json

import logging

import re
from collections import defaultdict

class LefParser:
    def __init__(self, lef_text):
        self.text = lef_text
        self.sections = defaultdict(list)
        self.macros = {}
        self.sites = {}
        self.layers = {}
        self.vias = {}
        self.via_rules = {}
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
            lines = block.strip().splitlines()
            site_name = lines[0].split()[1]
            self.sites[site_name] = {"raw": block}

    def _parse_macros(self):
        pattern = re.compile(r'MACRO (.*?)\n(.*?)END\s+\1', re.DOTALL | re.IGNORECASE)
        for match in pattern.finditer(self.text):
            name = match.group(1).strip()
            content = match.group(2).strip()
            self.macros[name] = {
                "raw": content,
                "class": self._extract_macro_field(content, "CLASS"),
                "origin": self._extract_macro_coords(content, "ORIGIN"),
                "foreign": self._extract_macro_foreign(content),
                "size": self._extract_macro_size(content),
                "symmetry": self._extract_macro_list_field(content, "SYMMETRY"),
                "site": self._extract_macro_field(content, "SITE"),
                "pins": self._parse_macro_pins(content),
                "obs": self._parse_macro_obs(content)
            }

    def _extract_macro_field(self, content, keyword):
        match = re.search(rf'{keyword} (.*?);', content)
        return match.group(1).strip() if match else None

    def _extract_macro_coords(self, content, keyword):
        match = re.search(rf'{keyword} (-?\d+\.?\d*) (-?\d+\.?\d*) ;', content)
        return list(map(float, match.groups())) if match else []

    def _extract_macro_foreign(self, content):
        match = re.search(r'FOREIGN (\S+) (-?\d+\.?\d*) (-?\d+\.?\d*) ;', content)
        if match:
            return {
                "name": match.group(1),
                "coords": [float(match.group(2)), float(match.group(3))]
            }
        return None

    def _extract_macro_size(self, content):
        match = re.search(r'SIZE (-?\d+\.?\d*) BY (-?\d+\.?\d*) ;', content)
        return list(map(float, match.groups())) if match else []

    def _extract_macro_list_field(self, content, keyword):
        match = re.search(rf'{keyword} (.*?);', content)
        return match.group(1).strip().split() if match else []

    def _parse_macro_pins(self, content):
        pin_pattern = re.compile(r'PIN (.*?)\n(.*?)END\s+\1', re.DOTALL | re.IGNORECASE)
        pins = {}
        for match in pin_pattern.finditer(content):
            pin_name = match.group(1).strip()
            pin_content = match.group(2).strip()
            pins[pin_name] = self._parse_pin_block(pin_content)
        return pins

    def _parse_pin_block(self, content):
        result = {
            "direction": self._extract_macro_field(content, "DIRECTION"),
            "use": self._extract_macro_field(content, "USE"),
            "antenna": [],
            "groundsensitivity": self._extract_macro_field(content, "GROUNDSENSITIVITY"),
            "supplysensitivity": self._extract_macro_field(content, "SUPPLYSENSITIVITY"),
            "ports": []
        }

        # Extract antenna fields
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("ANTENNA"):
                tokens = line.strip(';').split()
                result["antenna"].append({
                    "type": tokens[0],
                    "value": float(tokens[1]),
                    "layer": tokens[-1]
                })

        # Extract full PORT ... END blocks
        port_pattern = re.compile(r'PORT\s*(.*?)END', re.DOTALL | re.IGNORECASE)
        for port_match in port_pattern.finditer(content):
            port_block = port_match.group(1)
            port_data = self._extract_layer_rects(port_block)
            result["ports"].append(port_data)

        return result


    def _parse_macro_obs(self, content):
        obs_pattern = re.compile(r'OBS\s*(.*?)END', re.DOTALL | re.IGNORECASE)
        match = obs_pattern.search(content)
        if match:
            return self._extract_layer_rects(match.group(1).strip())
        return {}

    def _extract_layer_rects(self, content):
        layer_blocks = defaultdict(list)
        current_layer = None
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("LAYER"):
                current_layer = line.split()[1]
            elif line.startswith("RECT") and current_layer:
                coords = list(map(float, re.findall(r'-?\d+\.?\d*', line)))
                layer_blocks[current_layer].append(coords)
        return dict(layer_blocks)

    def _parse_layers(self):
        for block in self._extract_blocks("LAYER"):
            lines = block.strip().splitlines()
            layer_name = lines[0].split()[1]
            self.layers[layer_name] = {"raw": block}

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
            lines = block.strip().splitlines()
            rule_name = lines[0].split()[1]
            self.via_rules[rule_name] = {"raw": block}

    def _parse_property_definitions(self):
        pattern = re.compile(r'PROPERTYDEFINITIONS(.*?)END PROPERTYDEFINITIONS', re.DOTALL | re.IGNORECASE)
        match = pattern.search(self.text)
        if match:
            block = match.group(1)
            for line in block.strip().splitlines():
                tokens = line.strip().split()
                if len(tokens) >= 3:
                    key = f"{tokens[0]} {tokens[1]}"
                    value = " ".join(tokens[2:])
                    self.property_definitions[key] = value

    @staticmethod
    def from_file(file_path):
        with open(file_path, 'r') as f:
            lef_text = f.read()
        return LefParser(lef_text)

    # Accessor methods
    def get_sites(self):
        return self.sites

    def get_macros(self):
        return self.macros

    def get_layers(self):
        return self.layers

    def get_vias(self):
        return self.vias

    def get_via_rules(self):
        return self.via_rules

    def get_property_definitions(self):
        return self.property_definitions


    def get_parser_dict(self):
        return {
            "sites": self.sites,
            "macros": self.macros,
            "layers": self.layers,
            "vias": self.vias,
            "via_rules": self.via_rules
        }