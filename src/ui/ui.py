import tkinter as tk
from enum import Enum

# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure
from shapely import get_coordinates
from shapely.geometry import Point, Polygon, box

from constants.constants import (CALCULATION_P_COLOR, DEFAULT_XLIM,
                                 DEFAULT_YLIM, HITBOX_SIZE, HOW_TO_USE_TEXT,
                                 NORMAL_P_COLOR, SELECTED_P_COLOR, ZOOM_AMOUNT)

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
        self.ax.set_xlim(*DEFAULT_XLIM)
        self.ax.set_ylim(*DEFAULT_YLIM)
        self.base_scale = 1.1
        self.root = tk.Tk()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()

        self.plotted_lines = {}
        self.plotted_points = {}  # All points except calculation points
        self.plotted_temp_points = {}  # Points for the currently building road
        self.plotted_calculation_points = {}
        self.plotted_hitboxes = {}
        self.plotted_highlighted_path = None

        exit_button = tk.Button(
            self.root, command=self.root.destroy, text="Exit")
        print_roads_button = tk.Button(
            self.root, command=self.print_all_roads, text="All Roads")

        exit_button.pack()
        print_roads_button.pack()

        x_coord_label = tk.Label(self.root, text="X-coordinate")
        self.x_coord_entry = tk.Entry(self.root)
        y_coord_label = tk.Label(self.root, text="Y-coordinate")
        self.y_coord_entry = tk.Entry(self.root)
        add_point_button = tk.Button(
            self.root, command=self.handle_add_point, text="Add Point")

        x_coord_label.pack()
        self.x_coord_entry.pack()
        y_coord_label.pack()
        self.y_coord_entry.pack()
        add_point_button.pack()

        self.show_hitboxes = tk.IntVar(value=1)
        toggle_hitboxes = tk.Checkbutton(
            self.root, text="Show boxes around points", variable=self.show_hitboxes, onvalue=1, offvalue=0, command=self.redraw)
        toggle_hitboxes.pack()

        reset_zoom_button = tk.Button(
            self.root, text="Reset zoom and panning", command=self.reset_zoom_and_panning)
        reset_zoom_button.pack()

        how_to_use_button = tk.Button(
            self.root, text="How to Use", command=self.handle_how_to_use)
        how_to_use_button.pack()

        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.canvas.mpl_connect('button_press_event', self.onclick)
        self.canvas.mpl_connect('key_press_event', self.onkey)
        self.canvas.mpl_connect('scroll_event', self.zoom)

    def print_all_roads(self):
        print(self.network.roads)

    def handle_add_point(self):
        point = Point(self.x_coord_entry.get(), self.y_coord_entry.get())
        self.x_coord_entry.delete(0, tk.END)
        self.y_coord_entry.delete(0, tk.END)
        self.network.add_point_to_road(point)

        self.redraw()

    def handle_how_to_use(self):
        popup = tk.Toplevel()
        popup.title("Pop-up Window")
        popup.geometry("600x300")

        label = tk.Label(popup, text=HOW_TO_USE_TEXT, wraplength=500)
        label.pack()

        # Close button to destroy the pop-up window
        close_button = tk.Button(popup, text="Close", command=popup.destroy)
        close_button.pack()

    def redraw(self):
        if self.show_hitboxes.get() == 0:
            for point in list(self.plotted_points.keys()):
                self.remove_plotted_hitbox(point)

        if self.show_hitboxes.get() == 1 and len(self.plotted_hitboxes.values()) == 0:
            for point in list(self.plotted_points.keys()):
                self.plot_hitbox(point)

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
                self.remove_plotted_point(point, point_type=PointType.NORMAL)
                self.remove_plotted_hitbox(point)

        points = list(self.plotted_points.keys())
        for point in self.network.points:
            if point not in points:
                self.plot_point(point, point_type=PointType.NORMAL)
                if self.show_hitboxes.get() == 1:
                    self.plot_hitbox(point)

        points = list(self.plotted_temp_points.keys())
        for point in points:
            if point not in self.network.temp_points:
                self.remove_plotted_point(point, point_type=PointType.NORMAL)
                self.remove_plotted_hitbox(point)

        points = list(self.plotted_temp_points.keys())
        for point in self.network.temp_points:
            if point not in points:
                self.plot_point(point, point_type=PointType.NORMAL)
                if self.show_hitboxes.get() == 1:
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
                        calculation_point, point_type=PointType.CALCULATION)

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
                        calculation_point, point_type=PointType.CALCULATION)

        if self.plotted_highlighted_path:
            self.plotted_highlighted_path.remove()
            self.plotted_highlighted_path = None

        if self.network.highlighted_path:
            x = [coords[0]
                 for coords in get_coordinates(self.network.highlighted_path)]
            y = [coords[1]
                 for coords in get_coordinates(self.network.highlighted_path)]
            self.plotted_highlighted_path = self.ax.plot(
                x, y, "b")[0]

        self.canvas.draw()

    def reset_plotted_point_colors(self):
        for plotted_point in self.plotted_points.values():
            plotted_point.set_color(NORMAL_P_COLOR)

    def remove_plotted_point(self, point, point_type: PointType):
        match point_type:
            case PointType.NORMAL:
                point_storage = self.plotted_points
            case PointType.SELECTED:
                point_storage = self.plotted_points
            case PointType.CALCULATION:
                point_storage = self.plotted_calculation_points
        if point not in point_storage:
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

    def remove_plotted_hitbox(self, point: Point):
        if point not in self.plotted_hitboxes.keys():
            return
        self.plotted_hitboxes[point].remove()
        del self.plotted_hitboxes[point]

    def plot_road(self, road):
        plotted_line = self.ax.plot(
            road.xy[0], road.xy[1], label=f"Road {self.counter()}, length {road.length}")[0]
        self.plotted_lines[road] = plotted_line

    def plot_point(self, point, point_type: PointType):
        color = None
        point_storage = self.plotted_points
        match point_type:
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

    def onkey(self, event):
        if event.key == "c":
            if event.xdata is None or event.ydata is None:
                return
            point = Point(event.xdata, event.ydata)
            output = self.network.add_calculation_point(point)
        elif event.key == "right":
            xlim = self.ax.get_xlim()
            self.ax.set_xlim([xlim[0] + 1,
                              xlim[1] + 1])
        elif event.key == "left":
            xlim = self.ax.get_xlim()
            self.ax.set_xlim([xlim[0] - 1,
                              xlim[1] - 1])
        elif event.key == "up":
            ylim = self.ax.get_ylim()
            self.ax.set_ylim([ylim[0] + 1,
                              ylim[1] + 1])
        elif event.key == "down":
            ylim = self.ax.get_ylim()
            self.ax.set_ylim([ylim[0] - 1,
                              ylim[1] - 1])
        else:
            print("Invalid input!")

        self.redraw()  # CHECKS ENTIRE MAP FOR THINGS TO REDRAW

    def onclick(self, event):
        if PRINT_CLICK_INFO:
            print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
                  ('double' if event.dblclick else 'single', event.button,
                   event.x, event.y, event.xdata, event.ydata))
        if event.button == MouseButton.RIGHT:
            return
        elif event.button == MouseButton.LEFT:
            if event.xdata is None or event.ydata is None:
                return
            self.reset_plotted_point_colors()
            point = Point(event.xdata, event.ydata)
            output = self.network.add_point_to_road(point)
            if output and output[1] is True:
                self.plotted_points[output[0]].set_color(
                    SELECTED_P_COLOR)
        elif event.button == MouseButton.MIDDLE:
            if event.xdata is None or event.ydata is None:
                return
            point = Point(event.xdata, event.ydata)
            output = self.network.add_calculation_point(point)
        else:
            print("Invalid input!")

        self.redraw()  # CHECKS ENTIRE MAP FOR THINGS TO REDRAW

    def zoom(self, event):
        # get the current x and y limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        if event.button == 'down':
            # zoom in
            scale_factor = ZOOM_AMOUNT
        elif event.button == 'up':
            # zoom out
            scale_factor = -ZOOM_AMOUNT

        else:
            print("weird things with zoom!")
        # set new limits
        self.ax.set_xlim(xlim[0] - scale_factor,
                         xlim[1] + scale_factor)
        self.ax.set_ylim(ylim[0] - scale_factor,
                         ylim[1] + scale_factor)
        self.redraw()  # force re-draw

    def reset_zoom_and_panning(self):
        self.ax.set_xlim(*DEFAULT_XLIM)
        self.ax.set_ylim(*DEFAULT_YLIM)
        self.redraw()  # force re-draw

    def start_ui(self):
        self.root.mainloop()
