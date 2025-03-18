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

from circuit.circuit_components import Pin, CircuitCell, RectArea
from logger.logger import get_a_logger
import math
import numpy as np
import matplotlib.pyplot as plt
from draw_result.visualize_grid import visualize_grid, heatmap_test
from dataclasses import dataclass, field
import tomllib

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



    def __init__(self, components):



        self.routing_parameters = RoutingSizingParameters()


        self.logger = get_a_logger(__name__)

        #Load config
        self.config = self.__load_config()
        self.GRID_SIZE = self.config["generate_grid"]["GRID_SIZE"]
        self.SCALE_FACTOR = self.config["generate_grid"]["SCALE_FACTOR"]
        self.TRACE_WIDTH = self.config["generate_grid"]["TRACE_WIDTH"]
        self.VIA_MINIMUM_DISTANCE = self.config["generate_grid"]["VIA_MINIMUM_DISTANCE"]
        self.VIA_PADDING = self.config["magic_layout_creator"]["VIA_PADDING"]

        self.components = components
        self.port_area = {}
        self.port_scaled_coord = {}
        self.port_coordinates = {}
        self.used_area = RectArea(x1=self.GRID_SIZE, y1=self.GRID_SIZE, x2=0, y2=0)


        self.grid = None

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")


    def _port_area(self):

        for obj in self.components:
            if not isinstance(obj, (Pin, CircuitCell)):  # Skip components of these types
                self.used_area.x1 = min(self.used_area.x1, obj.transform_matrix.c)
                self.used_area.y1 = min(self.used_area.y1, obj.transform_matrix.f)
                self.used_area.x2 = max(self.used_area.x2, obj.transform_matrix.c + obj.bounding_box.x2)
                self.used_area.y2 = max(self.used_area.y2, obj.transform_matrix.f + obj.bounding_box.y2)

        for obj in self.components:

            if not isinstance(obj, (Pin, CircuitCell)):


                for port in obj.layout_ports:

                    if port.type == "B":
                        continue

                    x1 = (obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2 - self.used_area.x1 + self.LEEWAY_X)/self.SCALE_FACTOR
                    y1 = (obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2 - self.used_area.y1 + self.LEEWAY_Y)/self.SCALE_FACTOR

                    frac_x, int_x = math.modf(x1)
                    frac_y, int_y = math.modf(y1)
                    self.port_area.setdefault(port.type, []).append((round(int_x), round(int_y)))

                    self.port_coordinates.setdefault(str(obj.number_id) + port.type, []).extend([int(obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2), int(obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2)])
                    self.port_scaled_coord.setdefault(str(obj.number_id)+port.type, []).extend([int_x, frac_x, int_y, frac_y])


    def _calculate_non_overlap_parameters(self):
        self.routing_parameters.trace_width_scaled = math.ceil((self.TRACE_WIDTH+self.VIA_MINIMUM_DISTANCE+self.VIA_PADDING*2)/self.SCALE_FACTOR)
        for object_1 in self.components:
            if not isinstance(object_1, (Pin, CircuitCell)):
                for port in object_1.layout_ports:
                    if not port.type == "G":
                        self.routing_parameters.port_width_scaled = math.ceil(((port.area.x2-port.area.x1)/2 +self.VIA_MINIMUM_DISTANCE+self.VIA_PADDING*2+self.TRACE_WIDTH/2)/self.SCALE_FACTOR)

                    else:
                        self.routing_parameters.gate_width_scaled = math.ceil(((port.area.x2-port.area.x1)/2 +self.VIA_MINIMUM_DISTANCE+self.VIA_PADDING*2+self.TRACE_WIDTH/2)/self.SCALE_FACTOR)

                    self.routing_parameters.port_height_scaled = math.ceil(((port.area.y2-port.area.y1)/2 +self.VIA_MINIMUM_DISTANCE+self.VIA_PADDING*2+self.TRACE_WIDTH/2)/self.SCALE_FACTOR)
                    if self.routing_parameters.port_width_scaled != 0 and self.routing_parameters.gate_width_scaled != 0:
                        break



    def generate_grid(self):
        self.logger.info("Starting Grid Generation")



        scaled_grid_size_y = list(math.modf((self.used_area.y2-self.used_area.y1+2*self.LEEWAY_Y)/self.SCALE_FACTOR))
        scaled_grid_size_x = list(math.modf((self.used_area.x2 - self.used_area.x1 + 2 * self.LEEWAY_X)/self.SCALE_FACTOR))

        self.grid = [[0 for _ in range(int(scaled_grid_size_x[1]))] for _ in range(int(scaled_grid_size_y[1]))]


        for port in self.port_area:
            h = self.routing_parameters.port_height_scaled
            w = self.routing_parameters.gate_width_scaled if port == "G" else self.routing_parameters.port_width_scaled

            for x,y in self.port_area[port]:
                for i in range(y-h, y+h+1):
                    for j in range(x-w, x+w+1):
                        self.grid[i][j] = 1


        self.logger.info("Finished Grid Generation")

    def initialize_grid_generation(self):
        self._port_area()
        self._calculate_non_overlap_parameters()
        self.generate_grid()

        return self.grid, self.port_scaled_coord, self.used_area, self.port_coordinates, self.routing_parameters