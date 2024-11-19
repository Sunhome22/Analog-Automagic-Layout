import pulp

from circuit.circuit_components import CircuitCell, Pin

import heapq


def astar_test(grid, start, goal):
    # Convert start and goal to tuples in case they are lists
    start = tuple(start)
    goal = tuple(goal)

    # Define costs for tiles
    tile_cost = {
        0: 1,  # Walkable, low cost
        1: 1 # Walkable, higher cost
    }

    # Heuristic function (Manhattan Distance)
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # Priority queue
    open_set = []
    heapq.heappush(open_set, (0, start))

    # Cost from start to each node
    g_cost = {start: 0}
    came_from = {}

    while open_set:
        # Get the node with the lowest f-cost
        _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        # Explore neighbors (Up, Down, Left, Right)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < len(grid) and 0 <= neighbor[1] < len(grid[0]):
                # Get the cost of moving to the neighbor
                tile_value = grid[neighbor[0]][neighbor[1]]
                movement_cost = tile_cost.get(tile_value, float('inf'))  # Default to infinity for invalid tiles

                # Calculate new cost
                new_cost = g_cost[current] + movement_cost

                if neighbor not in g_cost or new_cost < g_cost[neighbor]:
                    g_cost[neighbor] = new_cost
                    priority = new_cost + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (priority, neighbor))
                    came_from[neighbor] = current

    return None
class Node():
    """A node class for A* Pathfinding"""

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position


def astar(maze, start, end):
    """Returns a list of tuples as a path from the given start to the given end in the given maze"""

    # Create start and end node
    start_node = Node(None, start)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end)
    end_node.g = end_node.h = end_node.f = 0

    # Initialize both open and closed list
    open_list = []
    closed_list = []

    # Add the start node
    open_list.append(start_node)

    # Loop until you find the end
    while len(open_list) > 0:

        # Get the current node
        current_node = open_list[0]
        current_index = 0
        for index, item in enumerate(open_list):
            if item.f < current_node.f:
                current_node = item
                current_index = index

        # Pop current off open list, add to closed list
        open_list.pop(current_index)
        closed_list.append(current_node)

        # Found the goal
        if current_node == end_node:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            return path[::-1] # Return reversed path

        # Generate children
        children = []
        for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0)]: # Adjacent squares

            # Get node position
            node_position = (current_node.position[0] + new_position[0], current_node.position[1] + new_position[1])

            # Make sure within range
            if node_position[0] > (len(maze) - 1) or node_position[0] < 0 or node_position[1] > (len(maze[len(maze)-1]) -1) or node_position[1] < 0:
                continue

            # Make sure walkable terrain

            if maze[node_position[0]][node_position[1]] != 0:
                continue

            # Create new node
            new_node = Node(current_node, node_position)

            # Append
            children.append(new_node)

        # Loop through children
        for child in children:

            # Child is on the closed list
            for closed_child in closed_list:
                if child == closed_child:
                    continue

            # Create the f, g, and h values
            child.g = current_node.g + 1
            child.h = ((child.position[0] - end_node.position[0]) ** 2) + ((child.position[1] - end_node.position[1]) ** 2)
            child.f = child.g + child.h

            # Child is already in the open list
            for open_node in open_list:
                if child == open_node and child.g > open_node.g:
                    continue

            # Add the child to the open list
            open_list.append(child)


def initiate_astar(grid, connections, local_connections, objects):
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

            if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell) and obj.number_id == id_start:
                for port in obj.layout_ports:

                    if port.type == start_area:

                        start = [(obj.transform_matrix.c + (port.area.x2+port.area.x1)//2)//10, (obj.transform_matrix.f + (port.area.y2 + port.area.y1)//2)//10]
                        start_found = True
                        break
            if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell) and obj.number_id == id_end:
                for port in obj.layout_ports:
                    if port.type == end_area:
                        end = [(obj.transform_matrix.c + (port.area.x2 + port.area.x1)//2) // 10,
                               (obj.transform_matrix.f + (port.area.y2 + port.area.y1)//2) // 10]
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
        path.append(astar_test(grid, start, end))



    return path, path_names
