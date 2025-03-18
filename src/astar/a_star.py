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
from numpy.matlib import empty
from traces.trace_generate import segment_path
from circuit.circuit_components import CircuitCell, Pin
from logger.logger import get_a_logger
import heapq
import tomllib


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



def reconstruct_path(came_from, current):
    """Reconstruct the path from start to goal."""
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


def a_star(grid_vertical, grid_horizontal, start, goals, minimum_segment_length):

    goal_indices = {goal: i for i, goal in enumerate(goals)}
    all_visited = (1 << len(goals)) - 1
    height = len(grid_vertical)
    width = len(grid_vertical[0]) if height > 0 else 0

    def in_bounds(pos):
        x, y = pos
        return 0 <= x < width and 0 <= y < height

    def is_walkable(pos, current_position):
        x, y = pos
        old_x, old_y = current_position
        if x - old_x == 0:
            return grid_vertical[y][x] == 0
        else:
            return grid_horizontal[y][x] == 0

    # Allowed movements: up, down, left, right.
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    open_set = PriorityQueue()
    init_mask = 0
    init_after_goal = start in goal_indices
    if init_after_goal:
        init_mask |= (1 << goal_indices[start])
    g_start = 0
    f_start = g_start + heuristic(start, init_mask, goals)
    # Initial state: no previous direction (None), segment length 0.
    open_set.push((g_start, start, init_mask, [start], None, 0, init_after_goal, False), f_start)

    visited_states = set()

    # Helper: for the state key, we cap the segment length to the minimum.
    def cap_seg(seg):
        return seg if seg < minimum_segment_length else minimum_segment_length

    while not open_set.is_empty():
        g, current, mask, path, last_dir, seg_len, after_goal, last_was_reversal = open_set.pop()
        state_key = (current, mask, last_dir, cap_seg(seg_len), after_goal, last_was_reversal)
        if state_key in visited_states:
            continue
        visited_states.add(state_key)

        # If all goals have been visited, return the path.
        if mask == all_visited:
            return path, g

        x, y = current
        # Determine edges traversed so far.
        edge_set = set(zip(path, path[1:]))

        for d in directions:
            dx, dy = d
            neighbor = (x + dx, y + dy)
            if not (in_bounds(neighbor) and is_walkable(neighbor, current)):
                continue

            # Initialize prospective state variables.
            prospective_last_dir = None
            prospective_seg_len = 0
            prospective_last_was_reversal = False

            if last_dir is None:
                # At the start: choose a direction and begin a new segment.
                prospective_last_dir = d
                prospective_seg_len = 1
            else:
                if d == last_dir:
                    # Continuing in the same direction.
                    prospective_last_dir = last_dir
                    edge = (current, neighbor)
                    edge_rev = (neighbor, current)
                    # If this edge is already in our path, we are retracing:
                    # do not increase segment length.
                    if edge in edge_set or edge_rev in edge_set:
                        prospective_seg_len = seg_len
                    else:
                        prospective_seg_len = seg_len + 1
                    prospective_last_was_reversal = False
                elif d[0] == -last_dir[0] and d[1] == -last_dir[1]:
                    # A reversal move is allowed only if:
                    # 1. We're coming after a goal,
                    # 2. The current segment has reached minimum length,
                    # 3. The previous move was not already a reversal.
                    if not after_goal or seg_len < minimum_segment_length or last_was_reversal:
                        continue
                    prospective_last_dir = d
                    prospective_seg_len = 1
                    prospective_last_was_reversal = True
                else:
                    # Turning into a new segment.
                    # You can only turn if your current (non-retracing) segment
                    # is at least minimum_segment_length.
                    if seg_len < minimum_segment_length:
                        continue
                    prospective_last_dir = d
                    prospective_seg_len = 1
                    prospective_last_was_reversal = False

            # When moving into a goal cell, the move is allowed only if the
            # current segment (or new segment being formed) meets the minimum length.
            # Also, reaching a goal resets the segment: segment length goes to 0 and direction to None.
            if neighbor in goal_indices:
                if prospective_seg_len < minimum_segment_length:
                    continue
                prospective_seg_len = 0
                prospective_last_dir = None

            # Update the visited goals mask.
            new_mask = mask
            new_after_goal = after_goal
            if neighbor in goal_indices:
                new_mask |= (1 << goal_indices[neighbor])
                new_after_goal = True

            # Compute cost: if moving along a retraced edge, cost increment is 0.
            edge = (current, neighbor)
            edge_rev = (neighbor, current)
            cost_increment = 0 if (edge in edge_set or edge_rev in edge_set) else 1

            new_g = g + cost_increment
            new_f = new_g + heuristic(neighbor, new_mask, goals)
            open_set.push(
                (new_g, neighbor, new_mask, path + [neighbor],
                 prospective_last_dir, prospective_seg_len, new_after_goal, prospective_last_was_reversal),
                new_f
            )

    return None, None


"""----------------------------SPLIT HERE---------------------------------------------"""


class InitiateAstarAlgorithm:
    def __init__(self, components, grid, connections, port_scaled_coordinates, port_coordinates, net_list,
                            routing_sizing_area):
        self.logger = get_a_logger(__name__)
        self.config = self.__load_config()
        self.RUN_MULTIPLE_ASTAR = self.config["astar"]["RUN_MULTIPLE_ASTAR"]

        self.routing_parameters = routing_sizing_area
        self.components = components
        self.grid_vertical = [row[:] for row in grid[:]]
        self.grid_horizontal = [row[:] for row in grid[:]]
        self.connections = connections
        self.port_scaled_coordinates = port_scaled_coordinates
        self.port_coordinates = port_coordinates
        self.net_list = net_list
        self.goal_nodes = []
        self.real_goal_nodes = []
        self.path = {}
        self.seg_list = {}
        
    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def _extract_goal_nodes(self,connection_list, net):
        self.goal_nodes = []
        self.real_goal_nodes = []
        for con in connection_list:
            start_found = False
            end_found = False
            if con.net == net:
                for index, placed_object in enumerate(self.components):

                    if not isinstance(placed_object, (Pin, CircuitCell)) and placed_object.number_id == int(
                            con.start_comp_id):
                        start = (int(self.port_scaled_coordinates[con.start_comp_id + con.start_area[0]][0]),
                                 int(self.port_scaled_coordinates[con.start_comp_id + con.start_area[0]][2]))
                        real_start = (int(self.port_coordinates[con.start_comp_id + con.start_area[0]][0]),
                                      int(self.port_coordinates[con.start_comp_id + con.start_area[0]][1]))
                        start_found = True

                    if not isinstance(placed_object, (Pin, CircuitCell)) and placed_object.number_id == int(
                            con.end_comp_id):
                        end = (int(self.port_scaled_coordinates[con.end_comp_id + con.end_area[0]][0]),
                               int(self.port_scaled_coordinates[con.end_comp_id + con.end_area[0]][2]))
                        real_end = (int(self.port_coordinates[con.end_comp_id + con.end_area[0]][0]),
                                    int(self.port_coordinates[con.end_comp_id + con.end_area[0]][1]))
                        end_found = True

                    if start_found and end_found:
                        if len(con.start_area) >= 2 or len(con.end_area) >= 2:
                            start, real_start, end, real_end = check_start_end_port(con, self.port_scaled_coordinates,
                                                                                    self.port_coordinates)

                        if start not in self.goal_nodes:
                            self.goal_nodes.append(start)
                            self.real_goal_nodes.append(real_start)

                        if end not in self.goal_nodes:
                            self.goal_nodes.append(end)
                            self.real_goal_nodes.append(real_end)

                        start_found = False
                        end_found = False

    def _extract_goal_nodes_from_single_connections(self, connection_list, net):
        for con in connection_list:

            if con.net == net:
                for index, placed_object in enumerate(self.components):

                    if not isinstance(placed_object, (Pin, CircuitCell)) and placed_object.number_id == int(
                            con.start_comp_id):
                        self.goal_nodes.append((int(self.port_scaled_coordinates[con.start_comp_id + con.start_area[0]][0]),
                                           int(self.port_scaled_coordinates[con.start_comp_id + con.start_area[0]][2])))
                        self.real_goal_nodes.append((int(self.port_coordinates[con.start_comp_id + con.start_area[0]][0]),
                                                int(self.port_coordinates[con.start_comp_id + con.start_area[0]][1])))

    def _lock_or_unlock_port(self, lock):

        h = self.routing_parameters.port_height_scaled
        w = self.routing_parameters.port_width_scaled
        for node in self.goal_nodes:
            for key in self.port_scaled_coordinates:
                if (int(self.port_scaled_coordinates[key][0]), int(self.port_scaled_coordinates[key][2])) == node:
                    w = self.routing_parameters.gate_width_scaled if key[1] == "G" else self.routing_parameters.port_width_scaled

                    break

            for y in range(node[1] - h, node[1] + h + 1):
                for x in range(node[0] - w, node[0] + w + 1):
                    self.grid_vertical[y][x] = lock
                    self.grid_horizontal[y][x] = lock

    def _update_grid(self, net):
        for segment in self.seg_list[net]:
            # vertical

            if segment[0][0] - segment[-1][0] == 0:
                for x, y in segment:
                    for i in range(-self.routing_parameters.trace_width_scaled,
                                   self.routing_parameters.trace_width_scaled + 1):
                        for p in range(-2, 3):
                            self.grid_vertical[y + p][x + i] = 1

            # horizontal
            if segment[0][1] - segment[-1][1] == 0:
                for x, y in segment:
                    for i in range(-self.routing_parameters.trace_width_scaled,
                                   self.routing_parameters.trace_width_scaled + 1):
                        for p in range(-2, 3):
                            self.grid_horizontal[y + i][x + p] = 1

    def _run_multiple_astar_multiple_times(self):
        best_path = None
        best_length = float('inf')
        if self.RUN_MULTIPLE_ASTAR:

            for start in self.goal_nodes:

                path, length = a_star(self.grid_vertical, self.grid_horizontal, start, self.goal_nodes, self.routing_parameters.port_width_scaled)

                if path is not None and length < best_length:
                    best_path = path
                    best_length = length
            return best_path
        else:
            path, _ = a_star(self.grid_vertical, self.grid_horizontal, self.goal_nodes[0], self.goal_nodes, self.routing_parameters.port_width_scaled)
            return path

    def _initiate_astar(self):
        self.logger.info("Starting Initiate A*")



        for net in self.net_list.pin_nets + self.net_list.applicable_nets:
            # Skipping these nets, that are handled by other routing algorithm
            if "VDD" in net or "VSS" in net:
                continue

            self._extract_goal_nodes(connection_list=self.connections["component_connections"], net=net)

            if len(self.goal_nodes) == 0:
                self._extract_goal_nodes_from_single_connections(
                    connection_list=self.connections["single_connections"], net=net)


            # Make goal nodes walkable
            self._lock_or_unlock_port(lock=0)

            if len(self.goal_nodes) > 1:
                p = self._run_multiple_astar_multiple_times()
            else:
                p = []

            self.path.setdefault(net, {})["goal_nodes"] = self.goal_nodes
            self.path.setdefault(net, {})["real_goal_nodes"] = self.real_goal_nodes
            # Make goal nodes non-walkable
            self._lock_or_unlock_port(lock=1)

            segments = segment_path(p)
            self.path.setdefault(net, {})["segments"] = segments
            self.seg_list.setdefault(net, []).extend(segments)

            self._update_grid(net=net)

        # heatmap_test(grid_vertical, "grid_vertical_heatmap")
        # heatmap_test(grid_horizontal, "grid_horizontal_heatmap")

        logger.info("Finished A*")




"""Helper function deciding which of two connected ports should be routed from"""
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













