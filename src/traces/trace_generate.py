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



def map_segments_to_rectangles(path_info, scale_factor, used_area):

    rectangles = []

    adjustment = (used_area[0] - 500, used_area[1]-500)

    offset_x, offset_y = calculate_offset(goal_nodes=path_info["goal_nodes"],
                              real_nodes=path_info["real_goal_nodes"],
                              scale_factor=scale_factor,
                                adjustment =adjustment)



    for segment in path_info["segments"]:
        start, end = calculate_real_coordinates(start_grid_point=segment[0],
                                                end_grid_point=segment[-1],
                                                scale_factor=scale_factor,
                                                offset_x=offset_x,
                                                offset_y=offset_y,
                                                adjustment=adjustment)

        rectangles.append(TraceRectangle(area=RectArea(x1=start[0], y1=start[1], x2=end[0], y2=end[1]), lost_points=[]))




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



def initiate_write_traces(components, all_paths,  scale_factor, trace_width, used_area):



    for index, net in enumerate(all_paths):



        mapped_rectangles = map_segments_to_rectangles(path_info=all_paths[net],
                                                           scale_factor=scale_factor,
                                                           used_area=used_area)









        components.append(_write_traces(mapped_rectangles, trace_width, index, net))

          #  _check_net_constraint_vioaltion(test)

    return components