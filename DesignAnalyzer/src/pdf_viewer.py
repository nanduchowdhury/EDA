


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

        # Control box (top-right floating)
        self.control_box = QFrame(self)
        self.control_box.setFrameShape(QFrame.Box)
        self.control_box.setStyleSheet("background-color: white; border: 1px solid gray;")
        self.control_box.setFixedSize(300, 60)

        # Controls layout
        ctrl_layout = QHBoxLayout()
        self.btn_scroll_top = QPushButton("↑")
        self.btn_scroll_bottom = QPushButton("↓")
        self.search_input = QLineEdit()
        self.btn_search_up = QPushButton("↑")
        self.btn_search_down = QPushButton("↓")

        ctrl_layout.addWidget(self.btn_scroll_top)
        ctrl_layout.addWidget(self.btn_scroll_bottom)
        ctrl_layout.addWidget(self.search_input)
        ctrl_layout.addWidget(self.btn_search_up)
        ctrl_layout.addWidget(self.btn_search_down)
        self.control_box.setLayout(ctrl_layout)

        self.layout.addWidget(self.control_box, alignment=Qt.AlignTop | Qt.AlignRight)

        # Connect
        self.btn_scroll_top.clicked.connect(self.scroll_to_top)
        self.btn_scroll_bottom.clicked.connect(self.scroll_to_bottom)
        self.btn_search_up.clicked.connect(lambda: self.search_text(direction='up'))
        self.btn_search_down.clicked.connect(lambda: self.search_text(direction='down'))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.control_box.move(self.width() - self.control_box.width() - 10, 10)

    def loadPdf(self, pdf_file: str):
        self.current_pdf_file = pdf_file
        self.pdf_doc = fitz.open(pdf_file)
        self.page_images.clear()
        self.matches.clear()
        self.current_match_index = -1

        # Clear previous content
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Render pages
        for page in self.pdf_doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            # Choose format based on alpha
            if pix.alpha:
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)
            else:
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            img = img.copy()  # Ensure the image data is copied and valid

            label = QLabel()
            label.setPixmap(QPixmap.fromImage(img))
            self.content_layout.addWidget(label)
            self.page_images.append((page, label))


    def scroll_to_top(self):
        self.scroll_area.verticalScrollBar().setValue(0)

    def scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())

    def search_text(self, direction='down'):
        text = self.search_input.text().strip()
        if not text or not self.pdf_doc:
            return

        if not self.matches:
            # Collect all matches across pages
            self.matches = []
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

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGBA8888)

        # Draw rectangle highlight
        painter = QPainter(img)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 0, 100))  # Yellow transparent
        r = fitz.Rect(rect)
        zoom = 2
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

