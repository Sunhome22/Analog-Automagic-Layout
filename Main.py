from tkinter.font import names
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from AstarPathAlgorithm import *
from SimplifyPath import *
from LPplacement import *
from circuit_components import *

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


def connection_list(objects):
    con = []
    object_list = objects


    for  obj in object_list:
        ports = obj.schematic_connections

        for key in ports:
            for key2 in ports:

                if key != key2:
                    if ports[key] == ports[key2]:
                        con.append([obj.name, key, obj.name, key2, ports[key]])



        for obj2 in object_list:
            ports2 = obj2.schematic_connections
            ports = obj.schematic_connections

            if obj != obj2:

                for key in ports:
                    for key2 in ports2:

                        if ports[key] == ports2[key]:

                            con.append([obj.name,key,obj2.name, key2, ports[key]])
                            print(con)
        object_list.pop(0)



def main():
    # Define grid size and objects

    grid_size = 10000
    padding = 0

    M1 = Transistor(name='x1',
schematic_connections={'D': 'IBNS_20U', 'G': 'IBPS_2U', 'S': 'VSS', 'B': 'VSS'},
layout_name='JNWATR_NCH_12C1F2', layout_library='JNW_ATR_SKY130A',
layout_ports=[LayoutPort(type='G', layer='m1', area_params=[80, 180, 112, 220]),
LayoutPort(type='S', layer='m1', area_params=[144, 300,240, 340]),
LayoutPort(type='B', layer='locali', area_params=[-48, 180, 48, 220]),
LayoutPort(type='D', layer='m1', area_params=[592, 20, 688, 60])],
transform_matrix=TransformMatrix(a=1, b=0, c=0, d=0, e=1, f=0),
bounding_box=RectArea(x1=0, y1=0, x2=832, y2=400))

    M2 = Transistor(name='x2',
schematic_connections={'D': 'IBPS_2U', 'G': 'IBPS_2U', 'S': 'VSS', 'B': 'VSS'},
layout_name='JNWATR_NCH_2C1F2', layout_library='JNW_ATR_SKY130A',
layout_ports=[LayoutPort(type='G', layer='m1', area_params=[80, 180, 112, 220]),
LayoutPort(type='S', layer='m1', area_params=[144, 300, 240, 340]),
LayoutPort(type='B', layer='locali', area_params=[-48, 180, 48, 220]),
LayoutPort(type='D', layer='m1', area_params=[272, 20, 368, 60])],
transform_matrix=TransformMatrix(a=1, b=0, c=0, d=0, e=1, f=0),
bounding_box=RectArea(0, 0, 512, 400))


    objects = [M1, M2]
    connection_list(objects)
    connections = [('A', 'B'), ('B', 'C'), ('C','D'), ('E','F'), ('F','G'), ('G','H'), ('H','I'), ('D','B'), ('A','I'), ('F','C')]
    center = True
    clean_path = True
    # Object parameters

    height = {'A': 10, 'B': 10, 'C': 10, 'D': 10, 'E': 10, 'F': 10, 'G': 10, 'H': 10, 'I': 10}
    width = {'A': 10, 'B': 10, 'C': 10, 'D': 10, 'E': 10, 'F': 10, 'G': 10, 'H': 10, 'I': 10}

    # space between objects
    print("[INFO]: Starting Linear Optimization")
    #result =  LinearOptimizationSolver(objects, connections, grid_size, height, width, padding)
   # x, y, new_width, new_height = result.initiate_solver()
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