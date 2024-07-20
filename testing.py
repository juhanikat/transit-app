import matplotlib.pyplot as plt
import mplcursors
from matplotlib.backend_bases import MouseButton, KeyEvent
from shapely import equals, intersection, line_merge, snap
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
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

print_click_info = False  # use to print information on each mouse click

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

    def __call__(self, amount=1):
        val = self.count
        self.count += amount
        return val


class DFS:
    def __init__(self, nodes):
        self.nodes = nodes
        self.graph = {node: [] for node in nodes}

    def add_edge(self, a, b):
        self.graph[a].append(b)
        self.graph[b].append(a)

    def visit(self, node):
        if node in self.visited:
            return
        self.visited.add(node)

        for next_node in self.graph[node]:
            self.visit(next_node)

    def search(self, start_node):
        self.visited = set()
        self.visit(start_node)
        return self.visited


class Hmmm:

    def __init__(self) -> None:
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)

        self.points = []  # Points
        self.roads = []  # LineStrings
        self.current_road_points = []  # Points
        self.current_road_connects_to = None
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

    def crossroad_already_exists(self, crossroad: Point):
        for existing_crossroad in self.crossroads:
            if equals(crossroad, existing_crossroad):
                return True
        return False

    def find_shortest_path(self, point1: Point, point2: Point):
        """Finds the shortest path between point1 and point2 along a road."""
        dfs = DFS(self.roads)
        start_road = None
        road: LineString
        for road in self.roads:
            if point1.dwithin(road, 1e-8):
                nearest_on_road = nearest_points(point1, road)[1]
                point1 = nearest_on_road
                start_road = road
            other_road: LineString
            for other_road in self.roads:
                if not (road is other_road) and road.crosses(other_road):
                    dfs.add_edge(road, other_road)
        if not start_road:
            print("point 1 is not on any road!")
            return
        visited_roads = dfs.search(start_road)
        visited_road: LineString
        for visited_road in visited_roads:
            if point2.dwithin(visited_road, 1e-8):
                nearest_on_road = nearest_points(point2, road)[1]
                point2 = nearest_on_road
                end_road = visited_road
                print(start_road.coords[0])
                print(end_road.coords[-1])
                # return True
        # return False

    def shared_coords(self, road1: LineString, road2: LineString):
        """Returns True if road1 and road2 share any coordinates, or False otherwise.
        Coordinates are the turning points of the road, not every coordinate that is covered by the LineString."""
        for coord1 in road1.coords:
            for coord2 in road2.coords:
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
                    if road != self.calculation_points[0][2]:
                        print(
                            "Points are on two different linestrings, distance not supported yet!")
                        different_linestrings = True
                    if not different_linestrings:
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
        overlapping_point = self.check_point_overlap(point)

        if not overlapping_point:
            # create new point normally
            self.points.append(point)
            self.current_road_points.append(point)
            plotted_point = self.ax.plot(*point.xy, f"{normal_p_color}o")[0]
            self.plotted_points[point] = plotted_point
            self.ax.plot(*create_hitbox(point).exterior.xy)
            if len(self.current_road_points) == 2:
                self.add_road()
        else:
            if len(self.current_road_points) > 0:
                # only the starting point of the new road can be an existing point
                return
            # sets an existing point as the starting point of a new road
            self.plotted_points[overlapping_point].set_color(
                selected_p_color)
            self.current_road_points.append(overlapping_point)
            for road in self.roads:
                for coord in road.coords:
                    if overlapping_point.coords[0] == coord:
                        if coord != road.coords[-1] and coord != road.coords[0]:
                            print(
                                "You can only start a new road from the first or last point on the existing road!")
                            print("Creating new road here.")
                        else:
                            # used later to merge these two roads
                            self.current_road_connects_to = road
                            print(
                                "Continuing existing road, will be merged when finished")

    def add_road(self):
        """Creates new road."""
        new_road = LineString([(point.x, point.y)
                               for point in self.current_road_points])
        """
        if self.current_road_connects_to:
            # join the new and existing roads together, then delete the existing road from roads and the plot too
            new_road = MultiLineString(
                [new_road, self.current_road_connects_to])
            new_road = line_merge(new_road)
            self.plotted_lines[self.current_road_connects_to].remove()
            self.roads.remove(self.current_road_connects_to)
            self.current_road_connects_to = None
        """
        self.roads.append(new_road)
        x, y = new_road.xy
        plotted_line = self.ax.plot(
            x, y, label=f"Road {self.counter()}, length {new_road.length}")[0]
        self.plotted_lines[new_road] = plotted_line
        self.current_road_points.clear()
        self.create_crossroads()
        self.create_cursor()
        print(f"Amount of roads: {len(self.roads)}")

    def finish_road(self):
        """Cancel road building mode."""
        pass

    def onclick(self, event):
        if print_click_info:
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
    h = Hmmm()
    h.main()
