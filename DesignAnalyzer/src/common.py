
from PyQt5.QtWidgets import QListWidget, QTextEdit

from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def addItemIfNotExists(self, text):
        """Add item to the list if it doesn't already exist."""
        for i in range(self.count()):
            if self.item(i).text() == text:
                return  # Item already exists, don't add it
        self.addItem(text)  # Add only if not found


class PlaceholderTextEdit(QTextEdit):
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent)
        self._placeholder_text = placeholder_text
        self._placeholder_visible = True
        self._init_placeholder()

        self.textChanged.connect(self._on_text_changed)
        self.setAcceptRichText(False)  # Optional: plain text only

    def _init_placeholder(self):
        """Initializes the placeholder appearance."""
        self.setTextColor(Qt.gray)
        self.setPlainText(self._placeholder_text)
        self._placeholder_visible = True

    def _on_text_changed(self):
        if self._placeholder_visible:
            # User typed something: remove placeholder
            content = self.toPlainText()
            if content != self._placeholder_text:
                self._placeholder_visible = False
                self.setTextColor(Qt.black)
                self.blockSignals(True)
                self.setPlainText(content)
                self.blockSignals(False)
        elif not self.toPlainText().strip():
            # Field cleared: show placeholder again
            self._init_placeholder()

    def focusInEvent(self, event):
        """Clear placeholder when focused."""
        super().focusInEvent(event)
        if self._placeholder_visible:
            self.clear()
            self.setTextColor(Qt.black)
            self._placeholder_visible = False

    def focusOutEvent(self, event):
        """Restore placeholder when unfocused and empty."""
        super().focusOutEvent(event)
        if not self.toPlainText().strip():
            self._init_placeholder()

    def toPlainText(self):
        """Return empty string if placeholder is visible."""
        if self._placeholder_visible:
            return ""
        return super().toPlainText()

