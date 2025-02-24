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
from numpy.ma.core import append

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


def map_segments_to_rectangles(path_segments, port_coord, connection_name):
    rectangles = []
    length_x, length_y = calculate_directional_lengths(path_segments)

    # Get the real-world start and end coordinates
    start_name, end_name = connection_name.split("_",1)
    start_real = port_coord[start_name]
    end_real = port_coord[end_name]

    cumulative_x = 0
    cumulative_y = 0
   # minimum_segment_length = 170


    for segment in path_segments:
        start_x, start_y = start_real if not rectangles else (rectangles[-1].area.x2, rectangles[-1].area.y2)

        if segment[0][0] == segment[-1][0]:  # Vertical segment
            segment_length = segment[-1][1] - segment[0][1]
            cumulative_y += abs(segment_length)
            end_x = start_x
            if end_real[1] > start_real[1]:
                end_y = start_real[1] + (end_real[1] - start_real[1]) * (cumulative_y / length_y)
            # elif end_real[1] == start_real[1]:
            #     minimum_segment_length = minimum_segment_length * (-1 if segment_length < 0 else 1)
            #     end_y = start_real[1] + minimum_segment_length * (cumulative_y / length_y)
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
            return

        rectangles.append(TraceRectangle(area=RectArea(x1=start_x, y1=start_y, x2=end_x, y2=end_y), lost_points=[]))

    return rectangles

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




def trace_stretch(switch_bool: bool, trace_width: int, index: int, length: int) -> tuple[int,int]:
    return 0,0
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



def _rectangle_consolidation(rectangles, segment_direction):

    new_rectangle = TraceRectangle(area = RectArea(), lost_points=[])

    if segment_direction == "h":

        min_x = min(min(sublist.area.x1, sublist.area.x2) for sublist in rectangles)
        max_x = max(max(sublist.area.x1, sublist.area.x2) for sublist in rectangles)
        y = rectangles[0].area.y1

        new_rectangle.area = RectArea(x1 = min_x, y1 = y, x2 = max_x, y2 = y)

        for sublist in rectangles:

            if (sublist.area.x1, sublist.area.y1) != (min_x, y) and (sublist.area.x1, sublist.area.y1) != (max_x, y):
                new_rectangle.lost_points.append((sublist.area.x1,sublist.area.y1))

            elif (sublist.area.x2, sublist.area.y2) != (min_x, y) and (sublist.area.x2, sublist.area.y2) != (max_x, y):
                new_rectangle.lost_points.append((sublist.area.x2, sublist.area.y2))

            if len(sublist.lost_points) > 0:
                new_rectangle.lost_points.extend(sublist.lost_points)


    elif segment_direction == "v":

        min_y = min(min(sublist.area.y1, sublist.area.y2) for sublist in rectangles)
        max_y = max(max(sublist.area.y1, sublist.area.y2) for sublist in rectangles)
        x = rectangles[0].area.x1

        new_rectangle.area = RectArea(x1=x, y1=min_y, x2=x, y2=max_y)

        for sublist in rectangles:

            if (sublist.area.x1, sublist.area.y1) != (x, min_y) and (sublist.area.x1, sublist.area.y1) != (x, max_y):
                new_rectangle.lost_points.append((sublist.area.x1, sublist.area.y1))

            elif (sublist.area.x2, sublist.area.y2) != (x, min_y) and (sublist.area.x2, sublist.area.y2) != (x, max_y):
                new_rectangle.lost_points.append((sublist.area.x2, sublist.area.y2))

            if len(sublist.lost_points) > 0:
                new_rectangle.lost_points.extend(sublist.lost_points)

    else:
        print("[ERROR] Direction invalid")

    return new_rectangle

def _eliminate_rectangles(rectangles, trace_width):
    spacing_m2 = 14 #horizontal
    spacing_m3 = 30 #vertical
    print("Rectangles length")
    print(len(rectangles))

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
            rectangles.append(_rectangle_consolidation(temp_seg_list, direction_rectangle_1))
            rectangles_duplicate.append(rectangles[-1])
           # rectangle_list.append(rectangles[-1])

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

def initiate_write_traces(objects, all_paths,  port_coordinates, seg_list, scale_factor, net_list):
    trace_width = 30
    test = []

    for index, net in enumerate(all_paths):
        #if not net == "local:net1" and not net =="local:net2" and not net == "local:VDD" and not net == "local:net3" and not net == "local:VSS" and not net == "local:I_BIAS" and not net == "local:net4" and not net == "net4" and not net == "net3" and not net == "net1":
        if not net == "net1" and not net == "net3" and not net == "net4" :
      #  if not net == "net3" and not net == "net1" and not net == "net2" and not net == "net4":

            net_rectangles = []
            for name, path in all_paths[net]:

                segments = segment_path(path)


                if len(segments) > 0:

                    mapped_rectangles = map_segments_to_rectangles(segments, port_coordinates, name)


                    net_rectangles.extend(_check_rectangle_port_overlap(mapped_rectangles, name, objects, trace_width))
                    break

            print(f"Length of net rectangles before delete duplicate: {len(net_rectangles)}")
            print("Stuck at _delete_duplicate")
           # net_rectangles = _delete_duplicate_rectangles(net_rectangles)

            print(f"Length of net rectangles before eliminate rectangles: {len(net_rectangles)}")
           # net_rectangles = _eliminate_rectangles(net_rectangles, trace_width)
            print("Stuck at _check_for_lost_points")
            print(f"Length of net rectangles before lost points: {len(net_rectangles)}")
            #net_rectangles =_check_for_lost_points(net_rectangles)
            print(f"Length of net rectangles end: {len(net_rectangles)}")

           # test.append(net_rectangles)

            #if test_redo == True:
                #net_rectangles = _eliminate_rectangles(net_rectangles, trace_width)
            objects.append(_write_traces(net_rectangles, trace_width, index, net))

      #  _check_net_constraint_vioaltion(test)

    return objects