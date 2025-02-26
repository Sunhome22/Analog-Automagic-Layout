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