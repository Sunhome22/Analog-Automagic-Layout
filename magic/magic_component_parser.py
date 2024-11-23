# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import os
import re
from circuit.circuit_components import LayoutPort, RectArea, Pin, CircuitCell, Transistor, Trace
from logger.logger import get_a_logger
from dataclasses import dataclass, fields

# ============================================= Magic component parser =================================================


class MagicComponentsParser:
    def __init__(self, project_properties, components):
        self.project_name = project_properties.name
        self.project_name_long = project_properties.name_long
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.current_component_library_path = None
        self.components = components
        self.logger = get_a_logger(__name__)

        # Component specific (gets reset for every component)
        self.found_transistor_well = False
        self.found_bounding_box = False
        self.transistor_well_size = RectArea

    def get_info(self):
        return self.__read_magic_files()

    def __read_magic_files(self):
        updated_components = 0

        # Iterate over all components
        for component in self.components:

            # Filter out pins, circuit cells and traces
            if not isinstance(component, (Pin, CircuitCell, Trace)):
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
                            self.__get_overlap_difference_for_cmos_transistors(text_line=text_line, component=component)

                        self.__basic_component_is_valid_check(component=component)

                except FileNotFoundError:
                    self.logger.error(f"The file {layout_file_path} was not found.")

        # Process complete
        self.logger.info(f"Process complete! Components updated: {updated_components}")

        return self.components

    def __get_overlap_difference_for_cmos_transistors(self, text_line: str, component: object):

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
                                    - (abs(component.bounding_box.x1) + abs(component.bounding_box.x2)))/2)
                y_difference = int((abs(self.transistor_well_size.y1) + abs(self.transistor_well_size.y2)
                                    - (abs(component.bounding_box.y1) + abs(component.bounding_box.y2)))/2)

                component.overlap_distance.x = x_difference
                component.overlap_distance.y = y_difference

                self.found_bounding_box = False

        self.found_bounding_box = False

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

    def __basic_component_is_valid_check(self, component):

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

