# ==================================================================================================================== #
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #

import re
from curses.textpad import rectangle
from dataclasses import dataclass
import re
import math


from circuit.circuit_components import Trace, RectAreaLayer, RectArea
from json_tool.json_converter import save_to_json
from magic.magic_layout_creator import MagicLayoutCreator

from circuit.circuit_components import CircuitCell, Pin, RectArea
from numpy.ma.core import append, trace

lost_start_end_points = []
@dataclass
class TraceRectangle:
    area: RectArea
    lost_points:list

    def __init__(self, area:RectArea, lost_points:list):
        self.area = area
        self.lost_points = lost_points






def direction(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return dx, dy

#--------------THIS WAS MADE FOR DEBUGGING-----------------------------#
def _check_net_constraint_violation(netlist):
    for net in netlist:
        for net2 in netlist:
            if net != net2:
                for seg in net:
                    for seg2 in net2:
                        if seg.segment[0]-seg.segment[2] == 0 and seg2.segment[0]-seg2.segment[2] == 0:
                            if seg.segment[0] - seg2.segment[2] <= 14+30 and (seg2.segment[1] <=seg.segment[1] <= seg2.segment[3] or seg2.segment[1] <=seg.segment[3] <= seg2.segment[3]) :
                                print("ERROR")

                        if seg.segment[1]-seg.segment[3] == 0 and seg2.segment[1]-seg2.segment[3] == 0:
                            if seg.segment[1] - seg2.segment[3] <= 30+30 and (seg2.segment[0] <=seg.segment[0] <= seg2.segment[2] or seg2.segment[0] <=seg.segment[2] <= seg2.segment[2]) :
                                print("ERROR")
        return

def segment_path(path):
    if path is None or len(path) < 2:
        return []  # No segments for a path with less than 2 points

    segments = []
    current_segment = [path[0]]  # Start with the first point
    # Track the initial direction
    current_direction = direction(path[0], path[1])

    for i in range(1, len(path)):
        next_direction = direction(path[i - 1], path[i])
        if next_direction != current_direction:
            # Direction changed, end the current segment
            current_segment.append(path[i - 1])
            segments.append(current_segment)
            # Start a new segment
            current_segment = [path[i - 1]]
            current_direction = next_direction

        # Add the current point to the segment
        current_segment.append(path[i])

    # Add the final segment
    if current_segment:
        segments.append(current_segment)


    return segments
def calculate_segment_length(segment):
    return sum(
        math.sqrt((segment[i][0] - segment[i - 1][0])**2 + (segment[i][1] - segment[i - 1][1])**2)
        for i in range(1, len(segment))
    )

def _calc_tmp_endpoint(start, end, lengths, segment_index, total_length):

    if total_length == 0:
        return start  # Avoid division by zero if all lengths are zero

    cumulative_length = sum(lengths[:segment_index])
    ratio = cumulative_length / total_length
    return start + (end - start) * ratio

def calculate_directional_lengths(path_segments):

    length_x = 0
    length_y = 0
    print(path_segments)
    for segment in path_segments:
        if segment[0][0] == segment[-1][0]:  # Vertical segment
            length_y += abs(segment[-1][1] - segment[0][1])  # Vertical length
        elif segment[0][1] == segment[-1][1]:  # Horizontal segment
            length_x += abs(segment[-1][0] - segment[0][0])  # Horizontal length
        else:
            raise ValueError("Segments must be either horizontal or vertical.")
    if length_x == 0:
        length_x = 1

    if length_y == 0:
        length_y = 1
    return length_x, length_y


def calculate_offset(goal_nodes, real_nodes, scale_factor, adjustment):
    offset_x, offset_y = 0, 0

    for i in range(len(goal_nodes)-1):

        offset_x += real_nodes[i][0] - (goal_nodes[i][0]*scale_factor+adjustment[0])
        offset_y += real_nodes[i][1] - (goal_nodes[i][1] * scale_factor+adjustment[1])

    return offset_x/len(goal_nodes), offset_y/len(goal_nodes)

def calculate_real_coordinates(start_grid_point, end_grid_point, scale_factor, offset_x, offset_y, adjustment):

    return ((offset_x+ adjustment[0] + start_grid_point[0] * scale_factor, offset_y+adjustment[1] + start_grid_point[1] * scale_factor),
            (offset_x +adjustment[0] +end_grid_point[0] * scale_factor, offset_y+adjustment[1] + end_grid_point[1] * scale_factor))

def lookup_known_coordinates(grid_node, real_node):
    lookup_table = {"x": {},
                    "y": {}
                    }

    for index, node in enumerate(grid_node):


        lookup_table["x"][node[0]] = real_node[index][0]
        lookup_table["y"][node[1]] = real_node[index][1]


    return lookup_table

def map_segments_to_rectangles(path_info, scale_factor, used_area):

    rectangles = []

    adjustment = (used_area[0] - 500, used_area[1]-500)

    offset_x, offset_y = calculate_offset(goal_nodes=path_info["goal_nodes"],
                              real_nodes=path_info["real_goal_nodes"],
                              scale_factor=scale_factor,
                                adjustment =adjustment)

    known_coordinates = lookup_known_coordinates(grid_node = path_info["goal_nodes"],
                                                 real_node = path_info["real_goal_nodes"])

    for segment in path_info["segments"]:
        start, end = calculate_real_coordinates(start_grid_point=segment[0],
                                                end_grid_point=segment[-1],
                                                scale_factor=scale_factor,
                                                offset_x=offset_x,
                                                offset_y=offset_y,
                                                adjustment=adjustment)

        rectangles.append(TraceRectangle(area=RectArea(x1=start[0], y1=start[1], x2=end[0], y2=end[1]), lost_points=[]))




    return rectangles

def _check_direction_change(start_end_indicator, rectangle_direction, component, port, distance, switch, overlapping_rectangle):
    if not start_end_indicator:
        if rectangle_direction:
            if component.transform_matrix.f + (port.area.y2 + port.area.y1) // 2 < overlapping_rectangle.area.y1:
                if switch:
                    direction_change = component.transform_matrix.f + port.area.y1 - distance
                else:
                    direction_change = component.transform_matrix.f + port.area.y2 + distance

            else:
                if switch:
                    direction_change = component.transform_matrix.f + port.area.y2 + distance
                else:
                    direction_change = component.transform_matrix.f + port.area.y1 - distance

            overlapping_rectangle.area.y1 = overlapping_rectangle.area.y2 = direction_change

        else:
            if component.transform_matrix.c + (
                        port.area.x2 + port.area.x1) // 2 < overlapping_rectangle.area.x1:
                if switch:
                    direction_change = component.transform_matrix.c + port.area.x1 - distance
                else:
                    direction_change = component.transform_matrix.c + port.area.x2 + distance
            else:
                if switch:
                    direction_change = component.transform_matrix.c + port.area.x2 + distance
                else:
                    direction_change = component.transform_matrix.c + port.area.x1 - distance

            overlapping_rectangle.area.x1 = overlapping_rectangle.area.x2 = direction_change

    else:
        if rectangle_direction:
            if overlapping_rectangle.area.x2 > overlapping_rectangle.area.x1:
                overlapping_rectangle.area.x2 -= 10
            else:
                overlapping_rectangle.x2 += 10

        else:

            if overlapping_rectangle.area.y2 > overlapping_rectangle.area.y1:

                overlapping_rectangle.area.y2 -= 10
            else:
                overlapping_rectangle.area.y2 += 10


    return overlapping_rectangle

def debug_print_arpo(obj, port, overlapping_rectangle):
    print("----------------------THE PROBLEMO------------------------")
    print(f"Object: {obj}")
    print(f"PORT: {port}")
    print(
        f"OVERLAPPING RECTANGLE: x1:{overlapping_rectangle.area.x1}, y1:{overlapping_rectangle.area.y1}, x2:{overlapping_rectangle.area.x2}, y2:{overlapping_rectangle.area.y2}")
    print("--------------------------END-----------------------------")
    return

def _adjust_rectangle_port_overlap(overlapping_port_rectangle, all_rectangles, previous_adjusted_seg, increment, start_end_indicator):

    adjustment_distance = 30
    all_rectangles_2 = all_rectangles[:]
    obj = overlapping_port_rectangle[0]
    port = overlapping_port_rectangle[1]
    overlapping_rectangle = overlapping_port_rectangle[2]
    switch = False

    #debug_print_arpo(obj = obj, port = port, overlapping_rectangle = overlapping_rectangle)

    print(f"Before change: x1:{overlapping_rectangle.area.x1}, y1:{overlapping_rectangle.area.y1}, x2:{overlapping_rectangle.area.x2}, y2:{overlapping_rectangle.area.y2}")

    old_start = (overlapping_rectangle.area.x1, overlapping_rectangle.area.y1)
    old_end = (overlapping_rectangle.area.x2, overlapping_rectangle.area.y2)

    if previous_adjusted_seg == overlapping_rectangle:
        increment = increment +1

        if increment >= 2 and increment%2 == 0:
            switch = True

        adjustment_distance = adjustment_distance + increment
    elif previous_adjusted_seg != overlapping_rectangle:
        increment = 0

    rectangle_direction = 1 if overlapping_rectangle.area.x1 != overlapping_rectangle.area.x2 else 0
    overlapping_rectangle = _check_direction_change(start_end_indicator=start_end_indicator,
                                                    rectangle_direction=rectangle_direction,
                                                    component = obj,
                                                    port = port,
                                                    distance = adjustment_distance,
                                                    switch = switch ,
                                                    overlapping_rectangle= overlapping_rectangle

    )

    print(
        f"After change: x1:{overlapping_rectangle.area.x1}, y1:{overlapping_rectangle.area.y1}, x2:{overlapping_rectangle.area.x2}, y2:{overlapping_rectangle.area.y2}")

    for rectangles in all_rectangles_2:

        rectangle_before = rectangles



        rectangle_direction = 1 if rectangle_before.area.x1 != rectangle_before.area.x2 else 0

        changed_coordinates = None

        if (rectangles.area.x1, rectangles.area.y1) == old_start:
            rectangles.area.x1, rectangles.area.y1 = overlapping_rectangle.area.x1, overlapping_rectangle.area.y1
            changed_coordinates = 0

        elif (rectangles.area.x1, rectangles.area.y1) == old_end:
            rectangles.area.x1, rectangles.area.y1 = overlapping_rectangle.area.x2, overlapping_rectangle.area.y2
            changed_coordinates = 0


        if (rectangles.area.x2, rectangles.area.y2) == old_start:
            rectangles.area.x2, rectangles.area.y2 = overlapping_rectangle.area.x1, overlapping_rectangle.area.y1
            changed_coordinates = 1


        elif (rectangles.area.x2, rectangles.area.y2) == old_end:
            rectangles.area.x2, rectangles.area.y2 = overlapping_rectangle.area.x2, overlapping_rectangle.area.y2
            changed_coordinates = 1


        if rectangles.area.x1 != rectangles.area.x2 and rectangles.area.y1 != rectangles.area.y2:
            if rectangle_direction:
                if changed_coordinates == 0:
                    rectangles.area.y2 = rectangles.area.y1
                else:
                    rectangles.area.y1 = rectangles.area.y2
            else:
                if changed_coordinates == 0:
                    rectangles.area.x2 = rectangles.area.x1
                else:
                    rectangles.area.x1 = rectangles.area.x2



    return all_rectangles_2,  overlapping_rectangle, increment








def _check_rectangle_port_overlap(rectangles, objects, trace_width, port_coordinates,  previous_adjusted_seg, increment, net, i):

    new_rectangles = rectangles[:]
    start_end_indicator = False

    i = i+1
    for obj in objects:
        if not isinstance(obj, (Pin, CircuitCell, Trace)):
            for ports in obj.layout_ports:

                allowed_overlap_conditions = {
                    "B" :     [ports.type == "B", ports.type == "b"]
                    }

                if any(allowed_overlap_conditions["B"]):
                    continue

                for index, seg in enumerate(rectangles):
                    overlap_conditions = {
                        "vertical_x" : [
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 <= obj.transform_matrix.c + ports.area.x2,
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 - trace_width-30  <= obj.transform_matrix.c+ ports.area.x2,
                                        obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 + trace_width+30  <= obj.transform_matrix.c + ports.area.x2
                                        ],

                        "vertical_y" : [
                                        obj.transform_matrix.f + ports.area.y1 >= min(seg.area.y1, seg.area.y2) and obj.transform_matrix.f + ports.area.y2 <= max(seg.area.y1, seg.area.y2),
                                        obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 < obj.transform_matrix.f + ports.area.y2,
                                        obj.transform_matrix.f + ports.area.y1 <= seg.area.y2 < obj.transform_matrix.f + ports.area.y2
                                        ],

                        "horizontal_y" : [
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 < obj.transform_matrix.f + ports.area.y2,
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 - trace_width -30 < obj.transform_matrix.f + ports.area.y2,
                                          obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 + trace_width +30 < obj.transform_matrix.f + ports.area.y2
                                          ],

                        "horizontal_x" : [
                                          obj.transform_matrix.c + ports.area.x1 >= min(seg.area.x1, seg.area.x2) and obj.transform_matrix.c + ports.area.x2<= max(seg.area.x1, seg.area.x2),
                                          obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 < obj.transform_matrix.c + ports.area.x2,
                                          obj.transform_matrix.c + ports.area.x1 <= seg.area.x2 < obj.transform_matrix.c + ports.area.x2
                                          ]
                    }

                    ignore_overlap_conditions = {
                        "same_net": [obj.schematic_connections[ports.type] == net],
                        "vertical_x": [
                            obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 <= obj.transform_matrix.c + ports.area.x2,

                        ],

                        "vertical_y": [
                            obj.transform_matrix.f + ports.area.y1 >= min(seg.area.y1,
                                                                          seg.area.y2) and obj.transform_matrix.f + ports.area.y2 <= max(
                                seg.area.y1, seg.area.y2),
                            obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 < obj.transform_matrix.f + ports.area.y2,
                            obj.transform_matrix.f + ports.area.y1 <= seg.area.y2 < obj.transform_matrix.f + ports.area.y2
                        ],

                        "horizontal_y": [
                            obj.transform_matrix.f + ports.area.y1 <= seg.area.y1 < obj.transform_matrix.f + ports.area.y2,

                        ],

                        "horizontal_x": [
                            obj.transform_matrix.c + ports.area.x1 >= min(seg.area.x1,
                                                                          seg.area.x2) and obj.transform_matrix.c + ports.area.x2 <= max(
                                seg.area.x1, seg.area.x2),
                            obj.transform_matrix.c + ports.area.x1 <= seg.area.x1 < obj.transform_matrix.c + ports.area.x2,
                            obj.transform_matrix.c + ports.area.x1 <= seg.area.x2 < obj.transform_matrix.c + ports.area.x2
                        ]
                    }


                    #hvis




                    if ignore_overlap_conditions["same_net"] and ((seg.area.x1 - seg.area.x2 == 0 and any(ignore_overlap_conditions["vertical_x"]) and any(ignore_overlap_conditions["vertical_y"])) or (seg.area.y1-seg.area.y2==0 and any(ignore_overlap_conditions["horizontal_x"]) and any(ignore_overlap_conditions["horizontal_y"]))):
                        continue


                    elif (seg.area.x1 - seg.area.x2 == 0 and any(overlap_conditions["vertical_x"]) and any(overlap_conditions["vertical_y"])) or (seg.area.y1 - seg.area.y2 == 0 and any(overlap_conditions["horizontal_x"]) and any(overlap_conditions["horizontal_y"])):


                        if (seg.area.x1, seg.area.y1) in port_coordinates or (seg.area.x2, seg.area.y2) in port_coordinates:
                            start_end_indicator = True


                        temporary_rectangles, previous_adjusted_seg, increment = _adjust_rectangle_port_overlap([obj, ports, seg], new_rectangles, previous_adjusted_seg, increment, start_end_indicator)

                        # if i >= 940:
                        #     print(f"EXITING ON {i}")
                        #     return rectangles

                        return _check_rectangle_port_overlap( rectangles=temporary_rectangles,
                                                              objects = objects,
                                                              port_coordinates=port_coordinates,
                                                              trace_width =trace_width,
                                                              previous_adjusted_seg=previous_adjusted_seg,
                                                              increment = increment,
                                                              net = net,
                                                              i = i)






    return rectangles




def trace_stretch(switch_bool: bool, trace_width: int, index: int, length: int) -> tuple[int,int]:

    if index == 0 and length == 1:
        return 0, 0
    elif index == 0 and length > 1:

        if switch_bool:
            return -trace_width // 2, 0
        else:
            return 0, trace_width // 2

    elif index == length - 1:
        if switch_bool:
            return 0, trace_width // 2
        else:
            return -trace_width // 2, 0
    else:
        return -trace_width // 2, trace_width // 2



def _rectangle_consolidation(rectangles, segment_direction, port_coordinates):
   # print(port_coordinates)
   # print("---------------------------------------------------------------------")
   # print(rectangles)
    new_rectangle = TraceRectangle(area = RectArea(), lost_points=[])

    if segment_direction == "h":
       # print("HORIZONTAL")
        min_x = min(min(sublist.area.x1, sublist.area.x2) for sublist in rectangles)
        max_x = max(max(sublist.area.x1, sublist.area.x2) for sublist in rectangles)

        new_y = rectangles[0].area.y1
        #print(f"FIRST Y: {new_y}")
        for rec in rectangles:
            for _,y in port_coordinates:
                if rec.area.y1 == y:

                    new_y = rec.area.y1
        #            print(f"SECOND Y: {new_y}")
                    break

        new_rectangle.area = RectArea(x1 = min_x, y1 = new_y, x2 = max_x, y2 = new_y)
       # print(f"becomes: x1:{new_rectangle.area.x1}, y1:{new_rectangle.area.y1}, x2:{new_rectangle.area.x2}, y2:{new_rectangle.area.y2}")
        for sublist in rectangles:

            if (sublist.area.x1, sublist.area.y1) != (min_x, new_y) and (sublist.area.x1, sublist.area.y1) != (max_x, new_y):
                new_rectangle.lost_points.append((sublist.area.x1,sublist.area.y1))

            elif (sublist.area.x2, sublist.area.y2) != (min_x, new_y) and (sublist.area.x2, sublist.area.y2) != (max_x, new_y):
                new_rectangle.lost_points.append((sublist.area.x2, sublist.area.y2))

            if len(sublist.lost_points) > 0:

                new_rectangle.lost_points.extend(sublist.lost_points)


    elif segment_direction == "v":
        #print("VERTICAL")

        min_y = min(min(sublist.area.y1, sublist.area.y2) for sublist in rectangles)
        max_y = max(max(sublist.area.y1, sublist.area.y2) for sublist in rectangles)
        new_x = rectangles[0].area.x1
        #print(f"FIRST X: {new_x}")
        for rec in rectangles:
            for x, _ in port_coordinates:
                if rec.area.x1 == x:
                    new_x = rec.area.x1
         #           print(f"SECOND X: {new_x}")
                    break
        new_rectangle.area = RectArea(x1=new_x, y1=min_y, x2=new_x, y2=max_y)
       # print(
        #    f"becomes: x1:{new_rectangle.area.x1}, y1:{new_rectangle.area.y1}, x2:{new_rectangle.area.x2}, y2:{new_rectangle.area.y2}")
        for sublist in rectangles:

            if (sublist.area.x1, sublist.area.y1) != (new_x, min_y) and (sublist.area.x1, sublist.area.y1) != (new_x, max_y):
                new_rectangle.lost_points.append((sublist.area.x1, sublist.area.y1))

            elif (sublist.area.x2, sublist.area.y2) != (new_x, min_y) and (sublist.area.x2, sublist.area.y2) != (new_x, max_y):
                new_rectangle.lost_points.append((sublist.area.x2, sublist.area.y2))

            if len(sublist.lost_points) > 0:
                new_rectangle.lost_points.extend(sublist.lost_points)

    else:
        print("[ERROR] Direction invalid")

    return new_rectangle

def _eliminate_rectangles(rectangles, trace_width, port_coordinates):
    spacing_m2 = 20#horizontal
    spacing_m3 = 30 #vertical

    i = 0
    rectangles_duplicate = rectangles[:]
    checked_rectangle = []
    rectangle_list = []
    for i, path_rectangle_1 in enumerate(rectangles):

        index_list = []
        temp_seg_list = [path_rectangle_1]

        #Change to .x1 and .x2
        direction_rectangle_1 = "h" if path_rectangle_1.area.x1 != path_rectangle_1.area.x2 else "v"

        for index, path_rectangle_2 in enumerate(rectangles_duplicate):

            direction_rectangle_2 = "h" if path_rectangle_2.area.x1 != path_rectangle_2.area.x2 else "v"

            conditions = {
                    "general" : [direction_rectangle_1==direction_rectangle_2,
                                 path_rectangle_1.area != path_rectangle_2.area,
                                 path_rectangle_1.area not in checked_rectangle,
                                 path_rectangle_2.area not in checked_rectangle
                                 ],
                    "v" : [direction_rectangle_1 == "v",
                           abs(path_rectangle_1.area.x1 - path_rectangle_2.area.x1) <= (trace_width + spacing_m3 ),
                           (min(int(path_rectangle_2.area.y1), int(path_rectangle_2.area.y2)) <=int(path_rectangle_1.area.y1) <= max(int(path_rectangle_2.area.y1), int(path_rectangle_2.area.y2))) or (min(int(path_rectangle_2.area.y1), int(path_rectangle_2.area.y2)) <=int(path_rectangle_1.area.y2) <= max(int(path_rectangle_2.area.y1), int(path_rectangle_2.area.y2)))
                           ],
                    "h" : [direction_rectangle_1 == "h",
                           abs(path_rectangle_1.area.y1 - path_rectangle_2.area.y1) <= (trace_width + spacing_m2 ),
                           (min(int(path_rectangle_2.area.x1), int(path_rectangle_2.area.x2)) <=int(path_rectangle_1.area.x1) <= max(int(path_rectangle_2.area.x1), int(path_rectangle_2.area.x2))) or (min(int(path_rectangle_2.area.x1), int(path_rectangle_2.area.x2)) <=int(path_rectangle_1.area.x2) <= max(int(path_rectangle_2.area.x1), int(path_rectangle_2.area.x2)))
                           ]
                }
            if all(conditions["general"]) and (all(conditions["h"]) or all(conditions["v"])):

                temp_seg_list.append(path_rectangle_2)
                index_list.append(index)
                checked_rectangle.append(path_rectangle_2.area)


        for x in sorted(index_list, reverse=True) :
            del rectangles_duplicate[x]

        if len(temp_seg_list) > 1:

            rectangles.append(_rectangle_consolidation(temp_seg_list, direction_rectangle_1, port_coordinates))
            rectangles_duplicate.append(rectangles[-1])

            if path_rectangle_1.area != rectangles[-1].area:
                checked_rectangle.append(path_rectangle_1.area)

            if rectangles[-1].area in checked_rectangle:
                rectangle_list.append(rectangles[-1])


        elif path_rectangle_1.area not in checked_rectangle:

            rectangle_list.append(path_rectangle_1)
            checked_rectangle.append(path_rectangle_1.area)




    return rectangle_list

def _write_traces(rectangles, trace_width, index, name):
    a_trace = Trace()
    a_trace.instance = a_trace.__class__.__name__
    a_trace.number_id = index
    a_trace.name = name


    for i, rect in enumerate(rectangles):
        if rect.area.x1 == rect.area.x2:  # Vertical
            if rect.area.y1 > rect.area.y2:  # Ensure y1 < y2
                rect.area.y1, rect.area.y2 = rect.area.y2, rect.area.y1
                switched_start_end = True
            else:
                switched_start_end = False

            added_length_start, added_length_end = trace_stretch(switched_start_end, trace_width, i, len(rectangles))

            a_trace.segments.append(RectAreaLayer(
                layer="m3",
                area=RectArea(
                    x1=int(rect.area.x1) - trace_width // 2,  # Adding width to trace
                    y1=int(rect.area.y1 + added_length_start),
                    x2=int(rect.area.x2) + trace_width // 2,
                    y2=int(rect.area.y2 + added_length_end)
                )
            ))
        elif rect.area.y1 == rect.area.y2:  # Horizontal
            if rect.area.x1 > rect.area.x2:  # Ensure x1 < x2
                rect.area.x1, rect.area.x2 = rect.area.x2, rect.area.x1
                switched_start_end = True
            else:
                switched_start_end = False
            added_length_start, added_length_end = trace_stretch(switched_start_end, trace_width, i,
                                                                 len(rectangles))

            a_trace.segments.append(RectAreaLayer(
                layer="m2",
                area=RectArea(
                    x1=int(rect.area.x1 + added_length_start),
                    y1=int(rect.area.y1) - trace_width // 2,
                    x2=int(rect.area.x2 + added_length_end),
                    y2=int(rect.area.y2) + trace_width // 2
                )
            ))
        else:
            print("ILLEGAL TRACE IN WRITE TRACE")
            print(f"x1:{rect.area.x1},  y1:{rect.area.y1}, x2:{rect.area.x2}, y2:{rect.area.y2}")

    return a_trace
def _check_for_lost_points(rectangles):

    for seg in rectangles:
        for next_segment in rectangles:
            if seg != next_segment:
                for lost_point in next_segment.lost_points:
                    if (seg.area.x1, seg.area.y1) == lost_point:
                        if seg.area.y1  == seg.area.y2 and next_segment.area.x1 == next_segment.area.x2:
                            seg.area.x1 = next_segment.area.x1
                        elif seg.area.x1 == seg.area.x2 and next_segment.area.y1 == next_segment.area.y2:
                            seg.area.y1 = next_segment.area.y1



                    elif (seg.area.x2, seg.area.y2) == lost_point:
                        if seg.area.y1 == seg.area.y2 and next_segment.area.x1 == next_segment.area.x2:
                            seg.area.x2 = next_segment.area.x2
                        elif seg.area.x1 == seg.area.x2 and next_segment.area.y1 == next_segment.area.y2:
                            seg.area.y2 = next_segment.area.y2
    # Må bruke segmentet og ikke lost_point direkte og finne ut av hvilket av de to punktene i next_segment som skal tas i bruk

    return rectangles

def _delete_duplicate_rectangles(rectangle_list):
    unique = []
    for sublist in rectangle_list:
        if sublist not in unique:
            unique.append(sublist)
    return unique

def _check_illegal_trace(trace_list):
    for seg in trace_list:
        for seg2 in trace_list:
            if seg != seg2:
                if seg.area.x1 - seg.area.x2 == 0 and seg2.area.x1 - seg2.area.x2 == 0:
                    if abs(seg.area.x1 - seg2.area.x1) <= 60 and (min(seg2.area.y1, seg2.area.y2) <= seg.area.y1 <= max(seg2.area.y1, seg2.area.y2) or min(seg2.area.y1, seg2.area.y2) <= seg.area.y2 <= max(seg2.area.y1, seg2.area.y2)):
                        print("True")
                        return True

                elif seg.area.y1 - seg.area.y2 == 0 and seg2.area.y1 - seg2.area.y2 == 0:
                    if abs(seg.area.y1 - seg2.area.y1) <= 44 and (min(seg2.area.x1, seg2.area.x2) <= seg.area.x1 <= max(seg2.area.x2, seg2.area.x1) or min(seg2.area.x1, seg2.area.x2) <= seg.area.x2 <= max(seg2.area.x2, seg2.area.x1)):
                        print("True")
                        return True
    print("False")
    return False

def _check_illegal_rectangles(rectangle_list):
    illegal = False
    for rect in rectangle_list:
        print(rect)
        if rect.area.x1!=rect.area.x2 and rect.area.y1!=rect.area.y2:
            print("Illegal rectangle")
            illegal = True
    if not illegal:
        print("NO ILLEGAL RECTANGLE")

    return

def _look_for_specific_rectangle(rectangle_list):
    specific_rectangle = TraceRectangle(area = RectArea(x1=1675.2, y1=1029, x2=1675.2, y2 =1028), lost_points=[])
    for rect in rectangle_list:
        if specific_rectangle.area == rect.area:
            print("---------- ")
            print("---------- ")
            print("CREATED HERE")
            print("---------- ")
            print("---------- ")
    return
def initiate_write_traces(components, all_paths,  scale_factor, trace_width, used_area):



    for index, net in enumerate(all_paths):


        if net == "net2":




            mapped_rectangles = map_segments_to_rectangles(path_info=all_paths[net],
                                                                   scale_factor=scale_factor,
                                                                   used_area=used_area)


            components.append(_write_traces(mapped_rectangles, trace_width, index, net))

          #  _check_net_constraint_vioaltion(test)

    return components