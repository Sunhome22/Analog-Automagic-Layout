from tkinter.font import names
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from AstarPathAlgorithm import *
from SimplifyPath import *
from LPplacement import *
from circuit_components import *
from json_converter import load_from_json, save_to_json


@dataclass
class Connection:
    starting_comp: str
    starting_area: str
    end_comp: str
    end_area: str
    net: str

    def __init__(self, starting_comp: str, starting_area: str, end_comp: str, end_area: str, net: str):
        self.starting_comp = starting_comp
        self.starting_area = starting_area
        self.end_comp = end_comp
        self.end_area = end_area
        self.net = net

def draw_result(grid_size, objects, paths, height, width, x, y):
    # set up plot
    fix, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)

    # draw grid

    for i in range(grid_size + 1):
        ax.axhline(i, lw=0.5, color='gray', zorder=0)
        ax.axvline(i, lw=0.5, color='gray', zorder=0)

    for obj in objects:
        print(f"x: {pulp.value(x[obj])}, y: {pulp.value(y[obj])} ")
        rect = patches.Rectangle((pulp.value(x[obj]), pulp.value(y[obj])), pulp.value(width[obj]),
                                 pulp.value(height[obj]), linewidth=1, edgecolor='blue', facecolor='red')

        ax.add_patch(rect)
        ax.text(pulp.value(x[obj]) + pulp.value(width[obj]) / 2, pulp.value(y[obj]) + pulp.value(height[obj]) / 2, obj,
                ha='center', va='center', fontsize=12, color='black')

    colors = ['blue', 'green', 'cyan', 'magenta', 'black', 'yellow']
    i = 0
    for path in paths:

        x_coord, y_coord = zip(*path)
        ax.plot(x_coord, y_coord, color=colors[i], lw=2)
        i += 1
        if i == len(colors) - 1:
            i = 0

    plt.title('OBJ placement')
    plt.show()


def generate_grid(grid_size, objects, height, width, xpos, ypos, center):
    grid = []
    value_appended = False

    for y in range(grid_size):
        grid.append([])
        for x in range(grid_size):
            for obj in objects:
                if center:
                    if int(pulp.value(xpos[obj]) + int(pulp.value(width[obj])) // 2) == x and int(
                            pulp.value(ypos[obj])) + int(pulp.value(height[obj])) // 2 == y:
                        grid[-1].append(1)
                        value_appended = True
                else:
                    if pulp.value(xpos[obj]) == x and pulp.value(ypos[obj]) == y:
                        grid[-1].append(1)
                        value_appended = True
                        break
                    elif pulp.value(xpos[obj]) <= x <= pulp.value(xpos[obj]) + pulp.value(
                            width[obj]) - 1 and pulp.value(ypos[obj]) <= y <= pulp.value(ypos[obj]) + pulp.value(
                            height[obj]) - 1:
                        grid[-1].append(1)
                        value_appended = True
                        break
            if not value_appended:
                grid[-1].append(0)
            else:
                value_appended = False

    return grid


def get_key(val, dict):
    for key, value in dict.items():
        if val == value:
            return key

    return "key doesn't exist"

def remove_duplicates_from_list(dict):
    temp = {}

    for key, value in dict.items():
        if value not in temp.values():
            temp[key] = value

    return temp

def local_nets(local_connection_list):
    local_connection_nets = {}

    for local_conn in local_connection_list:

        local_connection_nets[local_connection_list[local_conn].starting_comp]={ local_connection_list[local_conn].starting_area + local_connection_list[local_conn].end_area}
    return local_connection_nets

def connection_list(objects):

    object_list = objects
    connections = {}
    local_connections = {}
    single_connection = {}
    i = 0
    for  obj in object_list:

        if not isinstance(obj, Pin):
            ports = obj.schematic_connections

            for key in ports:
                for key2 in ports:

                    if key != key2:
                        entry = [{'starting_comp': obj.number_id,  'starting_area': key, 'end_comp': obj.number_id, 'end_area': key2, 'net': ports[key]},
                                 {'starting_comp': obj.number_id,  'starting_area': key2, 'end_comp': obj.number_id, 'end_area': key, 'net': ports[key]}]
                        if ports[key] == ports[key2] and not any(isinstance(obj, Connection) and obj.__dict__ == target for target in entry for obj in local_connections.values()):
                            local_connections[i]= Connection(obj.number_id, key, obj.number_id, key2, ports[key])
                            i+=1
            local_connection_area = local_nets(local_connections)
    i=0
    for obj in object_list:
        for obj2 in object_list:
            if not isinstance(obj, Pin) and not isinstance(obj2, Pin):

                ports = obj.schematic_connections
                ports2 = obj2.schematic_connections


                if obj != obj2 and obj.cell == obj2.cell:

                    for key in ports:
                        element_appended = False
                        for key2 in ports2:
                            key_u1 = key
                            key_u2 = key2
                            if ports[key] == ports2[key2]:

                                for local_con in local_connections:

                                    area = local_connections[local_con].starting_area + local_connections[local_con].end_area

                                    if obj.number_id == local_connections[local_con].starting_comp and (key == area[0] or key == area[1]):
                                        key_u1 = area


                                    if obj2.number_id == local_connections[local_con].starting_comp and (key2 == area[0] or key2 == area[1]):
                                        key_u2 = area


                                entry = [{'starting_comp': obj.number_id, 'starting_area': key_u1, 'end_comp': obj2.number_id,
                                      'end_area': key_u2, 'net': ports[key]},
                                     {'starting_comp': obj2.number_id, 'starting_area': key_u2, 'end_comp': obj.number_id,
                                      'end_area': key_u1, 'net': ports[key]}]

                                if not any(isinstance(obj, Connection) and obj.__dict__ == target for target in entry for obj in connections.values()):

                                    connections[i] = Connection(obj.number_id,key_u1,obj2.number_id, key_u2, ports[key])
                                    i+=1
                                element_appended = True


                        if not element_appended:
                            single_connection[-1] =  Connection(obj.number_id, key, "", "", ports[key])


    connections = remove_duplicates_from_list(connections)


    return single_connection, local_connections, connections



def main():
    # Define grid size and objects

    grid_size = 10000

    components = load_from_json(file_name='components')

    single_connection, local_connections, connections = connection_list(components)

    print(connections)
    run = True
    center = True
    clean_path = True

    if run:
    # space between objects
        print("[INFO]: Starting Linear Optimization")
        result =  LinearOptimizationSolver(components, connections, local_connections, grid_size)
        objects = result.initiate_solver()
        save_to_json(objects, file_name="Result50CV3")
        print("[INFO]: Finished Linear Optimization")
        print("[INFO]: Starting Grid Generation")
        #grid = generate_grid(grid_size, objects, new_height, new_width, x, y, center)
        print("[INFO]: Finished Grid Generation")
        print("[INFO]: Starting Initiate A*")
        #path = initiate_astar(grid, x, y, new_width, new_height, connections, center)
        print("[INFO]: Finished A*")
        print("[INFO]: Starting Simplifying Paths")
        # cleaned_paths = simplify_all_paths(path)
        print("[INFO]: Finished Simplifying Paths")
        print("[INFO]: Starting Drawing Results")
        #if clean_path:
        #  draw_result(grid_size, objects, cleaned_paths, new_height, new_width, x, y)
        #else:
        # draw_result(grid_size, objects, path, new_height, new_width, x, y)
        print("[INFO]: Finished Drawing Results")



main()