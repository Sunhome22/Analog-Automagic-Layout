import heapq

from circuit.circuit_components import CircuitCell, Pin


class Node:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = 0  # Distance from start node
        self.h = 0  # Heuristic distance to goal
        self.f = 0  # Total cost (f = g + h)

    def __lt__(self, other):
        return self.f < other.f


def heuristic(a, b):
    """Calculate Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar( start, end,grid):
    """
    Perform A* search on a grid.

    grid: 2D list where 0 represents open and 1 represents blocked
    start: Tuple (x, y) for the starting point
    end: Tuple (x, y) for the goal
    """
    open_list = []
    closed_list = set()
    start_node = Node(start)
    goal_node = Node(end)

    heapq.heappush(open_list, start_node)

    while open_list:
        current_node = heapq.heappop(open_list)
        closed_list.add(current_node.position)

        # If the goal is reached
        if current_node.position == goal_node.position:
            path = []
            while current_node:
                path.append(current_node.position)
                current_node = current_node.parent
            return path[::-1]

        # Generate neighbors
        neighbors = [
            (0, -1), (0, 1), (-1, 0), (1, 0)  # Up, Down, Left, Right
        ]
        for move in neighbors:
            neighbor_pos = (current_node.position[0] + move[0], current_node.position[1] + move[1])

            # Check boundaries and obstacles
            if (len(grid) > neighbor_pos[0] >= 0 == grid[neighbor_pos[0]][neighbor_pos[1]] and
                    0 <= neighbor_pos[1] < len(grid[0]) and
                    neighbor_pos not in closed_list):

                neighbor_node = Node(neighbor_pos, current_node)
                neighbor_node.g = current_node.g + 1
                neighbor_node.h = heuristic(neighbor_pos, goal_node.position)
                neighbor_node.f = neighbor_node.g + neighbor_node.h

                # Add to open list if not already there
                if all(neighbor_node.position != node.position or neighbor_node.f < node.f for node in open_list):
                    heapq.heappush(open_list, neighbor_node)

    return None



def initiate_astar(grid, connections, local_connections, objects, area, area_coordinates, perimeter):
    path = []
    local = True
    glo = False
    path_names = []
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    print(f"Grid size: {rows} rows, {cols} columns")

    if local and glo:
        spliced_list = {**connections, **local_connections}
    elif glo:
        spliced_list = connections

    else:
        spliced_list = local_connections

    for con in spliced_list.values():
        id_start = con.starting_comp
        id_end = con.end_comp
        start_area = con.starting_area[0]
        end_area = con.end_area[0]
        start_found = False
        end_found = False

        for obj in objects:

            if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == id_start:
                x_start = (obj.transform_matrix.c - perimeter[0] + 96 + 64 + 32)
                y_start = (obj.transform_matrix.f - perimeter[1] + 120)
                for port in obj.layout_ports:

                    if port.type == start_area:

                        start = (((port.area.x2+port.area.x1)//2 + x_start)//32,  ((port.area.y1+port.area.y2)//2+y_start) //40)

                        start_found = True
                        break
            if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == id_end:
                x_start = (obj.transform_matrix.c - perimeter[0] +( 96 + 64 + 32))
                y_start = (obj.transform_matrix.f - perimeter[1] + 120)
                for port in obj.layout_ports:
                    if port.type == end_area:
                        end = (((port.area.x2+port.area.x1)//2 + x_start)//32,  ((port.area.y1+port.area.y2)//2+y_start) //40)
                        end_found = True
                        break
            if start_found and end_found:
                break
        print("--------------------")
        print(id_start, id_end)
        string = str(id_start) + str(start_area) + "-" + str(id_end) + str(end_area)
        path_names.append(string)
        print(start_area, end_area)
        print(start, end)
        print("--------------------")
        path.append(astar(start, end, grid))
        print(path[-1])


    return path, path_names