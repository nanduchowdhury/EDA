import sys
import threading

class NameIndex:
    def __init__(self):
        self.name_to_id = {}
        self.id_to_name = {}
        self._counter = 0
        self._lock = threading.Lock()

    def set(self, name: str) -> int:
        name = sys.intern(name)  # Ensure a single memory allocation
        with self._lock:
            if name in self.name_to_id:
                return self.name_to_id[name]
            id_ = self._counter
            self._counter += 1
            self.name_to_id[name] = id_
            self.id_to_name[id_] = name
            return id_

    def get_id(self, name: str) -> int:
        """Return ID of the name if it exists, else raise KeyError."""
        name = sys.intern(name)
        with self._lock:
            if name not in self.name_to_id:
                raise KeyError(f"Name '{name}' not found in NameIndex")
            return self.name_to_id[name]

    def getName(self, id_: int) -> str:
        """Return name associated with ID, else raise KeyError."""
        with self._lock:
            if id_ not in self.id_to_name:
                raise KeyError(f"ID {id_} not found in NameIndex")
            return self.id_to_name[id_]

    def has_name(self, name: str) -> bool:
        """Check if a name exists in the index."""
        name = sys.intern(name)
        with self._lock:
            return name in self.name_to_id

    def has_id(self, id_: int) -> bool:
        """Check if an ID exists in the index."""
        with self._lock:
            return id_ in self.id_to_name

    def __len__(self) -> int:
        """Return number of names indexed."""
        with self._lock:
            return len(self.name_to_id)

# Global Name-mapping
gname_index = NameIndex()

