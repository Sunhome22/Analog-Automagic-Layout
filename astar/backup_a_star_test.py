# -*- coding: utf-8 -*-
"""
Created on Sun Nov 24 08:05:03 2024

@author: LeidulvMT
"""

import pulp
from traces.write_traces import segment_path
from circuit.circuit_components import CircuitCell, Pin

import heapq


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


def get_neighbors(node, grid):
    """Get valid neighbors for the current node."""
    x, y = node
    neighbors = []
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up

    for dx, dy in directions:
        nx, ny = x + dx, y + dy

        # Check bounds and obstacles
        if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0:
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


def a_star(grid, start, goal):
    """
    Perform the A* algorithm to find the shortest path in a grid.

    :param grid: 2D list representing the map (0 = free, 1 = obstacle)
    :param start: Starting point as a tuple (x, y)
    :param goal: Goal point as a tuple (x, y)
    :return: The shortest path as a list of tuples, or None if no path is found.
    """
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

        for neighbor in get_neighbors(current, grid):
            tentative_g_score = g_score[current] + 1  # Cost from start to neighbor

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                # Update the best path to this neighbor
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                open_set.push(neighbor, f_score[neighbor])

    return None  # No path found


def initiate_astar(grid, connections, local_connections, objects, area, area_coordinates, used_area):
    path = []
    local = True
    glo = False
    path_names = []
    coordinate_shift = []

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

                x_start = (obj.transform_matrix.c - used_area[0] + (96 + 60 + 30))
                y_start = (obj.transform_matrix.f - used_area[1] + 100)

                for p in obj.layout_ports:

                    if p.type == start_area:
                        start = (
                        ((p.area.x2 + p.area.x1) // 2 + x_start) // 32, ((p.area.y2 + p.area.y1) // 2 + y_start) // 40)
                        start_found = True
                        coordinate_shift.append((obj.transform_matrix.c, obj.transform_matrix.f))
                        break
            if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == id_end:
                x_start = (obj.transform_matrix.c - used_area[0] + (96 + 60 + 30))
                y_start = (obj.transform_matrix.f - used_area[1] + 100)
                for p in obj.layout_ports:
                    if p.type == end_area:
                        end = (
                        ((p.area.x2 + p.area.x1) // 2 + x_start) // 32, ((p.area.y2 + p.area.y1) // 2 + y_start) // 40)
                        end_found = True
                        break
            if start_found and end_found:
                break
        print("--------------------")
        print("Object position")
        print(obj.transform_matrix.c, obj.transform_matrix.f)
        print(id_start, id_end)
        string = str(id_start) + str(start_area) + "-" + str(id_end) + str(end_area)
        path_names.append(string)
        print(start, end)
        print("--------------------")
        path.append(a_star(grid, start, end))

        seg = segment_path(path[-1])
        print("Seg:")
        for s in seg:
            print(s)
        #if len(seg >= 1):
        print("PATH:")
        print(path[-1])
        print("Completed Path")

        add_grid_points = [sub[-1] for sub in seg]
        print(add_grid_points)

        print("ROW and COL values")
        for x, y in add_grid_points:
            grid[y][x] = 1

    return path, path_names