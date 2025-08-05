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
        bbox = [v / self.design_data.defParserImplement.get_unit() for v in bbox]
        self.drawArea.set_view_limits(bbox)



    def draw_nets(self, net_name=None, layer_name=None):

        net_id = gname_index.get_id(net_name) if net_name else None
        layer_id = gname_index.get_id(layer_name) if layer_name else None

        nets = self.design_data.defParserImplement.get_nets()

        for nid in nets:
            if net_id is not None and nid != net_id:
                continue
            
            wires = self.design_data.defParserImplement.get_wires_of_net(nid, layer_id)

            for wire in wires:

                layerId = wire.layer
                color = self.design_data.layer_color_map.get(layerId, QColor("lightblue"))

                wire_rects = self.design_data.defParserImplement.get_wire_rects(wire)

                if wire_rects and len(wire_rects) > 0:
                    self.drawArea.drawRects(wire_rects, color)

                wire_points = self.design_data.defParserImplement.get_wire_points(wire)

                if wire_points and len(wire_points) > 0:
                    wire_points_scaled = [tuple(v / self.design_data.defParserImplement.get_unit() for v in pt) for pt in wire_points]
                    self.drawArea.drawConnectingPoints(wire_points_scaled, color)

                print(f"Finished drawing {len(wire_rects)} rects and {len(wire_points)} points on layer {layerId} with color {color}")


        self.drawArea.refresh()


    def draw_inst_names(self, name_list):

        id_list = []

        for name in name_list:
            inst_id = gname_index.get_id(name)
            if inst_id is None:
                continue

            id_list.append(inst_id)

        rects = self.get_instance_rects(id_list)
        rects_scaled = [tuple(v / self.design_data.defParserImplement.get_unit() for v in rect) for rect in rects]

        self.drawArea.drawRects(rects_scaled, QColor("white"))

    def draw_instances_rtree(self, bbox=None):

        if len(self.design_data.inst_rtree) == 0:
            return

        if bbox is None:
            bbox = self.design_data.inst_rtree.get_bounds()

        visible_ids = list(self.design_data.inst_rtree.intersection(bbox))

        rects = self.get_instance_rects(visible_ids)
        rects_scaled = [tuple(v / self.design_data.defParserImplement.get_unit() for v in rect) for rect in rects]

        self.drawArea.drawRects(rects_scaled, QColor("gray"))

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

