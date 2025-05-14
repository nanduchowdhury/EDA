
from PyQt5.QtWidgets import QListWidget

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def addItemIfNotExists(self, text):
        """Add item to the list if it doesn't already exist."""
        for i in range(self.count()):
            if self.item(i).text() == text:
                return  # Item already exists, don't add it
        self.addItem(text)  # Add only if not found

