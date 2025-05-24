from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QFont

import pyqtgraph as pg

########################################################################
#
# Following are options of providing layout drawing capabilities
#
#   1. PyQtGraph
#   2. Matplotlib with FigureCanvasQTAgg
#   3. VisPy
#   4. Plotly + QWebEngineView
#   5. Leafmap / Folium + QWebEngineView
#   6. Mayavi or VTK with PyQt
#
########################################################################

class RulerWidget(QWidget):
    def __init__(self, orientation=Qt.Horizontal, color_bg="#222222", color_tick="#ffffff", parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.min_val = 0
        self.max_val = 100
        self.color_bg = color_bg
        self.color_tick = color_tick

        if self.orientation == Qt.Horizontal:
            self.setFixedHeight(30)
        else:
            self.setFixedWidth(40)

        self.setAutoFillBackground(True)

    def setRange(self, min_val, max_val):
        self.min_val = min_val
        self.max_val = max_val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.fillRect(self.rect(), QColor(self.color_bg))
            painter.setPen(QPen(QColor(self.color_tick)))
            painter.setFont(QFont("Arial", 6))

            range_val = self.max_val - self.min_val
            if range_val <= 0:
                return

            if self.orientation == Qt.Horizontal:
                width = self.width()
                step_px = 50
                step_val = range_val * step_px / width
                val = self.min_val
                while val <= self.max_val:
                    x = int((val - self.min_val) / range_val * width)
                    painter.drawLine(x, 0, x, self.height() // 3)
                    painter.drawText(x + 2, self.height() - 5, f"{val:.0f}")
                    val += step_val
            else:
                height = self.height()
                step_px = 50
                step_val = range_val * step_px / height
                val = self.min_val
                while val <= self.max_val:
                    y = int((val - self.min_val) / range_val * height)
                    painter.drawLine(0, y, self.width() // 3, y)
                    painter.drawText(5, y + 6, f"{val:.0f}")
                    val += step_val
        finally:
            painter.end()


class PyQtGraphLayoutWithScales(QWidget):
    def __init__(self, width=600, height=400, parent=None):
        super().__init__(parent)

        self.total_width = width
        self.total_height = height
        self.setFixedSize(self.total_width, self.total_height)

        self.initUI()

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # Ruler height and width
        rulerHeight = 30
        rulerWidth = 40

        # Create rulers with debug colors
        self.ruler_x = RulerWidget(Qt.Horizontal, color_bg="#552222", color_tick="#ffff00")
        self.ruler_y = RulerWidget(Qt.Vertical, color_bg="#225522", color_tick="#ffff00")

        # Create graphics view
        self.graphWidget = pg.GraphicsLayoutWidget()
        self.view = self.graphWidget.addViewBox(lockAspect=False, enableMenu=False)
        self.view.setMouseEnabled(x=True, y=True)

        # Add test rectangles (auto scaled)
        # self.populateGraphics()

        # Setup zoom/scroll signals
        self.view.sigRangeChanged.connect(self.updateRulers)

        # Layout setup
        centerLayout = QHBoxLayout()
        centerLayout.setContentsMargins(0, 0, 0, 0)
        centerLayout.setSpacing(0)
        centerLayout.addWidget(self.ruler_y)
        centerLayout.addWidget(self.graphWidget)

        self.mainLayout.addWidget(self.ruler_x)
        self.mainLayout.addLayout(centerLayout)

        # Set initial range
        self.view.autoRange()

    def populateGraphics(self):
        self.view.clear()
        for i in range(10):
            x, y, w, h = i * 50, i * 30, 40, 20
            rect = pg.QtWidgets.QGraphicsRectItem(x, y, w, h)
            rect.setPen(pg.mkPen('w'))
            rect.setBrush(pg.mkBrush(100, 100, 250, 120))
            self.view.addItem(rect)

    def updateRulers(self):
        rect = self.view.viewRect()
        self.ruler_x.setRange(rect.left(), rect.right())
        self.ruler_y.setRange(rect.top(), rect.bottom())

    def drawRects(self, rect_list):
        """
        Draw a list of rectangles on the view.
        Each item in rect_list should be a tuple: (x, y, width, height)
        """
        self.view.clear()  # Clear any existing items

        for rect in rect_list:
            x, y, w, h = rect
            item = pg.QtWidgets.QGraphicsRectItem(x, y, w, h)
            item.setPen(pg.mkPen('w'))
            item.setBrush(pg.mkBrush(150, 100, 200, 100))
            self.view.addItem(item)

        # Auto scale to fit the new rectangles
        self.view.autoRange()

        # Update rulers
        self.updateRulers()
