from circuit.circuit_components import Pin, CircuitCell
import math


def _port_area(objects, grid_size, leeway_x, leeway_y):
    port_area = []
    port_scaled_coord = {}
    port_coord = {}
    used_area = [grid_size, grid_size, 0, 0]

    for obj in objects:

        if not isinstance(obj, (Pin, CircuitCell)):
            if used_area[0] > obj.transform_matrix.c:
                used_area[0] = obj.transform_matrix.c

            if used_area[2] < obj.transform_matrix.c + obj.bounding_box.x2:
                used_area[2] = obj.transform_matrix.c + obj.bounding_box.x2

            if used_area[1] > obj.transform_matrix.f:
                used_area[1] = obj.transform_matrix.f
            if used_area[3] < obj.transform_matrix.f + obj.bounding_box.y2:
                used_area[3] = obj.transform_matrix.f + obj.bounding_box.y2

    for obj in objects:
        if not isinstance(obj, (Pin, CircuitCell)):
            for port in obj.layout_ports:
                x1 = (obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2 - used_area[0] + leeway_x)
                y1 = (obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2 - used_area[1] + leeway_y)

                frac_x, int_x = math.modf(x1)
                frac_y, int_y = math.modf(y1)

                int_x = int(int_x)
                int_y = int(int_y)
                port_area.append([int_x, int_y])

                new_entry = {str(obj.number_id) + port.type: []}

                new_entry[str(obj.number_id) + port.type].append([int_x, frac_x, int_y, frac_y])
                new_entry2 = {str(obj.number_id) + port.type: []}

                new_entry2[str(obj.number_id) + port.type].append([int(obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2), int(obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2)])
                port_coord.update(new_entry2)
                port_scaled_coord.update(new_entry)

    return port_area, port_scaled_coord, used_area, port_coord


def generate_grid(grid_size, objects):
    grid = []
    value_appended = False

    leeway_x = 500
    leeway_y = 500


    port_area, area_coordinates, used_area, port_coord = _port_area(objects, grid_size, leeway_x, leeway_y)

    scaled_grid_size_y = list(math.modf((used_area[3]-used_area[1]+2*leeway_y)))
    scaled_grid_size_x = list(math.modf((used_area[2] - used_area[0] + 2 * leeway_x)))

    grid = [[0 for _ in range(int(scaled_grid_size_x[1]))] for _ in range(int(scaled_grid_size_y[1]))]

    for x,y in port_area:
        print(x,y)
        grid[y][x] = 1

    return grid, port_area, area_coordinates, used_area, port_coord