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


def get_neighbors(node, grid, path_tracker):
    """Generate valid neighbors for a given node."""
    x, y, direction = node
    neighbors = []

    moves = {
        "up": (0, -1, "vertical"),
        "down": (0, 1, "vertical"),
        "left": (-1, 0, "horizontal"),
        "right": (1, 0, "horizontal"),
    }

    for move, (dx, dy, new_direction) in moves.items():
        nx, ny = x + dx, y + dy

        # Check bounds
        if 0 <= nx < len(grid[0]) and 0 <= ny < len(grid):
            # Check for overlap rule
            if (nx, ny) in path_tracker:
                # Allow crossing but not continuous overlap
                existing_direction = path_tracker[(nx, ny)]
                if existing_direction == new_direction:
                    continue  # Skip if the direction is the same
            # Valid neighbor
            if grid[ny][nx] == 0:  # 0 = Walkable
                neighbors.append((nx, ny, new_direction))
    return neighbors


def a_star_with_crossing_rule(start, goal, grid):
    """A* algorithm where paths can cross but cannot overlap continuously."""
    open_set = PriorityQueue()
    open_set.push((start[0], start[1], None), 0)  # (x, y, direction)

    # Ensure start and goal are tuples
    start = tuple(start)
    goal = tuple(goal)

    # Initialize g_score and f_score with tuples for keys
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    came_from = {}
    path_tracker = {}  # Tracks the direction of paths on the grid

    while not open_set.is_empty():
        current = open_set.pop()
        x, y, direction = current

        # Update the path tracker
        if direction:
            path_tracker[(x, y)] = direction

        # Check if the goal is reached
        if (x, y) == goal:
            return reconstruct_path(came_from, current)

        for neighbor in get_neighbors(current, grid, path_tracker):
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
        path.append((current[0], current[1]))  # Only include (x, y)
        current = came_from[(current[0], current[1], current[2])]
    path.reverse()
    return path


# Example Usage
if __name__ == "__main__":
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 1, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]  # 0 = Walkable, 1 = Obstacle

    # Ensure start and goal are tuples
    start = (0, 0)  # Start position
    goal = (4, 4)  # Goal position

    path = a_star_with_crossing_rule(start, goal, grid)
    if path:
        print("Path found:", path)
    else:
        print("No path found.")
