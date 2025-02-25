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

        if re.search(r".*VDD.*", component.schematic_connections['B']):
            __local_bulk_to_vdd_connection_for_sky130a_lib(self=self, component=component)


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


def __local_bulk_to_vdd_connection_for_sky130a_lib(self: object, component: object):
    trace = TraceNet(name=f"{component.name}_B_VDD", cell=component.cell)
    trace.instance = trace.__class__.__name__

    if component.group_endpoint == 'top':
        for structural_component in self.structural_components:
            print(structural_component)
            if re.search(r".*VDD.*", structural_component.name):
                bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'))
                bulk_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'B'))
                bulk_width = abs(bulk_x2-bulk_x1)
                main_segment = RectArea(x1=structural_component.layout.area.x1,
                                        y1=component.bounding_box.y2 + component.transform_matrix.f - bulk_width // 2
                                           + component.group_endpoint_bounding_box.y2 // 2,
                                        x2=structural_component.layout.area.x2,
                                        y2=component.bounding_box.y2 + component.transform_matrix.f + bulk_width // 2
                                           + component.group_endpoint_bounding_box.y2 // 2)

                left_segment = RectArea(x1=structural_component.layout.area.x1,
                                        y1=component.bounding_box.y2 + component.transform_matrix.f - bulk_width // 2
                                           + component.group_endpoint_bounding_box.y2 // 2,
                                        x2=structural_component.layout.area.x1 + self.RAIL_RING_WIDTH,
                                        y2=structural_component.layout.area.y2)

                right_segment = RectArea(x1=structural_component.layout.area.x2 - self.RAIL_RING_WIDTH,
                                         y1=component.bounding_box.y2 + component.transform_matrix.f - bulk_width // 2
                                            + component.group_endpoint_bounding_box.y2 // 2,
                                         x2=structural_component.layout.area.x2,
                                         y2=structural_component.layout.area.y2)

                # The two additional segments (left_segment and right_segment) are used for forcing via generation.
                # These remove the need for special handling
                trace.segments.append(RectAreaLayer(layer='m1', area=left_segment))
                trace.segments.append(RectAreaLayer(layer='locali', area=main_segment))
                trace.segments.append(RectAreaLayer(layer='m1', area=right_segment))
        self.components.append(trace)

    if component.group_endpoint == 'bottom':
        for structural_component in self.structural_components:
            if re.search(r".*VDD.*", structural_component.name):
                bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'))
                bulk_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'B'))
                bulk_width = abs(bulk_x2-bulk_x1)

                main_segment = RectArea(x1=structural_component.layout.area.x1,
                                        y1=component.bounding_box.y1 + component.transform_matrix.f - bulk_width // 2
                                           - component.group_endpoint_bounding_box.y2 // 2,
                                        x2=structural_component.layout.area.x2,
                                        y2=component.bounding_box.y1 + component.transform_matrix.f + bulk_width // 2
                                           - component.group_endpoint_bounding_box.y2 // 2)

                left_segment = RectArea(x1=structural_component.layout.area.x1,
                                        y1=component.bounding_box.y1 + component.transform_matrix.f - bulk_width // 2
                                           - component.group_endpoint_bounding_box.y2 // 2,
                                        x2=structural_component.layout.area.x1 + self.RAIL_RING_WIDTH,
                                        y2=structural_component.layout.area.y2)

                right_segment = RectArea(x1=structural_component.layout.area.x2 - self.RAIL_RING_WIDTH,
                                         y1=component.bounding_box.y1 + component.transform_matrix.f - bulk_width // 2
                                         - component.group_endpoint_bounding_box.y2 // 2,
                                         x2=structural_component.layout.area.x2,
                                         y2=structural_component.layout.area.y2)

                # The two additional segments (left_segment and right_segment) are used for forcing via generation.
                # These remove the need for special handling
                trace.segments.append(RectAreaLayer(layer='m1', area=left_segment))
                trace.segments.append(RectAreaLayer(layer='locali', area=main_segment))
                trace.segments.append(RectAreaLayer(layer='m1', area=right_segment))
        self.components.append(trace)



def get_component_group_end_points_for_atr_sky130a_lib(self: object):
    component_group_sets = defaultdict(list)
    min_y_components = list(defaultdict(list))
    max_y_components = list(defaultdict(list))

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

    # Check for overlap of y-minimum components
    prev_y_min = None
    y_min_overlap_components_to_remove = []

    for i, (y, components) in enumerate(min_y_components):

        if prev_y_min is not None:
            for component in components:
                if abs(y - prev_y_min) <= component.bounding_box.y2:

                    # Take the maximum of the last two components that compared a y-distance to be
                    # less/equal to the bounding box.
                    y_min_overlap_components_to_remove.append(max(min_y_components[i - 1], min_y_components[i],
                                                                  key=lambda distance: (distance[0])))
        prev_y_min = y

    # Check for overlap of y-maximum components
    prev_y_max = None
    y_max_overlap_components_to_remove = []

    for i, (y, components) in enumerate(max_y_components):

        if prev_y_max is not None:
            for component in components:
                # Maybe there are some edge case here!
                if abs(y - prev_y_max) <= component.bounding_box.y2:
                    # Take the minimum of the last two components that compared a y-distance to be
                    # less/equal to the bounding box.
                    y_max_overlap_components_to_remove.append(min(max_y_components[i - 1], max_y_components[i],
                                                                  key=lambda distance: (distance[0])))
        prev_y_max = y

    # Filter out y-minimum components that have been found to be overlapping
    for _, overlap_components in y_min_overlap_components_to_remove:
        min_y_components = [(y, [component for component in components if component not in overlap_components])
                            for y, components in min_y_components]
    min_y_components = [(y, components) for y, components in min_y_components if components]  # remove empty tuples

    # Filter out y-maximum components that have been found to be overlapping
    for _, overlap_components in y_max_overlap_components_to_remove:
        max_y_components = [(y, [component for component in components if component not in overlap_components])
                            for y, components in max_y_components]
    max_y_components = [(y, components) for y, components in max_y_components if components]  # remove empty tuples

    # Update transistor components with end point information
    for component in self.components:
        if isinstance(component, Transistor):

            for _, components in min_y_components:
                for comp in components:
                    if comp == component:
                        component.group_endpoint = "bottom"

            for _, components in max_y_components:
                for comp in components:
                    if comp == component:
                        if component.group_endpoint == "bottom":
                            component.group_endpoint = "top/bottom"
                        else:
                            component.group_endpoint = "top"

# ========================================== Magic layout creator functions ============================================


def place_transistor_endpoints_for_atr_sky130a_lib(self: object, component: object):
    if isinstance(component, Transistor):
        layout_name = re.sub(r".{3}$", "TAP", component.layout_name)

        if component.group_endpoint == "top":

            self.magic_file_lines.extend([
                f"use {layout_name} {component.group}_{component.name}_TAP {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f + component.bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint == "bottom":

            self.magic_file_lines.extend([
                f"use {layout_name} {component.group}_{component.name}_TAP {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f - component.group_endpoint_bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint == "top/bottom":

            self.magic_file_lines.extend([
                f"use {layout_name} {component.group}_{component.name}_TAP {self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d}"
                f" {component.transform_matrix.e} {component.transform_matrix.f - component.group_endpoint_bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

            self.magic_file_lines.extend([
                f"use {layout_name} {component.group}_{component.name}_TAP {self.current_component_library_path}",
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

    transistor_endpoint_layout_name = re.sub(r".{3}$", "TAP", component.layout_name)
    layout_file_path = os.path.expanduser(f"{self.current_component_library_path}/"
                                          f"{transistor_endpoint_layout_name}.mag")
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_endpoint_bounding_box_for_atr_sky130a_lib(text_line=text_line, component=component)

    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")



