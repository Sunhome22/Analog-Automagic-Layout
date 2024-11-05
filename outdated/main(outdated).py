from outdated.LPplacementoutdated import LinearOptimizationSolver1
def main():
    # Define grid size and objects

    grid_size = 10000
    padding = 0





    #transistors


    object = ['x1', 'x2']
    connections = [('x1', 'x2')]
    center = True
    clean_path = True
    # Object parameters

    height = {'x1': 11, 'x2': 12}
    width = {'x1': 22, 'x2': 23}

    # space between objects
    print("[INFO]: Starting Linear Optimization")
    lop = LinearOptimizationSolver1(object, connections, grid_size, height, width, padding)

    x, y, new_width, new_height = lop.initiate_solver()
    print("[INFO]: Finished Linear Optimization")
    print("[INFO]: Starting Grid Generation")
    #grid = generate_grid(grid_size, objects, new_height, new_width, x, y, center)
    print("[INFO]: Finished Grid Generation")
    print("[INFO]: Starting Initiate A*")
   # path = initiate_astar(grid, x, y, new_width, new_height, connections, center)

    print("[INFO]: Finished A*")
    print("[INFO]: Starting Simplifying Paths")
    #cleaned_paths = simplify_all_paths(path)
    i= 0


    print("[INFO]: Finished Simplifying Paths")

    print("[INFO]: Starting Drawing Results")
   # if clean_path:
    #    draw_result(grid_size, objects, cleaned_paths, new_height, new_width, x, y)
   # else:

    #    draw_result(grid_size, objects, path, new_height, new_width, x, y)
   # print("[INFO]: Finished Drawing Results")



main()