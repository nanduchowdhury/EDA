import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsProxyWidget
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import random
import pandas as pd

import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)



# ---------------- Abstract Base Class ----------------

class BasePlotView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataFrame = pd.DataFrame()
        self.initUI()

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)

        self.graphWidget = pg.GraphicsLayoutWidget()
        self.plotItem = self.graphWidget.addPlot()
        self.plotItem.showGrid(x=True, y=True)
        self.plotItem.setLabel('bottom', 'X-Axis')
        self.plotItem.setLabel('left', 'Y-Axis')
        self.view = self.plotItem.getViewBox()
        self.view.setMouseMode(pg.ViewBox.PanMode)
        self.view.setMouseEnabled(x=True, y=True)
        self.view.invertY(False)
        self.vLine = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('y'))
        self.hLine = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('y'))
        self.view.addItem(self.vLine)
        self.view.addItem(self.hLine)

        self.proxy = pg.SignalProxy(self.view.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        centerLayout = QHBoxLayout()
        centerLayout.setContentsMargins(0, 0, 0, 0)
        centerLayout.setSpacing(0)
        centerLayout.addWidget(self.graphWidget)
        self.mainLayout.addLayout(centerLayout)
        self.zoomFactor = 1.2
        self.view.autoRange()

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

    def setDataFrame(self, df):
        self.dataFrame = df.copy()
        self.updatePlot()

    def updatePlot(self):
        raise NotImplementedError("Subclasses must implement updatePlot()")


# ---------------- Bar Chart ----------------

class BarChartView(BasePlotView):
    barClicked = pyqtSignal(str)  # emits label of bar clicked

    def __init__(self, parent=None, x_col='X', y_col='Y'):
        self.x_col = x_col
        self.y_col = y_col
        super().__init__(parent)

    def setXYColumn(self, x_col, y_col):
        self.x_col = x_col
        self.y_col = y_col

    def updatePlot(self):

        self.plotItem.clear()
        if self.dataFrame.empty or self.x_col not in self.dataFrame or self.y_col not in self.dataFrame:
            return

        bar_width = 0.8
        for i, row in self.dataFrame.iterrows():
            x_val = i + 1
            label = str(row[self.x_col])
            value = float(row[self.y_col])
            bar = QGraphicsRectItem(x_val - bar_width / 2, 0, bar_width, value)
            bar.setBrush(QColor(*[random.randint(50, 255) for _ in range(3)]))
            bar.setPen(pg.mkPen('w'))
            bar.setToolTip(f"{label}: {value}")
            bar.setData(0, label)
            bar.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
            bar.setAcceptHoverEvents(True)
            bar.mousePressEvent = self.makeBarClickedHandler(label)
            self.view.addItem(bar)

        ticks = [(i + 1, str(row[self.x_col])) for i, row in self.dataFrame.iterrows()]
        self.plotItem.getAxis('bottom').setTicks([ticks])
        self.zoomFit()

    def makeBarClickedHandler(self, label):
        def handler(event):
            self.barClicked.emit(label)
        return handler


# ---------------- Pie Chart ----------------

class PieChartView(BasePlotView):
    sliceClicked = pyqtSignal(str)  # Not supported by matplotlib directly

    def __init__(self, parent=None, label_col='Label', value_col='Value'):
        self.label_col = label_col
        self.value_col = value_col
        super().__init__(parent)

    def updatePlot(self):
        self.view.clear()
        if self.dataFrame.empty or self.label_col not in self.dataFrame or self.value_col not in self.dataFrame:
            return

        fig, ax = plt.subplots()
        labels = self.dataFrame[self.label_col].astype(str)
        values = self.dataFrame[self.value_col].astype(float)
        colors = [plt.cm.tab20(i) for i in range(len(values))]

        ax.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        canvas = FigureCanvas(fig)
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(canvas)
        self.view.addItem(proxy)
        proxy.setPos(0, 0)
        self.zoomFit()
