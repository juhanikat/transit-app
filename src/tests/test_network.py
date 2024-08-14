import unittest

from shapely import LineString, Point

from network import network


class TestNetwork(unittest.TestCase):

    def setUp(self) -> None:
        self.network = network.Network()

    def test_creating_roads(self):
        point1 = Point(0, 0)
        point2 = Point(1, 1)
        line = LineString([point1, point2])
        road = self.network.add_road(line)
        self.assertEqual(road, LineString([point1, point2]))

        point1 = Point(0, 10)
        point2 = Point(10, -1)
        point3 = Point(0, 5)
        line = LineString([point1, point2, point3])
        road = self.network.add_road(line)
        self.assertEqual(road, LineString([point1, point2, point3]))

    def test_calculating_shortest_path_1(self):
        point1 = Point(0, 0)
        point2 = Point(1, 1)
        line = LineString([point1, point2])
        road = self.network.add_road(line)

        c_point1 = Point(0, 0)
        c_point2 = Point(1, 1)
        points, distance = self.network.find_shortest_path(c_point1, c_point2)
        self.assertEqual(points, [point1.coords[0], point2.coords[0]])
        self.assertAlmostEqual(distance, 1.414, 3)

    def test_calculating_shortest_path_2(self):
        point1 = Point(0, 0)
        point2 = Point(1, 1)
        line = LineString([point1, point2])
        self.network.add_road(line)

        point3 = Point(1, 1)
        point4 = Point(4, 4)
        line = LineString([point3, point4])
        self.network.add_road(line)

        c_point1 = Point(0, 0)
        c_point2 = Point(3, 3)
        points, distance = self.network.find_shortest_path(c_point1, c_point2)
        self.assertEqual(
            points, [point1.coords[0], point2.coords[0], c_point2.coords[0]])
        self.assertAlmostEqual(distance, 1.414*3, 2)
