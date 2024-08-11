import matplotlib.pyplot as plt
import mplcursors
from matplotlib.backend_bases import MouseButton
from shapely import intersection, snap
from shapely.geometry import LineString, Point, Polygon, box, MultiLineString
from shapely.geometry.multipoint import MultiPoint
from shapely.ops import nearest_points, split
from constants import HITBOX_SIZE, NORMAL_P_COLOR, SELECTED_P_COLOR, INTERSECTION_P_COLOR, CALCULATION_P_COLOR, CALCULATION_P_DISTANCE
from algorithms import DFS, Dijkstra
from ui import UI


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
        self.points = []  # All points except calculation points
        self.roads = []  # LineStrings
        self.current_road_points = []  # Points
        self.current_road_connects_to = None
        self.current_road_first_point_existing = False
        self.hitboxes = {}

        # Used for every road loop inside shortest_path function and its helper functions
        self.temp_roads = []

        # 0: (Point, distance to point on linestring, road that point is on) and 1: (same stuff)
        self.calculation_points = {}

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

    def remove_road(self, road):
        "Removes road."
        self.roads.remove(road)

    def invalid_point_placement(self, point: Point):
        """Returns True if added point is very near an existing point, or False otherwise."""
        for existing_point in self.points:
            if point.dwithin(existing_point, 1e-8):
                return True
        return False

    def find_and_move_road(self, point: Point):
        for road in self.temp_roads.copy():
            if point.dwithin(road, 1e-8):
                self.temp_roads.remove(road)
                new_road = snap(road, point, 0.0001)
                self.temp_roads.append(new_road)
                print(f"Moved Road: {new_road}")
                return new_road
        return False

    def find_shortest_path(self, point1: Point, point2: Point):
        """Finds the shortest path between point1 and point2 along a road. Uses Dijkstra's algorithm. Returns the roads that make up the path, and the distance from start to end."""

        if not self.connected(point1, point2):
            return False
        d = Dijkstra()
        start_road = None
        end_road = None
        start_road_parts = None
        end_road_parts = None
        self.temp_roads = self.roads.copy()

        start_road = self.find_and_move_road(point1)
        end_road = self.find_and_move_road(point2)

        start_road_parts = split(start_road, point1).geoms
        print("START ROAD PARTS")
        for part in start_road_parts:
            print(part)
        print("")

        d.add_node(start_road_parts[0].coords[0])
        if len(start_road_parts) > 1:
            d.add_node(point1.coords[0])
            d.add_node(start_road_parts[1].coords[1])
        else:
            d.add_node(start_road_parts[0].coords[1])

        if len(start_road_parts) > 1:
            d.add_edge(
                start_road_parts[0].coords[0], point1.coords[0], start_road_parts[0].length)
            d.add_edge(
                point1.coords[0], start_road_parts[0].coords[0], start_road_parts[0].length)
            d.add_edge(
                point1.coords[0], start_road_parts[1].coords[1],  start_road_parts[1].length)
            d.add_edge(
                start_road_parts[1].coords[1], point1.coords[0], start_road_parts[1].length)
        else:
            d.add_edge(
                start_road_parts[0].coords[0], start_road_parts[0].coords[1], start_road_parts[0].length)
            d.add_edge(
                start_road_parts[0].coords[1], start_road_parts[0].coords[0], start_road_parts[0].length)

        end_road_parts = split(end_road, point2).geoms
        print("END ROAD PARTS")
        for part in end_road_parts:
            print(part)
        print("")

        d.add_node(end_road_parts[0].coords[0])
        if len(end_road_parts) > 1:
            d.add_node(point2.coords[0])
            d.add_node(end_road_parts[1].coords[1])
        else:
            d.add_node(end_road_parts[0].coords[1])

        if len(end_road_parts) > 1:
            d.add_edge(
                end_road_parts[0].coords[0], point2.coords[0], end_road_parts[0].length)
            d.add_edge(
                point2.coords[0], end_road_parts[0].coords[0], end_road_parts[0].length)
            d.add_edge(
                end_road_parts[1].coords[1], point2.coords[0], end_road_parts[1].length)
            d.add_edge(
                point2.coords[0], end_road_parts[1].coords[1], end_road_parts[1].length)
        else:
            d.add_edge(
                end_road_parts[0].coords[0], end_road_parts[0].coords[1], end_road_parts[0].length)
            d.add_edge(
                end_road_parts[0].coords[1], end_road_parts[0].coords[0], end_road_parts[0].length)

        self.temp_roads += list(start_road_parts) + list(end_road_parts)

        point: Point
        for point in self.points:
            d.add_node(point.coords[0])
            other_point: Point
            for other_point in self.points:
                if point is other_point:
                    continue
                d.add_node(other_point.coords[0])

                road: LineString
                for road in self.temp_roads:
                    # checks if road connects point and other point
                    if (road.coords[0] == point.coords[0]
                        or road.coords[1] == point.coords[0]) and (road.coords[0] == other_point.coords[0]
                                                                   or road.coords[1] == other_point.coords[0]):
                        d.add_edge(
                            point.coords[0], other_point.coords[0], road.length)
                        d.add_edge(
                            other_point.coords[0], point.coords[0], road.length)

        roads, end_distance = d.find_distances(
            point1.coords[0], point2.coords[0])
        print("SELF ROADS")
        print(self.roads)
        return (roads, end_distance)

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
        """Returns True if <point1> and <point2> are connected by roads, or False otherwise."""
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
        """Splits road in segments based in the points in <split_points>. These points must be on the road. Deletes the old road and returns new roads."""
        # IMPORTANT this could be remade using split(),
        # but then because floating point problems, the road would need to be snapped to each point in <split_points>,
        # which might be difficult if there's more than 1 point.
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

        self.remove_road(road)
        return new_roads

    def create_crossroads(self):
        """Checks points where two roads intersect and adds crossroads there. Crossroad splits the existing roads. Returns list of new crossroads."""
        new_crossroads = []
        for road in self.roads:
            for other_road in self.roads:
                if road != other_road and bool(intersection(road, other_road)):
                    crossroads = intersection(road, other_road)
                    if isinstance(crossroads, MultiPoint):
                        crossroads = crossroads.geoms
                    else:
                        crossroads = [crossroads]
                    for crossroad in crossroads:
                        new_crossroads.append(crossroad)

        updated = {}  # road: crossroads pairs
        new_roads = []  # roads created later by split_road()
        for road in self.roads:
            updated[road] = []
        road: LineString
        for road in self.roads:
            for crossroad in new_crossroads:
                snapped_crossroad = self.snap_point_to_road(crossroad, road)
                if snapped_crossroad and not self.shared_coords(road, snapped_crossroad):
                    if self.check_point_overlap(crossroad):
                        # Road cannot be created if crossroad is near an existing point
                        return False
                    updated[road].append(snapped_crossroad)

        for road in updated:
            if road not in self.roads or len(updated[road]) == 0:
                continue
            new_roads += self.split_road(road, updated[road])

        for crossroad in new_crossroads:
            self.points.append(crossroad)
            self.hitboxes[crossroad] = create_hitbox(crossroad)
        for road in new_roads:
            self.add_road(road, check_crossroads=False)

        return new_crossroads

    def snap_point_to_road(self, point: Point, road: LineString):
        """Snaps <point> to <road> if it is very near it, and returns the snapped point. Returns False otherwise."""
        if road.dwithin(point, 1e-8):
            nearest_on_road = nearest_points(point, road)[1]
            snapped_point = snap(point, nearest_on_road, tolerance=0.0001)
            return snapped_point
        return False

    def add_calculation_point(self, point: Point):
        """Adds a point that distance is measured from, or to. After adding two points, the next point will remove the previous two.
        """

        if len(self.calculation_points) == 2:
            self.calculation_points.clear()

        road: LineString
        for road in self.roads:
            if point.dwithin(road, CALCULATION_P_DISTANCE):
                nearest_on_road = nearest_points(point, road)[1]
                point = snap(point, nearest_on_road,
                             tolerance=CALCULATION_P_DISTANCE)
                # if calculation point is close enough to any road to snap to it
                if len(self.calculation_points) == 0:
                    calculation_point = (
                        point, road.project(point), road)
                    self.calculation_points[0] = calculation_point
                elif len(self.calculation_points) == 1:
                    calculation_point = (
                        point, road.project(point), road)
                    self.calculation_points[1] = calculation_point

                    print(
                        f"CALCULATION POINT 1: {self.calculation_points[0][0]}")
                    print(
                        f"CALCULATION POINT 2: {self.calculation_points[1][0]}")
                    """
                    print(
                        f"Distance between the two points: {abs(self.calculation_points[1][1] - self.calculation_points[0][1])}")
                    print(
                        f"Connected: {self.connected(self.calculation_points[0][0], self.calculation_points[1][0])}")
                    """
                    shortest_path = self.find_shortest_path(
                        self.calculation_points[0][0], self.calculation_points[1][0])
                    if shortest_path:
                        print(
                            f"Distance from point 1 to point 2: {shortest_path[1]}")
                        print(
                            f"Points that the route goes through: {shortest_path[0]}")
                    else:
                        print("No path between calculation points!")
                return True

        return False

    def check_point_overlap(self, point: Point):
        """Checks if <point> overlaps with an existing points hitbox, and returns the existing point if so."""
        for other_point in self.points:
            hitbox = self.hitboxes[other_point]
            if point.within(hitbox):
                return other_point
        return False

    def add_point_to_road(self, point: Point) -> tuple:
        """_summary_

        Args:
            point (Point): _description_

        Returns:
            tuple: A tuple containing the added point, boolean that tells if added point was an existing one, the added road if one was built and any crossroads that were made.
        """
        point_overlaps = False
        overlapping_point: Point = self.check_point_overlap(point)

        if not overlapping_point:
            # create new point normally
            self.points.append(point)
            self.hitboxes[point] = create_hitbox(point)
        else:
            # sets an existing point as a point of a new road
            point = overlapping_point
            point_overlaps = True

        self.current_road_points.append(point)
        if len(self.current_road_points) == 2:
            print(self.current_road_points)
            self.add_road(self.current_road_points)
            self.current_road_points.clear()

        return (point, point_overlaps)

    def add_road(self, added: list | LineString, check_crossroads=True):
        """Checks that given road can be created, and creates it if so. <added> can be a list of shapely.Point objects or a LineString.
        Returns the road, or False if it could not be created."""
        coords = []
        if isinstance(added, list):
            point: Point
            for point in added:
                coords.append((point.x, point.y))
            new_road = LineString(coords)
        else:
            new_road = added

        self.roads.append(new_road)
        if check_crossroads:
            crossroads = self.create_crossroads()
            if crossroads is False:
                print("Crossroads was False")
                self.remove_road(new_road)
                # deletes current road points if they weren't permanent
                for point in self.current_road_points:
                    to_be_removed = True
                    for road in self.roads:
                        if point.coords[0] == road.coords[0] or point.coords[0] == road.coords[1]:
                            to_be_removed = False
                            break
                    if to_be_removed:
                        self.points.remove(point)
                        del self.hitboxes[point]
                print(f"Can't create road {new_road}")
                return False
        self.create_cursor()
        print(f"Amount of roads: {len(self.roads)}")
        return new_road

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
