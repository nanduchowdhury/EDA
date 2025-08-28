
import sys
from PySide6.QtWidgets import QApplication

from PySide6.QtGui import QFont

class BluePayload:
    def __init__(self):
        self.payload_class = None

    def setPayload(self, ui_class):
        """Set the UI class that will be instantiated in execute()."""
        self.payload_class = ui_class

    def execute(self):
        """Launch the PyQt application using the set payload class."""
        if self.payload_class is None:
            raise ValueError("Payload UI class not set. Use setPayload() before execute().")

        app = QApplication(sys.argv)

        # This is for migrating to PyQt6.
        app.setFont(QFont("Segoe UI", 9))
        app.setStyleSheet("""
                QWidget { font-size: 9pt; }
                QTabBar::tab { font-size: 9pt; }
            """)

        window = self.payload_class()  # create instance of the class
        window.create_GUI()
        window.show()
        sys.exit(app.exec())


def run_BluePayload(bluePayload_ui_obj):

    launcher = BluePayload()
    launcher.setPayload(bluePayload_ui_obj)
    launcher.execute()

