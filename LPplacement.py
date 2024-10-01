import pulp
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from AstarPathAlgorithm import *
from SimplifyPath import *

def linear_optimization_problem(objects, connections, grid_size, height, width, padding):
    #create a PuLP problem minimization
    prob = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)

    #parallization
    solver = pulp.PULP_CBC_CMD(msg=True, threads=10)
    # Decision variables: x and y coordinates
    x = pulp.LpVariable.dicts("x", objects, 0, grid_size-1, cat='Integer')
    y = pulp.LpVariable.dicts("y", objects, 0, grid_size-1, cat='Integer')

    #Decision variables: Minimize perimeter length
    x_min = pulp.LpVariable("x_min", lowBound=0)
    x_max = pulp.LpVariable("x_max", lowBound=0)
    y_min = pulp.LpVariable("y_min", lowBound=0)
    y_max = pulp.LpVariable("y_max", lowBound=0)

    rotated_width = {}
    rotated_height = {}
    #Rotation constraint
    for o1 in objects:
        # Decision variables: rotation
        r0 = pulp.LpVariable(f"r0_{o1}", cat='Binary')
        r90 = pulp.LpVariable(f"r90_{o1}", objects, cat='Binary')
        r180 = pulp.LpVariable(f"r180_{o1}", objects, cat='Binary')
        r270 = pulp.LpVariable(f"r270_{o1}", objects, cat='Binary')

        prob += r0 + r90 + r180 + r270 == 1, f"OneRotation_object_{o1}"
        rotated_width[o1] = r0 * width[o1] + r90 * height[o1] + r180 * width[o1] + r270 * height[o1]
        rotated_height[o1] = r0* height[o1] + r90 * width[o1] + r180 * height[o1] + r270 * width[o1]


    d_x = {}
    d_y = {}
    for o1,o2 in connections:
        d_x[(o1, o2)] = pulp.LpVariable(f"d_x_{o1}_{o2}", 0)
        d_y[(o1, o2)] = pulp.LpVariable(f"d_y_{o1}_{o2}", 0)

        prob += d_x[(o1, o2)] >= x[o1] - x[o2]
        prob += d_x[(o1, o2)] >= x[o2] - x[o1]

        prob += d_y[(o1, o2)] >= y[o1] - y[o2]
        prob += d_y[(o1, o2)] >= y[o2] - y[o1]


    #prob+= pulp.lpSum([d_x[(o1,o2)] + d_y[(o1,o2)] for o1,o2 in connections]), "totalWireLength"
    #Add constraints, e.g. no overlap
    m = grid_size
    for o1 in objects:
        for o2 in objects:
            if o1 != o2:
                z1 = pulp.LpVariable(f"z1_{o1}_{o2}", cat='Binary')
                z2 = pulp.LpVariable(f"z2_{o1}_{o2}", cat='Binary')
                z3 = pulp.LpVariable(f"z3_{o1}_{o2}", cat='Binary')
                z4 = pulp.LpVariable(f"z4_{o1}_{o2}", cat='Binary')

                prob += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{o1}_{o2}"

                prob += x[o1] + rotated_width[o1] + padding <= x[o2] + m * (1- z1), f"LeftOf_{o1}_{o2}"
                prob += x[o2] + rotated_width[o2]  + padding <= x[o1] + m * (1- z2), f"RightOf_{o1}_{o2}"
                prob += y[o1] + rotated_height[o1]  + padding<= y[o2] + m * (1- z3), f"Below_{o1}_{o2}"
                prob += y[o2] + rotated_height[o2] + padding <= y[o1] + m * (1- z4), f"Above_{o1}_{o2}"

                prob += x[o1] + rotated_width[o1] <= grid_size
                prob += x[o2] + rotated_width[o2] <= grid_size
                prob += y[o1] + rotated_height[o1] <= grid_size
                prob += y[o2] + rotated_height[o2] <= grid_size

                prob += x_max >= x[o1]
                prob += x_max >= x[o2]
                prob += x_min <= x[o2]
                prob += x_min <= x[o1]

                prob += y_max >= y[o1]
                prob += y_max >= y[o2]
                prob += y_min <= y[o2]
                prob += y_min <= y[o1]

    #prob += (x_max-x_min)+(x_max-x_min)+(y_max-y_min)+(y_max-y_min), "perimeterLength"
    prob+= pulp.lpSum([d_x[(o1,o2)] + d_y[(o1,o2)] for o1,o2 in connections])+(x_max-x_min)+(x_max-x_min)+(y_max-y_min)+(y_max-y_min), "totalWireLength"
    prob.solve(solver)

    # Display results

    print(f"Status: {pulp.LpStatus[prob.status]}")

    for obj in objects:
        print(f"Object {obj} is placed at ({pulp.value(x[obj])}, {pulp.value(y[obj])})")


    # total wire length

    total_length = pulp.value(prob.objective)
    print(f"Total wire length: {total_length}")

    return x, y, rotated_width, rotated_height



def draw_result(grid_size, objects, paths, height, width, x, y):
    #set up plot
    fix, ax = plt.subplots(figsize=(10,10))
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)

    #draw grid

    for i in range(grid_size +1):
        ax.axhline(i, lw=0.5, color='gray', zorder = 0)
        ax.axvline(i, lw=0.5, color='gray', zorder = 0)

    for obj in objects:
        print(f"x: {pulp.value(x[obj])}, y: {pulp.value(y[obj])} ")
        rect = patches.Rectangle((pulp.value(x[obj]), pulp.value(y[obj])), pulp.value(width[obj]), pulp.value(height[obj]), linewidth = 1, edgecolor='blue', facecolor = 'red')

        ax.add_patch(rect)
        ax.text(pulp.value(x[obj]) + pulp.value(width[obj])/2, pulp.value(y[obj]) + pulp.value(height[obj])/2, obj, ha='center', va='center', fontsize=12, color='black')

    #for o1, o2 in paths:
     #   x1 = pulp.value(x[o1]) + pulp.value(width[o1])/2
      #  y1 = pulp.value(y[o1]) + pulp.value(height[o1]) / 2
       # x2 = pulp.value(x[o2]) + pulp.value(width[o2]) / 2
        #y2 = pulp.value(y[o2]) + pulp.value(height[o2]) / 2

        #ax.plot([x1,x2], [y1,y2], 'r--', lw=2)
    colors = ['blue', 'green', 'cyan', 'magenta', 'black', 'yellow']
    i = 0
    for path in paths:

        x_coord, y_coord = zip(*path)
        ax.plot(x_coord, y_coord, color = colors[i], lw=2)
        i+=1
        if i == len(colors) -1:
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
                    if int(pulp.value(xpos[obj]) + int(pulp.value(width[obj])) // 2) == x and int(pulp.value(ypos[obj])) + int(pulp.value(height[obj])) // 2 == y:
                        grid[-1].append(1)
                        value_appended = True
                else:
                    if pulp.value(xpos[obj]) == x and pulp.value(ypos[obj]) == y:
                        grid[-1].append(1)
                        value_appended = True
                        break
                    elif pulp.value(xpos[obj])<= x <= pulp.value(xpos[obj])+pulp.value(width[obj])-1 and pulp.value(ypos[obj])<= y <= pulp.value(ypos[obj])+pulp.value(height[obj])-1:
                        grid[-1].append(1)
                        value_appended = True
                        break
            if not value_appended:
                grid[-1].append(0)
            else:
                value_appended = False



    return grid


def initiate_astar(grid, x, y, width, height, connections, center):
    path = []

    for connect in connections:
        if center:
            start = (int(pulp.value(x[connect[0]]) + pulp.value(width[connect[0]])//2), int(pulp.value(y[connect[0]])+ pulp.value(height[connect[0]]) //2))
            end = (int(pulp.value(x[connect[1]])+ pulp.value(width[connect[1]]) //2) , int(pulp.value(y[connect[1]]) + pulp.value(height[connect[1]]) //2))
            print(start, end)
        else:
            start = (int(pulp.value(x[connect[0]])) , int(pulp.value(y[connect[0]])))
            end = (int(pulp.value(x[connect[1]])), int(pulp.value(y[connect[1]])))
        if start[0] > end[0]:
            path.append(astar(grid, end, start))
        else:
            path.append(astar(grid, start, end))


    return path






