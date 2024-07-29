import matplotlib.pyplot as plt
import mplcursors
from matplotlib.backend_bases import MouseButton, KeyEvent
from shapely import equals, intersection, line_merge, snap
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.geometry.multipoint import MultiPoint
from shapely.ops import nearest_points
from constants import hb_size, normal_p_color, selected_p_color, intersection_p_color, calculation_p_color
from algorithms import DFS, Dijkstra
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

print_click_info = False  # use to print information on each mouse click


def create_hitbox(point: Point) -> Polygon:
    b = point.bounds
    new_b = (b[0] - hb_size, b[1] - hb_size, b[2] + hb_size, b[3] + hb_size)
    return box(*new_b)


class Counter:
    def __init__(self):
        self.count = 1

    def __call__(self, amount=1):
        val = self.count
        self.count += amount
        return val


class Network:

    def __init__(self) -> None:
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)

        self.points = []  # Points
        self.roads = []  # LineStrings
        self.current_road_points = []  # Points
        self.current_road_connects_to = None
        self.current_road_first_point_existing = False
        self.plotted_points = {}  # (Point: plotted point) pairs
        self.plotted_lines = {}  # (LineString: plotted Line2D) pairs
        self.crossroads = []  # Points
        # 0: (Point, distance to point on linestring, road that point is on) and 1: (same stuff)
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

    def remove_road(self, road):
        "Removes road and the plotted line which corresponds to road."
        self.roads.remove(road)
        if road not in self.plotted_lines.keys():
            print("ROAD DOES NOT EXIST IN PLOTTED LINES DICTIONARY, CANNOT DELETE!")
        self.plotted_lines[road].remove()
        del self.plotted_lines[road]

    def crossroad_already_exists(self, crossroad: Point):
        for existing_crossroad in self.crossroads:
            if equals(crossroad, existing_crossroad):
                return True
        return False

    def find_shortest_path(self, point1: Point, point2: Point):
        """Finds the shortest path between point1 and point2 along a road. Uses Dijkstra's algorithm. Returns the roads that make up the path."""
        d = Dijkstra(self.roads)
        start_road = None
        end_road = None
        # create edges for graph
        road: LineString
        for road in self.roads:
            print("juu")
            if point1.dwithin(road, 1e-8):
                nearest_on_road = nearest_points(point1, road)[1]
                point1 = nearest_on_road
                start_road = road
            if point2.dwithin(road, 1e-8):
                nearest_on_road = nearest_points(point2, road)[1]
                point2 = nearest_on_road
                end_road = road
            other_road: LineString
            for other_road in self.roads:
                if not (road is other_road) and (road.crosses(other_road) or self.shared_coords(road, other_road)):
                    print("joo")
                    d.add_edge(road, other_road,
                               other_road.length)

        if not start_road:
            print("point 1 is not on any road!")
            return

        distances = d.find_distances(start_road)
        print(f"Distances: {distances}")
        print(f"Distance to end: {distances[end_road] + start_road.length}")
        # return True
        # return False

    def shared_coords(self, object1: LineString, object2: LineString):
        """Returns True if object1 and object2 share any coordinates, or False otherwise. Objects can be Points or LineStrings.
        For roads, the coordinates are the turning points of the road, not every coordinate that is covered by the LineString."""
        if isinstance(object1, Point):
            if isinstance(object2, Point):
                return object1.x == object2.x and object1.y == object2.y
            elif isinstance(object2, LineString):
                for coord in object2.coords:
                    if object1.x == coord[0] and object1.y == coord[1]:
                        return True
                return False
        elif isinstance(object1, LineString):
            if isinstance(object2, Point):
                for coord in object1.coords:
                    if object2.x == coord[0] and object2.y == coord[1]:
                        return True
                return False
            elif isinstance(object2, LineString):
                for coord1 in object1.coords:
                    for coord2 in object2.coords:
                        if coord1 == coord2:
                            return True
                return False

    def connected(self, point1: Point, point2: Point):
        dfs = DFS(self.roads)
        start_road = None
        road: LineString
        for road in self.roads:
            if point1.dwithin(road, 1e-8):
                start_road = road
            other_road: LineString
            for other_road in self.roads:
                if not (road is other_road) and (road.crosses(other_road) or self.shared_coords(road, other_road)):
                    # could be cleaned up?
                    if other_road not in dfs.graph[road]:
                        dfs.add_edge(road, other_road)
        if not start_road:
            print("point 1 is not on any road!")
            return
        visited_roads = dfs.search(start_road)
        for visited_road in visited_roads:
            if point2.dwithin(visited_road, 1e-8):
                print(dfs.graph)
                return True
        return False

    def split_road_in_two_halves(self, road, split_point):
        new_road_1 = LineString([road.coords[0], split_point.coords[0]])
        new_road_2 = LineString([split_point.coords[0], road.coords[1]])

        self.remove_road(road)
        self.roads.append(new_road_1)
        self.roads.append(new_road_2)

        x, y = new_road_1.xy
        plotted_line = self.ax.plot(
            x, y, label=f"Road {self.counter()}, length {new_road_1.length}")[0]
        self.plotted_lines[new_road_1] = plotted_line

        x, y = new_road_2.xy
        plotted_line = self.ax.plot(
            x, y, label=f"Road {self.counter()}, length {new_road_2.length}")[0]
        self.plotted_lines[new_road_2] = plotted_line

        self.current_road_points.clear()
        self.create_crossroads()
        self.create_cursor()
        print(f"Amount of roads: {len(self.roads)}")

    def create_crossroads(self):
        """Checks points where two roads intersect and adds crossroads there. Crossroad splits the existing roads."""

        updated = {}  # road: crossroads pairs, can't update them inside for loops because new roads get added, which extends the loops
        for road in self.roads:
            updated[road] = []
            for other_road in self.roads:
                if road != other_road and bool(intersection(road, other_road)):
                    crossroads = intersection(road, other_road)
                    for point in self.points:
                        if self.shared_coords(point, crossroads):
                            print("nope")
                            print(self.crossroads)
                            return
                    if type(crossroads) is MultiPoint:
                        for point in crossroads.geoms:
                            # prevents duplicate crossroads
                            if not self.crossroad_already_exists(point):
                                self.crossroads.append(point)
                                updated[road].append(crossroads)
                                self.ax.plot(
                                    *point.xy, f"{intersection_p_color}o")
                    else:
                        # prevents duplicate crossroads
                        if not self.crossroad_already_exists(crossroads):
                            self.crossroads.append(crossroads)
                            updated[road].append(crossroads)
                            self.ax.plot(*crossroads.xy,
                                         f"{intersection_p_color}o")
        for road in updated:
            for crossroads in updated[road]:
                self.split_road_in_two_halves(road, crossroads)

    def add_calculation_point(self, point: Point):
        """Adds a point that distance is measured from, or to. After adding two points, the next point will remove the previous two.
        Points currently have to be on the same linestring."""
        different_linestrings = False
        if len(self.calculation_points) == 2:
            self.calculation_points.clear()
            for plotted_point in self.plotted_calculation_points:
                plotted_point.remove()
            self.plotted_calculation_points.clear()
        for road in self.roads:
            nearest_on_road = nearest_points(point, road)[1]
            snapped_point = snap(point, nearest_on_road, tolerance=0.7)
            # if calculation point is close enough to any road to snap to it
            if snapped_point != point:
                point = snapped_point
                if len(self.calculation_points) == 0:
                    self.calculation_points[0] = (
                        point, road.project(point), road)
                elif len(self.calculation_points) == 1:
                    self.calculation_points[1] = (
                        point, road.project(point), road)
                    print(
                        f"Distance between the two points: {abs(self.calculation_points[1][1] - self.calculation_points[0][1])}")
                    print(
                        f"Connected: {self.connected(self.calculation_points[0][0], self.calculation_points[1][0])}")
                    print(
                        f"Pathfinding: {self.find_shortest_path(self.calculation_points[0][0], self.calculation_points[1][0])}")
                plotted_point = self.ax.plot(
                    *point.xy, f"{calculation_p_color}o")[0]
                self.plotted_calculation_points.append(plotted_point)
                return True
        return False

    def check_point_overlap(self, point: Point):
        """Checks if <point> overlaps with an existing points hitbox, and returns the existing point if so."""
        for other_point in self.points:
            hitbox = create_hitbox(other_point)
            if point.within(hitbox):
                return other_point
        return False

    def add_point_to_road(self, point: Point):
        """Adds a point to the road that is currently building."""
        self.reset_plotted_point_colors()
        overlapping_point: Point = self.check_point_overlap(point)

        if not overlapping_point:
            # create new point normally
            self.points.append(point)
            self.current_road_points.append(point)
            plotted_point = self.ax.plot(*point.xy, f"{normal_p_color}o")[0]
            self.plotted_points[point] = plotted_point
            self.ax.plot(*create_hitbox(point).exterior.xy)

        else:
            # sets an existing point as a point of a new road
            self.plotted_points[overlapping_point].set_color(
                selected_p_color)
            self.current_road_points.append(overlapping_point)

        if len(self.current_road_points) == 2:
            self.add_road(self.current_road_points)
            self.current_road_points.clear()

    def add_road(self, points: list):
        """Creates new road from points given, and plots it. The list <points> must consist of shapely.Point objects."""
        coords = []
        point: Point
        for point in points:
            coords.append((point.x, point.y))
        new_road = LineString(coords)
        self.roads.append(new_road)

        x, y = new_road.xy
        plotted_line = self.ax.plot(
            x, y, label=f"Road {self.counter()}, length {new_road.length}")[0]
        self.plotted_lines[new_road] = plotted_line

        self.create_crossroads()
        self.create_cursor()
        print(f"Amount of roads: {len(self.roads)}")

    def onclick(self, event):
        if print_click_info:
            print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
                  ('double' if event.dblclick else 'single', event.button,
                   event.x, event.y, event.xdata, event.ydata))
        if event.button == MouseButton.RIGHT:
            return
        elif event.button == MouseButton.LEFT:
            point = Point(event.xdata, event.ydata)
            self.add_point_to_road(point)
        elif event.button == MouseButton.MIDDLE:
            point = Point(event.xdata, event.ydata)
            self.add_calculation_point(point)
        else:
            print("Invalid input!")

    def onkey(self, event):
        return
        if event.key == "c":
            print(self.connected(self.points[0], self.points[1]))
        else:
            print("Invalid input!")

    def main(self):
        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.fig.canvas.mpl_connect('key_press_event', self.onkey)

        # Show the plot
        plt.ion()
        plt.show(block=True)


if __name__ == "__main__":
    n = Network()
    n.main()
