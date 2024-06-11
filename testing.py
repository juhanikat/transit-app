from matplotlib import pyplot as plt
from matplotlib import axes
from matplotlib.lines import Line2D
from matplotlib.backend_bases import MouseButton
import math
import numpy as np

import matplotlib.pyplot as plt

import matplotlib.patches as patches
from matplotlib.path import Path


class LineBuilder:
    def __init__(self, ax: axes.Axes):
        self.ax = ax
        self.length = 0
        self.patch = None
        self.verts = []
        self.codes = []
        self.cid = self.ax.figure.canvas.mpl_connect(
            'button_press_event', self.add_point)
        self.cid = self.ax.figure.canvas.mpl_connect(
            'button_press_event', self.create_line)

    def add_point(self, event):
        if event.button != MouseButton.RIGHT:
            return
        print('move', event)
        if event.inaxes != self.ax:
            return
        if len(self.verts) > 0:
            self.length += math.sqrt(abs(self.verts[-1][0] - event.xdata) + abs(
                self.verts[-1][1] - event.ydata))
            print(self.length)
        self.verts.append((event.xdata, event.ydata))
        if len(self.codes) == 0:
            self.codes.append(Path.MOVETO)
        else:
            self.codes.append(Path.LINETO)

        path = Path(self.verts, self.codes)
        self.patch = patches.PathPatch(path, facecolor=(0, 0, 0, 0))
        for patch in self.ax.patches:
            print(patch)
            patch.remove()
        self.ax.add_patch(self.patch)
        plt.show()

    def create_line(self, event):
        if event.button != MouseButton.LEFT:
            return
        print('click', event)
        if event.inaxes != self.ax:
            return


fig, ax = plt.subplots()
ax.set_title('click to build line segments')
linebuilder = LineBuilder(ax)
plt.show()
