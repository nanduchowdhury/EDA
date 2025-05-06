
import json
import re


class DefParser:
    def __init__(self):
        self.data = {
            "version": None,
            "dividerchar": None,
            "busbitchars": None,
            "design": None,
            "units": None,
            "property_definitions": {},
            "die_area": None,
            "rows": [],
            "tracks": [],
            "gcellgrid": [],
            "vias": [],
            "regions": [],
            "components": [],
            "pins": []
        }

    def parse(self, filename):
        with open(filename, 'r') as file:
            lines = file.readlines()

        self.lines = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
        self.index = 0
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.startswith("VERSION"):
                self._parse_version(line)
            elif line.startswith("DIVIDERCHAR"):
                self._parse_dividerchar(line)
            elif line.startswith("BUSBITCHARS"):
                self._parse_busbitchars(line)
            elif line.startswith("DESIGN"):
                self._parse_design(line)
            elif line.startswith("UNITS"):
                self._parse_units(line)
            elif line.startswith("PROPERTYDEFINITIONS"):
                self._parse_property_definitions()
            elif line.startswith("DIEAREA"):
                self._parse_diearea(line)
            elif line.startswith("ROW"):
                self._parse_rows()
            elif line.startswith("TRACKS"):
                self._parse_tracks()
            elif line.startswith("GCELLGRID"):
                self._parse_gcellgrid()
            elif line.startswith("VIAS"):
                self._parse_vias()
            elif line.startswith("REGIONS"):
                self._parse_regions()
            elif line.startswith("COMPONENTS"):
                self._parse_components()
            elif line.startswith("PINS"):
                self._parse_pins()
            else:
                self.index += 1

        return self.data

    def _parse_version(self, line):
        self.data["version"] = line.split()[1].strip(";")
        self.index += 1

    def _parse_dividerchar(self, line):
        self.data["dividerchar"] = line.split()[1].strip(";").strip('"')
        self.index += 1

    def _parse_busbitchars(self, line):
        self.data["busbitchars"] = line.split()[1].strip(";").strip('"')
        self.index += 1

    def _parse_design(self, line):
        self.data["design"] = line.split()[1].strip(";")
        self.index += 1

    def _parse_units(self, line):
        match = re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", line)
        if match:
            self.data["units"] = {"distance": "MICRONS", "microns": int(match.group(1))}
        self.index += 1

    def _parse_property_definitions(self):
        self.index += 1
        prop = {}
        while not self.lines[self.index].startswith("END PROPERTYDEFINITIONS"):
            line = self.lines[self.index]
            if line.startswith("DESIGN"):
                key = line.split()[1]
                type_ = line.split()[2]
                value = " ".join(line.split()[3:]).strip(";").strip('"')
                prop[key] = {"type": type_, "value": value}
            self.index += 1
        self.data["property_definitions"] = prop
        self.index += 1

    def _parse_diearea(self, line):
        coords = re.findall(r"\(\s*\d+\s+\d+\s*\)", line)
        self.data["die_area"] = [tuple(map(int, c.strip("()").split())) for c in coords]
        self.index += 1

    def _parse_rows(self):
        while self.lines[self.index].startswith("ROW"):
            self.data["rows"].append(self.lines[self.index])
            self.index += 1

    def _parse_tracks(self):
        while self.lines[self.index].startswith("TRACKS"):
            self.data["tracks"].append(self.lines[self.index])
            self.index += 1

    def _parse_gcellgrid(self):
        while self.lines[self.index].startswith("GCELLGRID"):
            self.data["gcellgrid"].append(self.lines[self.index])
            self.index += 1

    def _parse_vias(self):
        self.index += 1  # skip "VIAS n ;"
        vias = []
        while not self.lines[self.index].startswith("END VIAS"):
            if self.lines[self.index].startswith("-"):
                via = {"name": self.lines[self.index][2:].strip()}
                self.index += 1
                while self.lines[self.index].startswith("+"):
                    parts = self.lines[self.index][1:].split()
                    key = parts[0]
                    val = parts[1:] if len(parts) > 2 else parts[1]
                    via[key.lower()] = val
                    self.index += 1
                vias.append(via)
            else:
                self.index += 1
        self.data["vias"] = vias
        self.index += 1

    def _parse_regions(self):
        self.index += 1
        regions = []
        while not self.lines[self.index].startswith("END REGIONS"):
            line = self.lines[self.index]
            if line.startswith("-"):
                name = line.split()[1]
                coords = re.findall(r"\(\s*\d+\s+\d+\s*\)", line)
                region = {
                    "name": name,
                    "coords": [tuple(map(int, c.strip("()").split())) for c in coords]
                }
                if "+ TYPE" in line:
                    region["type"] = line.split("+ TYPE")[1].strip(" ;")
                regions.append(region)
            self.index += 1
        self.data["regions"] = regions
        self.index += 1

    def _parse_components(self):
        self.index += 1
        components = []
        while not self.lines[self.index].startswith("END COMPONENTS"):
            line = self.lines[self.index]
            if line.startswith("-"):
                components.append(line)
            self.index += 1
        self.data["components"] = components
        self.index += 1

    def _parse_pins(self):
        self.index += 1
        pins = []
        while not self.lines[self.index].startswith("END PINS"):
            line = self.lines[self.index]
            if line.startswith("-"):
                name = line.split()[1]
                pin = {"name": name}
                self.index += 1
                while self.index < len(self.lines) and self.lines[self.index].startswith("+"):
                    parts = self.lines[self.index][1:].split()
                    pin[parts[0].lower()] = " ".join(parts[1:])
                    self.index += 1
                pins.append(pin)
            else:
                self.index += 1
        self.data["pins"] = pins
        self.index += 1

