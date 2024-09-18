import pulp
import matplotlib.pyplot as plt
import matplotlib.patches as patches


def linear_optimization_problem(objects, connections, grid_size, height, width, padding):
    #create a PuLP problem minimization
    prob = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)

    # Decision variables: x and y coordinates
    x = pulp.LpVariable.dicts("x", objects, 0, grid_size-1, cat='Integer')
    y = pulp.LpVariable.dicts("y", objects, 0, grid_size-1, cat='Integer')

    x_min = pulp.LpVariable("x_min", lowBound=0)
    x_max = pulp.LpVariable("x_max", lowBound=0)
    y_min = pulp.LpVariable("y_min", lowBound=0)
    y_max = pulp.LpVariable("y_max", lowBound=0)


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
    M = grid_size
    for o1 in objects:
        for o2 in objects:
            if o1 != o2:
                z1 = pulp.LpVariable(f"z1_{o1}_{o2}", cat='Binary')
                z2 = pulp.LpVariable(f"z2_{o1}_{o2}", cat='Binary')
                z3 = pulp.LpVariable(f"z3_{o1}_{o2}", cat='Binary')
                z4 = pulp.LpVariable(f"z4_{o1}_{o2}", cat='Binary')

                prob += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{o1}_{o2}"

                prob += x[o1] + width[o1] + padding <= x[o2] + M * (1- z1), f"LeftOf_{o1}_{o2}"
                prob += x[o2] + width[o2]  + padding <= x[o1] + M * (1- z2), f"RightOf_{o1}_{o2}"
                prob += y[o1] + height[o1]  + padding<= y[o2] + M * (1- z3), f"Below_{o1}_{o2}"
                prob += y[o2] + height[o2] + padding <= y[o1] + M * (1- z4), f"Above_{o1}_{o2}"

                prob += x[o1] + width[o1] <= grid_size
                prob += x[o2] + width[o2] <= grid_size
                prob += y[o1] + height[o1] <= grid_size
                prob += y[o2] + height[o2] <= grid_size

                prob += x_max >= x[o1]
                prob += x_max >= x[o2]
                prob += x_min <= x[o2]
                prob += x_min <= x[o1]

                prob += y_max >= y[o1]
                prob += y_max >= y[o2]
                prob += y_min <= y[o2]
                prob += y_min <= y[o1]

    #prob += (x_max-x_min)+(x_max-x_min)+(y_max-y_min)+(y_max-y_min), "perimeterLength"
    prob+= pulp.lpSum([d_x[(o1,o2)] + d_y[(o1,o2)] for o1,o2 in connections])+(y_max-y_min)+(y_max-y_min), "totalWireLength"
    prob.solve()

    # Display results

    print(f"Status: {pulp.LpStatus[prob.status]}")

    for obj in objects:
        print(f"Object {obj} is placed at ({pulp.value(x[obj])}, {pulp.value(y[obj])})")


    # total wire length

    total_length = pulp.value(prob.objective)
    print(f"Total wire length: {total_length}")

    return x, y



def draw_result(grid_size, objects, connections, height, width, x, y):
    #set up plot
    fix, ax = plt.subplots(figsize=(10,10))
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)

    #draw grid

    for i in range(grid_size +1):
        ax.axhline(i, lw=0.5, color='gray', zorder = 0)
        ax.axvline(i, lw=0.5, color='gray', zorder = 0)

    for obj in objects:
        rect = patches.Rectangle((pulp.value(x[obj]), pulp.value(y[obj])), width[obj], height[obj], linewidth = 1, edgecolor='blue', facecolor = 'red')

        ax.add_patch(rect)
        ax.text(pulp.value(x[obj]) + width[obj]/2, pulp.value(y[obj]) + height[obj]/2, obj, ha='center', va='center', fontsize=12, color='black')

    for o1, o2 in connections:
        x1 = pulp.value(x[o1]) + width[o1]/2
        y1 = pulp.value(y[o1]) + height[o1] / 2
        x2 = pulp.value(x[o2]) + width[o2] / 2
        y2 = pulp.value(y[o2]) + height[o2] / 2

        ax.plot([x1,x2], [y1,y2], 'r--', lw=2)


    plt.title('OBJ placement')
    plt.show()

def main():
    # Define grid size and objects

    grid_size = 100


    objects = ['A', 'B', 'C', 'D']
    connections = [('A', 'B'), ('B', 'C'), ('C', 'D')]

    # Object parameters

    height = {'A': 10, 'B': 20, 'C': 40, 'D': 10}
    width = {'A': 20, 'B': 10, 'C': 20, 'D': 10}

    # space between objects

    padding = 10

    x, y = linear_optimization_problem(objects, connections, grid_size, height, width, padding)

    draw_result(grid_size, objects, connections, height, width, x, y)


main()