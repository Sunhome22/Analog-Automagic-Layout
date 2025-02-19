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
from dataclasses import dataclass

# =============================================== Trace Generator ======================================================

@dataclass
class LocalConnection:
    connection_type_pair: list[str]
    connection_net_name_pair: list[str]

class TraceGenerator:

    def __init__(self, project_properties, components):
        self.project_properties = project_properties
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_lib_name = project_properties.lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.functional_components = []
        self.structural_components = []
        self.components = components
        self.logger = get_a_logger(__name__)

        # Make lists of functional components and structural components
        for component in self.components:
            if not isinstance(component, (Pin, CircuitCell, TraceNet)):
                self.functional_components.append(component)
            else:
                self.structural_components.append(component)

        self.__generate_local_cmos_traces()


    def __generate_local_cmos_traces(self):
        self.__find_cmos_local_connections()


    def __find_cmos_local_connections(self):

        for index, component in enumerate(self.functional_components):
            if component.schematic_connections['B'] == component.schematic_connections['S']:
                self.__local_bulk_to_source_connection(component, index)

    def __local_bulk_to_source_connection(self, component: object, index: int):
        trace = TraceNet(number_id=index, name=f"{component.name}_B_S", cell=component.cell)
        trace.instance = trace.__class__.__name__


        source_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'S'), None)
        source_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'S'), None)
        source_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'S'), None)
        bulk_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'B'), None)

        trace.segments=[RectAreaLayer(layer='locali', area=RectArea(x1=bulk_x1 + component.transform_matrix.c,
                                                                    y1=source_y1 + component.transform_matrix.f,
                                                                    x2=source_x2 + component.transform_matrix.c,
                                                                    y2=source_y2 + component.transform_matrix.f))]
        self.components.append(trace)


    def __local_bulk_to_drain_connection(self):
        pass

    def __local_bulk_to_bulk_connection(self):
        pass

    def __local_gate_to_drain_connection(self):
        pass

    def __local_gate_to_source_connection(self):
        pass

    def get(self):
        return self.components