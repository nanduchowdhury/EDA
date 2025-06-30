from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout

class VTKWidgetWrapper(QWidget):
    def __init__(self, width=600, height=400, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.vtkWidget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtkWidget)

        self.ren = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        self.actor = None


    def init_vtk_scene(self, source):
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())

        self.actor = vtk.vtkActor()
        self.actor.SetMapper(mapper)
        self.actor.GetProperty().SetColor(0.59, 0.29, 0.0)  # brown

        self.ren.AddActor(self.actor)
        self.ren.SetBackground(0.1, 0.1, 0.1)
        self.ren.ResetCamera()

        self.iren.Initialize()
        self.add_axes()

    def zoomOut(self, factor=1.2):
        camera = self.ren.GetActiveCamera()
        camera.Dolly(1 / factor)  # Zoom out
        self.ren.ResetCameraClippingRange()
        self.vtkWidget.GetRenderWindow().Render()

    def zoomIn(self, factor=1.2):
        camera = self.ren.GetActiveCamera()
        camera.Dolly(factor)  # Zoom in
        self.ren.ResetCameraClippingRange()
        self.vtkWidget.GetRenderWindow().Render()

    def zoomFit(self):
        self.ren.ResetCamera()
        self.ren.ResetCameraClippingRange()
        self.vtkWidget.GetRenderWindow().Render()

    def panLeft(self, factor=0.1):
        self._panCamera(dx=-factor, dy=0)

    def panRight(self, factor=0.1):
        self._panCamera(dx=factor, dy=0)

    def panUp(self, factor=0.1):
        self._panCamera(dx=0, dy=factor)

    def panDown(self, factor=0.1):
        self._panCamera(dx=0, dy=-factor)


    def _panCamera(self, dx=0.1, dy=0.0):
        camera = self.ren.GetActiveCamera()
        bounds = self.ren.ComputeVisiblePropBounds()

        center_x = (bounds[0] + bounds[1]) / 2.0
        center_y = (bounds[2] + bounds[3]) / 2.0
        range_x = bounds[1] - bounds[0]
        range_y = bounds[3] - bounds[2]

        # Compute pan deltas
        delta_x = dx * range_x
        delta_y = dy * range_y

        # Get camera position and focal point
        pos = list(camera.GetPosition())
        focal = list(camera.GetFocalPoint())

        # Move both by the deltas
        camera.SetFocalPoint(focal[0] + delta_x, focal[1] + delta_y, focal[2])
        camera.SetPosition(pos[0] + delta_x, pos[1] + delta_y, pos[2])

        self.ren.ResetCameraClippingRange()
        self.vtkWidget.GetRenderWindow().Render()


    def add_axes(self):
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(5, 5, 5)
        axes.AxisLabelsOn()
        self.ren.AddActor(axes)

    def show_mesh(self):
        if self.actor is not None:
            self.actor.GetProperty().EdgeVisibilityOn()
            self.actor.GetProperty().SetEdgeColor(1.0, 1.0, 1.0)
            self.actor.GetProperty().SetLineWidth(1.0)
            self.vtkWidget.GetRenderWindow().Render()
        else:
            print("No mesh to show.")

    def hide_mesh(self):
        if self.actor is not None:
            self.actor.GetProperty().EdgeVisibilityOff()
            self.vtkWidget.GetRenderWindow().Render()
        else:
            print("No mesh to hide.")


    def write_stl_ascii(self, filename, source):
        stl_writer = vtk.vtkSTLWriter()
        stl_writer.SetInputConnection(source.GetOutputPort())
        stl_writer.SetFileName(filename)
        stl_writer.SetFileTypeToASCII()  # Important: ASCII mode
        stl_writer.Write()
        print(f"Written ASCII STL to: {filename}")

    def read_stl_ascii(self, filename):
        reader = vtk.vtkSTLReader()
        reader.SetFileName(filename)
        reader.Update()

        polydata = reader.GetOutput()
        print(f"Read STL: {polydata.GetNumberOfPoints()} points, {polydata.GetNumberOfPolys()} polygons")

        return reader
    
    def extract_points_from_vtk_polydata(self, source):
        polydata = source.GetOutput()
        points = polydata.GetPoints()
        n = points.GetNumberOfPoints()
        return np.array([points.GetPoint(i) for i in range(n)])
    
    def compute_pca_axis(self, points):
        mean = np.mean(points, axis=0)
        centered = points - mean
        _, _, vh = np.linalg.svd(centered)
        axis = vh[0]  # principal direction
        return mean, axis
    
    def estimate_cylinder_parameters(self, source):

        points = self.extract_points_from_vtk_polydata(source)

        center, axis = self.compute_pca_axis(points)

        # Project points onto axis to get height
        projections = np.dot(points - center, axis)
        height = projections.max() - projections.min()

        # Compute radius as mean orthogonal distance to axis
        axis_point = center
        orthogonal_vectors = points - axis_point
        projection_lengths = np.dot(orthogonal_vectors, axis)
        projected = np.outer(projection_lengths, axis)
        radial_vectors = orthogonal_vectors - projected
        distances = np.linalg.norm(radial_vectors, axis=1)
        radius = np.mean(distances)

        return {
            "center": center.tolist(),
            "axis": axis.tolist(),
            "radius": radius,
            "height": height
        }
    
    @property
    def view(self):
        return self.vtkWidget  # for compatibility with .view        