import os
import re
import time
import SPICE_parser
import Magic_component_parser
from circuit_components import RectArea
from utilities import Text
from typing import List
class MagicLayoutCreator:

    def __init__(self, project_properties, components):
        self.project_properties = project_properties
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

        print(f"{Text.INFO} Magic file created and written")


    def place_metal_box(self, layer: str, area_params: List[int]):
        rect_area = RectArea()
        rect_area.set(area_params)

        self.magic_file_lines.extend([
            f"<< {layer} >>",
            f"rect {rect_area.x1} {rect_area.y1} {rect_area.x2} {rect_area.y2}"
        ])


    def cell_creator(self, component):

        self.magic_file_lines.extend([
            f"use {component.layout_name} {component.name} ../{component.layout_library}",
            f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
            f" {component.transform_matrix.c} {component.transform_matrix.d}"
            f" {component.transform_matrix.e} {component.transform_matrix.f}",
            f"box {component.bounding_box.x1} {component.bounding_box.y1} {component.bounding_box.x2}"
            f" {component.bounding_box.y2}"
        ])

    def file_creator(self):

        # Top of magic file template
        self.magic_file_lines.extend([
            "magic",
            "tech sky130A",
            "magscale 1 1",
            f"timestamp {int(time.time())}",
            "<< checkpaint >>",
            "rect 0 0 0 0"  # Rectangle completely covering everything in the cell. TBD!
        ])

        i = 0
        for component in self.components:

            # Test placing
            if isinstance(component, (SPICE_parser.Transistor, SPICE_parser.Capacitor, SPICE_parser.Resistor)):
                i += 1200

                # Update component attributes with information from it's associated magic file
                component = Magic_component_parser.MagicComponentParser(self.project_properties, component).get_info()

                # Test transformation matrix
                component.transform_matrix.set([1, 0, i, 0, 1, 0])

                self.cell_creator(component=component)

        # Test placing
        self.place_metal_box('m2', [100, 100, 200, 1500])


        # Labels and properties
        self.magic_file_lines.extend([
            "<< labels >>",
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        # Write everything
        self.write_magic_file()

        # Temporary debugging
        print(f"\n{Text.DEBUG} Components registered:")
        for item in self.components:
            print(f"- {item}")

