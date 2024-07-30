import matplotlib.pyplot as plt
import mplcursors
from matplotlib.backend_bases import MouseButton
from shapely import intersection, snap
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.multipoint import MultiPoint
from shapely.ops import nearest_points
from constants import HITBOX_SIZE, NORMAL_P_COLOR, SELECTED_P_COLOR, INTERSECTION_P_COLOR, CALCULATION_P_COLOR
from algorithms import DFS, Dijkstra


PRINT_CLICK_INFO = False  # use to print information on each mouse click
NO_CURSOR = False  # No yellow boxes


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

    def remove_road(self, road):
        "Removes road and the plotted line which corresponds to road."
        self.roads.remove(road)
        if road not in self.plotted_lines.keys():
            print("ROAD DOES NOT EXIST IN PLOTTED LINES DICTIONARY, CANNOT DELETE!")
        self.plotted_lines[road].remove()
        del self.plotted_lines[road]

    def crossroad_already_exists(self, crossroad: Point):
        """Returns True if added crossroad is very near an existing one, or False otherwise."""
        for existing_crossroad in self.crossroads:
            if crossroad.dwithin(existing_crossroad, 1e-8):
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

    def split_road(self, road: LineString, split_points: list):
        new_roads = []
        if len(split_points) == 0:
            print("Empty split points list!")
            return
        if len(split_points) == 1:
            new_road_1 = LineString(
                [road.coords[0], split_points[0].coords[0]])
            new_road_2 = LineString(
                [split_points[0].coords[0], road.coords[1]])
            new_roads.append(new_road_1)
            new_roads.append(new_road_2)
        else:
            first_road = LineString(
                [road.coords[0], split_points[0].coords[0]])
            new_roads.append(first_road)

            for i in range(1, len(split_points)):
                new_road = LineString(
                    [split_points[i - 1].coords[0], split_points[i].coords[0]])
                new_roads.append(new_road)

            last_road = LineString(
                [split_points[-1].coords[0], road.coords[1]])
            new_roads.append(last_road)

        for new_road in new_roads:
            self.add_road(new_road)
        self.remove_road(road)

        self.current_road_points.clear()

    def create_crossroads(self):
        """Checks points where two roads intersect and adds crossroads there. Crossroad splits the existing roads."""

        for road in self.roads:
            for other_road in self.roads:
                if road != other_road and bool(intersection(road, other_road)):
                    crossroads = intersection(road, other_road)
                    # if crossroad is at the same point as a road ending point, nothing is done
                    for point in self.points:
                        if self.shared_coords(point, crossroads):
                            continue

                    if isinstance(crossroads, MultiPoint):
                        for point in crossroads.geoms:
                            # prevents duplicate crossroads
                            if not self.crossroad_already_exists(point):
                                self.crossroads.append(point)
                                self.ax.plot(
                                    *point.xy, f"{INTERSECTION_P_COLOR}o")
                    else:
                        # prevents duplicate crossroads
                        if not self.crossroad_already_exists(crossroads):
                            self.crossroads.append(crossroads)
                            self.ax.plot(*crossroads.xy,
                                         f"{INTERSECTION_P_COLOR}o")

        updated = {}  # road: crossroads pairs
        for road in self.roads:
            updated[road] = []
        for road in self.roads:
            for crossroad in self.crossroads:
                if road.dwithin(crossroad, 1e-8) and not self.shared_coords(road, crossroad):
                    updated[road].append(crossroad)
        for road in updated:
            if road not in self.roads:
                continue
            self.split_road(road, updated[road])

    def add_calculation_point(self, point: Point):
        """Adds a point that distance is measured from, or to. After adding two points, the next point will remove the previous two.
        Points currently have to be on the same linestring."""
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
                    *point.xy, f"{CALCULATION_P_COLOR}o")[0]
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
            plotted_point = self.ax.plot(*point.xy, f"{NORMAL_P_COLOR}o")[0]
            self.plotted_points[point] = plotted_point
            self.ax.plot(*create_hitbox(point).exterior.xy)

        else:
            # sets an existing point as a point of a new road
            self.plotted_points[overlapping_point].set_color(
                SELECTED_P_COLOR)
            self.current_road_points.append(overlapping_point)

        if len(self.current_road_points) == 2:
            self.add_road(self.current_road_points)
            self.current_road_points.clear()
            self.create_crossroads()

    def add_road(self, added: list | LineString):
        """Creates new road from points given, and plots it. <added> can be a list of shapely.Point objects or a LineString."""
        coords = []
        if isinstance(added, list):
            point: Point
            for point in added:
                coords.append((point.x, point.y))
            new_road = LineString(coords)
        else:
            new_road = added

        self.roads.append(new_road)
        x, y = new_road.xy
        plotted_line = self.ax.plot(
            x, y, label=f"Road {self.counter()}, length {new_road.length}")[0]
        self.plotted_lines[new_road] = plotted_line

        self.create_cursor()
        print(f"Amount of roads: {len(self.roads)}")

    def onclick(self, event):
        if PRINT_CLICK_INFO:
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
