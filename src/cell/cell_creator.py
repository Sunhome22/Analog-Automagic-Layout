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
from linear_optimization.linear_optimization import LinearOptimizationSolver
from logger.logger import get_a_logger
from circuit.circuit_components import (RectArea, RectAreaLayer, Transistor, Capacitor, Resistor, Pin, CircuitCell,
                                        TraceNet, RectAreaLayer, DigitalBlock)
from traces.trace_generator import TraceGenerator


# =================================================== Cell Creator =====================================================

class CellCreator:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties, components):
        self.project_directory = project_properties.directory
        self.project_properties = project_properties
        self.component_libraries = project_properties.component_libraries
        self.components = components
        self.updated_components = list()
        self.origin_scaled_cell_offsets = list()
        self.FUNCTIONAL_TYPES = (Transistor, Resistor, Capacitor)
        self.top_cell = CircuitCell()

        self.__create_cells()
        self.__add_top_cell_rails_around_cells()
        self.__add_top_cell_rail_to_rail_connections()

    def __use_earlier_solution_for_cell(self, cell_nr, cell, solved_circuit_cells,
                                        components_grouped_by_circuit_cell, grouped_components):

        for new_component in components_grouped_by_circuit_cell[grouped_components]:

            # Circuit cell
            if isinstance(new_component, CircuitCell):
                for solved_component in solved_circuit_cells[cell]:
                    if isinstance(solved_component, CircuitCell):
                        new_component.bounding_box = solved_component.bounding_box
                        component_width = solved_component.bounding_box.x2 - solved_component.bounding_box.x1
                        # Proper placement of cell is yet to be done!!
                        new_component.transform_matrix.set([1, 0, cell_nr * component_width, 0, 1, 0])

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
                solved_component.named_cell = grouped_components
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
                if (re.search(r"^(?:.*--)?(.*)$", grouped_components).group(1)
                        == f"{circuit_cell.name}_{circuit_cell.cell}"):
                    print(re.search(r"^(?:.*--)?(.*)$", grouped_components).group(1))
                    components_grouped_by_circuit_cell[grouped_components].append(circuit_cell)

        # Cell creation process
        for cell_nr, grouped_components in enumerate(components_grouped_by_circuit_cell):
            """With every iteration there is a set of components along with their associated circuit cell"""

            # Step 1: Check if current circuit cell already has been solved
            cell = re.search(r'_(.*)', grouped_components).group(1)
            if cell in solved_circuit_cells.keys():
                self.logger.info(f"Using previously found solution for cell '{cell}' "
                                 f"with respect to cell chain '{grouped_components}'")
                self.__use_earlier_solution_for_cell(
                    cell_nr=cell_nr,
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
            if any(isinstance(c, self.FUNCTIONAL_TYPES) for c in components_grouped_by_circuit_cell[grouped_components]):
                components = LinearOptimizationSolver(components_grouped_by_circuit_cell[grouped_components],
                                                      connections, overlap_dict).solve_placement()

            # Step 3: Move all components to the origin
            origin_scaled_used_area = RectArea()
            used_area = RectArea()
            if any(isinstance(c, self.FUNCTIONAL_TYPES) for c in components_grouped_by_circuit_cell[grouped_components]):
                _, _, used_area, _, _ = GridGeneration(components=components).initialize_grid_generation()
                origin_scaled_used_area = RectArea(x1=0, y1=0, x2=abs(used_area.x2 - used_area.x1),
                                                   y2=abs(used_area.y2 - used_area.y1))
            for component in components:
                if isinstance(component, CircuitCell):
                    component.bounding_box = origin_scaled_used_area
                elif isinstance(component, self.FUNCTIONAL_TYPES):
                    component.transform_matrix.c -= used_area.x1
                    component.transform_matrix.f -= used_area.y1

            # Step 4: Find and generate trace paths
            grid, port_scaled_coordinates, _, port_coordinates, routing_parameters = GridGeneration(
                components=components).initialize_grid_generation()

            # paths = AstarInitiator(grid=grid,
            #                       connections=connections,
            #                       components=components,
            #                       port_scaled_coordinates=port_scaled_coordinates,
            #                       port_coordinates=port_coordinates,
            #                       net_list=net_list,
            #                       routing_parameters=routing_parameters
            #                       ).get()
            components = TraceGenerator(project_properties=self.project_properties,
                                        components=components,
                                        paths=[],
                                        net_list=net_list,
                                        used_area=origin_scaled_used_area
                                        ).get()

            # Step 5: Move all components to the origin again since trace generation changed the cell bounding box
            new_x1 = 0
            new_y1 = 0
            for component in components:
                if isinstance(component, CircuitCell):
                    new_x1 = abs(component.bounding_box.x1)
                    new_y1 = abs(component.bounding_box.y1)
                    component.bounding_box = RectArea(x1=0, x2=abs(component.bounding_box.x2 - component.bounding_box.x1),
                                                      y1=0, y2=abs(component.bounding_box.y2 - component.bounding_box.y1))

                if isinstance(component, self.FUNCTIONAL_TYPES):
                    component.transform_matrix.c += new_x1
                    component.transform_matrix.f += new_y1

                elif isinstance(component, TraceNet):
                    for segment in component.segments:
                        segment.area.x1 += new_x1
                        segment.area.y1 += new_y1
                        segment.area.x2 += new_x1
                        segment.area.y2 += new_y1

                    for via in component.vias:
                        via.area.x1 += new_x1
                        via.area.y1 += new_y1
                        via.area.x2 += new_x1
                        via.area.y2 += new_y1

            # Step 6: Create an update list of components
            for component in components:
                self.updated_components.append(component)
                solved_circuit_cells[cell].append(component)
            components.clear()

        self.__set_cells_position()

    def __set_cells_position(self):
        prev_cell_chain_depth = 0
        offset_from_deepening_cells = 0
        cell_nr = 0

        for component in self.updated_components:
            if isinstance(component, CircuitCell):
                self.origin_scaled_cell_offsets.append(component.bounding_box.x2 - component.bounding_box.x1)
                cell_nr += 1
                if len(re.findall(r"--", component.cell_chain)) != prev_cell_chain_depth:
                    prev_cell_chain_depth = len(re.findall(r"--", component.cell_chain))
                    offset_from_deepening_cells = self.origin_scaled_cell_offsets[prev_cell_chain_depth - 1]
                    component.transform_matrix.set([1, 0, offset_from_deepening_cells, 0, 1, 0])
                else:
                    component.transform_matrix.set([1, 0, offset_from_deepening_cells
                                                    + self.origin_scaled_cell_offsets[cell_nr - 1], 0, 1, 0])

    def __add_top_cell_rails_around_cells(self):
        top_cell_rails = list()
        all_cell_rails = list()
        top_cell_components = list()

        for component in self.updated_components:
            if isinstance(component, Pin) and (re.search(r".*VDD.*", component.name, re.IGNORECASE)
                    or re.search(r".*VSS.*", component.name, re.IGNORECASE)):
                all_cell_rails.append(copy.deepcopy(component))

                # Check if this component is already in rails by name
                if not any(rail.name == component.name for rail in top_cell_rails):
                    top_cell_rails.append(copy.deepcopy(component))

        top_cell_x2 = 0
        for component in self.updated_components:
            if isinstance(component, CircuitCell):
                top_cell_x2 += (component.bounding_box.x2 - component.bounding_box.x1)
        top_cell_y2 = max(component.layout.area.y2 for component in all_cell_rails)

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

                for nr, rail in enumerate(top_cell_rails):
                    rail.cell = component.cell
                    rail.number_id = len(self.updated_components) + nr
                    rail.named_cell = component.named_cell
                    rail.parent_cell = component.parent_cell
                    rail.cell_chain = component.cell_chain
                    rail.layout = RectAreaLayer()
                    top_cell_components.append(rail)

                top_cell_components.append(self.top_cell)

        components = TraceGenerator(project_properties=self.project_properties,
                                    components=top_cell_components,
                                    paths=[],
                                    net_list=None,
                                    used_area=self.top_cell.bounding_box
                                    ).get()



        # Don't include the temporary top cell since it is not real, but was needed for top cell trace generation
        for component in components:
            if not isinstance(component, CircuitCell):
                self.updated_components.append(component)

        rail_nr = 0
        for top_cell_rail in top_cell_rails:
            for rail in all_cell_rails:
                for component in self.updated_components:
                    if isinstance(component, CircuitCell) and component.cell_chain == rail.cell_chain:
                        print(component.cell_chain, rail.cell_chain)
                        print(component.transform_matrix)
                        if top_cell_rail.name == rail.name:
                            rail_nr += 1
                            trace = TraceNet(name=f"{rail.name}_{rail_nr}", cell=component.cell, named_cell=component.named_cell)
                            trace.instance = trace.__class__.__name__
                            trace.parent_cell = component.parent_cell
                            trace.cell_chain = component.cell_chain
                            top_cell_rail_y1 = -(top_cell_rail.layout.area.y2 - self.top_cell.bounding_box.y2)

                            segment1 = RectArea(x1=rail.layout.area.x1,
                                               y1=top_cell_rail_y1,
                                               x2=rail.layout.area.x1 + 50,
                                               y2=top_cell_rail.layout.area.y2)

                            segment2 = RectArea(x1=rail.layout.area.x2 - 50,
                                               y1=top_cell_rail_y1,
                                               x2=rail.layout.area.x2,
                                               y2=top_cell_rail.layout.area.y2)
                            #top_via = RectArea(x1=segment1.x1, y1=segment1.y2, x2=left_segment.x2, y2=top_segment.y2)

                            trace.segments = [RectAreaLayer(layer="m1", area=segment1),
                                              RectAreaLayer(layer="m1", area=segment2)]

                            self.updated_components.append(trace)


    def __add_top_cell_rail_to_rail_connections(self):
        pass


    def get(self):
        return self.updated_components