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
from itertools import combinations

import pulp
from traces.trace_generate import segment_path
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


def get_neighbors(node, grid, goal, seg_list, net):
    """Get valid neighbors for the current node."""
    neighbors = []
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # Right, Down, Left, Up
    in_seg = False
    index = "ph"
    segment_net = "ph"
    s ="ph"
    if seg_list:
        for s_net in seg_list:
            for i, seg in enumerate(seg_list[s_net]):
                if node in seg:
                    in_seg = True
                    index = i
                    segment_net = s_net
                    break
    #Both segment_net and net the path is in can be "local", such as local:net1 and both can be just net1
    if segment_net in net or net in segment_net:
        s = net

    for dx, dy in directions:
        nx, ny = node[0] + dx, node[1] + dy

        if in_seg:
            # Check bounds and obstacles
            if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0 and ((nx, ny) not in seg_list[segment_net][index] or s == net):
                neighbors.append(((nx,ny), (dx,dy)))
            elif 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == goal:
                neighbors.append(((nx,ny), (dx,dy)))
        else:
            if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == 0:
                neighbors.append(((nx,ny), (dx,dy)))
            elif 0 <= nx < len(grid[0]) and 0 <= ny < len(grid) and grid[ny][nx] == goal:
                neighbors.append(((nx,ny), (dx,dy)))

    return neighbors


def reconstruct_path(came_from, current):
    """Reconstruct the path from start to goal."""
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


def a_star(grid, start, goal, seg_list, net):
    open_set = PriorityQueue()
    open_set.push((start,None),0)

    came_from = {}  # To reconstruct the path
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while not open_set.is_empty():
        current, current_dir = open_set.pop()

        # Check if we reached the goal
        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor, direction in get_neighbors(current, grid, goal, seg_list, net):
            direction_change_penalty = 0 if current_dir is None or current_dir == direction else 1

            tentative_g_score = g_score[current] + 1 + direction_change_penalty  # Cost from start to neighbor

            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                # Update the best path to this neighbor
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                open_set.push((neighbor,direction), f_score[neighbor])

    return None  # No path found

def check_start_end_port(con, port_scaled_coords: dict):
    start_ports = con.start_area
    end_ports = con.end_area
    port_combinations = {}

    for x in start_ports:
        for y in end_ports:

            point1 = [port_scaled_coords[con.start_comp_id + x][0], port_scaled_coords[con.start_comp_id + x][2]]
            point2 = [port_scaled_coords[con.end_comp_id + y][0], port_scaled_coords[con.end_comp_id + y][2]]
            port_combinations[x+y]=sum(abs(a - b) for a, b in zip(point1, point2))

    designated_ports = min(port_combinations, key = port_combinations.get)

    start = (int(port_scaled_coords[con.start_comp_id + designated_ports[0]][0]),
             int(port_scaled_coords[con.start_comp_id + designated_ports[0]][2]))
    end = (int(port_scaled_coords[con.end_comp_id + designated_ports[1]][0]),
             int(port_scaled_coords[con.end_comp_id + designated_ports[1]][2]))

    return start, designated_ports[0], end, designated_ports[1]





def initiate_astar(grid, connections, local_connections, objects, port_scaled_coords, net_list):
    logger.info("Starting Initiate A*")
    grid_vertical = grid
    grid_horizontal = grid
    path = {}
    seg_list = {}

    done = []

    spliced_list = local_connections + connections

    for net in net_list.applicable_nets:
        for con in spliced_list:

            if con.net == net or ("local" in con.net and con not in done):

                done.append(con)
                start_found = False
                end_found = False


                for index, obj in enumerate(objects):

                    if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == int(con.start_comp_id):
                        start = (int(port_scaled_coords[con.start_comp_id + con.start_area[0]][0]), int(port_scaled_coords[con.start_comp_id + con.start_area[0]][2]))
                        start_found = True

                    if not isinstance(obj, (Pin, CircuitCell)) and obj.number_id == int(con.end_comp_id):
                        end = (int(port_scaled_coords[con.end_comp_id + con.end_area[0]][0]), int(port_scaled_coords[con.end_comp_id + con.end_area[0]][2]))
                        end_found = True

                    if start_found and end_found:
                        break

                if len(con.start_area)>=2 or len(con.end_area) >= 2:
                    start, con.start_area, end, con.end_area = check_start_end_port(con, port_scaled_coords)






                #Start and end point walkable

                grid[start[1]][start[0]] = grid[end[1]][end[0]] = 0
                p = a_star(grid, start, end, seg_list, con.net)
                path.setdefault(con.net, []).append((con.start_comp_id+con.start_area + "_"+con.end_comp_id+con.end_area, p))

                #Start and end point not walkable
                grid[start[1]][start[0]] =  grid[end[1]][end[0]] = 1


                seg = segment_path(p)
                if con.net not in seg_list:
                    seg_list[con.net] = []

                for s in seg:
                    seg_list[con.net].append(s)


                add_grid_points = [sub[-1] for sub in seg]

                for x, y in add_grid_points:
                    grid[y][x] = 1


    logger.info("Finished A*")
    return path, seg_list