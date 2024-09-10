import pulp
import heapq
import matplotlib.pyplot as plt
import matplotlib.patches as patches



# Define grid size and objects

N, M = 10, 10

connections = [(0, 1), (1,2), (0,2)]
#Object parameters
num_objects = len(sum(connections, ()))

#create a PuLP problem minimization
prob = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)

# Create decision variables: x and y coordinates for each object (integer values between 0 an and grid_size-1
x = pulp.LpVariable.dicts("x", range(num_objects), 0, N-1, cat='Integer')
y = pulp.LpVariable.dicts("y", range(num_objects), 0, M-1, cat='Integer')

#Objective function: minimize total Manhattan distance between connected objects

def astar(start, goal, grid):
    if start is None or goal is None:
        return None
    def heuristic(a,b):
        if a[0] or a[1] is None or b[0] or b[1] is None:
            return float('inf')

        dx = a[0] - b[0] if a[0] > b[0] else b[0] - a[0]
        dy = a[1] - b[1] if a[1] > b[1] else b[1] - a[1]
        return dx+dy

    def neighbors(node):
        x,y = node
        directions =[(0,1), (1,0), (0, -1), (-1,0)]
        result = []
        for dx, dy in directions:
            nx,ny= x+dx, y+dy
            if 0 <=nx<N and 0<=ny<M and grid[nx][ny]:
                result.append((nx,ny))
        return result

    open_list=[]
    heapq.heappush(open_list,(0,start))
    came_from = {}
    g_score = {start:0}
    f_score={start: heuristic(start,goal)}
    while open_list:
        current = heapq.heappop(open_list)[1]

        if current == goal:
            path= []

            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]
        for neighbor in neighbors(current):
            tentative_g_score = g_score[current] + 1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_list, (f_score[neighbor], neighbor))

    return None

def calculate_total_path_length(postions, connections, grid):
    total_path_length = 0
    for i,j in connections:
        start = postions[i]
        goal = positions[j]
        path = astar(start,goal, grid)
        if path is None:
            return float('inf')
        total_path_length += len(path)-1
    return total_path_length

for i in range(num_objects):
    for j in range(i+1, num_objects):
        prob += x[i] != x[j]or y[i] != y[j], f"NonOverlap_{i}_{j}"
prob.solve()

positions = [(pulp.value(x[i]), pulp.value(y[i])) for i in range (num_objects)]

grid = [[0 for _ in range(M)] for _ in range(N)]
for i, (x_pos, y_pos) in enumerate(positions):
    if x_pos is not None and y_pos is not None:
        grid[int(x_pos)][int(y_pos)] = 1

total_path_length = calculate_total_path_length(positions, connections, grid)

print(f"Total path length: {total_path_length}")
print(f"Object positions: {positions}")

status = pulp.LpStatus[prob.status]
print(f"Solver status: {status}")