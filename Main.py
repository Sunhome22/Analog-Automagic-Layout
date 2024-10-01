from tkinter.font import names

from AstarPathAlgorithm import *
from SimplifyPath import *
from LPplacement import *

class objects:
    type = "Transistor"
    def __init__(self, name, width, height, ports, connections):
        self.name = name
        self.width = width
        self.height = height
        self.ports = ports
        self.connections = connections




def main():
    # Define grid size and objects

    grid_size = 100
    padding = 10

    # Standard ports

    p = {"S" : (5, 10), "G" : (0, 5), "D" : (0, 5)}



    #transistors
    M1 = objects("M1", 10, 10, p, {"S" : "M2: S"} )
    M2 = objects("M2", 10, 10, p, {"S": "M3: S"})
    M3 = objects("M3", 10, 10, p, {"S": "M4: S"})
    M4 = objects("M4", 10, 10, p, {"S": "M5: S"})
    M5 = objects("M5", 10, 10, p, {"S": "M6: S"})
    M6 = objects("M6", 10, 10, p, {"S": "M7: S"})
    M7 = objects("M7", 10, 10, p, {"S": "M8: S"})
    M8 = objects("M8", 10, 10, p, {"S": "M1: S"})


    object = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    connections = [('A', 'B'), ('B', 'C'), ('C', 'D'), ('E', 'A'), ('F', 'G'), ('H', 'D')]
    center = True
    clean_path = True
    # Object parameters

    height = {'A': 10, 'B': 10, 'C': 10, 'D': 10, 'E': 10, 'F': 10, 'G': 10, 'H': 10}
    width = {'A': 20, 'B': 20, 'C': 20, 'D': 20, 'E': 20, 'F': 20, 'G': 20, 'H': 20}

    # space between objects
    print("[INFO]: Starting Linear Optimization")
    x, y, new_width, new_height = linear_optimization_problem(objects, connections, grid_size, height, width, padding)
    print("[INFO]: Finished Linear Optimization")
    print("[INFO]: Starting Grid Generation")
    grid = generate_grid(grid_size, objects, new_height, new_width, x, y, center)
    print("[INFO]: Finished Grid Generation")
    print("[INFO]: Starting Initiate A*")
    path = initiate_astar(grid, x, y, new_width, new_height, connections, center)

    print("[INFO]: Finished A*")
    print("[INFO]: Starting Simplifying Paths")
    cleaned_paths = simplify_all_paths(path)
    i= 0


    print("[INFO]: Finished Simplifying Paths")

    print("[INFO]: Starting Drawing Results")
    if clean_path:
        draw_result(grid_size, objects, cleaned_paths, new_height, new_width, x, y)
    else:

        draw_result(grid_size, objects, path, new_height, new_width, x, y)
    print("[INFO]: Finished Drawing Results")



main()