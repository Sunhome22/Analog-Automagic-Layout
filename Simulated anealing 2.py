import random
import math
import matplotlib.pyplot as plt
import numpy as np
import decimal


random_move_count = 0
shift_pos_count = 0
count_left = 0
count_right = 0
count_up = 0
count_down = 0

def initialize_objects(num_objects, grid_width, grid_height):
       # """Initialize objects with random non-overlapping positions."""
    positions = set()
    objects = []
    while len(objects) < num_objects:
        position = (random.randint(0, grid_width - 1), random.randint(0, grid_height - 1))
        if position not in positions:
            objects.append(position)
            positions.add(position)

            print(f"[INFO:] {positions}")
    return objects

def manhattan_distance( obj1, obj2):

    return abs(obj1[0] - obj2[0]) + abs(obj1[1] - obj2[1])


def determinant(matrix):
    return np.linalg.det(matrix)


def intersection(edge1, edge2):
    p1, p2 = edge1
    p3, p4 = edge2

    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    # Calculating x* and y*

    matrix_1 = np.array([[x1, y1], [x2, y2]])
    matrix_2 = np.array([[x3, y3], [x4, y4]])
    matrix_3 = np.array([[x1, 1], [x2, 1]])
    matrix_4 = np.array([[x3, 1], [x4, 1]])
    matrix_5 = np.array([[y1, 1], [y2, 1]])
    matrix_6 = np.array([[y3, 1], [y4, 1]])

    x_star_matrix = np.array(
        [[determinant(matrix_1), determinant(matrix_3)], [determinant(matrix_2), determinant(matrix_4)]])
    y_star_matrix = np.array(
        [[determinant(matrix_1), determinant(matrix_5)], [determinant(matrix_2), determinant(matrix_4)]])
    denominator_matrix = np.array(
        [[determinant(matrix_3), determinant(matrix_5)], [determinant(matrix_4), determinant(matrix_6)]])

    denominator = determinant(denominator_matrix)
    denominator_x = determinant(x_star_matrix)
    denominator_y = determinant(y_star_matrix)

    if denominator != 0:
        x_star = denominator_x / denominator
        y_star = denominator_y / denominator

        if (x_star < min(x1, x2, x3, x4) and x_star > max(x1, x2, x3, x4) and y_star < min(y1, y2, y3, y4) and y_star > max(y1, y2, y3, y4)).any():
            return False

        return True

    else:
        return False


def count_intersections(objects, connections):
       # #Count the number of intersections between edges."""


        intersections = 0
        edges = [(objects[a], objects[b]) for a, b in connections]
        for i in range(len(edges)):
            for j in range(i + 1, len(edges)):
                if intersection(edges[i], edges[j]):
                    intersections += 1
        return intersections

def total_edge_length(objects, connections):
    #Calculate the total edge length (L) as the sum of Manhattan distances between connected objects."""
    total_length = 0
    for a, b in connections:
        total_length += manhattan_distance(objects[a], objects[b])
    return total_length

def total_squared_edge_length(objects, connections):
    #Calculate the total squared edge length (S) as the sum of squared Manhattan distances between connected objects."""
    total_squared_length = 0
    for a, b in connections:
        dist = manhattan_distance(objects[a], objects[b])
        total_squared_length += dist ** 2
    return total_squared_length

def calculate_euclidean_length(obj1, obj2):
    return math.sqrt((obj1[0]-(obj2[0]))**2 + (obj1[1]-obj2[1])**2)

def total_euclidean_length(objects, connections):
    euclidean_length=0
    for a,b in connections:
        euclidean_length+= calculate_euclidean_length(objects[a], objects[b])
    return euclidean_length

def objective_function(objects, alpha, beta, theta, eta, connections):
    #Calculate the objective function F(G) = alpha*N + beta*L + theta*S."""

    n = count_intersections(objects, connections)
    l = total_edge_length(objects, connections)
    s = total_squared_edge_length(objects, connections)
    e = total_euclidean_length(objects, connections)
    return alpha * n  + beta * l  + theta * s + e * eta

def shift_pos(current_position):
    global count_left
    global count_right
    global count_up
    global count_down
    direction = random.randrange(0, 4)

    if direction == 0:
        new_position = (current_position[0] + 1, current_position[1])
        count_right += 1
    elif direction == 1:
        new_position = (current_position[0] - 1, current_position[1])
        count_left += 1
    elif direction == 2:
        new_position = (current_position[0], current_position[1] + 1)
        count_down += 1
    else:
        new_position = (current_position[0], current_position[1] - 1)
        count_up += 1
    return new_position

def move_pos(grid_width, grid_height):
    return random.randrange(0, grid_width), random.randrange(0, grid_height)

def random_neighbor(objects, grid_width, grid_height, temperature):
    #Generate a neighboring solution by moving one object to a random, non-overlapping position."""
    global random_move_count
    global shift_pos_count
    counter = 0
    new_objects = objects[:]
    positions = set(new_objects)

    # Select a random object to move
    idx = random.randint(0, len(new_objects) - 1)
    current_position = new_objects[idx]

    # Find a new non-overlapping position
    while True:


       # random_move = random.randrange(0, 2)

        #Test

        if temperature >= 5:
            random_move = 0
        else:
            random_move = 1


        if random_move == 0:
            new_position = shift_pos(current_position)
            random_move_count += 1

        else:

            new_position = move_pos(grid_width, grid_height)
            shift_pos_count += 1



        if new_position in positions:

            for i in range(len(new_objects)):
                if new_position == new_objects[i]:
                    new_objects[i] = current_position
                    new_objects[idx] = new_position
                    break
                break
        elif 0 <= new_position[0] <= grid_width - 1 and 0 <= new_position[1] <= grid_height - 1:
                new_objects[idx] = new_position
                break
        else:
            counter +=1

            if counter >= 1000:
                break

    return new_objects


def acceptance_probability(current_cost, new_cost, temperature):
    #Calculate the probability of accepting a worse solution."""
    if new_cost < current_cost:
        return 1.0
    try:
        return decimal.Decimal((current_cost - new_cost) / temperature).exp()
    except:
        return -1

def draw_solution(grid_width, grid_height, objects, connections):
    #Draw the grid, objects, and edges using matplotlib."""
    fig, ax = plt.subplots()

    # Draw grid lines
    for x in range(grid_width + 1):
        ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
    for y in range(grid_height + 1):
        ax.axhline(y, color='gray', linestyle='--', linewidth=0.5)

    # Plot objects
    for i, (x, y) in enumerate(objects):
        ax.plot(x + 0.5, y + 0.5, 'bo', markersize=10)  # Place objects at the center of the grid cells
        ax.text(x + 0.5, y + 0.5, f'{i}', color='white', ha='center', va='center')

    # Plot edges
    for a, b in connections:
        obj_a = objects[a]
        obj_b = objects[b]
        ax.plot([obj_a[0] + 0.5, obj_b[0] + 0.5], [obj_a[1] + 0.5, obj_b[1] + 0.5], 'r-')

    # Set axis limits and labels
    ax.set_xlim(0, grid_width)
    ax.set_ylim(0, grid_height)
    ax.set_xticks(range(grid_width + 1))
    ax.set_yticks(range(grid_height + 1))
    ax.set_aspect('equal')

    plt.gca().invert_yaxis()  # Invert the y-axis to match the traditional grid layout
    plt.show()


def anneal(current_solution, current_cost, grid_width, grid_height, connections, alpha, beta, theta, eta, temperature, cooling_rate, min_temperature):
    #Perform the simulated annealing process."""
    best_cost = current_cost
    best_solution = current_solution
    counter = 0
    given_best = False
    while temperature > min_temperature:

        new_solution = random_neighbor(current_solution, grid_width, grid_height, temperature)
        new_cost = objective_function(current_solution, alpha, beta, theta, eta, connections)

        if new_cost <= best_cost:
            best_cost = new_cost
            best_solution = new_solution

        if acceptance_probability(current_cost, new_cost, temperature) > random.random():

            current_solution = new_solution
            current_cost = new_cost
            counter = 0
            #draw_solution(grid_width, grid_height, current_solution, connections)
        else:
            counter +=1

        if counter >= 1000 and current_solution != best_solution:

            print(f"[INFO] {temperature}")
            counter = 0
            given_best = True
            current_cost = best_cost
            current_solution = best_solution

        temperature *= cooling_rate
            #objects = current_solution

    return current_solution, current_cost, best_solution, best_cost, given_best

def call_annealing(num_objects, grid_width, grid_height,alpha, beta, theta, eta, connections, temperature, cooling_rate, min_temperature ):
    best_solution = initialize_objects(num_objects, grid_width, grid_height)
    best_cost = objective_function(best_solution, alpha, beta, theta, eta, connections)

    counter = 0
    while True:
        counter +=1
        final_solution, final_cost, best_solution, best_cost, given_best = anneal(best_solution, best_cost, grid_width, grid_height,
                                                                          connections, alpha, beta, theta,eta, temperature,cooling_rate, min_temperature)
        print(counter)
        print(f"final_cost: {final_cost}")
        print(f"best_cost: {best_cost}")
        if final_cost <= best_cost and given_best == False:

            return final_solution, final_cost
        elif counter >= 50:
            return best_solution, best_cost
# Example usage
def main():
    grid_width = 100
    grid_height = 100
    num_objects = 20


    connections = [(0, 1), (1, 2), (2, 3), (3, 4), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (0, 12), (1, 13), (2, 14), (3, 15), (4, 16), (5, 17), (6, 18), (7, 19)]  # Example netlist (graph)

    alpha = 10
    beta = 100
    theta = 10
    eta = 100
    temperature = 10000.0  # Initial temperature
    cooling_rate = 0.995  # Rate at which temperature decreases
    min_temperature = 0.1  # Stop when temperature is this lo


    final_solution, final_cost = call_annealing(num_objects, grid_width, grid_height,alpha, beta, theta, eta ,connections, temperature, cooling_rate, min_temperature )



    print(f"Final solution: {final_solution}")
    print(f"Final cost (F(G)): {final_cost}")
    print(f"Random move Count: {random_move_count}")
    print(f"Shift position count: {shift_pos_count}")

    draw_solution(grid_width, grid_height, final_solution, connections)


main()