import os
import time
from circuit_components import RectArea, Transistor, Capacitor, Resistor
from utilities import Text
from typing import List
from Magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image

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

    def place_black_white_picture(self, image_path: str):
        black_pixels, white_pixels = get_black_white_pixel_boxes_from_image(image_path)

        self.magic_file_lines.append(f"<< m1 >>")
        for box in black_pixels:
            rect_area = RectArea()
            rect_area.set(box)
            self.magic_file_lines.append(f"rect {rect_area.x1} {rect_area.y1} {rect_area.x2} {rect_area.y2}")

        self.magic_file_lines.append(f"<< m2 >>")
        for box in white_pixels:
            rect_area = RectArea()
            rect_area.set(box)
            self.magic_file_lines.append(f"rect {rect_area.x1} {rect_area.y1} {rect_area.x2} {rect_area.y2}")

    def place_text(self, layer: str, text: str):
        pixel_boxes = get_pixel_boxes_from_text(text)

        self.magic_file_lines.append(f"<< {layer} >>")

        for box in pixel_boxes:
            rect_area = RectArea()
            rect_area.set(box)
            self.magic_file_lines.append(f"rect {rect_area.x1} {rect_area.y1} {rect_area.x2} {rect_area.y2}")

    def place_box(self, layer: str, area: List[int]):
        rect_area = RectArea()
        rect_area.set(area)

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

    def magic_file_top_template(self):
        self.magic_file_lines.extend([
            "magic",
            "tech sky130A",
            "magscale 1 1",
            f"timestamp {int(time.time())}",
            "<< checkpaint >>",
            "rect 0 0 0 0"  # Rectangle completely covering everything in the cell. TBD!
        ])

    def file_creator(self):
        self.magic_file_top_template()

        # Just for testing from here:
        i = 1000

        for component in self.components:

            if isinstance(component, (Transistor, Capacitor, Resistor)):
                # Test placing
                i += 1500

                # Test transformation matrix
                component.transform_matrix.set([1, 0, i, 0, 1, 1500])
                self.cell_creator(component=component)

        self.place_black_white_picture("Carsten Wulff Picture.jpg")

        #self.place_box('m2', [0, 0, 100, 1500])
        #self.place_box('m1', [0, 1400, 1500, 1500])
        #self.place_box('viali', [10, 1500, 100, 1500])

        # Make your own libraries for MIM capacitor and BJT
        # To here!

        # Labels and properties
        self.magic_file_lines.extend([
            "<< labels >>",
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        # Write everything to file
        self.write_magic_file()


