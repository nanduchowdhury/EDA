

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import QTimer, Qt
import sys

import logging
from datetime import datetime

class UILogHandler(logging.Handler):
    def __init__(self, ui_log_callback):
        super().__init__()
        self.ui_log_callback = ui_log_callback

    def emit(self, record):
        log_entry = self.format(record)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.ui_log_callback(now, log_entry)


from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPalette, QBrush, QLinearGradient, QColor
import sys

class ErrorManager:
    def __init__(self, parent, window_width, window_height, timeout=15000):

        self.parent = parent
        self.window_width = window_width
        self.window_height = window_height
        self.timeout = timeout

        self.popup_width = int(self.window_width * 0.45)

        self._build_popup()
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.popup.hide)


    def _build_popup(self):
        self.popup = QDialog(self.parent)
        # self.popup.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # self.popup.setAttribute(Qt.WA_TranslucentBackground)

        self.popup.resize(self.popup_width, 100)  # initial size

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color: black; font-size: 14px;")

        self.ok_button = QPushButton("OK")
        self.ok_button.setFixedSize(100, 45)
        self.ok_button.clicked.connect(self.popup.hide)

        layout.addWidget(self.label)
        layout.addWidget(self.ok_button)
        self.popup.setLayout(layout)

        # Set gradient background
        gradient = QLinearGradient(0, 0, 0, self.popup.height())
        gradient.setColorAt(0.0, QColor("#cce7ff"))
        gradient.setColorAt(1.0, QColor("#e6f2ff"))
        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(gradient))
        self.popup.setAutoFillBackground(True)
        self.popup.setPalette(palette)

    def showMessage(self, msg):

        logging.info(msg)

        self.label.setText(msg)
        self.popup.adjustSize()
        self._move_to_bottom_right()
        self.popup.show()
        self.timer.start(self.timeout)

    def _move_to_bottom_right(self):
        self.popup.resize(self.popup_width, self.popup.height())
        x = self.window_width - self.popup_width - 20
        y = self.window_height - self.popup.height() - 20
        self.popup.move(x, y)





