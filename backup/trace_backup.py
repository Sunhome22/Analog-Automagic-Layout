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
from dataclasses import dataclass
import re
import math


from circuit.circuit_components import Trace, RectAreaLayer, RectArea
from json_tool.json_converter import save_to_json
from magic.magic_layout_creator import MagicLayoutCreator


def direction(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return dx, dy


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


def map_path_to_rectangles(path_segments, port_coord, connection_info):
    rectangles = []
    length_x, length_y = calculate_directional_lengths(path_segments)

    # Get the real-world start and end coordinates
    start_real = port_coord[f"{connection_info.start_comp_id}{connection_info.start_area}"][0]
    end_real = port_coord[f"{connection_info.end_comp_id}{connection_info.end_area}"][0]

    cumulative_x = 0
    cumulative_y = 0



    for segment in path_segments:
        start_x, start_y = start_real if not rectangles else (rectangles[-1][2], rectangles[-1][3])

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

        rectangles.append([start_x, start_y, end_x, end_y])

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

def _remove_duplicates(my_list: list) -> list:
    seen = set()
    unique_data = []
    for item in my_list:
        # Normalize the tuple by sorting its elements
        normalized = tuple(sorted(item))
        if normalized not in seen:
            seen.add(normalized)
            unique_data.append(item)
    return unique_data



def _eliminate_segments(seg_list, scale_factor, net_list):
    spacing_m2 = 14 #vertical
    spacing_m3 = 30 #horizontal
    segment_list_vertical = {}
    segment_list_horizontal = {}
    for key in seg_list:
        segments = seg_list[key][:]
        segments_duplicate = seg_list[key][:]

        for path_segment_1 in segments:
            temp_seg_list =path_segment_1
            index_list = []
            direction_segment_1 = "v" if path_segment_1[0][0] != path_segment_1[0][1] else "h"
            direction_index = 1 if path_segment_1[0][0] != path_segment_1[0][1] else 0
            for index, path_segment_2 in enumerate(segments_duplicate):
                direction_segment_2 = "v" if path_segment_1[0][0] != path_segment_1[0][1] else "h"
                if direction_segment_1==direction_segment_2 and path_segment_1 != path_segment_2:
                    if direction_segment_1 == "h" and path_segment_1[0][1]-path_segment_2[0][1] <=30+30/scale_factor: #horizontal, m3
                        temp_seg_list.append(path_segment_2)
                        index_list.append(index)
                    elif direction_segment_1=="v" and path_segment_1[0][0] - path_segment_2[0][0] <= 30 + 14 / scale_factor:  # vertical, m2
                        temp_seg_list.append(path_segment_2)
                        index_list.append(index)

            for i in index_list:
                del segments_duplicate[i]

            for i in range(1,temp_seg_list):
                temp_seg_list[i][direction_index] = temp_seg_list[0][direction_index]

            temp_seg_list = _remove_duplicates(temp_seg_list)

            if direction_index:
                segment_list_vertical.append(temp_seg_list)
            else:
                segment_list_horizontal.append(temp_seg_list)
    segment_list_vertical.extend(segment_list_horizontal)
    return segment_list_vertical

def write_traces(objects, path, path_names,  port_coord, seg_list, scale_factor, net_list):
    trace_width = 30
    segment_list = _eliminate_segments(seg_list, scale_factor, net_list)
    i = 0
    segments = []
    for net in net_list:
        i+=1
        a_trace = Trace()
        a_trace.instance = a_trace.__class__.__name__  # Add instance type
        a_trace.number_id = i
        a_trace.name =net
        #a_trace.cell = path_names[index].cell
        for p in path:
            if p[0] == net:
                segments.extend(segment_path(p))

        if len(segments) > 0:
            rectangles = map_path_to_rectangles(segments, port_coord, path_names[index])

            for i, rect in enumerate(rectangles):
                if rect[0] == rect[2]:  # Vertical
                    if rect[1] > rect[3]:  # Ensure y1 < y2
                        rect[1], rect[3] = rect[3], rect[1]
                        switched_start_end = True
                    else:
                        switched_start_end = False

                    added_length_start, added_length_end = trace_stretch(switched_start_end, trace_width, i, len(rectangles))
                    a_trace.segments.append(RectAreaLayer(
                        layer="m2",
                            area=RectArea(
                                x1=int(rect[0]) - trace_width // 2, #Adding width to trace
                                y1=int(rect[1] + added_length_start),
                                x2=int(rect[2]) + trace_width // 2,
                                y2=int(rect[3] + added_length_end)
                            )
                        ))
                elif rect[1] == rect[3]:  # Horizontal
                    if rect[0] > rect[2]:  # Ensure x1 < x2
                        rect[0], rect[2] = rect[2], rect[0]
                        switched_start_end = True
                    else:
                        switched_start_end = False
                    added_length_start, added_length_end = trace_stretch(switched_start_end, trace_width, i,
                                                                             len(rectangles))
                    a_trace.segments.append(RectAreaLayer(
                            layer="m3",
                            area=RectArea(
                                x1=int(rect[0] + added_length_start),
                                y1=int(rect[1]) - trace_width // 2,
                                x2=int(rect[2] + added_length_end),
                                y2=int(rect[3]) + trace_width // 2
                            )
                        ))


            objects.append(a_trace)

    return objects