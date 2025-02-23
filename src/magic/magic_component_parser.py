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
import re
from circuit.circuit_components import LayoutPort, RectArea, Pin, CircuitCell, TraceNet
from logger.logger import get_a_logger
from dataclasses import fields
import libraries.atr_sky130a_lib as ATR

# ============================================= Magic component parser =================================================


class MagicComponentsParser:
    def __init__(self, project_properties, components):
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.current_component_library_path = None
        self.components = components
        self.logger = get_a_logger(__name__)

        # Component specific (gets reset for every component)
        self.found_transistor_well = False
        self.found_bounding_box = False
        self.transistor_well_size = RectArea

    def get(self):
        return self.__read_magic_files()

    def __read_magic_files(self):
        updated_components = 0

        # Iterate over all components
        for component in self.components:

            # Filter out pins, circuit cells and trace nets
            if not isinstance(component, (Pin, CircuitCell, TraceNet)):
                updated_components += 1

                # Find library of current component
                self.current_component_library_path = next(
                    (lib.path for lib in self.component_libraries if component.layout_library in lib.path), None)

                layout_file_path = os.path.expanduser(f"{self.current_component_library_path}/"
                                                      f"{component.layout_name}.mag")

                try:
                    with open(layout_file_path, "r") as magic_file:
                        for text_line in magic_file:
                            self.__get_component_bounding_box_info(text_line=text_line, component=component)
                            self.__get_component_port_info(text_line=text_line, component=component)

                            # ATR SKY130A LIB component handling
                            if any(lib for lib in self.component_libraries if re.search(r"ATR", lib.name)):
                                ATR.get_overlap_difference_for_atr_sky130a_lib(self=self, text_line=text_line,
                                                                               component=component)

                        self.__check_component_is_valid(component=component)

                except FileNotFoundError:
                    self.logger.error(f"The file {layout_file_path} was not found.")

        # Process complete
        self.logger.info(f"Process complete! Functional components updated: {updated_components}")

        return self.components



    def __get_component_bounding_box_info(self, text_line: str, component: object):

        if re.search(r'string FIXED_BBOX', text_line):
            text_line_words = text_line.split()
            component.bounding_box.set(map(int, text_line_words[2:6]))
            self.found_bounding_box = True

    def __get_component_port_info(self, text_line: str, component: object):

        if re.search(r'flabel', text_line):
            text_line_words = text_line.split()

            layout_port = LayoutPort(type=text_line_words[-1], layer=text_line_words[1],
                                     area=RectArea(x1=int(text_line_words[3]), y1=int(text_line_words[4]),
                                                   x2=int(text_line_words[5]), y2=int(text_line_words[6])))

            component.layout_ports.append(layout_port)

    @staticmethod
    def __adjust_port_sizes_to_minimum(component: object):
        """Adjust port sizes to the smallest one found. This is no longer in use"""
        port_areas = []
        port_with_minimum_area = None

        # Find the port with the smallest area
        for port in component.layout_ports:
            new_area = (port.area.x2 - port.area.x1) * (port.area.y2 - port.area.y1)
            port_areas.append(new_area)
            for area in port_areas:
                if len(port_areas) == 1:
                    port_with_minimum_area = port
                elif new_area < area:
                    port_with_minimum_area = port

        minimum_x_length = port_with_minimum_area.area.x2 - port_with_minimum_area.area.x1
        minimum_y_length = port_with_minimum_area.area.y2 - port_with_minimum_area.area.y1

        # Adjust port sizes to become the same as the area of the smallest port and center them
        for port in component.layout_ports:
            port.area.x1 = ((port.area.x2 - port.area.x1) // 2) + port.area.x1 - (minimum_x_length // 2)
            port.area.y1 = ((port.area.y2 - port.area.y1) // 2) + port.area.y1 - (minimum_y_length // 2)
            port.area.x2 = port.area.x1 + minimum_x_length
            port.area.y2 = port.area.y1 + minimum_y_length

    def __check_component_is_valid(self, component: object):

        # Check if both bounding box info and layout port info is present
        if not all(getattr(component.bounding_box, field.name) == 0 for field
                   in fields(component.bounding_box)) and component.layout_ports:
            self.logger.info(f"Found layout ports and bounding box for '{component.name}' from "
                             f"'{component.cell}' with layout '{component.layout_name}'")

        # Check if both bounding box info and layout port info is missing
        elif not component.layout_ports and all(getattr(component.bounding_box, field.name) == 0 for field
                                                in fields(component.bounding_box)):
            self.logger.error(f"Found no layout ports or bounding box for'{component.name}' from "
                              f"'{component.cell}' with layout '{component.layout_name}'")

        # Check if layout ports are missing
        elif not component.layout_ports:
            self.logger.error(f"Found no layout ports for '{component.name}' from "
                              f"'{component.cell}' with layout '{component.layout_name}'")

        # Bounding box is missing
        else:
            self.logger.error(f"Found no bounding box for'{component.name}' from "
                              f"'{component.cell}' with layout '{component.layout_name}'")

