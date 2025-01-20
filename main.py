from os.path import pathsep

from astar.a_star_test import initiate_astar
from draw_result.draw import draw_result
from linear_optimization.linear_optimization_test import *
from circuit.circuit_components import *
from json_tool.json_converter import load_from_json, save_to_json
from grid.generate_grid import generate_grid
from connections.connections import *
from traces.write_trace_test import write_traces



def main():
    # Define grid size and objects
    grid_size = 3000
    components = load_from_json(file_name='json_tool/components.json')
    single_connection, local_connections, connections = connection_list(components)
    overlap_dict = overlap_transistors(components)
    linear_optimization_enabled = True
    solver_enabled = True
    if solver_enabled:
    # space between objects
        print("[INFO]: Starting Linear Optimization")
        if linear_optimization_enabled:
            result =  LinearOptimizationSolver(components, connections, local_connections, grid_size, overlap_dict)
            objects = result.initiate_solver()
            save_to_json(objects, file_name="Results/ResultV21Mirrored5.json")
        else:
            objects = load_from_json(file_name="Results/ResultV21Mirrored4.json")
        print("[INFO]: Finished Linear Optimization")
        print("[INFO]: Starting Grid Generation")
        grid,  area_coordinates, used_area, port_coord = generate_grid(grid_size, objects)
        print("[INFO]: Finished Grid Generation")
        print("[INFO]: Starting Initiate A*")
        path, path_names = initiate_astar(grid, connections, local_connections, objects, area_coordinates)
        print("[INFO]: Finished A*")

        write_traces(objects, path, path_names, port_coord)
        print("[INFO]: Starting Simplifying Paths")

        print("[INFO]: Finished Simplifying Paths")
        print("[INFO]: Starting Drawing Results")

        draw_result(grid_size, objects, path, used_area)
        print("[INFO]: Finished Drawing Results")




if __name__ == "__main__":
    main()