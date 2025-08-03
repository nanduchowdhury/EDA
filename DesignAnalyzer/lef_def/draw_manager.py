from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PyQt5.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

from global_name_index import gname_index

from rtree import index


class DrawManager:
    def __init__(self, drawArea, design_data):
        self.drawArea = drawArea
        self.design_data = design_data

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


    def draw_nets(self, net_name=None, layer_name=None):

        net_id = gname_index.get_id(net_name) if net_name else None
        layer_id = gname_index.get_id(layer_name) if layer_name else None

        nets = self.design_data.defParserImplement.get_nets()

        if len(nets) != 0:
            print(f'Number of nets: {len(nets)}')

        for nid in nets:
            if net_id is not None and nid != net_id:
                continue
            
            wires = self.design_data.defParserImplement.get_wires_of_net(nid, layer_id)

            if len(wires) != 0:
                print(f'Number of wires in net {nid}: {len(wires)}')

            for wire in wires:
                wire_rects = self.design_data.defParserImplement.get_wire_rects(wire)

                if len(wire_rects) != 0:
                    print(f'Number of rects in wire: {len(wire_rects)}')

                self.drawArea.drawRects(wire_rects, QColor("blue"))

                wire_points = self.design_data.defParserImplement.get_wire_points(wire)
                
                if len(wire_points) != 0:
                    print(f'Number of points in wire: {len(wire_points)}')

                self.drawArea.drawConnectingPoints(wire_points, QColor("yellow"))


    def draw_inst_names(self, name_list):

        id_list = []

        for name in name_list:
            inst_id = gname_index.get_id(name)
            if inst_id is None:
                continue

            id_list.append(inst_id)

        rects = self.get_instance_rects(id_list)
        self.drawArea.drawRects(rects, QColor("white"))

    def draw_instances_rtree(self, bbox=None):

        if len(self.design_data.inst_rtree) == 0:
            return

        if bbox is None:
            bbox = self.design_data.inst_rtree.get_bounds()

        visible_ids = list(self.design_data.inst_rtree.intersection(bbox))

        rects = self.get_instance_rects(visible_ids)
        self.drawArea.drawRects(rects, QColor("red"))

    def get_instance_rects(self, instList):
        rect_list = []

        for i in instList:
            id = i
            if isinstance(id, str):
                id = gname_index.get_id(i)

            inst = self.design_data.instData.instance_data[id]
            x1, y1, x2, y2 = inst.location

            x = min(x1, x2)
            y = min(y1, y2)
            w = abs(x2 - x1)
            h = abs(y2 - y1)

            rect_list.append((x, y, w, h))

        return rect_list


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

