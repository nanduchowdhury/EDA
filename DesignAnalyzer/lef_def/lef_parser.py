
from collections import defaultdict

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
class LefUnits:
    time: Optional[Tuple[int, int]] = None           # (unit_id, value)
    capacitance: Optional[Tuple[int, int]] = None    # (unit_id, value)
    resistance: Optional[Tuple[int, int]] = None     # (unit_id, value)
    power: Optional[Tuple[int, int]] = None          # (unit_id, value)
    current: Optional[Tuple[int, int]] = None        # (unit_id, value)
    voltage: Optional[Tuple[int, int]] = None        # (unit_id, value)
    database: Optional[Tuple[int, int]] = None       # (unit_id, value)
    frequency: Optional[Tuple[int, int]] = None      # (unit_id, value)

@dataclass
class LefPropertyDefinition:
    obj_type: str                # e.g., LIBRARY, LAYER, VIA, etc.
    prop_name: str               # e.g., NAME, intNum, etc.
    data_type: str               # STRING, INTEGER, REAL
    range: Optional[Tuple[float, float]] = None  # (min, max) if RANGE present
    default: Optional[str] = None                # Default value if present

@dataclass
class LefLayer:
    name_id: int
    type: Optional[str] = None
    direction: Optional[str] = None
    pitch: Optional[List[float]] = None
    width: Optional[float] = None
    minwidth: Optional[float] = None
    maxwidth: Optional[float] = None
    spacing: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)  # Store all lines for advanced/rare features

@dataclass
class LefViaLayerRect:
    layer_id: int
    rects: List[Tuple[float, float, float, float]] = field(default_factory=list)

@dataclass
class LefVia:
    name_id: int
    generated: bool = False
    resistance: Optional[float] = None
    layers: List[LefViaLayerRect] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class LefSite:
    name_id: int
    class_type: Optional[str] = None
    symmetry: List[str] = field(default_factory=list)
    size: Optional[Tuple[float, float]] = None
    rowpattern: Optional[str] = None
    properties: Dict[str, str] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class LefPort:
    layers: List[Dict] = field(default_factory=list)  # Each dict: {'layer': ..., 'geometry': ...}

@dataclass
class LefPin:
    name_id: int
    direction: Optional[str] = None
    use: Optional[str] = None
    shape: Optional[str] = None
    properties: Dict[str, str] = field(default_factory=dict)
    electrical: Dict[str, float] = field(default_factory=dict)
    antenna: List[str] = field(default_factory=list)
    ports: List[LefPort] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class LefMacro:
    name_id: int
    class_type: Optional[str] = None
    source: Optional[str] = None
    foreign: Optional[str] = None
    power: Optional[float] = None
    size: Optional[Tuple[float, float]] = None
    symmetry: List[str] = field(default_factory=list)
    site: Optional[str] = None
    pins: List[LefPin] = field(default_factory=list)
    obs: List[str] = field(default_factory=list)
    density: List[str] = field(default_factory=list)
    timing: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class LefViaruleLayer:
    layer_id: int
    direction: Optional[str] = None
    width: Optional[Tuple[float, float]] = None  # (min, max) if "TO" present, else (val, val)
    overhang: Optional[float] = None
    metaloverhang: Optional[float] = None
    rects: List[Tuple[float, float, float, float]] = field(default_factory=list)
    spacing: Optional[Tuple[float, float]] = None
    resistance: Optional[float] = None
    properties: Dict[str, str] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class LefViarule:
    name_id: int
    generate: bool = False
    layers: List[LefViaruleLayer] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class LefData:
    version_id: Optional[int] = None
    namescasesensitive: Optional[bool] = None
    fixedmask: Optional[bool] = None
    nowireextensionatpin: Optional[bool] = None
    busbitchars_id: Optional[int] = None
    dividerchar_id: Optional[int] = None
    useminspacing: Dict[str, bool] = field(default_factory=dict)
    clearancemeasure: List[int] = field(default_factory=list)
    manufacturinggrid: Optional[float] = None
    units: Optional[LefUnits] = None
    property_definitions: List[LefPropertyDefinition] = field(default_factory=list)
    layers: List[LefLayer] = field(default_factory=list)
    vias: List[LefVia] = field(default_factory=list)
    sites: List[LefSite] = field(default_factory=list)
    macros: Dict[int, LefMacro] = field(default_factory=dict)
    viarules: List[LefViarule] = field(default_factory=list)

class LefParser:
    def __init__(self):
        self.lef_data = LefData()

    def parse_version(self, line: str):
        if line.startswith("VERSION"):
            version = line.split()[1]
            self.lef_data.version_id = gname_index.set(version)

    def parse_namescasesensitive(self, line: str):
        # NAMESCASESENSITIVE ON ;
        value = line.split()[1].strip(";")
        self.lef_data.namescasesensitive = (value == "ON")

    def parse_fixedmask(self, line: str):
        # FIXEDMASK ;
        self.lef_data.fixedmask = True

    def parse_nowireextensionatpin(self, line: str):
        # NOWIREEXTENSIONATPIN ON ;
        value = line.split()[1].strip(";")
        self.lef_data.nowireextensionatpin = (value == "ON")

    def parse_busbitchars(self, line: str):
        # BUSBITCHARS "<>" ;
        m = re.search(r'BUSBITCHARS\s+"([^"]+)"', line)
        if m:
            self.lef_data.busbitchars_id = gname_index.set(m.group(1))

    def parse_dividerchar(self, line: str):
        # DIVIDERCHAR ":" ;
        m = re.search(r'DIVIDERCHAR\s+"?([^";]+)"?', line)
        if m:
            self.lef_data.dividerchar_id = gname_index.set(m.group(1).strip())

    def parse_useminspacing(self, line: str):
        # USEMINSPACING OBS OFF ; or USEMINSPACING PIN ON ;
        parts = line.split()
        if len(parts) >= 3:
            if not hasattr(self.lef_data, "useminspacing"):
                self.lef_data.useminspacing = {}
            self.lef_data.useminspacing[parts[1]] = (parts[2] == "ON")

    def parse_clearancemeasure(self, line: str):
        # CLEARANCEMEASURE EUCLIDEAN ; or CLEARANCEMEASURE MAXXY ;
        value = line.split()[1].strip(";")
        if not hasattr(self.lef_data, "clearancemeasure"):
            self.lef_data.clearancemeasure = []
        self.lef_data.clearancemeasure.append(gname_index.set(value))

    
    def parse_units(self, lines: list):
        """
        Parses the UNITS section of a LEF file.
        """
        units = LefUnits()
        for line in lines:
            line = line.strip().rstrip(';')
            if line.startswith("TIME"):
                parts = line.split()
                units.time = (gname_index.set(parts[1]), int(parts[2]))
            elif line.startswith("CAPACITANCE"):
                parts = line.split()
                units.capacitance = (gname_index.set(parts[1]), int(parts[2]))
            elif line.startswith("RESISTANCE"):
                parts = line.split()
                units.resistance = (gname_index.set(parts[1]), int(parts[2]))
            elif line.startswith("POWER"):
                parts = line.split()
                units.power = (gname_index.set(parts[1]), int(parts[2]))
            elif line.startswith("CURRENT"):
                parts = line.split()
                units.current = (gname_index.set(parts[1]), int(parts[2]))
            elif line.startswith("VOLTAGE"):
                parts = line.split()
                units.voltage = (gname_index.set(parts[1]), int(parts[2]))
            elif line.startswith("DATABASE"):
                parts = line.split()
                units.database = (gname_index.set(parts[1]), int(parts[2]))
            elif line.startswith("FREQUENCY"):
                parts = line.split()
                units.frequency = (gname_index.set(parts[1]), int(parts[2]))
        self.lef_data.units = units


    def parse_property_definitions(self, lines: list):
        """
        Parses the PROPERTYDEFINITIONS section of a LEF file.
        Stores results in self.lef_data.property_definitions as a list of LefPropertyDefinition.
        """
        if not hasattr(self.lef_data, "property_definitions"):
            self.lef_data.property_definitions = []

        for line in lines:
            line = line.strip().rstrip(';')
            if not line or line.startswith("PROPERTYDEFINITIONS") or line.startswith("END PROPERTYDEFINITIONS"):
                continue

            tokens = line.split()
            if len(tokens) < 4:
                continue  # Not a valid property definition

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
                    default = tokens[idx+3].strip('"')
            elif len(tokens) > 3:
                # Default value for STRING, INTEGER, REAL
                default = tokens[3].strip('"')

            self.lef_data.property_definitions.append(
                LefPropertyDefinition(
                    obj_type=obj_type,
                    prop_name=prop_name,
                    data_type=data_type,
                    range=prop_range,
                    default=default
                )
            )


    def parse_layer(self, lines: list):
        """
        Parses a LAYER section (CUT or ROUTING) from LEF.
        Stores all lines for advanced/rare features in raw_lines.
        """
        # First line: LAYER layerName
        header = lines[0].strip()
        parts = header.split()
        name_id = gname_index.set(parts[1])
        layer = LefLayer(name_id=name_id)
        layer.raw_lines = lines[:]  # Save all lines for advanced/rare features

        for line in lines[1:]:
            line = line.strip().rstrip(";")
            if not line or line.startswith("END"):
                continue
            if line.startswith("TYPE"):
                layer.type = line.split()[1]
            elif line.startswith("DIRECTION"):
                layer.direction = line.split()[1]
            elif line.startswith("PITCH"):
                nums = [float(x) for x in line.split()[1:]]
                layer.pitch = nums
            elif line.startswith("WIDTH"):
                layer.width = float(line.split()[1])
            elif line.startswith("MINWIDTH"):
                layer.minwidth = float(line.split()[1])
            elif line.startswith("MAXWIDTH"):
                layer.maxwidth = float(line.split()[1])
            elif line.startswith("SPACING"):
                layer.spacing.append(line)
            elif line.startswith("PROPERTY"):
                # PROPERTY propName propVal ;
                tokens = line.split(None, 2)
                if len(tokens) == 3:
                    prop_name = tokens[1]
                    prop_val = tokens[2].strip('"')
                    layer.properties[prop_name] = prop_val
            # You can add more elifs for other fields as needed

        if not hasattr(self.lef_data, "layers"):
            self.lef_data.layers = []
        self.lef_data.layers.append(layer)


    def parse_via(self, lines: list):
        try:

            """
            Parses a VIA section from LEF.
            """
            header = lines[0].strip()
            parts = header.split()
            name_id = gname_index.set(parts[1])
            generated = "GENERATED" in header
            via = LefVia(name_id=name_id, generated=generated)
            via.raw_lines = lines[:]

            current_layer = None

            for line in lines[1:]:
                line = line.strip().rstrip(";")
                if not line or line.startswith("END"):
                    continue
                if line.startswith("RESISTANCE"):
                    via.resistance = float(line.split()[1])
                elif line.startswith("LAYER"):
                    layer_id = gname_index.set(line.split()[1])
                    current_layer = LefViaLayerRect(layer_id=layer_id)
                    via.layers.append(current_layer)
                elif line.startswith("RECT") and current_layer is not None:
                    tokens = line.split()
                    idx = 1
                    mask = None
                    # Check for optional MASK
                    if idx < len(tokens) and tokens[idx] == "MASK":
                        mask = int(tokens[idx + 1])
                        idx += 2
                    # Next 4 tokens are the rectangle coordinates
                    if idx + 3 < len(tokens):
                        rect = tuple(map(float, tokens[idx:idx + 4]))
                        # Store as (mask, rect) if mask present, else just rect
                        if mask is not None:
                            current_layer.rects.append((mask, rect))
                        else:
                            current_layer.rects.append(rect)
                # You can add more elifs for POLYGON, etc. if needed

            if not hasattr(self.lef_data, "vias"):
                self.lef_data.vias = []
            self.lef_data.vias.append(via)
        
        except Exception as e:
            print(f"Error LEF parsing VIA: lines: {lines} error: {e}")



    def parse_site(self, lines: list):
        """
        Parses a SITE section from LEF.
        """
        header = lines[0].strip()
        parts = header.split()
        name_id = gname_index.set(parts[1])
        site = LefSite(name_id=name_id)
        site.raw_lines = lines[:]

        for line in lines[1:]:
            line = line.strip().rstrip(";")
            if not line or line.startswith("END"):
                continue
            if line.startswith("CLASS"):
                site.class_type = line.split()[1]
            elif line.startswith("SYMMETRY"):
                site.symmetry = line.split()[1:]
            elif line.startswith("SIZE"):
                # SIZE 67.2 BY 6
                m = re.match(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)', line)
                if m:
                    site.size = (float(m.group(1)), float(m.group(2)))
            elif line.startswith("ROWPATTERN"):
                site.rowpattern = line[len("ROWPATTERN"):].strip()
            elif line.startswith("PROPERTY"):
                tokens = line.split(None, 2)
                if len(tokens) == 3:
                    prop_name = tokens[1]
                    prop_val = tokens[2].strip('"')
                    site.properties[prop_name] = prop_val

        if not hasattr(self.lef_data, "sites"):
            self.lef_data.sites = []
        self.lef_data.sites.append(site)


    def parse_macro(self, lines: list):
        """
        Parses a MACRO section from LEF.
        """
        header = lines[0].strip()
        name_id = gname_index.set(header.split()[1])
        macro = LefMacro(name_id=name_id)
        macro.raw_lines = lines[:]

        i = 1
        n = len(lines)
        while i < n:
            line = lines[i].strip().rstrip(";")
            if not line or line.startswith("END"):
                i += 1
                continue
            if line.startswith("CLASS"):
                macro.class_type = line.split()[1]
            elif line.startswith("SOURCE"):
                macro.source = line.split()[1]
            elif line.startswith("FOREIGN"):
                macro.foreign = line.split()[1]
            elif line.startswith("POWER"):
                macro.power = float(line.split()[1])
            elif line.startswith("SIZE"):
                m = re.match(r'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)', line)
                if m:
                    macro.size = (float(m.group(1)), float(m.group(2)))
            elif line.startswith("SYMMETRY"):
                macro.symmetry = line.split()[1:]
            elif line.startswith("SITE"):
                macro.site = line.split()[1]
            elif line.startswith("PROPERTY"):
                tokens = line.split(None, 2)
                if len(tokens) == 3:
                    prop_name = tokens[1]
                    prop_val = tokens[2].strip('"')
                    macro.properties[prop_name] = prop_val
            elif line.startswith("PIN"):
                # Parse PIN block
                pin_lines = [line]
                i += 1
                while i < n and not lines[i].strip().startswith("END"):
                    pin_lines.append(lines[i])
                    i += 1
                if i < n:
                    pin_lines.append(lines[i])  # Add END line
                macro.pins.append(self.parse_pin(pin_lines))
            elif line.startswith("OBS"):
                # Parse OBS block
                obs_lines = [line]
                i += 1
                while i < n and not lines[i].strip().startswith("END"):
                    obs_lines.append(lines[i])
                    i += 1
                if i < n:
                    obs_lines.append(lines[i])
                macro.obs.extend(obs_lines)
            elif line.startswith("DENSITY"):
                # Parse DENSITY block
                density_lines = [line]
                i += 1
                while i < n and not lines[i].strip().startswith("END"):
                    density_lines.append(lines[i])
                    i += 1
                if i < n:
                    density_lines.append(lines[i])
                macro.density.extend(density_lines)
            elif line.startswith("TIMING"):
                # Parse TIMING block
                timing_lines = [line]
                i += 1
                while i < n and not lines[i].strip().startswith("END"):
                    timing_lines.append(lines[i])
                    i += 1
                if i < n:
                    timing_lines.append(lines[i])
                macro.timing.extend(timing_lines)
            i += 1

        if not hasattr(self.lef_data, "macros"):
            self.lef_data.macros = {}
        self.lef_data.macros[macro.name_id] = macro

    def parse_pin(self, lines: list) -> LefPin:
        """
        Parses a PIN block from LEF.
        """
        header = lines[0].strip()
        name_id = gname_index.set(header.split()[1])
        pin = LefPin(name_id=name_id)
        pin.raw_lines = lines[:]
        i = 1
        n = len(lines)
        while i < n:
            line = lines[i].strip().rstrip(";")
            if not line or line.startswith("END"):
                i += 1
                continue
            if line.startswith("DIRECTION"):
                pin.direction = line.split()[1]
            elif line.startswith("USE"):
                pin.use = line.split()[1]
            elif line.startswith("SHAPE"):
                pin.shape = line.split()[1]
            elif line.startswith("PROPERTY"):
                tokens = line.split(None, 2)
                if len(tokens) == 3:
                    prop_name = tokens[1]
                    prop_val = tokens[2].strip('"')
                    pin.properties[prop_name] = prop_val
            elif line.startswith("PORT"):
                # Parse PORT block
                port_lines = [line]
                i += 1
                while i < n and not lines[i].strip().startswith("END"):
                    port_lines.append(lines[i])
                    i += 1
                if i < n:
                    port_lines.append(lines[i])
                pin.ports.append(self.parse_port(port_lines))
            else:
                # Try to parse electrical/antenna fields
                tokens = line.split()
                if len(tokens) == 2:
                    try:
                        pin.electrical[tokens[0]] = float(tokens[1])
                    except Exception:
                        pass
                elif "ANTENNA" in line:
                    pin.antenna.append(line)
            i += 1
        return pin


    def parse_port(self, lines: list) -> LefPort:
        """
        Parses a PORT block from LEF.
        """
        port = LefPort()
        i = 1
        n = len(lines)
        current_layer = None
        for i in range(1, n):
            line = lines[i].strip().rstrip(";")
            if not line or line.startswith("END"):
                continue
            if line.startswith("LAYER"):
                current_layer = {'layer': line.split()[1], 'geometry': []}
                port.layers.append(current_layer)
            elif current_layer is not None:
                current_layer['geometry'].append(line)
        return port


    def parse_viarule(self, lines: list):
        try:
            """
            Parses a VIARULE section from LEF.
            """
            header = lines[0].strip()
            parts = header.split()
            name_id = gname_index.set(parts[1])
            generate = "GENERATE" in header.upper()
            viarule = LefViarule(name_id=name_id, generate=generate)
            viarule.raw_lines = lines[:]

            current_layer = None

            i = 1
            n = len(lines)
            while i < n:
                line = self.clean_semicolon_and_beyond(lines[i].strip())
                if not line or line.startswith("END"):
                    i += 1
                    continue
                if line.startswith("LAYER"):
                    layer_id = gname_index.set(line.split()[1])
                    current_layer = LefViaruleLayer(layer_id=layer_id)
                    viarule.layers.append(current_layer)
                elif current_layer is not None:
                    if line.startswith("DIRECTION"):
                        current_layer.direction = line.split()[1]
                    elif line.startswith("WIDTH"):
                        tokens = line.split()
                        if "TO" in tokens:
                            idx = tokens.index("TO")
                            minw = float(tokens[1])
                            maxw = float(tokens[idx+1])
                            current_layer.width = (minw, maxw)
                        else:
                            val = float(tokens[1])
                            current_layer.width = (val, val)
                    elif line.startswith("OVERHANG"):
                        current_layer.overhang = float(line.split()[1])
                    elif line.startswith("METALOVERHANG"):
                        current_layer.metaloverhang = float(line.split()[1])
                    elif line.startswith("RECT"):
                        line = line.replace('(', '').replace(')', '')
                        nums = list(map(float, line.split()[1:]))
                        if len(nums) == 4:
                            current_layer.rects.append(tuple(nums))
                    elif line.startswith("SPACING"):
                        tokens = line.split()
                        if "BY" in tokens:
                            idx = tokens.index("BY")
                            val1 = float(tokens[1])
                            val2 = float(tokens[idx+1])
                            current_layer.spacing = (val1, val2)
                    elif line.startswith("RESISTANCE"):
                        current_layer.resistance = float(line.split()[1])
                    elif line.startswith("PROPERTY"):
                        tokens = line.split(None, 2)
                        if len(tokens) == 3:
                            prop_name = tokens[1]
                            prop_val = tokens[2].strip('"')
                            current_layer.properties[prop_name] = prop_val
                    current_layer.raw_lines.append(line)
                elif line.startswith("PROPERTY"):
                    # Top-level VIARULE properties
                    tokens = line.split()
                    for j in range(1, len(tokens)-1, 2):
                        prop_name = tokens[j]
                        prop_val = tokens[j+1].strip('"')
                        viarule.properties[prop_name] = prop_val
                i += 1

            if not hasattr(self.lef_data, "viarules"):
                self.lef_data.viarules = []
            self.lef_data.viarules.append(viarule)

        except Exception as e:
            print(f"Error LEF parsing VIARULE: lines: {lines} error: {e}")


    def clean_semicolon_and_beyond(self, line: str) -> str:
        cleaned = line.split(';', 1)[0].strip()
        return cleaned

    def parse(self, lef_file_content: str):
        lines = lef_file_content.splitlines()
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i].strip()
            if not line or line.startswith("#"):
                i += 1
                continue

            # One-liner sections
            if line.startswith("VERSION"):
                self.parse_version(line)
                i += 1
            elif line.startswith("NAMESCASESENSITIVE"):
                self.parse_namescasesensitive(line)
                i += 1
            elif line.startswith("FIXEDMASK"):
                self.parse_fixedmask(line)
                i += 1
            elif line.startswith("NOWIREEXTENSIONATPIN"):
                self.parse_nowireextensionatpin(line)
                i += 1
            elif line.startswith("BUSBITCHARS"):
                self.parse_busbitchars(line)
                i += 1
            elif line.startswith("DIVIDERCHAR"):
                self.parse_dividerchar(line)
                i += 1
            elif line.startswith("USEMINSPACING"):
                self.parse_useminspacing(line)
                i += 1
            elif line.startswith("CLEARANCEMEASURE"):
                self.parse_clearancemeasure(line)
                i += 1

            # Multi-line sections
            elif line.startswith("UNITS"):
                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i].strip()
                    block_lines.append(l)
                    if l.startswith("END UNITS"):
                        break
                    i += 1
                self.parse_units(block_lines)
                i += 1

            elif line.startswith("NONDEFAULTRULE"):
                
                tokens = line.split()
                if len(tokens) > 1:
                    nondefaultrule_name = tokens[1]

                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i]   # Do not strip here. Some nondefaultrules do not END with the rule-name.
                    block_lines.append(l)
                    if l.startswith("END"):
                        print(f"Found END {nondefaultrule_name} in line: {l}")
                        break
                    i += 1
                # Handle NONDEFAULTRULE parsing if needed
                i += 1

            elif line.startswith("PROPERTYDEFINITIONS"):
                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i].strip()
                    block_lines.append(l)
                    if l.startswith("END PROPERTYDEFINITIONS"):
                        break
                    i += 1
                self.parse_property_definitions(block_lines)
                i += 1


            elif line.startswith("VIARULE"):
                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i].strip()
                    block_lines.append(l)
                    if l.startswith("END"):
                        break
                    i += 1
                self.parse_viarule(block_lines)
                i += 1

            elif line.startswith("VIA"):
                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i].strip()
                    block_lines.append(l)
                    if l.startswith("END"):
                        break
                    i += 1
                self.parse_via(block_lines)
                i += 1

            elif line.startswith("SITE"):
                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i].strip()
                    block_lines.append(l)
                    if l.startswith("END"):
                        break
                    i += 1
                self.parse_site(block_lines)
                i += 1

            elif line.startswith("MACRO"):
                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i].strip()
                    block_lines.append(l)
                    if l.startswith("END"):
                        break
                    i += 1
                self.parse_macro(block_lines)
                i += 1

            # Keep LAYER at the very end - LAYER shows up in other blocks too.
            elif line.startswith("LAYER"):
                block_lines = [line]
                i += 1
                while i < n:
                    l = lines[i].strip()
                    block_lines.append(l)
                    if l.startswith("END"):
                        break
                    i += 1
                self.parse_layer(block_lines)
                i += 1

            else:
                i += 1



class LefParserImplement:
    def __init__(self):

        self.parser_dict = {}

    def parse(self, file_path):
        if file_path:
            with open(file_path, 'r') as f:
                lef_text = f.read()
                lefParser = LefParser()
                lefParser.parse(lef_text)
                self.parser_dict[file_path] = lefParser

    def get_macros(self, cell_name=None):

        macros = []

        for l, parser in self.parser_dict.items():

            if cell_name is None:
                macros.extend(parser.lef_data.macros.values())
                continue

            # If cell_name is provided, filter macros by name
            cell_name_id = gname_index.set(cell_name)
            if cell_name_id not in parser.lef_data.macros:
                continue
            macro = parser.lef_data.macros.get(cell_name_id)
            if macro:
                macros.append(macro)

        return macros

    
    def get_layers(self, metal_or_via=None):
        layers = []
        for l, parser in self.parser_dict.items():
            for layer in parser.lef_data.layers:
                # if metal_or_via is None or layer.type.upper() == metal_or_via.upper():
                    layers.append(layer)
        return layers
    
    def get_layer(self, layer_name):
        layer_name_id = gname_index.set(layer_name)
        for l, parser in self.parser_dict.items():
            for layer in parser.lef_data.layers:
                if layer.name_id == layer_name_id:
                    return layer
        return None

    def get_vias(self):
        vias = []
        for l, parser in self.parser_dict.items():
            if hasattr(parser.lef_data, "vias"):
                vias.extend(parser.lef_data.vias)
        return vias
    

