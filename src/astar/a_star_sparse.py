import heapq
import math
import time

from draw_result.visualize_grid import load_matrix

import heapq
import time


def manhattan(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def tsp_order_no_start(goals, penalty=1000):
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
def tsp_order(start, goals):
    nodes = [start] + goals
    n = len(nodes)
    dist = [[0]*n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            dist[i][j] = abs(nodes[i][0] - nodes[j][0]) + abs(nodes[i][1] - nodes[j][1])
    goal_count = len(goals)
    all_mask = (1 << goal_count) - 1
    dp, parent = {}, {}
    for j in range(1, goal_count+1):
        mask = 1 << (j-1)
        dp[(mask, j)] = dist[0][j]
        parent[(mask, j)] = (0, 0)
    for mask in range(all_mask+1):
        for j in range(1, goal_count+1):
            if not (mask & (1 << (j-1))):
                continue
            if (mask, j) not in dp:
                continue
            base = dp[(mask, j)]
            rem = all_mask ^ mask
            subset = rem
            while subset:
                bit = subset & -subset
                subset -= bit
                k = bit.bit_length()
                new_mask = mask | bit
                new_cost = base + dist[j][k]
                if new_cost < dp.get((new_mask, k), float('inf')):
                    dp[(new_mask, k)] = new_cost
                    parent[(new_mask, k)] = (mask, j)
    end_state, best = None, float('inf')
    for j in range(1, goal_count+1):
        if dp.get((all_mask, j), float('inf')) < best:
            best = dp[(all_mask, j)]
            end_state = (all_mask, j)
    order = []
    cur = end_state
    while cur and cur in parent:
        mask, j = cur
        order.append(j-1)
        cur = parent[cur]
        if cur[1] == 0:
            break
    order.reverse()
    return order

def astar_segment(start, goal, obst_vert, obst_horiz, H, W, min_seg, visited):
    dirs = {0: (-1, 0), 1: (0, 1), 2: (1, 0), 3: (0, -1)}
    start_state = (start[0], start[1], None, 0)
    open_heap = []
    h_val = abs(start[0] - goal[0]) + abs(start[1] - goal[1])
    heapq.heappush(open_heap, (h_val, 0, start_state))
    best_cost = {start_state: 0}
    pred = {start_state: None}
    final_state = None
    while open_heap:
        f, g, state = heapq.heappop(open_heap)
        x, y, d, seg = state
        if (x, y) == goal:
            final_state = state
            break
        for nd in range(4):
            dx, dy = dirs[nd]
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= H or ny < 0 or ny >= W:
                continue
            if nd == 0:
                if x == 0 or (obst_vert[x-1][y] >= 0.9 and not obst_vert[x-1][y] == 2):
                    continue
            elif nd == 2:
                if x >= H - 1 or (obst_vert[x][y] >= 0.9 and not obst_vert[x][y] == 2):
                    continue
            elif nd == 1:
                if y >= W - 1:
                    continue

                if obst_horiz[x][y] >= 0.9 and not obst_horiz[x][y] == 2  :
                    continue
            elif nd == 3:
                if y == 0:
                    continue
                if obst_horiz[x][y-1] >= 0.9 and not obst_horiz[x][y-1] == 2:
                    continue
            if d is None:
                new_seg = 1
                ndir = nd
            elif nd == d:
                new_seg = seg + 1
                ndir = d
            else:
                if seg < min_seg:
                    continue
                new_seg = 1
                ndir = nd
            new_state = (nx, ny, ndir, new_seg)
            step_cost = 0.5 if (nx, ny) in visited else 1.0
            new_g = g + step_cost
            if new_g < best_cost.get(new_state, float('inf')):
                best_cost[new_state] = new_g
                h_new = abs(nx - goal[0]) + abs(ny - goal[1])
                heapq.heappush(open_heap, (new_g + h_new, new_g, new_state))
                pred[new_state] = state
    else:
        return None, float('inf')
    path_seg = []
    st = final_state
    while st is not None:
        path_seg.append((st[0], st[1]))
        st = pred.get(st)
    path_seg.reverse()
    return path_seg, best_cost[final_state]

def find_multi_goal_path(obst_vert, obst_horiz, start, goals, min_seg):
    H = len(obst_vert)
    W = len(obst_horiz[0])
    order = tsp_order(start, goals)
    ordered_goals = [goals[i] for i in order]
    ordered_goals = goals[:]
    print(ordered_goals)
    full_path = [start]
    total_cost = 0
    visited = set([start])
    seg_path, cost = astar_segment(start, goals[0], obst_vert, obst_horiz, H, W, min_seg, visited)
    print(seg_path)
    curr = start
    for tg in ordered_goals:
        seg_path, cost = astar_segment(curr, tg, obst_vert, obst_horiz, H, W, min_seg, visited)
        if seg_path is None:
            return None, float('inf')
        full_path.extend(seg_path[1:])
        total_cost += cost
        for cell in seg_path:
            visited.add(cell)
        curr = tg
    return full_path, total_cost
def extract_goal_coordinates(matrix):
    goal_coords = []
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            if value == 2:
                goal_coords.append((i, j))
    return goal_coords

def main():
    obstacles_vertical  = load_matrix("test_grid")
    obstacles_horizontal = load_matrix("test_grid")
    goal = extract_goal_coordinates(obstacles_horizontal)

    obst_vert = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 1, 0, 1, 0],
        [0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0]
    ]
    obst_horiz = [
        [0, 0, 0, 0, 1, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0]
    ]
    start = (0, 0)
    goals = [(2, 3), (4, 6), (3, 0)]


    print(f"goals {goal}")
    start_time = time.perf_counter()
    path, cost = find_multi_goal_path(obst_vert, obst_horiz, start, goals, min_seg = 0)
    end_time = time.perf_counter()
    if path is None:
        print("No path Found")

    else:
        print("Path:", path)
        print("Cost:", cost)
    print("Time: {:.4f} sec".format(end_time - start_time))

if __name__ == '__main__':
    main()
