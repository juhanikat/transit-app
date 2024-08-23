import time

from shapely import equals, intersection, snap
from shapely.geometry import LineString, MultiLineString, Point
from shapely.geometry.multipoint import MultiPoint
from shapely.ops import nearest_points, split

from .algorithms import DFS, Dijkstra
from .constants import (CALCULATION_P_DISTANCE, MIN_DISTANCE_BETWEEN_C_POINTS,
                        MIN_DISTANCE_BETWEEN_POINT_AND_ROAD)
from .utilities import (AddPointOutput, AddRoadOutput, ShortestPathOutput,
                        create_hitbox, find_and_move_road,
                        find_road_that_has_point, invalid_point_placement,
                        point_ends_road, point_near_point, shared_coords)


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

        self.shortest_path_output = None
        self.add_point_output = None
        self._add_road_output = None

    def find_shortest_path(self, point1: Point, point2: Point):
        """Finds the shortest path between point1 and point2 along a road. Uses Dijkstra's algorithm.
        If a path can be found, returns the points that make up the path, and the distance from start point to end point.
        Returns False otherwise."""

        if not self.connected(point1, point2):
            self.shortest_path_output = ShortestPathOutput(
                error="POINT1 AND POINT2 ARE NOT CONNECTED")
            return self.shortest_path_output

        start_time1 = time.time()
        d = Dijkstra()
        used_roads = self.roads.copy()

        start_road = find_road_that_has_point(point1, used_roads)
        end_road = find_road_that_has_point(point2, used_roads)

        if equals(start_road, end_road):
            start_road = find_and_move_road(point1, used_roads)
            start_road = find_and_move_road(point2, used_roads)
            road_parts = list(split(start_road, point1).geoms)
            for part in road_parts.copy():
                if point2.dwithin(part, 1e-8):
                    more_parts = list(split(part, point2).geoms)
                    road_parts.remove(part)
                    road_parts += more_parts
            used_roads += road_parts

        else:
            start_road = find_and_move_road(point1, used_roads)
            end_road = find_and_move_road(point2, used_roads)

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
        self.shortest_path_output = ShortestPathOutput(
            points=points, end_distance=end_distance)
        print(f"TIME FOR FIND_SHORTEST_PATH 2: {end_time2 - start_time2}")
        return self.shortest_path_output

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
                     shared_coords(road, other_road)):
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
                        if point_ends_road(crossroad, self.roads):
                            continue
                        nearby_points = point_near_point(
                            crossroad, self.points)
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

    def add_calculation_point(self, point: Point):
        """Adds a point that distance is measured from, or to. 
        After adding two points, the next point will remove the previous two.
        """
        if len(self.calculation_points) == 2:
            self.calculation_points.clear()

        if len(self.calculation_points) == 1 and point.dwithin(self.calculation_points[0][0], MIN_DISTANCE_BETWEEN_C_POINTS):
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

                    """
                    print(
                        f"CALCULATION POINT 1: {self.calculation_points[0][0]}")
                    print(
                        f"CALCULATION POINT 2: {self.calculation_points[1][0]}")

                    print(
                        f"Distance between the two points: {abs(self.calculation_points[1][1] - self.calculation_points[0][1])}")
                    print(
                        f"Connected: {self.connected(self.calculation_points[0][0], self.calculation_points[1][0])}")
                    """
                    self.find_shortest_path(
                        self.calculation_points[0][0], self.calculation_points[1][0])
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
            if invalid_point_placement(point, self.points, self.roads):
                # if point is near another point or road, new road is cancelled
                self.add_point_output = AddPointOutput(
                    error="Point is too close to another point or road!")
                self.clear_temp()
                return self.add_point_output
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
                self.add_point_output = AddPointOutput(
                    error="Start and end point cannot be the same point!")
                return self.add_point_output

        self.current_road_points.append(point)
        if len(self.current_road_points) == 2:
            self._add_road(self.current_road_points)

        self.add_point_output = AddPointOutput(
            point=point, point_overlaps=point_overlaps)
        return self.add_point_output

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
                self.clear_temp()
                self._add_road_output = AddRoadOutput(
                    error=f"Road is equal to another road!")
                return self._add_road_output

        for point in self.points:
            if point.dwithin(new_road, MIN_DISTANCE_BETWEEN_POINT_AND_ROAD) and \
                    not shared_coords(point, new_road):
                self.clear_temp()
                self._add_road_output = AddRoadOutput(
                    error=f"The road is too close to an existing point!")
                return self._add_road_output

        self.temp_roads.append(new_road)
        if check_crossroads:
            crossroads = self.create_crossroads()
            if crossroads is False:
                self.clear_temp()
                self._add_road_output = AddRoadOutput(
                    error=f"Can't create road because crossroads cannot be made here!")
                return self._add_road_output

        for point in self.temp_points:
            self.points.append(point)
        for point, hitbox in self.temp_hitboxes.items():
            self.hitboxes[point] = hitbox
        for road in self.temp_roads:
            self.roads.append(road)
        self.clear_temp()
        self._add_road_output = AddRoadOutput(road=road, all_roads=self.roads)
        return self._add_road_output
