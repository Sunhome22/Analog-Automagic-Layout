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
    y_params= {
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


def get_component_group_end_points_for_atr_sky130a_lib(self: object):

    component_group_sets = defaultdict(list)

    min_y_components = list(defaultdict(list))
    max_y_components = list(defaultdict(list))

    min_x_components = list(defaultdict(list))
    max_x_components = list(defaultdict(list))

    # Make sets of component groups
    for component in self.transistor_components:
        if component.group:
            component_group_sets[component.group].append(component)

    # Iterate over each set and their components within and get max- and min y position for each.
    for group, components in component_group_sets.items():
        components_y_placement = defaultdict(list)

        for component in components:
            components_y_placement[component.transform_matrix.f].append(component)

        min_y_components.append(min(components_y_placement.items()))
        max_y_components.append(max(components_y_placement.items()))

    # Iterate over each set and their components within and get max- and min x position for each.
    for group, components in component_group_sets.items():
        components_x_placement = defaultdict(list)

        for component in components:
            components_x_placement[component.transform_matrix.c].append(component)

        min_x_components.append(min(components_x_placement.items()))
        max_x_components.append(max(components_x_placement.items()))

    for components in max_y_components:
        for component in components[1]:
            print(f"pre_max_y: {component.name}")

    # Check for overlap of y-minimum components
    prev_y_min = None
    y_min_overlap_components_to_remove = []

    for i, (y, components) in enumerate(min_y_components):

        if prev_y_min:
            for component in components:

                if abs(y - prev_y_min) == component.bounding_box.y2:

                    # Take the maximum of the last two components that compared a y-distance to be
                    # less/equal to the bounding box.
                    y_min_overlap_components_to_remove.append(max(min_y_components[i - 1], min_y_components[i],
                                                                  key=lambda distance: (distance[0])))

        prev_y_min = y

    # Check for overlap of x-minimum components
    # prev_x_min = None
    # x_min_overlap_components_to_remove = []
    #
    # for i, (x, components) in enumerate(min_x_components):
    #
    #     if prev_x_min:
    #         for component in components:
    #
    #             if abs(x - prev_x_min) == component.bounding_box.x2:
    #                 # Take the maximum of the last two components that compared a y-distance to be
    #                 # less/equal to the bounding box.
    #                 x_min_overlap_components_to_remove.append(max(min_x_components[i - 1], min_x_components[i],
    #                                                               key=lambda distance: (distance[0])))
    #
    #     prev_x_min = x

    # Check for overlap of y-maximum components
    prev_y_max = None
    y_max_overlap_components_to_remove = []

    for i, (y, components) in enumerate(max_y_components):

        if prev_y_max is not None:
            for component in components:
                # Maybe there are some edge case here still!
                if abs(y - prev_y_max) == component.bounding_box.y2:

                    # Take the minimum of the last two components that compared a y-distance to be
                    # less/equal to the bounding box.
                    y_max_overlap_components_to_remove.append(min(max_y_components[i - 1], max_y_components[i],
                                                                  key=lambda distance: (distance[0])))
        prev_y_max = y

    # Check for overlap of x-maximum components
    # prev_x_max = None
    # x_max_overlap_components_to_remove = []
    #
    # for i, (x, components) in enumerate(max_x_components):
    #
    #     if prev_x_max is not None:
    #         for component in components:
    #             print(component)
    #             # Maybe there are some edge case here still!
    #             if abs(x - prev_x_max) == component.bounding_box.x2:
    #                 # Take the minimum of the last two components that compared a y-distance to be
    #                 # less/equal to the bounding box.
    #                 x_max_overlap_components_to_remove.append(min(max_x_components[i - 1], max_x_components[i],
    #                                                               key=lambda distance: (distance[0])))
    #     prev_x_max = x

    # Filter out y-minimum components that have been found to be overlapping
    for _, overlap_components in y_min_overlap_components_to_remove:
        min_y_components = [(y, [component for component in components if component not in overlap_components])
                            for y, components in min_y_components]
    min_y_components = [(y, components) for y, components in min_y_components if components]  # remove empty tuples

    # Filter out x-minimum components that have been found to be overlapping
    # for _, overlap_components in x_min_overlap_components_to_remove:
    #     min_x_components = [(x, [component for component in components if component not in overlap_components])
    #                         for x, components in min_x_components]
    # min_x_components = [(x, components) for x, components in min_x_components if components]  # remove empty tuples

    # Filter out y-maximum components that have been found to be overlapping
    for _, overlap_components in y_max_overlap_components_to_remove:
        max_y_components = [(y, [component for component in components if component not in overlap_components])
                            for y, components in max_y_components]
    max_y_components = [(y, components) for y, components in max_y_components if components]  # remove empty tuples

    # Filter out x-maximum components that have been found to be overlapping
    # for _, overlap_components in x_max_overlap_components_to_remove:
    #     max_x_components = [(x, [component for component in components if component not in overlap_components])
    #                         for x, components in max_x_components]
    # max_x_components = [(x, components) for x, components in max_x_components if components]  # remove empty tuples

    for components in min_x_components:
        for component in components[1]:
            print(f"minimum_x: {component.name}")

    for components in max_x_components:
        for component in components[1]:
            print(f"max_x: {component.name}")

    for components in min_y_components:
        for component in components[1]:
            print(f"minimum_y: {component.name}")

    for components in max_y_components:
        for component in components[1]:
            print(f"max_y: {component.name}")

    # Update transistor components with end point information
    for component in self.components:
        if isinstance(component, Transistor):

            for _, y_components in min_y_components:
                for y_comp in y_components:

                    for _, x_components in min_x_components:
                        for x_comp in x_components:
                            if x_comp == component:
                                if y_comp == x_comp:
                                    #print(f"min x: {x_comp.name}")
                                    component.group_endpoint = "no_rail_bot"

                    for _, x_components in max_x_components:
                        for x_comp in x_components:

                            if x_comp == component:
                                if y_comp != x_comp:
                                    #print(f"max x: {x_comp.name}")
                                    component.group_endpoint = "no_rail_bot"

            # for _, mx_y_components in max_y_components:
            #     for mx_y_comp in mx_y_components:
            #
            #         for _, mi_x_components in min_x_components:
            #             for mi_x_comp in mi_x_components:
            #                 if mi_x_comp == component:
            #                     if mx_y_comp == mi_x_comp:
            #                         if component.group_endpoint == "no_rail_bot":
            #                             component.group_endpoint = "no_rail_top/bot"
            #
            #                         else:
            #                             component.group_endpoint = "no_rail_top"
            #
            #         for _, mx_x_components in max_x_components:
            #             for mx_x_comp in mx_x_components:
            #                 if mx_x_comp == component:
            #                     if mx_y_comp != mx_x_comp:
            #                         if component.group_endpoint == "no_rail_bot":
            #                             component.group_endpoint = "no_rail_top/bot"
            #
            #                         else:
            #                             component.group_endpoint = "no_rail_top"

                # for comp in components:
                #     if comp == component:
                #         if component.group_endpoint == "rail_bot":
                #             component.group_endpoint = "rail_top/bot"
                #         else:
                #             component.group_endpoint = "rail_top"

    # # Update transistor components with end point information
    # for component in self.components:
    #     if isinstance(component, Transistor):
    #
    #
    #                     component.group_endpoint = "no_rail_bot"
    #
    #         for _, components in max_x_components:
    #             for comp in components:
    #                 if comp == component:
    #                     if component.group_endpoint == "no_rail_bot":
    #                         component.group_endpoint = "no_rail_top/bot"
    #                     else:
    #                         component.group_endpoint = "no_rail_top"


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



