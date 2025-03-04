def _adjust_rectangle_port_overlap(overlapping_port_rectangle, all_rectangles):


    obj = overlapping_port_rectangle[0]
    port = overlapping_port_rectangle[1]

    overlapping_rectangle = overlapping_port_rectangle[2]

    old_start = (overlapping_rectangle.area.x1, overlapping_rectangle.area.y1)
    old_end = (overlapping_rectangle.area.x2, overlapping_rectangle.area.y2)



    rectangle_direction = 1 if overlapping_rectangle.area.x1 != overlapping_rectangle.area.x2 else 0

    if rectangle_direction:
        direction_change = obj.transform_matrix.f + port.area.y2 + 60 if obj.transform_matrix.f + (port.area.y2+port.area.y1) // 2 <= overlapping_rectangle.area.y1 else obj.transform_matrix.f+port.area.y1-60
        overlapping_rectangle.area.y1 = overlapping_rectangle.area.y2 = direction_change
    else:
        direction_change = obj.transform_matrix.c + port.area.x2 + 60 if obj.transform_matrix.c + (port.area.x2 + port.area.x1) // 2 <= overlapping_rectangle.area.x1 else obj.transform_matrix.c + port.area.x1 - 60
        overlapping_rectangle.area.x1 = overlapping_rectangle.area.x2 = direction_change

    for rectangles in all_rectangles:


        if (rectangles.area.x1, rectangles.area.y1) == old_start:
            rectangles.area.x1, rectangles.area.y1 = overlapping_rectangle.area.x1, overlapping_rectangle.area.y1


        if (rectangles.area.x2, rectangles.area.y2) == old_start:
            rectangles.area.x2, rectangles.area.y2 = overlapping_rectangle.area.x1, overlapping_rectangle.area.y1


        if (rectangles.area.x2, rectangles.area.y2) == old_end:
            rectangles.area.x2, rectangles.area.y2 = overlapping_rectangle.area.x2, overlapping_rectangle.area.y2


        if (rectangles.area.x1, rectangles.area.y1) == old_end:
            rectangles.area.x1, rectangles.area.y1 = overlapping_rectangle.area.x2, overlapping_rectangle.area.y2

    return all_rectangles








def _check_rectangle_port_overlap(rectangles, name, objects, trace_width):
    pattern = r"^(\d+)([A-Za-z])_(\d+)([A-Za-z])$"
    non_overlapping_rectangles = []
    overlapping_port_rectangles = []
    match = re.match(pattern, name)

    if match:
        start_object_id = int(match.group(1))
        start_object_port = match.group(2)
        end_object_id = int(match.group(3))
        end_object_port = match.group(4)
    else:

        #Should be logger
        print("[ERROR] INVALID PATH NAME")
        return


    for obj in objects:
        if not isinstance(obj, (Pin, CircuitCell)):
            for ports in obj.layout_ports:

                allowed_overlap_conditions = {
                    "start" : [obj.number_id == start_object_id, ports.type == start_object_port],
                    "end" :   [obj.number_id == end_object_id, ports.type == end_object_port],
                    "B" :     [ports.type == "B", ports.type == "b"]
                    }
                if all(allowed_overlap_conditions["start"]) or all(allowed_overlap_conditions["end"]) or any(allowed_overlap_conditions["B"]):
                    continue

                for seg in rectangles:
                    overlap_conditions = {
                        "vertical_x" : [
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 <= obj.transform_matrix.c + ports.area.x2,
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 - trace_width -30 <= obj.transform_matrix.c+ ports.area.x2,
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 + trace_width +30 <= obj.transform_matrix.c + ports.area.x2
                                        ],

                        "vertical_y" : [
                                        obj.transform_matrix.f + ports.area.y1 >= min(seg.area.y1, seg.area.y2) and obj.transform_matrix.f + ports.area.y2 <= max(seg.area.y1, seg.area.y2),
                                        obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 <= obj.transform_matrix.f + ports.area.y2,
                                        obj.transform_matrix.f + ports.area.y1 <= seg.area.y2 <= obj.transform_matrix.f + ports.area.y2
                                        ],

                        "horizontal_y" : [
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 <= obj.transform_matrix.f + ports.area.y2,
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 - trace_width -30 <= obj.transform_matrix.f + ports.area.y2,
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 + trace_width +30 <= obj.transform_matrix.f + ports.area.y2
                                          ],

                        "horizontal_x" : [
                                          obj.transform_matrix.c + ports.area.x1 >= min(seg.area.x1, seg.area.x2) and obj.transform_matrix.c + ports.area.x2<= max(seg.area.x1, seg.area.x2),
                                          obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 <= obj.transform_matrix.c + ports.area.x2,
                                          obj.transform_matrix.c + ports.area.x1 <= seg.area.x2 <= obj.transform_matrix.c + ports.area.x2
                                          ]
                    }

                    if (seg.area.x1 - seg.area.x2 == 0 and any(overlap_conditions["vertical_x"]) and any(overlap_conditions["vertical_y"])) or (seg.area.y1 - seg.area.y2 == 0 and any(overlap_conditions["horizontal_x"]) and any(overlap_conditions["horizontal_y"])):

                        temporary_rectangles = _adjust_rectangle_port_overlap([obj, ports, seg], rectangles)
                        return _check_rectangle_port_overlap(temporary_rectangles, name, objects, trace_width)





    return rectangles



##OLD_VERSION#
def _adjust_rectangle_port_overlap(overlapping_port_rectangle, non_overlapping_rectangles, all_rectangles):

    adjusted_rectangles = []
    test = []
    old_start = (None, None)
    old_end = (None, None)
    for obj, port, overlapping_rectangle in overlapping_port_rectangle:




        old_start = (overlapping_rectangle.area.x1,overlapping_rectangle.area.y1)
        old_end = (overlapping_rectangle.area.x2,overlapping_rectangle.area.y2)

        rectangle_direction = 1 if overlapping_rectangle.area.x1 != overlapping_rectangle.area.x2 else 0

        if rectangle_direction:
            direction_change = obj.transform_matrix.f + port.area.y2 + 60 if obj.transform_matrix.f + (port.area.y2+port.area.y1) // 2 <= overlapping_rectangle.area.y1 else obj.transform_matrix.f+port.area.y1-60
            overlapping_rectangle.area.y1 = overlapping_rectangle.area.y2 = direction_change
        else:
            direction_change = obj.transform_matrix.c + port.area.x2 + 60 if obj.transform_matrix.c + (port.area.x2 + port.area.x1) // 2 <= overlapping_rectangle.area.x1 else obj.transform_matrix.c + port.area.x1 - 60
            overlapping_rectangle.area.x1 = overlapping_rectangle.area.x2 = direction_change
        test.append(overlapping_rectangle)
        adjusted_rectangles.append(overlapping_rectangle)
        for rectangles in non_overlapping_rectangles:

            adjustment_conditions = {
                "start_point" : [
                                 rectangles.area.x1 == old_start[0],
                                 rectangles.area.y1 == old_start[1]
                                 ],
                "start_point2": [
                    rectangles.area.x2 == old_start[0],
                    rectangles.area.y2 == old_start[1]
                ],
                "end_point" : [
                               rectangles.area.x2 == old_end[0],
                               rectangles.area.y2 == old_end[1]
                               ],
                "end_point2": [
                    rectangles.area.x1 == old_end[0],
                    rectangles.area.y1 == old_end[1]
                ]

                              }



            if all(adjustment_conditions["start_point"]):
                rectangles.area.x1 = overlapping_rectangle.area.x1
                rectangles.area.y1 = overlapping_rectangle.area.y1

            if all(adjustment_conditions["start_point2"]):
                rectangles.area.x2 = overlapping_rectangle.area.x1
                rectangles.area.y2= overlapping_rectangle.area.y1

            if all(adjustment_conditions["end_point"]):
                rectangles.area.x2 = overlapping_rectangle.area.x2
                rectangles.area.y2 = overlapping_rectangle.area.y2
            if all(adjustment_conditions["end_point2"]):
                rectangles.area.x1 = overlapping_rectangle.area.x2
                rectangles.area.y1 = overlapping_rectangle.area.y2



            adjusted_rectangles.append(rectangles)



    return adjusted_rectangles








def _check_rectangle_port_overlap(rectangles, name, objects, trace_width):
    pattern = r"^(\d+)([A-Za-z])_(\d+)([A-Za-z])$"
    non_overlapping_rectangles = []
    overlapping_port_rectangles = []
    match = re.match(pattern, name)

    if match:
        start_object_id = int(match.group(1))
        start_object_port = match.group(2)
        end_object_id = int(match.group(3))
        end_object_port = match.group(4)
    else:

        #Should be logger
        print("[ERROR] INVALID PATH NAME")
        return


    for obj in objects:
        if not isinstance(obj, (Pin, CircuitCell)):
            for ports in obj.layout_ports:

                allowed_overlap_conditions = {
                    "start" : [obj.number_id == start_object_id, ports.type == start_object_port],
                    "end" :   [obj.number_id == end_object_id, ports.type == end_object_port],
                    "B" :     [ports.type == "B", ports.type == "b"]
                    }
                if all(allowed_overlap_conditions["start"]) or all(allowed_overlap_conditions["end"]) or any(allowed_overlap_conditions["B"]):
                    continue

                for seg in rectangles:
                    overlap_conditions = {
                        "vertical_x" : [
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 <= obj.transform_matrix.c + ports.area.x2,
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 - trace_width -30 <= obj.transform_matrix.c+ ports.area.x2,
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 + trace_width +30 <= obj.transform_matrix.c + ports.area.x2
                                        ],

                        "vertical_y" : [
                                        obj.transform_matrix.f + ports.area.y1 >= min(seg.area.y1, seg.area.y2) and obj.transform_matrix.f + ports.area.y2 <= max(seg.area.y1, seg.area.y2),
                                        obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 <= obj.transform_matrix.f + ports.area.y2,
                                        obj.transform_matrix.f + ports.area.y1 <= seg.area.y2 <= obj.transform_matrix.f + ports.area.y2
                                        ],

                        "horizontal_y" : [
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 <= obj.transform_matrix.f + ports.area.y2,
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 - trace_width -30 <= obj.transform_matrix.f + ports.area.y2,
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 + trace_width +30 <= obj.transform_matrix.f + ports.area.y2
                                          ],

                        "horizontal_x" : [
                                          obj.transform_matrix.c + ports.area.x1 >= min(seg.area.x1, seg.area.x2) and obj.transform_matrix.c + ports.area.x2<= max(seg.area.x1, seg.area.x2),
                                          obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 <= obj.transform_matrix.c + ports.area.x2,
                                          obj.transform_matrix.c + ports.area.x1 <= seg.area.x2 <= obj.transform_matrix.c + ports.area.x2
                                          ]
                    }

                    if (seg.area.x1 - seg.area.x2 == 0 and any(overlap_conditions["vertical_x"]) and any(overlap_conditions["vertical_y"])) or (seg.area.y1 - seg.area.y2 == 0 and any(overlap_conditions["horizontal_x"]) and any(overlap_conditions["horizontal_y"])):
                            # print("overlap found")
                            # print(obj.number_id)
                            # print(obj.name)
                            # print(f"Object placement: x: {obj.transform_matrix.c}, y: {obj.transform_matrix.f}")
                            # print(f"Port: {ports.type} x1:{obj.transform_matrix.c + ports.area.x1}, y1:{obj.transform_matrix.f + ports.area.y1}, x2:{obj.transform_matrix.c + ports.area.x2}, y2:{obj.transform_matrix.f + ports.area.y2}")
                            # print(name)
                            # print(f"Rectangle x1:{seg.area.x1}, y1:{seg.area.y1}, x2:{seg.area.x2}, y2:{seg.area.y2}")

                            overlapping_port_rectangles.append([obj, ports, seg])






    if len(overlapping_port_rectangles) >= 1:

        for rect in rectangles:
            overlapping_bool = False
            for overlapping_entry in overlapping_port_rectangles:

                if overlapping_entry[2] == rect:
                    overlapping_bool = True
            if not overlapping_bool:
                non_overlapping_rectangles.append(rect)

        non_overlapping_rectangles = _adjust_rectangle_port_overlap(overlapping_port_rectangles, non_overlapping_rectangles, rectangles)





    return non_overlapping_rectangles


##Something to try:

def grid_to_real(grid_coord, scale, offset):
    """
    Converts a grid coordinate to a real-world coordinate.

    :param grid_coord: Tuple (i, j) representing the grid index.
    :param scale: Tuple (delta_x, delta_y) representing the size of a grid cell in real-world units.
    :param offset: Tuple (x0, y0) representing the real-world coordinate corresponding to grid (0, 0).
    :return: Tuple (x, y) as the real-world coordinate.
    """
    i, j = grid_coord
    delta_x, delta_y = scale
    x0, y0 = offset
    return (x0 + i * delta_x, y0 + j * delta_y)


ef
compute_path_segments(grid_path, scale, offset):
"""
Converts a grid-based path to real coordinates and computes segments.

:param grid_path: List of grid coordinates (e.g., [(i1, j1), (i2, j2), ...]).
:param scale: Tuple (delta_x, delta_y).
:param offset: Tuple (x0, y0).
:return: List of segments. Each segment is a dictionary with 'start', 'end', and 'length'.
"""
# Convert the grid path to real coordinates.
real_path = [grid_to_real(coord, scale, offset) for coord in grid_path]

segments = []
for i in range(1, len(real_path)):
    start = real_path[i - 1]
    end = real_path[i]
    # Compute Euclidean distance.
    length = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
    segments.append({
        "start": start,
        "end": end,
        "length": length
    })
return segments

# Example parameters:
# Suppose each grid cell is 0.5 by 0.5 meters.
scale = (0.5, 0.5)

# And we know that the grid cell (4, 3) corresponds to the real-world coordinate (12, 9).
goal_grid_coord = (4, 3)
goal_real_coord = (12, 9)
offset = (goal_real_coord[0] - goal_grid_coord[0] * scale[0],
          goal_real_coord[1] - goal_grid_coord[1] * scale[1])
# In this case:
# offset = (12 - 4*0.5, 9 - 3*0.5) = (12 - 2, 9 - 1.5) = (10, 7.5)

# Example grid path from multi-goal A* (list of grid coordinates)
grid_path = [(0, 0), (1, 0), (2, 1), (3, 2), (4, 3)]

# Compute the segments
segments = compute_path_segments(grid_path, scale, offset)

# Display the segments.
for seg in segments:
    print(f"Segment from {seg['start']} to {seg['end']} with length {seg['length']:.2f}")