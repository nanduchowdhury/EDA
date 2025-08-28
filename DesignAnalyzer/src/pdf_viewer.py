from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QFrame
)
from PySide6.QtCore import Qt, QModelIndex, QPointF
from PySide6.QtPdf import QPdfDocument, QPdfSearchModel
from PySide6.QtPdfWidgets import QPdfView


import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from typing import List
from PySide6.QtGui import QImage

import logging

logging.getLogger("pdfminer").setLevel(logging.WARNING)
logging.getLogger("pdfplumber").setLevel(logging.WARNING)

class PDFViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_doc = QPdfDocument(self)
        self.current_pdf_file = None
        self.search_model = QPdfSearchModel(self)
        self.current_match_index = -1

        self.initUI()
        self.setLayout(self.layout)

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # The actual PDF view widget
        self.pdf_view = QPdfView()
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)

        self.layout.addWidget(self.pdf_view)

        # Floating control box
        self.control_box = QFrame(self)
        self.control_box.setParent(self)
        self.control_box.setFrameShape(QFrame.Shape.Box)
        self.control_box.setStyleSheet("background-color: white; border: 1px solid gray;")
        self.control_box.setFixedSize(340, 100)

        ctrl_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        self.btn_scroll_top = QPushButton("⇑")
        self.btn_scroll_bottom = QPushButton("⇓")
        self.search_input = QLineEdit()
        self.btn_search_up = QPushButton("↑")
        self.btn_search_down = QPushButton("↓")
        row1.addWidget(self.btn_scroll_top)
        row1.addWidget(self.btn_scroll_bottom)
        row1.addWidget(self.search_input)
        row1.addWidget(self.btn_search_up)
        row1.addWidget(self.btn_search_down)

        row2 = QHBoxLayout()
        self.btn_zoom_in = QPushButton("Z+")
        self.btn_zoom_out = QPushButton("Z-")
        self.btn_zoom_fit = QPushButton("Zf")
        row2.addWidget(self.btn_zoom_in)
        row2.addWidget(self.btn_zoom_out)
        row2.addWidget(self.btn_zoom_fit)

        ctrl_layout.addLayout(row1)
        ctrl_layout.addLayout(row2)
        self.control_box.setLayout(ctrl_layout)

        # Connect
        self.btn_scroll_top.clicked.connect(self.scroll_to_top)
        self.btn_scroll_bottom.clicked.connect(self.scroll_to_bottom)
        self.btn_search_up.clicked.connect(lambda: self.search_text(direction='up'))
        self.btn_search_down.clicked.connect(lambda: self.search_text(direction='down'))
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_fit.clicked.connect(self.zoom_fit)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.control_box.move(self.width() - self.control_box.width() - 40, 10)

    # --------------------
    # Load PDF
    # --------------------
    def loadPdf(self, pdf_file: str):
        self.current_pdf_file = pdf_file
        self.pdf_doc.load(pdf_file)
        self.pdf_view.setDocument(self.pdf_doc)
        self.search_model.setDocument(self.pdf_doc)
        self.current_match_index = -1

    # --------------------
    # Zoom Controls
    # --------------------
    def zoom_in(self):
        self.pdf_view.setZoomFactor(self.pdf_view.zoomFactor() + 0.25)

    def zoom_out(self):
        self.pdf_view.setZoomFactor(max(0.5, self.pdf_view.zoomFactor() - 0.25))

    def zoom_fit(self):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

    # --------------------
    # Navigation
    # --------------------
    def scroll_to_top(self):
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)
        self.pdf_view.pageNavigator().jump(0, QPointF(0.0, 0.0))

    def scroll_to_bottom(self):
        last_page = self.pdf_doc.pageCount() - 1
        self.pdf_view.pageNavigator().jump(last_page, QPointF(1.0, 1.0))

    # --------------------
    # Search & Highlight
    # --------------------

    def search_text(self, direction='down'):
        text = self.search_input.text().strip()
        if not text:
            return

        # Run search
        self.search_model.setSearchString(text)

        if self.search_model.rowCount(QModelIndex()) == 0:
            return

        if direction == 'down':
            self.current_match_index = (self.current_match_index + 1) % self.search_model.rowCount(QModelIndex())
        elif direction == 'up':
            self.current_match_index = (self.current_match_index - 1) % self.search_model.rowCount(QModelIndex())

        match_count = self.search_model.rowCount(QModelIndex())
        print(f"Match {self.current_match_index + 1} of {match_count}")

        idx = self.search_model.index(self.current_match_index, 0)
        page = idx.data(QPdfSearchModel.Role.Page.value)

        self.pdf_view.pageNavigator().jump(page, QPointF(0, 0))
        self.pdf_view.setCurrentSearchResultIndex(self.current_match_index)

        print(f"Jumped to page {page}")

    # --------------------
    # Helpers
    # --------------------
    def get_file_base_name(self):
        if self.current_pdf_file:
            return self.current_pdf_file.split('/')[-1]
        return None





class PDFViewerWithExtract(PDFViewer):  # extend the QtPdf-based viewer
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdfplumber_pages = None
        self._fitz_doc = None

    def loadPdf(self, pdf_file: str):
        super().loadPdf(pdf_file)

        # also open with fitz/pdfplumber for extraction
        self._fitz_doc = fitz.open(pdf_file)
        self._pdfplumber_pages = pdfplumber.open(pdf_file)

    # --------------------
    # Extraction helpers
    # --------------------
    def getPagesText(self) -> List[str]:
        if not self._pdfplumber_pages:
            return []
        texts = []
        for page in self._pdfplumber_pages.pages:
            text = page.extract_text()
            texts.append(text if text else "")
        return texts

    def getAllTables(self) -> List[pd.DataFrame]:
        if not self._pdfplumber_pages:
            return []
        tables = []
        for page in self._pdfplumber_pages.pages:
            for table in page.extract_tables():
                tables.append(pd.DataFrame(table))
        return tables

    def getAllImages(self) -> List[QImage]:
        images = []
        if not self._fitz_doc:
            return []
        for page in self._fitz_doc:
            for img in page.get_images(full=True):
                xref = img[0]
                base_img = self._fitz_doc.extract_image(xref)
                img_bytes = base_img["image"]
                qimg = QImage.fromData(img_bytes)
                images.append(qimg)
        return images



