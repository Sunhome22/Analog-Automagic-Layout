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
from typing import List, Dict, Tuple
from collections import defaultdict


from logger.logger import get_a_logger
from circuit.circuit_components import (RectArea, RectAreaLayer, Transistor, Capacitor, Resistor, Pin, CircuitCell,
                                        TraceNet, RectAreaLayer, DigitalBlock)

# ======================================================================================================================
# ================================================ ATR SKY130A handling ================================================
# ======================================================================================================================


# ============================================ Bounding box update functions ===========================================

def update_bounding_boxes_for_atr_sky130a_lib(self):

    for component in self.atr_transistor_components:
        print(component.group_endpoint, component.overlap_distance)


# ============================================= Trace generation functions =============================================
def generate_local_traces_for_atr_sky130a_lib(self):
    for component in self.atr_transistor_components:
        if component.schematic_connections['B'] == component.schematic_connections['S']:
            __local_bulk_to_source_connection(self=self, component=component)

        if component.schematic_connections['G'] == component.schematic_connections['D']:
            __local_gate_to_drain_connection(self=self, component=component)

    # Make dict of component names based on y-coordinate
    y_grouped_component_names = defaultdict(list)
    for component in self.atr_transistor_components:
        y_grouped_component_names[component.transform_matrix.f].append(component.name)
    y_grouped_component_names = dict(y_grouped_component_names)

    # Get components connecting bulk to rail
    components_with_bulk_to_rail_connection = []
    for component in self.atr_transistor_components:
        if (re.search(r".*VDD.*", component.schematic_connections['B'], re.IGNORECASE) or
                re.search(r".*VSS.*", component.schematic_connections['B'], re.IGNORECASE)):
            components_with_bulk_to_rail_connection.append(component)

    # Make groups of components that have their bulk connected to a rail and have the same y-coordinate
    y_group_components = defaultdict(list)
    for _, group in y_grouped_component_names.items():
        for comp_name in group:
            for component in components_with_bulk_to_rail_connection:
                if component.name == comp_name:
                    group_name = "_".join(map(str, group))
                    y_group_components[group_name].append(component)

    # Iterate over y-grouped components and check for match against bulk to rail components. On component hit against a
    # group discard all other components within group. This solution removes redundant rail traces for each component
    # with the same y-coordinates.
    for _, group in y_grouped_component_names.items():
        found_comp = False
        for comp_name in group:
            for component in components_with_bulk_to_rail_connection:
                if component.name == comp_name and not found_comp:
                    found_comp = True
                    group_name = "_".join(map(str, group))
                    __local_bulk_to_rail_connection(
                        self=self,
                        component=component,
                        rail=component.schematic_connections['B'],
                        group_name=group_name,
                        group_components=y_group_components[group_name],
                    )


def __local_bulk_to_source_connection(self, component):
    trace = TraceNet(name=f"{component.name}_B_S", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'))
    source_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'S'))
    source_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'S'))
    source_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'S'))

    trace.segments = [RectAreaLayer(layer='locali', area=RectArea(x1=bulk_x1 + component.transform_matrix.c,
                                                                  y1=source_y1 + component.transform_matrix.f,
                                                                  x2=source_x2 + component.transform_matrix.c,
                                                                  y2=source_y2 + component.transform_matrix.f))]
    self.components.append(trace)


def __local_gate_to_drain_connection(self, component: Transistor):
    trace = TraceNet(name=f"{component.name}_G_D", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

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


def __local_bulk_to_rail_connection(self, component, rail: str, group_name: str, group_components):
    y_params = {
        'rail_top': (component.bounding_box.y2, component.group_endpoint_bounding_box.y2 // 2),
        'rail_bot': (component.bounding_box.y1, -component.group_endpoint_bounding_box.y2 // 2),
    }

    if component.group_endpoint:

        if component.group_endpoint == 'rail_top/bot':

            generate_bulk_to_rail_segments(self=self, rail=rail, component=component, y_params=y_params['rail_top'],
                                           group_endpoint="RAIL_TOP", group_name=group_name,
                                           group_components=group_components)
            generate_bulk_to_rail_segments(self=self, rail=rail, component=component, y_params=y_params['rail_bot'],
                                           group_endpoint="RAIL_BOT", group_name=group_name,
                                           group_components=group_components)

        elif re.search(r'^rail_top.*', component.group_endpoint):
            generate_bulk_to_rail_segments(self=self, rail=rail, component=component,
                                           y_params=y_params['rail_top'],
                                           group_endpoint=component.group_endpoint.upper(),
                                           group_name=group_name, group_components=group_components)

        elif re.search(r'^rail_bot.*', component.group_endpoint):
            generate_bulk_to_rail_segments(self=self, rail=rail, component=component,
                                           y_params=y_params['rail_bot'],
                                           group_endpoint=component.group_endpoint.upper(),
                                           group_name=group_name, group_components=group_components)


def generate_bulk_to_rail_segments(self, rail: str, component: Transistor, y_params: tuple,
                                   group_endpoint: str, group_name: str, group_components):
    trace = TraceNet(name=f"{group_name}_B_{rail}_{group_endpoint}", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'))
    bulk_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'B'))
    bulk_width = abs(bulk_x2 - bulk_x1)

    # self.CUSTOM_RELATIVE_PLACEMENT_ORDER = self.config["initiator_lp"]["CUSTOM_RELATIVE_PLACEMENT_ORDER"]
    # self.RELATIVE_PLACEMENT = self.config["initiator_lp"]["RELATIVE_PLACEMENT"]
    # self.CUSTOM_TRANSISTOR_ORDER = self.config["initiator_lp"]["CUSTOM_TRANSISTOR_ORDER"]
    #print(group_components)
    print("============")
    rail_nr = 0
    for structural_component in self.structural_components:
        if re.search(rf"\b{rail}\b", structural_component.name, re.IGNORECASE):
            x1, x2 = __get_bulk_to_rail_length_of_component_placement_order(self=self,
                                                                            structural_component=structural_component,
                                                                            group_components=group_components)

            segment = RectArea(x1=x1,
                               y1=y_params[0] + component.transform_matrix.f - (bulk_width // 2) + y_params[1],
                               x2=x2,
                               y2=y_params[0] + component.transform_matrix.f + (bulk_width // 2) + y_params[1])

            via_left = RectArea(x1=x1,
                                y1=y_params[0] + component.transform_matrix.f - bulk_width // 2 + y_params[1],
                                x2=x1 + self.RAIL_RING_WIDTH,
                                y2=y_params[0] + component.transform_matrix.f + (bulk_width // 2) + y_params[1])

            via_right = RectArea(x1=x2 - self.RAIL_RING_WIDTH,
                                 y1=y_params[0] + component.transform_matrix.f - bulk_width // 2 + y_params[1],
                                 x2=x2,
                                 y2=y_params[0] + component.transform_matrix.f + (bulk_width // 2) + y_params[1])

            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_left))
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_right))
            trace.segments.append(RectAreaLayer(layer='locali', area=segment))

    self.components.append(trace)

def __get_bulk_to_rail_length_of_component_placement_order(self, structural_component,
                                                           group_components) -> Tuple[int, int]:
    x1 = 0
    x2 = 0
    total_length = sum((component.bounding_box.x2 - component.bounding_box.x1) for component in group_components)
    smallest_x_cord_comp = min(group_components, key=lambda component: component.transform_matrix.c)
    print(total_length, smallest_x_cord_comp)

    if self.RELATIVE_COMPONENT_PLACEMENT == "A":
        x1 = structural_component.layout.area.x1
        x2 = structural_component.layout.area.x2

    elif self.RELATIVE_COMPONENT_PLACEMENT == "S":

        if self.CUSTOM_COMPONENT_ORDER[0] == "T":
            x1 = structural_component.layout.area.x1
            x2 = structural_component.layout.area.x1 + total_length

        elif self.CUSTOM_COMPONENT_ORDER[1] == "T":
            x1 = smallest_x_cord_comp.transform_matrix.c - 200
            x2 = smallest_x_cord_comp.transform_matrix.c + total_length + 200

        elif self.CUSTOM_COMPONENT_ORDER[2] == "T":
            x1 = structural_component.layout.area.x2 - total_length
            x2 = structural_component.layout.area.x2

    return x1, x2

def get_component_group_endpoints_for_atr_sky130a_lib(self):
    components_and_positions = []

    for component in self.atr_transistor_components:
        components_and_positions.append((component, component.transform_matrix.c, component.transform_matrix.f))

    # Sorts components first by x and then by y (ascending order)
    sorted_components_by_x = sorted(components_and_positions, key=lambda item: (item[1], item[2]))

    # Sorts components first by y and then by x (ascending order)
    sorted_components_by_y = sorted(components_and_positions, key=lambda item: (item[2], item[1]))

    # Groups components by axis into a set of x-groups and y-groups
    groups_x = group_components_by_axis(sorted_components_by_x)
    groups_y = group_components_by_axis(sorted_components_by_y)

    # Find matching components and add x,y indexing identifiers.
    component_x_group_y_group = [
        (comp_x, index_x, index_y)
        for index_x, group_x in enumerate(groups_x)
        for comp_x in group_x
        for index_y, group_y in enumerate(groups_y)
        for comp_y in group_y
        if comp_x == comp_y
    ]

    # Group components by x_group and convert dictionary to sorted list of lists. Used for no rail assignment
    grouped_dict_x = defaultdict(list)
    for component, x, y in component_x_group_y_group:
        grouped_dict_x[x].append([component, x, y])
    grouped_components_x = [grouped_dict_x[key] for key in sorted(grouped_dict_x)]

    # Lists for finding rail endpoints.
    possible_y_max_components = []
    possible_y_min_components = []

    # Assignment of no rail endpoints
    for component in self.atr_transistor_components:
        for components in grouped_components_x:
            y_group_index = components[0][2]

            # Special handling is need in the case there are just 2, 3 or 4 components
            # Maybe there is some other way to solve this
            if 2 <= len(self.atr_transistor_components) <= 4:
                idx = [c[0][0] for c in components].index(component)

                is_top_bot = ((idx == 0 and (len(components) == 1 or len(self.atr_transistor_components) == 3))
                              or len(self.atr_transistor_components) == 2)

                is_top = ((idx == len(components) - 1 and len(components) > 1)
                          or (idx == 1 and len(self.atr_transistor_components) == 4))

                is_bot = (idx == 0 and len(components) > 1) or (idx == len(components) - 2)

                if is_top_bot:
                    component.group_endpoint = "no_rail_top/bot"
                    possible_y_max_components.append((component, component.transform_matrix.f, y_group_index))
                    possible_y_min_components.append((component, component.transform_matrix.f, y_group_index))
                elif is_top:
                    component.group_endpoint = "no_rail_top"
                    possible_y_max_components.append((component, component.transform_matrix.f, y_group_index))
                elif is_bot:
                    component.group_endpoint = "no_rail_bot"
                    possible_y_min_components.append((component, component.transform_matrix.f, y_group_index))

            # Default handling
            else:
                if component == components[0][0][0] and len(components) == 1:
                    component.group_endpoint = "no_rail_top/bot"
                    possible_y_max_components.append((component, component.transform_matrix.f, y_group_index))
                    possible_y_min_components.append((component, component.transform_matrix.f, y_group_index))

                elif component == components[-1][0][0] and len(components) > 1:
                    possible_y_max_components.append((component, component.transform_matrix.f, y_group_index))
                    component.group_endpoint = "no_rail_top"

                elif component == components[0][0][0] and len(components) > 1:
                    component.group_endpoint = "no_rail_bot"
                    possible_y_min_components.append((component, component.transform_matrix.f, y_group_index))

    # Assignment of rail endpoints
    for min_y_components in list(find_min_y_components(possible_y_min_components).values()):
        for min_y_component in min_y_components:

            for component in self.atr_transistor_components:
                if min_y_component == component:
                    if component.group_endpoint == "no_rail_top/bot":
                        component.group_endpoint = "rail_bot/no_rail_top"
                    else:
                        component.group_endpoint = "rail_bot"

    for max_y_components in list(find_max_y_components(possible_y_max_components).values()):
        for max_y_component in max_y_components:
            for component in self.atr_transistor_components:
                if max_y_component == component:
                    if component.group_endpoint == "rail_bot/no_rail_top":
                        component.group_endpoint = "rail_top/bot"
                    else:
                        if component.group_endpoint == "no_rail_top/bot":
                            component.group_endpoint = "rail_top/no_rail_bot"
                        else:
                            component.group_endpoint = "rail_top"
    # Logging
    for component in self.components:
        if isinstance(component, Transistor):
            self.logger.info(f"Component '{component.name}' was assigned group endpoint '{component.group_endpoint}'")


def group_components_by_axis(sorted_components: list) -> list:
    # Create a set of direction groups that are based on overlap and position (not transistors object group label)
    groups = []
    current_group = [sorted_components[0]]

    for i in range(1, len(sorted_components)):
        _, _, prev_y = sorted_components[i - 1]
        component, x, y = sorted_components[i]

        if abs(y - prev_y) > component.bounding_box.y2:
            groups.append(current_group)
            current_group = []

        current_group.append((component, x, y))

    # Append the last group
    groups.append(current_group)

    return groups


def find_max_y_components(possible_y_max_components: list) -> dict:
    groups = defaultdict(list)

    for component, y, group in possible_y_max_components:
        groups[group].append((component, y))

    max_y_components = {}
    for group, components in groups.items():
        max_y = max(components, key=lambda x: x[1])[1]
        max_y_components[group] = [component for component, y in components if y == max_y]

    return max_y_components


def find_min_y_components(possible_y_min_components: list) -> dict:
    groups = defaultdict(list)

    for component, y, group in possible_y_min_components:
        groups[group].append((component, y))

    min_y_components = {}
    for group, components in groups.items():
        min_y = min(components, key=lambda x: x[1])[1]
        min_y_components[group] = [component for component, y in components if y == min_y]

    return min_y_components


# ========================================== Magic layout creator functions ============================================


def place_transistor_endpoints_for_atr_sky130a_lib(self, component: Transistor):
    if isinstance(component, Transistor):
        layout_name_top = re.sub(r".{3}$", "TAPTOP", component.layout_name)
        layout_name_bot = re.sub(r".{3}$", "TAPBOT", component.layout_name)

        if component.group_endpoint in {"rail_top", "no_rail_top", "rail_top/no_rail_bot", "rail_bot/no_rail_top",
                                        "rail_top/bot", "no_rail_top/bot"}:
            self.magic_file_lines.extend([
                f"use {layout_name_top} {component.group}_{component.name}_TAPTOP "
                f"{self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b} "
                f"{component.transform_matrix.c} {component.transform_matrix.d} {component.transform_matrix.e} "
                f"{component.transform_matrix.f + component.bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

        if component.group_endpoint in {"rail_bot", "no_rail_bot", "rail_bot/no_rail_top", "rail_top/no_rail_bot",
                                        "rail_top/bot", "no_rail_top/bot"}:
            self.magic_file_lines.extend([
                f"use {layout_name_bot} {component.group}_{component.name}_TAPBOT "
                f"{self.current_component_library_path}",
                f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
                f" {component.transform_matrix.c} {component.transform_matrix.d} {component.transform_matrix.e} "
                f"{component.transform_matrix.f - component.group_endpoint_bounding_box.y2}",
                f"box {component.group_endpoint_bounding_box.x1} {component.group_endpoint_bounding_box.y1} "
                f"{component.group_endpoint_bounding_box.x2} {component.group_endpoint_bounding_box.y2}"
            ])

# ========================================== Magic component parser functions ==========================================


def get_overlap_difference_for_atr_sky130a_lib(self, text_line: str, component: Transistor):
    if self.found_transistor_well_line_label:
        line_words = text_line.split()

        self.transistor_well_size = RectArea(x1=int(line_words[1]), y1=int(line_words[2]), x2=int(line_words[3]),
                                             y2=int(line_words[4]))
        self.found_transistor_well_line_label = False

    elif re.search(r'<< nwell >>', text_line) or re.search(r'<< pwell >>', text_line):
        # Next line contains well size info
        self.found_transistor_well_line_label = True

    # Calculate overlap difference after bounding box has been set
    elif self.found_bounding_box:

        x_difference = int((abs(self.transistor_well_size.x1) + abs(self.transistor_well_size.x2)
                            - (abs(component.bounding_box.x1) + abs(component.bounding_box.x2))) / 2)
        y_difference = int((abs(self.transistor_well_size.y1) + abs(self.transistor_well_size.y2)
                            - (abs(component.bounding_box.y1) + abs(component.bounding_box.y2))) / 2)

        component.overlap_distance.x = x_difference
        component.overlap_distance.y = y_difference


def get_component_bounding_box_for_atr_sky130a_lib(self, text_line: str, component):

    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.bounding_box.set([int(val) // self.scale_factor for val in text_line_words[2:6]])
        self.found_bounding_box = True


def get_component_endpoint_bounding_box_for_atr_sky130a_lib(self, text_line: str, component):

    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.group_endpoint_bounding_box.set([int(val) // self.scale_factor for val in text_line_words[2:6]])


def magic_component_parsing_for_atr_sky130a_lib(self, layout_file_path: str, component):
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_overlap_difference_for_atr_sky130a_lib(text_line=text_line, component=component, self=self)
                get_component_bounding_box_for_atr_sky130a_lib(text_line=text_line, component=component, self=self)
    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")

    # It's safe to assumes that top and bottom taps have equal bounding boxes.
    transistor_endpoint_layout_name = re.sub(r".{3}$", "TAPTOP", component.layout_name)
    layout_file_path = os.path.expanduser(f"{self.current_component_library_path}/"
                                          f"{transistor_endpoint_layout_name}.mag")
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_endpoint_bounding_box_for_atr_sky130a_lib(self=self, text_line=text_line, component=component)

    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")
