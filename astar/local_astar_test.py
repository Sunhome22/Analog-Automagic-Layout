import heapq


class PriorityQueue:
    """Priority Queue implementation using heapq."""

    def __init__(self):
        self.elements = []

    def is_empty(self):
        return len(self.elements) == 0

    def push(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def pop(self):
        return heapq.heappop(self.elements)[1]


def heuristic(a, b):
    """Manhattan distance heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def is_valid_block(x, y, direction, path_width, grid):
    """Check if a block of size `path_width` is valid at position (x, y)."""
    grid_height = len(grid)
    grid_width = len(grid[0])

    # Validate block based on direction
    if direction in ["up", "down"]:
        # Moving vertically: check a column of width `path_width`
        for dx in range(-(path_width // 2), (path_width // 2) + 1):
            nx = x + dx
            if not (0 <= nx < grid_width) or not (0 <= y < grid_height) or grid[y][nx] != 0:
                return False
    elif direction in ["left", "right"]:
        # Moving horizontally: check a row of width `path_width`
        for dy in range(-(path_width // 2), (path_width // 2) + 1):
            ny = y + dy
            if not (0 <= x < grid_width) or not (0 <= ny < grid_height) or grid[ny][x] != 0:
                return False
    return True


def get_neighbors(node, path_width, grid):
    """Generate neighbors considering path width."""
    x, y, direction = node
    neighbors = []

    moves = {
        "up": (0, -1, "up"),
        "down": (0, 1, "down"),
        "left": (-1, 0, "left"),
        "right": (1, 0, "right"),
    }

    for move, (dx, dy, new_direction) in moves.items():
        nx, ny = x + dx, y + dy
        if is_valid_block(nx, ny, new_direction, path_width, grid):
            neighbors.append((nx, ny, new_direction))
    return neighbors


def expand_path(path, path_width):
    """Expand the path to include all points occupied by the path width."""
    expanded_path = set()
    for x, y, direction in path:
        if direction in ["up", "down"]:
            # Add points in a column
            for dx in range(-(path_width // 2), (path_width // 2) + 1):
                expanded_path.add((x + dx, y))
        elif direction in ["left", "right"]:
            # Add points in a row
            for dy in range(-(path_width // 2), (path_width // 2) + 1):
                expanded_path.add((x, y + dy))
    return sorted(expanded_path)  # Sorted for consistency


def a_star(start, goal, grid, path_width):
    """A* algorithm with variable path width."""
    open_set = PriorityQueue()
    open_set.push((start[0], start[1], None), 0)  # (x, y, direction)

    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while not open_set.is_empty():
        current = open_set.pop()
        x, y, direction = current

        if (x, y) == goal:
            path = reconstruct_path(came_from, current)
            expanded_path = expand_path(path, path_width)
            return expanded_path

        for neighbor in get_neighbors(current, path_width, grid):
            nx, ny, new_direction = neighbor
            tentative_g_score = g_score.get((x, y), float('inf')) + 1

            if (nx, ny) not in g_score or tentative_g_score < g_score.get((nx, ny), float('inf')):
                came_from[(nx, ny, new_direction)] = (x, y, direction)
                g_score[(nx, ny)] = tentative_g_score
                f_score[(nx, ny)] = g_score[(nx, ny)] + heuristic((nx, ny), goal)
                open_set.push((nx, ny, new_direction), f_score[(nx, ny)])

    return None  # No path found


def reconstruct_path(came_from, current):
    """Reconstruct the path from start to goal."""
    path = []
    while current in came_from:
        path.append(current)  # Include direction for expansion
        current = came_from[(current[0], current[1], current[2])]
    path.reverse()
    return path


# Example Usage
if __name__ == "__main__":
    grid = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0],
        [0, 0, 3, 3, 3, 3, 3, 3, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]  # 0 = Walkable, 1 = Obstacle

    start = (3
             , 0)  # Start position
    goal = (7, 7)  # Goal position
    path_width = 3
    path = a_star(start, goal, grid, path_width)
    if path:
        print("Path found:", path)
    else:
        print("No path found.")
