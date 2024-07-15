import matplotlib.pyplot as plt
import mplcursors
from matplotlib.backend_bases import MouseButton
from shapely import equals, intersection, snap
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.multipoint import MultiPoint
from shapely.ops import nearest_points

"""
# Create a line representing a road
road = LineString([(0, 0), (1, 2), (2, 3), (4, 4)])

# Plot the road
x, y = road.xy
plt.plot(x, y, label='Road')

# Define points on the road
point_a = Point(1, 2)
point_b = Point(2, 3)

# Plot the points
plt.plot(*point_a.xy, 'go', label='Point A')
plt.plot(*point_b.xy, 'ro', label='Point B')

# Calculate the distance between the points on the road
distance = point_a.distance(point_b)
print(f"Distance between points A and B: {distance}")
"""

hb_size = 0.3
normal_p_color = "b"
selected_p_color = "r"
intersection_p_color = "g"
calculation_p_color = "c"


def create_hitbox(point: Point) -> Polygon:
    b = point.bounds
    new_b = (b[0] - hb_size, b[1] - hb_size, b[2] + hb_size, b[3] + hb_size)
    return box(*new_b)


class Counter:
    def __init__(self):
        self.count = 1

    def __call__(self):
        val = self.count
        self.count += 1
        return val


class Hmmm:

    def __init__(self) -> None:
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)

        self.points = []  # Points
        self.roads = []  # LineStrings
        self.current_road_points = []  # Points
        self.plotted_points = {}  # (Point: plotted point) pairs
        self.crossroads = []  # Points
        self.calculation_points = {}
        self.plotted_calculation_points = []

        self.counter = Counter()

    def create_cursor(self):
        """Needs to be recreated every time new data is added?"""
        def joku(sel):
            sel.annotation.set_text(sel.artist)

        cursor = mplcursors.cursor(hover=True)
        cursor.connect(
            "add", lambda sel: joku(sel))

    def reset_plotted_point_colors(self):
        for plotted_point in self.plotted_points.values():
            plotted_point.set_color(normal_p_color)

    def crossroad_already_exists(self, crossroad: Point):
        for existing_crossroad in self.crossroads:
            if equals(crossroad, existing_crossroad):
                return True
        return False

    def create_crossroads(self):
        """Checks points where two roads intersect and adds crossroads there."""
        for road in self.roads:
            for other_road in self.roads:
                if road != other_road and bool(intersection(road, other_road)):
                    crossroads = intersection(road, other_road)
                    if type(crossroads) is MultiPoint:
                        for point in crossroads.geoms:
                            # prevents duplicate crossroads
                            if not self.crossroad_already_exists(point):
                                self.crossroads.append(point)
                                self.ax.plot(
                                    *point.xy, f"{intersection_p_color}o")
                    else:
                        # prevents duplicate crossroads
                        if not self.crossroad_already_exists(crossroads):
                            self.crossroads.append(crossroads)
                            self.ax.plot(*crossroads.xy,
                                         f"{intersection_p_color}o")

    def add_point_to_road(self, point: Point):
        """Adds a point to the road that is currently building."""
        for other_point in self.points:
            hitbox = create_hitbox(other_point)
            if point.within(hitbox):
                if len(self.current_road_points) > 0:
                    # a road can only use an existing point as a starting point
                    return
                else:
                    # sets an existing point as the starting point of a new road
                    self.plotted_points[other_point].set_color(
                        selected_p_color)
                    self.current_road_points.append(other_point)
                    return

        self.reset_plotted_point_colors()
        self.current_road_points.append(point)
        self.points.append(point)
        plotted_point = self.ax.plot(*point.xy, f"{normal_p_color}o")[0]
        self.plotted_points[point] = plotted_point
        self.ax.plot(*create_hitbox(point).exterior.xy)

    def add_calculation_point(self, point: Point):
        """Adds a point that distance is measured from, or to. After adding two points, the next point will remove the previous two.
        Points currently have to be on the same linestring."""
        if len(self.calculation_points) == 2:
            self.calculation_points.clear()
            for plotted_point in self.plotted_calculation_points:
                plotted_point = plotted_point[0]
                plotted_point.remove()
            self.plotted_calculation_points.clear()
        for road in self.roads:
            nearest_on_road = nearest_points(point, road)[1]
            snapped_point = snap(point, nearest_on_road, tolerance=0.7)
            # if calculation point is close enough to any road to snap to it
            if snapped_point != point:
                point = snapped_point
                # print(road.project(point))
                if len(self.calculation_points) == 0:
                    self.calculation_points[0] = (
                        point, road.project(point), road)
                elif len(self.calculation_points) == 1:
                    self.calculation_points[1] = (
                        point, road.project(point), road)
                    if road != self.calculation_points[0][2]:
                        self.calculation_points.clear()
                        for plotted_point in self.plotted_calculation_points:
                            plotted_point = plotted_point[0]
                            plotted_point.remove()
                        self.plotted_calculation_points.clear()
                        print(
                            "Points are on two different linestrings, not supported yet!")
                        return False
                    print(
                        f"Distance between the two points: {abs(self.calculation_points[1][1] - self.calculation_points[0][1])}")
                plotted_point = self.ax.plot(
                    *point.xy, f"{calculation_p_color}o")
                self.plotted_calculation_points.append(plotted_point)
                return True
        return False

    def finish_road(self):
        """Creates new road."""
        if len(self.current_road_points) < 2:
            return
        new_road = LineString([(point.x, point.y)
                               for point in self.current_road_points])
        print(new_road.project(self.points[2]))
        self.roads.append(new_road)
        x, y = new_road.xy
        self.ax.plot(
            x, y, label=f"Road {self.counter()}, length {new_road.length}")
        self.current_road_points.clear()
        self.create_crossroads()
        self.create_cursor()

    def onclick(self, event):
        print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              ('double' if event.dblclick else 'single', event.button,
               event.x, event.y, event.xdata, event.ydata))
        if event.button == MouseButton.RIGHT:
            self.finish_road()
        elif event.button == MouseButton.LEFT:
            point = Point(event.xdata, event.ydata)
            self.add_point_to_road(point)
        elif event.button == MouseButton.MIDDLE:
            point = Point(event.xdata, event.ydata)
            self.add_calculation_point(point)
        else:
            print("Invalid input!")

    def main(self):
        event = self.fig.canvas.mpl_connect('button_press_event', self.onclick)

        # Show the plot
        plt.ion()
        plt.show(block=True)


if __name__ == "__main__":
    h = Hmmm()
    h.main()
    print("Hello world!")
