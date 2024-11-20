# TODO: Add copyright/license notice

# ================================================== Libraries =========================================================
import os
import time
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, Trace
from typing import List
from magic.magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image
from logger.logger import get_a_logger
from collections import defaultdict, deque

# ============================================== Magic layout creator ==================================================
VIA_SIZE_OFFSET = 5

via_map = {
    ('locali', 'm1'): 'viali',
    ('m1', 'm2'): 'via1',
    ('m2', 'm3'): 'via2'
}

intermediate_metal_layers = {
    ('locali', 'm2'): 'm1',
    ('m1', 'm3'): 'm2',
    ('m2', 'm4'): 'm3'
}

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

    def add_trace_vias(self, component):
        """Checks for overlap between segments of a trace in different layers and adds vias"""
        last_segment_layer = None

        for segment in component.segments:

            if segment.layer != last_segment_layer:
                last_segment_layer = segment.layer
                print(last_segment_layer)

    def add_trace_connection_point(self, trace):
        # TODO: Make this more understandable

        # Iterate over all components
        for component in self.components:
            if not isinstance(component, (Pin, CircuitCell, Trace)):

                # Iterate over all ports for every segment of the current trace
                for port in component.layout_ports:
                    for segment in trace.segments:

                        segment_midpoint_x = abs(segment.area.x2) # will always be on x2
                        segment_midpoint_y = (abs(segment.area.y2) - abs(segment.area.y1))//2 + abs(segment.area.y1)

                        # Get the actual position of the port by adding transform matrix details
                        port_pos = RectArea(x1=port.area.x1 + component.transform_matrix.c,
                                            x2=port.area.x2 + component.transform_matrix.c,
                                            y1=port.area.y1 + component.transform_matrix.f,
                                            y2=port.area.y2 + component.transform_matrix.f)

                        # Check if the segment point is within the bounds of a specific port
                        if (port_pos.y2 >= segment_midpoint_y >= port_pos.y1
                                and port_pos.x2 >= segment_midpoint_x >= port_pos.x1):

                            metal_layers = self.get_inbetween_layers(start_layer=segment.layer, end_layer=port.layer,
                                                                     map=intermediate_metal_layers)

                            via_layers = self.get_inbetween_layers(start_layer=segment.layer, end_layer=port.layer,
                                                                   map=via_map)

                            # Place all necessary metal(s)
                            self.place_box(layer=segment.layer, area=port_pos)

                            for metal_layer in metal_layers:
                                self.place_box(layer=metal_layer, area=port_pos)


                            # Set via size in relation to port
                            via_pos = RectArea(x1=port_pos.x1 + 5, y1=port_pos.y1 + 5,
                                               x2=port_pos.x2 - 5, y2=port_pos.y2 - 5)

                            # Place all necessary via(s)
                            for via_layer in via_layers:
                                self.place_box(layer=via_layer, area=via_pos)



    def get_inbetween_layers(self, start_layer, end_layer, map):
        path = []
        current_layer = start_layer

        while current_layer != end_layer:
            # Find the next layer to traverse
            found = False
            for (layer1, layer2), item in map.items():
                if current_layer == layer1 and layer2 not in path:
                    path.append(item)
                    current_layer = layer2
                    found = True
                    break
                elif current_layer == layer2 and layer1 not in path:
                    path.append(item)
                    current_layer = layer1
                    found = True
                    break

            if not found:
                return self.logger.error(f"A problem occurred between these layers: {start} to {end}")

        return path



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
                self.add_trace_connection_point(trace=component)
                self.trace_creator(component=component)
                self.add_trace_vias(component=component)

        # Labels and properties
        self.magic_file_lines.extend([
            "<< labels >>",
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        # Write everything to file
        self.write_magic_file()


