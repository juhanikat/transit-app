from shapely import Point, Polygon, box

from .constants import HITBOX_SIZE


def create_hitbox(point: Point) -> Polygon:
    """Creates a hitbox around a point. Used when the user wants to click the point."""
    b = point.bounds
    new_b = (b[0] - HITBOX_SIZE, b[1] - HITBOX_SIZE,
             b[2] + HITBOX_SIZE, b[3] + HITBOX_SIZE)
    return box(*new_b)
