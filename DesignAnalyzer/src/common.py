
from PyQt5.QtWidgets import QListWidget, QTextEdit, QLabel, QListWidgetItem
from PyQt5.QtGui import QColor, QPainter, QTextCursor
from PyQt5.QtCore import Qt, QTimer, QPoint, QObject, pyqtSignal


from PyQt5.QtWidgets import (
    QTabWidget, QMenu, QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QWidget
)
from abc import ABC, abstractmethod


class TabWidgetRmbMenu(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def onClick(self, tab_widget: QTabWidget, tab_index: int):
        pass



class TabWidgetRmbPopOut(TabWidgetRmbMenu):
    def __init__(self, main_window_width, main_window_height, name="Pop Out"):
        super().__init__(name)
        self.popped_out = False
        self.original_index = None
        self.tab_content_widget = None
        self.tab_name = ""
        self.tab_widget = None
        self.dialog = None
        self.main_window_width = main_window_width
        self.main_window_height = main_window_height

    def onClick(self, tab_widget: QTabWidget, tab_index: int):
        if self.popped_out:
            return  # already popped out

        self.popped_out = True
        self.original_index = tab_index
        self.tab_widget = tab_widget
        self.tab_name = tab_widget.tabText(tab_index)
        self.tab_content_widget = tab_widget.widget(tab_index)

        # Remove from tab widget
        tab_widget.removeTab(tab_index)

        # Custom dialog class with reject overridden
        class CustomDialog(QDialog):
            def __init__(dlg_self):
                super().__init__(tab_widget)
                dlg_self.setWindowTitle(f"Popout - {self.tab_name}")
                dlg_self.setModal(True)
                dlg_self.resize(int(self.main_window_width * 0.8), int(self.main_window_height * 0.8))

                dialog_layout = QHBoxLayout(dlg_self)
                dlg_self.setLayout(dialog_layout)

                self.tabWidgetInDialog = QTabWidget()
                self.tab_content_widget.setParent(self.tabWidgetInDialog)
                self.tabWidgetInDialog.addTab(self.tab_content_widget, self.tab_name)
                dialog_layout.addWidget(self.tabWidgetInDialog, stretch=3)

                close_btn = QPushButton("Close")
                dialog_layout.addWidget(close_btn)

                close_btn.clicked.connect(self.on_close)

            def reject(dlg_self):
                self.on_close()  # call your close logic
                super().reject()

        self.dialog = CustomDialog()
        self.dialog.exec_()

    def on_close(self):
        if self.popped_out and self.tab_content_widget:
            self.tab_content_widget.setParent(None)
            self.tab_widget.insertTab(self.original_index, self.tab_content_widget, self.tab_name)
            self.tab_widget.setCurrentIndex(self.original_index)
            self.popped_out = False
        if self.dialog:
            self.dialog.accept()



class TabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rmb_menu_items = []

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def addRmbMenu(self, menu_item_list):
        self._rmb_menu_items.extend(menu_item_list)

    def _show_context_menu(self, pos: QPoint):
        # Map to global position
        global_pos = self.mapToGlobal(pos)

        tab_bar = self.tabBar()
        tab_index = tab_bar.tabAt(pos)

        if tab_index == -1:
            return  # No tab under cursor

        menu = QMenu(self)

        # Populate menu items
        for item in self._rmb_menu_items:
            action = menu.addAction(item.name)

            # Avoid lambda late-binding issue
            def create_handler(menu_item, idx):
                return lambda: menu_item.onClick(self, idx)

            action.triggered.connect(create_handler(item, tab_index))

        menu.exec_(global_pos)



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
        self._history = []
        self._history_index = -1

        self._suggestions = []  # Full suggestion list
        self._current_suggestions = []  # Suggestions matching current input
        self._init_placeholder()

        self.textChanged.connect(self._on_text_changed)
        self.setAcceptRichText(False)  # Optional: plain text only
        
        self._enter_press_callback = None


    def on_enter_pressed(self, callback):
        """Register a function to be called when Enter is pressed."""
        self._enter_press_callback = callback

    def _init_placeholder(self):
        """Initializes the placeholder appearance."""
        self.setTextColor(Qt.gray)
        # self.blockSignals(True)
        self.setPlainText(self._placeholder_text)
        # self.blockSignals(False)
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
                
        # Do NOT trigger placeholder here - it results in infinite recursion
        #elif not self.toPlainText().strip():
            # Field cleared: show placeholder again
        #    self._init_placeholder()

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

    def addHistory(self, text):
        if text and text not in self._history:
            self._history.append(text)
        self._history_index = len(self._history)

    def setSuggestions(self, suggestions):
        self._suggestions = suggestions

    def keyPressEvent(self, event):

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self._enter_press_callback:
                self._enter_press_callback()
        
        elif event.key() == Qt.Key_Up:
            if self._history and self._history_index > 0:
                self._history_index -= 1
                
                self.blockSignals(True)
                self.setPlainText(self._history[self._history_index])
                self.blockSignals(False)

                self.moveCursor(QTextCursor.End)
        elif event.key() == Qt.Key_Down:
            if self._history and self._history_index < len(self._history) - 1:
                self._history_index += 1

                self.blockSignals(True)
                self.setPlainText(self._history[self._history_index])
                self.blockSignals(False)

                self.moveCursor(QTextCursor.End)
        elif event.key() == Qt.Key_Tab:
            self._applySuggestion()
        else:
            super().keyPressEvent(event)

    def _applySuggestion(self):
        current_text = self.toPlainText()
        if not current_text:
            return

        self._current_suggestions = [
            s for s in self._suggestions if s.startswith(current_text)
        ]
        if self._current_suggestions:
            next_suggestion = self._current_suggestions[0]

            self.blockSignals(True)
            self.setPlainText(next_suggestion)
            self.blockSignals(False)
            
            self.moveCursor(QTextCursor.End)


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


class GlobalSignals(QObject):

    signal_update_sql_run_status = pyqtSignal(dict)

    def __init__(self):
        super().__init__()


global_signals = GlobalSignals()

