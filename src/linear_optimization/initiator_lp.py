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
    STANDARD_TRANSISTOR_ORDER = ["C", "B"]

    def __init__(self, components, connections, overlap_components):


        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))

        #load config
        self.config = self.__load_config()
        self.SUB_CELL_OFFSET = self.config["initiator_lp"]["SUB_CELL_OFFSET"]
        self.UNITED_RES_CAP = self.config["initiator_lp"]["UNITED_RES_CAP"]
        self.RELATIVE_PLACEMENT = self.config["initiator_lp"]["RELATIVE_PLACEMENT"]
        self.CUSTOM_RELATIVE_PLACEMENT_ORDER = self.config["initiator_lp"]["CUSTOM_RELATIVE_PLACEMENT_ORDER"]
        self.ENABLE_CUSTOM_ORDER = self.config["initiator_lp"]["ENABLE_CUSTOM_ORDER"]
        self.ENABLE_CUSTOM_TRANSISTOR_ORDER  = self.config["initiator_lp"]["ENABLE_CUSTOM_TRANSISTOR_ORDER"]
        self.CUSTOM_TRANSISTOR_ORDER = self.config["initiator_lp"]["CUSTOM_TRANSISTOR_ORDER"]
        self.CMOS_BIPOLAR_OFFSET = self.config["initiator_lp"]["CMOS_BIPOLAR_OFFSET"]
        # Inputs

        self.components = components
        self.overlap_components = overlap_components
        self.connections = connections["component_connections"]
        self.placed_cells = 0
        self.component_handling = None

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
        self.temp_transistor_x = []
        self.temp_transistor_y = []

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
        self.used_area = RectArea(x1=sys.maxsize, y1=sys.maxsize, x2=0, y2=0)
        for key in self.coordinates_x:
            for obj in self.components:
                if obj.number_id == key:
                    if self.component_handling == "CB":
                        self.used_area.x1 = min(self.used_area.x1, round(self.coordinates_x[key]))
                        self.used_area.y1 = min(self.used_area.y1, round(self.coordinates_y[key]))
                        self.used_area.x2 = max(self.used_area.x2,
                                                round(pulp.value(self.coordinates_x[key])) + obj.bounding_box.x2)
                        self.used_area.y2 = max(self.used_area.y2,
                                                round(pulp.value(self.coordinates_y[key])) + obj.bounding_box.y2)
                    else:
                        self.used_area.x1 = min(self.used_area.x1, round(pulp.value(self.coordinates_x[key])))
                        self.used_area.y1 = min(self.used_area.y1, round(pulp.value(self.coordinates_y[key])))
                        self.used_area.x2 = max(self.used_area.x2, round(pulp.value(self.coordinates_x[key]))
                                                + obj.bounding_box.x2)
                        self.used_area.y2 = max(self.used_area.y2, round(pulp.value(self.coordinates_y[key]))
                                                + obj.bounding_box.y2)
        self.used_area_all.append(self.used_area)

        self.logger.info(f"Used_area: {self.used_area}")

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

            elif  isinstance(obj, Capacitor):
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
            if self.RELATIVE_PLACEMENT == "S":
                return self.used_area_all[0].x2-self.used_area_all[0].x1, 0

            else:
                return 0, self.used_area_all[0].y2 - self.used_area_all[0].y1
        elif self.placed_cells == 2:
            if self.RELATIVE_PLACEMENT == "S":
                return (self.used_area_all[0].x2 - self.used_area_all[0].x1  + self.used_area_all[1].x2
                        - self.used_area_all[1].x1, 0)

            else:
                return (0,
                        self.used_area_all[0].y2 - self.used_area_all[0].y1  + self.used_area_all[1].y2
                        - self.used_area_all[1].y1)
        else:
            return 0, 0

    def __update_component_info(self):

        previous_x, previous_y = self.__get_previous_placement_offset()

        for component in self.components:
            for placement_id in self.coordinates_x:
                if placement_id == component.number_id:

                    if self.component_handling == "CB":
                        component.transform_matrix.set([1, 0, int(round(self.coordinates_x[component.number_id])
                                                                  - self.used_area.x1 + self.placed_cells
                                                                  * self.x_offset + previous_x), 0, 1,
                                                        int(round(self.coordinates_y[component.number_id])
                                                            - self.used_area.y1 + self.placed_cells
                                                            * self.y_offset + previous_y)])
                    else:
                        component.transform_matrix.set([1, 0,
                                                        int(round(pulp.value(self.coordinates_x[component.number_id]))
                                                            - self.used_area.x1 + self.placed_cells
                                                            * self.x_offset + previous_x), 0, 1,
                                                        int(round(pulp.value(self.coordinates_y[component.number_id]))
                                                            - self.used_area.y1 + self.placed_cells
                                                            * self.y_offset + previous_y)])
        self.placed_cells += 1
        self.logger.info(f"placed_cells: {self.placed_cells}")

    def __get_minimum_x_y(self, x_coordinate_list, y_coordinate_list, minimum):

        if minimum:
            x = sys.maxsize
            y = sys.maxsize
            for key in x_coordinate_list:
                x = min(x, round(pulp.value(x_coordinate_list[key])))
                y = min(y, round(pulp.value(y_coordinate_list[key])))

        else:
            x = 0
            y = 0
            for key in x_coordinate_list:
                for obj in self.components:
                    if obj.number_id == key:

                        x= max(x,round(x_coordinate_list[key]) + obj.bounding_box.x2)
                        y= max(y,round(y_coordinate_list[key]) + obj.bounding_box.y2)
        return x, y

    def __transistor_placement_edit(self):

        if self.ENABLE_CUSTOM_TRANSISTOR_ORDER:
            transistor_order = self.CUSTOM_TRANSISTOR_ORDER
        else:
            transistor_order = self.STANDARD_TRANSISTOR_ORDER

        x, y = self.__get_minimum_x_y(self.coordinates_x, self.coordinates_y, minimum = True)
        x1, y1 = self.__get_minimum_x_y(self.temp_transistor_x, self.temp_transistor_y, minimum = True)
        temp_x = {}
        temp_y = {}
        if transistor_order[0] == "C":
            for key in self.coordinates_x:
                temp_x[key] = pulp.value(self.coordinates_x[key])-x
                temp_y[key] = pulp.value(self.coordinates_y[key])-y

            x_max, y_max = self.__get_minimum_x_y(temp_x, temp_y, minimum=False)

            for key in self.temp_transistor_x:
                temp_x[key] = pulp.value(self.temp_transistor_x[key]) - x1
                temp_y[key] = pulp.value(self.temp_transistor_y[key]) - y1 + y_max + self.CMOS_BIPOLAR_OFFSET
        else:
            for key in self.temp_transistor_x:
                temp_x[key] = pulp.value(self.temp_transistor_x[key]) - x1
                temp_y[key] = pulp.value(self.temp_transistor_y[key]) - y1
            x_max, y_max = self.__get_minimum_x_y(temp_x, temp_y, minimum=False)
            for key in self.coordinates_x:
                temp_x[key] = pulp.value(self.coordinates_x[key]) - x
                temp_y[key] = pulp.value(self.coordinates_y[key]) - y + y_max + self.CMOS_BIPOLAR_OFFSET

        self.coordinates_x = temp_x
        self.coordinates_y = temp_y

    def __call_linear_optimization(self):

        if self.ENABLE_CUSTOM_ORDER:
            order = self.CUSTOM_RELATIVE_PLACEMENT_ORDER
        else:
            order = self.STANDARD_ORDER

        for letter in order:
            self.component_handling = letter
            if letter == "T":
                object_type = letter
                if self.bipolar_transistors:

                    self.temp_transistor_x, self.temp_transistor_y = LinearOptimizationSolver(
                        components=self.bipolar_transistors,
                        component_connections=self.bipolar_transistor_connections,
                        overlap_components=self.overlap_components["bipolar"],
                        object_type=object_type,
                        overlap=True).solve_placement()

                if self.transistors:

                    self.coordinates_x, self.coordinates_y = (
                        LinearOptimizationSolver(components=self.transistors,
                                                 component_connections=self.transistor_connections,
                                                 overlap_components=self.overlap_components["cmos"],
                                                 object_type=object_type,
                                                 overlap=True).solve_placement())

                if self.coordinates_x and self.temp_transistor_x:
                    self.component_handling = "CB"
                    self.__transistor_placement_edit()

                self.__get_used_area()
                self.__update_component_info()

            elif self.resistors and letter == "R":
                if self.UNITED_RES_CAP:
                    object_type = "RC"
                    merged = {"side": [], "top": []}
                    merged_connection_lists = self.resistor_connections + self.capacitor_connections

                    for key in ["resistor", "capacitor"]:
                        merged["side"].extend(self.overlap_components[key].get("side", []))
                        merged["top"].extend(self.overlap_components[key].get("top", []))

                else:
                    object_type = letter
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

            elif self.capacitors and letter == "C" and not self.UNITED_RES_CAP:
                object_type = letter
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
        return self.components

