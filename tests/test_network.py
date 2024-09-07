import unittest

from shapely import LineString, Point

from src.transit_app.constants import (HITBOX_SIZE,
                                       MIN_DISTANCE_WHEN_PLACING_POINT)
from src.transit_app.network import Network


class TestNetwork(unittest.TestCase):

    def setUp(self) -> None:
        self.network = Network()

    def test_creating_roads(self):
        point1 = Point(0, 0)
        point2 = Point(1, 1)
        self.network.add_point(point1)
        self.network.add_point(point2)
        self.assertEqual(len(self.network.roads), 1)
        self.assertEqual(self.network.roads[0], LineString([point1, point2]))

        point1 = Point(0, 10)
        point2 = Point(10, -1)
        point3 = Point(0, 5)
        self.network.add_point(point1)
        self.network.add_point(point2)
        self.network.add_point(point2)
        self.network.add_point(point3)
        self.assertEqual(len(self.network.roads), 3)
        self.assertEqual(self.network.roads[1], LineString(
            [point1, point2]))
        self.assertEqual(self.network.roads[2], LineString(
            [point2, point3]))

    def test_point_adding_limits(self):
        point1 = Point(0, 0)
        point2 = Point(3, 0)
        self.network.add_point(point1)
        self.network.add_point(point2)
        self.assertEqual(len(self.network.roads), 1)
        self.assertEqual(len(self.network.points), 2)

        point3 = Point(0, 0)  # selects point1
        self.network.add_point(point3)
        self.assertEqual(len(self.network.points), 2)

        point4 = Point(0, HITBOX_SIZE)  # still selects point1
        self.network.add_point(point4)
        self.assertEqual(len(self.network.points), 2)

        # does not select point 1 and is far enough from any existing geometry
        point5 = Point(0, MIN_DISTANCE_WHEN_PLACING_POINT + 0.1)
        self.network.add_point(point5)
        # still 2 because point is temp_point at this point
        self.assertEqual(len(self.network.points), 2)

        point6 = Point(0, MIN_DISTANCE_WHEN_PLACING_POINT * 2 + 0.1)
        self.network.add_point(point6)
        # new road is added
        self.assertEqual(len(self.network.points), 4)

    def test_adding_points(self):
        point1 = Point(0, 0)
        point2 = Point(1, 1)
        self.network.add_point(point1)
        self.network.add_point(point2)
        self.assertEqual(len(self.network.roads), 1)
        self.assertEqual(len(self.network.points), 2)

        point3 = Point(1, 1)
        point4 = Point(4, 4)
        self.network.add_point(point3)
        self.network.add_point(point4)
        self.assertEqual(len(self.network.roads), 2)
        # point1 and point3 are the same!
        self.assertEqual(len(self.network.points), 3)

    def test_calculating_shortest_path_1(self):
        point1 = Point(0, 0)
        point2 = Point(1, 1)
        self.network.add_point(point1)
        self.network.add_point(point2)

        c_point1 = Point(0, 0)
        c_point2 = Point(1, 1)
        output = self.network.find_shortest_path(c_point1, c_point2)
        self.assertEqual(output.points, [point1.coords[0], point2.coords[0]])
        self.assertAlmostEqual(output.end_distance, 1.414, 3)

    def test_calculating_shortest_path_2(self):
        point1 = Point(0, 0)
        point2 = Point(1, 1)
        self.network.add_point(point1)
        self.network.add_point(point2)

        point3 = Point(1, 1)
        point4 = Point(4, 4)
        self.network.add_point(point3)
        self.network.add_point(point4)

        c_point1 = Point(0, 0)
        c_point2 = Point(3, 3)
        output = self.network.find_shortest_path(c_point1, c_point2)
        self.assertEqual(
            output.points, [point1.coords[0], point2.coords[0], c_point2.coords[0]])
        self.assertAlmostEqual(output.end_distance, 1.414*3, 2)

    def test_crossroads(self):
        point1 = Point(0, 1)
        point2 = Point(2, 1)
        point3 = Point(1, 0)
        point4 = Point(1, 2)
        self.network.add_point(point1)
        self.network.add_point(point2)
        self.assertEqual(len(self.network.roads), 1)
        self.network.add_point(point3)
        self.network.add_point(point4)
        # crossroad splits 2 roads into 4
        self.assertEqual(len(self.network.roads), 4)
        self.assertEqual(len(self.network.crossroads), 1)

    def test_invalid_crossroads(self):
        point1 = Point(5, 5)
        point2 = Point(7, 5)
        point3 = Point(5, 6)
        point4 = Point(5, 4)
        self.network.add_point(point1)
        self.network.add_point(point2)
        self.assertEqual(len(self.network.roads), 1)
        self.network.add_point(point3)
        self.network.add_point(point4)
        self.assertEqual(len(self.network.roads), 1)
        self.assertEqual(len(self.network.crossroads), 0)
