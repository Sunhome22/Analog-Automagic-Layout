from circuit.circuit_components import Pin, CircuitCell


def generate_grid(grid_size, objects):
    grid = []
    value_appended = False
    OFFSET_X = 184
    OFFSET_Y = 128


    i = 0
    p = 0
    f = 0
    for y in range(grid_size//10):
        grid.append([])
        for x in range(grid_size//10):
            for obj in objects:

                if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
                    conditions = [
                        (obj.transform_matrix.c + obj.bounding_box.x2 + OFFSET_X/2)/10 >= x,
                        (obj.transform_matrix.c - OFFSET_X/2)/10  <= x,
                         (obj.transform_matrix.f + obj.bounding_box.y2 + OFFSET_Y/2)/10>= y,
                          (obj.transform_matrix.f - OFFSET_Y/2)/10 <= y
                    ]



                    if all(conditions):
                        i += 1
                        grid[-1].append(1)
                        value_appended = True
                        break

            if not value_appended:
                grid[-1].append(0)
                p += 1
            else:

                value_appended = False
            f += 1


    # for row in grid:
    #     print(row)
    print(f"Appended 1's: {i}")
    print(f"Appended 0's: {p}")
    print(f"Appended 1and0's: {f}")
    return grid