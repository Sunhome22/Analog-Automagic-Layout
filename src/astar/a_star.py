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


from logger.logger import get_a_logger
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

class Memoize:
    def __init__(self, func):
        self.func = func
        self.memo = {}

    def __call__(self, *args):
        if args not in self.memo:
            self.memo[args] = self.func(*args)
        return self.memo[args]

    def __get__(self, instance, owner):
        # Bind the instance to the function
        return lambda *args: self(instance, *args)


class AstarAlgorithm:
    logger = get_a_logger(__name__)
    def __init__(self, grid_vertical, grid_horizontal, start, goal_nodes, minimum_segment_length):
        #Inputs
        self.grid_vertical = grid_vertical
        self.grid_horizontal = grid_horizontal
        self.goal_nodes = goal_nodes
        self.minimum_segment_length = minimum_segment_length
        self.start = start

        #Parameters
        self.height = len(grid_vertical)
        self.width = len(grid_vertical[0]) if self.height > 0 else 0



    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, pos, current_position):
        x, y = pos
        old_x, old_y = current_position
        if x - old_x == 0:
            return self.grid_vertical[y][x] == 0
        else:
            return self.grid_horizontal[y][x] == 0

    # Helper: for the state key, we cap the segment length to the minimum.
    def cap_seg(self, seg):
        return seg if seg < self.minimum_segment_length else self.minimum_segment_length

    @Memoize
    def a_star(self):

        goal_indices = {goal: i for i, goal in enumerate(self.goal_nodes)}
        all_visited = (1 << len(self.goal_nodes)) - 1


        # Allowed movements: up, down, left, right.
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        open_set = PriorityQueue()
        init_mask = 0
        init_after_goal = self.start in goal_indices
        if init_after_goal:
            init_mask |= (1 << goal_indices[self.start])
        g_start = 0
        f_start = g_start + heuristic(self.start, init_mask, self.goal_nodes)
        # Initial state: no previous direction (None), segment length 0.
        open_set.push((g_start, self.start, init_mask, [self.start], None, 0, init_after_goal, False), f_start)

        visited_states = set()

        while not open_set.is_empty():
            g, current, mask, path, last_dir, seg_len, after_goal, last_was_reversal = open_set.pop()
            state_key = (current, mask, last_dir, self.cap_seg(seg_len), after_goal, last_was_reversal)
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
                if not (self.in_bounds(neighbor) and self.is_walkable(neighbor, current)):
                    continue

                if not self.is_walkable(neighbor, current):
                    self.logger.error("Node not walkable but still going")
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
                        if not after_goal or seg_len < self.minimum_segment_length or last_was_reversal:
                            continue
                        prospective_last_dir = d
                        prospective_seg_len = 1
                        prospective_last_was_reversal = True
                    else:
                        # Turning into a new segment.
                        # You can only turn if your current (non-retracing) segment
                        # is at least minimum_segment_length.
                        if seg_len < self.minimum_segment_length:
                            continue
                        prospective_last_dir = d
                        prospective_seg_len = 1
                        prospective_last_was_reversal = False


                if neighbor in goal_indices:
                    if prospective_seg_len < self.minimum_segment_length:
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
                new_f = new_g + heuristic(neighbor, new_mask, self.goal_nodes)
                open_set.push(
                    (new_g, neighbor, new_mask, path + [neighbor],
                     prospective_last_dir, prospective_seg_len, new_after_goal, prospective_last_was_reversal),
                    new_f
                )
        self.logger.error("No viable path found")
        return None, None


def heuristic(current, mask, goals):

    # Get unvisited goals.
    unvisited = [goal for i, goal in enumerate(goals) if not (mask & (1 << i))]
    if not unvisited:
        return 0

    return min(manhattan(current, goal) for goal in unvisited)


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])



















