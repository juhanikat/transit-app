"""Copied from TIRA 2024 material."""

import heapq


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
    def __init__(self, nodes):
        self.nodes = nodes
        self.graph = {node: [] for node in nodes}

    def add_edge(self, node_a, node_b, weight):
        self.graph[node_a].append((node_b, weight))

    def find_distances(self, start_node):
        distances = {}
        for node in self.nodes:
            distances[node] = float("inf")
        distances[start_node] = 0

        queue = []
        heapq.heappush(queue, (0, start_node))

        visited = set()
        while queue:
            node_a = heapq.heappop(queue)[1]
            if node_a in visited:
                continue
            visited.add(node_a)

            for node_b, weight in self.graph[node_a]:
                new_distance = distances[node_a] + weight
                if new_distance < distances[node_b]:
                    distances[node_b] = new_distance
                    new_pair = (new_distance, node_b)
                    heapq.heappush(queue, new_pair)

        return distances
