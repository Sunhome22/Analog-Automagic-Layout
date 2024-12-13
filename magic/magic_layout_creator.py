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
from typing import List
from magic.magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image
from logger.logger import get_a_logger
from collections import defaultdict, deque

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
        self.cells_added = 0
        self.traces_added = 0

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

    def __write_magic_file(self):
        magic_file_path = os.path.expanduser(f"{self.project_directory}design/"
                                             f"{self.project_lib_name}/{self.project_cell_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        self.logger.info(f"Process complete! File '{self.project_cell_name}.mag' was created. "
                         f"Components: {self.cells_added} Traces: {self.traces_added}")

    def __place_box(self, layer: str, area: RectArea):
        """Adds a box to the list of magic file lines"""
        self.magic_file_lines.extend([
            f"<< {layer} >>",
            f"rect {area.x1} {area.y1} {area.x2} {area.y2}"
        ])

    def __via_placer(self, start_layer: str, end_layer: str, area: RectArea):
        """Adds via(s) and potentially necessary metal layers between a top layer and a bottom layer"""

        VIA_OFFSET = 6  # Needs to be handled in the future, but works for now.

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

        # Place all necessary metal(s)
        if metal_layers is not None:
            for metal_layer in metal_layers:
                self.__place_box(layer=metal_layer, area=metal_area)

        # Place all necessary via(s)
        if via_layers is not None:
            for via_layer in via_layers:
                self.__place_box(layer=via_layer, area=area)

    def __add_trace_vias(self, component: Trace) -> int:
        """Checks for overlap between segments of a trace in different layers and adds vias.
        Returns the number of vias placed"""

        last_segment_layer = None
        segments_on_different_layers = []
        via_count = 0

        for segment in component.segments:

            if last_segment_layer != segment.layer:
                last_segment_layer = segment.layer

                segments_on_different_layers.append(segment)

            if len(segments_on_different_layers) == 2:

                # Handles first possible overlap orientation
                if segments_on_different_layers[0].area.x1 == segments_on_different_layers[1].area.x1:

                    via_area = RectArea(x1=segments_on_different_layers[0].area.x1,
                                        y1=segments_on_different_layers[0].area.y1,
                                        x2=segments_on_different_layers[1].area.x2,
                                        y2=segments_on_different_layers[0].area.y2)

                    self.__via_placer(start_layer=segments_on_different_layers[0].layer,
                                      end_layer=segments_on_different_layers[1].layer, area=via_area)

                    segments_on_different_layers.pop(0)
                    via_count += 1

                # Handles second possible overlap orientation
                elif segments_on_different_layers[0].area.y1 == segments_on_different_layers[1].area.y1:

                    via_area = RectArea(x1=segments_on_different_layers[0].area.x1,
                                        y1=segments_on_different_layers[0].area.y1,
                                        x2=segments_on_different_layers[0].area.x2,
                                        y2=segments_on_different_layers[1].area.y2)

                    self.__via_placer(start_layer=segments_on_different_layers[0].layer,
                                      end_layer=segments_on_different_layers[1].layer, area=via_area)

                    segments_on_different_layers.pop(0)
                    via_count += 1

                # Any thing else you be impossible
                else:
                    self.logger.error("An unexpteced overlap position between trace segments occured")

        return via_count

    def __add_trace_connection_point(self, trace: Trace):
        """Creates a connection point based on which layer a trace want to connect to a port"""

        # Iterate over all components
        for component in self.components:
            if not isinstance(component, (Pin, CircuitCell, Trace)):

                # Iterate over all ports for every segment of the current trace
                for port in component.layout_ports:
                    for segment in trace.segments:

                        segment_midpoint_x = abs(segment.area.x2)  # will always be on x2
                        segment_midpoint_y = (abs(segment.area.y2) - abs(segment.area.y1))//2 + abs(segment.area.y1)

                        # Get the position of the port in final layout by adding transform matrix details
                        port_pos = RectArea(x1=port.area.x1 + component.transform_matrix.c,
                                            x2=port.area.x2 + component.transform_matrix.c,
                                            y1=port.area.y1 + component.transform_matrix.f,
                                            y2=port.area.y2 + component.transform_matrix.f)

                        # Check if the segment point is within the bounds of a specific port
                        if (port_pos.y2 >= segment_midpoint_y >= port_pos.y1
                                and port_pos.x2 >= segment_midpoint_x >= port_pos.x1):

                            self.__via_placer(start_layer=segment.layer, end_layer=port.layer, area=port_pos)

                            self.logger.info(f"Connection point placed for port '{port.type}' of '{component.name}' "
                                             f"between layer '{port.layer}' and '{segment.layer}'")

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
        """Returns a list of layers between a start layer and an end layer based on a map"""

        try:
            graph = {}
            for (start, end), intermediate in via_map.items():
                graph.setdefault(start, []).append((end, intermediate))

            # Breadth first search (typical implementation)
            queue = deque([(start_layer, [])])  # current_node, intermediates_so_far
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

    def __trace_creator(self, component: Trace):
        via_count = 0
        segment_count = 0
        invalid_segments = 0

        # Check if segmemts are valid
        for segment in component.segments:
            if segment.area.x2 <= segment.area.x1 or segment.area.y2 <= segment.area.y1:
                invalid_segments += 1
                self.logger.error(f"For trace '{component.name}' segment area {segment.area} is invalid!")

        # Skip generation if there are invalid segmetns
        if invalid_segments != 0:
            return

        # Add segments
        for segment in component.segments:
            self.__place_box(layer=segment.layer, area=segment.area)
            segment_count += 1

        # Add vias at intersection points between segments that move up/down in layers
        via_count += self.__add_trace_vias(component)
        self.traces_added += 1
        self.logger.info(f"{component.instance} '{component.name}' placed with segments: {segment_count}"
                         f" vias: {via_count}")


    def __cell_creator(self, component):

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
        
        # Place transistors, resistors or capacitors
        for component in self.components:
            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.__cell_creator(component=component)

        # Place connection points
        for component in self.components:
            if isinstance(component, Trace):
                self.__add_trace_connection_point(trace=component)

        # Place traces
        for component in self.components:
            if isinstance(component, Trace):
                self.__trace_creator(component=component)

        # Labels and properties
        self.magic_file_lines.extend([
            "<< labels >>",
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        # Write everything to file
        self.__write_magic_file()


