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

# ===================================================== Libraries ======================================================
import os
import re
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from itertools import groupby
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict
from logger.logger import get_a_logger
from circuit.circuit_components import (RectArea, RectAreaLayer, Transistor, Capacitor, Resistor, Pin, CircuitCell,
                                        TraceNet, RectAreaLayer)

# ======================================================================================================================
# ================================================ ATR SKY130A handling ================================================
# ======================================================================================================================


# ============================================= Trace generator functions ==============================================
def generate_local_traces_for_atr_sky130a_lib(self: object):
    for component in self.transistor_components:
        if component.schematic_connections['B'] == component.schematic_connections['S']:
            __local_bulk_to_source_connection_for_atr_sky130a_lib(self=self, component=component)

        if component.schematic_connections['G'] == component.schematic_connections['D']:
            __local_gate_to_drain_connection_for_sky130a_lib(self=self, component=component)

    for component in self.transistor_components:
        if (re.search(r".*VDD.*", component.schematic_connections['B']) or
                re.search(r".*VSS.*", component.schematic_connections['B'])):
            __local_bulk_to_rail_connection_for_sky130a_lib(self=self, component=component,
                                                            rail=component.schematic_connections['B'])


def __local_bulk_to_source_connection_for_atr_sky130a_lib(self: object, component: object):
    trace = TraceNet(name=f"{component.name}_B_S", cell=component.cell)
    trace.instance = trace.__class__.__name__

    bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'))
    source_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'S'))
    source_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'S'))
    source_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'S'))

    trace.segments=[RectAreaLayer(layer='locali', area=RectArea(x1=bulk_x1 + component.transform_matrix.c,
                                                                y1=source_y1 + component.transform_matrix.f,
                                                                x2=source_x2 + component.transform_matrix.c,
                                                                y2=source_y2 + component.transform_matrix.f))]
    self.components.append(trace)


def __local_gate_to_drain_connection_for_sky130a_lib(self: object, component: object):
    trace = TraceNet(name=f"{component.name}_G_D", cell=component.cell)
    trace.instance = trace.__class__.__name__

    gate_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'G'))
    gate_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'G'))
    drain_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'D'))
    gate_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'G'))
    gate_mirrored_x2 = component.bounding_box.x2 - gate_x1

    trace.segments = [RectAreaLayer(layer='locali', area=RectArea(x1=drain_x1 + component.transform_matrix.c,
                                                                  y1=gate_y1 + component.transform_matrix.f,
                                                                  x2=gate_mirrored_x2 + component.transform_matrix.c,
                                                                  y2=gate_y2 + component.transform_matrix.f))]
    self.components.append(trace)


def __local_bulk_to_rail_connection_for_sky130a_lib(self: object, component: object, rail):
    y_params = {
        'rail_top': (component.bounding_box.y2, component.group_endpoint_bounding_box.y2 // 2),
        'rail_bot': (component.bounding_box.y1, -component.group_endpoint_bounding_box.y2 // 2),
    }

    if component.group_endpoint:

        if component.group_endpoint == 'rail_top/bot':
            generate_bulk_to_rail_segments(self=self, rail=rail, component=component,
                                           y_params=y_params['rail_top'], group_endpoint="TOP")
            generate_bulk_to_rail_segments(self=self, rail=rail, component=component,
                                           y_params=y_params['rail_bot'], group_endpoint="BOT")

        if component.group_endpoint == 'rail_top' or component.group_endpoint == 'rail_bot':
            generate_bulk_to_rail_segments(self=self, rail=rail, component=component,
                                           y_params=y_params[component.group_endpoint],
                                           group_endpoint=component.group_endpoint.upper())


def generate_bulk_to_rail_segments(self, rail, component, y_params, group_endpoint):

    trace = TraceNet(name=f"{component.name}_B_{rail}_{group_endpoint}", cell=component.cell)
    trace.instance = trace.__class__.__name__

    bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'))
    bulk_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'B'))
    bulk_width = abs(bulk_x2 - bulk_x1)

    for structural_component in self.structural_components:
        if re.search(rf".*{rail}.*", structural_component.name):
            middle_segment = RectArea(x1=structural_component.layout.area.x1,
                                      y1=y_params[0] + component.transform_matrix.f - (bulk_width // 2) + y_params[1],
                                      x2=structural_component.layout.area.x2,
                                      y2=y_params[0] + component.transform_matrix.f + (bulk_width // 2) + y_params[1])

            left_segment = RectArea(x1=structural_component.layout.area.x1,
                                    y1=y_params[0] + component.transform_matrix.f - bulk_width // 2 + y_params[1],
                                    x2=structural_component.layout.area.x1 + self.RAIL_RING_WIDTH,
                                    y2=structural_component.layout.area.y2)

            right_segment = RectArea(x1=structural_component.layout.area.x2 - self.RAIL_RING_WIDTH,
                                     y1=y_params[0] + component.transform_matrix.f - bulk_width // 2 + y_params[1],
                                     x2=structural_component.layout.area.x2,
                                     y2=structural_component.layout.area.y2)

            # The two additional segments (left_segment and right_segment) are used for forcing via generation, and
            # remove the need for special handling
            trace.segments.append(RectAreaLayer(layer='m1', area=left_segment))
            trace.segments.append(RectAreaLayer(layer='locali', area=middle_segment))
            trace.segments.append(RectAreaLayer(layer='m1', area=right_segment))
    self.components.append(trace)


def get_component_group_endpoints_for_atr_sky130a_lib(self: object):
    component_names_and_cords = []
    overlapping_components_x_sort = []
    overlapping_components_y_sort = []

    for component in self.transistor_components:
        component_names_and_cords.append((component, component.transform_matrix.c, component.transform_matrix.f))

    # Sorts components first by x and then by y (ascending order)
    sorted_components_by_x = sorted(component_names_and_cords, key=lambda item: (item[1], item[2]))

    # Sorts components first by y and then by x (ascending order)
    sorted_components_by_y = sorted(component_names_and_cords, key=lambda item: (item[2], item[1]))


    # Get overlapping components with x direction sorting
    prev_component_x_sort = None
    current_component_x_sort = None
    for component in sorted_components_by_x:

        if prev_component_x_sort:
            if component[2] - prev_component_x_sort[2] == component[0].bounding_box.y2:

                # Don't add the same component twice
                if prev_component_x_sort != current_component_x_sort:
                    overlapping_components_x_sort.append((prev_component_x_sort[0],
                                                          prev_component_x_sort[1], prev_component_x_sort[2]))

                overlapping_components_x_sort.append((component[0], component[1], component[2]))
                current_component_x_sort = (component[0], component[1], component[2])
            else:
                overlapping_components_x_sort.append((0,0,0)) # adds blanks between every overlapping set of components

        prev_component_x_sort = (component[0], component[1], component[2])

    # Get overlapping components with y direction sorting
    prev_component_y_sort = None
    current_component_y_sort = None
    for component in sorted_components_by_y:

        if prev_component_y_sort:
            if component[1] - prev_component_y_sort[1] == component[0].bounding_box.x2:

                # Don't add the same component twice
                if prev_component_y_sort != current_component_y_sort:
                    overlapping_components_y_sort.append((prev_component_y_sort[0],
                                                          prev_component_y_sort[1], prev_component_y_sort[2]))

                overlapping_components_y_sort.append((component[0], component[1], component[2]))
                current_component_y_sort = (component[0], component[1], component[2])
            else:
                overlapping_components_y_sort.append((0, 0, 0))  # adds blanks between every overlapping set of components

        prev_component_y_sort = (component[0], component[1], component[2])

    # Print sorted list
    print("Sorted:")
    for component in sorted_components_by_x:
        print(component[0].name, component[1], component[2])

    #print("Overlapping:")
    #for component in overlapping_components:
    #    print(component[0].name, component[1], component[2])



    # Place no overlap top and bot endpoints
    grouped_overlap_lists_x_sort = [list(group) for _, group in groupby(overlapping_components_x_sort, key=lambda x: x[1])]
    grouped_overlap_lists_y_sort = [list(group) for _, group in groupby(overlapping_components_y_sort, key=lambda x: x[2])]

    # for grouped_overlap_list in grouped_overlap_lists_y_sort:
    #     for component in grouped_overlap_list:
    #         if component[0] == 0:
    #             print("empty")
    #         else:
    #             print(component[0].name)

    # If I don't have it in y_sort it must be a rail top or bot somewhere. Search through x_sort and find it.
    # List position in x_sort defines if it is a top or bot
    # if I have multiple components not defined in y_sort. I need to do the same thing, however they may be in the same x_sort
    # but can also not be. Deal with this also.

    for component in self.transistor_components:
        for grouped_overlap_list in grouped_overlap_lists:
            if component == grouped_overlap_list[0][0]:
                component.group_endpoint = 'no_rail_bot'
            if component == grouped_overlap_list[-1][0]:
                component.group_endpoint = 'no_rail_top'



    # Grouping using groupby
    # prev_overlap_component = None
    # for component in overlapping_components:
    #     if prev_overlap_component:
    #         if prev_overlap_component[1] == component[1]:
    #             print(component[0].name)
    #
    #
    #     prev_overlap_component = component




    # Logging
    for component in self.components:
        if isinstance(component, Transistor):
            self.logger.info(f"Component '{component.name}' "
                             f"was assigned group endpoint '{component.group_endpoint}'")


# ========================================== Magic layout creator functions ============================================


def place_transistor_endpoints_for_atr_sky130a_lib(self: object, component: object):
    if isinstance(component, Transistor):
        layout_name_top = re.sub(r".{3}$", "TAPTOP", component.layout_name)
        layout_name_bot = re.sub(r".{3}$", "TAPBOT", component.layout_name)

        if component.group_endpoint == "rail_top":

            self.magic_file_lines.extend([
                f"use {layout_name_top} {component.group}_{component.name}_TAPTOP {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f + component.bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint == "rail_bot":
            self.magic_file_lines.extend([
                f"use {layout_name_bot} {component.group}_{component.name}_TAPBOT {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f - component.group_endpoint_bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint == "rail_top/bot":

            self.magic_file_lines.extend([
                f"use {layout_name_bot} {component.group}_{component.name}_TAPBOT {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f - component.group_endpoint_bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

            self.magic_file_lines.extend([
                f"use {layout_name_top} {component.group}_{component.name}_TAPTOP {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f + component.bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint == "no_rail_top":

            self.magic_file_lines.extend([
                f"use {layout_name_top} {component.group}_{component.name}_TAPTOP {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f + component.bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint == "no_rail_bot":
            self.magic_file_lines.extend([
                f"use {layout_name_bot} {component.group}_{component.name}_TAPBOT {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f - component.group_endpoint_bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint == "no_rail_top/bot":

            self.magic_file_lines.extend([
                f"use {layout_name_bot} {component.group}_{component.name}_TAPBOT {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f - component.group_endpoint_bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

            self.magic_file_lines.extend([
                f"use {layout_name_top} {component.group}_{component.name}_TAPTOP {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f + component.bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])




# ========================================== Magic component parser functions ==========================================


def get_overlap_difference_for_atr_sky130a_lib(self: object, text_line: str, component: object):
    if component.type == "nmos" or component.type == "pmos":

        if self.found_transistor_well:
            line_words = text_line.split()
            self.transistor_well_size = RectArea(x1=int(line_words[1]), y1=int(line_words[2]), x2=int(line_words[3]),
                                                 y2=int(line_words[4]))
            self.found_transistor_well = False

        elif re.search(r'<< nwell >>', text_line) or re.search(r'<< pwell >>', text_line):
            # Next line contains well size info
            self.found_transistor_well = True

        # Calculate overlap difference after bounding box has been set
        elif self.found_bounding_box:

            x_difference = int((abs(self.transistor_well_size.x1) + abs(self.transistor_well_size.x2)
                                - (abs(component.bounding_box.x1) + abs(component.bounding_box.x2))) / 2)
            y_difference = int((abs(self.transistor_well_size.y1) + abs(self.transistor_well_size.y2)
                                - (abs(component.bounding_box.y1) + abs(component.bounding_box.y2))) / 2)

            component.overlap_distance.x = x_difference
            component.overlap_distance.y = y_difference

            self.found_bounding_box = False

    self.found_bounding_box = False


def get_component_bounding_box_for_atr_sky130a_lib(self: object, text_line: str, component: object):

    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.bounding_box.set(map(int, text_line_words[2:6]))
        self.found_bounding_box = True


def get_component_endpoint_bounding_box_for_atr_sky130a_lib(text_line: str, component: object):

    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.group_endpoint_bounding_box.set(map(int, text_line_words[2:6]))


def magic_component_parsing_for_atr_sky130a_lib(self: object, layout_file_path: str, component: object):
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_bounding_box_for_atr_sky130a_lib(text_line=text_line, component=component, self=self)
                get_overlap_difference_for_atr_sky130a_lib(text_line=text_line, component=component, self=self)
    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")

    # It's safe to assumes that top and bottom taps have equal bounding box.
    transistor_endpoint_layout_name = re.sub(r".{3}$", "TAPTOP", component.layout_name)
    layout_file_path = os.path.expanduser(f"{self.current_component_library_path}/"
                                          f"{transistor_endpoint_layout_name}.mag")
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_endpoint_bounding_box_for_atr_sky130a_lib(text_line=text_line, component=component)

    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")



