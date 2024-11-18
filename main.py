import matplotlib.pyplot as plt
import matplotlib.patches as patches
from linear_optimization.linear_optimization_test import *
from circuit.circuit_components import *
from json_tool.json_converter import load_from_json, save_to_json
import pulp

from path.a_star import initiate_astar
from path.simplify_path import simplify_all_paths


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

def draw_result(grid_size, objects, connections):
    # set up plot
    fix, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)



    # draw grid

    for i in range(grid_size + 1):
        ax.axhline(i, lw=0.5, color='gray', zorder=0)
        ax.axvline(i, lw=0.5, color='gray', zorder=0)

    for obj in objects:
        if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
            print(f"x: {obj.transform_matrix.c}", f"y: {obj.transform_matrix.f} ")
            rect = patches.Rectangle((obj.transform_matrix.c, obj.transform_matrix.f), obj.bounding_box.x2, obj.bounding_box.y2, linewidth=1, edgecolor='blue', facecolor='red')

            ax.add_patch(rect)
            ax.text(obj.transform_matrix.c + (obj.bounding_box.x2 / 2), obj.transform_matrix.f + (obj.bounding_box.y2 / 2), obj.number_id,
                ha='center', va='center', fontsize=12, color='black')


    for p in connections.values():
        start = p.starting_comp
        end = p.end_comp
        x_values = []
        y_values = []

        for obj in objects:
            if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
                if obj.number_id == start:

                    x_values.append(obj.transform_matrix.c + (obj.bounding_box.x2/2))
                    y_values.append(obj.transform_matrix.f + (obj.bounding_box.y2 / 2))
                    break
        for obj in objects:
            if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
                if obj.number_id == end:
                    x_values.append(obj.transform_matrix.c + (obj.bounding_box.x2/2))
                    y_values.append(obj.transform_matrix.f + (obj.bounding_box.y2 / 2))
                    break
        plt.plot(x_values, y_values)

        plt.plot([grid_size//2, grid_size//2], [0, grid_size])




    plt.title('OBJ placement')
    plt.savefig('Results/ResultV21Mirrored5.png')


def generate_grid(grid_size, objects):
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

        if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
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
            if not isinstance(obj, Pin) and not isinstance(obj2, Pin) and not isinstance(obj, CircuitCell) and not isinstance(obj2, CircuitCell):

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


def _overlap_transistors(comp):
    n = []
    p = []
    dict = {}
    for obj in comp:
        if isinstance(obj, Transistor):
            if obj.type == "pmos":
                p.append(obj)
            elif obj.type== "nmos":
                n.append(obj)
            else:
                print("[ERROR] Could not find Transistor type")

    n_duplicate = n[:]
    p_duplicate = p[:]
    top = []
    side = []



    for i in n:
        for j in n_duplicate:
            if i != j:

                if (i.bounding_box.x2 - i.bounding_box.x1) == (j.bounding_box.x2 - j.bounding_box.x1):
                    top.append([i.number_id, j.number_id])

                if (i.bounding_box.y2 - i.bounding_box.y1) == (j.bounding_box.y2 - j.bounding_box.y1):
                    side.append([i.number_id, j.number_id])
        n_duplicate.remove(i)
    for k in p:
        for l in p_duplicate:
            if k != l:

                if (k.bounding_box.x2 - k.bounding_box.x1) == (l.bounding_box.x2 - l.bounding_box.x1):
                    top.append([k.number_id, l.number_id])

                if (k.bounding_box.y2 - k.bounding_box.y1) == (l.bounding_box.y2 - l.bounding_box.y1):
                    side.append([k.number_id, l.number_id])
        p_duplicate.remove(k)

    dict["side"] = side
    dict["top"] = top


    return dict


def diff_components(components):
    diff_pairs = []
    comp = components[:]
    for obj in components:
        for obj1 in comp:
            if obj.group == obj1.group and "diff" in obj.type:
                diff_pairs.append([obj, obj1])
        comp.remove(obj)
    return diff_pairs



def main():
    # Define grid size and objects

    grid_size = 3000

    components = load_from_json(file_name='json_tool/components.json')

    single_connection, local_connections, connections = connection_list(components)

    overlap_dict = _overlap_transistors(components)

    run = True
    clean_path = True

    if run:
    # space between objects
        print("[INFO]: Starting Linear Optimization")
        result =  LinearOptimizationSolver(components, connections, local_connections, grid_size, overlap_dict)
        objects = result.initiate_solver()
        save_to_json(objects, file_name="Results/ResultV21Mirrored5.json")
        print("[INFO]: Finished Linear Optimization")
        print("[INFO]: Starting Grid Generation")
        grid = generate_grid(grid_size, objects)
        print("[INFO]: Finished Grid Generation")
        print("[INFO]: Starting Initiate A*")
        path = initiate_astar(grid,  connections, objects)
        print("[INFO]: Finished A*")
        print("[INFO]: Starting Simplifying Paths")
        cleaned_paths = simplify_all_paths(path)
        print("[INFO]: Finished Simplifying Paths")
        print("[INFO]: Starting Drawing Results")
        if clean_path:
            draw_result(grid_size, objects, cleaned_paths)
        else:
            draw_result(grid_size, objects, connections)
        print("[INFO]: Finished Drawing Results")



main()