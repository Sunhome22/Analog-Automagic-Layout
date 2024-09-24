import os
import re
import time
import SPICE_parser

from utilities import TextColor


class MagicLayoutCreator:

    def __init__(self, project_properties, components):
        self.project_name = project_properties.name
        self.project_name_long = project_properties.name_long
        self.project_directory = project_properties.directory
        self.standard_libraries = project_properties.standard_libraries
        self.components = components
        self.magic_file_lines = list

        self.creator()

    def write_magic_file(self):
        magic_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                             f"{self.project_name_long}/{self.project_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        print(f"{TextColor.INFO} Magic file created and written")

    def open_magic_file(self):
        pass

    def place_metal(self, layer):
        pass

    def creator(self):
        i = 0

        # Top of file template
        self.magic_file_lines = [
            "magic",
            "tech sky130A",
            "magscale 1 1",
            f"timestamp {int(time.time())}",
            "<< checkpaint >>",
            "rect 0 0 0 0"
        ]

        for component in self.components:

            if isinstance(component, SPICE_parser.Transistor):
                i += 1500
                self.magic_file_lines.append(f"use {component.layout} {component.name} ../{component.library}")
                self.magic_file_lines.append(f"transform 1 0 {i} 0 1 0")
                self.magic_file_lines.append(f"box 0 0 0 0")

            if isinstance(component, SPICE_parser.Capacitor):
                self.magic_file_lines.append(f"use {component.layout} {component.name} ../{component.library}")
                self.magic_file_lines.append(f"transform 1 0 500 0 1 0")
                self.magic_file_lines.append(f"box 0 0 0 0")

        # Bottom of file template
        self.magic_file_lines.append("<< labels >>")
        self.magic_file_lines.append("<< properties >>")
        self.magic_file_lines.append("<< end >>")

        self.write_magic_file()

        # Temporary debugging
        print(f"\n{TextColor.DEBUG} Components registered:")
        for item in self.components:
            print(f"- {item}")

