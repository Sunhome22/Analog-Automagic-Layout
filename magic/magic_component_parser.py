# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import os
import re
from circuit.circuit_components import LayoutPort, RectArea, Pin
from utilities.utilities import Text

# ============================================= Magic component parser =================================================


class MagicComponentsParser:
    def __init__(self, project_properties, components):
        self.project_name = project_properties.name
        self.project_name_long = project_properties.name_long
        self.project_directory = project_properties.directory
        self.components = components
        self.component = None

    def get_info(self):
        return self.__read_magic_files()

    def __read_magic_files(self):
        updated_components = 0
        for component in self.components:
            self.component = component

            # Filter out Pins
            if not isinstance(component, Pin):
                updated_components += 1
                layout_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                                      f"{component.layout_library}/{component.layout_name}.mag")
                try:
                    with open(layout_file_path, "r") as magic_file:
                        for text_line in magic_file:
                            self.__get_component_bounding_box_info(text_line=text_line)
                            self.__get_component_port_info(text_line=text_line)

                        print(f"{Text.INFO} {Text.MAGIC_PARSER} Found layout ports and bouding box for"
                              f" '{component.name}' from '{component.cell}' with"
                              f" layout '{component.layout_name}'")

                except FileNotFoundError:
                    print(f"{Text.ERROR} The file {layout_file_path} was not found.")

        # Process complete
        print(f"{Text.INFO} {Text.MAGIC_PARSER} ======================================================================="
              f"==========================")
        print(f"{Text.INFO} {Text.MAGIC_PARSER} Process completed!"
              f" Components updated: {updated_components}")
        print(f"{Text.INFO} {Text.MAGIC_PARSER} ======================================================================="
              f"==========================")

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
