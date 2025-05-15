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

import os
import re
import tomllib
import pulp
from circuit.circuit_components import Pin, CircuitCell, Transistor, TraceNet, Resistor, Capacitor, RectArea
from connections.connections import overlap_pairs
from linear_optimization.linear_optimization import LinearOptimizationSolver
from logger.logger import get_a_logger
import sys


class LPInitiator:
    logger = get_a_logger(__name__)
    STANDARD_ORDER = ["T", "B", "R", "C"]

    def __init__(self, components, connections, overlap_components):
        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))

        #load config
        self.config = self.__load_config()
        self.SUB_CELL_OFFSET_1 = self.config["initiator_lp"]["SUB_CELL_OFFSET_1"]
        self.SUB_CELL_OFFSET_2 = self.config["initiator_lp"]["SUB_CELL_OFFSET_2"]
        self.SUB_CELL_OFFSET_3 = self.config["initiator_lp"]["SUB_CELL_OFFSET_3"]
        self.UNITED_RES_CAP = self.config["initiator_lp"]["UNITED_RES_CAP"]
        self.RELATIVE_COMPONENT_PLACEMENT = self.config["initiator_lp"]["RELATIVE_COMPONENT_PLACEMENT"]
        self.CUSTOM_COMPONENT_ORDER = self.config["initiator_lp"]["CUSTOM_COMPONENT_ORDER"]
        self.ENABLE_CUSTOM_COMPONENT_ORDER = self.config["initiator_lp"]["ENABLE_CUSTOM_COMPONENT_ORDER"]
        # Inputs

        self.components = components
        self.overlap_components = overlap_components
        self.connections = connections["component_connections"]
        self.placed_cells = 0
        self.component_handling = None
        self.placed_sub_cells = []
        self.transistors = []
        self.transistor_connections = []
        self.resistors = []
        self.resistor_connections = []
        self.bipolar_transistors = []
        self.bipolar_transistor_connections = []
        self.capacitors = []
        self.capacitor_connections = []

        self.used_area = RectArea(x1=sys.maxsize, y1=sys.maxsize, x2=0, y2=0)
        self.used_area_all = []
        self.coordinates_x = []
        self.coordinates_y = []

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    @staticmethod
    def __check_vdd_vss(net):
        return re.search(".*VSS.*", net, re.IGNORECASE) or re.search(".*VDD.*", net, re.IGNORECASE)

    def __get_used_area(self):
        self.used_area = RectArea(x1=sys.maxsize, y1=sys.maxsize, x2=0, y2=0)
        for key in self.coordinates_x:
            for obj in self.components:
                if obj.number_id == key:

                    self.used_area.x1 = min(self.used_area.x1, round(pulp.value(self.coordinates_x[key])))
                    self.used_area.y1 = min(self.used_area.y1, round(pulp.value(self.coordinates_y[key])))
                    self.used_area.x2 = max(self.used_area.x2, round(pulp.value(self.coordinates_x[key]))
                                            + obj.bounding_box.x2)
                    self.used_area.y2 = max(self.used_area.y2, round(pulp.value(self.coordinates_y[key]))
                                            + obj.bounding_box.y2)
        self.used_area_all.append(self.used_area)

    def __extract_components(self):

        for obj in self.components:
            if (isinstance(obj, Transistor) and (obj.type == "nmos" or obj.type == "pmos")
                    and obj not in self.transistors):
                self.transistors.append(obj)
            elif (isinstance(obj, Transistor) and (obj.type == "pnp" or obj.type == "npn")
                  and obj not in self.bipolar_transistors):
                self.bipolar_transistors.append(obj)

            elif isinstance(obj, Resistor) and obj not in self.resistors:
                self.resistors.append(obj)

            elif isinstance(obj, Capacitor):
                if self.UNITED_RES_CAP and obj not in self.resistors:
                    self.resistors.append(obj)
                elif obj not in self.capacitors:
                    self.capacitors.append(obj)

    def __extract_connection(self):
        component_types = ["nmos", "pmos", "npn", "pnp", "mim", "vpp", "hpo", "xhpo"]
        for con in self.connections:

            connection_conditions = {
                "Transistors": [con.start_comp_type == component_types[0] or con.start_comp_type == component_types[1],
                                con.end_comp_type == component_types[0] or con.end_comp_type == component_types[1]],
                "Bipolar_transistors": [con.start_comp_type == component_types[2]
                                        or con.start_comp_type == component_types[3],
                                        con.end_comp_type == component_types[2]
                                        or con.end_comp_type == component_types[3]],
                "Capacitors": [con.start_comp_type == component_types[4] or con.start_comp_type == component_types[5],
                               con.end_comp_type == component_types[4] or con.end_comp_type == component_types[5]],
                "Resistors": [con.start_comp_type == component_types[6] or con.start_comp_type == component_types[7],
                              con.end_comp_type == component_types[6] or con.end_comp_type == component_types[7]],
                "United": [self.UNITED_RES_CAP,
                           con.start_comp_type == component_types[4] or con.start_comp_type == component_types[5]
                           or con.start_comp_type == component_types[6] or con.start_comp_type == component_types[7],
                           con.end_comp_type == component_types[4] or con.end_comp_type == component_types[5]
                           or con.end_comp_type == component_types[6] or con.end_comp_type == component_types[7]]
            }

            if not self.__check_vdd_vss(con.net):
                if all(connection_conditions["Transistors"]):
                    self.transistor_connections.append(con)
                elif all(connection_conditions["Bipolar_transistors"]):
                    self.bipolar_transistor_connections.append(con)
                elif all(connection_conditions["United"]):
                    self.resistor_connections.append(con)
                elif all(connection_conditions["Resistors"]):
                    self.resistor_connections.append(con)
                elif all(connection_conditions["Capacitors"]):
                    self.capacitor_connections.append(con)

    def __get_previous_placement_offset(self):
        if self.placed_cells == 1:
            if self.RELATIVE_COMPONENT_PLACEMENT == "H":
                return self.used_area_all[0].x2-self.used_area_all[0].x1 + self.SUB_CELL_OFFSET_1, 0

            else:
                return 0, self.used_area_all[0].y2 - self.used_area_all[0].y1 + self.SUB_CELL_OFFSET_1
        elif self.placed_cells == 2:
            if self.RELATIVE_COMPONENT_PLACEMENT == "H":
                return (self.used_area_all[0].x2 - self.used_area_all[0].x1 + self.used_area_all[1].x2
                        - self.used_area_all[1].x1 + self.SUB_CELL_OFFSET_1 + self.SUB_CELL_OFFSET_2, 0)

            else:
                return (0,
                        self.used_area_all[0].y2 - self.used_area_all[0].y1 + self.used_area_all[1].y2
                        - self.used_area_all[1].y1 + self.SUB_CELL_OFFSET_1 + self.SUB_CELL_OFFSET_2)
        elif self.placed_cells == 3:
            if self.RELATIVE_COMPONENT_PLACEMENT == "H":
                return (self.used_area_all[0].x2 - self.used_area_all[0].x1 + self.used_area_all[1].x2
                        - self.used_area_all[1].x1 + self.used_area_all[2].x2 - self.used_area_all[2].x1
                        + self.SUB_CELL_OFFSET_1 + self.SUB_CELL_OFFSET_2 + self.SUB_CELL_OFFSET_3, 0)

            else:
                return (0,
                        self.used_area_all[0].y2 - self.used_area_all[0].y1 + self.used_area_all[1].y2
                        - self.used_area_all[1].y1 + self.used_area_all[2].y2 - self.used_area_all[2].y1
                        + self.SUB_CELL_OFFSET_1 + self.SUB_CELL_OFFSET_2 + self.SUB_CELL_OFFSET_3)

        else:
            return 0, 0

    def __update_component_info(self):

        previous_x, previous_y = self.__get_previous_placement_offset()

        for component in self.components:
            for placement_id in self.coordinates_x:
                if placement_id == component.number_id:

                    component.transform_matrix.set([1, 0,
                                                    int(round(pulp.value(self.coordinates_x[component.number_id]))
                                                        - self.used_area.x1 + previous_x), 0, 1,
                                                    int(round(pulp.value(self.coordinates_y[component.number_id]))
                                                        - self.used_area.y1 + previous_y)])
        self.placed_cells += 1

    def __call_linear_optimization(self):

        if self.ENABLE_CUSTOM_COMPONENT_ORDER:
            order = self.CUSTOM_COMPONENT_ORDER
        else:
            order = self.STANDARD_ORDER

        for object_type in order:
            self.component_handling = object_type
            if object_type == "T" and self.transistors:
                self.placed_sub_cells.append(object_type)
                self.coordinates_x, self.coordinates_y = (
                    LinearOptimizationSolver(components=self.transistors,
                                             component_connections=self.transistor_connections,
                                             overlap_components=self.overlap_components["cmos"],
                                             object_type=object_type,
                                             overlap=True).solve_placement())

                self.__get_used_area()
                self.__update_component_info()

            elif self.bipolar_transistors and object_type == "B":
                self.placed_sub_cells.append(object_type)
                self.coordinates_x, self.coordinates_y = LinearOptimizationSolver(
                    components=self.bipolar_transistors,
                    component_connections=self.bipolar_transistor_connections,
                    overlap_components=self.overlap_components["bipolar"],
                    object_type=object_type,
                    overlap=True).solve_placement()

                self.__get_used_area()
                self.__update_component_info()

            elif self.resistors and object_type == "R":
                if self.UNITED_RES_CAP:
                    object_type = "RC"
                    self.placed_sub_cells.append(object_type)
                    merged = {"side": [], "top": []}
                    merged_connection_lists = self.resistor_connections + self.capacitor_connections

                    for key in ["resistor", "capacitor"]:
                        merged["side"].extend(self.overlap_components[key].get("side", []))
                        merged["top"].extend(self.overlap_components[key].get("top", []))

                else:
                    self.placed_sub_cells.append(object_type)
                    merged = self.overlap_components["resistor"]
                    merged_connection_lists = self.resistor_connections

                self.coordinates_x, self.coordinates_y = (
                    LinearOptimizationSolver(components=self.resistors,
                                             component_connections=merged_connection_lists,
                                             overlap_components=merged,
                                             object_type=object_type,
                                             overlap=False).solve_placement())

                self.__get_used_area()
                self.__update_component_info()

            elif self.capacitors and object_type == "C" and not self.UNITED_RES_CAP:
                self.placed_sub_cells.append(object_type)
                self.coordinates_x, self.coordinates_y = (
                    LinearOptimizationSolver(components=self.capacitors,
                                             component_connections=self.capacitor_connections,
                                             overlap_components=self.overlap_components["capacitor"],
                                             object_type=object_type,
                                             overlap=False).solve_placement())
                self.__get_used_area()
                self.__update_component_info()

    def initiate_linear_optimization(self):
        self.__extract_components()
        self.__extract_connection()
        self.__call_linear_optimization()
        return self.components, self.placed_sub_cells