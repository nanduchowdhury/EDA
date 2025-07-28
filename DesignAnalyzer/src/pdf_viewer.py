


import fitz  # PyMuPDF
from matplotlib.pylab import size
import pdfplumber
import pandas as pd
from typing import List

from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QLineEdit, QFrame, QApplication
)
from PyQt5.QtGui import QPixmap, QImage, QColor, QPainter
from PyQt5.QtCore import Qt


class PDFViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_doc = None
        self.page_images = []
        self.current_pdf_file = None
        self.matches = []
        self.current_match_index = -1

        self.original_images = []
        self.zoom_factor = 2.0  # Default zoom

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
        self.btn_scroll_top = QPushButton("↑")
        self.btn_scroll_bottom = QPushButton("↓")
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
        row2.addWidget(self.btn_zoom_in)
        row2.addWidget(self.btn_zoom_out)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.control_box.move(self.width() - self.control_box.width() - 10, 10)

    def loadPdf(self, pdf_file: str):
        self.current_pdf_file = pdf_file
        self.pdf_doc = fitz.open(pdf_file)
        self.page_images.clear()
        self.original_images = []
        self.matches.clear()
        self.current_match_index = -1

        # Clear previous content
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Render pages
        for page in self.pdf_doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom_factor, self.zoom_factor))
            if pix.alpha:
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)
            else:
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            img = img.copy()  # Ensure the image data is copied and valid

            label = QLabel()
            label.setPixmap(QPixmap.fromImage(img))
            self.content_layout.addWidget(label)
            self.page_images.append((page, label))
            self.original_images.append(img)  # Store original image for highlighting

    def zoom_in(self):
        self.zoom_factor = min(self.zoom_factor + 0.25, 5.0)
        if self.current_pdf_file:
            self.loadPdf(self.current_pdf_file)
            # Restore highlights if a search is active
            if hasattr(self, '_last_search_text') and self._last_search_text and self.matches:
                self.search_text(direction='down')

    def zoom_out(self):
        self.zoom_factor = max(self.zoom_factor - 0.25, 0.5)
        if self.current_pdf_file:
            self.loadPdf(self.current_pdf_file)
            # Restore highlights if a search is active
            if hasattr(self, '_last_search_text') and self._last_search_text and self.matches:
                self.search_text(direction='down')


    def scroll_to_top(self):
        self.scroll_area.verticalScrollBar().setValue(0)

    def scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def search_text(self, direction='down'):
        text = self.search_input.text().strip()
        if not text or not self.pdf_doc:
            return

        # Always clear previous matches and highlights when the search text changes
        if not hasattr(self, '_last_search_text') or self._last_search_text != text:
            self.matches = []
            self.current_match_index = -1
            self._last_search_text = text
            # Restore all pages to original images (remove previous highlights)
            for i, (page, label) in enumerate(self.page_images):
                label.setPixmap(QPixmap.fromImage(self.original_images[i]))

        if not self.matches:
            # Collect all matches across pages
            for page_num, page in enumerate(self.pdf_doc):
                text_instances = page.search_for(text, quads=False)
                for inst in text_instances:
                    self.matches.append((page_num, inst))

        if not self.matches:
            return

        # Move match index
        if direction == 'down':
            self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        else:
            self.current_match_index = (self.current_match_index - 1) % len(self.matches)

        page_num, rect = self.matches[self.current_match_index]
        self.highlight_match(page_num, rect)

    def highlight_match(self, page_num, rect):
        page, label = self.page_images[page_num]

        # Start from the original image for this page
        img = self.original_images[page_num].copy()

        # Draw rectangle highlight
        painter = QPainter(img)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 0, 100))  # Yellow transparent
        r = fitz.Rect(rect)
        zoom = self.zoom_factor  # Use current zoom factor!
        painter.drawRect(int(r.x0 * zoom), int(r.y0 * zoom), int(r.width * zoom), int(r.height * zoom))
        painter.end()

        label.setPixmap(QPixmap.fromImage(img))

        # Scroll to view
        label_pos = label.pos().y()
        self.scroll_area.verticalScrollBar().setValue(label_pos - 20)

    def getAllTables(self) -> List:
        if not self.current_pdf_file:
            return []

        tables = []
        with pdfplumber.open(self.current_pdf_file) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    import pandas as pd
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
                fmt = base_img["ext"]
                image = QImage.fromData(img_bytes)
                images.append(image)
        return images

