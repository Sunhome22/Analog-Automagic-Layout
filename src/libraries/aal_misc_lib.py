# ==================================================================================================================== #
# Copyright (C) 2025 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #

# ===================================================== Libraries ======================================================
import re
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from itertools import groupby
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict
from logger.logger import get_a_logger
from circuit.circuit_components import (RectArea, RectAreaLayer, Transistor, Capacitor, Resistor, Pin, CircuitCell,
                                        TraceNet, RectAreaLayer, DigitalBlock)

# ======================================================================================================================
# ================================================== AAL MISC handling =================================================
# ======================================================================================================================

# ========================================== Magic component parser functions ==========================================


def get_component_bounding_box_for_aal_misc_lib(self, text_line: str, component):
    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.bounding_box.set([int(val) // self.scale_factor for val in text_line_words[2:6]])
        self.found_bounding_box = True


def magic_component_parsing_for_aal_misc_lib(self, layout_file_path: str, component):
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_bounding_box_for_aal_misc_lib(text_line=text_line, component=component, self=self)
    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")


# ========================================= Bipolar PNP trace generation functions =====================================
def generate_local_traces_for_aal_misc_lib_pnp_bipolars(self):
    aal_misc_pnp_transistor_components = []

    for component in self.components:
        if (isinstance(component, Transistor) and re.search(r'AAL_MISC', component.layout_library)
                and component.type == "pnp"):
            aal_misc_pnp_transistor_components.append(component)

    if not aal_misc_pnp_transistor_components:
        return

    for component in aal_misc_pnp_transistor_components:
        if component.schematic_connections['B'] == component.schematic_connections['C']:
            __local_base_to_collector_connection(self=self, component=component)

    # Make dict of component names based on y-coordinate
    y_grouped_component_names = defaultdict(list)
    for component in aal_misc_pnp_transistor_components:
        y_grouped_component_names[component.transform_matrix.f].append(component.name)
    y_grouped_component_names = dict(y_grouped_component_names)

    # Get components connecting collector to rail
    components_with_collector_to_rail_connection = []
    for component in aal_misc_pnp_transistor_components:
        if (re.search(r".*VDD.*", component.schematic_connections['C'], re.IGNORECASE) or
                re.search(r".*VSS.*", component.schematic_connections['C'], re.IGNORECASE)):
            components_with_collector_to_rail_connection.append(component)

    # Make groups of components that have their collectors connected to a rail and have the same y-coordinate
    y_group_components = defaultdict(list)
    for _, group in y_grouped_component_names.items():
        for comp_name in group:
            for component in components_with_collector_to_rail_connection:
                if component.name == comp_name:
                    group_name = "_".join(map(str, group))
                    y_group_components[group_name].append(component)

    # Iterate over y-grouped components and check for match against collectors to rail components.
    # On component hit against a group discard all other components within group. This solution removes redundant rail
    # traces for each component with the same y-coordinates.
    for _, group in y_grouped_component_names.items():
        found_comp = False
        for comp_name in group:
            for component in components_with_collector_to_rail_connection:
                if component.name == comp_name and not found_comp:
                    found_comp = True
                    group_name = "_".join(map(str, group))
                    __local_collector_to_rail_connection(
                        self=self, component=component,
                        rail=component.schematic_connections['C'],
                        group_name=group_name,
                        group_components=y_group_components[group_name]
                    )


def __local_base_to_collector_connection(self, component):
    trace = TraceNet(name=f"{component.name}_B_C", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.named_parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    collector_x1 = next((port.area.x1 for port in component.layout_ports if port.type == 'C'))
    collector_x2 = next((port.area.x2 for port in component.layout_ports if port.type == 'C'))
    collector_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'C'))
    base_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'B'))

    trace.segments = [RectAreaLayer(layer=self.METAL_LAYERS[0], area=RectArea(
        x1=collector_x1 + component.transform_matrix.c,
        y1=base_y2 + component.transform_matrix.f,
        x2=collector_x2 + component.transform_matrix.c,
        y2=collector_y1 + component.transform_matrix.f))]
    self.components.append(trace)


def __local_collector_to_rail_connection(self, component, rail: str, group_name: str, group_components: list):
    y_params = {
        'rail_bot': (component.bounding_box.y1, 0, 1),
        'rail_top': (component.bounding_box.y2, 1, 0)
    }
    generate_collector_to_rail_connection(self=self, rail=rail, component=component, y_params=y_params['rail_top'],
                                          group_endpoint="RAIL_TOP", group_name=group_name,
                                          group_components=group_components)

    generate_collector_to_rail_connection(self=self, rail=rail, component=component, y_params=y_params['rail_bot'],
                                          group_endpoint="RAIL_BOT", group_name=group_name,
                                          group_components=group_components)


def generate_collector_to_rail_connection(self, rail: str, component, y_params: tuple,
                                          group_endpoint: str, group_name: str, group_components: list):

    trace = TraceNet(name=f"{group_name}_C_{rail}_{group_endpoint}", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.named_parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    collector_y1 = next((port.area.y1 for port in component.layout_ports if port.type == 'C'))
    collector_y2 = next((port.area.y2 for port in component.layout_ports if port.type == 'C'))
    collector_width = abs(collector_y2 - collector_y1)

    for structural_component in self.structural_components:
        if re.search(rf"\b{rail}\b", structural_component.name, re.IGNORECASE):
            __create_port_to_rail_connection_based_on_component_placement_order(
                self=self,
                pin=structural_component,
                y_params=y_params,
                component=component,
                connection_width=collector_width,
                group_components=group_components,
                trace=trace,
                component_type="B"
            )
            __add_connections_for_middle_placed_components(self=self, pin=structural_component,
                                                           group_components=group_components, trace=trace,
                                                           component_type="B")
    self.components.append(trace)


# ======================================== MiM capacitor trace generation functions ====================================
def generate_local_traces_for_aal_misc_lib_mim_capacitors(self):
    aal_misc_mim_capacitor_components = []

    for component in self.components:
        if (isinstance(component, Capacitor) and re.search(r'AAL_MISC', component.layout_library)
                and component.type == "mim"):
            aal_misc_mim_capacitor_components.append(component)

    if not aal_misc_mim_capacitor_components:
        return

    # Make dict of component names based on y-coordinate
    y_grouped_component_names = defaultdict(list)
    for component in aal_misc_mim_capacitor_components:
        y_grouped_component_names[component.transform_matrix.f].append(component.name)
    y_grouped_component_names = dict(y_grouped_component_names)

    # Get components connecting port A to rail
    components_with_a_to_rail_connection = []
    for component in aal_misc_mim_capacitor_components:
        if (re.search(r".*VDD.*", component.schematic_connections['A'], re.IGNORECASE) or
                re.search(r".*VSS.*", component.schematic_connections['A'], re.IGNORECASE)):
            components_with_a_to_rail_connection.append(component)

    # Get components connecting port B to rail
    components_with_b_to_rail_connection = []
    for component in aal_misc_mim_capacitor_components:
        if (re.search(r".*VDD.*", component.schematic_connections['B'], re.IGNORECASE) or
                re.search(r".*VSS.*", component.schematic_connections['B'], re.IGNORECASE)):
            components_with_b_to_rail_connection.append(component)

    # Make groups of components that have their A ports connected to a rail and have the same y-coordinate
    port_a_group_y_components = defaultdict(list)
    for _, group in y_grouped_component_names.items():
        for comp_name in group:
            for component in components_with_a_to_rail_connection:
                if component.name == comp_name:
                    group_name = "_".join(map(str, group))
                    port_a_group_y_components[group_name].append(component)

    # Iterate over y-grouped components and check for match against A to rail components.
    # On component hit against a group discard all other components within group. This solution removes redundant rail
    # traces for each component with the same y-coordinates.
    for _, group in y_grouped_component_names.items():
        found_comp = False
        for comp_name in group:
            for component in components_with_a_to_rail_connection:
                if component.name == comp_name and not found_comp:
                    found_comp = True
                    group_name = "_".join(map(str, group))
                    __local_a_to_rail_connection(
                        self=self, component=component,
                        rail=component.schematic_connections['A'],
                        group_name=group_name,
                        group_components=port_a_group_y_components[group_name]
                    )

    # Make groups of components that have their B ports connected to a rail and have the same y-coordinate
    port_b_group_y_components = defaultdict(list)
    for _, group in y_grouped_component_names.items():
        for comp_name in group:
            for component in components_with_b_to_rail_connection:
                if component.name == comp_name:
                    group_name = "_".join(map(str, group))
                    port_b_group_y_components[group_name].append(component)

    # Iterate over y-grouped components and check for match against B to rail components.
    # On component hit against a group discard all other components within group. This solution removes redundant rail
    # traces for each component with the same y-coordinates.
    for _, group in y_grouped_component_names.items():
        found_comp = False
        for comp_name in group:
            for component in components_with_b_to_rail_connection:
                if component.name == comp_name and not found_comp:
                    found_comp = True
                    group_name = "_".join(map(str, group))
                    __local_b_to_rail_connection(
                        self=self, component=component,
                        rail=component.schematic_connections['B'],
                        group_name=group_name,
                        group_components=port_b_group_y_components[group_name]
                    )


def __local_a_to_rail_connection(self, component, rail: str, group_name: str, group_components: list):
    y_params = {
        'rail_bot': (next((port.area.y1 for port in component.layout_ports if port.type == 'A')), 0, 1),
        'rail_top': (next((port.area.y2 for port in component.layout_ports if port.type == 'A')), 1, 0)
    }
    if re.search(r".*VDD.*", rail, re.IGNORECASE):
        __generate_capacitor_port_to_rail_connection(
            self=self,
            rail=rail,
            component=component,
            y_params=y_params['rail_top'],
            group_endpoint="RAIL_TOP",
            group_name=group_name,
            group_components=group_components,
            port_name="A",
            component_type="C",
            width_factor=20
        )
    else:
        __generate_capacitor_port_to_rail_connection(
            self=self,
            rail=rail,
            component=component,
            y_params=y_params['rail_bot'],
            group_endpoint="RAIL_BOT",
            group_name=group_name,
            group_components=group_components,
            port_name="A",
            component_type="C",
            width_factor=20
        )


def __local_b_to_rail_connection(self, component, rail: str, group_name: str, group_components: list):
    y_params = {
        'rail_bot': (next((port.area.y1 for port in component.layout_ports if port.type == 'B')), 0, 1),
        'rail_top': (next((port.area.y2 for port in component.layout_ports if port.type == 'B')), 1, 0)
    }
    if re.search(r".*VDD.*", rail, re.IGNORECASE):
        __generate_capacitor_port_to_rail_connection(
            self=self,
            rail=rail,
            component=component,
            y_params=y_params['rail_top'],
            group_endpoint="RAIL_TOP",
            group_name=group_name,
            group_components=group_components,
            port_name="B",
            component_type="C",
            width_factor=4
        )
    else:
        __generate_capacitor_port_to_rail_connection(
            self=self,
            rail=rail,
            component=component,
            y_params=y_params['rail_bot'],
            group_endpoint="RAIL_BOT",
            group_name=group_name,
            group_components=group_components,
            port_name="B",
            component_type="C",
            width_factor=4
        )


def __generate_capacitor_port_to_rail_connection(
        self, rail: str, component, y_params: tuple, group_endpoint: str, group_name: str, group_components: list,
        port_name: str, component_type: str, width_factor: int):

    trace = TraceNet(name=f"{group_name}_{port_name}_{rail}_{group_endpoint}", named_cell=component.named_cell)
    trace.instance = trace.__class__.__name__
    trace.cell = self.circuit_cell.cell
    trace.parent_cell = self.circuit_cell.parent_cell
    trace.named_parent_cell = self.circuit_cell.parent_cell
    trace.cell_chain = self.circuit_cell.cell_chain

    y1 = next((port.area.y1 for port in component.layout_ports if port.type == port_name))
    y2 = next((port.area.y2 for port in component.layout_ports if port.type == port_name))
    width = abs(y2 - y1) // width_factor

    for structural_component in self.structural_components:
        if re.search(rf"\b{rail}\b", structural_component.name, re.IGNORECASE):

            for comp in group_components:
                print(comp.transform_matrix.f, port_name)
                via_connect_x1 = next((port.area.x1 for port in comp.layout_ports if port.type == port_name))
                via_connect_x2 = next((port.area.x2 for port in comp.layout_ports if port.type == port_name))
                via_connect = RectArea(x1=via_connect_x1 + comp.transform_matrix.c,
                                       y1=y_params[0] + comp.transform_matrix.f - width * y_params[1],
                                       x2=via_connect_x2 + comp.transform_matrix.c,
                                       y2=y_params[0] + comp.transform_matrix.f + width * y_params[2])
                trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[3]}', area=via_connect))

            __create_port_to_rail_connection_based_on_component_placement_order(
                self=self,
                pin=structural_component,
                y_params=y_params,
                component=component,
                connection_width=width,
                group_components=group_components,
                trace=trace,
                component_type=component_type,
            )
            __add_connections_for_middle_placed_components(
                self=self,
                pin=structural_component,
                group_components=group_components, trace=trace,
                component_type=component_type)
    self.components.append(trace)

# ========================================== General trace generation functions ========================================


def __create_port_to_rail_connection_based_on_component_placement_order(
        self, pin: Pin, y_params: tuple, component: Transistor | Capacitor | Resistor, connection_width: int,
        group_components: list, trace: TraceNet, component_type: str):

    total_length = sum((comp.bounding_box.x2 - comp.bounding_box.x1) for comp in group_components)
    smallest_x_component = min(group_components, key=lambda comp: comp.transform_matrix.c)

    if self.RELATIVE_COMPONENT_PLACEMENT == "V" or len(self.functional_component_order) == 1:
        x1 = pin.layout.area.x1
        x2 = pin.layout.area.x2

        segment = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                           x2=x2, y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

        via_left = RectArea(x1=x1, y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                            x2=x1 + self.RAIL_RING_WIDTH,
                            y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

        via_right = RectArea(x1=x2 - self.RAIL_RING_WIDTH,
                             y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                             x2=x2, y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

        trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_left))
        trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_right))
        trace.segments.append(RectAreaLayer(layer=self.METAL_LAYERS[0], area=segment))

    elif self.RELATIVE_COMPONENT_PLACEMENT == "H":

        if self.functional_component_order[0] == component_type:
            x1 = pin.layout.area.x1
            x2 = total_length

            segment = RectArea(x1=x1,
                               y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                               x2=x2,
                               y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

            via_left = RectArea(x1=x1,
                                y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                                x2=x1 + self.RAIL_RING_WIDTH,
                                y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])
            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_left))
            trace.segments.append(RectAreaLayer(layer=self.METAL_LAYERS[0], area=segment))

        elif self.functional_component_order[-1] == component_type:
            x1 = pin.layout.area.x2 - total_length + pin.layout.area.x1
            x2 = pin.layout.area.x2

            segment = RectArea(x1=x1,
                               y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                               x2=x2,
                               y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

            via_right = RectArea(x1=x2 - self.RAIL_RING_WIDTH,
                                 y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                                 x2=x2,
                                 y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])
            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYER[0]}-{self.METAL_LAYER[1]}', area=via_right))
            trace.segments.append(RectAreaLayer(layer=self.METAL_LAYER[0], area=segment))

        elif (self.functional_component_order[1] == component_type and len(self.functional_component_order) > 2
              or self.functional_component_order[2] == component_type and len(self.functional_component_order) > 3):
            x1 = smallest_x_component.transform_matrix.c + pin.layout.area.x1
            x2 = smallest_x_component.transform_matrix.c + total_length - pin.layout.area.x1

            segment = RectArea(x1=x1,
                               y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                               x2=x2,
                               y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

            via_left = RectArea(x1=x1,
                                y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                                x2=x1 + self.RAIL_RING_WIDTH,
                                y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

            via_right = RectArea(x1=x2 - self.RAIL_RING_WIDTH,
                                 y1=y_params[0] + component.transform_matrix.f - connection_width * y_params[1],
                                 x2=x2,
                                 y2=y_params[0] + component.transform_matrix.f + connection_width * y_params[2])

            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_left))
            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_right))
            trace.segments.append(RectAreaLayer(layer=self.METAL_LAYERS[0], area=segment))


def __add_connections_for_middle_placed_components(self, pin: Pin, group_components: list, trace: TraceNet,
                                                   component_type: str):

    if self.RELATIVE_COMPONENT_PLACEMENT == "H" and len(self.functional_component_order) > 2:

        if (self.functional_component_order[1] == component_type and len(self.functional_component_order) > 2
                or self.functional_component_order[2] == component_type and len(
                    self.functional_component_order) > 3):
            current_rail_bottom_segment = RectAreaLayer()
            smallest_x_cord_comp = min(group_components, key=lambda component: component.transform_matrix.c)
            total_length = sum(
                (component.bounding_box.x2 - component.bounding_box.x1) for component in group_components)

            # Get bottom segment of current rail
            for component in self.components:
                if isinstance(component, TraceNet) and component.cell_chain == pin.cell_chain:
                    if (re.search(r"^(?!.*(?:TOP|BOT)).*VDD.*$", component.name, re.IGNORECASE) and
                        re.search(r"^(?!.*(?:TOP|BOT)).*VDD.*$", pin.name, re.IGNORECASE)) or (
                            re.search(r"^(?!.*(?:TOP|BOT)).*VSS.*$", component.name, re.IGNORECASE) and
                            re.search(r"^(?!.*(?:TOP|BOT)).*VSS.*$", pin.name, re.IGNORECASE)):
                        current_rail_bottom_segment = min(component.segments, key=lambda s: (s.area.y1, s.area.y2))

            segment_left = RectArea(x1=smallest_x_cord_comp.transform_matrix.c + pin.layout.area.x1,
                                    y1=current_rail_bottom_segment.area.y1,
                                    x2=smallest_x_cord_comp.transform_matrix.c + pin.layout.area.x1
                                    + self.RAIL_RING_WIDTH,
                                    y2=pin.layout.area.y2)

            segment_right = RectArea(x1=smallest_x_cord_comp.transform_matrix.c - pin.layout.area.x1
                                     + total_length - self.RAIL_RING_WIDTH,
                                     y1=current_rail_bottom_segment.area.y1,
                                     x2=smallest_x_cord_comp.transform_matrix.c - pin.layout.area.x1
                                     + total_length,
                                     y2=pin.layout.area.y2)

            via_right_top = RectArea(x1=smallest_x_cord_comp.transform_matrix.c + pin.layout.area.x1,
                                     y1=current_rail_bottom_segment.area.y1,
                                     x2=smallest_x_cord_comp.transform_matrix.c + pin.layout.area.x1
                                     + self.RAIL_RING_WIDTH,
                                     y2=current_rail_bottom_segment.area.y1 + self.RAIL_RING_WIDTH)

            via_right_bot = RectArea(x1=smallest_x_cord_comp.transform_matrix.c + pin.layout.area.x1,
                                     y1=pin.layout.area.y2 - self.RAIL_RING_WIDTH,
                                     x2=smallest_x_cord_comp.transform_matrix.c + pin.layout.area.x1
                                     + self.RAIL_RING_WIDTH,
                                     y2=pin.layout.area.y2)

            via_left_top = RectArea(x1=smallest_x_cord_comp.transform_matrix.c - pin.layout.area.x1
                                    + total_length - self.RAIL_RING_WIDTH,
                                    y1=current_rail_bottom_segment.area.y1,
                                    x2=smallest_x_cord_comp.transform_matrix.c - pin.layout.area.x1
                                    + total_length,
                                    y2=current_rail_bottom_segment.area.y1 + self.RAIL_RING_WIDTH)

            via_left_bot = RectArea(x1=smallest_x_cord_comp.transform_matrix.c - pin.layout.area.x1
                                    + total_length - self.RAIL_RING_WIDTH,
                                    y1=pin.layout.area.y2 - self.RAIL_RING_WIDTH,
                                    x2=smallest_x_cord_comp.transform_matrix.c - pin.layout.area.x1
                                    + total_length,
                                    y2=pin.layout.area.y2)

            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_left_top))
            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_left_bot))
            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_right_top))
            trace.vias.append(RectAreaLayer(layer=f'{self.METAL_LAYERS[0]}-{self.METAL_LAYERS[1]}', area=via_right_bot))
            trace.segments.append(RectAreaLayer(layer=self.METAL_LAYERS[1], area=segment_left))
            trace.segments.append(RectAreaLayer(layer=self.METAL_LAYERS[1], area=segment_right))
