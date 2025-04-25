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

# ===================================================== Libraries ======================================================
import os
import re
import copy
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from itertools import groupby
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict
import copy

from astar.a_star_initiator import AstarInitiator
from connections.connections import ConnectionLists
from grid.generate_grid import GridGeneration
from linear_optimization.initiator_lp import LPInitiator
from linear_optimization.linear_optimization import LinearOptimizationSolver
from logger.logger import get_a_logger
from circuit.circuit_components import (RectArea, RectAreaLayer, Transistor, Capacitor, Resistor, Pin, CircuitCell,
                                        TraceNet, RectAreaLayer, DigitalBlock)
from traces.generate_astar_path_traces import GenerateAstarPathTraces
from traces.generate_rail_traces import GenerateRailTraces
from astar.a_star import AstarAlgorithm
from libraries.library_handling import LibraryHandling


# =================================================== Cell Creator =====================================================

class CellCreator:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties, components):
        self.project_directory = project_properties.directory
        self.project_properties = project_properties
        self.component_libraries = project_properties.component_libraries
        self.components = components

        self.top_cell = CircuitCell
        self.updated_components = []
        self.origin_scaled_cell_offsets = list()
        self.FUNCTIONAL_TYPES = (Transistor, Resistor, Capacitor)

        self.__create_cells()
        self.__set_cells_positions()
        self.__add_top_cell_rails_around_cells()
        #self.__add_top_cell_rail_to_rail_connections()

    def __use_earlier_solution_for_cell(self, cell, solved_circuit_cells,
                                        components_grouped_by_circuit_cell, grouped_components):
        for new_component in components_grouped_by_circuit_cell[grouped_components]:

            # Circuit cell
            if isinstance(new_component, CircuitCell):
                for solved_component in solved_circuit_cells[cell]:
                    if isinstance(solved_component, CircuitCell):
                        new_component.bounding_box = solved_component.bounding_box

            # Transistors
            if isinstance(new_component, (Transistor, Resistor, Capacitor)):
                for solved_component in solved_circuit_cells[cell]:
                    if (isinstance(solved_component, (Transistor, Resistor, Capacitor)) and
                            new_component.name == solved_component.name):
                        new_component.transform_matrix = solved_component.transform_matrix
                        if (isinstance(solved_component, Transistor) and
                                (solved_component.type == "nmos" or solved_component.type == "pmos")):
                            new_component.group_endpoint = solved_component.group_endpoint

            # Pins
            if isinstance(new_component, Pin):
                for solved_component in solved_circuit_cells[cell]:
                    if isinstance(solved_component, Pin) and new_component.name == solved_component.name:
                        new_component.layout = solved_component.layout

        # Trace nets
        for solved_component in copy.deepcopy(solved_circuit_cells[cell]):
            if isinstance(solved_component, TraceNet):
                solved_component.cell_chain = grouped_components
                solved_component.named_cell = re.search(r'--([^-]+)$', grouped_components).group(1)
                components_grouped_by_circuit_cell[grouped_components].append(solved_component)

        # Append everything for this cell to the list of updated components
        for solved_component in components_grouped_by_circuit_cell[grouped_components]:
            self.updated_components.append(solved_component)

    def __create_cells(self):
        components_grouped_by_circuit_cell = defaultdict(list)
        circuit_cells = list()
        solved_circuit_cells = defaultdict(list)

        for component in self.components:
            if isinstance(component, CircuitCell):
                circuit_cells.append(component)
            else:
                components_grouped_by_circuit_cell[component.cell_chain].append(component)

        for circuit_cell in circuit_cells:
            for grouped_components in components_grouped_by_circuit_cell:
                print(grouped_components)
                if (re.search(r"^(?:.*--)?(.*)$", grouped_components).group(1)
                        == f"{circuit_cell.name}_{circuit_cell.cell}"):
                    print(f"{circuit_cell.name}_{circuit_cell.cell}")
                    components_grouped_by_circuit_cell[grouped_components].append(circuit_cell)

        # Cell creation process
        for cell_nr, grouped_components in enumerate(components_grouped_by_circuit_cell):
            """With every iteration there is a set of components along with their associated circuit cell"""

            # Step 1: Check if current circuit cell already has been solved
            cell = components_grouped_by_circuit_cell[grouped_components][0].cell

            if cell in solved_circuit_cells.keys():
                self.logger.info(f"Using previously found solution for cell '{cell}' "
                                 f"with respect to cell chain '{grouped_components}'")
                self.__use_earlier_solution_for_cell(
                    cell=cell,
                    solved_circuit_cells=solved_circuit_cells,
                    components_grouped_by_circuit_cell=components_grouped_by_circuit_cell,
                    grouped_components=grouped_components
                )
                continue

            # Step 2: Perform placement of functional components
            connections, overlap_dict, net_list = ConnectionLists(
                input_components=components_grouped_by_circuit_cell[grouped_components]).get()

            components = components_grouped_by_circuit_cell[grouped_components]
            if any(isinstance(c, self.FUNCTIONAL_TYPES) for c
                   in components_grouped_by_circuit_cell[grouped_components]):
                components = LPInitiator(components, connections, overlap_dict).initiate_linear_optimization()

            # Step 3: Move all components to the origin
            origin_scaled_used_area = RectArea()
            used_area = RectArea()
            if any(isinstance(c, self.FUNCTIONAL_TYPES) for c
                   in components_grouped_by_circuit_cell[grouped_components]):
                _, _, used_area, _, _, _ = GridGeneration(components=components).initialize_grid_generation()
                origin_scaled_used_area = RectArea(x1=0, y1=0, x2=abs(used_area.x2 - used_area.x1),
                                                   y2=abs(used_area.y2 - used_area.y1))
            for component in components:
                if isinstance(component, CircuitCell):
                    component.bounding_box = origin_scaled_used_area
                elif isinstance(component, self.FUNCTIONAL_TYPES):
                    component.transform_matrix.c -= used_area.x1
                    component.transform_matrix.f -= used_area.y1

            # Step 4: Grid generation
            grid, scaled_port_coordinates, used_area, port_coordinates, routing_parameters, component_ports \
                = GridGeneration(components=components).initialize_grid_generation()

            # Step 5: A star path routing between component ports
            # paths, grid_vertical, grid_horizontal = (
            #     AstarInitiator(grid=grid,
            #                    connections=connections,
            #                    components=components,
            #                    scaled_port_coordinates=scaled_port_coordinates,
            #                    port_coordinates=port_coordinates,
            #                    net_list=net_list,
            #                    routing_parameters=routing_parameters,
            #                    component_ports=component_ports
            #                    ).get())

            # Step 6: Trace generation
            # components = GenerateAstarPathTraces(components=components, paths=[], net_list=net_list,
            #                                      used_area=origin_scaled_used_area).get()
            components = GenerateRailTraces(project_properties=self.project_properties, components=components).get()

            # Step 7: Handle specifics for components of different libraries
            components = LibraryHandling(project_properties=self.project_properties, components=components).get()

            # Step 8: Move all components to the origin based on the updated cell bounding box from rail generation
            components = self.__move_all_components_to_origin_based_on_rail_offsets(components=components)

            print("================================================================")
            # Step 9: Create an update list of components
            for component in components:
                self.updated_components.append(component)
                solved_circuit_cells[cell].append(component)
            components.clear()

    def __move_all_components_to_origin_based_on_rail_offsets(self, components):
        rails_offset_x = 0
        rails_offset_y = 0
        zero_segment_trace_net_names = list()

        for component in components:
            if isinstance(component, CircuitCell):
                rails_offset_x = abs(component.bounding_box.x1)
                rails_offset_y = abs(component.bounding_box.y1)
                component.bounding_box = RectArea(x1=0, x2=abs(component.bounding_box.x2 - component.bounding_box.x1),
                                                  y1=0, y2=abs(component.bounding_box.y2 - component.bounding_box.y1))
        for component in components:
            if isinstance(component, self.FUNCTIONAL_TYPES):
                component.transform_matrix.c += rails_offset_x
                component.transform_matrix.f += rails_offset_y

            elif isinstance(component, TraceNet):
                if len(component.segments) == 0:
                    zero_segment_trace_net_names.append(component.name)
                else:
                    for segment in component.segments:
                        segment.area.x1 += rails_offset_x
                        segment.area.y1 += rails_offset_y
                        segment.area.x2 += rails_offset_x
                        segment.area.y2 += rails_offset_y

                for via in component.vias:
                    via.area.x1 += rails_offset_x
                    via.area.y1 += rails_offset_y
                    via.area.x2 += rails_offset_x
                    via.area.y2 += rails_offset_y

        for component in components:
            if isinstance(component, Pin):
                if component.name in zero_segment_trace_net_names:
                    component.layout.area.x1 += rails_offset_x
                    component.layout.area.y1 += rails_offset_y
                    component.layout.area.x2 += rails_offset_x
                    component.layout.area.y2 += rails_offset_y

        return components

    def __set_cells_positions(self):
        prev_cell_chain_depth = 0
        offset_from_deepening_cells = 0
        offset_from_deepening_cells_sum = 0
        offset_from_non_deepening_cells = 0
        cell_nr = 0
        # Add support for y change in placement and packing
        depth_offset_map = {}
        for component in self.updated_components:
            if isinstance(component, CircuitCell):

                current_chain_depth = len(re.findall(r"--", component.cell_chain))
                current_width = component.bounding_box.x2 - component.bounding_box.x1

                if current_chain_depth not in depth_offset_map:
                    if current_chain_depth == 0:
                        depth_offset_map[0] = 0
                    else:
                        # Deeper levels start where parent level is currently
                        parent_depth = current_chain_depth - 1
                        depth_offset_map[current_chain_depth] = depth_offset_map.get(parent_depth, 0)

                current_offset = depth_offset_map[current_chain_depth]
                print(current_offset, component.cell_chain)

                component.transform_matrix.set([1, 0, current_offset, 0, 1, 0])
                depth_offset_map[current_chain_depth] += current_width

    def __add_top_cell_rails_around_cells(self):

        top_cell_rails = list()
        all_cell_rails = list()
        top_cell_components = list()

        for component in self.updated_components:
            if isinstance(component, Pin) and (re.search(r".*VDD.*", component.name, re.IGNORECASE)
                                               or re.search(r".*VSS.*", component.name, re.IGNORECASE)):
                all_cell_rails.append(copy.deepcopy(component))

                if component.parent_cell == "TOP_CELL":
                    top_cell_rails.append(copy.deepcopy(component))

                # Check if this component is already in rails
                # if not any(rail.name == component.name for rail in top_cell_rails):
                #    top_cell_rails.append(copy.deepcopy(component))

        top_cell_x2 = 0
        for component in self.updated_components:
            if isinstance(component, CircuitCell):
                top_cell_x2 += (component.bounding_box.x2 - component.bounding_box.x1)

        # top_cell_rails_exists = all(c.layout for c in all_cell_rails)
        top_cell_y2 = max(component.layout.area.y2 for component in all_cell_rails if component.layout)

        # Create a top cell with bounding box covering all cells but with all other attributes of UTOP
        for component in self.updated_components:
            if isinstance(component, CircuitCell) and component.name == 'UTOP':
                self.top_cell = CircuitCell(name="TOP_CELL",
                                            number_id=0,
                                            instance=component.instance,
                                            cell=component.cell,
                                            named_cell=component.named_cell,
                                            parent_cell=component.parent_cell,
                                            cell_chain=component.cell_chain,
                                            bounding_box=RectArea(x1=0, y1=0, x2=top_cell_x2, y2=top_cell_y2))
                # if not top_cell_rails_exists:
                for nr, rail in enumerate(top_cell_rails):
                    rail.cell = component.cell
                    rail.number_id = len(self.updated_components) + nr
                    rail.named_cell = component.named_cell
                    rail.parent_cell = component.parent_cell
                    rail.cell_chain = component.cell_chain
                    rail.layout = RectAreaLayer()
                    top_cell_components.append(rail)

        top_cell_components.append(self.top_cell)

        components = GenerateRailTraces(self.project_properties, top_cell_components).get()
        for component in components:
            # Don't include the temporary top cell since it is not real, but was needed for top cell trace generation
            if not isinstance(component, CircuitCell):
                self.updated_components.append(component)

        # Adding of VDD/VSS connection between circuit cells

        # Step 1:
        # for top_cell_rail in top_cell_rails:
        #     for rail in all_cell_rails:
        #         for component in self.updated_components:
        #             if isinstance(component, CircuitCell) and component.cell_chain == rail.cell_chain:
        #
        #                 if top_cell_rail.name == rail.name:
        #                     trace = TraceNet(name=f"{rail.name}_CONNECTION", cell=component.cell,
        #                     named_cell=component.named_cell)
        #                     trace.instance = trace.__class__.__name__
        #                     trace.parent_cell = component.parent_cell
        #                     trace.cell_chain = component.cell_chain
        #                     print(self.top_cell.bounding_box.y2)
        #                     print(top_cell_rail.layout.area.y2)
        #                     top_cell_rail_y1 = -(top_cell_rail.layout.area.y2 - self.top_cell.bounding_box.y2)
        #
        #                     segment1 = RectArea(x1=rail.layout.area.x1,
        #                                        y1=top_cell_rail_y1,
        #                                        x2=rail.layout.area.x1 + 50,
        #                                        y2=top_cell_rail.layout.area.y2)
        #
        #                     segment2 = RectArea(x1=rail.layout.area.x2 - 50,
        #                                        y1=top_cell_rail_y1,
        #                                        x2=rail.layout.area.x2,
        #                                        y2=top_cell_rail.layout.area.y2)
        #
        #                     # segment3 = RectArea(x1=rail.layout.area.x1 - 50,
        #                     #                     y1=top_cell_rail.layout.area.y1,
        #                     #                     x2=rail.layout.area.x2 + 50,
        #                     #                     y2=top_cell_rail.layout.area.y2)
        #                     #top_via = RectArea(x1=segment1.x1, y1=segment1.y2, x2=left_segment.x2, y2=top_segment.y2)
        #
        #                     trace.segments = [RectAreaLayer(layer="m1", area=segment1),
        #                                       RectAreaLayer(layer="m1", area=segment2)]
        #
        #                     self.updated_components.append(trace)
        #

        components_grouped_by_circuit_cell = defaultdict(list)
        components_grouped_by_circuit_cell_with_children_cells_and_pins = defaultdict(list)
        circuit_cells = list()

        for component in self.updated_components:
            if isinstance(component, CircuitCell):
                circuit_cells.append(component)
            else:
                components_grouped_by_circuit_cell[component.cell_chain].append(component)

        for circuit_cell in circuit_cells:
            for grouped_components in components_grouped_by_circuit_cell:
                if (re.search(r"^(?:.*--)?(.*)$", grouped_components).group(1)
                        == f"{circuit_cell.name}_{circuit_cell.cell}"):
                    components_grouped_by_circuit_cell[grouped_components].append(circuit_cell)

        # For every set of grouped components append children cells and their pins
        for cell_nr, grouped_components in enumerate(components_grouped_by_circuit_cell):
            for component in components_grouped_by_circuit_cell[grouped_components]:
                (components_grouped_by_circuit_cell_with_children_cells_and_pins[grouped_components]
                 .append(copy.deepcopy(component)))
                if isinstance(component, CircuitCell):

                    for circuit_cell in circuit_cells:
                        if circuit_cell.parent_cell == component.cell:
                            (components_grouped_by_circuit_cell_with_children_cells_and_pins[grouped_components]
                             .append(copy.deepcopy(circuit_cell)))

                            for comp in self.updated_components:
                                if isinstance(comp, Pin):
                                    if comp.cell_chain == circuit_cell.cell_chain:
                                        (components_grouped_by_circuit_cell_with_children_cells_and_pins
                                         [grouped_components]
                                         .append(copy.deepcopy(comp)))

        cell_to_cell_connections = list()

        for cell_nr, grouped_components in enumerate(components_grouped_by_circuit_cell_with_children_cells_and_pins):

            print("===================")
            for component in components_grouped_by_circuit_cell_with_children_cells_and_pins[grouped_components]:

                if isinstance(component, CircuitCell):
                    if component.cell_chain != grouped_components:
                        cell_to_cell_connection = list()

                        for inside_connection, outside_connection in component.schematic_connections.items():
                            for comp in components_grouped_by_circuit_cell_with_children_cells_and_pins[grouped_components]:
                                if isinstance(comp, Pin):

                                    if comp.cell_chain != grouped_components:
                                        if outside_connection == comp.name and comp.layout:
                                            # Valid pins that are connected to something and have layout
                                            cell_to_cell_connection.append(comp)
                                            print(f"others: {comp.name, comp.layout}")
                                            for c in components_grouped_by_circuit_cell_with_children_cells_and_pins[
                                                grouped_components]:
                                                if isinstance(c, Pin):
                                                    if c.cell_chain == grouped_components:
                                                        if inside_connection == c.name and c.layout:
                                                            # Valid pins that are connected to something and have layout
                                                            cell_to_cell_connection.append(c)
                                                            print(f"others: {c.name, c.layout}")
                        cell_to_cell_connections.append(cell_to_cell_connection)

        # Update vertical and horizontal grids to include both cells that are being routed between
        # unfinished stuff here
        # for connection in cell_to_cell_connections:
        #     p1 = (((connection[0].layout.area.x2 - connection[0].layout.area.x1) // 2
        #            + connection[0].layout.area.x1) // 16,
        #           ((connection[0].layout.area.y2 - connection[0].layout.area.y1) // 2
        #            + connection[0].layout.area.y1) // 16)
        #
        #     p2 = (((connection[1].layout.area.x2 - connection[1].layout.area.x1) // 2
        #            + connection[0].layout.area.x1) // 16,
        #           ((connection[1].layout.area.y2 - connection[1].layout.area.y1) // 2
        #            + connection[0].layout.area.y1) // 16)
        #
        #     print(p1, p2)

            # grid, scaled_port_coordinates, used_area, port_coordinates, routing_parameters, component_ports \
            #     = GridGeneration(components=self.updated_components).initialize_grid_generation()
            #
            # path, length = (AstarAlgorithm(copy.deepcopy(grid), copy.deepcopy(grid), p1, [p2],
            #                                routing_parameters.minimum_segment_length).a_star())
            # print(path)
            # self.updated_components = TraceGenerator(project_properties=self.project_properties,
            #                                          components=self.updated_components,
            #                                          paths=path,
            #                                          net_list=None,
            #                                          used_area=used_area
            #                                          ).get()

            # functional_components = list()
            # for component in self.updated_components:
            #     if isinstance(component, (Transistor, Capacitor, Resistor)):
            #         functional_components.append(component)
            #

            # print(cell_to_cell_connections, path, length)

        print("===================")
        # print(grouped_components)
        # for cell_nr_1, grouped_components_1 in enumerate(components_grouped_by_circuit_cell):
        #     for component_1 in components_grouped_by_circuit_cell[grouped_components_1]:
        #         if isinstance(component_1, CircuitCell):

    def __add_top_cell_rail_to_rail_connections(self):
        pass

    def get(self):
        return self.updated_components
