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
from dataclasses import dataclass

from circuit.circuit_components import Pin, CircuitCell
from logger.logger import get_a_logger
import math
import numpy as np
import matplotlib.pyplot as plt
from draw_result.visualize_grid import visualize_grid, heatmap_test
from dataclasses import dataclass, field

@dataclass
class RoutingSizingParameters:
    trace_width_scaled: int = field(default_factory=int)
    port_width_scaled: int = field(default_factory=int)
    port_height_scaled: int = field(default_factory=int)
    gate_width_scaled: int = field(default_factory=int)
    minimum_segment_length: int = field(default_factory=int)

class GridGeneration:
    LEEWAY_X= 500
    LEEWAY_Y = 500



    def __init__(self, grid_size, objects, scale, trace_width, via_minimum_distance, added_via_size):
        self.trace_width = trace_width
        self.via_minimum_distance = via_minimum_distance
        self.added_via_size = added_via_size

        self.routing_sizing_area = RoutingSizingParameters()


        self.logger = get_a_logger(__name__)
        self.grid_size = grid_size
        self.objects = objects
        self.port_area = {}
        self.scale_factor = scale
        self.port_scaled_coord = {}
        self.port_coordinates = {}
        self.used_area = [grid_size, grid_size, 0, 0]


        self.grid = None


    def _port_area(self):

        for obj in self.objects:
            if not isinstance(obj, (Pin, CircuitCell)):  # Skip objects of these types
                self.used_area[0] = min(self.used_area[0], obj.transform_matrix.c)
                self.used_area[2] = max(self.used_area[2], obj.transform_matrix.c + obj.bounding_box.x2)
                self.used_area[1] = min(self.used_area[1], obj.transform_matrix.f)
                self.used_area[3] = max(self.used_area[3], obj.transform_matrix.f + obj.bounding_box.y2)

        for obj in self.objects:

            if not isinstance(obj, (Pin, CircuitCell)):


                for port in obj.layout_ports:

                    if port.type == "B":
                        continue

                    x1 = (obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2 - self.used_area[0] + self.LEEWAY_X)/self.scale_factor
                    y1 = (obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2 - self.used_area[1] + self.LEEWAY_Y)/self.scale_factor

                    frac_x, int_x = math.modf(x1)
                    frac_y, int_y = math.modf(y1)
                    self.port_area.setdefault(port.type, []).append((round(int_x), round(int_y)))

                    self.port_coordinates.setdefault(str(obj.number_id) + port.type, []).extend([int(obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2), int(obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2)])
                    self.port_scaled_coord.setdefault(str(obj.number_id)+port.type, []).extend([int_x, frac_x, int_y, frac_y])


    def _calculate_non_overlap_parameters(self):
        self.routing_sizing_area.trace_width_scaled = math.ceil((self.trace_width+self.via_minimum_distance+self.added_via_size*2)/self.scale_factor)
        for object_1 in self.objects:
            if not isinstance(object_1, (Pin, CircuitCell)):
                for port in object_1.layout_ports:
                    if not port.type == "G":
                        self.routing_sizing_area.port_width_scaled = math.ceil(((port.area.x2-port.area.x1)/2 +self.via_minimum_distance+self.added_via_size*2+self.trace_width/2)/self.scale_factor)

                    else:
                        self.routing_sizing_area.gate_width_scaled = math.ceil(((port.area.x2-port.area.x1)/2 +self.via_minimum_distance+self.added_via_size*2+self.trace_width/2)/self.scale_factor)

                    self.routing_sizing_area.port_height_scaled = math.ceil(((port.area.y2-port.area.y1)/2 +self.via_minimum_distance+self.added_via_size*2+self.trace_width/2)/self.scale_factor)
                    if self.routing_sizing_area.port_width_scaled != 0 and self.routing_sizing_area.gate_width_scaled != 0:
                        break



    def generate_grid(self):
        self.logger.info("Starting Grid Generation")



        scaled_grid_size_y = list(math.modf((self.used_area[3]-self.used_area[1]+2*self.LEEWAY_Y)/self.scale_factor))
        scaled_grid_size_x = list(math.modf((self.used_area[2] - self.used_area[0] + 2 * self.LEEWAY_X)/self.scale_factor))

        self.grid = [[0 for _ in range(int(scaled_grid_size_x[1]))] for _ in range(int(scaled_grid_size_y[1]))]


        for port in self.port_area:
            h = self.routing_sizing_area.port_height_scaled
            w = self.routing_sizing_area.gate_width_scaled if port == "G" else self.routing_sizing_area.port_width_scaled

            for x,y in self.port_area[port]:
                for i in range(y-h, y+h+1):
                    for j in range(x-w, x+w+1):
                        self.grid[i][j] = 1


        self.logger.info("Finished Grid Generation")

    def initialize_grid_generation(self):
        self._port_area()
        self._calculate_non_overlap_parameters()
        self.generate_grid()

        return self.grid, self.port_scaled_coord, self.used_area, self.port_coordinates, self.routing_sizing_area