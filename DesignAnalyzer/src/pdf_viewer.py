import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from typing import List

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QLineEdit, QFrame
)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter
from PyQt5.QtCore import Qt

import logging

logging.getLogger("pdfminer").setLevel(logging.WARNING)
logging.getLogger("pdfplumber").setLevel(logging.WARNING)


class PDFViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_doc = None
        self.page_images = []
        self.original_images = []
        self.current_pdf_file = None
        self.matches = []
        self.current_match_index = -1
        self.zoom_factor = 2.0

        # Lazy loading control
        self.total_pages = 0
        self.current_start = 1
        self.current_end = 1
        self.preloaded_next = None
        self.preloaded_prev = None

        self.initUI()
        self.setLayout(self.layout)

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)

        # Control box (top-right floating, NOT added to layout)
        self.control_box = QFrame(self)
        self.control_box.setParent(self)
        self.control_box.setFrameShape(QFrame.Box)
        self.control_box.setStyleSheet("background-color: white; border: 1px solid gray;")
        self.control_box.setFixedSize(340, 100)

        # Controls layout (two rows)
        ctrl_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        # Use Unicode double arrows for up/down
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
    # Main PDF loading logic
    # --------------------
    def loadPdf(self, pdf_file: str):
        self.current_pdf_file = pdf_file
        self.pdf_doc = fitz.open(pdf_file)
        self.matches.clear()
        self.current_match_index = -1

        self.total_pages = len(self.pdf_doc)
        self.current_start = 1
        self.current_end = min(10, self.total_pages)

        self.preloaded_next = None
        self.preloaded_prev = None

        self._loadPages(self.current_start, self.current_end)
        self._preload_next_chunk()
        self._preload_prev_chunk()

        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll)

    def _renderPages(self, start: int, end: int):
        rendered = []
        for page_num in range(start - 1, end):
            page = self.pdf_doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom_factor, self.zoom_factor))
            if pix.alpha:
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)
            else:
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            rendered.append(img.copy())
        return rendered

    def _loadPages(self, start: int, end: int, preloaded_images=None):
        start = max(1, start)
        end = min(self.total_pages, end)

        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.page_images.clear()
        self.original_images.clear()

        if preloaded_images is None:
            preloaded_images = self._renderPages(start, end)

        for i, img in enumerate(preloaded_images):
            label = QLabel()
            label.setPixmap(QPixmap.fromImage(img))
            self.content_layout.addWidget(label)
            page_obj = self.pdf_doc[start - 1 + i]
            self.page_images.append((page_obj, label))
            self.original_images.append(img)

        self.current_start = start
        self.current_end = end

        self._preload_next_chunk()
        self._preload_prev_chunk()

    def _preload_next_chunk(self):
        if self.current_end < self.total_pages:
            start = self.current_end + 1
            end = min(start + 9, self.total_pages)
            imgs = self._renderPages(start, end)
            self.preloaded_next = (start, end, imgs)
        else:
            self.preloaded_next = None

    def _preload_prev_chunk(self):
        if self.current_start > 1:
            end = self.current_start - 1
            start = max(1, end - 9)
            imgs = self._renderPages(start, end)
            self.preloaded_prev = (start, end, imgs)
        else:
            self.preloaded_prev = None

    def on_scroll(self, value):
        bar = self.scroll_area.verticalScrollBar()
        max_val = bar.maximum()
        min_val = bar.minimum()

        if value >= max_val - 50 and self.preloaded_next:
            start, end, imgs = self.preloaded_next
            self._loadPages(start, end, preloaded_images=imgs)
        elif value <= min_val + 50 and self.preloaded_prev:
            start, end, imgs = self.preloaded_prev
            self._loadPages(start, end, preloaded_images=imgs)

    # --------------------
    # Zoom Controls
    # --------------------
    def zoom_in(self):
        self.zoom_factor = min(self.zoom_factor + 0.25, 5.0)
        self._loadPages(self.current_start, self.current_end)

    def zoom_out(self):
        self.zoom_factor = max(self.zoom_factor - 0.25, 0.5)
        self._loadPages(self.current_start, self.current_end)

    def zoom_fit(self):
        self.zoom_factor = 1.0
        self._loadPages(self.current_start, self.current_end)

    # --------------------
    # Navigation
    # --------------------
    def scroll_to_top(self):
        self.scroll_area.verticalScrollBar().setValue(0)

    def scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    # --------------------
    # Search & Highlight
    # --------------------
    def search_text(self, direction='down'):
        text = self.search_input.text().strip()
        if not text or not self.pdf_doc:
            return

        if not hasattr(self, '_last_search_text') or self._last_search_text != text:
            self.matches = []
            self.current_match_index = -1
            self._last_search_text = text
            for page_num, page in enumerate(self.pdf_doc):
                text_instances = page.search_for(text, quads=False)
                for inst in text_instances:
                    self.matches.append((page_num, inst))

        if not self.matches:
            return

        if direction == 'down':
            self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        elif direction == 'up':
            self.current_match_index = (self.current_match_index - 1) % len(self.matches)

        page_num, rect = self.matches[self.current_match_index]

        if not (self.current_start - 1 <= page_num <= self.current_end - 1):
            start = (page_num // 10) * 10 + 1
            end = min(start + 9, self.total_pages)
            self._loadPages(start, end)

        self.highlight_match(page_num, rect)

    def highlight_match(self, page_num, rect):
        if not (self.current_start - 1 <= page_num <= self.current_end - 1):
            return

        idx = page_num - (self.current_start - 1)
        page, label = self.page_images[idx]

        img = self.original_images[idx].copy()
        painter = QPainter(img)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 0, 100))
        r = fitz.Rect(rect)
        zoom = self.zoom_factor
        painter.drawRect(int(r.x0 * zoom), int(r.y0 * zoom),
                         int(r.width * zoom), int(r.height * zoom))
        painter.end()

        label.setPixmap(QPixmap.fromImage(img))
        label_pos = label.pos().y()
        self.scroll_area.verticalScrollBar().setValue(label_pos - 20)

    # --------------------
    # Extraction helpers
    # --------------------
    def getAllTables(self) -> List:
        if not self.current_pdf_file:
            return []
        tables = []
        with pdfplumber.open(self.current_pdf_file) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    tables.append(pd.DataFrame(table))
        return tables

    def getAllImages(self) -> List[QImage]:
        images = []
        if not self.pdf_doc:
            return []
        for page in self.pdf_doc:
            img_list = page.get_images(full=True)
            for img in img_list:
                xref = img[0]
                base_img = self.pdf_doc.extract_image(xref)
                img_bytes = base_img["image"]
                image = QImage.fromData(img_bytes)
                images.append(image)
        return images

    def getPagesText(self) -> List[str]:
        if not self.current_pdf_file:
            return []
        pages_text = []
        with pdfplumber.open(self.current_pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                pages_text.append(text if text else "")
        return pages_text
