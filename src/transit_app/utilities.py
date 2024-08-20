from shapely import LineString, Point, Polygon, box, equals, snap

from .constants import HITBOX_SIZE, MIN_DISTANCE_WHEN_PLACING_POINT


def create_hitbox(point: Point) -> Polygon:
    """Creates a hitbox around a point. Used when the user wants to click the point."""
    b = point.bounds
    new_b = (b[0] - HITBOX_SIZE, b[1] - HITBOX_SIZE,
             b[2] + HITBOX_SIZE, b[3] + HITBOX_SIZE)
    return box(*new_b)


def point_near_point(point: Point, all_points: list):
    """Returns a list of points that are near <point>, or False if none were found."""
    nearby_points = []
    for existing_point in all_points:
        if (point is not existing_point and
                point.dwithin(existing_point, MIN_DISTANCE_WHEN_PLACING_POINT)):
            nearby_points.append(existing_point)
    if len(nearby_points) == 0:
        return False
    return nearby_points


def find_road_that_has_point(point: Point, roads: list):
    """Returns the road that contains <point>, or False if none exist.
    Due to floating point issues the point is never actually on the road, 
    only very close to it, so dwithin() has to be used."""
    for road in roads:
        if point.dwithin(road, 1e-8):
            return road
    return False


def find_and_move_road(point: Point, roads: list):
    """Finds the road that contains <point>, and snaps said road to <point>. 
    Returns False if no such road exists.
    Due to floating point issues the point is never actually on the road, 
    only very close to it, so dwithin() has to be used."""
    for road in roads.copy():
        if point.dwithin(road, 1e-8):
            roads.remove(road)
            new_road = snap(road, point, 0.0001)
            roads.append(new_road)
            return new_road
    return False


def point_ends_road(point: Point, roads: list):
    """Returns True if <point> is the start or end point of any existing road, 
    or False otherwise."""
    road: LineString
    for road in roads:
        if equals(point, Point(road.coords[0])) or equals(point, Point(road.coords[1])):
            return True
    return False


def invalid_point_placement(point: Point, all_points: list, roads: list):
    """Returns True if added point is very near an existing point or an existing road, 
    or False otherwise."""
    for existing_point in all_points:
        if point.dwithin(existing_point, MIN_DISTANCE_WHEN_PLACING_POINT):
            return True
    for existing_road in roads:
        if point.dwithin(existing_road, MIN_DISTANCE_WHEN_PLACING_POINT):
            return True
    return False


def shared_coords(object1: LineString, object2: LineString):
    """Returns True if object1 and object2 share any coordinates, or False otherwise. 
    Objects can be Points or LineStrings.
    For roads, the coordinates are the ending points of the road, 
    not every coordinate that is covered by the LineString."""
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
