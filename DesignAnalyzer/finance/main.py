
import sys
import os
import pdfplumber

# Append the absolute path of ../src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from blue_payload import run_BluePayload
from main_ui import MainUI


class FinanceUI(MainUI):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LefDef UI")


    def read_pdf(self):
        
        with pdfplumber.open("statement.pdf") as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    for row in table:
                        print(row)

if __name__ == "__main__":
    run_BluePayload(FinanceUI)


