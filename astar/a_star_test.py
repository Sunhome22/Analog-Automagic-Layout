

import pulp

from circuit.circuit_components import CircuitCell, Pin

import heapq


class PriorityQueue:
    def __init__(self):
        self.elements = []

    def is_empty(self):
        return len(self.elements) == 0

    def push(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def pop(self):
        return heapq.heappop(self.elements)[1]


def heuristic(a, b):
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_valid_block(x, y, grid, path_width, start_area, end_area, path_tracker, current_direction):
    """Check if a block of size path_width is valid at position (x, y)."""
    grid_height = len(grid)
    grid_width = len(grid[0])

    for dx in range(path_width):
        for dy in range(path_width):
            nx, ny = x + dx, y + dy

            # Check bounds
            if nx >= grid_width or ny >= grid_height:
                return False

            # Special obstacle check
            if grid[ny][nx] == 2:  # Special obstacle
                if (nx, ny) not in start_area and (nx, ny) not in end_area:
                    return False

            # Regular obstacle check
            if grid[ny][nx] == 1:  # Regular obstacle
                return False

            # Crossing rule check
            if (nx, ny) in path_tracker:
                existing_direction = path_tracker[(nx, ny)]
                if existing_direction == "horizontal" and current_direction == "horizontal":
                    return False
                if existing_direction == "vertical" and current_direction == "vertical":
                    return False

    return True


def get_neighbors(node, grid, path_width, start_area, end_area, path_tracker):
    """Generate neighbors while respecting all rules."""
    x, y, direction = node
    neighbors = []

    moves = {
        "up": (0, -1, "vertical"),
        "down": (0, 1, "vertical"),
        "left": (-1, 0, "horizontal"),
        "right": (1, 0, "horizontal"),
    }

    for move, (dx, dy, new_direction) in moves.items():
        nx, ny = x + dx, y + dy
        if is_valid_block(nx, ny, grid, path_width, start_area, end_area, path_tracker, new_direction):
            neighbors.append((nx, ny, new_direction))

    return neighbors


def a_star(start_area, end_area, grid, path_width):
    """A* algorithm with all rules implemented."""
    open_set = PriorityQueue()

    # Initialize the open set with all nodes in the starting area
    for start in start_area:
        open_set.push((start[0], start[1], None), 0)  # (x, y, direction)

    came_from = {}
    g_score = {start: 0 for start in start_area}
    f_score = {start: heuristic(start, end_area[0]) for start in start_area}

    # Track paths with their direction (horizontal/vertical)
    path_tracker = {}

    while not open_set.is_empty():
        current = open_set.pop()
        x, y, direction = current

        # Add to path tracker
        if direction:
            path_tracker[(x, y)] = direction

        # Check if current node is in the ending area
        if (x, y) in end_area:
            return reconstruct_path(came_from, current)

        for neighbor in get_neighbors(current, grid, path_width, start_area, end_area, path_tracker):
            nx, ny, new_direction = neighbor
            tentative_g_score = g_score[(x, y)] + 1  # Uniform cost

            if (nx, ny) not in g_score or tentative_g_score < g_score[(nx, ny)]:
                came_from[(nx, ny)] = (x, y, direction)
                g_score[(nx, ny)] = tentative_g_score
                f_score[(nx, ny)] = g_score[(nx, ny)] + heuristic((nx, ny), end_area[0])
                open_set.push((nx, ny, new_direction), f_score[(nx, ny)])

    return None  # No path found


def reconstruct_path(came_from, current):
    """Reconstruct the path."""
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[(current[0], current[1])]
    path.reverse()
    return path









def initiate_astar(grid, connections, local_connections, objects, area, area_coordinates):
    path = []
    local = True
    glo = False
    path_names = []
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
                for p in area_coordinates:

                    if p == str(obj.number_id) + start_area:

                        start = area_coordinates[str(obj.number_id) + start_area]
                        start_found = True
                        break
            if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == id_end:
                for p in area_coordinates:
                    if p == str(obj.number_id) + end_area:
                        end = area_coordinates[str(obj.number_id) + start_area]
                        end_found = True
                        break
            if start_found and end_found:
                break
        print("--------------------")
        print(id_start, id_end)
        string = str(id_start) + str(start_area) + "-" + str(id_end) + str(end_area)
        path_names.append(string)
        print(start_area, end_area)

        print("--------------------")
        path.append(a_star(start, end, grid, 30))
        print(path)
        print("Completed Path")



    return path, path_names
