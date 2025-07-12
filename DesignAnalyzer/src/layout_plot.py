import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsProxyWidget, QMenu, QAction
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import random
import pandas as pd

import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)


# ---------------- Base Plot ----------------


class BasePlotView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dataFrame = pd.DataFrame()
        self.initUI()

    def initUI(self):
        self.mainLayout = QVBoxLayout(self)
        self.graphWidget = pg.GraphicsLayoutWidget()
        self.plotItem = self.graphWidget.addPlot()
        self.plotItem.showGrid(x=True, y=True)
        self.plotItem.setLabel('bottom', 'X-Axis')
        self.plotItem.setLabel('left', 'Y-Axis')
        self.view = self.plotItem.getViewBox()

        self.vLine = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('y'))
        self.hLine = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('y'))
        self.view.addItem(self.vLine)
        self.view.addItem(self.hLine)

        layout = QHBoxLayout()
        layout.addWidget(self.graphWidget)
        self.mainLayout.addLayout(layout)

        self.zoomFactor = 1.2
        self.view.autoRange()

    def zoomFit(self):
        self.view.autoRange()

    def setDataFrame(self, df):
        self.dataFrame = df.copy()
        self.updatePlot()

    def updatePlot(self):
        raise NotImplementedError("Subclasses must implement updatePlot()")

# ---------------- Bar Chart ----------------



class BarChartView(BasePlotView):
    def __init__(self, x_col="X", y_col="Y", parent=None):
        super().__init__(parent)
        self.x_col = x_col
        self.y_col = y_col
        self.bar_items = []
        self._lastClickedBar = None

        # ✅ Create action once
        self.showInTableAction = QAction("Show in table", self)
        self.showInTableAction.triggered.connect(self.onShowInTable)

        # ✅ Add once to ViewBox menu
        self.plotItem.getViewBox().menu.addSeparator()
        self.plotItem.getViewBox().menu.addAction(self.showInTableAction)


    def contextMenuEvent(self, event):
        """Handle right-click: detect which bar was clicked"""
        pos = event.pos()
        scene_pos = self.view.mapToScene(pos)
        self._lastClickedBar = None

        for bar in self.bar_items:
            local_pos = bar.mapFromScene(scene_pos)
            if bar.contains(local_pos):
                self._lastClickedBar = bar
                break

        # Let default menu popup happen
        super().contextMenuEvent(event)


    def onShowInTable(self):
        """Triggered when 'Show in table' is clicked in RMB"""
        if self._lastClickedBar is None:
            print("No bar selected.")
            return

        tooltip = self._lastClickedBar.toolTip()
        print(f"🟦 Show in Table: {tooltip}")
        # You can emit signal or call another slot to reflect in a table

    def setXYColumn(self, x_col, y_col):
        self.x_col = x_col
        self.y_col = y_col

    def setDataFrame(self, df):
        self.dataFrame = df.copy()
        self.updatePlot()

    def updatePlot(self):
        self.plotItem.clear()
        self.bar_items.clear()

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

            self.view.addItem(bar)
            self.bar_items.append(bar)

        # Set axis ticks
        ticks = [(i + 1, str(row[self.x_col])) for i, row in self.dataFrame.iterrows()]
        self.plotItem.getAxis('bottom').setTicks([ticks])
        self.zoomFit()

    def zoomFit(self):
        self.view.autoRange()


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
