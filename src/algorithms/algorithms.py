"""Copied from TIRA 2024 material."""

import heapq
import time


class DFS:
    def __init__(self, nodes):
        self.nodes = nodes
        self.graph = {node: [] for node in nodes}
        self.visited = None

    def add_edge(self, a, b):
        self.graph[a].append(b)
        self.graph[b].append(a)

    def visit(self, node):
        if node in self.visited:
            return
        self.visited.add(node)

        for next_node in self.graph[node]:
            self.visit(next_node)

    def search(self, start_node):
        self.visited = set()
        self.visit(start_node)
        return self.visited


class Dijkstra:
    """Does not take nodes when initialized, they have to be added with add_node()!"""

    def __init__(self) -> None:
        self.graph = {}
        self.distances = {}

    def add_node(self, node):
        if node not in self.graph.keys():
            self.graph[node] = []

    def add_edge(self, node_a, node_b, weight):
        if (node_b, weight) not in self.graph[node_a]:
            self.graph[node_a].append((node_b, weight))

    def find_distances(self, start_node, end_node):
        """Returns shortest path between start_node and end_node, and the distance from start_node to end_node."""
        start_time = time.time()
        self.distances = {}
        for node in self.graph.keys():
            self.distances[node] = float("inf")
        self.distances[start_node] = 0
        previous = {}
        previous[start_node] = None

        queue = []
        heapq.heappush(queue, (0, start_node))

        visited = set()
        while queue:
            node_a = heapq.heappop(queue)[1]
            if node_a in visited:
                continue
            visited.add(node_a)

            for node_b, weight in self.graph[node_a]:
                new_distance = self.distances[node_a] + weight
                if new_distance < self.distances[node_b]:
                    self.distances[node_b] = new_distance
                    previous[node_b] = node_a
                    new_pair = (new_distance, node_b)
                    heapq.heappush(queue, new_pair)

        if self.distances[end_node] == float("inf"):
            return None

        path = []
        node = end_node
        while node:
            path.append(node)
            node = previous[node]

        path.reverse()
        end_time = time.time()
        print(f"TIME FOR FIND_DISTANCES(): {end_time - start_time}")
        return (path, self.distances[end_node])
