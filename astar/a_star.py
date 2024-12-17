# ==================================================================================================================== #
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #

import pulp
from traces.write_trace import segment_path
from circuit.circuit_components import CircuitCell, Pin
from logger.logger import get_a_logger
import heapq

logger = get_a_logger(__name__)

class PriorityQueue:
    """Priority Queue for managing open set nodes."""

    def __init__(self):
        self.elements = []

    def is_empty(self):
        return len(self.elements) == 0

    def push(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def pop(self):
        return heapq.heappop(self.elements)[1]


def heuristic(a, b):
    """Manhattan distance heuristic for grid-based movement."""

    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(node, grid, goal, seg_list):
    """Get valid neighbors for the current node."""
    x, y = node
    neighbors = []
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up
    in_seg = False
    index = 0

    if len(seg_list) > 0:
        for i, seg in enumerate(seg_list):
            if node in seg:
                in_seg = True
                index = i
                break

    for dx, dy in directions:
        nx, ny = x + dx, y + dy

        if in_seg:
            # Check bounds and obstacles
            if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0 and (nx, ny) not in seg_list[index]:
                neighbors.append((nx, ny))
            elif 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == goal:
                neighbors.append((nx, ny))
        else:
            if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0:
                neighbors.append((nx, ny))
            elif 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == goal:
                neighbors.append((nx, ny))

    return neighbors


def reconstruct_path(came_from, current):
    """Reconstruct the path from start to goal."""
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


def a_star(grid, start, goal, seg_list):
    open_set = PriorityQueue()
    open_set.push(start, 0)

    came_from = {}  # To reconstruct the path
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while not open_set.is_empty():
        current = open_set.pop()

        # Check if we reached the goal
        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in get_neighbors(current, grid, goal, seg_list):
            tentative_g_score = g_score[current] + 1  # Cost from start to neighbor

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                # Update the best path to this neighbor
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                open_set.push(neighbor, f_score[neighbor])

    return None  # No path found


def initiate_astar(grid, connections, local_connections, objects, area_coordinates):
    logger.info("Starting Initiate A*")

    path = []
    seg_list = []
    path_names = []

    spliced_list = {**connections, **local_connections}

    for con in spliced_list.values():
        id_start = con.starting_comp
        id_end = con.end_comp
        start_area = con.starting_area[0]
        end_area = con.end_area[0]
        start_found = False
        end_found = False

        for obj in objects:

            if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == id_start:
                start = (
                area_coordinates[str(id_start) + start_area][0][0], area_coordinates[str(id_start) + start_area][0][2])

                start_found = True

            if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == id_end:
                end = (area_coordinates[str(id_end) + end_area][0][0], area_coordinates[str(id_end) + end_area][0][2])
                end_found = True

            if start_found and end_found:
                break

        string = str(id_start) + str(start_area) + "-" + str(id_end) + str(end_area)
        path_names.append(string)

        #Start and end point walkable
        grid[start[1]][start[0]] = 0
        grid[end[1]][end[0]] = 0

        path.append(a_star(grid, start, end, seg_list))

        #Start and end point not walkable
        grid[start[1]][start[0]] = 1
        grid[end[1]][end[0]] = 1

        seg = segment_path(path[-1])


        for s in seg:
            seg_list.append(s)


        add_grid_points = [sub[-1] for sub in seg]

        for x, y in add_grid_points:
            grid[y][x] = 1


    logger.info("Finished A*")
    return path, path_names