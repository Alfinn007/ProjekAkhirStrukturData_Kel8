class MinPriorityQueue:
    def __init__(self):
        self.heap = []

    def push(self, item):
        self.heap.append(item)
        self._bubble_up(len(self.heap) - 1)

    def pop(self):
        if not self.heap:
            return None
        if len(self.heap) == 1:
            return self.heap.pop()
        
        root = self.heap[0]
        self.heap[0] = self.heap.pop()
        self._bubble_down(0)
        return root

    def is_empty(self):
        return len(self.heap) == 0

    def _bubble_up(self, index):
        parent_index = (index - 1) // 2
        if index > 0 and self.heap[index][0] < self.heap[parent_index][0]:
            self.heap[index], self.heap[parent_index] = self.heap[parent_index], self.heap[index]
            self._bubble_up(parent_index)

    def _bubble_down(self, index):
        smallest = index
        left_child = 2 * index + 1
        right_child = 2 * index + 2
        
        if left_child < len(self.heap) and self.heap[left_child][0] < self.heap[smallest][0]:
            smallest = left_child
            
        if right_child < len(self.heap) and self.heap[right_child][0] < self.heap[smallest][0]:
            smallest = right_child
            
        if smallest != index:
            self.heap[index], self.heap[smallest] = self.heap[smallest], self.heap[index]
            self._bubble_down(smallest)

class TobaccoGraph:
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
        if start_node not in self.titik or end_node not in self.titik:
             return [], 0

        pq = MinPriorityQueue()
        pq.push((0, start_node))
        
        distances = {node: float('inf') for node in self.titik}
        distances[start_node] = 0
        
        previous_nodes = {node: None for node in self.titik}
        visited = set()
        
        while not pq.is_empty():
            current_distance, current_node = pq.pop()
            
            if current_node == end_node:
                break
            
            if current_node in visited:
                continue
            visited.add(current_node)
            
            neighbor_map = self.titik.get(current_node)
            if neighbor_map:
                for neighbor, weight in neighbor_map.items():
                    distance = current_distance + weight
                    
                    if distance < distances[neighbor]:
                        distances[neighbor] = distance
                        previous_nodes[neighbor] = current_node
                        pq.push((distance, neighbor))
                
        if distances[end_node] == float('inf'):
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
        
        reversed_path = []
        for i in range(len(path) - 1, -1, -1):
            reversed_path.append(path[i])
            
        return reversed_path