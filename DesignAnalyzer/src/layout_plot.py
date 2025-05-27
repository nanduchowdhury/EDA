import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsProxyWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import random

import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)


class PlotWithScales(QWidget):
    def __init__(self, width=600, height=400, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
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
        self.view.setLimits(xMin=0, xMax=1000, yMin=0, yMax=1000)
        self.view.invertY(False)  # (0,0) is bottom-left
        self.view.setBackgroundColor("black")

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

    def panLeft(self, factor=0.1):
        dx = -factor * self.view.viewRect().width()
        self.view.translateBy(x=dx, y=0)

    def panRight(self, factor=0.1):
        dx = factor * self.view.viewRect().width()
        self.view.translateBy(x=dx, y=0)

    def panUp(self, factor=0.1):
        dy = -factor * self.view.viewRect().height()
        self.view.translateBy(x=0, y=dy)

    def panDown(self, factor=0.1):
        dy = factor * self.view.viewRect().height()
        self.view.translateBy(x=0, y=dy)

    def plotWaveform(self, x_data, y_data, xLabel="X", yLabel="Y", color='cyan'):
        self.plotItem.clear()

        self.plotItem.setLabel('bottom', xLabel)
        self.plotItem.setLabel('left', yLabel)

        self.plotItem.plot(x_data, y_data, pen=pg.mkPen(color=color, width=1.5), antialias=True)
        self.view.addItem(self.vLine)
        self.view.addItem(self.hLine)

        self.zoomFit()

    def plotBar(self, dataList, xLabel="X", yLabel="Y"):
        self.plotItem.clear()
        self.plotItem.setLabel('bottom', xLabel)
        self.plotItem.setLabel('left', yLabel)

        bar_width = 0.8
        for i, (value, label) in enumerate(dataList):
            x = i + 1
            bar = QGraphicsRectItem(x - bar_width / 2, 0, bar_width, value)
            color = QColor(*[random.randint(50, 255) for _ in range(3)])
            bar.setBrush(color)
            bar.setPen(pg.mkPen('w'))
            bar.setToolTip(f"{label}: {value}")
            self.view.addItem(bar)

        self.plotItem.getAxis('bottom').setTicks([[ (i+1, label) for i, (_, label) in enumerate(dataList) ]])

        self.zoomFit()

    def plotPie(self, dataList):
        fig, ax = plt.subplots()
        values = [v for v, _ in dataList]
        labels = [l for _, l in dataList]
        colors = [plt.cm.tab20(i) for i in range(len(dataList))]

        ax.pie(values, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')

        canvas = FigureCanvas(fig)
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(canvas)
        self.view.clear()
        self.view.addItem(proxy)
        proxy.setPos(0, 0)

        self.zoomFit()
