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
from circuit.circuit_components import LayoutPort, RectArea, Transistor, Capacitor, Resistor, DigitalBlock
from logger.logger import get_a_logger
from dataclasses import fields
import libraries.atr_sky130a_lib as atr
import libraries.tr_sky130a_lib as tr
import libraries.aal_misc_sky130a_lib as aal

# ============================================= Magic component parser =================================================


class MagicComponentsParser:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties, components):
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.current_component_library_path = None
        self.components = components

        # Component specific (gets reset for every component)
        self.found_transistor_well = False
        self.found_bounding_box = False
        self.transistor_well_size = RectArea
        self.scale_factor = 0

    def get(self):
        return self.__read_magic_files()

    def __read_magic_files(self):
        updated_components = 0

        # Iterate over all components
        for component in self.components:

            if isinstance(component, (Transistor, Capacitor, Resistor, DigitalBlock)):
                updated_components += 1

                # Find library of current component
                self.current_component_library_path = next(
                    (lib.path for lib in self.component_libraries if component.layout_library in lib.path), None)

                layout_file_path = os.path.expanduser(f"{self.current_component_library_path}/"
                                                      f"{component.layout_name}.mag")

                # General component handling
                try:
                    with open(layout_file_path, "r") as magic_file:
                        for text_line in magic_file:
                            self.__get_scale_factor(text_line=text_line)
                            self.__get_component_port_info(text_line=text_line, component=component)
                except FileNotFoundError:
                    self.logger.error(f"The file {layout_file_path} was not found.")

                # ATR SKY130A LIB component handling
                if re.search(r'_ATR_', component.layout_library):
                    atr.magic_component_parsing_for_atr_sky130a_lib(self=self, layout_file_path=layout_file_path,
                                                                    component=component)
                # TR SKY130A LIB component handling
                if re.search(r'_TR_', component.layout_library):
                    tr.magic_component_parsing_for_tr_sky130a_lib(self=self, layout_file_path=layout_file_path,
                                                                  component=component)
                # AAL MISC SKY130A LIB component handling
                if re.search(r'AAL_MISC', component.layout_library):
                    aal.magic_component_parsing_for_aal_misc_sky130a_lib(self=self, layout_file_path=layout_file_path,
                                                                         component=component)

                self.__check_component_is_valid(component=component)

        # Process complete
        self.logger.info(f"Process complete! Functional components updated: {updated_components}")

        return self.components

    @staticmethod
    def __get_port_metal_layer(input_value):
        if input_value in ['locali', 'm1', 'm2', 'm3', 'm4', 'm5']:
            return input_value

        metal_mapping = {
            'metal1': 'm1',
            'metal2': 'm2',
            'metal3': 'm3',
            'metal4': 'm4',
            'metal5.': 'm5'
        }
        return metal_mapping.get(input_value, "Invalid metal")

    def __get_scale_factor(self, text_line: str):
        if re.search(r'magscale', text_line):
            text_line_words = text_line.split()
            self.scale_factor = int(text_line_words[2])

    def __get_component_port_info(self, text_line: str, component: Transistor | Resistor | Capacitor):

        if re.search(r'flabel', text_line):
            text_line_words = text_line.split()

            layout_port = LayoutPort(type=text_line_words[-1], layer=text_line_words[1],
                                     area=RectArea(x1=int(text_line_words[3]) // self.scale_factor,
                                                   y1=int(text_line_words[4]) // self.scale_factor,
                                                   x2=int(text_line_words[5]) // self.scale_factor,
                                                   y2=int(text_line_words[6]) // self.scale_factor))

            component.layout_ports.append(layout_port)

    @staticmethod
    def __adjust_port_sizes_to_minimum(component: Transistor | Resistor | Capacitor):
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

    def __check_component_is_valid(self, component: Transistor | Resistor | Capacitor):

        # Check if both bounding box info and layout port info is present
        if not all(getattr(component.bounding_box, field.name) == 0 for field
                   in fields(component.bounding_box)) and component.layout_ports:
            self.logger.info(f"Found layout ports and bounding box for '{component.name}' from named cell "
                             f"'{component.named_cell}' in '{component.parent_cell}' with layout "
                             f"'{component.layout_name}'")

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
