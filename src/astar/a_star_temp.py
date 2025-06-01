from itertools import combinations
from logger.logger import get_a_logger  # Remove if not needed
import sys

class PriorityQueue:
    # Holds tuples (priority, item)
    def __init__(self):
        self.elements = []

    def is_empty(self):
        return not self.elements

    def push(self, item, priority):
        self.elements.append((priority, item))
        idx = len(self.elements) - 1
        self._sift_up(idx)

    def pop(self):
        if not self.elements:
            raise IndexError("pop from empty priority queue")

        last_item = self.elements.pop()
        if not self.elements:
            return last_item[1]

        top = self.elements[0]
        self.elements[0] = last_item
        self._sift_down(0)
        return top[1]

    def _sift_up(self, idx):
        while idx > 0:
            parent = (idx - 1) >> 1
            if self.elements[idx][0] < self.elements[parent][0]:
                self.elements[idx], self.elements[parent] = self.elements[parent], self.elements[idx]
                idx = parent
            else:
                break

    def _sift_down(self, idx):
        size = len(self.elements)
        while True:
            left = (idx << 1) + 1
            right = (idx << 1) + 2
            smallest = idx

            if left < size and self.elements[left][0] < self.elements[smallest][0]:
                smallest = left
            if right < size and self.elements[right][0] < self.elements[smallest][0]:
                smallest = right

            if smallest != idx:
                self.elements[idx], self.elements[smallest] = self.elements[smallest], self.elements[idx]
                idx = smallest
            else:
                break

def tsp_ordering(goals):
    penalty = 10000
    n = len(goals)
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dx = abs(goals[i][0] - goals[j][0])
            dy = abs(goals[i][1] - goals[j][1])
            cost = dx + dy
            if (1 <= dx <= 8) or (1 <= dy <= 8):
                cost += penalty
            dist[i][j] = cost
    dp = {}
    parent = {}
    for j in range(n):
        dp[(1 << j, j)] = 0
    for mask in range(1 << n):
        for j in range(n):
            if (mask & (1 << j)) == 0:
                continue
            if (mask, j) not in dp:
                continue
            base = dp[(mask, j)]
            for k in range(n):
                if mask & (1 << k):
                    continue
                new_mask = mask | (1 << k)
                new_cost = base + dist[j][k]
                if new_cost < dp.get((new_mask, k), float('inf')):
                    dp[(new_mask, k)] = new_cost
                    parent[(new_mask, k)] = (mask, j)
    full_mask = (1 << n) - 1
    best = float('inf')
    best_end = None
    for j in range(n):
        if dp.get((full_mask, j), float('inf')) < best:
            best = dp[(full_mask, j)]
            best_end = j
    order = []
    state = (full_mask, best_end)
    while state in parent:
        order.append(state[1])
        state = parent[state]
    order.append(state[1])
    order.reverse()
    return order

def in_bounds(pos, width, height):
    x, y = pos
    return 0 <= x < width and 0 <= y < height

def is_walkable(pos, current_position, grid_vertical, grid_horizontal):
    x, y = pos
    old_x, old_y = current_position
    if x - old_x == 0:
        return grid_vertical[y][x] == 0
    else:
        return grid_horizontal[y][x] == 0

def cap_seg(seg, minimum_segment_length):
    return seg if seg < minimum_segment_length else minimum_segment_length

def astar_start(grid_vertical, grid_horizontal, start, goal_nodes, minimum_segment_length, tsp, trace_width_scaled):
    print("no cython")
    path = []
    cost = 0

    if tsp:
        if len(goal_nodes) <= 2:
            path, cost = a_star(grid_vertical, grid_horizontal, goal_nodes[0], goal_nodes, minimum_segment_length)
        else:
            order = tsp_ordering(goal_nodes)
            for i in range(1, len(order)):
                partial_path, partial_cost = a_star(
                    grid_vertical, grid_horizontal,
                    goal_nodes[order[i-1]], [goal_nodes[order[i]]], minimum_segment_length)
                segments = segmentation(partial_path)

                if partial_path is None and i > 1:
                    partial_path, partial_cost = a_star(
                        grid_vertical, grid_horizontal,
                        goal_nodes[order[i-2]], [goal_nodes[order[i]]], minimum_segment_length)
                if partial_path is None and i < len(order) - 1:
                    partial_path, partial_cost = a_star(
                        grid_vertical, grid_horizontal,
                        goal_nodes[order[i-1]], [goal_nodes[order[i+1]]], minimum_segment_length)

                if partial_path:
                    # grid_vertical, grid_horizontal = lock_trace(grid_vertical, grid_horizontal, segments, trace_width_scaled)
                    path.extend(partial_path)
                    cost += partial_cost
                else:
                    return None, None
    else:
        path, cost = a_star(grid_vertical, grid_horizontal, start, goal_nodes, minimum_segment_length)

    return path, cost

def a_star(grid_vertical, grid_horizontal, start, goal_nodes, minimum_segment_length):
    height = len(grid_vertical)
    width = len(grid_vertical[0]) if height > 0 else 0

    goal_indices = {goal: i for i, goal in enumerate(goal_nodes)}
    all_visited = (1 << len(goal_nodes)) - 1

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    open_set = PriorityQueue()
    init_mask = 0
    init_after_goal = start in goal_indices
    if init_after_goal:
        init_mask |= (1 << goal_indices[start])
    g_start = 0
    f_start = g_start + _heuristic(start, init_mask, goal_nodes)

    open_set.push((g_start, start, init_mask, [start], None, 0, init_after_goal, False), f_start)

    visited_states = set()

    while not open_set.is_empty():
        g, current, mask, path, last_dir, seg_len, after_goal, last_was_reversal = open_set.pop()
        state_key = (current, mask, last_dir, cap_seg(seg_len, minimum_segment_length), after_goal, last_was_reversal)
        if state_key in visited_states:
            continue
        visited_states.add(state_key)

        if mask == all_visited:
            return path, g

        x, y = current
        edge_set = set(zip(path, path[1:]))

        for d in directions:
            dx, dy = d
            neighbor = (x + dx, y + dy)
            if not (in_bounds(neighbor, width, height) and is_walkable(neighbor, current, grid_vertical, grid_horizontal)):
                continue

            prospective_last_dir = None
            prospective_seg_len = 0
            prospective_last_was_reversal = False

            if last_dir is None:
                prospective_last_dir = d
                prospective_seg_len = 1
                penalty = 0
            else:
                if d == last_dir:
                    penalty = 0
                    prospective_last_dir = last_dir
                    edge = (current, neighbor)
                    edge_rev = (neighbor, current)
                    if edge in edge_set or edge_rev in edge_set:
                        prospective_seg_len = seg_len
                    else:
                        prospective_seg_len = seg_len + 1
                    prospective_last_was_reversal = False
                elif d[0] == -last_dir[0] and d[1] == -last_dir[1]:
                    if not after_goal or seg_len < minimum_segment_length:
                        continue
                    prospective_last_dir = d
                    prospective_seg_len = 1
                    prospective_last_was_reversal = True
                    penalty = 1
                else:
                    if seg_len < minimum_segment_length:
                        continue
                    prospective_last_dir = d
                    prospective_seg_len = 1
                    prospective_last_was_reversal = False
                    penalty = 1

            if neighbor in goal_indices:
                if prospective_seg_len < minimum_segment_length:
                    continue
                prospective_seg_len = 0
                prospective_last_dir = None

            new_mask = mask
            new_after_goal = after_goal
            if neighbor in goal_indices:
                new_mask |= (1 << goal_indices[neighbor])
                new_after_goal = True

            edge = (current, neighbor)
            edge_rev = (neighbor, current)
            cost_increment = 0 if (edge in edge_set or edge_rev in edge_set) else 1

            new_g = g + cost_increment + penalty
            new_f = new_g + _heuristic(neighbor, new_mask, goal_nodes)
            open_set.push(
                (new_g, neighbor, new_mask, path + [neighbor],
                 prospective_last_dir, prospective_seg_len, new_after_goal, prospective_last_was_reversal),
                new_f
            )

    return None, None

def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def _heuristic(current, mask, goals):
    unvisited = [goal for i, goal in enumerate(goals) if not (mask & (1 << i))]
    if not unvisited:
        return 0
    return min(_manhattan(current, goal) for goal in unvisited)

def lock_trace(grid_vertical, grid_horizontal, segments, trace_width_scaled):
    for segment in segments:
        # vertical
        if segment[0][0] - segment[-1][0] == 0:
            for x, y in segment:
                for i in range(-trace_width_scaled, trace_width_scaled + 1):
                    for p in range(-trace_width_scaled, trace_width_scaled+1):
                        if y+p < len(grid_vertical)-1 and x+i < len(grid_vertical[0])-1:
                            grid_vertical[y + p][x + i] = 0.9
        # horizontal
        if segment[0][1] - segment[-1][1] == 0:
            for x, y in segment:
                for i in range(-trace_width_scaled, trace_width_scaled + 1):
                    for p in range(-trace_width_scaled, trace_width_scaled+1):
                        if y + i < len(grid_horizontal)-1 and x + p < len(grid_horizontal[0])-1:
                            grid_horizontal[y + i][x + p] = 0.9
    return grid_vertical, grid_horizontal

def direction(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return dx, dy

def segmentation(path):
    if path is None or len(path) < 2:
        return []
    segments = []
    current_segment = [path[0]]
    current_direction = direction(path[0], path[1])
    for i in range(1, len(path)):
        next_direction = direction(path[i-1], path[i])
        if next_direction != current_direction:
            current_segment.append(path[i-1])
            segments.append(current_segment)
            current_segment = [path[i-1]]
            current_direction = next_direction
        current_segment.append(path[i])
    if current_segment:
        segments.append(current_segment)
    return segments