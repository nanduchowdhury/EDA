from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

from rtree import index


class DrawManager:
    def __init__(self, drawArea):
        self.drawArea = drawArea

        self.view = self.drawArea.view

        self.bounding_box = None

        self._zoom_factor = 1.25
        self._current_scale = 1.0
        self.base_scale = 1.0


    def set_scale(self, bbox):

        self.bounding_box = bbox
        (min_x, min_y, max_x, max_y) = bbox

        # self.rightScale.setMinMax(min_y, max_y)
        # self.bottomScale.setMinMax(min_x, max_x)

        view_width = self.view.viewport().width()
        view_height = self.view.viewport().height()

        width_um = max_x - min_x
        height_um = max_y - min_y

        scale_x = view_width / width_um if width_um else 1
        scale_y = view_height / height_um if height_um else 1
        self.base_scale = min(scale_x, scale_y)
        self._current_scale = 1.0


    def load_design_instances(self, rtree, designInstances):

        self.designInstances = designInstances


        visible_bbox = rtree.get_bounds()

        visible_ids = list(rtree.intersection(visible_bbox))

        self.draw_instances(visible_ids, QColor(0, 0, 0))


    def draw_instances(self, instList, color):

        rect_list = []

        for i in instList:
            inst = self.designInstances.instance_data[i]
            x1, y1, x2, y2 = inst.location

            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)

            rect_list.append((x, y, w, h))

        self.drawArea.drawRects(rect_list)

    def draw_instances_1(self, instList, color):

        min_x, min_y, max_x, max_y = self.bounding_box
        scale = self.base_scale * self._current_scale

        for i in instList:
            inst = self.designInstances.instance_data[i]
            x1, y1, x2, y2 = inst.location

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
            rect_item.setPen(color)
            # self.scene.addItem(rect_item)


    def zoom_in(self):
        self._current_scale *= self._zoom_factor
        self._drawVisibleInstances()

    def zoom_out(self):
        self._current_scale /= self._zoom_factor
        self._drawVisibleInstances()

    def fit_to_view(self):
        self._current_scale = 1.0
        self._drawVisibleInstances()

