from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

from rtree import index

from draw_manager import DrawManager

class LayoutView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.start_pos = None
        self.temp_rect_item = None
        self.layout_draw = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = self.mapToScene(event.pos())
            if self.temp_rect_item:
                self.scene().removeItem(self.temp_rect_item)
                self.temp_rect_item = None

    def mouseMoveEvent(self, event):
        if self.start_pos:
            end_pos = self.mapToScene(event.pos())
            rect = QRectF(self.start_pos, end_pos).normalized()

            if self.temp_rect_item:
                self.temp_rect_item.setRect(rect)
            else:
                pen = QPen(QColor(0, 0, 255), 1, Qt.DashLine)
                self.temp_rect_item = QGraphicsRectItem(rect)
                self.temp_rect_item.setPen(pen)
                self.temp_rect_item.setBrush(QColor(0, 0, 255, 40))
                self.scene().addItem(self.temp_rect_item)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.temp_rect_item:
            selection_rect = self.temp_rect_item.rect()
            self.find_instances_in_rect(selection_rect)
            self.start_pos = None

    def find_instances_in_rect(self, rect: QRectF):
        if self.layout_draw:
            selected = []
            for name, data in self.layout_draw.instances.items():
                item = data.get("graphics_item")
                if item and rect.contains(item.rect().center()):
                    selected.append((name, data["coords"]))
            print("\n[Selected Instances in Region]")
            for name, coords in selected:
                print(f"{name}: {coords}")



class ScaleWidget(QLabel):
    def __init__(self, orientation, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.min_val = 0
        self.max_val = 100

        if orientation == Qt.Horizontal:
            self.setFixedHeight(40)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            self.setFixedWidth(50)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.setStyleSheet("background-color: #333; color: white;")
        self.markers = []  # (pos_px, label_str)

    def setMinMax(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        self.update()  # trigger repaint

    def updateMarker(self):
        self.markers.clear()

        range_val = self.max_val - self.min_val
        if range_val <= 0:
            return

        step = range_val / 10  # 10 steps approx
        width = self.width()
        height = self.height()

        val = self.min_val
        while val <= self.max_val + 1e-6:  # small epsilon for float precision
            ratio = (val - self.min_val) / range_val
            if self.orientation == Qt.Horizontal:
                x = int(ratio * width)
                self.markers.append((x, f"{val:.1f}"))  # round to 1 decimal
            else:
                y = int(ratio * height)
                self.markers.append((y, f"{val:.1f}"))
            val += step


    def paintEvent(self, event):
        super().paintEvent(event)

        self.updateMarker()

        painter = QPainter(self)
        painter.setPen(Qt.white)
        font = QFont("Arial", 6, QFont.Bold)
        painter.setFont(font)

        if self.orientation == Qt.Horizontal:
            for x, label in self.markers:
                painter.drawLine(x, 0, x, 10)
                painter.drawText(x + 2, self.height() - 20, label)
        else:
            for y, label in self.markers:
                painter.drawLine(0, y, 10, y)
                painter.drawText(12, y + 4, label)




class LayoutAreaWithScales(QWidget):
    def __init__(self, width=800, height=600, parent=None):
        super().__init__(parent)
        self.view = LayoutView()
        self.view.setMinimumSize(width - 100, height - 300)

        self.rightScale = ScaleWidget(Qt.Vertical)
        self.bottomScale = ScaleWidget(Qt.Horizontal)

        self.drawManager = DrawManager(self.view, 
                        self.rightScale, self.bottomScale)

        self.setupLayout()

    def setupLayout(self):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.view,        0, 0)
        layout.addWidget(self.rightScale,  0, 1)
        layout.addWidget(self.bottomScale, 1, 0)

        spacer = QWidget()  # bottom-right corner (blank)
        spacer.setFixedSize(30, 20)
        # layout.addWidget(spacer, 1, 1)

        self.setLayout(layout)

    def showCurrentPosition(self, x, y):
        self.bottomScale.setText(f"X: {x}")
        self.rightScale.setText(f"Y: {y}")