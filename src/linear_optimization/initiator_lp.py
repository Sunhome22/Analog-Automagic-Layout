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
    STANDARD_ORDER = ["T", "R", "C"]
    def __init__(self, components, connections, overlap_components):


        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))

        #load config
        self.config = self.__load_config()
        self.SUB_CELL_OFFSET = self.config["initiator_lp"]["SUB_CELL_OFFSET"]
        self.UNITED_RES_CAP = self.config["initiator_lp"]["UNITED_RES_CAP"]
        self.RELATIVE_PLACEMENT = self.config["initiator_lp"]["RELATIVE_PLACEMENT"]
        self.CUSTOM_RELATIVE_PLACEMENT_ORDER = self.config["initiator_lp"]["CUSTOM_RELATIVE_PLACEMENT_ORDER"]
        self.ENABLE_CUSTOM_ORDER = self.config["initiator_lp"]["ENABLE_CUSTOM_ORDER"]

        # Inputs

        self.components = components
        self.overlap_components = overlap_components
        self.connections = connections["component_connections"]
        self.placed_cells = 0
        for c in self.connections:
            self.logger.info(c)


        self.transistors = []
        self.transistor_connections = []
        self.resistors = []
        self.resistor_connections = []
        self.overlap_resistors = {
            "top": [],
            "side": []
        }
        self.overlap_capacitors = {
            "top": [],
            "side": []}
        self.overlap_transistors = {
            "top": [],
            "side": []
        }
        self.capacitors = []
        self.capacitor_connections = []

        self.used_area = RectArea(x1=sys.maxsize, y1=sys.maxsize, x2=0, y2=0)
        self.used_area_all = []
        self.coordinates_x = []
        self.coordinates_y = []

        if self.RELATIVE_PLACEMENT == "S":
            self.x_offset = self.SUB_CELL_OFFSET
            self.y_offset = 0
        else:
            self.x_offset = 0
            self.y_offset = self.SUB_CELL_OFFSET



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
        for key in self.coordinates_x:
            for obj in self.components:
                if obj.number_id == key:

                    self.used_area.x1 = min(self.used_area.x1, obj.transform_matrix.c)
                    self.used_area.y1 = min(self.used_area.y1, obj.transform_matrix.f)
                    self.used_area.x2 = max(self.used_area.x2, round(pulp.value(self.coordinates_x[key]))+ obj.bounding_box.x2)
                    self.used_area.y2 = max(self.used_area.y2, round(pulp.value(self.coordinates_y[key])) + obj.bounding_box.y2)
        self.used_area_all.append(self.used_area)

    def __extract_components(self):


        for obj in self.components:
            if isinstance(obj, Transistor) and obj not in self.transistors:
                self.transistors.append(obj)

            elif isinstance(obj, Resistor) and obj not in self.resistors:
                    self.resistors.append(obj)

            elif  isinstance(obj, Capacitor):
                if self.UNITED_RES_CAP and obj not in self.resistors:
                    self.resistors.append(obj)
                elif obj not in self.capacitors:
                    self.capacitors.append(obj)

    def __extract_overlap_pairs(self):

        for overlap_type in self.overlap_components:
            for overlap_pair in self.overlap_components[overlap_type]:

                if overlap_pair.instance == "Transistor":
                    self.overlap_transistors[overlap_type].append(overlap_pair)
                elif overlap_pair.instance == "Resistor":
                    self.overlap_resistors[overlap_type].append(overlap_pair)

                elif overlap_pair.instance == "Capacitor":
                    if self.UNITED_RES_CAP:
                        self.overlap_resistors[overlap_type].append(overlap_pair)
                    else:
                        self.overlap_capacitors[overlap_type].append(overlap_pair)

    def __extract_connection(self):
        component_types = ["nmos", "pmos", "npn", "pnp", "mim", "vpp", "hpo", "xhpo"]
        for con in self.connections:

            connection_conditions = {
                "Transistors": [con.start_comp_type == component_types[0] or con.start_comp_type == component_types[
                    1] or con.start_comp_type == component_types[2] or con.start_comp_type == component_types[3],
                                con.end_comp_type == component_types[0] or con.end_comp_type == component_types[
                                    1] or con.end_comp_type == component_types[2] or con.end_comp_type ==
                                component_types[3]],
                "Capacitors": [con.start_comp_type == component_types[4] or con.start_comp_type == component_types[5],
                               con.end_comp_type == component_types[4] or con.end_comp_type == component_types[5]],
                "Resistors": [con.start_comp_type == component_types[6] or con.start_comp_type == component_types[7],
                              con.end_comp_type == component_types[6] or con.end_comp_type == component_types[7]]
            }

            if not self.__check_vdd_vss(con.net):
                if all(connection_conditions["Transistors"]):

                    self.transistor_connections.append(con)
                elif all(connection_conditions["Resistors"]):
                    self.resistor_connections.append(con)
                elif all(connection_conditions["Capacitors"]):
                    if self.UNITED_RES_CAP:
                        self.resistor_connections.append(con)
                    else:
                        self.capacitor_connections.append(con)

    def __update_component_info(self):

        if self.placed_cells == 1:
            if self.CUSTOM_RELATIVE_PLACEMENT_ORDER == "S":
                previous_x = self.used_area_all[0].x2-self.used_area_all[0].x1
                previous_y = 0
            else:
                previous_x = 0
                previous_y = self.used_area_all[0].y2 - self.used_area_all[0].y1
        elif self.placed_cells == 2:
            if self.CUSTOM_RELATIVE_PLACEMENT_ORDER == "S":
                previous_x = self.used_area_all[0].x2 - self.used_area_all[0].x1 + self.x_offset + self.used_area_all[1].x2 - self.used_area_all[1].x2
                previous_y = 0
            else:
                previous_x = 0
                previous_y = self.used_area_all[0].y2 - self.used_area_all[0].y1 + self.y_offset + self.used_area_all[1].y2 - self.used_area_all[1].y2
        else:
            previous_x = 0
            previous_y = 0

        for component in self.components:
            for placement_id in self.coordinates_x:
                if placement_id == component.number_id:

                    component.transform_matrix.set([1, 0, int(round(pulp.value(self.coordinates_x[component.number_id]))-self.used_area.x1 + self.placed_cells*self.x_offset + previous_x), 0, 1,
                                                    int(round(pulp.value(self.coordinates_y[component.number_id]))-self.used_area.y1 + self.placed_cells*self.y_offset + previous_y)])
        self.placed_cells += 1



    def __call_linear_optimization(self):

        if self.ENABLE_CUSTOM_ORDER:
            order = self.CUSTOM_RELATIVE_PLACEMENT_ORDER
        else:
            order = self.STANDARD_ORDER


        for letter in order:
            if self.transistors and letter == "T":


                self.coordinates_x, self.coordinates_y = LinearOptimizationSolver(self.transistors, self.transistor_connections,  self.overlap_transistors).solve_placement()

                self.__get_used_area()
                self.__update_component_info()

            if self.resistors and letter == "R":
                self.coordinates_x, self.coordinates_y = LinearOptimizationSolver(self.resistors, self.resistor_connections, self.overlap_resistors).solve_placement()
                self.__get_used_area()
                self.__update_component_info()

            if self.capacitors and letter == "C" and not self.UNITED_RES_CAP:
                self.coordinates_x, self.coordinates_y = LinearOptimizationSolver(self.capacitors,
                                                                                  self.capacitor_connections,
                                                                                  self.overlap_capacitors).solve_placement()
                self.__get_used_area()
                self.__update_component_info()





    def initiate_linear_optimization(self):
        self.__extract_components()
        self.__extract_connection()
        self.__extract_overlap_pairs()
        self.__call_linear_optimization()

        return self.components