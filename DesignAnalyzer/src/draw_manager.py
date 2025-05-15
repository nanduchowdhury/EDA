from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

from rtree import index


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

