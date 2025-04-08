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
        self.last_origin_scaled_used_area_x2 = 0

        self.__create_cells()
        self.__add_top_cell_rails_around_cells()

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
                components_grouped_by_circuit_cell[component.parent_cell_chain].append(component)

        for circuit_cell in circuit_cells:
            for grouped_components in components_grouped_by_circuit_cell:
                if (re.search(r"^(?:.*--)?(.*)$", grouped_components).group(1)
                        == f"{circuit_cell.name}_{circuit_cell.cell}"):
                    components_grouped_by_circuit_cell[grouped_components].append(circuit_cell)

        # for grouped_components in enumerate(components_grouped_by_circuit_cell):
        #     for component in components_grouped_by_circuit_cell[grouped_components]:
        #         if not isinstance(component, (Transistor, Resistor, Capacitor, CircuitCell)):
        #             continue

        # Main cell creation loop
        for cell_nr, grouped_components in enumerate(components_grouped_by_circuit_cell):
            """With every iteration there is a set of components along with their associated circuit cell"""

            # Check if current circuit cell already has been solved
            cell = re.search(r'_(.*)', grouped_components).group(1)
            if cell in solved_circuit_cells.keys():
                self.logger.info(f"Using previously found solution for cell '{cell}' "
                                 f"with respect to parent cell chain '{grouped_components}'")
                self.__use_earlier_solution_for_cell(
                    cell_nr=cell_nr,
                    cell=cell,
                    solved_circuit_cells=solved_circuit_cells,
                    components_grouped_by_circuit_cell=components_grouped_by_circuit_cell,
                    grouped_components=grouped_components
                )
                continue

            connections, overlap_dict, net_list = ConnectionLists(
                input_components=components_grouped_by_circuit_cell[grouped_components]).get()

            components = LinearOptimizationSolver(components_grouped_by_circuit_cell[grouped_components],
                                                  connections, overlap_dict).solve_placement()

            # Move all components to the origin and set circuit cell position in top cell
            _, _, used_area, _, _ = GridGeneration(components=components).initialize_grid_generation()
            origin_scaled_used_area = RectArea(x1=0, y1=0, x2=used_area.x2 - used_area.x1,
                                               y2=used_area.y2 - used_area.y1)
            for component in components:
                if isinstance(component, CircuitCell):
                    component.bounding_box = origin_scaled_used_area
                elif isinstance(component, (Transistor, Capacitor, Resistor)):
                    component.transform_matrix.c -= used_area.x1
                    component.transform_matrix.f -= used_area.y1

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

            # Update components
            for component in components:
                self.updated_components.append(component)
                solved_circuit_cells[cell].append(component)
            components.clear()

        self.__set_cells_position()

    def __set_cells_position(self):
        print("yo")
        #for component in self.updated_components:

        # for component in components:
        #     if isinstance(component, CircuitCell):
        #         if component.cell == "COMP" or component.cell == "COMP2":
        #             component.bounding_box = origin_scaled_used_area
        #             continue
        #         print(component.bounding_box.x2, component.bounding_box.x2)
        #         # difference to add = ((component.bounding_box.x2 - component.bounding_box.x1)
        #         # - (component.bounding_box.x2 - component.bounding_box.x1)) // 2
        #         component.transform_matrix.set([1, 0, self.last_origin_scaled_used_area_x2, 0, 1, 0])
        #
        #         self.last_origin_scaled_used_area_x2 += abs(component.bounding_box.x2 - component.bounding_box.x1)

    def __add_top_cell_rails_around_cells(self):

        rails = []
        for component in self.updated_components:
            if isinstance(component, Pin) and (re.search(r".*VDD.*", component.name, re.IGNORECASE) or
                                               re.search(r".*VSS.*", component.name, re.IGNORECASE)):
                rails.append(component)

        for component in rails:
            for comp in rails:
                if component.name == comp.name and component.named_cell != comp.named_cell:
                    print(component, comp)


    def get(self):
        return self.updated_components