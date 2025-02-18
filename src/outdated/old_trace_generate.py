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

lost_start_end_points = []
@dataclass
class NewSegment:
    segment:list
    lost_points:list

    def __init__(self, segment:list, lost_points:list):
        self.segment = segment
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

    for segment in path_segments:
        segment = segment
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


def map_path_to_rectangles(path_segments, port_coord, connection_name):
    rectangles = []
    length_x, length_y = calculate_directional_lengths(path_segments)

    # Get the real-world start and end coordinates
    start_name, end_name = connection_name.split("_",1)
    start_real = port_coord[start_name]
    end_real = port_coord[end_name]

    cumulative_x = 0
    cumulative_y = 0



    for segment in path_segments:
        start_x, start_y = start_real if not rectangles else (rectangles[-1].segment[2], rectangles[-1].segment[3])

        if segment[0][0] == segment[-1][0]:  # Vertical segment
            segment_length = abs(segment[-1][1] - segment[0][1])
            cumulative_y += segment_length
            end_x = start_x
            if end_real[1] > start_real[1]:
                end_y = start_real[1] + (end_real[1] - start_real[1]) * (cumulative_y / length_y)
            else:
                end_y = start_real[1] - (start_real[1]- end_real[1]) * (cumulative_y / length_y)
        elif segment[0][1] == segment[-1][1]:  # Horizontal segment
            segment_length = abs(segment[-1][0] - segment[0][0])
            cumulative_x += segment_length
            end_y = start_y
            if end_real[0] > start_real[0]:
                end_x = start_real[0] + (end_real[0] - start_real[0]) * (cumulative_x / length_x)
            else:
                end_x = start_real[0] - (start_real[0]- end_real[0]) * (cumulative_x / length_x)

        else:
            print("ERROR: Invalid segment, must be either vertical or horizontal")

        rectangles.append(NewSegment(segment = [start_x, start_y, end_x, end_y], lost_points=[]))

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

#Denne ser ikke ut til å bli brukt
# def _remove_duplicates(my_list: list) -> list:
#     seen = set()
#     unique_data = []
#     for item in my_list:
#         if not type(item) == float or int:
#             # Normalize the tuple by sorting its elements
#             normalized = tuple(sorted(item))
#             if normalized not in seen:
#                 seen.add(normalized)
#                 unique_data.append(item)
#     return unique_data

def _rectangle_consolidation(rectangles, segment_direction):

    seg = NewSegment(segment = [],lost_points = [])
    if segment_direction == "h":

        min_x = min(min(sublist[0], sublist[2]) for sublist in rectangles)
        max_x = max(max(sublist[0], sublist[2]) for sublist in rectangles)
        y = rectangles[0][1]

        seg.segment.extend([min_x, y, max_x, y])

        for sublist in rectangles:

            if (sublist[0], sublist[1]) != (min_x, y) and (sublist[0], sublist[1]) != (max_x, y):
                seg.lost_points.append((sublist[0],sublist[1]))

            elif (sublist[2], sublist[3]) != (min_x, y) and (sublist[2], sublist[3]) != (max_x, y):
                seg.lost_points.append((sublist[2], sublist[3]))


    elif segment_direction == "v":

        min_y = min(min(sublist[1], sublist[3]) for sublist in rectangles)
        max_y = max(max(sublist[1], sublist[3]) for sublist in rectangles)
        x = rectangles[0][0]

        seg.segment.extend([x, min_y, x, max_y])

        for sublist in rectangles:

            if (sublist[0], sublist[1]) != (x, min_y) and (sublist[0], sublist[1]) != (x, max_y):
                seg.lost_points.append((sublist[0], sublist[1]))

            elif (sublist[2], sublist[3]) != (x, min_y) and (sublist[2], sublist[3]) != (x, max_y):
                seg.lost_points.append((sublist[2], sublist[3]))

    else:
        print("[ERROR] Direction invalid")

    return seg

def _eliminate_rectangles(rectangles, trace_width):
    spacing_m2 = 14 #horizontal
    spacing_m3 = 30 #vertical
    p = 0
    first_rectangle_list = []
    last_rectangle_list = []
    illegal_placement = True
    while  illegal_placement:
        rectangle_list = []

        rectangles_duplicate = rectangles[:]
        checked_rectangle = []
        for i, path_rectangle_1 in enumerate(rectangles):
            path_rectangle_1 = path_rectangle_1.segment
            index_list = []
            temp_seg_list = [path_rectangle_1]

            #Change to .x1 and .x2
            direction_rectangle_1 = "h" if path_rectangle_1[0] != path_rectangle_1[2] else "v"

            for index, path_rectangle_2 in enumerate(rectangles_duplicate):
                path_rectangle_2 = path_rectangle_2.segment

                direction_rectangle_2 = "h" if path_rectangle_2[0] != path_rectangle_2[2] else "v"


                if direction_rectangle_1==direction_rectangle_2 and path_rectangle_1 != path_rectangle_2 and path_rectangle_2 not in checked_rectangle and path_rectangle_1 not in checked_rectangle:
                    print("THIS IS TRUE")
                    conditions = {
                        "v" : [direction_rectangle_1 == "v",
                               abs(path_rectangle_1[0] - path_rectangle_2[0]) <= (trace_width + spacing_m3 ),
                               (min(int(path_rectangle_2[1]), int(path_rectangle_2[3])) <=int(path_rectangle_1[1]) <= max(int(path_rectangle_2[1]), int(path_rectangle_2[3]))) or (min(int(path_rectangle_2[1]), int(path_rectangle_2[3])) <=int(path_rectangle_1[3]) <= max(int(path_rectangle_2[1]), int(path_rectangle_2[3])))
                               ],
                        "h" : [direction_rectangle_1 == "h",
                               abs(path_rectangle_1[1] - path_rectangle_2[1]) <= (trace_width + spacing_m2 ),
                               (min(int(path_rectangle_2[0]), int(path_rectangle_2[2])) <=int(path_rectangle_1[0]) <= max(int(path_rectangle_2[0]), int(path_rectangle_2[2]))) or (min(int(path_rectangle_2[0]), int(path_rectangle_2[2])) <=int(path_rectangle_1[2]) <= max(int(path_rectangle_2[0]), int(path_rectangle_2[2])))
                               ]
                    }
                    if all(conditions["h"]) or all(conditions["v"]):
                        print("ALL CONDITIONS SATISFIED")#horizontal, m3
                        temp_seg_list.append(path_rectangle_2)
                        index_list.append(index)
                        checked_rectangle.append(path_rectangle_2)
            checked_rectangle.append(path_rectangle_1)
            for x in sorted(index_list, reverse=True) :
                del rectangles_duplicate[x]

            if len(temp_seg_list) > 1:
                rectangle_list.append(_rectangle_consolidation(temp_seg_list, direction_rectangle_1))
                rectangles_duplicate.append(rectangle_list[-1])
            else:
                rectangle_list.append(NewSegment(segment=temp_seg_list[0], lost_points=[]))


        illegal_placement = _check_illegal_trace(rectangle_list)
        if illegal_placement:
            rectangles = rectangle_list
        p+= 1
        print(i)
        if p == 1:
            first_rectangle_list = rectangle_list
        if p >= 100:
            illegal_placement = False

            print("First")
            print(first_rectangle_list)
            print("Last")
            print(rectangle_list)

    return rectangle_list

def _write_traces(rectangles, trace_width, index, name):
    a_trace = Trace()
    a_trace.instance = a_trace.__class__.__name__
    a_trace.number_id = index
    a_trace.name = name

    for i, rect in enumerate(rectangles):
        if rect.segment[0] == rect.segment[2]:  # Vertical
            if rect.segment[1] > rect.segment[3]:  # Ensure y1 < y2
                rect.segment[1], rect.segment[3] = rect.segment[3], rect.segment[1]
                switched_start_end = True
            else:
                switched_start_end = False

            added_length_start, added_length_end = trace_stretch(switched_start_end, trace_width, i, len(rectangles))

            a_trace.segments.append(RectAreaLayer(
                layer="m3",
                area=RectArea(
                    x1=int(rect.segment[0]) - trace_width // 2,  # Adding width to trace
                    y1=int(rect.segment[1] + added_length_start),
                    x2=int(rect.segment[2]) + trace_width // 2,
                    y2=int(rect.segment[3] + added_length_end)
                )
            ))
        elif rect.segment[1] == rect.segment[3]:  # Horizontal
            if rect.segment[0] > rect.segment[2]:  # Ensure x1 < x2
                rect.segment[0], rect.segment[2] = rect.segment[2], rect.segment[0]
                switched_start_end = True
            else:
                switched_start_end = False
            added_length_start, added_length_end = trace_stretch(switched_start_end, trace_width, i,
                                                                 len(rectangles))

            a_trace.segments.append(RectAreaLayer(
                layer="m2",
                area=RectArea(
                    x1=int(rect.segment[0] + added_length_start),
                    y1=int(rect.segment[1]) - trace_width // 2,
                    x2=int(rect.segment[2] + added_length_end),
                    y2=int(rect.segment[3]) + trace_width // 2
                )
            ))
    return a_trace
def _check_for_lost_points(rectangles):

    for seg in rectangles:
        for next_segment in rectangles:
            if seg != next_segment:
                for lost_point in next_segment.lost_points:
                    if (seg.segment[0], seg.segment[1]) == lost_point:
                        if seg.segment[1]  == seg.segment[3] and next_segment.segment[0] == next_segment.segment[2]:
                            seg.segment[0] = next_segment.segment[0]
                    elif (seg.segment[2], seg.segment[3]) == lost_point:
                        if seg.segment[1] == seg.segment[3] and next_segment.segment[0] == next_segment.segment[2]:
                            seg.segment[0] = next_segment.segment[0]
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
                if seg.segment[0] - seg.segment[2] == 0 and seg2.segment[0] - seg2.segment[2] == 0:
                    if abs(seg.segment[0] - seg2.segment[0]) <= 60 and (min(seg2.segment[1], seg2.segment[3]) <= seg.segment[1] <= max(seg2.segment[1], seg2.segment[3]) or min(seg2.segment[1], seg2.segment[3]) <= seg.segment[3] <= max(seg2.segment[1], seg2.segment[3])):
                        print("True")
                        return True

                elif seg.segment[1] - seg.segment[3] == 0 and seg2.segment[1] - seg2.segment[3] == 0:
                    if abs(seg.segment[1] - seg2.segment[1]) <= 44 and (min(seg2.segment[0], seg2.segment[2]) <= seg.segment[0] <= max(seg2.segment[2], seg2.segment[0]) or min(seg2.segment[0], seg2.segment[2]) <= seg.segment[2] <= max(seg2.segment[2], seg2.segment[0])):
                        print("True")
                        return True
    print("False")
    return False

def initiate_write_traces(objects, all_paths,  port_coord, seg_list, scale_factor, net_list):
    trace_width = 30
    test = []

    for index, net in enumerate(all_paths):
        if not net == "local:net1" and not net =="local:net2" and not net == "local:VDD" and not net == "local:net3" and not net == "local:VSS" and not net == "local:I_BIAS" and not net == "local:net4" and not net == "local:net4" and not net == "net3" and not net == "net1" :

            net_rectangles = []
            for name, path in all_paths[net]:
                segments = segment_path(path)
                if len(segments) > 0:
                    net_rectangles.extend(map_path_to_rectangles(segments, port_coord, name))
            print("Stuck at _delete_duplicate")
            net_rectangles = _delete_duplicate_rectangles(net_rectangles)
            print("Stuck at _eliminate_rectangles")
            net_rectangles = _eliminate_rectangles(net_rectangles, trace_width)
            print("Stuck at _check_for_lost_points")
            net_rectangles =_check_for_lost_points(net_rectangles)

           # test.append(net_rectangles)

            #if test_redo == True:
                #net_rectangles = _eliminate_rectangles(net_rectangles, trace_width)
            objects.append(_write_traces(net_rectangles, trace_width, index, net))

  #  _check_net_constraint_vioaltion(test)

    return objects