from matplotlib import pyplot as plt, patches

from circuit.circuit_components import Pin, CircuitCell, Trace


def draw_result(grid_size, objects, connections):
    # set up plot
    fix, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, grid_size)
    ax.set_ylim(0, grid_size)
    path = True



    # draw grid

    for i in range(grid_size + 1):
        ax.axhline(i, lw=0.5, color='gray', zorder=0)
        ax.axvline(i, lw=0.5, color='gray', zorder=0)

    for obj in objects:
        if not isinstance(obj, (Pin, CircuitCell, Trace)):

            rect = patches.Rectangle((obj.transform_matrix.c, obj.transform_matrix.f), obj.bounding_box.x2, obj.bounding_box.y2, linewidth=1, edgecolor='blue', facecolor='red')

            ax.add_patch(rect)
            ax.text(obj.transform_matrix.c + (obj.bounding_box.x2 / 2), obj.transform_matrix.f + (obj.bounding_box.y2 / 2), obj.number_id,
                ha='center', va='center', fontsize=12, color='black')

    if not path:
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
    else:
        scaled_points = []
        for p in connections:
            scaled_points.append( [(x * 10, y * 10) for x, y in p])
        for con in scaled_points:

            x_coords, y_coords = zip(*con)
            plt.plot(x_coords, y_coords, marker = 'o', linestyle = '-')




    plt.title('OBJ placement')
    plt.savefig('Results/ResultV3LocalRoute.png')