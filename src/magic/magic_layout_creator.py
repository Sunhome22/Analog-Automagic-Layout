# ==================================================================================================================== #
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #

# ================================================== Libraries =========================================================
import os
import time
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, Trace
from magic.magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image
from logger.logger import get_a_logger
from collections import deque

# ============================================== Magic layout creator ==================================================


class MagicLayoutCreator:

    def __init__(self, project_properties, components):
        self.project_properties = project_properties
        self.project_cell_name = project_properties.cell_name
        self.project_lib_name = project_properties.lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.current_component_library_path = None
        self.components = components
        self.magic_file_lines = []
        self.total_functional_components_added = 0
        self.total_connection_points_added = 0
        self.total_traces_added = 0
        self.total_vias_added = 0

        self.logger = get_a_logger(__name__)
        self.__file_creator()

    def place_black_white_picture(self, image_path: str):
        """Not used"""
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
        """Not used"""
        pixel_boxes = get_pixel_boxes_from_text(text)

        self.magic_file_lines.append(f"<< {layer} >>")

        for box in pixel_boxes:
            rect_area = RectArea()
            rect_area.set(box)
            self.magic_file_lines.append(f"rect {rect_area.x1} {rect_area.y1} {rect_area.x2} {rect_area.y2}")

    def __place_box(self, layer: str, area: RectArea):
        """Adds a box to the list of magic file lines"""
        self.magic_file_lines.extend([
            f"<< {layer} >>",
            f"rect {area.x1} {area.y1} {area.x2} {area.y2}"
        ])

    def __via_placer(self, start_layer: str, end_layer: str, area: RectArea):
        """Adds via(s) and potentially necessary metal layers between a top layer and a bottom layer"""

        VIA_OFFSET = 7  # Needs to be handled in the future, but works for now.

        via_map = {
            ('locali', 'm1'): 'viali',
            ('m1', 'locali'): 'viali',
            ('m1', 'm2'): 'via1',
            ('m2', 'm1'): 'via1',
            ('m2', 'm3'): 'via2',
            ('m3', 'm2'): 'via2',
            ('m3', 'm4'): 'via3',
            ('m4', 'm3'): 'via3',
        }
        metal_layer_list = ['locali', 'm1', 'm2', 'm3', 'm4']

        metal_layers = self.get_inbetween_metal_layers(start_layer=start_layer, end_layer=end_layer,
                                                       metal_layer_list=metal_layer_list)
        via_layers = self.__get_inbetween_via_layers(start_layer=start_layer, end_layer=end_layer, via_map=via_map)

        # Metal area is increased with an offset to compensate for the via if via is present
        metal_area = RectArea(x1=area.x1, y1=area.y1, x2=area.x2, y2=area.y2)
        if via_layers is not None:
            metal_area = RectArea(x1=area.x1 - VIA_OFFSET, y1=area.y1 - VIA_OFFSET,
                                  x2=area.x2 + VIA_OFFSET, y2=area.y2 + VIA_OFFSET)

        # Place all required metal(s)
        if metal_layers is not None:
            for metal_layer in metal_layers:
                self.__place_box(layer=metal_layer, area=metal_area)

        # Place all required via(s)
        if via_layers is not None:
            for via_layer in via_layers:
                self.__place_box(layer=via_layer, area=area)

    def __add_trace_vias(self, trace: Trace) -> int:
        """Checks for overlap between segments of a trace in different layers and adds vias."""
        last_segment_layer = None
        previous_segment = None
        via_count = 0

        for segment in trace.segments:

            if last_segment_layer != segment.layer:
                last_segment_layer = segment.layer

                if previous_segment:

                    # Calculate overlap
                    overlap_x1 = max(previous_segment.area.x1, segment.area.x1)
                    overlap_y1 = max(previous_segment.area.y1, segment.area.y1)
                    overlap_x2 = min(previous_segment.area.x2, segment.area.x2)
                    overlap_y2 = min(previous_segment.area.y2, segment.area.y2)

                    # Skip if no overlap
                    if overlap_x1 < overlap_x2 and overlap_y1 < overlap_y2:

                        # Define via area
                        via_area = RectArea(
                            x1=overlap_x1,
                            y1=overlap_y1,
                            x2=overlap_x2,
                            y2=overlap_y2
                        )
                        # Place the via
                        self.__via_placer(
                            start_layer=previous_segment.layer,
                            end_layer=segment.layer,
                            area=via_area
                        )
                        via_count += 1

                # Update the previous segment
                previous_segment = segment

        return via_count

    def __add_trace_connection_point(self, trace: Trace):
        """Creates a connection point based on which layer a trace wants to connect to a port.
        Multiple connections to a port will show as the connection point being added multiple times"""

        # Iterate over all components and filter out things that does not have ports
        for component in self.components:
            if not isinstance(component, (Pin, CircuitCell, Trace)):

                # Iterate over all ports for every segment of the current trace
                for port in component.layout_ports:
                    for segment in trace.segments:

                        # Get port position in finished layout by adding transform matrix coordinates
                        port_pos = RectArea(x1=port.area.x1 + component.transform_matrix.c,
                                            x2=port.area.x2 + component.transform_matrix.c,
                                            y1=port.area.y1 + component.transform_matrix.f,
                                            y2=port.area.y2 + component.transform_matrix.f)

                        # Check for overlap between the port and the segment and add vias accordingly
                        if not (segment.area.x2 < port_pos.x1 or segment.area.x1 > port_pos.x2 or
                                segment.area.y2 < port_pos.y1 or segment.area.y1 > port_pos.y2):

                            self.__via_placer(start_layer=segment.layer, end_layer=port.layer, area=port_pos)

                            self.total_connection_points_added += 1

                            self.logger.info(f"Connection placed on port '{port.type}' of '{component.name}' "
                                             f"between layer '{port.layer}' and '{segment.layer}' "
                                             f"for trace '{trace.name}'")

    def get_inbetween_metal_layers(self, start_layer: str, end_layer: str, metal_layer_list: list):
        """Gets all metal layers, including start and end layer, and deals with if their positions are
            effectively swapped in the metal layer list"""

        try:
            # Get layers between the start and end (inclusive)
            result = metal_layer_list[min(metal_layer_list.index(start_layer), metal_layer_list.index(end_layer)):
                                      max(metal_layer_list.index(start_layer), metal_layer_list.index(end_layer)) + 1]
            return result

        except ValueError:
            self.logger.error(f"Could not get layers inbetween '{start_layer}' to '{end_layer}'")

    def __get_inbetween_via_layers(self, start_layer: str, end_layer: str, via_map: dict):
        """Returns a list of layers between a start layer and an end layer based on a map using
           the breath first search algorithm"""

        try:
            graph = {}
            for (start, end), intermediate in via_map.items():
                graph.setdefault(start, []).append((end, intermediate))

            queue = deque([(start_layer, [])])  # current node, intermediates so far
            visited = set()

            while queue:
                current_node, intermediates = queue.popleft()

                # Return nodes if the target is reached
                if current_node == end_layer:
                    return intermediates

                # Go through neighbors
                visited.add(current_node)
                for neighbor, intermediate in graph.get(current_node, []):
                    if neighbor not in visited:
                        queue.append((neighbor, intermediates + [intermediate]))

            return None  # No path found

        except ValueError:
            self.logger.error(f"Could not get layers inbetween '{start_layer}' to '{end_layer}'")

    def __trace_creator(self, trace: Trace):
        via_count = 0
        segment_count = 0

        # Basic check if segments are valid for being displayed in magic: x1 < x2 and y1 < y2
        for segment in trace.segments:
            if segment.area.x2 < segment.area.x1 or segment.area.y2 < segment.area.y1:
                self.logger.error(f"For trace '{trace.name}' segment area {segment.area} is invalid!")

        # Add segments
        for segment in trace.segments:
            self.__place_box(layer=segment.layer, area=segment.area)
            segment_count += 1

        # Add vias at intersection points between segments that move up/down in layers
        via_count += self.__add_trace_vias(trace=trace)

        self.logger.info(f"{trace.instance} '{trace.name}' placed with segments: {segment_count} vias: {via_count}")
        self.total_vias_added += via_count
        self.total_traces_added += 1

    def __functional_component_creator(self, component):

        # Find library of current functional component
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
        self.total_functional_components_added += 1

        self.logger.info(f"{component.instance} '{component.name} {component.layout_name}' "
                         f"placed with {component.transform_matrix}")

    def __structural_component_creator(self, component):
        print("TBD")

    def __magic_file_top_template(self):
        self.magic_file_lines.extend([
            "magic",
            "tech sky130A",
            "magscale 1 1",
            f"timestamp {int(time.time())}",
            "<< checkpaint >>",
            "rect 0 0 0 0"  # Rectangle completely covering everything in the cell. TBD!
        ])

    def __file_creator(self):
        self.__magic_file_top_template()

        # Place functional components
        for component in self.components:
            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.__functional_component_creator(component=component)

        # Place connection points
        for component in self.components:
            if isinstance(component, Trace):
                self.__add_trace_connection_point(trace=component)

        # Place traces
        for component in self.components:
            if isinstance(component, Trace):
                self.__trace_creator(trace=component)

        # Labels and properties
        self.magic_file_lines.extend([
            "<< labels >>",
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        # Write everything to file
        self.__write_magic_file()

    def __write_magic_file(self):
        magic_file_path = os.path.expanduser(f"{self.project_directory}/design/"
                                             f"{self.project_lib_name}/{self.project_cell_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        self.logger.info(f"Process complete! File '{self.project_cell_name}.mag' was created. "
                         f"| Functional Components: {self.total_functional_components_added} | "
                         f"Connection Points: {self.total_connection_points_added} | "
                         f"Traces: {self.total_traces_added} | Vias: {self.total_vias_added} |")



