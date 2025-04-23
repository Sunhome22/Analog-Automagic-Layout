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
import re
import sys
from dataclasses import dataclass

from circuit.circuit_components import Pin, CircuitCell, RectArea, Transistor, Resistor, Capacitor
from connections.connections import Connection
from logger.logger import get_a_logger
import math
import numpy as np
import matplotlib.pyplot as plt
from draw_result.visualize_grid import visualize_grid, heatmap_test
from dataclasses import dataclass, field
import tomllib

@dataclass
class Coordinates:
    x: int = field(default_factory=int)
    y: int = field(default_factory=int)

    def __init__(self, x,y):
        self.x = x
        self.y = y

@dataclass
class PortSize:
    width: int = field(default_factory=int)
    height: int = field(default_factory=int)



@dataclass
class RoutingParameters:
    trace_width_scaled: int = field(default_factory=int)
    minimum_segment_length: int = field(default_factory=int)
@dataclass
class BT:
    E: PortSize = field(default_factory=PortSize)
    C: PortSize = field(default_factory=PortSize)
    B: PortSize = field(default_factory=PortSize)


@dataclass
class CMOS:
    G: PortSize = field(default_factory=PortSize)
    S: PortSize = field(default_factory=PortSize)
    D: PortSize = field(default_factory=PortSize)
    VG: PortSize = field(default_factory=PortSize)
    VS: PortSize = field(default_factory=PortSize)
    VD: PortSize = field(default_factory=PortSize)

@dataclass
class Res:
    B: PortSize = field(default_factory=PortSize)
    P: PortSize = field(default_factory=PortSize)
    N: PortSize = field(default_factory=PortSize)
@dataclass
class Cap:
    A: PortSize = field(default_factory=PortSize)
    B: PortSize = field(default_factory=PortSize)

@dataclass
class ComponentPorts:
    cmos: CMOS = field(default_factory=CMOS)
    bipolar: BT = field(default_factory=BT)
    resistor: Res = field(default_factory=Res)
    capacitor: Cap = field(default_factory=Cap)


class GridGeneration:
    logger = get_a_logger(__name__)
    def __init__(self, components):



        #LOAD CONFIG
        self.config = self.__load_config()
        self.SCALE_FACTOR = self.config["generate_grid"]["SCALE_FACTOR"]
        self.TRACE_WIDTH = self.config["generate_grid"]["TRACE_WIDTH"]
        self.VIA_MINIMUM_DISTANCE = self.config["generate_grid"]["VIA_MINIMUM_DISTANCE"]
        self.VIA_PADDING = self.config["magic_layout_creator"]["VIA_PADDING"]
        self.GRID_LEEWAY_X = self.config["generate_grid"]["GRID_LEEWAY_X"]
        self.GRID_LEEWAY_Y = self.config["generate_grid"]["GRID_LEEWAY_Y"]

        #INPUTS
        self.components = components


        #PARAMETERS
        self.routing_parameters = RoutingParameters()
        self.component_ports = ComponentPorts()

        self.port_area = {}
        self.scaled_port_coordinates = {}
        self.port_coordinates = {}
        self.used_area = RectArea(x1=sys.maxsize, y1=sys.maxsize, x2=0, y2=0)
        self.grid = None



    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")


    def __port_area(self):

        for obj in self.components:
            if not check_instance(obj):  # Skip components of these types
                self.used_area.x1 = min(self.used_area.x1, obj.transform_matrix.c)
                self.used_area.y1 = min(self.used_area.y1, obj.transform_matrix.f)
                self.used_area.x2 = max(self.used_area.x2, obj.transform_matrix.c + obj.bounding_box.x2)
                self.used_area.y2 = max(self.used_area.y2, obj.transform_matrix.f + obj.bounding_box.y2)

        for obj in self.components:

            if not check_instance(obj):
                for port in obj.layout_ports:

                    if port.type == "B" and isinstance(obj, Transistor) and (obj.type == "nmos" or obj.type == "pmos"):
                        continue

                    x1 = (obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2 - self.used_area.x1 + self.GRID_LEEWAY_X)/self.SCALE_FACTOR
                    y1 = (obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2 - self.used_area.y1 + self.GRID_LEEWAY_Y)/self.SCALE_FACTOR

                    frac_x, int_x = math.modf(x1)
                    frac_y, int_y = math.modf(y1)
                    self.port_area.setdefault(str(obj.number_id)+obj.type + port.type, Coordinates(x =round(int_x), y= round(int_y)))

                    self.port_coordinates.setdefault(str(obj.number_id)+obj.type + port.type, Coordinates(x = int(obj.transform_matrix.c + (port.area.x1 + port.area.x2)/2), y= int(obj.transform_matrix.f + (port.area.y1 + port.area.y2)/2)))
                    self.scaled_port_coordinates.setdefault(str(obj.number_id)+obj.type+port.type, Coordinates(x=int(int_x), y = int(int_y)))


    def __calculate_non_overlap_parameters(self):
        self.routing_parameters.trace_width_scaled = math.ceil((self.TRACE_WIDTH+self.VIA_MINIMUM_DISTANCE+self.VIA_PADDING*2)/self.SCALE_FACTOR) +1
        self.routing_parameters.minimum_segment_length =  math.ceil((48 +self.VIA_MINIMUM_DISTANCE+self.VIA_PADDING*2+self.TRACE_WIDTH/2)/self.SCALE_FACTOR) +1
        for obj in self.components:


            if not check_instance(obj):
                for port in obj.layout_ports:
                    port_height = math.ceil(((port.area.y2 - port.area.y1) / 2 + self.VIA_MINIMUM_DISTANCE + self.VIA_PADDING * 2 + self.TRACE_WIDTH / 2) / self.SCALE_FACTOR) + 1
                    port_width = math.ceil(((port.area.x2 - port.area.x1) / 2 + self.VIA_MINIMUM_DISTANCE + self.VIA_PADDING * 2 + self.TRACE_WIDTH / 2) / self.SCALE_FACTOR) + 1
                    port_height_v = math.ceil(((port.area.y2 - port.area.y1) / 2 + self.VIA_PADDING  + self.TRACE_WIDTH / 2) / self.SCALE_FACTOR) + 1
                    port_width_v = math.ceil(((port.area.x2 - port.area.x1) / 2 +  self.VIA_PADDING  + self.TRACE_WIDTH / 2) / self.SCALE_FACTOR) + 1

                    if isinstance(obj, Transistor):

                        if obj.type =="nmos" or obj.type == "pmos":
                            if port.type == "G":

                                self.component_ports.cmos.G.width = port_width
                                self.component_ports.cmos.G.height = port_height
                                self.component_ports.cmos.VG.width = port_width_v
                                self.component_ports.cmos.VG.height = port_height_v
                            elif port.type == "D":

                                self.component_ports.cmos.D.width = port_width
                                self.component_ports.cmos.D.height = port_height
                                self.component_ports.cmos.VD.width = port_width_v
                                self.component_ports.cmos.VD.height = port_height_v

                            elif port.type == "S":

                                self.component_ports.cmos.S.width = port_width
                                self.component_ports.cmos.S.height = port_height
                                self.component_ports.cmos.VS.width = port_width_v
                                self.component_ports.cmos.VS.height = port_height_v
                        else:

                            if port.type == "B":
                                self.component_ports.bipolar.B.width = port_width
                                self.component_ports.bipolar.B.height = port_height
                            elif port.type =="C":
                                self.component_ports.bipolar.C.width = port_width
                                self.component_ports.bipolar.C.height = port_height
                            elif port.type == "E":
                                self.component_ports.bipolar.E.width = port_width
                                self.component_ports.bipolar.E.height = port_height
                    elif isinstance(obj, Resistor):

                        if port.type == "B":

                            self.component_ports.resistor.B.width = port_width
                            self.component_ports.resistor.B.height = port_height

                        elif port.type == "P":

                            self.component_ports.resistor.P.width = port_width -2
                            self.component_ports.resistor.P.height = port_height +1

                        elif port.type == "N":

                            self.component_ports.resistor.N.width = port_width -2
                            self.component_ports.resistor.N.height = port_height +1

                    elif isinstance(obj, Capacitor):

                        if port.type == "A":

                            self.component_ports.capacitor.A.width = port_width
                            self.component_ports.capacitor.A.height = port_height

                        elif port.type == "B":

                            self.component_ports.capacitor.B.width = port_width
                            self.component_ports.capacitor.B.width = port_height




    def __generate_grid(self):
        self.logger.info("Starting Grid Generation")

        scaled_grid_size_y = list(math.modf((self.used_area.y2-self.used_area.y1+2*self.GRID_LEEWAY_Y)/self.SCALE_FACTOR))
        scaled_grid_size_x = list(math.modf((self.used_area.x2 - self.used_area.x1 + 2 * self.GRID_LEEWAY_X)/self.SCALE_FACTOR))
        self.grid = [[0 for _ in range(int(scaled_grid_size_x[1]))] for _ in range(int(scaled_grid_size_y[1]))]


        component_types= ["nmos","pmos","npn","pnp","mim","vpp","hpo","xhpo"]

        for port in self.port_area:

            object_id, component_type, port_type = get_obj_id_and_types(port)

            if component_type == component_types[0] or component_type == component_types[1]:

                if check_ignorable_port(self.logger,components=self.components, object_id = object_id, port = port_type):
                    port_attribute = getattr(self.component_ports.cmos, "V"+port_type)

                else:
                    port_attribute = getattr(self.component_ports.cmos, port_type)

            elif component_type == component_types[2] or component_type == component_types[3]:
                port_attribute = getattr(self.component_ports.bipolar, port_type)
            elif component_type == component_types[4] or component_type == component_types[5]:
                port_attribute = getattr(self.component_ports.capacitor, port_type)
            elif component_type == component_types[6] or component_type == component_types[7]:
                port_attribute = getattr(self.component_ports.resistor, port_type)

            else:
                self.logger.error("No matching component type found")
                port_attribute = getattr(self.component_ports.cmos, port_type)




            h = port_attribute.height
            w = port_attribute.width


            self.logger.info(f"Grid_size x: {len(self.grid[0])}, y: {len(self.grid)}")

            for i in range(self.port_area[port].y-h, self.port_area[port].y+h+1):
                for j in range(self.port_area[port].x-w, self.port_area[port].x+w+1):
                    if i < scaled_grid_size_y[1] and j < scaled_grid_size_x[1]:
                        self.logger.info(f"Trying to update  grid x: {j}, y:{i}")
                        self.grid[i][j] = 1





        self.logger.info("Finished Grid Generation")

    def initialize_grid_generation(self):
        self.__port_area()
        self.__calculate_non_overlap_parameters()
        self.__generate_grid()
        heatmap_test(self.grid, "Ports")
        return self.grid, self.scaled_port_coordinates, self.used_area, self.port_coordinates, self.routing_parameters, self.component_ports

def check_instance(obj):
    return isinstance(obj, (Pin, CircuitCell))

def get_obj_id_and_types(key):
    pattern = r'^([1-9]\d{0,2})([A-Za-z]{1,10})([A-Z])$'
    match = re.match(pattern, key)

    if match:
        #returns object id, object type and port type
        return match.group(1), match.group(2), match.group(3)
    else:
        return None, None, None

def check_ignorable_port(logger, components, object_id, port):
    for obj in components:
        if obj.number_id == int(object_id):

            port_connection = obj.schematic_connections[port]

            return re.search(".*VSS.*", port_connection, re.IGNORECASE) or re.search(".*VDD.*", port_connection, re.IGNORECASE)
