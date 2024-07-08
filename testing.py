import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseButton
from shapely.geometry import LineString, Point, Polygon
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

hb_size = 0.3


class MyPoint:
    """This should be subclassing Point but it doesn't work with Shapely? I guess\n
    use <p> attribute to access the actual point"""

    def __init__(self, x, y):
        self.p = Point(x, y)
        b = self.p.bounds
        self.hitbox = Polygon([(b[0] - hb_size, b[1] - hb_size), (b[0] - hb_size, b[3] + hb_size),
                              (b[2] + hb_size, b[3] + hb_size), (b[2] + hb_size, b[1] - hb_size)])


class Hmmm:

    def __init__(self) -> None:
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlim(0, 10)
        self.ax.set_ylim(0, 10)

        self.points = []
        self.roads = []
        self.current_road_points = []

    def onclick(self, event):
        print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              ('double' if event.dblclick else 'single', event.button,
               event.x, event.y, event.xdata, event.ydata))
        if event.button == MouseButton.RIGHT:
            new_road = LineString([(point.p.x, point.p.y)
                                  for point in self.current_road_points])
            x, y = new_road.xy
            self.ax.plot(x, y)
            self.current_road_points.clear()
        else:
            point = MyPoint(event.xdata, event.ydata)
            for other_point in self.points:
                hitbox = other_point.hitbox
                if point.p.within(hitbox):
                    print("on")

            self.current_road_points.append(point)
            self.points.append(point)
            self.ax.plot(*point.p.xy, "bo")
            self.ax.plot(*point.hitbox.exterior.xy)

    def main(self):
        event = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        # Show the plot
        plt.ion()
        plt.show(block=True)


if __name__ == "__main__":
    h = Hmmm()
    h.main()
