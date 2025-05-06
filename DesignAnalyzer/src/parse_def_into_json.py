import json
import re

from def_parser import DefParser

def num_vias(json_struct, layerName=None):
    """
    Returns the number of vias. If layerName is provided, only count vias that include that layer.
    If layerName is empty or None, count all vias.

    Args:
        json_struct (dict): Parsed JSON structure from the DEF file.
        layerName (str or None): Layer name to filter vias by. If empty, all vias are counted.

    Returns:
        int: Number of vias matching the condition.
    """
    vias = json_struct.get("vias", [])
    if not layerName:
        return len(vias)
    return sum(1 for via in vias if layerName in via.get("layers", []))


# Example usage:
print("Start reading DEF...")
parser = DefParser()
# result = parser.parse("small.def")
result = parser.parse("../power3.txt")

print("Finished reading DEF...")
# print(json.dumps(result, indent=2))

print(num_vias(result, ""))


