from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QBrush, QColor, QCursor, QPen


class LayoutView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.start_pos = None
        self.temp_rect_item = None
        self.layout_draw = None  # will be linked from LayoutDraw

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


class LayoutDraw:
    def __init__(self, view):
        self.view = view
        self.view.layout_draw = self  # link back
        self.instances = {}

        self.scene = QGraphicsScene(0, 0, view.width(), view.height())
        self.view.setScene(self.scene)

        self._zoom_factor = 1.25
        self._current_scale = 1.0

    def setInstances(self, instance_dict):
        self.instances = instance_dict

    def drawInstances(self):
        self.scene.clear()

        if not self.instances:
            return

        all_x, all_y = [], []
        for data in self.instances.values():
            x1, y1, x2, y2 = data["coords"]
            all_x.extend([x1, x2])
            all_y.extend([y1, y2])

        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)

        width_um = max_x - min_x
        height_um = max_y - min_y

        view_width = self.view.viewport().width()
        view_height = self.view.viewport().height()

        scale_x = view_width / width_um if width_um else 1
        scale_y = view_height / height_um if height_um else 1
        self.base_scale = min(scale_x, scale_y)
        self._current_scale = 1.0

        for inst_name, data in self.instances.items():
            x1, y1, x2, y2 = data["coords"]
            x = (x1 - min_x) * self.base_scale
            y = (max_y - y2) * self.base_scale  # Y flip
            w = (x2 - x1) * self.base_scale
            h = (y2 - y1) * self.base_scale

            rect_item = QGraphicsRectItem(QRectF(x, y, w, h))
            rect_item.setBrush(QBrush(QColor(200, 100, 100, 120)))
            rect_item.setPen(QColor(0, 0, 0))
            self.scene.addItem(rect_item)

            data["graphics_item"] = rect_item

        self.view.resetTransform()
        self.view.scale(self.base_scale, self.base_scale)


    def zoom_in(self):
        self.view.scale(self._zoom_factor, self._zoom_factor)
        self._current_scale *= self._zoom_factor

    def zoom_out(self):
        self.view.scale(1 / self._zoom_factor, 1 / self._zoom_factor)
        self._current_scale /= self._zoom_factor

    def fit_to_view(self):
        self.view.resetTransform()
        self.view.scale(self.base_scale, self.base_scale)
        self._current_scale = 1.0


