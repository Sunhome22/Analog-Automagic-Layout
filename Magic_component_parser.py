import os
import re
from utilities import Text

class MagicComponentParser:
    def __init__(self, project_properties, component):
        self.project_name = project_properties.name
        self.project_name_long = project_properties.name_long
        self.project_directory = project_properties.directory
        self.standard_libraries = project_properties.standard_libraries
        self.component = component

    def get_info(self):
        return self.read_magic_file()

    def read_magic_file(self):
        layout_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                              f"{self.component.layout_library}/{self.component.layout_name}.mag")
        try:
            with open(layout_file_path, "r") as magic_file:
                for line in magic_file:
                    self._get_component_bounding_box_info(line)
                    self._get_component_port_info(line)
                return self.component

        except FileNotFoundError:
            print(f"{Text.ERROR} The file {layout_file_path} was not found.")

    def _get_component_bounding_box_info(self, line: str):

        if re.search(r'string FIXED_BBOX', line):
            line_words = line.split()
            self.component.b_box = list(map(int, line_words[2:6]))

    def _get_component_port_info(self, line: str):

        if re.search(r'flabel', line):
            self.component.layout_ports[0].type = "to"
            line_words = line.split()
            print(line)




        # with open(layout_file_path, "r") as file:
        #    file.read()