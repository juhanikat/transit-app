HITBOX_SIZE = 0.3
NORMAL_P_COLOR = "b"
SELECTED_P_COLOR = "r"
INTERSECTION_P_COLOR = "g"
CALCULATION_P_COLOR = "c"

# how far away can you click from a road to create a calculation point there
CALCULATION_P_DISTANCE = 0.2

# how far away a point needs to be placed from an existing geometry
MIN_DISTANCE_WHEN_PLACING_POINT = 0.5

# how far away any road needs to be from any point (that is not a coordinate of that road)
MIN_DISTANCE_BETWEEN_POINT_AND_ROAD = 0.2

DEFAULT_XLIM = (0, 10)
DEFAULT_YLIM = (0, 10)
# how much to zoom in/out
ZOOM_AMOUNT = 1

HOW_TO_USE_TEXT = """
Start drawing a road by clicking anywhere on the map, then click somewhere else to finish the road. Note that you can not start or end a road right next to an existing one. \n
You can connect roads by clicking the blue points at either end of any road. \n
Press middle mouse button (or C) to place a calculation point. Place another calculation point somewhere else to highlight the shortest path between them. \n
You can move the map with arrow keys, and zoom in/out using the scroll wheel. \n
"""
