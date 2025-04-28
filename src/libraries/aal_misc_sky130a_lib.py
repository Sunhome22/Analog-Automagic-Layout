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
                                        TraceNet, RectAreaLayer, DigitalBlock)

# ======================================================================================================================
# ============================================== AAL MISC SKY130A handling =============================================
# ======================================================================================================================

# ========================================== Magic component parser functions ==========================================


def get_component_bounding_box_for_aal_misc_sky130a_lib(self, text_line: str, component):
    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.bounding_box.set([int(val) // self.scale_factor for val in text_line_words[2:6]])
        self.found_bounding_box = True


def magic_component_parsing_for_aal_misc_sky130a_lib(self, layout_file_path: str, component):
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_bounding_box_for_aal_misc_sky130a_lib(text_line=text_line, component=component, self=self)
    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")


def generate_local_traces_for_aal_misc_sky130a_lib(self):
    # Make groups of components by y-coordinate
    y_grouped_component_names = defaultdict(list)
    for component in self.aal_capacitor_components:
        y_grouped_component_names[component.transform_matrix.f].append(component.name)
    y_grouped_component_names = dict(y_grouped_component_names)

    # Get components connecting bulk to rail
    components_with_bulk_to_rail_connection = []
    for component in self.aal_capacitor_components:
        if (re.search(r".*VDD.*", component.schematic_connections['B'], re.IGNORECASE) or
                re.search(r".*VSS.*", component.schematic_connections['B'], re.IGNORECASE)):
            components_with_bulk_to_rail_connection.append(component)

    # Iterate over y-grouped components and check for match against bulk to rail components. On component hit against a
    # group discard all other components within group. This solution removes redundant rail traces for each component
    # with the same y-coordinates.
    # for _, group in y_grouped_component_names.items():
    #     found_comp = False
    #     for comp_name in group:
    #         for component in components_with_bulk_to_rail_connection:
    #             if component.name == comp_name and not found_comp:
    #                 found_comp = True
    #                 group_name = "_".join(map(str, group))
    #                 __local_bulk_to_rail_connection(self=self, component=component,
    #                                                 rail=component.schematic_connections['B'],
    #                                                 group_name=group_name)


def __local_bulk_to_rail_connection(self, component, rail: str, group_name: str):
    y_params = {
        'rail_bot': (component.bounding_box.y1, 0, 1),
        'rail_top': (component.bounding_box.y2, 1, 0)
    }
    generate_bulk_to_rail_segments(self=self, rail=rail, component=component, y_params=y_params['rail_top'],
                                   group_endpoint="RAIL_TOP", group_name=group_name)
    generate_bulk_to_rail_segments(self=self, rail=rail, component=component, y_params=y_params['rail_bot'],
                                   group_endpoint="RAIL_BOT", group_name=group_name)


def generate_bulk_to_rail_segments(self, rail: str, component, y_params: tuple,
                                   group_endpoint: str, group_name: str):

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
            segment = RectArea(x1=structural_component.layout.area.x1,
                               y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                               x2=structural_component.layout.area.x2,
                               y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            via_left = RectArea(x1=structural_component.layout.area.x1,
                                y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                                x2=structural_component.layout.area.x1 + self.RAIL_RING_WIDTH,
                                y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            via_right = RectArea(x1=structural_component.layout.area.x2 - self.RAIL_RING_WIDTH,
                                 y1=y_params[0] + component.transform_matrix.f - bulk_width * y_params[1],
                                 x2=structural_component.layout.area.x2,
                                 y2=y_params[0] + component.transform_matrix.f + bulk_width * y_params[2])

            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_left))
            trace.vias.append(RectAreaLayer(layer='locali-m1', area=via_right))
            trace.segments.append(RectAreaLayer(layer='locali', area=segment))

    self.components.append(trace)

