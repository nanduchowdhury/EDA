from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGraphicsRectItem
from PyQt5.QtCore import Qt, QRectF
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
    def __init__(self, orientation=Qt.Horizontal, color_bg="navy", color_tick="white", parent=None):
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
                    painter.drawLine(x, 0, x, self.height() // 2)
                    painter.drawText(x + 2, self.height() - 5, f"{val:.0f}")
                    val += step_val
            else:
                height = self.height()
                step_px = 50
                step_val = range_val * step_px / height
                val = self.min_val
                while val <= self.max_val:
                    y = int((val - self.min_val) / range_val * height)
                    painter.drawLine(0, height - y, self.width() // 2, height - y)
                    painter.drawText(25, height - y + 6, f"{val:.0f}")
                    val += step_val
        finally:
            painter.end()


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
        self.setFixedSize(width, height)

        self.rect_items = []
        self.initUI()

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        # Rulers (bottom and right) with light-blue background
        self.ruler_x = RulerWidget(Qt.Horizontal, color_bg="#2C3539")
        self.ruler_y = RulerWidget(Qt.Vertical, color_bg="#2C3539")

        # Plot area
        self.graphWidget = pg.GraphicsLayoutWidget()
        self.view = self.graphWidget.addViewBox(lockAspect=False, enableMenu=False)
        self.view.setMouseMode(pg.ViewBox.PanMode)
        self.view.setMouseEnabled(x=True, y=True)
        self.view.setLimits(xMin=0, xMax=1000, yMin=0, yMax=1000)
        self.view.invertY(True)  # (0,0) is now bottom-left
        self.view.setBackgroundColor("black")

        # Grid
        self.grid = pg.GridItem()
        self.grid.setPen(pg.mkPen(color=(200, 200, 200), width=0.5))
        self.view.addItem(self.grid)

        # Crosshair
        self.vLine = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('y'))
        self.hLine = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('y'))
        self.view.addItem(self.vLine)
        self.view.addItem(self.hLine)

        # Mouse move event
        self.proxy = pg.SignalProxy(self.view.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

        # Layout with right and bottom rulers
        centerLayout = QHBoxLayout()
        centerLayout.setContentsMargins(0, 0, 0, 0)
        centerLayout.setSpacing(0)
        centerLayout.addWidget(self.graphWidget)
        centerLayout.addWidget(self.ruler_y)

        self.mainLayout.addLayout(centerLayout)
        self.mainLayout.addWidget(self.ruler_x)

        # Zoom factor
        self.zoomFactor = 1.2
        self.view.autoRange()

    def drawRects(self, rect_list):
        self.view.clear()
        self.rect_items.clear()

        for x, y, w, h in rect_list:
            item = FixedRectItem(x, y, w, h)
            item.setPen(pg.mkPen('black'))
            item.setBrush(pg.mkBrush(150, 100, 200, 100))
            self.view.addItem(item)
            self.rect_items.append(item)

        # Add back grid and crosshairs
        self.view.addItem(self.grid)
        self.view.addItem(self.vLine)
        self.view.addItem(self.hLine)
        self.view.autoRange()
        self.updateRulers()

    def updateRulers(self):
        rect = self.view.viewRect()
        self.ruler_x.setRange(rect.left(), rect.right())
        self.ruler_y.setRange(rect.top(), rect.bottom())

    def mouseMoved(self, evt):
        pos = evt[0]
        if self.view.sceneBoundingRect().contains(pos):
            mousePoint = self.view.mapSceneToView(pos)
            self.vLine.setPos(mousePoint.x())
            self.hLine.setPos(mousePoint.y())

    def zoomIn(self):
        self.view.scaleBy((1 / self.zoomFactor, 1 / self.zoomFactor))
        self.updateRulers()

    def zoomOut(self):
        self.view.scaleBy((self.zoomFactor, self.zoomFactor))
        self.updateRulers()

    def zoomFit(self):
        self.view.autoRange()
        self.updateRulers()
