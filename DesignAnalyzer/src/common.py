
from PyQt5.QtWidgets import QListWidget, QTextEdit, QLabel

from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtCore import Qt, QTimer


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


class ScrollingLabel(QLabel):
    def __init__(self, text="", parent=None, speed=60, step=2):
        super().__init__(parent)
        self._text = text
        self._offset = 0
        self._step = step
        self._scrolling_enabled = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self._timer.start(speed)

        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setMinimumHeight(20)

    def setText(self, text):
        self._text = text
        self._offset = 0
        self._updateScrolling()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._updateScrolling()

    def _updateScrolling(self):
        """Enable scrolling only if text width exceeds label width."""
        text_width = self.fontMetrics().width(self._text)
        self._scrolling_enabled = text_width > self.width()

    def _on_timer(self):
        if self._scrolling_enabled:
            self._offset += self._step
            if self._offset > self.fontMetrics().width(self._text):
                self._offset = -self.width()
            self.update()

    def paintEvent(self, event):
        if not self._scrolling_enabled:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.setFont(self.font())

        x = -self._offset
        y = int(self.height() / 2 + self.fontMetrics().ascent() / 2)

        text_width = self.fontMetrics().width(self._text)
        while x < self.width():
            painter.drawText(x, y, self._text)
            x += text_width + 50  # space between repetitions
