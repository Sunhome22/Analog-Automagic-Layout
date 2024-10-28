# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import os
import time
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell
from utilities.utilities import Text
from typing import List
from magic.magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image
from logger.logger import get_a_logger

# ============================================== Magic layout creator ==================================================


class MagicLayoutCreator:

    def __init__(self, project_properties, components):
        self.project_properties = project_properties
        self.project_name = project_properties.name
        self.project_name_long = project_properties.name_long
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.current_component_library_path = None
        self.components = components
        self.magic_file_lines = []
        self.cells_added = 0

        self.logger = get_a_logger(__name__)
        self.file_creator()

    def write_magic_file(self):
        magic_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                             f"{self.project_name_long}/{self.project_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        self.logger.info(f"Process complete! File '{self.project_name}.mag' was created with "
                         f"{self.cells_added} components")

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
        # Find library of current component
        self.current_component_library_path = next(
            (lib.path for lib in self.component_libraries if component.layout_library in lib.path), None)

        self.magic_file_lines.extend([
            f"use {component.layout_name} {component.name} {self.current_component_library_path}",
            f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
            f" {component.transform_matrix.c} {component.transform_matrix.d}"
            f" {component.transform_matrix.e} {component.transform_matrix.f}",
            f"box {component.bounding_box.x1} {component.bounding_box.y1} {component.bounding_box.x2}"
            f" {component.bounding_box.y2}"
        ])
        self.cells_added += 1
        self.logger.info(f"Component '{component.name} {component.layout_name}' placed with {component.transform_matrix}")

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

            # Filter out pins and circuit cells
            if not isinstance(component, (Pin, CircuitCell)):
                # Test placing
                i += 1500 #
                component.transform_matrix.set([0, 1, i, -1, 0, 1500]) # can't have floating point number on x!!!

                self.cell_creator(component=component)

        #self.place_black_white_picture("Carsten Wulff Picture.jpg")
        #self.place_box('m2', [0, 0, 100, 1500])
        #self.place_box('m1', [0, 1400, 1500, 1500])
        #self.place_box('viali', [10, 1500, 100, 1500])

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


