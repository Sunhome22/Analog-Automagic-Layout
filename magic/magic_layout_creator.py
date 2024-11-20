# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import os
import time
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, Trace
from typing import List
from magic.magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image
from logger.logger import get_a_logger

# ============================================== Magic layout creator ==================================================
VIA_SIZE_OFFSET = 10

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
        self.traces_added = 0

        self.logger = get_a_logger(__name__)
        self.file_creator()

    def write_magic_file(self):
        magic_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                             f"{self.project_name_long}/{self.project_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        self.logger.info(f"Process complete! File '{self.project_name}.mag' was created. "
                         f"Components: {self.cells_added} Traces: {self.traces_added}")

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

    def place_box(self, layer: str, area: RectArea):

        self.magic_file_lines.extend([
            f"<< {layer} >>",
            f"rect {area.x1} {area.y1} {area.x2} {area.y2}"
        ])

    def via_adder(self, component):
        """Checks for overlap between segments of a trace in different layers and adds vias"""
        last_segment_layer = None

        for segment in component.segments:

            if segment.layer != last_segment_layer:
                last_segment_layer = segment.layer
                print(last_segment_layer)



    def trace_creator(self, component):
        via_count = 0
        segment_count = 0

        for segment in component.segments:
            self.place_box(layer=segment.layer, area=segment.area)
            segment_count += 1

        for via in component.vias:
            via.area.x1 = via.area.x1 + VIA_SIZE_OFFSET
            via.area.y1 = via.area.y1 + VIA_SIZE_OFFSET
            via.area.x2 = via.area.x2 - VIA_SIZE_OFFSET
            via.area.y2 = via.area.y2 - VIA_SIZE_OFFSET
            self.place_box(layer=via.layer, area=via.area)
            via_count += 1

        self.traces_added += 1
        self.logger.info(f"{component.instance} '{component.name}' placed. "
                         f"Segments: {segment_count} Vias: {via_count} ")

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
        self.logger.info(f"{component.instance} '{component.name} {component.layout_name}' "
                         f"placed with {component.transform_matrix}")

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

        for component in self.components:

            # Filter out pins, traces and circuit cells (temporary)
            if not isinstance(component, (Pin, CircuitCell, Trace)):
                self.cell_creator(component=component)

            # Handle Traces
            if isinstance(component, Trace):
                self.via_adder(component=component)
                self.trace_creator(component=component)

        # Labels and properties
        self.magic_file_lines.extend([
            "<< labels >>",
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        # Write everything to file
        self.write_magic_file()


