import matplotlib.pyplot as plt
import matplotlib.patches as patches


def drawNtransistor(ax, x, y, height, width):

    rect = patches.Rectangle((x, y), width, height, fill=True)
    ax.add_patch(rect)

    # Add text labels at various positions
    ax.text(x+width/2, y+height/2, 'N', ha = 'center', va = 'center', fontsize = 20, color = 'blue')
    ax.text(x, y+height/2, 'B', horizontalalignment='left', verticalalignment='center', fontsize=20, color = 'red')
    ax.text(x+width/2, y+height, 'C', horizontalalignment='center', verticalalignment='top', fontsize = 20, color = 'red')
    ax.text(x+width/2,y, 'E', horizontalalignment = 'center', verticalalignment = 'bottom', fontsize=20, color='red')

def drawPtransistor(ax, x, y, height, width):

    rect = patches.Rectangle((x+5, y+5), width, height, fill=True)
    ax.add_patch(rect)
    x+=5
    y+=5
    # Add text labels at various positions
    ax.text(x+width/2, y+height/2, 'P', ha = 'center', va = 'center', fontsize = 20, color = 'blue')
    ax.text(x, y+height/2, 'B', horizontalalignment='left', verticalalignment='center', fontsize=20, color = 'red')
    ax.text(x+width/2, y+height, 'C', horizontalalignment='center', verticalalignment='top', fontsize = 20, color = 'red')
    ax.text(x+width/2,y, 'E', horizontalalignment = 'center', verticalalignment = 'bottom', fontsize=20, color='red')

def main():
    x, width = 1, 3
    y, height = 1, 3
    grid_size = 10

    fix, ax = plt.subplots(figsize=(10, 10))
    for i in range(grid_size + 1):
        ax.axhline(i, lw=0.5, color='gray', zorder=0)
        ax.axvline(i, lw=0.5, color='gray', zorder=0)

    drawNtransistor(ax, x, y, height, width)
    drawPtransistor(ax, x, y, height, width)


    plt.show()


##
import random
import math
import matplotlib.pyplot as plt
import Intersection
class SimulatedAnnealingGrid:
    def __init__(self, grid_width, grid_height, num_objects, connections, alpha=1, beta=1, theta=1):
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.num_objects = num_objects
        self.connections = connections  # List of tuples representing connections (edges) between objects
        self.temperature = 1000000000.0  # Initial temperature
        self.cooling_rate = 0.99998  # Rate at which temperature decreases
        self.min_temperature = 0.1  # Stop when temperature is this low
        self.alpha = alpha
        self.beta = beta
        self.theta = theta
        self.objects = self.initialize_objects()

    def initialize_objects(self):
        """Initialize objects with random non-overlapping positions."""
        positions = set()
        objects = []
        while len(objects) < self.num_objects:
            position = (random.randint(0, self.grid_width - 1), random.randint(0, self.grid_height - 1))
            if position not in positions:
                objects.append(position)
                positions.add(position)
                
                print(positions)
        return objects

    def manhattan_distance(self, obj1, obj2):
        """Calculate the Manhattan distance between two objects."""
        return abs(obj1[0] - obj2[0]) + abs(obj1[1] - obj2[1])

    def count_intersections(self):
        """Count the number of intersections between edges."""
        def edge_intersects(e1, e2):
            """Check if two edges (each represented by a pair of points) intersect."""
            # Simple axis-aligned bounding box intersection check
            (a, b), (c, d) = e1, e2
            return (min(a[0], b[0]) <= max(c[0], d[0]) and
                    min(c[0], d[0]) <= max(a[0], b[0]) and
                    min(a[1], b[1]) <= max(c[1], d[1]) and
                    min(c[1], d[1]) <= max(a[1], b[1]))

        intersections = 0
        edges = [(self.objects[a], self.objects[b]) for a, b in self.connections]
        for i in range(len(edges)):
            for j in range(i + 1, len(edges)):
                if edge_intersects(edges[i], edges[j]):
                    intersections += 1
        return intersections

    def total_edge_length(self):
        """Calculate the total edge length (L) as the sum of Manhattan distances between connected objects."""
        total_length = 0
        for a, b in self.connections:
            total_length += self.manhattan_distance(self.objects[a], self.objects[b])
        return total_length

    def total_squared_edge_length(self):
        """Calculate the total squared edge length (S) as the sum of squared Manhattan distances between connected objects."""
        total_squared_length = 0
        for a, b in self.connections:
            dist = self.manhattan_distance(self.objects[a], self.objects[b])
            total_squared_length += dist ** 2
        return total_squared_length

    def objective_function(self):
        """Calculate the objective function F(G) = alpha*N + beta*L + theta*S."""
        N = self.count_intersections()
        L = self.total_edge_length()
        S = self.total_squared_edge_length()
        return self.alpha * N + self.beta * L + self.theta * S

    def random_neighbor(self):
        """Generate a neighboring solution by moving one object to a random, non-overlapping position."""
        new_objects = self.objects[:]
        positions = set(new_objects)

        # Select a random object to move
        idx = random.randint(0, self.num_objects - 1)
        current_position = new_objects[idx]

        # Find a new non-overlapping position
        while True:
            
            direction = random.randrange(0, 4)
            
            if direction == 0:
                new_position = (current_position[0]+1, current_position[1])
            elif direction == 1:
                new_position = (current_position[0]-1, current_position[1])
            elif direction == 2:
                new_position = (current_position[0], current_position[1]+1)
            else:
                new_position = (current_position[0], current_position[1]+1)
            
            
            
            
            
            if new_position not in positions:
                
                if 0<=new_position[0] <= self.grid_width-1 and 0<=new_position[1] <= self.grid_height-1:
                    new_objects[idx] = new_position
                    break
        
        return new_objects

    def acceptance_probability(self, current_cost, new_cost):
        """Calculate the probability of accepting a worse solution."""
        if new_cost > current_cost:
            return 1.0
        return math.exp((current_cost - new_cost) / self.temperature)
    def draw_solution(self):
        """Draw the grid, objects, and edges using matplotlib."""
        fig, ax = plt.subplots()

        # Draw grid lines
        for x in range(self.grid_width + 1):
            ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
        for y in range(self.grid_height + 1):
            ax.axhline(y, color='gray', linestyle='--', linewidth=0.5)

        # Plot objects
        for i, (x, y) in enumerate(self.objects):
            ax.plot(x + 0.5, y + 0.5, 'bo', markersize=10)  # Place objects at the center of the grid cells
            ax.text(x + 0.5, y + 0.5, f'{i}', color='white', ha='center', va='center')

        # Plot edges
        for a, b in self.connections:
            obj_a = self.objects[a]
            obj_b = self.objects[b]
            ax.plot([obj_a[0] + 0.5, obj_b[0] + 0.5], [obj_a[1] + 0.5, obj_b[1] + 0.5], 'r-')

        # Set axis limits and labels
        ax.set_xlim(0, self.grid_width)
        ax.set_ylim(0, self.grid_height)
        ax.set_xticks(range(self.grid_width + 1))
        ax.set_yticks(range(self.grid_height + 1))
        ax.set_aspect('equal')

        plt.gca().invert_yaxis()  # Invert the y-axis to match the traditional grid layout
        plt.show()

    def anneal(self):
        """Perform the simulated annealing process."""
        current_solution = self.objects
        current_cost = self.objective_function()

        while self.temperature > self.min_temperature:
            new_solution = self.random_neighbor()
            new_cost = self.objective_function()

            if self.acceptance_probability(current_cost, new_cost) > random.random():

                current_solution = new_solution
                current_cost = new_cost
                self.draw_solution()
            self.temperature *= self.cooling_rate

        self.objects = current_solution
        
        
        return current_solution, current_cost

    

# Example usage
if __name__ == "__main__":
    grid_width = 10
    grid_height = 10
    num_objects = 5
    connections = [(0, 1), (1, 2), (2, 3), (3, 4)]  # Example netlist (graph)

    alpha = 1
    beta = 2
    theta = 3

    sa = SimulatedAnnealingGrid(grid_width, grid_height, num_objects, connections, alpha, beta, theta)
    final_solution, final_cost = sa.anneal()

    print(f"Final solution: {final_solution}")
    print(f"Final cost (F(G)): {final_cost}")

    # Draw the final solution
    sa.draw_solution()
###-----------------------------------------###
import numpy as np


def determinant(matrix):
    print(matrix)
    return np.linalg.det(matrix)



def intersection(edge1, edge2):
    
    p1, p2 = edge1
    p3, p4 = edge2

    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    
    
    #Calculating x* and y*  

    matrix_1 = np.array([[x1, y1], [x2, y2]])
    matrix_2 = np.array([[x3, y3], [x4, y4]])
    matrix_3 = np.array([[x1, 1], [x2, 1]])
    matrix_4 = np.array([[x3, 1], [x4, 1]])
    matrix_5 = np.array([[y1, 1], [y2, 1]])
    matrix_6 = np.array([[y3, 1], [y4, 1]])
    
    
    
    x_star_matrix =np.array([[determinant(matrix_1), determinant(matrix_3)], [determinant(matrix_2), determinant(matrix_4)]]) 
    y_star_matrix =np.array([[determinant(matrix_1), determinant(matrix_5)], [determinant(matrix_2), determinant(matrix_4)]])
    denom_matrix = np.array([[determinant(matrix_3), determinant(matrix_5)], [determinant(matrix_4), determinant(matrix_6)]])
    
    denom= determinant(denom_matrix)
    denom_x = determinant(x_star_matrix)
    denom_y = determinant(y_star_matrix)
    
    
    if denom != 0:
        x_star = denom_x/denom 
        y_star = denom_y/denom_matrix
        
        
        if x_star < min(x1, x2, x3, x4) or x_star > max(x1, x2, x3, x4) or y_star < min(y1, y2, y3, y4) or y_star > max(y1, y2, y3, y4):
            return None
        
        return x_star, y_star
    
    else:
        return None
    
    
    
main()
