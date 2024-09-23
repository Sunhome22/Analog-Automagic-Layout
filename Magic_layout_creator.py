import os
import re
import time
import SPICE_parser
from utilities import TextColor

class MagicLayoutCreator:

    def __init__(self, project_name, project_name_long, project_dir, components):
        self.project_name = project_name
        self.project_name_long = project_name_long
        self.project_dir = project_dir
        self.components = components
        self.magic_file_lines = list
        self.creator()

    def write_magic_file(self):
        magic_file_path = os.path.expanduser(f"{self.project_dir}design/{self.project_name_long}/{self.project_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        print(f"{TextColor.INFO} Magic file created and written")

    def place_metal(self, layer):
        pass

    def creator(self):
        self.magic_file_lines = [
            "magic",
            "tech sky130A",
            "magscale 1 1",
            f"timestamp {int(time.time())}",
            "<< checkpaint >>"
        ]
        for component in self.components:

            if isinstance(component, SPICE_parser.Transistor):
                self.magic_file_lines.append("rect 0 0 0 0")
                self.magic_file_lines.append(f"use {component.layout} {component.name} ../JNW_ATR_SKY130A")
                self.magic_file_lines.append("transform 1 0 0 0 1 0")
                self.magic_file_lines.append("box 0 0 0 0")

        self.magic_file_lines.append("<< labels >>")
        self.magic_file_lines.append("<< properties >>")
        self.magic_file_lines.append("<< end >>")

        self.write_magic_file()

        # Temporary debugging
        print(f"\n{TextColor.DEBUG} Components registered:")
        for item in self.components:
            print(f"- {item}")

