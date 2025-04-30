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
# ================================================= TR SKY130A handling ================================================
# ======================================================================================================================

# ========================================== Magic component parser functions ==========================================


def get_component_bounding_box_for_tr_sky130a_lib(self, text_line: str, component):
    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.bounding_box.set([int(val) // self.scale_factor for val in text_line_words[2:6]])
        self.found_bounding_box = True


def magic_component_parsing_for_tr_sky130a_lib(self, layout_file_path: str, component):
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_bounding_box_for_tr_sky130a_lib(text_line=text_line, component=component, self=self)
    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")


def generate_local_traces_for_tr_sky130a_lib_resistors(self):

    for component in self.tr_resistor_components:
        if component.schematic_connections['B'] == component.schematic_connections['N']:
            __local_bulk_to_negative_connection(self=self, component=component)

        if component.schematic_connections['B'] == component.schematic_connections['P']:
            __local_bulk_to_positive_connection(self=self, component=component)

    # Make dict of component names based on y-coordinate
    y_grouped_component_names = defaultdict(list)
    for component in self.tr_resistor_components:
        y_grouped_component_names[component.transform_matrix.f].append(component.name)
    y_grouped_component_names = dict(y_grouped_component_names)

    # Get components connecting bulk to rail
    components_with_bulk_to_rail_connection = []
    for component in self.tr_resistor_components:
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
                    __local_bulk_to_rail_connection(self=self, component=component,
                                                    rail=component.schematic_connections['B'],
                                                    group_name=group_name,
                                                    group_components=y_group_components[group_name])


def __local_bulk_to_negative_connection(self, component):
    trace = TraceNet(name=f"{component.name}_B_N", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'))
    negative_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'N'))
    negative_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'N'))
    negative_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'N'))

    trace.segments = [RectAreaLayer(layer='locali', area=RectArea(x1=bulk_x1 + component.transform_matrix.c,
                                                                  y1=negative_y1 + component.transform_matrix.f,
                                                                  x2=negative_x2 + component.transform_matrix.c,
                                                                  y2=negative_y2 + component.transform_matrix.f))]
    self.components.append(trace)


def __local_bulk_to_positive_connection(self, component):
    trace = TraceNet(name=f"{component.name}_B_P", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    bulk_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'B'))
    positive_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'P'))
    positive_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'P'))
    positive_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'P'))

    trace.segments = [RectAreaLayer(layer='locali', area=RectArea(x1=positive_x1 + component.transform_matrix.c,
                                                                  y1=positive_y1 + component.transform_matrix.f,
                                                                  x2=bulk_x2 + component.transform_matrix.c,
                                                                  y2=positive_y2 + component.transform_matrix.f))]
    self.components.append(trace)


def __local_bulk_to_rail_connection(self, component, rail: str, group_name: str, group_components: list):
    y_params = {
        'rail_bot': (component.bounding_box.y1, 0, 1),
        'rail_top': (component.bounding_box.y2, 1, 0)
    }
    generate_bulk_to_rail(self=self, rail=rail, component=component, y_params=y_params['rail_top'],
                          group_endpoint="RAIL_TOP", group_name=group_name,group_components=group_components)
    generate_bulk_to_rail(self=self, rail=rail, component=component, y_params=y_params['rail_bot'],
                          group_endpoint="RAIL_BOT", group_name=group_name, group_components=group_components)


def generate_bulk_to_rail(self, rail: str, component, y_params: tuple,
                                   group_endpoint: str, group_name: str, group_components: list):

    trace = TraceNet(name=f"{group_name}_B_{rail}_{group_endpoint}", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    bulk_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'B'))
    bulk_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'B'))
    bulk_width = abs(bulk_y2 - bulk_y1)

    for structural_component in self.structural_components:
        if re.search(rf"\b{rail}\b", structural_component.name, re.IGNORECASE):
            __create_bulk_to_rail_based_on_component_placement_order(
                self=self,
                structural_component=structural_component,
                y_params=y_params,
                component=component,
                bulk_width=bulk_width,
                group_components=group_components,
                trace=trace
            )
            __add_connections_for_middle_placed_components(self=self, structural_component=structural_component,
                                                           group_components=group_components, trace=trace)
    self.components.append(trace)


def __create_bulk_to_rail_based_on_component_placement_order(
        self, structural_component, y_params, component, bulk_width, group_components, trace):

    total_length = sum((comp.bounding_box.x2 - comp.bounding_box.x1) for comp in group_components)
    smallest_x_component = min(group_components, key=lambda comp: comp.transform_matrix.c)

    if self.RELATIVE_COMPONENT_PLACEMENT == "A" or len(self.functional_component_order) == 1:
        x1 = structural_component.layout.area.x1
        x2 = structural_component.layout.area.x2

        segment = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                           x2=x2, y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

        via_left = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                            x2=x1 + self.RAIL_RING_WIDTH,
                            y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

        via_right = RectArea(x1=x2 - self.RAIL_RING_WIDTH,
                             y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                             x2=x2, y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

        trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_left))
        trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_right))
        trace.segments.append(RectAreaLayer(layer='locali', area=segment))

    elif self.RELATIVE_COMPONENT_PLACEMENT == "S":

        if self.functional_component_order[0] == "R":
            x1 = structural_component.layout.area.x1
            x2 = total_length

            segment = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                               x2=x2, y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            via_left = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                                x2=x1 + self.RAIL_RING_WIDTH,
                                y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_left))
            trace.segments.append(RectAreaLayer(layer='locali', area=segment))

        elif self.functional_component_order[-1] == "R":
            x1 = structural_component.layout.area.x2 - total_length + structural_component.layout.area.x1
            x2 = structural_component.layout.area.x2

            segment = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                               x2=x2, y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            via_right = RectArea(x1=x2 - self.RAIL_RING_WIDTH,
                                 y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                                 x2=x2, y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_right))
            trace.segments.append(RectAreaLayer(layer='locali', area=segment))

        elif self.functional_component_order[1] == "R" or self.functional_component_order[2] == "R":
            x1 = smallest_x_component.transform_matrix.c + structural_component.layout.area.x1
            x2 = smallest_x_component.transform_matrix.c + total_length - structural_component.layout.area.x1

            segment = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                               x2=x2, y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            via_left = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                                x2=x1 + self.RAIL_RING_WIDTH,
                                y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            via_right = RectArea(x1=x2 - self.RAIL_RING_WIDTH,
                                 y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                                 x2=x2, y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_left))
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_right))
            trace.segments.append(RectAreaLayer(layer='locali', area=segment))


def __add_connections_for_middle_placed_components(self, structural_component, group_components, trace):
    if self.RELATIVE_COMPONENT_PLACEMENT == "S" and len(self.functional_component_order) > 2:

        if self.functional_component_order[1] == "R" or self.functional_component_order[2] == "R":
            current_rail_bottom_segment = RectAreaLayer()
            smallest_x_cord_comp = min(group_components, key=lambda component: component.transform_matrix.c)
            total_length = sum((component.bounding_box.x2 - component.bounding_box.x1) for component in group_components)

            # Get bottom segment of current rail
            for component in self.components:
                if isinstance(component, TraceNet) and component.cell_chain == structural_component.cell_chain:
                    if (re.search(r".*VDD.*", component.name, re.IGNORECASE) and
                            re.search(r".*VDD.*", structural_component.name, re.IGNORECASE)) or (
                            re.search(r".*VSS.*", component.name, re.IGNORECASE) and
                            re.search(r".*VSS.*", structural_component.name, re.IGNORECASE)):
                        current_rail_bottom_segment = min(component.segments, key=lambda s: (s.area.y1, s.area.y2))

            segment_left = RectArea(x1=smallest_x_cord_comp.transform_matrix.c + structural_component.layout.area.x1,
                                    y1=current_rail_bottom_segment.area.y1,
                                    x2=smallest_x_cord_comp.transform_matrix.c + structural_component.layout.area.x1
                                    + self.RAIL_RING_WIDTH,
                                    y2=structural_component.layout.area.y2)

            segment_right = RectArea(x1=smallest_x_cord_comp.transform_matrix.c - structural_component.layout.area.x1
                                     + total_length - self.RAIL_RING_WIDTH,
                                     y1=current_rail_bottom_segment.area.y1,
                                     x2=smallest_x_cord_comp.transform_matrix.c - structural_component.layout.area.x1
                                     + total_length,
                                     y2=structural_component.layout.area.y2)

            via_right_top = RectArea(x1=smallest_x_cord_comp.transform_matrix.c + structural_component.layout.area.x1,
                                     y1=current_rail_bottom_segment.area.y1,
                                     x2=smallest_x_cord_comp.transform_matrix.c + structural_component.layout.area.x1
                                     + self.RAIL_RING_WIDTH,
                                     y2=current_rail_bottom_segment.area.y1 + self.RAIL_RING_WIDTH)

            via_right_bot = RectArea(x1=smallest_x_cord_comp.transform_matrix.c + structural_component.layout.area.x1,
                                     y1=structural_component.layout.area.y2 - self.RAIL_RING_WIDTH,
                                     x2=smallest_x_cord_comp.transform_matrix.c + structural_component.layout.area.x1
                                     + self.RAIL_RING_WIDTH,
                                     y2=structural_component.layout.area.y2)

            via_left_top = RectArea(x1=smallest_x_cord_comp.transform_matrix.c - structural_component.layout.area.x1
                                    + total_length - self.RAIL_RING_WIDTH,
                                    y1=current_rail_bottom_segment.area.y1,
                                    x2=smallest_x_cord_comp.transform_matrix.c - structural_component.layout.area.x1
                                    + total_length,
                                    y2=current_rail_bottom_segment.area.y1 + self.RAIL_RING_WIDTH)

            via_left_bot = RectArea(x1=smallest_x_cord_comp.transform_matrix.c - structural_component.layout.area.x1
                                    + total_length - self.RAIL_RING_WIDTH,
                                    y1=structural_component.layout.area.y2 - self.RAIL_RING_WIDTH,
                                    x2=smallest_x_cord_comp.transform_matrix.c - structural_component.layout.area.x1
                                    + total_length,
                                    y2=structural_component.layout.area.y2)

            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_left_top))
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_left_bot))
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_right_top))
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_right_bot))
            trace.segments.append(RectAreaLayer(layer='m1', area=segment_left))
            trace.segments.append(RectAreaLayer(layer='m1', area=segment_right))
