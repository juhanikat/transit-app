import tkinter as tk
from matplotlib.backend_bases import MouseButton
from shapely.geometry import Point, Polygon, box
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure
"""
root = tkinter.Tk()
root.wm_title("Embedding in Tk")

fig = Figure(figsize=(5, 4), dpi=100)
t = np.arange(0, 3, .01)
ax = fig.add_subplot()
line, = ax.plot(t, 2 * np.sin(2 * np.pi * t))
ax.set_xlabel("time [s]")
ax.set_ylabel("f(t)")

canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
canvas.draw()

# pack_toolbar=False will make it easier to use a layout manager later on.
toolbar = NavigationToolbar2Tk(canvas, root, pack_toolbar=False)
toolbar.update()

canvas.mpl_connect(
    "key_press_event", lambda event: print(f"you pressed {event.key}"))
canvas.mpl_connect("key_press_event", key_press_handler)

button_quit = tkinter.Button(master=root, text="Quit", command=root.destroy)


def update_frequency(new_val):
    # retrieve frequency
    f = float(new_val)

    # update data
    y = 2 * np.sin(2 * np.pi * f * t)
    line.set_data(t, y)

    # required to update canvas and attached toolbar!
    canvas.draw()


slider_update = tkinter.Scale(root, from_=1, to=5, orient=tkinter.HORIZONTAL,
                              command=update_frequency, label="Frequency [Hz]")

# Packing order is important. Widgets are processed sequentially and if there
# is no space left, because the window is too small, they are not displayed.
# The canvas is rather flexible in its size, so we pack it last which makes
# sure the UI controls are displayed as long as possible.
button_quit.pack(side=tkinter.BOTTOM)
slider_update.pack(side=tkinter.BOTTOM)
toolbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)
canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)

tkinter.mainloop()
"""
from enum import Enum
from constants import NORMAL_P_COLOR, SELECTED_P_COLOR, INTERSECTION_P_COLOR, CALCULATION_P_COLOR, HITBOX_SIZE


PRINT_CLICK_INFO = False  # use to print information on each mouse click


class PointType(Enum):
    NORMAL = "normal"
    SELECTED = "selected"
    CALCULATION = "calculation"


def create_hitbox(point: Point) -> Polygon:
    b = point.bounds
    new_b = (b[0] - HITBOX_SIZE, b[1] - HITBOX_SIZE,
             b[2] + HITBOX_SIZE, b[3] + HITBOX_SIZE)
    return box(*new_b)


class Counter:
    def __init__(self):
        self.count = 1

    def __call__(self, amount=1):
        val = self.count
        self.count += amount
        return val


class UI:

    def __init__(self, network) -> None:
        self.network = network
        self.counter = Counter()
        self.fig = Figure()
        self.ax = self.fig.add_subplot()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)
        self.root = tk.Tk()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()

        self.plotted_lines = {}
        self.plotted_points = {}  # All points except calculation points
        self.plotted_calculation_points = {}
        self.plotted_hitboxes = {}

        exit_button = tk.Button(
            self.root, command=self.root.destroy, text="Exit")
        print_roads_button = tk.Button(
            self.root, command=self.print_all_roads, text="All Roads")
        exit_button.pack()
        print_roads_button.pack()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.canvas.mpl_connect('button_press_event', self.onclick)

    def print_all_roads(self):
        print(self.network.roads)

    def redraw(self):
        lines = list(self.plotted_lines.keys())
        for line in lines:
            if line not in self.network.roads:
                self.remove_plotted_road(line)

        lines = list(self.plotted_lines.keys())
        for road in self.network.roads:
            if road not in lines:
                self.plot_road(road)

        points = list(self.plotted_points.keys())
        for point in points:
            if point not in self.network.points:
                self.remove_plotted_point(point, type=PointType.NORMAL)
                self.remove_hitbox(point)

        points = list(self.plotted_points.keys())
        for point in self.network.points:
            if point not in points:
                self.plot_point(point, type=PointType.NORMAL)
                self.plot_hitbox(point)

        if self.network.calculation_points:
            if len(self.network.calculation_points) == 1:
                network_calc_points = [self.network.calculation_points[0][0]]
            elif len(self.network.calculation_points) == 2:
                network_calc_points = [
                    self.network.calculation_points[0][0], self.network.calculation_points[1][0]]
            calculation_points = list(self.plotted_calculation_points.keys())
            for calculation_point in calculation_points:
                if calculation_point not in network_calc_points:
                    self.remove_plotted_point(
                        calculation_point, type=PointType.CALCULATION)

        if self.network.calculation_points:
            if len(self.network.calculation_points) == 1:
                network_calc_points = [self.network.calculation_points[0][0]]
            elif len(self.network.calculation_points) == 2:
                network_calc_points = [
                    self.network.calculation_points[0][0], self.network.calculation_points[1][0]]
            calculation_points = list(self.plotted_calculation_points.keys())
            for calculation_point in network_calc_points:
                if calculation_point not in calculation_points:
                    self.plot_point(
                        calculation_point, type=PointType.CALCULATION)

    def reset_plotted_point_colors(self):
        for plotted_point in self.plotted_points.values():
            plotted_point.set_color(NORMAL_P_COLOR)

    def remove_plotted_point(self, point, type: PointType):
        match type:
            case PointType.NORMAL:
                point_storage = self.plotted_points
            case PointType.SELECTED:
                point_storage = self.plotted_points
            case PointType.CALCULATION:
                point_storage = self.plotted_calculation_points
        if point not in point_storage.keys():
            print("POINT NOT IN PLOTTED_POINTS DICT KEYS!")
            return
        point_storage[point].remove()
        del point_storage[point]

    def remove_plotted_road(self, road):
        if road not in self.plotted_lines.keys():
            print("ROAD NOT IN PLOTTED_LINES DICT KEYS!")
            return
        self.plotted_lines[road].remove()
        del self.plotted_lines[road]

    def remove_hitbox(self, point):
        if point not in self.plotted_hitboxes.keys():
            print("POINT NOT IN PLOTTED_HITBOXES DICT KEYS!")
            return
        print(self.plotted_hitboxes[point])
        self.plotted_hitboxes[point].remove()
        del self.plotted_hitboxes[point]

    def plot_road(self, road):
        plotted_line = self.ax.plot(
            road.xy[0], road.xy[1], label=f"Road {self.counter()}, length {road.length}")[0]
        self.plotted_lines[road] = plotted_line

    def plot_point(self, point, type: PointType):
        color = None
        point_storage = self.plotted_points
        match type:
            case PointType.NORMAL:
                color = NORMAL_P_COLOR
            case PointType.SELECTED:
                color = SELECTED_P_COLOR
            case PointType.CALCULATION:
                color = CALCULATION_P_COLOR
                point_storage = self.plotted_calculation_points
        plotted_point = self.ax.plot(
            *point.xy, f"{color}o")[0]
        point_storage[point] = plotted_point

    def plot_hitbox(self, point):
        plotted_hitbox = self.ax.plot(*create_hitbox(point).exterior.xy)[0]
        self.plotted_hitboxes[point] = plotted_hitbox

    def onclick(self, event):
        if PRINT_CLICK_INFO:
            print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
                  ('double' if event.dblclick else 'single', event.button,
                   event.x, event.y, event.xdata, event.ydata))
        if event.button == MouseButton.RIGHT:
            return
        elif event.button == MouseButton.LEFT:
            self.reset_plotted_point_colors()
            point = Point(event.xdata, event.ydata)
            output = self.network.add_point_to_road(point)
            if output[1] is True:
                self.plotted_points[output[0]].set_color(
                    SELECTED_P_COLOR)
        elif event.button == MouseButton.MIDDLE:
            point = Point(event.xdata, event.ydata)
            output = self.network.add_calculation_point(point)
        else:
            print("Invalid input!")

        self.redraw()  # CHECKS ENTIRE MAP FOR THINGS TO REDRAW
        self.canvas.draw()

    def start_ui(self):
        self.root.mainloop()
