

from circuit.circuit_components import Pin, CircuitCell
def _port_area(objects):
    port_area = []
    area_coordinates = {}


    for obj in objects:
        if not isinstance(obj, (Pin,CircuitCell)):
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


    return port_area, area_coordinates



def generate_grid(grid_size, objects):
    grid = []
    value_appended = False

    area, area_coordinates = _port_area(objects)
    for y in range(grid_size):
        grid.append([])
        for x in range(grid_size):
            for p in area:

                if p[0]<=x<=p[2] and p[1]<=y<=p[3]:

                    grid[-1].append(2)
                    value_appended = True
                    break

            if not value_appended:
                grid[-1].append(0)

            else:

                value_appended = False




    return grid, area, area_coordinates