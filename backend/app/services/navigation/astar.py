import json
import os
import math
import heapq
from typing import Dict, List, Any, Tuple, Optional, Set

def get_layout_data() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    layout_path = os.path.join(base_dir, 'data', 'mall_layout.json')
    with open(layout_path, 'r', encoding='utf-8') as f:
        return json.load(f)

class Node:
    def __init__(self, floor: str, x: float, y: float, name: str = None, is_store: bool = False):
        self.floor = str(floor)
        self.x = float(x)
        self.y = float(y)
        self.name = name
        self.is_store = is_store
        self.id = f"f{self.floor}_x{int(self.x)}_y{int(self.y)}"

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)
        
    def __repr__(self):
        return f"Node({self.id}, name={self.name})"

def do_lines_intersect(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    # Returns true if line segments p1p2 and p3p4 intersect
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def rect_edges(rect: Dict[str, float]) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
    return [
        ((x, y), (x + w, y)),
        ((x + w, y), (x + w, y + h)),
        ((x + w, y + h), (x, y + h)),
        ((x, y + h), (x, y))
    ]

def line_intersects_rect(p1: Tuple[float, float], p2: Tuple[float, float], rect: Dict[str, float]) -> bool:
    # Check if the line segment intersects any edge of the rectangle
    edges = rect_edges(rect)
    for edge in edges:
        if do_lines_intersect(p1, p2, edge[0], edge[1]):
            return True
            
    # Also check if points are completely inside the rectangle
    def is_inside(p):
        return rect['x'] < p[0] < rect['x'] + rect['width'] and rect['y'] < p[1] < rect['y'] + rect['height']
    
    if is_inside(p1) or is_inside(p2):
        return True
        
    return False

def get_closest_point_on_rect(px: float, py: float, rect: Dict[str, float]) -> Tuple[float, float]:
    x = max(rect['x'], min(px, rect['x'] + rect['width']))
    y = max(rect['y'], min(py, rect['y'] + rect['height']))
    return x, y

class NavigationGraph:
    def __init__(self, layout_data: Dict[str, Any]):
        self.layout = layout_data
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[Tuple[str, float]]] = {}
        self.store_nodes: Dict[str, Node] = {} # lowercased store/landmark name to node
        self.build_graph()

    def add_node(self, node: Node) -> Node:
        if node.id not in self.nodes:
            self.nodes[node.id] = node
            self.edges[node.id] = []
        # Update name if new node has one
        if node.name and not self.nodes[node.id].name:
            self.nodes[node.id].name = node.name
        if node.is_store:
            self.nodes[node.id].is_store = True
        return self.nodes[node.id]

    def add_edge(self, n1: Node, n2: Node, cost: float):
        if (n2.id, cost) not in self.edges[n1.id]:
            self.edges[n1.id].append((n2.id, cost))
        if (n1.id, cost) not in self.edges[n2.id]:
            self.edges[n2.id].append((n1.id, cost))

    def get_corridor_centerline(self, corridor: Dict[str, Any]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        # Usually horizontal or vertical. Let's assume horizontal if width > height
        if corridor['width'] > corridor['height']:
            cy = corridor['y'] + corridor['height'] / 2.0
            return ((corridor['x'], cy), (corridor['x'] + corridor['width'], cy))
        else:
            cx = corridor['x'] + corridor['width'] / 2.0
            return ((cx, corridor['y']), (cx, corridor['y'] + corridor['height']))

    def build_graph(self):
        floors = self.layout.get('FLOOR_LAYOUTS', {})
        
        # 1. Add Corridor Nodes and Edges
        corridor_nodes_by_floor = {}
        for floor_id, floor_data in floors.items():
            corridor_nodes_by_floor[floor_id] = []
            corridors = floor_data.get('corridors', [])
            
            # Extract endpoints and intersections of centerlines
            centerlines = [self.get_corridor_centerline(c) for c in corridors]
            
            # Nodes for endpoints
            for c_idx, line in enumerate(centerlines):
                n1 = self.add_node(Node(floor_id, line[0][0], line[0][1]))
                n2 = self.add_node(Node(floor_id, line[1][0], line[1][1]))
                self.add_edge(n1, n2, math.hypot(line[1][0] - line[0][0], line[1][1] - line[0][1]))
                corridor_nodes_by_floor[floor_id].extend([n1, n2])
                
            # Nodes for intersections and touching corridors
            for i in range(len(centerlines)):
                for j in range(i + 1, len(centerlines)):
                    line1 = centerlines[i]
                    line2 = centerlines[j]
                    rect1 = corridors[i]
                    rect2 = corridors[j]
                    
                    def rects_touch(r1, r2):
                        return (r1['x'] <= r2['x'] + r2['width'] and r2['x'] <= r1['x'] + r1['width'] and
                                r1['y'] <= r2['y'] + r2['height'] and r2['y'] <= r1['y'] + r1['height'])

                    if do_lines_intersect(line1[0], line1[1], line2[0], line2[1]) or rects_touch(rect1, rect2):
                        is_horiz1 = line1[0][1] == line1[1][1]
                        is_horiz2 = line2[0][1] == line2[1][1]
                        if is_horiz1 != is_horiz2:
                            ix = line2[0][0] if is_horiz1 else line1[0][0]
                            iy = line1[0][1] if is_horiz1 else line2[0][1]
                            
                            # Clamp intersection to segments
                            ix1 = max(min(line1[0][0], line1[1][0]), min(ix, max(line1[0][0], line1[1][0])))
                            iy1 = max(min(line1[0][1], line1[1][1]), min(iy, max(line1[0][1], line1[1][1])))
                            
                            ix2 = max(min(line2[0][0], line2[1][0]), min(ix, max(line2[0][0], line2[1][0])))
                            iy2 = max(min(line2[0][1], line2[1][1]), min(iy, max(line2[0][1], line2[1][1])))
                            
                            p1_node = self.add_node(Node(floor_id, ix1, iy1))
                            p2_node = self.add_node(Node(floor_id, ix2, iy2))
                            corridor_nodes_by_floor[floor_id].extend([p1_node, p2_node])
                            
                            # Connect the clamped points to each other
                            dist_p1_p2 = math.hypot(ix1 - ix2, iy1 - iy2)
                            if dist_p1_p2 <= 100: # They touch, so distance is small
                                self.add_edge(p1_node, p2_node, dist_p1_p2)
                            
                            # Connect to endpoints of both lines
                            for p in [line1[0], line1[1]]:
                                p_end = self.add_node(Node(floor_id, p[0], p[1]))
                                self.add_edge(p1_node, p_end, math.hypot(ix1 - p[0], iy1 - p[1]))
                            for p in [line2[0], line2[1]]:
                                p_end = self.add_node(Node(floor_id, p[0], p[1]))
                                self.add_edge(p2_node, p_end, math.hypot(ix2 - p[0], iy2 - p[1]))

        # 2. Add Stores, Landmarks, and Starting Points
        # Also project them to the nearest corridor centerline and check walkability
        for floor_id, floor_data in floors.items():
            stores = floor_data.get('stores', [])
            landmarks = floor_data.get('landmarks', [])
            corridors = floor_data.get('corridors', [])
            
            entities = []
            for s in stores:
                entities.append((s['name'], s, True))
            for l in landmarks:
                entities.append((l['name'], l, False))
                
            for sp in self.layout.get('STARTING_POINTS', []):
                if str(sp['floor']) == floor_id:
                    entities.append((sp['name'], sp, False))
            
            for name, entity_data, is_store_rect in entities:
                ex, ey = entity_data['x'], entity_data['y']
                ew = entity_data.get('width', 0)
                eh = entity_data.get('height', 0)
                
                # Determine Access Point
                access_node = None
                if is_store_rect and ew > 0 and eh > 0:
                    # Find closest corridor to the center
                    cx, cy = ex + ew/2.0, ey + eh/2.0
                    
                    best_dist = float('inf')
                    best_proj = None
                    best_access = None
                    
                    for corridor in corridors:
                        cline = self.get_corridor_centerline(corridor)
                        # Project (cx, cy) onto cline
                        is_horiz = cline[0][1] == cline[1][1]
                        if is_horiz:
                            px = max(cline[0][0], min(cx, cline[1][0]))
                            py = cline[0][1]
                        else:
                            px = cline[0][0]
                            py = max(cline[0][1], min(cy, cline[1][1]))
                            
                        # The access point on the store boundary
                        ax, ay = get_closest_point_on_rect(px, py, entity_data)
                        
                        dist = math.hypot(px - ax, py - ay)
                        
                        # Check collision against ALL stores
                        collision = False
                        for other_store in stores:
                            if other_store['name'] == name:
                                continue
                            if line_intersects_rect((ax, ay), (px, py), other_store):
                                collision = True
                                break
                                
                        if not collision and dist < best_dist:
                            best_dist = dist
                            best_proj = (px, py)
                            best_access = (ax, ay)
                            
                    if best_access and best_proj:
                        access_node = self.add_node(Node(floor_id, best_access[0], best_access[1], name=name, is_store=True))
                        proj_node = self.add_node(Node(floor_id, best_proj[0], best_proj[1]))
                        self.add_edge(access_node, proj_node, best_dist)
                        corridor_nodes_by_floor[floor_id].append(proj_node)
                        # Connect proj_node to endpoints of the corridor it's on
                        for corridor in corridors:
                            cline = self.get_corridor_centerline(corridor)
                            if (cline[0][1] == cline[1][1] == best_proj[1]) or (cline[0][0] == cline[1][0] == best_proj[0]):
                                # Is on this centerline
                                n1 = self.add_node(Node(floor_id, cline[0][0], cline[0][1]))
                                n2 = self.add_node(Node(floor_id, cline[1][0], cline[1][1]))
                                self.add_edge(proj_node, n1, math.hypot(best_proj[0] - cline[0][0], best_proj[1] - cline[0][1]))
                                self.add_edge(proj_node, n2, math.hypot(best_proj[0] - cline[1][0], best_proj[1] - cline[1][1]))
                else:
                    # Point entity (landmark or start point)
                    access_node = self.add_node(Node(floor_id, ex, ey, name=name))
                    
                    # Project to nearest corridor
                    best_dist = float('inf')
                    best_proj = None
                    for corridor in corridors:
                        cline = self.get_corridor_centerline(corridor)
                        is_horiz = cline[0][1] == cline[1][1]
                        if is_horiz:
                            px = max(cline[0][0], min(ex, cline[1][0]))
                            py = cline[0][1]
                        else:
                            px = cline[0][0]
                            py = max(cline[0][1], min(ey, cline[1][1]))
                        
                        collision = False
                        for store in stores:
                            if line_intersects_rect((ex, ey), (px, py), store):
                                collision = True
                                break
                                
                        dist = math.hypot(px - ex, py - ey)
                        if not collision and dist < best_dist:
                            best_dist = dist
                            best_proj = (px, py)
                            
                    if best_proj:
                        proj_node = self.add_node(Node(floor_id, best_proj[0], best_proj[1]))
                        self.add_edge(access_node, proj_node, best_dist)
                        corridor_nodes_by_floor[floor_id].append(proj_node)
                        for corridor in corridors:
                            cline = self.get_corridor_centerline(corridor)
                            if (cline[0][1] == cline[1][1] == best_proj[1]) or (cline[0][0] == cline[1][0] == best_proj[0]):
                                n1 = self.add_node(Node(floor_id, cline[0][0], cline[0][1]))
                                n2 = self.add_node(Node(floor_id, cline[1][0], cline[1][1]))
                                self.add_edge(proj_node, n1, math.hypot(best_proj[0] - cline[0][0], best_proj[1] - cline[0][1]))
                                self.add_edge(proj_node, n2, math.hypot(best_proj[0] - cline[1][0], best_proj[1] - cline[1][1]))
                
                if access_node:
                    self.store_nodes[name.lower().strip()] = access_node

        # 3. Add Floor Connections (Escalators/Elevators)
        connections = self.layout.get('FLOOR_CONNECTIONS', {})
        for floor_id, conn_data in connections.items():
            pt = conn_data.get('connectionPoint')
            if not pt: continue
            
            node_current = self.add_node(Node(floor_id, pt['x'], pt['y'], name=f"Escalator F{floor_id}"))
            self.store_nodes[f"escalator_f{floor_id}"] = node_current
            
            # Connect the escalator to the corridor
            best_dist = float('inf')
            best_proj = None
            for corridor in floors.get(floor_id, {}).get('corridors', []):
                cline = self.get_corridor_centerline(corridor)
                is_horiz = cline[0][1] == cline[1][1]
                if is_horiz:
                    px = max(cline[0][0], min(pt['x'], cline[1][0]))
                    py = cline[0][1]
                else:
                    px = cline[0][0]
                    py = max(cline[0][1], min(pt['y'], cline[1][1]))
                    
                dist = math.hypot(px - pt['x'], py - pt['y'])
                if dist < best_dist:
                    best_dist = dist
                    best_proj = (px, py)
                    
            if best_proj:
                proj_node = self.add_node(Node(floor_id, best_proj[0], best_proj[1]))
                self.add_edge(node_current, proj_node, best_dist)
            
            # Cross-floor edges
            if conn_data.get('up'):
                up_floor = str(conn_data['up'])
                if up_floor in connections:
                    up_pt = connections[up_floor]['connectionPoint']
                    node_up = self.add_node(Node(up_floor, up_pt['x'], up_pt['y'], name=f"Escalator F{up_floor}"))
                    self.add_edge(node_current, node_up, 50.0)
                    
        # 4. Connect all nodes that lie on the same corridor centerline
        for floor_id, floor_data in floors.items():
            corridors = floor_data.get('corridors', [])
            for corridor in corridors:
                cline = self.get_corridor_centerline(corridor)
                is_horiz = cline[0][1] == cline[1][1]
                
                # Find all nodes on this centerline
                nodes_on_line = []
                for node in self.nodes.values():
                    if node.floor == floor_id:
                        if is_horiz and abs(node.y - cline[0][1]) < 1e-6 and cline[0][0] <= node.x <= cline[1][0]:
                            nodes_on_line.append(node)
                        elif not is_horiz and abs(node.x - cline[0][0]) < 1e-6 and cline[0][1] <= node.y <= cline[1][1]:
                            nodes_on_line.append(node)
                            
                # Sort nodes by coordinate
                if is_horiz:
                    nodes_on_line.sort(key=lambda n: n.x)
                else:
                    nodes_on_line.sort(key=lambda n: n.y)
                    
                # Connect adjacent nodes sequentially
                for i in range(len(nodes_on_line) - 1):
                    n1 = nodes_on_line[i]
                    n2 = nodes_on_line[i+1]
                    dist = math.hypot(n1.x - n2.x, n1.y - n2.y)
                    self.add_edge(n1, n2, dist)

    def find_node_by_name(self, name: str) -> Optional[Node]:
        return self.store_nodes.get(name.lower().strip())

def floor_index(floor_str: str) -> int:
    if floor_str == 'B1': return -1
    try: return int(floor_str)
    except: return 0

def heuristic(n1: Node, n2: Node) -> float:
    # 3D Euclidean distance. 1 floor transition = exactly 50 units (as defined in cost model).
    dx = n1.x - n2.x
    dy = n1.y - n2.y
    dz = (floor_index(n1.floor) - floor_index(n2.floor)) * 50.0
    return math.sqrt(dx*dx + dy*dy + dz*dz)

def calculate_astar_route(graph: NavigationGraph, start_name: str, goal_name: str) -> Optional[Dict[str, Any]]:
    start_node = graph.find_node_by_name(start_name)
    goal_node = graph.find_node_by_name(goal_name)
    
    if not start_node or not goal_node:
        return None
        
    if start_node.id == goal_node.id:
        return {
            "from": {"name": start_name, "floor": start_node.floor},
            "to": {"name": goal_name, "floor": goal_node.floor},
            "floors": [{"floor": start_node.floor, "path": [{"x": start_node.x, "y": start_node.y}]}],
            "totalDistance": 0,
            "estimatedTime": 0,
            "steps": [f"You are already at {goal_name}"],
            "nodes_explored": 0
        }

    open_set = []
    heapq.heappush(open_set, (0.0, start_node.id))
    
    came_from = {}
    g_score = {start_node.id: 0.0}
    nodes_explored = 0
    
    while open_set:
        nodes_explored += 1
        current_f, current_id = heapq.heappop(open_set)
        
        if current_id == goal_node.id:
            return reconstruct_path(graph, came_from, current_id, start_name, goal_name, nodes_explored, g_score[current_id])
            
        for neighbor_id, cost in graph.edges.get(current_id, []):
            tentative_g = g_score[current_id] + cost
            if neighbor_id not in g_score or tentative_g < g_score[neighbor_id]:
                came_from[neighbor_id] = current_id
                g_score[neighbor_id] = tentative_g
                f_score = tentative_g + heuristic(graph.nodes[neighbor_id], goal_node)
                heapq.heappush(open_set, (f_score, neighbor_id))
                
    return None # No route found

def reconstruct_path(graph: NavigationGraph, came_from: Dict[str, str], current_id: str, start_name: str, goal_name: str, nodes_explored: int, total_cost: float) -> Dict[str, Any]:
    path_ids = [current_id]
    while current_id in came_from:
        current_id = came_from[current_id]
        path_ids.append(current_id)
        
    path_ids.reverse()
    
    floors = []
    current_floor_path = []
    current_floor = None
    
    for nid in path_ids:
        node = graph.nodes[nid]
        if current_floor != node.floor:
            if current_floor is not None and current_floor_path:
                floors.append({
                    "floor": current_floor,
                    "path": current_floor_path
                })
            current_floor = node.floor
            current_floor_path = [{"x": node.x, "y": node.y}]
        else:
            current_floor_path.append({"x": node.x, "y": node.y})
            
    if current_floor is not None and current_floor_path:
        floors.append({
            "floor": current_floor,
            "path": current_floor_path
        })
        
    # Generate steps
    steps = [f"Start from {start_name}"]
    for i in range(len(floors) - 1):
        steps.append(f"Take escalator to Floor {floors[i+1]['floor']}")
    steps.append(f"Walk to {goal_name}")
    
    # Simplify path (remove colinear intermediate points)
    for floor in floors:
        path = floor['path']
        if len(path) > 2:
            simplified = [path[0]]
            for i in range(1, len(path)-1):
                p_prev = simplified[-1]
                p_curr = path[i]
                p_next = path[i+1]
                
                # Cross product to check colinearity
                cross = (p_curr['y'] - p_prev['y']) * (p_next['x'] - p_curr['x']) - (p_curr['x'] - p_prev['x']) * (p_next['y'] - p_curr['y'])
                if abs(cross) > 1e-6:
                    simplified.append(p_curr)
            simplified.append(path[-1])
            floor['path'] = simplified
    
    return {
        "from": {"name": start_name, "floor": graph.nodes[path_ids[0]].floor},
        "to": {"name": goal_name, "floor": graph.nodes[path_ids[-1]].floor},
        "floors": floors,
        "totalDistance": int(total_cost),  # layout units
        "estimatedTime": math.ceil(total_cost / 50.0), # Assuming ~50 units per minute
        "steps": steps,
        "nodes_explored": nodes_explored
    }

if __name__ == '__main__':
    import time
    layout = get_layout_data()
    t0 = time.time()
    graph = NavigationGraph(layout)
    t1 = time.time()
    route = calculate_astar_route(graph, "Main Entrance", "PVR Cinemas")
    t2 = time.time()
    print(f"Graph build time: {(t1-t0)*1000:.2f}ms")
    print(f"A* search time: {(t2-t1)*1000:.2f}ms")
    print(json.dumps(route, indent=2))
