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

from circuit.circuit_components import Pin, CircuitCell
from logger.logger import get_a_logger
import math


class GridGeneration:
    LEEWAY_X= 500
    LEEWAY_Y = 500



    def __init__(self, grid_size, objects, scale):

        self.logger = get_a_logger(__name__)
        self.grid_size = grid_size
        self.objects = objects
        self.port_area = []
        self.scale_factor = scale
        self.port_scaled_coord = {}
        self.port_coord = {}
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
                    x1 = (obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2 - self.used_area[0] + self.LEEWAY_X)/self.scale_factor
                    y1 = (obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2 - self.used_area[1] + self.LEEWAY_Y)/self.scale_factor

                    frac_x, int_x = math.modf(x1)
                    frac_y, int_y = math.modf(y1)

                    self.port_area.append([int(int_x), int(int_y)])
                    self.port_coord.setdefault(str(obj.number_id) + port.type, []).extend([int(obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2), int(obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2)])
                    self.port_scaled_coord.setdefault(str(obj.number_id)+port.type, []).extend([int_x, frac_x, int_y, frac_y])




    def generate_grid(self):
        self.logger.info("Starting Grid Generation")

        value_appended = False

        #port_area, area_coordinates, used_area, port_coord = _port_area(objects, grid_size, leeway_x, leeway_y)

        scaled_grid_size_y = list(math.modf((self.used_area[3]-self.used_area[1]+2*self.LEEWAY_Y)/self.scale_factor))
        scaled_grid_size_x = list(math.modf((self.used_area[2] - self.used_area[0] + 2 * self.LEEWAY_X)/self.scale_factor))

        self.grid = [[0 for _ in range(int(scaled_grid_size_x[1]))] for _ in range(int(scaled_grid_size_y[1]))]

        for x,y in self.port_area:
            self.grid[y][x] = 1

        self.logger.info("Finished Grid Generation")

    def initialize_grid_generation(self):
        self._port_area()
        self.generate_grid()
        
        return self.grid, self.port_scaled_coord, self.used_area, self.port_coord