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
from circuit.circuit_components import (RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, TraceNet,
                                        RectAreaLayer)
from magic.magic_drawer import get_pixel_boxes_from_text, get_black_white_pixel_boxes_from_image
from logger.logger import get_a_logger
from collections import deque
import tomllib
import re
import libraries.atr_sky130a_lib as atr
import copy

# ============================================== Magic layout creator ==================================================


class MagicLayoutCreator:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties, components):
        self.project_properties = project_properties
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.current_component_library_path = None
        self.components = components
        self.magic_file_lines = []
        self.total_functional_components_added = 0
        self.total_connection_points_added = 0
        self.total_trace_nets_added = 0
        self.total_vias_added = 0
        self.total_circuit_cells_added = 0

        self.config = self.__load_config()
        self.TECHNOLOGY = self.config["magic_layout_creator"]["TECHNOLOGY"]
        self.VIA_PADDING = self.config["magic_layout_creator"]["VIA_PADDING"]
        self.METAL_LAYERS = self.config["magic_layout_creator"]["METAL_LAYERS"]
        self.VIA_MAP = self.config["magic_layout_creator"]["VIA_MAP"]

        self.__generate_magic_files()

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def place_black_white_picture(self, image_path: str, layer1: str, layer2: str):
        """Not used"""
        black_pixels, white_pixels = get_black_white_pixel_boxes_from_image(image_path)

        self.magic_file_lines.append(f"<< {layer1} >>")
        for box in black_pixels:
            rect_area = RectArea()
            rect_area.set(box)
            self.magic_file_lines.append(f"rect {rect_area.x1} {rect_area.y1} {rect_area.x2} {rect_area.y2}")

        self.magic_file_lines.append(f"<< {layer2} >>")
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

    def __via_placer(self, start_layer: str, end_layer: str, area: RectArea, trace_net: TraceNet):
        """Adds via(s) and potentially necessary metal layers between a top layer and a bottom layer"""

        if start_layer == end_layer:
            self.logger.error(f"Can't place via between {start_layer} and {end_layer}")
            return

        # Build the complete via map
        via_map = {}
        for key, value in self.VIA_MAP.items():
            key_tuple = tuple(key.split("-"))

            # Add both the original and swapped key-value pairs to the map since traversal can go both directions
            via_map[key_tuple] = value
            via_map[key_tuple[::-1]] = value

        metal_layers = self.__get_inbetween_metal_layers(start_layer=start_layer, end_layer=end_layer,
                                                         metal_layer_list=self.METAL_LAYERS)
        via_layers = self.__get_inbetween_via_layers(start_layer=start_layer, end_layer=end_layer, via_map=via_map)

        # Metal area is increased with an offset to compensate for the via if via is present
        metal_area = RectArea(x1=area.x1, y1=area.y1, x2=area.x2, y2=area.y2)

        if via_layers is not None:
            metal_area = RectArea(x1=area.x1 - self.VIA_PADDING, y1=area.y1 - self.VIA_PADDING,
                                  x2=area.x2 + self.VIA_PADDING, y2=area.y2 + self.VIA_PADDING)

        trace_net.vias.append(RectAreaLayer(layer=f"{metal_layers[0]}-{metal_layers[1]}", area=area))

        # Place all required metal(s)
        if metal_layers is not None:
            for metal_layer in metal_layers:
                self.__place_box(layer=metal_layer, area=metal_area)

        # Place all required via(s)
        if via_layers is not None:
            for via_layer in via_layers:
                self.__place_box(layer=via_layer, area=area)

    def __add_trace_net_vias(self, trace_net: TraceNet) -> int:
        """Checks for overlap between segments of a trace net in different layers and adds vias.
           Vias only get added when layer changes occur."""
        previous_segment = None
        via_count = 0

        for segment in trace_net.segments:
            if previous_segment and previous_segment.layer != segment.layer:

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
                        area=via_area,
                        trace_net=trace_net
                    )
                    via_count += 1

            # Update the previous segment
            previous_segment = segment

        return via_count

    def __add_trace_net_connection_point(self, trace_net: TraceNet, components):
        """Creates a connection point based on which layer a trace segment wants to connect to a port.
        Multiple connections to a port will show as the connection point being added multiple times"""

        # Iterate over all components and filter out things that does not have ports
        for component in components:
            if not isinstance(component, (Pin, CircuitCell, TraceNet)):

                # Iterate over all ports for every segment of the current trace net
                for port in component.layout_ports:
                    for segment in trace_net.segments:

                        # Get port position in finished layout by adding transform matrix coordinates
                        port_pos = RectArea(x1=port.area.x1 + component.transform_matrix.c,
                                            x2=port.area.x2 + component.transform_matrix.c,
                                            y1=port.area.y1 + component.transform_matrix.f,
                                            y2=port.area.y2 + component.transform_matrix.f)

                        # Hinder placement of connection points to bulks since they are always connected in the
                        # lowest metal and cell to cell routing in the highest metal
                        if (port.type == "B" or segment.layer == self.METAL_LAYERS[0] or
                                segment.layer == self.METAL_LAYERS[4]):
                            continue

                        # Check for overlap between the port and the segment and add vias accordingly
                        if (not (segment.area.x2 < port_pos.x1 or segment.area.x1 > port_pos.x2 or
                                 segment.area.y2 < port_pos.y1 or segment.area.y1 > port_pos.y2)
                                and segment.layer != port.layer):

                            self.__via_placer(start_layer=segment.layer, end_layer=port.layer, area=port_pos,
                                              trace_net=trace_net)

                            self.total_connection_points_added += 1

                            self.logger.info(f"Connection placed on port '{port.type}' of '{component.name}' "
                                             f"between layer '{port.layer}' and '{segment.layer}' "
                                             f"for trace net '{trace_net.name}' of '{trace_net.named_cell}'")

    def __get_inbetween_metal_layers(self, start_layer: str, end_layer: str, metal_layer_list: list):
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

    def __trace_net_creator(self, trace_net: TraceNet):
        via_count = 0
        segment_count = 0

        # Check if segments are valid for being displayed in magic: x1 < x2 and y1 < y2
        for segment in trace_net.segments:
            if segment.area.x2 < segment.area.x1 or segment.area.y2 < segment.area.y1:
                self.logger.error(f"For trace '{trace_net.name}' segment area {segment.area} is invalid!")

        # Add predefined trace segments
        for segment in trace_net.segments:
            self.__place_box(layer=segment.layer, area=segment.area)
            segment_count += 1

        # Add predefined trace vias
        current_trace_net_vias = copy.deepcopy(trace_net.vias)
        trace_net.vias.clear()

        for via in current_trace_net_vias:
            self.__via_placer(start_layer=re.search(r'^[^-]+', via.layer).group(0),
                              end_layer=re.search(r'[^-]*$', via.layer).group(0),
                              area=via.area,
                              trace_net=trace_net)
            via_count += 1

        # Automatically create vias at intersection points between trace segments that move up/down in layers
        via_count += self.__add_trace_net_vias(trace_net=trace_net)

        self.logger.info(f"Trace net '{trace_net.name}' placed with segments: {segment_count} vias: {via_count}")
        self.total_vias_added += via_count
        self.total_trace_nets_added += 1

    def __functional_component_creator(self, component):

        # Find library of current functional component
        self.current_component_library_path = next(
            (lib.path for lib in self.component_libraries if component.layout_library in lib.path), None)

        self.magic_file_lines.extend([
            f"use {component.layout_name}  {component.group}_{component.name} "
            f"../{re.search(r'[^/]+$', self.current_component_library_path).group()}",
            f"timestamp {int(time.time())}",
            f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
            f" {component.transform_matrix.c} {component.transform_matrix.d}"
            f" {component.transform_matrix.e} {component.transform_matrix.f}",
            f"box {component.bounding_box.x1} {component.bounding_box.y1} {component.bounding_box.x2}"
            f" {component.bounding_box.y2}"
        ])
        self.total_functional_components_added += 1

        self.logger.info(f"{component.instance} '{component.name} {component.layout_name}' "
                         f"placed with {component.transform_matrix}")

        # ATR SKY130A LIB component handling
        if any(lib for lib in self.component_libraries if re.search(r"ATR", lib.name)):
            atr.place_transistor_endpoints_for_atr_sky130a_lib(self=self, component=component)

    def __pin_component_creator(self, component):
        # Check that layout type is valid
        if isinstance(component.layout, RectAreaLayer):
            self.magic_file_lines.extend([
                f"flabel {component.layout.layer} s {component.layout.area.x1} {component.layout.area.y1} "
                f"{component.layout.area.x2} {component.layout.area.y2} 0 FreeSans 400 0 0 0 {component.name}",
                f"port {component.number_id} nsew signal bidirectional"
            ])
            self.logger.info(f"{component.instance} '{component.name}' placed in layer '{component.layout.layer}' "
                             f"with {component.layout.area}")

    def __circuit_cell_component_creator(self, component):

        self.magic_file_lines.extend([
            f"use {component.cell} {component.named_cell} ",
            f"transform {component.transform_matrix.a} {component.transform_matrix.b}"
            f" {component.transform_matrix.c} {component.transform_matrix.d}"
            f" {component.transform_matrix.e} {component.transform_matrix.f}",
            f"box {component.bounding_box.x1} {component.bounding_box.y1} {component.bounding_box.x2}"
            f" {component.bounding_box.y2}"
        ])
        self.logger.info(f"{component.instance} '{component.named_cell}' of parent cell '{component.parent_cell}' "
                         f"placed with {component.transform_matrix}")

        self.total_circuit_cells_added += 1

    def __magic_file_top_template(self):
        self.magic_file_lines.extend([
            "magic",
            f"tech {self.TECHNOLOGY}",
            "magscale 1 1",
            f"timestamp {int(time.time())}",
            "<< checkpaint >>",
            "rect 0 0 1 1"  # Rectangle completely covering everything in the cell. TBD!
        ])

    def __magic_file_creator(self, components, file_name):
        self.__magic_file_top_template()

        # Place functional components
        for component in components:
            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.__functional_component_creator(component=component)

        # Place connection points
        for component in components:
            if isinstance(component, TraceNet):
                self.__add_trace_net_connection_point(trace_net=component, components=components)

        # Place trace nets
        for component in components:
            if isinstance(component, TraceNet):
                self.__trace_net_creator(trace_net=component)

        # Place circuit cells
        for component in components:
            if isinstance(component, CircuitCell):
                self.__circuit_cell_component_creator(component=component)

        # Place pins
        self.magic_file_lines.append("<< labels >>")
        for component in components:
            if isinstance(component, Pin):
                self.__pin_component_creator(component=component)

        # Properties
        self.magic_file_lines.extend([
            "<< properties >>",
        ])

        # Bottom of magic file template
        self.magic_file_lines.append("<< end >>")

        # Write everything to file
        self.__write_magic_file(file_name=file_name)

    def __write_magic_file(self, file_name):
        magic_file_path = os.path.expanduser(f"{self.project_directory}/design/"
                                             f"{self.project_top_lib_name}/{file_name}.mag")

        with open(magic_file_path, "w") as file:
            file.write("\n".join(self.magic_file_lines))

        self.logger.info(f"File '{file_name}.mag' was created. "
                         f"| Functional Components: {self.total_functional_components_added} | "
                         f"Connection Points: {self.total_connection_points_added} | "
                         f"Trace nets: {self.total_trace_nets_added} | Vias: {self.total_vias_added} | "
                         f"Circuit cells: {self.total_circuit_cells_added}")
        self.logger.info(f"============================================================================================"
                         f"============================================")

    def __generate_magic_files(self):
        cell_chains = []

        # Retrieve all sub cells
        for component in self.components:
            if isinstance(component, CircuitCell):
                cell_chains.append(component.cell_chain)

        # Iterate over found cells and generate .mag files for each one
        for cell_chain in cell_chains:
            cell = None
            cell_components = []

            self.magic_file_lines = []
            self.total_functional_components_added = 0
            self.total_connection_points_added = 0
            self.total_trace_nets_added = 0
            self.total_vias_added = 0
            self.total_circuit_cells_added = 0

            for component in self.components:

                if isinstance(component, CircuitCell):
                    # Assign new cell name on change
                    if component.cell_chain == cell_chain:
                        cell = component.cell

                if component.cell_chain == "":
                    self.logger.error(f"{component.name} is missing a cell chain")
                    continue

                if component.cell_chain != cell_chain:
                    continue

                if cell is None:
                    cell = component.cell

                if not isinstance(component, CircuitCell):
                    cell_components.append(component)

            # Top cell handling
            if cell_chain == "UTOP_" + self.project_top_cell_name:
                cell = self.project_top_cell_name

            # Add circuit cells that has the current cell as parent and do not have the same name
            for comp in self.components:
                if (isinstance(comp, CircuitCell) and comp.parent_cell == cell and
                        all(existing_comp.named_cell != comp.named_cell for existing_comp in cell_components)):
                    cell_components.append(comp)

            # Create file if component list is not empty
            self.__magic_file_creator(components=cell_components, file_name=cell)

        self.logger.info("Process complete!")