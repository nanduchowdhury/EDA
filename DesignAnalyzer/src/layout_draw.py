from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

from rtree import index

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


class DrawManager:
    def __init__(self, view, rightScale, bottomScale):
        self.view = view
        self.rightScale = rightScale
        self.bottomScale = bottomScale

        self.view.layout_draw = self
        self.instances = {}
        self.rtree_index = None

        # Disable scrollbars completely
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        self._zoom_factor = 1.25
        self._current_scale = 1.0
        self.base_scale = 1.0
        self.bounding_box = None

    def setInstances(self, instance_dict):
        self.instances = instance_dict
        self.rtree_index = index.Index()

        all_x, all_y = [], []

        for i, (inst_name, data) in enumerate(self.instances.items()):
            x1, y1, x2, y2 = data["coords"]
            bbox = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            self.rtree_index.insert(i, bbox)
            data["bbox"] = bbox
            data["id"] = i

            all_x.extend([x1, x2])
            all_y.extend([y1, y2])

        if not all_x or not all_y:
            return

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        self.bounding_box = (min_x, max_x, min_y, max_y)

        self.rightScale.setMinMax(min_y, max_y)
        self.bottomScale.setMinMax(min_x, max_x)

    def drawInstances(self):
        """Initial draw: fit all instances to view by computing base_scale"""
        self.scene.clear()

        if not self.instances or not self.bounding_box:
            return

        min_x, max_x, min_y, max_y = self.bounding_box
        view_width = self.view.viewport().width()
        view_height = self.view.viewport().height()

        width_um = max_x - min_x
        height_um = max_y - min_y

        scale_x = view_width / width_um if width_um else 1
        scale_y = view_height / height_um if height_um else 1
        self.base_scale = min(scale_x, scale_y)
        self._current_scale = 1.0

        self._drawVisibleInstances()

    def _drawVisibleInstances(self):
        """Draw instances that intersect visible view rectangle"""
        self.scene.clear()

        if not self.bounding_box or not self.rtree_index:
            return

        min_x, max_x, min_y, max_y = self.bounding_box
        scale = self.base_scale * self._current_scale

        view_width = self.view.viewport().width()
        view_height = self.view.viewport().height()

        # Get visible area in layout coords
        visible_min_x = min_x
        visible_max_x = min_x + view_width / scale
        visible_max_y = max_y
        visible_min_y = max_y - view_height / scale

        visible_bbox = (visible_min_x, visible_min_y, visible_max_x, visible_max_y)

        visible_ids = list(self.rtree_index.intersection(visible_bbox))

        for i in visible_ids:
            # Retrieve instance by id
            inst = next(inst for inst in self.instances.values() if inst["id"] == i)
            x1, y1, x2, y2 = inst["bbox"]

            # Transform to screen coords
            sx1 = (x1 - min_x) * scale
            sy1 = (max_y - y1) * scale
            sx2 = (x2 - min_x) * scale
            sy2 = (max_y - y2) * scale

            x = min(sx1, sx2)
            y = min(sy1, sy2)
            w = abs(sx2 - sx1)
            h = abs(sy2 - sy1)

            rect_item = QGraphicsRectItem(QRectF(x, y, w, h))
            rect_item.setBrush(QBrush(QColor(200, 100, 100, 120)))
            rect_item.setPen(QColor(0, 0, 0))
            self.scene.addItem(rect_item)

    def zoom_in(self):
        self._current_scale *= self._zoom_factor
        self._drawVisibleInstances()

    def zoom_out(self):
        self._current_scale /= self._zoom_factor
        self._drawVisibleInstances()

    def fit_to_view(self):
        self._current_scale = 1.0
        self._drawVisibleInstances()




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