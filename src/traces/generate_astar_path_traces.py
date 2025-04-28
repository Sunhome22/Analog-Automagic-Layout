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

# ================================================== Libraries =========================================================

from dataclasses import dataclass
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, TraceNet, \
    RectAreaLayer
from logger.logger import get_a_logger
import tomllib
import re
import libraries.atr_sky130a_lib as atr


# =============================================== Data classes =========================================================
@dataclass
class TraceRectangle:
    area: RectArea
    lost_points: list

    def __init__(self, area: RectArea, lost_points: list):
        self.area = area
        self.lost_points = lost_points
# =============================================== Trace Generator ======================================================


class GenerateAstarPathTraces:
    logger = get_a_logger(__name__)

    def __init__(self, components, paths, net_list, used_area):
        self.components = components
        self.paths = paths
        self.net_list = net_list
        self.used_area = used_area

        # Load config
        self.config = self.__load_config()
        self.TRACE_WIDTH = self.config["generate_grid"]["TRACE_WIDTH"]
        self.SCALE_FACTOR = self.config["generate_grid"]["SCALE_FACTOR"]
        self.GRID_LEEWAY_X = self.config["generate_grid"]["GRID_LEEWAY_X"]
        self.GRID_LEEWAY_Y = self.config["generate_grid"]["GRID_LEEWAY_Y"]

        for component in self.components:
            # There should only be one CircuitCell when generating A* paths traces
            if isinstance(component, CircuitCell):
                self.circuit_cell = component

        # Variables for trace generate
        self.scale_offset_x = 0
        self.scale_offset_y = 0
        self.mapped_rectangles = []
        self.adjustment = self.used_area.x1 - self.GRID_LEEWAY_X, self.used_area.y1 - self.GRID_LEEWAY_Y

        self.__generate_traces()

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def __calculate_offset(self, goal_nodes, real_nodes,):
        self.scale_offset_x, self.scale_offset_y = 0, 0
        for index in range(len(goal_nodes)-1):
            self.scale_offset_x += real_nodes[index][0] - (goal_nodes[index][0]*self.SCALE_FACTOR + self.adjustment[0])
            self.scale_offset_y += real_nodes[index][1] - (goal_nodes[index][1]*self.SCALE_FACTOR + self.adjustment[1])

        self.scale_offset_x /= len(goal_nodes) if len(goal_nodes) > 0 else 1
        self.scale_offset_y /= len(goal_nodes) if len(goal_nodes) > 0 else 1

    def __calculate_real_coordinates(self, segment):
        start_x, start_y = segment[0]
        end_x, end_y = segment[-1]

        return ((self.scale_offset_x + self.adjustment[0] + start_x * self.SCALE_FACTOR,
                 self.scale_offset_y + self.adjustment[1] + start_y * self.SCALE_FACTOR),
                (self.scale_offset_x + self.adjustment[0] + end_x * self.SCALE_FACTOR,
                 self.scale_offset_y + self.adjustment[1] + end_y * self.SCALE_FACTOR))

    def __map_segments_to_rectangles(self, path_info):
        rectangles = []
        self.__calculate_offset(goal_nodes=path_info["goal_nodes"],
                                real_nodes=path_info["real_goal_nodes"])

        for segment in path_info["segments"]:
            start, end = self.__calculate_real_coordinates(segment)
            rectangles.append(TraceRectangle(area=RectArea(x1=start[0], y1=start[1], x2=end[0], y2=end[1]),
                                             lost_points=[]))

        self.mapped_rectangles = rectangles

    def __trace_stretch(self, switch_start: bool, index: int) -> tuple[int, int]:
        length = len(self.mapped_rectangles)

        match (index, length, switch_start):

            case (0, 1, _):
                return 0, 0
            case (0, l, 1) if l > 1:
                return -self.TRACE_WIDTH // 2, 0
            case (0, l, 0) if l > 1:
                return 0, self.TRACE_WIDTH // 2
            case (i, l, 1) if i == l - 1:
                return 0, self.TRACE_WIDTH // 2
            case (i, l, 0) if i == l - 1:
                return -self.TRACE_WIDTH // 2, 0
            case _:
                return -self.TRACE_WIDTH // 2, self.TRACE_WIDTH // 2

    def __write_traces(self, net):
        trace = TraceNet()
        trace.instance = trace.__class__.__name__
        trace.named_cell = self.circuit_cell.named_cell
        trace.cell_chain = self.circuit_cell.cell_chain
        trace.cell = self.circuit_cell.cell
        trace.name = net

        for index, rectangle in enumerate(self.mapped_rectangles):

            if rectangle.area.x1 == rectangle.area.x2:

                if rectangle.area.y1 > rectangle.area.y2:
                    rectangle.area.y1, rectangle.area.y2 = rectangle.area.y2, rectangle.area.y1
                    switch_start = True
                else:
                    switch_start = False

                stretch_start, stretch_end = self.__trace_stretch(switch_start=switch_start, index=index)

                trace.segments.append(RectAreaLayer(
                    layer="m3",
                    area=RectArea(
                        x1=int(rectangle.area.x1) - self.TRACE_WIDTH // 2,  # Adding width to trace
                        y1=int(rectangle.area.y1 + stretch_start),
                        x2=int(rectangle.area.x2) + self.TRACE_WIDTH // 2,
                        y2=int(rectangle.area.y2 + stretch_end)
                    )
                ))
            elif rectangle.area.y1 == rectangle.area.y2:

                if rectangle.area.x1 > rectangle.area.x2:
                    rectangle.area.x1, rectangle.area.x2 = rectangle.area.x2, rectangle.area.x1
                    switch_start = True
                else:
                    switch_start = False
                stretch_start, stretch_end = self.__trace_stretch(switch_start=switch_start, index=index)

                trace.segments.append(RectAreaLayer(
                    layer="m2",
                    area=RectArea(
                        x1=int(rectangle.area.x1) + stretch_start,  # Adding width to trace
                        y1=int(rectangle.area.y1 - self.TRACE_WIDTH // 2),
                        x2=int(rectangle.area.x2) + stretch_end,
                        y2=int(rectangle.area.y2 + self.TRACE_WIDTH // 2)
                    )
                ))
            else:
                self.logger.error(f"Illegal trace with size: x1: {rectangle.area.x1}, y1: {rectangle.area.y1}, "
                                  f"x2: {rectangle.area.x2}, y2: {rectangle.area.y2}")

        self.components.append(trace)

    def __write_labels(self, net):
        if net in self.net_list.pin_nets:
            self.logger.info("start wrtie labels")
            for obj in self.components:
                if isinstance(obj, Pin) and obj.name == net:
                    self.logger.info("1")
                    if len(self.components[-1].segments) > 1:
                        obj.layout = RectAreaLayer(layer=self.components[-1].segments[0].layer,
                                                   area=self.components[-1].segments[0].area)
                        self.logger.info("2")
                    else:
                        self.logger.info("3")
                        for new_obj in self.components:
                            if not isinstance(new_obj, (Pin, TraceNet, CircuitCell)):
                                for port in new_obj.schematic_connections:
                                    if new_obj.schematic_connections[port] == net:
                                        for p in new_obj.layout_ports:
                                            if p.type == port:
                                                self.logger.info("4")
                                                obj.layout = RectAreaLayer(layer=p.layer, area=RectArea())
                                                obj.layout.area.x1 = p.area.x1 + new_obj.transform_matrix.c
                                                obj.layout.area.x2 = p.area.x2 + new_obj.transform_matrix.c
                                                obj.layout.area.y1 = p.area.y1 + new_obj.transform_matrix.f
                                                obj.layout.area.y2 = p.area.y2 + new_obj.transform_matrix.f

    def __generate_traces(self):

        for net in self.paths:
            self.__map_segments_to_rectangles(path_info=self.paths[net])
            self.__write_traces(net=net)
            self.__write_labels(net=net)

    def get(self):
        return self.components


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
