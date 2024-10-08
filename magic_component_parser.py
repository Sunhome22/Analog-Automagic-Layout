# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import os
import re
from circuit_components import LayoutPort
from utilities import Text
from circuit_components import Pin

# ============================================= Magic component parser =================================================


class MagicComponentsParser:
    def __init__(self, project_properties, components):
        self.project_name = project_properties.name
        self.project_name_long = project_properties.name_long
        self.project_directory = project_properties.directory
        self.standard_libraries = project_properties.standard_libraries
        self.components = components
        self.component = None

    def get_info(self):
        return self.read_magic_files()

    def read_magic_files(self):

        for component in self.components:
            self.component = component

            # Filter out Pins
            if not isinstance(component, Pin):
                layout_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                                      f"{component.layout_library}/{component.layout_name}.mag")
                try:
                    with open(layout_file_path, "r") as magic_file:
                        for text_line in magic_file:
                            self._get_component_bounding_box_info(text_line=text_line)
                            self._get_component_port_info(text_line=text_line)

                        print(f"{Text.INFO} Magic layout port and bouding box info extracted for "
                              f"'{component.__class__.__name__}' named '{component.name}' with "
                              f"layout '{component.layout_name}'")

                except FileNotFoundError:
                    print(f"{Text.ERROR} The file {layout_file_path} was not found.")

        return self.components

    def _get_component_bounding_box_info(self, text_line: str):

        if re.search(r'string FIXED_BBOX', text_line):
            text_line_words = text_line.split()
            self.component.bounding_box.set(map(int, text_line_words[2:6]))

    def _get_component_port_info(self, text_line: str):

        if re.search(r'flabel', text_line):
            text_line_words = text_line.split()

            layout_port = LayoutPort(type=text_line_words[-1], layer=text_line_words[1], area_params=[
                int(text_line_words[3]), int(text_line_words[4]), int(text_line_words[5]), int(text_line_words[6])])

            self.component.layout_ports.append(layout_port)
