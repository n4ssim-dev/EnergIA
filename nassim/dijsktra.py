graph = {
   "A": {"B": 3, "C": 3},
   "B": {"A": 3, "D": 3.5, "E": 2.8},
   "C": {"A": 3, "E": 2.8, "F": 3.5},
   "D": {"B": 3.5, "E": 3.1, "G": 10},
   "E": {"B": 2.8, "C": 2.8, "D": 3.1, "G": 7},
   "F": {"G": 2.5, "C": 3.5},
   "G": {"F": 2.5, "E": 7, "D": 10},
}

class Graph:
    def __init__(self, graph : dict = {}):
        self.graph = graph

    def add_edge(self, node1, node2, weight):
        if node1 not in self.graph:
            self.graph[node1] = {}
        self.graph[node1][node2] = weight

    def shortest_distance(self, source: str):
        distances = {node: float("inf") for node in self.graph}
        distances[source] = 0
        visited = set()

        while len(visited) < len(self.graph):
            current = None
            current_dist = float("inf")
            for node in self.graph:
                if node not in visited and distances[node] < current_dist:
                    current = node
                    current_dist = distances[node]

            if current is None:
                break
            visited.add(current)

            for neighbor, weight in self.graph[current].items():
                new_dist = distances[current] + weight
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist

        return distances

G = Graph(graph=graph)

distances = G.shortest_distance("B")
to_f = distances["F"]
print(f"The shortest distance from B to F is {to_f}")