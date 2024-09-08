import tkinter as tk
import typing
from enum import Enum

import matplotlib.patheffects as pe
import mplcursors
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
from matplotlib.figure import Figure
from shapely import get_coordinates
from shapely.geometry import Point

from .constants import (CALCULATION_P_COLOR, DEFAULT_XLIM, DEFAULT_YLIM,
                        HOW_TO_USE_TEXT, HPATH_COLOR, NORMAL_P_COLOR,
                        ROAD_COLOR, ROAD_WIDTH, SELECTED_P_COLOR)
from .utilities import (AddCalculationPointOutput, AddPointOutput,
                        AddRoadOutput, CreateCrossroadsOutput,
                        ShortestPathOutput, create_hitbox)

if typing.TYPE_CHECKING:
    from .network import Network


NO_CURSOR = False  # No yellow boxes
PRINT_CLICK_INFO = False  # use to print information on each mouse click


class PointType(Enum):
    NORMAL = "normal"
    SELECTED = "selected"
    CALCULATION = "calculation"


class Counter:
    def __init__(self):
        self.count = 1

    def __call__(self, amount=1):
        val = self.count
        self.count += amount
        return val


class UI:

    def __init__(self, network: "Network") -> None:
        self.network = network
        self.counter = Counter()
        self.fig = Figure()
        self.ax = self.fig.add_subplot()
        self.ax.set_xlim(*DEFAULT_XLIM)
        self.ax.set_ylim(*DEFAULT_YLIM)
        self.root = tk.Tk()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)

        self.zoom_level = 0

        self.plotted_lines = {}
        self.plotted_points = {}  # All points except calculation points
        self.plotted_temp_points = {}  # Points for the currently building road
        self.plotted_calculation_points = {}
        self.plotted_hitboxes = {}
        self.plotted_highlighted_path = None

        self.printed_shortest_path_output: ShortestPathOutput = None
        self.printed_add_point_output: AddPointOutput = None
        self.printed_add_road_output: AddRoadOutput = None
        self.printed_create_crossroads_output: CreateCrossroadsOutput = None
        self.printed_add_calculation_point_output: AddCalculationPointOutput = None

        self.build_ui_elements()

        self.canvas.mpl_connect('button_press_event', self.onclick)
        self.canvas.mpl_connect('key_press_event', self.onkey)
        self.canvas.mpl_connect('scroll_event', self.zoom)

        self.add_info_text("Start drawing!", sep=False)
        self.canvas.draw()

    def print_all_roads(self):
        new_text = f"All Roads ({len(self.network.roads)} in total):"
        for road in self.network.roads:
            new_text += f"\n{road}"
        self.add_info_text(new_text)

    def handle_add_point(self):
        x_coord = self.x_coord_entry.get()
        y_coord = self.y_coord_entry.get()
        if x_coord == "" or y_coord == "":
            return
        point = Point(x_coord, y_coord)
        self.x_coord_entry.delete(0, tk.END)
        self.y_coord_entry.delete(0, tk.END)
        self.network.add_point(point)

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

    def clear_info_text(self):
        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        self.info_text.config(state="disabled")

    def add_info_text(self, text: str, sep=True):
        self.info_text.config(state="normal")
        if sep:
            self.info_text.insert(tk.END, "\n-------------------")
        self.info_text.insert(tk.END, f"\n{text}")
        self.info_text.see(tk.END)
        self.info_text.config(state="disabled")

    def create_cursor(self):
        """Needs to be recreated every time new data is added?"""
        def joku(sel):
            if NO_CURSOR:
                sel.annotation.set_text("")
            else:
                sel.annotation.set_text(sel.artist)

        cursor = mplcursors.cursor(hover=True)
        cursor.connect(
            "add", lambda sel: joku(sel))

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
            road.xy[0], road.xy[1], linewidth=ROAD_WIDTH, color=ROAD_COLOR,
            path_effects=[
                pe.Stroke(linewidth=5, foreground='black'), pe.Normal()],
            zorder=0, label=f"Road {self.counter()}, length {road.length}")[0]
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
            self.network.add_calculation_point(point)
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
            self.network.add_point(point)
        elif event.button == MouseButton.MIDDLE:
            if event.xdata is None or event.ydata is None:
                return
            point = Point(event.xdata, event.ydata)
            self.network.add_calculation_point(point)
        else:
            print("Invalid input!")

        self.redraw()  # CHECKS ENTIRE MAP FOR THINGS TO REDRAW
        if not NO_CURSOR:
            self.create_cursor()

    def zoom(self, event):
        # get the current x and y limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        if event.button == 'down':
            # zoom in
            if self.zoom_level == 3:
                print("max zoom in")
                return
            self.zoom_level += 1
            self.ax.set_xlim(xlim[0] + 1,
                             xlim[1] - 1)
            self.ax.set_ylim(ylim[0] + 1,
                             ylim[1] - 1)
        elif event.button == 'up':
            # zoom out
            if self.zoom_level == -10:
                print("max zoom out")
                return
            self.zoom_level -= 1
            self.ax.set_xlim(xlim[0] - 1,
                             xlim[1] + 1)
            self.ax.set_ylim(ylim[0] - 1,
                             ylim[1] + 1)
        else:
            print("weird things with zoom!")
        self.redraw()  # force re-draw

    def reset_zoom_and_panning(self):
        self.ax.set_xlim(*DEFAULT_XLIM)
        self.ax.set_ylim(*DEFAULT_YLIM)
        self.redraw()  # force re-draw

    def redraw(self):
        self.longest_road_label.config(
            text=f"Longest road length: {self.network.stats['longest_road_length']}")
        self.shortest_road_label.config(
            text=f"Shortest road length: {self.network.stats['shortest_road_length']}")
        self.road_amount_label.config(
            text=f"Road amount: {self.network.stats['road_amount']}")

        if self.network.shortest_path_output:
            if self.printed_shortest_path_output is not self.network.shortest_path_output:
                self.printed_shortest_path_output = self.network.shortest_path_output
                self.add_info_text(self.printed_shortest_path_output)

        if self.network.add_point_output:
            if self.printed_add_point_output is not self.network.add_point_output:
                self.printed_add_point_output = self.network.add_point_output
                if self.printed_add_point_output.point_overlaps:
                    self.plotted_points[self.printed_add_point_output.point].set_color(
                        SELECTED_P_COLOR)
                if self.printed_add_point_output.error:
                    self.add_info_text(self.printed_add_point_output)

        if self.network.add_road_output:
            if self.printed_add_road_output is not self.network.add_road_output:
                self.printed_add_road_output = self.network.add_road_output
                self.add_info_text(self.printed_add_road_output)

        if self.network.create_crossroads_output:
            if self.printed_create_crossroads_output is not self.network.create_crossroads_output:
                self.printed_create_crossroads_output = self.network.create_crossroads_output
                self.add_info_text(self.printed_create_crossroads_output)

        if self.network.add_calculation_point_output:
            if self.printed_add_calculation_point_output is not self.network.add_calculation_point_output:
                self.printed_add_calculation_point_output = self.network.add_calculation_point_output
                if self.printed_add_calculation_point_output.error or \
                        self.printed_add_calculation_point_output.c_point_added:
                    self.add_info_text(
                        self.printed_add_calculation_point_output)

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

        # remove c points
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

        # add c points
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
                x, y, linewidth=ROAD_WIDTH, color=HPATH_COLOR, zorder=0)[0]

        self.canvas.draw()

    def build_ui_elements(self):
        rows = 3
        columns = 2
        for i in range(rows):
            self.root.grid_rowconfigure(i, weight=1, uniform="row")
        for j in range(columns):
            self.root.grid_columnconfigure(j, weight=1, uniform="row")

        # Frame 1
        frame_1 = tk.Frame(
            self.root, highlightbackground="black", highlightthickness=1)
        frame_1.grid(row=0, column=0, sticky="nsew")

        exit_button = tk.Button(
            frame_1, command=self.root.destroy, text="Exit")
        exit_button.pack()

        print_roads_button = tk.Button(
            frame_1, command=self.print_all_roads, text="All Roads")
        print_roads_button.pack()

        x_coord_label = tk.Label(frame_1, text="X-coordinate")
        self.x_coord_entry = tk.Entry(frame_1)
        y_coord_label = tk.Label(frame_1, text="Y-coordinate")
        self.y_coord_entry = tk.Entry(frame_1)
        add_point_button = tk.Button(
            frame_1, command=self.handle_add_point, text="Add Point")

        x_coord_label.pack()
        self.x_coord_entry.pack()
        y_coord_label.pack()
        self.y_coord_entry.pack()
        add_point_button.pack()

        self.show_hitboxes = tk.IntVar(value=1)
        toggle_hitboxes = tk.Checkbutton(
            frame_1, text="Show boxes around points",
            variable=self.show_hitboxes, onvalue=1, offvalue=0, command=self.redraw)
        toggle_hitboxes.pack()

        reset_zoom_button = tk.Button(
            frame_1, text="Reset zoom and panning", command=self.reset_zoom_and_panning)
        reset_zoom_button.pack()

        how_to_use_button = tk.Button(
            frame_1, text="How to Use", command=self.handle_how_to_use)
        how_to_use_button.pack()

        self.longest_road_label = tk.Label(frame_1, text="Longest road: ")
        self.shortest_road_label = tk.Label(frame_1, text="Shortest road: ")
        self.road_amount_label = tk.Label(frame_1, text="Road amount: ")
        self.road_amount_label.pack()
        self.longest_road_label.pack()
        self.shortest_road_label.pack()

        # Frame 2
        frame_2 = tk.Frame(
            self.root, highlightbackground="black", highlightthickness=1)
        frame_2.grid(row=0, column=1, sticky="nsew")

        self.info_text = tk.Text(frame_2)
        self.info_text.pack()

        self.canvas.get_tk_widget().grid(row=1, column=0, rowspan=2,
                                         columnspan=2, sticky="nsew")

    def start_ui(self):
        self.root.mainloop()
