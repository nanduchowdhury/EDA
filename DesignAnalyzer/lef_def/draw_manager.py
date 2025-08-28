from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizePolicy, QFrame, QGridLayout
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import QBrush, QColor, QCursor, QPen, QPainter, QFont

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

        self.selected_instances = set()
        self.selected_layer_rects = {}


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
                    self.drawArea.drawRects(rect_list=wire_rects, color=color)

                wire_points = self.design_data.defParserImplement.get_wire_points(wire)

                if wire_points and len(wire_points) > 0:
                    wire_points_scaled = [tuple(v / self.design_data.defParserImplement.get_unit() for v in pt) for pt in wire_points]
                    self.drawArea.drawConnectingPoints(wire_points_scaled, color)

                print(f"Finished drawing {len(wire_rects)} rects and {len(wire_points)} points on layer {layerId} with color {color}")


        self.drawArea.refresh()


    def clear_selection(self):
       
        self.select_unselect_draw_inst_ids(id_list=self.selected_instances, do_what="UNSELECT")

        self.selected_instances.clear()
        self.selected_layer_rects.clear()

    
    def select_unselect_draw_inst_ids(self, id_list, do_what="DRAW"):
        
        if not id_list:
            return

        self.selected_instances.update(id_list)

        rects = self.get_instance_rects(id_list)
        rects_scaled = [tuple(v / self.design_data.defParserImplement.get_unit() for v in rect) for rect in rects]

        if do_what == "DRAW":
            self.drawArea.drawRects(rect_list=rects_scaled, color=QColor("gray"), brush=True)
        elif do_what == "UNSELECT":
            self.drawArea.drawRects(rect_list=rects_scaled, color=QColor("gray"))
        elif do_what == "SELECT":
            self.drawArea.drawRects(rect_list=rects_scaled, color=QColor("white"))


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


    def zoom_instances(self, instList):

        rects = self.get_instance_rects(instList)
        rects_scaled = [tuple(v / self.design_data.defParserImplement.get_unit() for v in rect) for rect in rects]

        if not rects_scaled:
            return

        self.zoom_rects(rects_scaled)


    def zoom_rects(self, rect_list):
        """
        Zooms the view to fit the given list of rectangles.
        Each rectangle should be a tuple (x, y, w, h).
        """
        if not rect_list:
            return

        min_x = min(rect[0] for rect in rect_list)
        min_y = min(rect[1] for rect in rect_list)
        max_x = max(rect[0] + rect[2] for rect in rect_list)
        max_y = max(rect[1] + rect[3] for rect in rect_list)

        bbox = (min_x, min_y, max_x, max_y)

        self.drawArea.zoomBbox(bbox)


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

