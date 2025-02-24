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
from collections import defaultdict
import libraries.atr_sky130a_lib as ATR

# =============================================== Trace Generator ======================================================

@dataclass
class LocalConnection:
    connection_type_pair: list[str]
    connection_net_name_pair: list[str]


class TraceGenerator:

    def __init__(self, project_properties, components):
        self.project_properties = project_properties
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.transistor_components = []
        self.structural_components = []
        self.functional_components = []
        self.components = components
        self.logger = get_a_logger(__name__)
        
        # Load config
        self.config = self.__load_config()
        self.INIT_RAIL_RING_OFFSET = self.config["trace_generator"]["INIT_RAIL_RING_OFFSET"]
        self.RAIL_RING_OFFSET = self.config["trace_generator"]["RAIL_RING_OFFSET"]
        self.RAIL_RING_WIDTH = self.config["trace_generator"]["RAIL_RING_WIDTH"]

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

        self.__generate_rails()

        # ATR SKY130A LIB component handling
        if any(lib for lib in self.component_libraries if re.search(r"ATR", lib.name)):
            ATR.generate_local_traces_for_atr_sky130a_lib(self=self)
            ATR.get_component_group_end_points_for_atr_sky130a_lib(self=self)

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def __generate_trace_box_around_cell(self, component, offset: int, width: int, layer: str):
        """Width extends outwards from offset"""

        trace = TraceNet(name=component.name, cell=self.circuit_cell.name)
        trace.instance = trace.__class__.__name__

        left_segment = RectArea(x1=self.circuit_cell.bounding_box.x1 - offset - width,
                                y1=self.circuit_cell.bounding_box.y1 - offset,
                                x2=self.circuit_cell.bounding_box.x1 - offset,
                                y2=self.circuit_cell.bounding_box.y2 + offset)

        right_segment = RectArea(x1=self.circuit_cell.bounding_box.x2 + offset,
                                 y1=self.circuit_cell.bounding_box.y1 - offset,
                                 x2=self.circuit_cell.bounding_box.x2 + offset + width,
                                 y2=self.circuit_cell.bounding_box.y2 + offset)

        top_segment = RectArea(x1=self.circuit_cell.bounding_box.x1 - offset - width,
                               y1=self.circuit_cell.bounding_box.y2 + offset,
                               x2=self.circuit_cell.bounding_box.x2 + offset + width,
                               y2=self.circuit_cell.bounding_box.y2 + offset + width)

        bottom_segment = RectArea(x1=self.circuit_cell.bounding_box.x1 - offset - width,
                                  y1=self.circuit_cell.bounding_box.y1 - offset - width,
                                  x2=self.circuit_cell.bounding_box.x2 + offset + width,
                                  y2=self.circuit_cell.bounding_box.y1 - offset)

        trace.segments = [RectAreaLayer(layer=layer, area=left_segment),
                          RectAreaLayer(layer=layer, area=right_segment),
                          RectAreaLayer(layer=layer, area=top_segment),
                          RectAreaLayer(layer=layer, area=bottom_segment)]

        self.components.append(trace)
        component.layout = [RectAreaLayer(layer=layer, area=top_segment),
                            RectAreaLayer(layer=layer, area=bottom_segment)]

    def __generate_rails(self):
        # Automated adding of VDD/VSS ring nets around cell based on found pins
        rail_number = 0
        for component in self.structural_components:
            if re.search(r".*VDD.*", component.name) or re.search(r".*VSS.*", component.name):
                self.__generate_trace_box_around_cell(
                    component, offset=self.INIT_RAIL_RING_OFFSET + self.RAIL_RING_OFFSET*rail_number,
                    width=self.RAIL_RING_WIDTH, layer="m1"
                )
                rail_number += 1


    def get(self):
        return self.components
