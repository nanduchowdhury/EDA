

import logging

from def_parser import DefParserImplement
from lef_parser import LefParserImplement

class DesignData:
    def __init__(self, _defParserImplement=None, _lefParserImplement=None):
        self.defParserImplement = _defParserImplement
        self.lefParserImplement = _lefParserImplement
        self.instances = {}

    def execute(self):
        if not self.defParserImplement or not self.lefParserImplement:
            logging.error("Missing DEF or LEF parser.")
            return

        # Step 1: Get DEF component data
        def_data = self.defParserImplement.def_dict
        design_units = def_data.get("units", {}).get("database", 2000)
        design_units = int(design_units)

        components = def_data.get("components", [])
        if not isinstance(components, list):
            logging.error(f"'components' should be a list, got {type(components)}")
            return

        # Step 2: Get LEF macro data
        macros = self.lefParserImplement.lef_dict.get("macros", {})

        for comp in components:
            instance_name = comp.get("inst_name")
            cell_name = comp.get("cell_name")
            location = comp.get("location")

            if not instance_name or not cell_name or not location:
                logging.warning(f"Invalid component entry: {comp}")
                continue

            x_dbu, y_dbu = location
            x_dbu = int(x_dbu)
            y_dbu = int(y_dbu)

            x_um = x_dbu / design_units
            y_um = y_dbu / design_units

            macro = macros.get(cell_name)
            if not macro:
                logging.warning(f"Macro {cell_name} not found in LEF for instance {instance_name}.")
                continue

            width, height = macro.get("size", [0.0, 0.0])

            bbox = [x_um, y_um, x_um + width, y_um + height]

            self.instances[instance_name] = {
                "cell": cell_name,
                "bbox": bbox
            }

        logging.info(f"Parsed {len(self.instances)} instances.")


