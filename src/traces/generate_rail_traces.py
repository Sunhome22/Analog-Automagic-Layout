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
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, TraceNet, \
    RectAreaLayer
from logger.logger import get_a_logger
import tomllib
import re
import libraries.atr_sky130a_lib as atr

# =============================================== Trace Generator ======================================================


class GenerateRailTraces:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties, components):
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.structural_components = []
        self.functional_components = []
        self.components = components

        # Load config
        self.config = self.__load_config()
        self.INIT_RAIL_RING_OFFSET_X = self.config["generate_rail_traces"]["INIT_RAIL_RING_OFFSET_X"]
        self.INIT_RAIL_RING_OFFSET_Y = self.config["generate_rail_traces"]["INIT_RAIL_RING_OFFSET_Y"]
        self.RAIL_RING_OFFSET = self.config["generate_rail_traces"]["RAIL_RING_OFFSET"]
        self.RAIL_RING_WIDTH = self.config["generate_rail_traces"]["RAIL_RING_WIDTH"]

        # Make lists of different component types
        for component in self.components:
            if isinstance(component, (Pin, CircuitCell)):
                self.structural_components.append(component)
                self.structural_components.sort(key=lambda comp: comp.name)

            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.functional_components.append(component)

            # There should only be one CircuitCell when generating rails
            if isinstance(component, CircuitCell):
                self.circuit_cell = component

        self.__generate_rails()

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def __generate_trace_box_around_cell(self, pin, offset_x: int, offset_y: int, width: int):
        """Width extends outwards from offset"""

        trace = TraceNet(name=pin.name, cell=self.circuit_cell.cell, named_cell=self.circuit_cell.named_cell)
        trace.instance = trace.__class__.__name__
        trace.parent_cell = self.circuit_cell.parent_cell
        trace.cell_chain = self.circuit_cell.cell_chain

        left_segment = RectArea(x1=self.circuit_cell.bounding_box.x1 - offset_x - width,
                                y1=self.circuit_cell.bounding_box.y1 - offset_y,
                                x2=self.circuit_cell.bounding_box.x1 - offset_x,
                                y2=self.circuit_cell.bounding_box.y2 + offset_y)

        right_segment = RectArea(x1=self.circuit_cell.bounding_box.x2 + offset_x,
                                 y1=self.circuit_cell.bounding_box.y1 - offset_y,
                                 x2=self.circuit_cell.bounding_box.x2 + offset_x + width,
                                 y2=self.circuit_cell.bounding_box.y2 + offset_y)

        top_segment = RectArea(x1=self.circuit_cell.bounding_box.x1 - offset_x - width,
                               y1=self.circuit_cell.bounding_box.y2 + offset_y,
                               x2=self.circuit_cell.bounding_box.x2 + offset_x + width,
                               y2=self.circuit_cell.bounding_box.y2 + offset_y + width)

        bot_segment = RectArea(x1=self.circuit_cell.bounding_box.x1 - offset_x - width,
                               y1=self.circuit_cell.bounding_box.y1 - offset_y - width,
                               x2=self.circuit_cell.bounding_box.x2 + offset_x + width,
                               y2=self.circuit_cell.bounding_box.y1 - offset_y)

        top_left_via = RectArea(x1=left_segment.x1, y1=top_segment.y1, x2=left_segment.x2, y2=top_segment.y2)
        bot_left_via = RectArea(x1=left_segment.x1, y1=bot_segment.y1, x2=left_segment.x2, y2=bot_segment.y2)
        top_right_via = RectArea(x1=right_segment.x1, y1=top_segment.y1, x2=right_segment.x2, y2=top_segment.y2)
        bot_right_via = RectArea(x1=right_segment.x1, y1=bot_segment.y1, x2=right_segment.x2, y2=bot_segment.y2)

        trace.vias = [RectAreaLayer(layer='locali-m1', area=top_left_via),
                      RectAreaLayer(layer='locali-m1', area=bot_left_via),
                      RectAreaLayer(layer='locali-m1', area=top_right_via),
                      RectAreaLayer(layer='locali-m1', area=bot_right_via)]

        trace.segments = [RectAreaLayer(layer="locali", area=top_segment),
                          RectAreaLayer(layer="locali", area=bot_segment),
                          RectAreaLayer(layer="m1", area=left_segment),
                          RectAreaLayer(layer="m1", area=right_segment)]

        self.components.append(trace)

        # Make top segment layout area for pin
        pin.layout = RectAreaLayer(layer="locali", area=top_segment)

    def __generate_rails(self):

        # ATR SKY130A LIB component handling
        # for component in self.components:
        #     if re.search(r'_ATR_', component.layout_library):
        #         atr.update_bounding_boxes_for_atr_sky130a_lib(self=self)

        # Default rail generation (only creates rails if there are functional components)
        if self.functional_components:
            # Automated adding of VDD/VSS ring nets around cell based on found pins
            rail_number = 0
            for component in self.structural_components:
                if (re.search(r".*VDD.*", component.name, re.IGNORECASE) or
                        re.search(r".*VSS.*", component.name, re.IGNORECASE)):
                    self.__generate_trace_box_around_cell(
                        pin=component,
                        offset_x=self.INIT_RAIL_RING_OFFSET_X + self.RAIL_RING_OFFSET * rail_number,
                        offset_y=self.INIT_RAIL_RING_OFFSET_Y + self.RAIL_RING_OFFSET * rail_number,
                        width=self.RAIL_RING_WIDTH
                    )
                    rail_number += 1

            # Update the cell's bounding box based on added rails
            for nr, component in enumerate(self.structural_components):
                if isinstance(component, CircuitCell):
                    component.bounding_box.x1 -= (self.INIT_RAIL_RING_OFFSET_X + (self.RAIL_RING_OFFSET * rail_number)
                                                  - (self.RAIL_RING_OFFSET - self.RAIL_RING_WIDTH))
                    component.bounding_box.x2 += (self.INIT_RAIL_RING_OFFSET_X + (self.RAIL_RING_OFFSET * rail_number))
                    component.bounding_box.y1 -= (self.INIT_RAIL_RING_OFFSET_Y + (self.RAIL_RING_OFFSET * rail_number)
                                                  - (self.RAIL_RING_OFFSET - self.RAIL_RING_WIDTH))
                    component.bounding_box.y2 += (self.INIT_RAIL_RING_OFFSET_Y + (self.RAIL_RING_OFFSET * rail_number))

        # Root cell rail generation
        if self.circuit_cell.name == "ROOT_CELL":

            # Adjust cells bounding box to compensate for the last added cell
            self.circuit_cell.bounding_box.x2 -= self.RAIL_RING_OFFSET - self.RAIL_RING_WIDTH
            self.circuit_cell.bounding_box.y2 -= self.RAIL_RING_OFFSET - self.RAIL_RING_WIDTH

            # Automated adding of VDD/VSS ring nets around cell based on found pins
            rail_number = 0
            for component in self.structural_components:
                if (re.search(r".*VDD.*", component.name, re.IGNORECASE) or
                        re.search(r".*VSS.*", component.name, re.IGNORECASE)):

                    self.__generate_trace_box_around_cell(
                        pin=component,
                        offset_x=self.RAIL_RING_OFFSET - self.RAIL_RING_WIDTH + self.RAIL_RING_OFFSET * rail_number,
                        offset_y=self.RAIL_RING_OFFSET - self.RAIL_RING_WIDTH + self.RAIL_RING_OFFSET * rail_number,
                        width=self.RAIL_RING_WIDTH
                    )
                    rail_number += 1

            # There is no reason to update the bounding box since the root cell is not included in the
            # list of all components

    def get(self):
        return self.components
