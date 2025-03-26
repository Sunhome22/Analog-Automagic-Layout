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

        self.__create_cells()

    def __create_cells(self):
        components_grouped_by_circuit_cell = defaultdict(list)
        circuit_cells = list()

        for component in self.components:
            if isinstance(component, CircuitCell):
                print(component)
                circuit_cells.append(component)
            else:
                components_grouped_by_circuit_cell[component.parent_cell_chain].append(component)

        for circuit_cell in circuit_cells:
            for grouped_components in components_grouped_by_circuit_cell:
                if (re.search(r"^(?:.*--)?(.*)$", grouped_components).group(1)
                        == f"{circuit_cell.name}_{circuit_cell.cell}"):
                    components_grouped_by_circuit_cell[grouped_components].append(circuit_cell)

        for index, grouped_components in enumerate(components_grouped_by_circuit_cell):

            connections, overlap_dict, net_list = ConnectionLists(
                input_components=components_grouped_by_circuit_cell[grouped_components]).get()

            components = LinearOptimizationSolver(components_grouped_by_circuit_cell[grouped_components],
                                                  connections, overlap_dict).solve_placement()

            grid, port_scaled_coordinates, used_area, port_coordinates, routing_parameters = GridGeneration(
                components=components).initialize_grid_generation()

            origin_scaled_used_area = RectArea(x1=0, y1=0, x2=used_area.x2 - used_area.x1, y2=used_area.y2 - used_area.y1)

            for component in components:
                if isinstance(component, CircuitCell):
                    component.transform_matrix.set([1, 0, index*2000, 0, 1, 0])
                    component.bounding_box = origin_scaled_used_area

                # Scale other placed components to origin also
                elif isinstance(component, (Transistor, Capacitor, Resistor)):
                    component.transform_matrix.c -= used_area.x1
                    component.transform_matrix.f -= used_area.y1

            # path = AstarInitiator(grid=grid,
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

            # Update component information
            for component in components:
                self.updated_components.append(component)

            components.clear()

    def get(self):
        return self.updated_components