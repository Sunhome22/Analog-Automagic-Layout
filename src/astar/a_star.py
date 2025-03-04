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



from draw_result.visualize_grid import heatmap_test

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


def heuristic(current, mask, goals):

    # Get unvisited goals.
    unvisited = [goal for i, goal in enumerate(goals) if not (mask & (1 << i))]
    if not unvisited:
        return 0

    def manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    return min(manhattan(current, goal) for goal in unvisited)


# def get_neighbors(node, grid_vertical, grid_horizontal, goal, current_dir, seg_length):
#     """Get valid neighbors for the current node."""
#     neighbors = []
#     h_dir = [(1, 0), (-1, 0)]
#     v_dir = [ (0, 1), (0, -1)]
#
#
#
#
#     for hdx, hdy in h_dir:
#         hx, hy = node[0] + hdx, node[1] + hdy
#
#
#             # Check bounds and obstacles
#         if 0 <= hx < len(grid_horizontal[0]) and 0 <= hy < len(grid_horizontal) and grid_horizontal[hy][hx] == 0:
#             neighbors.append(((hx,hy), (hdx,hdy)))
#         elif 0 <= hx < len(grid_horizontal[0]) and 0 <= hy < len(grid_horizontal) and grid_horizontal[hy][hx] == goal:
#             neighbors.append(((hx,hy), (hdx,hdy)))
#
#
#     for vdx, vdy in v_dir:
#         vx, vy = node[0] + vdx, node[1] + vdy
#
#         if 0 <= vx < len(grid_vertical[0]) and 0 <= vy < len(grid_vertical) and grid_vertical[vy][vx] == 0:
#             neighbors.append(((vx,vy), (vdx,vdy)))
#         elif 0 <= vx < len(grid_vertical[0]) and 0 <= vy < len(grid_vertical) and grid_vertical[vy][vx] == goal:
#             neighbors.append(((vx,vy), (vdx,vdy)))
#
#
#     return neighbors


def reconstruct_path(came_from, current):
    """Reconstruct the path from start to goal."""
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


def a_star(grid_vertical, grid_horizontal, start, goals):
    minimum_seg_length = 6 # Change this to 1 for debugging, but note the impact on state space.
    goal_indices = {goal: i for i, goal in enumerate(goals)}
    all_visited = (1 << len(goals)) - 1
    height = len(grid_vertical)
    width = len(grid_vertical[0]) if height > 0 else 0
    min_seg_after_goal = 10
    def in_bounds(pos):
        x, y = pos
        return 0 <= x < width and 0 <= y < height

    def is_walkable(pos, current_position):
        x, y = pos
        old_x, old_y = current_position
        if x-old_x == 0:
            return grid_vertical[y][x] == 0
        else:
            return grid_horizontal[y][x]==0


    # Movements: up, down, left, right.
    directions = [(0, -1), (0, 1),(-1, 0), (1, 0)]

    open_set = PriorityQueue()
    init_mask = 0
    init_after_goal = start in goal_indices
    if init_after_goal:
        init_mask |= (1 << goal_indices[start])
    g_start = 0
    f_start = g_start + heuristic(start, init_mask, goals)
    # For the starting state, no previous direction (None) and segment length 0.
    open_set.push((g_start, start, init_mask, [start], None, 0, init_after_goal), f_start)

    visited_states = set()

    # Helper to cap the segment length in state keys.
    def cap_seg(seg):
        return seg if seg < minimum_seg_length else minimum_seg_length

    while not open_set.is_empty():
        g, current, mask, path, last_dir, seg_len, after_goal = open_set.pop()
        state_key = (current, mask, last_dir, cap_seg(seg_len), after_goal)
        if state_key in visited_states:
            continue
        visited_states.add(state_key)

        # Goal test: all goals have been visited.
        if mask == all_visited:
            return path, g

        x, y = current
        for d in directions:
            dx, dy = d
            neighbor = (x + dx, y + dy)
            if in_bounds(neighbor) and is_walkable(neighbor, current):
                new_g = g + 1  # uniform cost per step.
                new_mask = mask
                if neighbor in goal_indices:
                    new_mask |= (1 << goal_indices[neighbor])
                    new_after_goal = True
                else:
                    new_after_goal = after_goal

                # Determine new segment parameters.
                if last_dir is None:
                    # Starting state: choose any direction.
                    new_last_dir = d
                    new_seg_len = 1
                else:
                    if d == last_dir:
                        # Continue in the same direction.
                        new_last_dir = last_dir
                        new_seg_len = seg_len + 1
                    else:
                        # Attempting a turn: only allowed if the current segment length meets the minimum.
                        required_min = min_seg_after_goal if after_goal else minimum_seg_length
                        if seg_len >= required_min:
                            new_last_dir = d
                            new_seg_len = 1
                            new_after_goal = False
                        else:
                            continue  # Skip neighbor: segment too short to turn.

                new_f = new_g + heuristic(neighbor, new_mask, goals)
                open_set.push(
                    (new_g, neighbor, new_mask, path + [neighbor], new_last_dir, new_seg_len, new_after_goal),
                    new_f
                )

    return None, None


def check_start_end_port(con, port_scaled_coordinates: dict, port_coordinates: dict):
    start_ports = con.start_area
    end_ports = con.end_area
    port_combinations = {}

    for x in start_ports:
        for y in end_ports:

            point1 = [port_scaled_coordinates[con.start_comp_id + x][0], port_scaled_coordinates[con.start_comp_id + x][2]]
            point2 = [port_scaled_coordinates[con.end_comp_id + y][0], port_scaled_coordinates[con.end_comp_id + y][2]]
            port_combinations[x+y]=sum(abs(a - b) for a, b in zip(point1, point2))

    designated_ports = min(port_combinations, key = port_combinations.get)

    start = (int(port_scaled_coordinates[con.start_comp_id + designated_ports[0]][0]),
             int(port_scaled_coordinates[con.start_comp_id + designated_ports[0]][2]))
    real_start = (int(port_coordinates[con.start_comp_id + designated_ports[0]][0]),
             int(port_coordinates[con.start_comp_id + designated_ports[0]][1]))
    end = (int(port_scaled_coordinates[con.end_comp_id + designated_ports[1]][0]),
             int(port_scaled_coordinates[con.end_comp_id + designated_ports[1]][2]))
    real_end = (int(port_coordinates[con.end_comp_id + designated_ports[1]][0]),
             int(port_coordinates[con.end_comp_id + designated_ports[1]][1]))

    return start, real_start, end, real_end

def _lock_or_unlock_port(grid_vertical, grid_horizontal, goal, port_scaled_coordinates, lock):
    print(port_scaled_coordinates)
    h = 4
    w = 6
    for node in goal:
        for key in port_scaled_coordinates:
            if (int(port_scaled_coordinates[key][0]),int(port_scaled_coordinates[key][2])) == node:
                w = 4 if key[1] == "G" else 6
                break
        for y in range(node[1]-h, node[1]+h+1):
            for x in range(node[0]-w, node[0]+w+1):


                grid_vertical[y][x] = lock
                grid_horizontal[y][x] = lock

    return grid_vertical, grid_horizontal

def run_multiple_astar_multiple_times(grid_vertical, grid_horizontal,goals, run_multiple):
    best_path = None
    best_length = float('inf')
    if run_multiple:

        for start in goals:
            path, length = a_star(grid_vertical, grid_horizontal, start, goals)
            if path is not None and length < best_length:
                best_path = path
                best_length = length
        return best_path
    else:
        path, _ = a_star(grid_vertical, grid_horizontal, goals[0], goals)
        return path


def initiate_astar(grid, connections, components, port_scaled_coordinates, port_coordinates, net_list, run_multiple_astar):
    logger.info("Starting Initiate A*")
    grid_vertical = [row[:] for row in grid[:]]
    grid_horizontal = [row[:] for row in grid[:]]
    local_paths = {}
    path = {}
    seg_list = {}

    done = []

    start_id = 0
    end_id = 0

    for net in net_list.applicable_nets:

        goal_nodes = []
        real_goal_nodes = []
        for con in connections:
            start_found = False
            end_found = False
            if con.net == net:
                for index, placed_object in enumerate(components):

                    if not isinstance(placed_object, (Pin, CircuitCell)) and placed_object.number_id == int(con.start_comp_id):
                        start = (int(port_scaled_coordinates[con.start_comp_id + con.start_area[0]][0]), int(port_scaled_coordinates[con.start_comp_id + con.start_area[0]][2]))
                        real_start = (int(port_coordinates[con.start_comp_id + con.start_area[0]][0]), int(port_coordinates[con.start_comp_id + con.start_area[0]][1]))
                        start_found = True


                    if not isinstance(placed_object, (Pin, CircuitCell)) and placed_object.number_id == int(con.end_comp_id):
                        end = (int(port_scaled_coordinates[con.end_comp_id + con.end_area[0]][0]), int(port_scaled_coordinates[con.end_comp_id + con.end_area[0]][2]))
                        real_end = (int(port_coordinates[con.end_comp_id + con.end_area[0]][0]), int(port_coordinates[con.end_comp_id + con.end_area[0]][1]))
                        end_found = True

                    if start_found and end_found:
                        if len(con.start_area) >= 2 or len(con.end_area) >= 2:
                            start, real_start, end, real_end = check_start_end_port(con, port_scaled_coordinates, port_coordinates)

                        if start not in goal_nodes:
                            goal_nodes.append(start)
                            real_goal_nodes.append(real_start)


                        if end not in goal_nodes:
                            goal_nodes.append(end)
                            real_goal_nodes.append(real_end)


                        start_found = False
                        end_found = False


       #Make goal nodes walkable
        grid_vertical, grid_horizontal = _lock_or_unlock_port(grid_vertical, grid_horizontal, goal_nodes, port_scaled_coordinates , 0)


        p = run_multiple_astar_multiple_times(grid_vertical, grid_horizontal, goal_nodes, run_multiple_astar)

        path.setdefault(net, {})["goal_nodes"] = goal_nodes
        path.setdefault(net, {})["real_goal_nodes"] = real_goal_nodes
        #Make goal nodes non-walkable
        grid_vertical, grid_horizontal= _lock_or_unlock_port(grid_vertical, grid_horizontal, goal_nodes,port_scaled_coordinates,1)

        seg = segment_path(p)
        path.setdefault(net, {})["segments"] = seg
        if net not in seg_list:
            seg_list[net] = []


        for s in seg:
            seg_list[net].append(s)

        for seg in seg_list[net]:
            # vertical
            if seg[0][0] - seg[-1][0] == 0:

                for x, y in seg:
                    for i in range(-4, 5):
                        grid_vertical[y][x + i] = 1
                # for x,y in seg:
                #     grid_vertical[y][x] = 0.2

            # horizontal
            if seg[0][1] - seg[-1][1] == 0:
                for x, y in seg:
                    for i in range(-4, 5):
                        grid_horizontal[y + i][x] = 1

    heatmap_test(grid_vertical, "grid_vertical_heatmap")
    heatmap_test(grid_horizontal, "grid_horizontal_heatmap")



    logger.info("Finished A*")
    return path, seg_list