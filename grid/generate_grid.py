

from circuit.circuit_components import Pin, CircuitCell
def _port_area(objects, grid_size):
    port_area = []
    area_coordinates = {}
    perimeter = [grid_size, grid_size, 0, 0 ]

    for obj in objects:
        if not isinstance(obj, (Pin,CircuitCell)):

            if perimeter[0] > obj.transform_matrix.c:
                perimeter[0] = obj.transform_matrix.c
            if perimeter[2] < obj.transform_matrix.c + obj.bounding_box.x2:
                perimeter[2] = obj.transform_matrix.c + obj.bounding_box.x2

            if perimeter[1] > obj.transform_matrix.f:
                perimeter[1] = obj.transform_matrix.f
            if perimeter[3] < obj.transform_matrix.f + obj.bounding_box.y2:
                perimeter[3] = obj.transform_matrix.f + obj.bounding_box.y2




            for port in obj.layout_ports:
                x1 = obj.transform_matrix.c + port.area.x1
                x2 = obj.transform_matrix.c + port.area.x2
                y1 = obj.transform_matrix.f + port.area.y1
                y2 = obj.transform_matrix.f + port.area.y2

                port_area.append([x1, y1, x2, y2])

                new_entry = {str(obj.number_id) + port.type : []}
                for y in range(y1, y2, 1):
                    for x in range(x1, x2, 1):
                            new_entry[str(obj.number_id) + port.type].append((x,y))

                area_coordinates.update(new_entry)


    return port_area, area_coordinates, perimeter



def generate_grid(grid_size, objects):
    grid = []
    value_appended = False

    leeway_x = 96 + 64 + 32
    leeway_y = 120
    wire_width = 30





    area, area_coordinates, perimeter = _port_area(objects, grid_size)

    for y in range(perimeter[1]-leeway_y, perimeter[3]+leeway_y, 40):
        grid.append([])
        for x in range(perimeter[0]-leeway_x, perimeter[2]+leeway_x, 32):

            for p in area:

                if p[0]<=x<=p[2] and p[1]<=y<=p[3]:

                    grid[-1].append(1)
                    value_appended = True
                    break

            if not value_appended:
                grid[-1].append(0)

            else:

                value_appended = False




    return grid, area, area_coordinates, perimeter