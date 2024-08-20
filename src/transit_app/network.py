import time

from shapely import equals, intersection, snap
from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.multipoint import MultiPoint
from shapely.ops import nearest_points, split

from .algorithms import DFS, Dijkstra
from .constants import (CALCULATION_P_DISTANCE,
                        MIN_DISTANCE_BETWEEN_POINT_AND_ROAD,
                        MIN_DISTANCE_WHEN_PLACING_POINT)
from .utilities import create_hitbox

print(__name__)


class Network:

    def __init__(self) -> None:
        self.points = []  # All points except calculation points
        self.crossroads = set()  # All these points are inside self.points too
        self.roads = []  # LineStrings
        self.hitboxes = {}

        # Points that the currently building road is using
        self.temp_points = []
        self.temp_hitboxes = {}  # for temp points
        # Used for every road loop inside shortest_path function and its helper functions
        self.temp_roads = []

        self.current_road_points = []

        # 0: (Point, distance to point on linestring, road that point is on) and 1: (same stuff)
        self.calculation_points = {}
        self.highlighted_path = None

    def point_near_point(self, point: Point):
        nearby_points = []
        for existing_point in self.points:
            if point.dwithin(existing_point, MIN_DISTANCE_WHEN_PLACING_POINT):
                nearby_points.append(existing_point)
        if len(nearby_points) == 0:
            return False
        return nearby_points

    def invalid_point_placement(self, point: Point):
        """Returns True if added point is very near an existing point or an existing road, or False otherwise."""
        for existing_point in self.points:
            if point.dwithin(existing_point, MIN_DISTANCE_WHEN_PLACING_POINT):
                return True
        for existing_road in self.roads:
            if point.dwithin(existing_road, MIN_DISTANCE_WHEN_PLACING_POINT):
                return True
        return False

    def find_road_that_has_point(self, point: Point, used_roads: list):
        for road in used_roads:
            if point.dwithin(road, 1e-8):
                return road

    def find_and_move_road(self, point: Point, used_roads: list):
        for road in used_roads.copy():
            if point.dwithin(road, 1e-8):
                used_roads.remove(road)
                new_road = snap(road, point, 0.0001)
                used_roads.append(new_road)
                print(f"Moved Road: {new_road}")
                return new_road
        return False

    def find_shortest_path(self, point1: Point, point2: Point):
        """Finds the shortest path between point1 and point2 along a road. Uses Dijkstra's algorithm.
        Returns the points that make up the path, and the distance from start point to end point."""

        if not self.connected(point1, point2):
            print("POINT1 AND POINT2 ARE NOT CONNECTED")
            return False

        start_time1 = time.time()
        d = Dijkstra()
        used_roads = self.roads.copy()

        start_road = self.find_road_that_has_point(point1, used_roads)
        end_road = self.find_road_that_has_point(point2, used_roads)

        if equals(start_road, end_road):
            start_road = self.find_and_move_road(point1, used_roads)
            start_road = self.find_and_move_road(point2, used_roads)
            road_parts = list(split(start_road, point1).geoms)
            for part in road_parts.copy():
                if point2.dwithin(part, 1e-8):
                    more_parts = list(split(part, point2).geoms)
                    road_parts.remove(part)
                    road_parts += more_parts
            used_roads += road_parts

        else:
            start_road = self.find_and_move_road(point1, used_roads)
            end_road = self.find_and_move_road(point2, used_roads)

            start_road_parts = split(start_road, point1).geoms
            """
            print("START ROAD PARTS")
            for part in start_road_parts:
                print(part)
            print("")
            """

            end_road_parts = split(end_road, point2).geoms
            """
            print("END ROAD PARTS")
            for part in end_road_parts:
                print(part)
            print("")
            """

            used_roads += list(start_road_parts) + list(end_road_parts)

        end_time1 = time.time()
        print(f"TIME FOR FIND_SHORTEST_PATH 1: {end_time1- start_time1}")
        start_time2 = time.time()

        for road in used_roads:
            d.add_node(road.coords[0])
            d.add_node(road.coords[1])
            d.add_edge(
                road.coords[0], road.coords[1], road.length)
            d.add_edge(
                road.coords[1], road.coords[0], road.length)

        points, end_distance = d.find_distances(
            point1.coords[0], point2.coords[0])
        self.highlighted_path = MultiLineString([points])

        end_time2 = time.time()
        print(f"TIME FOR FIND_SHORTEST_PATH 2: {end_time2 - start_time2}")
        return (points, end_distance)

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
                if not (road is other_road) and \
                    (road.crosses(other_road) or
                     self.shared_coords(road, other_road)):
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
        """Splits road in segments based in the points in <split_points>. 
        These points must be on the road. Deletes the old road and returns new roads."""
        new_roads = []
        print(len(split_points))
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

        if road in self.roads:
            self.roads.remove(road)
        else:
            self.temp_roads.remove(road)
        return new_roads

    def point_ends_road(self, point: Point):
        """Returns True if <point> is the start or end point of an existing road, 
        or False otherwise."""
        for road in self.roads:
            if equals(point, Point(road.coords[0])) or equals(point, Point(road.coords[1])):
                return True
        return False

    def create_crossroads(self):
        """Checks points where two roads intersect and adds crossroads there. 
        Crossroad splits the existing roads. Returns list of new crossroads."""
        new_crossroads = set()
        used_roads = self.roads + self.temp_roads
        updated = {road: [] for road in used_roads}  # road: crossroads pairs
        for road in used_roads:
            for other_road in used_roads:
                if road != other_road and bool(intersection(road, other_road)):
                    crossroads = intersection(road, other_road)
                    if not isinstance(crossroads, MultiPoint) and not isinstance(crossroads, Point):
                        print("CROSSROADS IS NOT MULTIPOINT OR A POINT!")
                        return False
                    if isinstance(crossroads, MultiPoint):
                        crossroads = crossroads.geoms
                    else:
                        crossroads = [crossroads]
                    for crossroad in crossroads:
                        if self.point_ends_road(crossroad):
                            continue
                        nearby_points = self.point_near_point(crossroad)
                        if nearby_points:
                            if crossroad not in self.crossroads:
                                # If crossroad is new and near anything, can't add road
                                print("NEW CROSSROAD POINT NEAR A POINT")
                                return False
                            for nearby_point in nearby_points:
                                if nearby_point not in self.crossroads:
                                    # if crossroad is near a non-crossroad point, can't add road
                                    print("NON CROSSROAD POINT NEAR A CROSSROAD")
                                    return False
                        updated[road].append(crossroad)
                        new_crossroads.add(crossroad)

        new_roads = []
        for road in updated:
            if road not in used_roads or len(updated[road]) == 0:
                continue
            new_roads += self.split_road(road, updated[road])

        for crossroad in new_crossroads:
            self.points.append(crossroad)
            self.crossroads.add(crossroad)
            self.hitboxes[crossroad] = create_hitbox(crossroad)
        for road in new_roads:
            self._add_road(road, check_crossroads=False)

        return new_crossroads

    def snap_point_to_road(self, point: Point, road: LineString):
        """Snaps <point> to <road> if it is very near it, and returns the snapped point. 
        Returns False otherwise."""
        if road.dwithin(point, 1e-8):
            nearest_on_road = nearest_points(point, road)[1]
            snapped_point = snap(point, nearest_on_road, tolerance=0.0001)
            return snapped_point
        return False

    def add_calculation_point(self, point: Point):
        """Adds a point that distance is measured from, or to. 
        After adding two points, the next point will remove the previous two.
        """
        if len(self.calculation_points) == 2:
            self.calculation_points.clear()

        if len(self.calculation_points) == 1 and point.dwithin(self.calculation_points[0][0], 0.1):
            print("Can't add calculation point right next to another one!")
            return False
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
                    self.highlighted_path = None
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
                            "Points that the route goes through: ")
                        for index, point in enumerate(shortest_path[0]):
                            if index == 0:
                                print(f"START {point}")
                            elif index == len(shortest_path[0]) - 1:
                                print(f"END {point}")
                            else:
                                print(f"{index}: {point}")
                    else:
                        print("No path between calculation points!")
                return True

        return False

    def check_point_overlap(self, point: Point):
        """Checks if <point> overlaps with an existing points hitbox, 
        and returns the existing point if so."""
        for other_point in self.points:
            hitbox = self.hitboxes[other_point]
            if point.within(hitbox):
                return other_point

        for other_point in self.temp_points:
            hitbox = self.temp_hitboxes[other_point]
            if point.within(hitbox):
                return other_point
        return False

    def clear_temp(self):
        """Clears all temp values and current road points. 
        Used after cancelling a road."""
        self.temp_points.clear()
        self.temp_roads.clear()
        self.temp_hitboxes = {}
        self.current_road_points.clear()

    def add_point(self, point: Point) -> tuple | bool:
        """Checks if a point can be added to the network, and adds it.

        Args:
            point (Point): The point that is added.

        Returns: Tuple with the added point as the first member,
        and a boolean telling whether or not the point overlaps another as the second member.
        Returns False if the point could not be added.

        """
        point_overlaps = False
        overlapping_point: Point = self.check_point_overlap(point)

        if not overlapping_point:
            if self.invalid_point_placement(point):
                # if point is near another point or road, new road is cancelled
                print("INVALID POINT PLACEMENT")
                self.clear_temp()
                return False
            self.temp_points.append(point)
            self.temp_hitboxes[point] = create_hitbox(point)
        else:
            # sets an existing point as a point of a new road
            point = overlapping_point
            if len(self.current_road_points) != 1:
                # only highlights the starting point of road, not the ending point
                point_overlaps = True
            elif equals(point, self.current_road_points[0]):
                # if start and end are the same point, new road is cancelled
                self.clear_temp()
                return False

        self.current_road_points.append(point)
        if len(self.current_road_points) == 2:
            self._add_road(self.current_road_points)

        return (point, point_overlaps)

    def _add_road(self, added: list | LineString, check_crossroads=True):
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

        for road in self.roads:
            if equals(road, new_road):
                print("CANT ADD ROAD, IT IS EQUAL TO ANOTHER ROAD")
                self.clear_temp()
                return False

        for point in self.points:
            if point.dwithin(new_road, MIN_DISTANCE_BETWEEN_POINT_AND_ROAD) and \
                    not self.shared_coords(point, new_road):
                print("EXISTING POINT TOO CLOSE TO NEW ROAD")
                self.clear_temp()
                return False

        self.temp_roads.append(new_road)
        if check_crossroads:
            crossroads = self.create_crossroads()
            if crossroads is False:
                self.clear_temp()
                print(f"Crossroads was False, can't create road {new_road}")
                return False

        for point in self.temp_points:
            self.points.append(point)
        for point, hitbox in self.temp_hitboxes.items():
            self.hitboxes[point] = hitbox
        for road in self.temp_roads:
            self.roads.append(road)
        self.clear_temp()
        print(f"Added road: {new_road}")
        print(f"Amount of roads: {len(self.roads)}")
        return new_road
