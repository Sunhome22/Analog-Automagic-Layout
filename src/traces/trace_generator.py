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
import os
import time
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, TraceNet, RectAreaLayer
from magic.magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image
from logger.logger import get_a_logger
from collections import deque
import tomllib
import re
from dataclasses import dataclass


# =============================================== Trace Generator ======================================================

@dataclass
class LocalConnection:
    connection_type_pair: list[str]
    connection_net_name_pair: list[str]

class TraceGenerator:

    RAIL_OFFSET = 150
    RAIL_WIDTH = 80

    def __init__(self, project_properties, components):
        self.project_properties = project_properties
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_lib_name = project_properties.lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.transistor_components = []
        self.structural_components = []
        self.functional_components = []
        self.components = components
        self.logger = get_a_logger(__name__)

        # Make lists of different component types
        for component in self.components:
            if isinstance(component, Transistor):
                self.transistor_components.append(component)

            if isinstance(component, (Pin, CircuitCell)):
                self.structural_components.append(component)

            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.functional_components.append(component)

            # There should only be one CircuitCell in components for each cell iteration of trace_generator
            if isinstance(component, CircuitCell):
                self.circuit_cell = component

        self.__generate_rails(rail_offset=self.RAIL_OFFSET, rail_width=self.RAIL_WIDTH)
        self.__generate_local_traces_for_cmos_transistors()


    def __generate_local_traces_for_cmos_transistors(self):
        """This works with Carsten Wulff's ATR library. A certain port setup in layout is required"""
        for component in self.transistor_components:
            if component.schematic_connections['B'] == component.schematic_connections['S']:
                self.__local_bulk_to_source_connection(component=component)
            if component.schematic_connections['G'] == component.schematic_connections['D']:
                self.__local_gate_to_drain_connection(component=component)
            if component.schematic_connections['B'] == 'VDD':
                self.__local_bulk_to_vdd_connection(component=component)

    def __local_bulk_to_source_connection(self, component: object):
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

    def __local_gate_to_drain_connection(self, component: object):
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


    def __generate_trace_box_around_cell(self, name: str, layer: str, offset: int, width: int):
        """Width extends outwards from offset"""

        trace = TraceNet(name=name, cell=self.circuit_cell.name)
        trace.instance = trace.__class__.__name__

        trace.segments = [
            # Left
            RectAreaLayer(layer=layer, area=RectArea(x1=self.circuit_cell.bounding_box.x1 - offset - width,
                                                     y1=self.circuit_cell.bounding_box.y1 - offset,
                                                     x2=self.circuit_cell.bounding_box.x1 - offset,
                                                     y2=self.circuit_cell.bounding_box.y2 + offset)),
            # Right
            RectAreaLayer(layer=layer, area=RectArea(x1=self.circuit_cell.bounding_box.x2 + offset,
                                                     y1=self.circuit_cell.bounding_box.y1 - offset,
                                                     x2=self.circuit_cell.bounding_box.x2 + offset + width,
                                                     y2=self.circuit_cell.bounding_box.y2 + offset)),
            # Top
            RectAreaLayer(layer=layer, area=RectArea(x1=self.circuit_cell.bounding_box.x1 - offset - width,
                                                     y1=self.circuit_cell.bounding_box.y2 + offset,
                                                     x2=self.circuit_cell.bounding_box.x2 + offset + width,
                                                     y2=self.circuit_cell.bounding_box.y2 + offset + width)),
            # Bottom
            RectAreaLayer(layer=layer, area=RectArea(x1=self.circuit_cell.bounding_box.x1 - offset - width,
                                                     y1=self.circuit_cell.bounding_box.y1 - offset - width,
                                                     x2=self.circuit_cell.bounding_box.x2 + offset + width,
                                                     y2=self.circuit_cell.bounding_box.y1 - offset))
        ]
        self.components.append(trace)

    def __generate_rails(self, rail_offset, rail_width):
        self.__generate_trace_box_around_cell(name='VDD_RAIL', layer='locali', offset=rail_offset, width=rail_width)
        self.__generate_trace_box_around_cell(name='VSS_RAIL', layer='m1', offset=rail_offset, width=rail_width)


    def __local_bulk_to_vdd_connection(self, component):
        for component in self.components:
            if component.name == 'VDD_RAIL':
                print(component)

    def get(self):
        return self.components