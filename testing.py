from matplotlib import pyplot as plt
from matplotlib import axes
from matplotlib.lines import Line2D
from matplotlib.backend_bases import MouseButton
from matplotlib.collections import PatchCollection
import math
import numpy as np
from matplotlib.figure import Figure
import matplotlib

import matplotlib.pyplot as plt

from matplotlib.patches import PathPatch
from matplotlib.path import Path


matplotlib.use('TKAgg')


class Network:
    """Holds the entire road network."""

    def __init__(self, figure: Figure, ax: axes.Axes) -> None:
        self.figure = figure
        self.ax = ax
        self.patches = []
        self.roads = []
        self.temp_road = None

    def get_ax(self):
        return self.ax

    def get_roads(self):
        return self.roads

    def clear_temp_road(self):
        self.temp_road = None

    def set_temp_road(self, verts: list):
        codes = [Path.MOVETO]
        codes += [Path.LINETO for _ in range(len(verts) - 1)]
        path = Path(verts, codes)
        self.temp_road = path

    def add_road(self, verts: list):
        codes = [Path.MOVETO]
        codes += [Path.LINETO for _ in range(len(verts) - 1)]
        path = Path(verts, codes)
        self.roads.append(path)

    def display(self):
        for patch in self.ax.patches:
            print(patch)
            patch.remove()

        patches = []
        for road in self.get_roads():
            patch = PathPatch(road, facecolor=(
                0, 0, 0, 0), edgecolor=(0, 0, 0, 0.2))
            patches.append(patch)

        if self.temp_road:
            patch = PathPatch(self.temp_road, facecolor=(
                0, 0, 0, 0), edgecolor=(0, 0, 0, 0.2))
            patches.append(patch)
        for patch in patches:
            self.ax.add_patch(patch)


class LineBuilder:
    def __init__(self, network: Network):
        self.ax = network.get_ax()
        self.network = network
        self.currently_building = None
        self.length = 0
        self.patch = None
        self.verts = []
        self.codes = []
        self.cid = self.ax.figure.canvas.mpl_connect(
            'button_press_event', self.add_point)
        self.cid = self.ax.figure.canvas.mpl_connect(
            'button_press_event', self.finish_building)

    def add_point(self, event):
        if event.button != MouseButton.RIGHT:
            return
        if event.inaxes != self.ax:
            return
        if not self.currently_building:
            self.currently_building = []
        if len(self.verts) > 0:
            self.length += math.sqrt(abs(self.verts[-1][0] - event.xdata) + abs(
                self.verts[-1][1] - event.ydata))
        self.currently_building.append((event.xdata, event.ydata))
        self.network.set_temp_road(self.currently_building)
        self.network.display()

    def finish_building(self, event):
        if event.button != MouseButton.LEFT:
            return
        if event.inaxes != self.ax:
            return
        if not self.currently_building:
            return

        self.network.clear_temp_road()
        self.network.add_road(self.currently_building)
        self.currently_building = None
        self.network.display()


fig, ax = plt.subplots()
ax.set_title('click to build line segments')
linebuilder = LineBuilder(Network(fig, ax))
plt.ion()
plt.show(block=True)
