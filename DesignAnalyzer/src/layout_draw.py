from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QGraphicsRectItem
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QBrush, QColor

class LayoutDraw:
    def __init__(self, view):
        self.view = view
        self.instances = {}

        # Create the scene and set its size to match the widget
        self.scene = QGraphicsScene(0, 0, view.width(), view.height())

        # Assign the scene directly to the widget (QGraphicsView)
        self.view.setScene(self.scene)

        print(f"[LayoutDraw] Widget size: {view.width()} x {view.height()}")

    def setInstances(self, instance_dict):
        self.instances = instance_dict

    def drawInstances(self):
        self.scene.clear()

        if not self.instances:
            return

        # Compute bounds
        all_x = []
        all_y = []
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
        scale = min(scale_x, scale_y)

        for inst_name, data in self.instances.items():
            x1, y1, x2, y2 = data["coords"]
            x = (x1 - min_x) * scale
            y = (max_y - y2) * scale  # flip Y axis
            w = (x2 - x1) * scale
            h = (y2 - y1) * scale

            rect = QGraphicsRectItem(QRectF(x, y, w, h))
            rect.setBrush(QBrush(QColor(200, 100, 100, 120)))
            rect.setPen(QColor(0, 0, 0))
            self.scene.addItem(rect)
