from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGraphicsRectItem, QLabel, QGraphicsPathItem, QSizePolicy
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QBrush
import pyqtgraph as pg

import math

import numpy as np

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

class FixedRectItem(QGraphicsRectItem):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag(0))  # no movement/select
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        rect = self.rect()
        pos = self.pos()
        self.setToolTip(f"Rect at ({pos.x():.0f}, {pos.y():.0f}), size ({rect.width():.0f}x{rect.height():.0f})")
        super().hoverEnterEvent(event)


class PyQtGraphLayoutWithScales(QWidget):
    def __init__(self, width=600, height=400, parent=None):
        super().__init__(parent)
        
        ##############################################
        # Do NOT use any of the following - else widgets will be clipped insde 
        # the tab-wdget where this widget is added.
        ##############################################
        # self.setFixedSize(width, height)
        # self.setMinimumSize(width, height)
        # self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.rect_items = []
        self.initUI()

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # Use PlotItem for axes
        self.graphWidget = pg.GraphicsLayoutWidget()
        self.plotItem = self.graphWidget.addPlot(row=0, col=0)
        self.plotItem.showGrid(x=True, y=True, alpha=0.5)
        self.plotItem.setMouseEnabled(x=True, y=True)
        self.plotItem.setLimits(xMin=0, xMax=1000, yMin=0, yMax=1000)
        self.plotItem.invertY(False)  # Y axis: bottom=min, top=max
        self.plotItem.getViewBox().invertX(False)  # X axis: left=min, right=max
        self.graphWidget.setBackground("black")

        self.view = self.plotItem.getViewBox()

        # Crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('y'))
        self.hLine = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('y'))
        self.view.addItem(self.vLine)
        self.view.addItem(self.hLine)

        # Mouse move event
        self.proxy = pg.SignalProxy(self.view.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

        # Change cursor to cross when mouse enters the plot area
        self.view.setCursor(Qt.CursorShape.CrossCursor)

        self.mainLayout.addWidget(self.graphWidget)
        self.setLayout(self.mainLayout)

        # Zoom factor
        self.zoomFactor = 1.2
        self.view.autoRange()

    def drawRects(self, rect_list, color='red', pen_width=1.5, brush=False):
        
        # self.view.clear()
        # self.rect_items.clear()

        for x, y, w, h in rect_list:
            item = FixedRectItem(x, y, w, h)
            item.setPen(pg.mkPen(color=color, width=pen_width))

            if brush:
                item.setBrush(pg.mkBrush(150, 100, 200, 100))
            else:
                item.setBrush(QBrush(Qt.BrushStyle.NoBrush))

            self.view.addItem(item)
            self.rect_items.append(item)


    def refresh(self):
        self.view.addItem(self.vLine)
        self.view.addItem(self.hLine)
        self.view.autoRange()


    def drawConnectingPoints(self, points, color='white'):
        """
        Draws lines connecting the given points in order.
        Each point should be a tuple (x, y).
        """
        if not points or len(points) < 2:
            return

        pen = pg.mkPen(color=color, width=2)
        path = pg.QtGui.QPainterPath()
        path.moveTo(points[0][0], points[0][1])
        for pt in points[1:]:
            path.lineTo(pt[0], pt[1])

        item = pg.QtWidgets.QGraphicsPathItem(path)
        item.setPen(pen)
        self.view.addItem(item)

    def mouseMoved(self, evt):
        pos = evt[0]
        if self.view.sceneBoundingRect().contains(pos):
            mousePoint = self.view.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def set_view_limits(self, bbox):
        """
        Sets the plot limits according to the given diearea bounding box.
        bbox should be (min_x, min_y, max_x, max_y)
        """
        min_x, min_y, max_x, max_y = bbox
        self.plotItem.setLimits(xMin=min_x, xMax=max_x, yMin=min_y, yMax=max_y)
        self.plotItem.setRange(xRange=(min_x, max_x), yRange=(min_y, max_y), padding=0)
        self.view.autoRange()


    # ... (zoom and pan methods unchanged)


    def mouseMoved(self, evt):
        pos = evt[0]
        if self.view.sceneBoundingRect().contains(pos):
            mousePoint = self.view.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def zoomIn(self):
        self.view.scaleBy((1 / self.zoomFactor, 1 / self.zoomFactor))

    def zoomOut(self):
        self.view.scaleBy((self.zoomFactor, self.zoomFactor))

    def zoomFit(self):
        self.view.autoRange()

    def zoomBbox(self, bbox):
        """
        Zooms the view to the given bbox area.
        bbox should be (min_x, min_y, max_x, max_y)
        """
        min_x, min_y, max_x, max_y = bbox
        self.plotItem.setRange(xRange=(min_x, max_x), yRange=(min_y, max_y), padding=0)
        # self.view.autoRange()

# --------- Pan Methods ----------
    def panLeft(self, factor=0.1):  # 10% of visible width
        rect = self.view.viewRect()
        dx = -factor * rect.width()
        self.view.translateBy(x=dx, y=0)

        self.view.update()
        self.graphWidget.update()

    def panRight(self, factor=0.1):
        rect = self.view.viewRect()
        dx = factor * rect.width()
        self.view.translateBy(x=dx, y=0)

        self.view.update()
        self.graphWidget.update()

    def panUp(self, factor=0.1):
        rect = self.view.viewRect()
        dy = -factor * rect.height()
        self.view.translateBy(x=0, y=dy)

        self.view.update()
        self.graphWidget.update()

    def panDown(self, factor=0.1):
        rect = self.view.viewRect()
        dy = factor * rect.height()
        self.view.translateBy(x=0, y=dy)

        self.view.update()
        self.graphWidget.update()


