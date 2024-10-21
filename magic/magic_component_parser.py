# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import os
import re
from circuit.circuit_components import LayoutPort, RectArea, Pin
from utilities.utilities import Text
from logger.logger import get_a_logger

# ============================================= Magic component parser =================================================


class MagicComponentsParser:
    def __init__(self, project_properties, components):
        self.project_name = project_properties.name
        self.project_name_long = project_properties.name_long
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.current_component_library_path = None
        self.components = components
        self.component = None
        self.logger = get_a_logger(__name__)

    def get_info(self):
        return self.__read_magic_files()

    def __read_magic_files(self):
        updated_components = 0
        for component in self.components:
            self.component = component

            # Filter out Pins
            if not isinstance(component, Pin):
                updated_components += 1

                # Find library of current component using matching
                self.current_component_library_path = next(
                    (lib.path for lib in self.component_libraries if component.layout_library in lib.path), None)

                layout_file_path = os.path.expanduser(f"{self.current_component_library_path}/"
                                                      f"{component.layout_name}.mag")

                try:
                    with open(layout_file_path, "r") as magic_file:
                        for text_line in magic_file:
                            self.__get_component_bounding_box_info(text_line=text_line)
                            self.__get_component_port_info(text_line=text_line)

                        self.logger.info(f"Found layout ports and bouding box for '{component.name}' from "
                                         f"'{component.cell}' with layout '{component.layout_name}'")

                except FileNotFoundError:
                    self.logger.error(f"The file {layout_file_path} was not found.")

        # Process complete
        self.logger.info(f"Process complete! Components updated: {updated_components}")

        return self.components

    def __get_component_bounding_box_info(self, text_line: str):

        if re.search(r'string FIXED_BBOX', text_line):
            text_line_words = text_line.split()
            self.component.bounding_box.set(map(int, text_line_words[2:6]))

    def __get_component_port_info(self, text_line: str):

        if re.search(r'flabel', text_line):
            text_line_words = text_line.split()

            layout_port = LayoutPort(type=text_line_words[-1], layer=text_line_words[1],
                                     area=RectArea(x1=int(text_line_words[3]), y1=int(text_line_words[4]),
                                                   x2=int(text_line_words[5]), y2=int(text_line_words[6])))

            self.component.layout_ports.append(layout_port)
