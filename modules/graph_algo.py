import heapq

class TobbacoGraph:
  def __init__(self):
    self.titik = {}
    
  def add_edge(self, from_node, to_node, weight):
    if from_node not in self.titik:
      self.titik[from_node] = {}
    if to_node not in self.titik:
      self.titik[to_node] = {}
      
    self.titik[from_node][to_node] = weight
    self.titik[to_node][from_node] = weight  
    
  def dijkstra(self, start_node, end_node):
    queue = [(0, start_node)]
    distances = {node: float('inf') for node in self.titik}
    distances[start_node] = 0
    previous_nodes = {node: None for node in self.titik}
    visited = set()
    
    while queue:
      current_distance, current_node = heapq.heappop(queue)
      
      if current_node == end_node:
        break
      
      if current_node in visited:
        continue
      visited.add(current_node)
      
      for neighbor, weight in self.titik.get(current_node, {}).items():
        distance = current_distance + weight
        
        if distance < distances[neighbor]:
          distances[neighbor] = distance
          previous_nodes[neighbor] = current_node
          heapq.heappush(queue, (distance, neighbor))
          
    if distances[current_node] == float('inf'):
        return [], 0
      
    return self.buat_path(previous_nodes, start_node, end_node), distances[end_node]
  
  def buat_path(self, previous_nodes, start_node, end_node):
    path = []
    current_node = end_node
    
    while current_node is not None:
      path.append(current_node)
      if current_node == start_node:
        break
      current_node = previous_nodes[current_node]
    path.reverse()
    return path