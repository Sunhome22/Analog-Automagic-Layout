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
        self.magic_file_lines = []

        self.file_creator()

    def write_magic_file(self):
        magic_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                             f"{self.project_name_long}/{self.project_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        print(f"{TextColor.INFO} Magic file created and written")

    def _get_bounding_box_info_for_component(self, component):
        print(component.library)
        layout_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                            f"{component.library}/{component.layout_name}.mag")

        #with open(layout_file_path, "r") as file:
        #    file.read()

    def place_metal(self, layer):
        pass

    def cell_creator(self, component):

        self.magic_file_lines.extend([
            f"use {component.layout_name} {component.name} ../{component.library}",
            f"transform {component.t_matrix[0]} {component.t_matrix[1]} {component.t_matrix[2]}"
            f" {component.t_matrix[3]} {component.t_matrix[4]} {component.t_matrix[5]}",
            f"box {component.b_box[0]} {component.b_box[1]} {component.b_box[2]} {component.b_box[3]}"
        ])

    def file_creator(self):

        # Top of magic file template
        self.magic_file_lines.extend([
            "magic",
            "tech sky130A",
            "magscale 1 1",
            f"timestamp {int(time.time())}",
            "<< checkpaint >>",
            "rect 0 0 0 0" # Rectangle completely covering everything in the cell. TBD!
        ])

        i = 0

        for component in self.components:
            i += 500

            if isinstance(component, SPICE_parser.Transistor):
                self._get_bounding_box_info_for_component(component)
                component.t_matrix = [1, 0, i, 0, 1, 0] # test
                component.b_box = [0, 0, 0, 0]
                self.cell_creator(component=component)


            if isinstance(component, SPICE_parser.Capacitor):
                self.magic_file_lines.append(f"use {component.layout_name} {component.name} ../{component.library}")
                self.magic_file_lines.append(f"transform 1 0 0 0 1 0")
                self.magic_file_lines.append(f"box 0 0 0 0")


        # Labels and properties
        self.magic_file_lines.extend([
            "<< labels >>",
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        self.write_magic_file()

        # Temporary debugging
        print(f"\n{TextColor.DEBUG} Components registered:")
        for item in self.components:
            print(f"- {item}")

