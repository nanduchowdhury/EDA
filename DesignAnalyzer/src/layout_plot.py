
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsProxyWidget, QMenu, QAction, QToolTip
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QUrl, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QFont


from matplotlib.figure import Figure

import mplcursors
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable


import os
import folium
from PyQt5.QtWebEngineWidgets import QWebEngineView

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
        self._showInTableCallback = None
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


    def registerActionOnShowInTable(self, actionMethod):
        """Register a user-defined callback for 'Show in table'."""
        self._showInTableCallback = actionMethod

    def onShowInTable(self):
        """Triggered when 'Show in table' is clicked in RMB"""
        if self._lastClickedBar is None:
            print("No bar selected.")
            return
        
        if self._lastClickedBar and self._showInTableCallback:
            # label = self._lastClickedBar.data(0)
            label = self._lastClickedBar.toolTip()
            self._showInTableCallback(label)

    def setXYColumn(self, x_col, y_col):
        self.x_col = x_col
        self.y_col = y_col

    def setDataFrame(self, df):
        self.dataFrame = df.copy()
        self.updatePlot()

    def checkInputValidity(self):
        if self.dataFrame.empty:
            raise ValueError("Input data is empty. Please set valid input data.")
        if self.x_col not in self.dataFrame:
            raise ValueError(f"Column '{self.x_col}' not found in input data.")
        if self.y_col not in self.dataFrame:
            raise ValueError(f"Column '{self.y_col}' not found in input data.")
        if self.dataFrame.shape[0] > 500:
            raise ValueError("Input data has too many rows. Please try on smaller set.")
        
    def updatePlot(self):
        self.plotItem.clear()
        self.bar_items.clear()

        self.checkInputValidity()

        bar_width = 0.8
        for i, row in self.dataFrame.iterrows():
            x_val = i + 1
            label = str(row[self.x_col])
            value_str = row[self.y_col]
            value = float(value_str)

            bar = QGraphicsRectItem(x_val - bar_width / 2, 0, bar_width, value)
            bar.setBrush(QColor(*[random.randint(50, 255) for _ in range(3)]))
            bar.setPen(pg.mkPen('w'))
            bar.setToolTip(f"{label} : {value_str}")
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

class BasePiePlotView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    def zoomFit(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def clear(self):
        self.scene.clear()



class PieChartView(BasePiePlotView):
    sliceClicked = pyqtSignal(str)  # Emits label when a slice is clicked

    def __init__(self, parent=None, label_col='Label', value_col='Value'):
        super().__init__(parent)
        self.label_col = label_col
        self.value_col = value_col
        self.dataFrame = None
        self.wedges = []

    def setLabelAndValue(self, label_col, value_col):
        self.label_col = label_col
        self.value_col = value_col

    def setDataFrame(self, df):
        self.dataFrame = df
        self.updatePlot()

    def checkInputValidity(self):
        if self.dataFrame.empty:
            raise ValueError("Input data is empty. Please set valid input data.")
        if self.label_col not in self.dataFrame:
            raise ValueError(f"Column '{self.label_col}' not found in input data.")
        if self.value_col not in self.dataFrame:
            raise ValueError(f"Column '{self.y_col}' not found in input data.")
        if self.dataFrame.shape[0] > 100:
            raise ValueError("Input data has too many rows. Please try on smaller set.")
        
    def updatePlot(self):

        self.checkInputValidity()

        self.clear()

        fig = Figure(facecolor='black')
        ax = fig.add_subplot(111)
        ax.set_facecolor('black')

        labels = self.dataFrame[self.label_col].astype(str).tolist()
        values = self.dataFrame[self.value_col].astype(float).tolist()
        total = sum(values)
        colors = ['blue', 'red', 'green', 'yellow', 'purple', 'brown', 'white']
        colors = (colors * ((len(values) // len(colors)) + 1))[:len(values)]

        wedges, texts = ax.pie(
            values,
            labels=labels,
            labeldistance=1.15,
            startangle=90,
            colors=colors,
            textprops={'color': 'white'},
        )

        ax.axis('equal')  # Circular

        # Annotate each wedge with label + percent for hover and click
        for wedge, label, value in zip(wedges, labels, values):
            wedge.set_label(label)
            wedge.set_gid(f"{label}: {value / total * 100:.1f}%")

        self.wedges = wedges

        # Embed canvas
        canvas = FigureCanvas(fig)
        proxy = QGraphicsProxyWidget()
        proxy.setWidget(canvas)
        self.scene.addItem(proxy)
        proxy.setPos(0, 0)
        self.zoomFit()

        # Hook events
        canvas.mpl_connect("motion_notify_event", self._onHover)
        canvas.mpl_connect("button_press_event", self._onClick)

    def _onHover(self, event):
        if event.inaxes:
            for wedge in self.wedges:
                if wedge.contains_point([event.x, event.y], radius=1.0):
                    tooltip = wedge.get_gid()  # label: percent%
                    pos = QPoint(event.guiEvent.globalX() + 10, event.guiEvent.globalY() + 10)
                    QToolTip.showText(pos, tooltip, self)
                    return
        QToolTip.hideText()

    def _onClick(self, event):
        if event.inaxes:
            for wedge in self.wedges:
                if wedge.contains_point([event.x, event.y], radius=1.0):
                    label = wedge.get_label()
                    self.sliceClicked.emit(label)


class WorldMapWidget(BasePlotView):
    def __init__(self, colName="", parent=None):
        super().__init__(parent)
        self.cityColumn = colName
        self.geolocator = Nominatim(user_agent="map_viewer")
        self.web_view = QWebEngineView()
        self._map_file = os.path.abspath("temp_map.html")

        # Replace graphWidget layout with map view
        self.mainLayout.removeWidget(self.graphWidget)
        self.graphWidget.setParent(None)
        self.mainLayout.addWidget(self.web_view)

    def setColumnName(self, colName):
        """Set the column name from which cities will be read."""
        self.cityColumn = colName

    def validateCities(self):
        """Validate that all cities in the column exist (can be geocoded)."""
        if self.dataFrame.empty or self.cityColumn not in self.dataFrame:
            raise ValueError(f"DataFrame is empty or column '{self.cityColumn}' not found.")

        invalid_cities = []
        for city in self.dataFrame[self.cityColumn].dropna().unique():
            try:
                location = self.geolocator.geocode(city)
                if not location:
                    invalid_cities.append(city)
            except (GeocoderTimedOut, GeocoderUnavailable):
                continue  # optionally retry or skip
        if invalid_cities:
            raise ValueError(f"These cities could not be located: {invalid_cities}")

    def showCities(self):
        """Show all valid cities from the specified column on the map."""
        if self.dataFrame.empty or self.cityColumn not in self.dataFrame:
            raise ValueError(f"No data or column '{self.cityColumn}' missing.")

        city_names = self.dataFrame[self.cityColumn].dropna().unique()

        # Start map with default view
        fmap = folium.Map(location=[20, 0], zoom_start=2)

        for city in city_names:
            try:
                location = self.geolocator.geocode(city)
                if location:
                    folium.Marker(
                        location=(location.latitude, location.longitude),
                        popup=city,
                        tooltip=city,
                        icon=folium.Icon(color="blue", icon="info-sign")
                    ).add_to(fmap)
            except (GeocoderTimedOut, GeocoderUnavailable):
                print(f"⏱ Timeout or unavailable while geocoding: {city}")

        fmap.save(self._map_file)
        self.web_view.load(QUrl.fromLocalFile(self._map_file))

    def updatePlot(self):
        # Not applicable here, since we show map in webview instead
        pass


