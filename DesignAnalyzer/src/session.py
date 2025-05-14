import json
import os

import json

class Session:
    def __init__(self):
        self._data = {}

    def readSession(self, jsonFile):
        try:
            with open(jsonFile, 'r') as f:
                self._data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {}

    def writeSession(self, jsonFile):
        with open(jsonFile, 'w') as f:
            json.dump(self._data, f, indent=4)

    def getAttr(self, key):
        return self._data.get(key)

    def setAttr(self, key, value):
        self._data[key] = value

    def clear(self):
        self._data.clear()

    def isAttrPresent(self, key):
        return key in self._data

    def addAttr(self, key, value):
        """Add value to list under key. Create list if it doesn't exist."""
        if key not in self._data or not isinstance(self._data[key], list):
            self._data[key] = []
        self._data[key].append(value)

    def dump(self):
        print(json.dumps(self._data, indent=4))

        