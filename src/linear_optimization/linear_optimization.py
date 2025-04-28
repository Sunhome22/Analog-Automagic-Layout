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

import pulp
import time
import pickle
import pyscipopt
import os
import tomllib
from circuit.circuit_components import Pin, CircuitCell, Transistor, TraceNet
from logger.logger import get_a_logger


class LinearOptimizationSolver:
    logger = get_a_logger(__name__)

    def __init__(self, components, component_connections, overlap_components, object_type, overlap):
        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))

        # Load config
        self.config = self.__load_config()
        self.ALPHA = self.config["linear_optimization"]["ALPHA"]
        self.BETA = self.config["linear_optimization"]["BETA"]
        self.THETA = self.config["linear_optimization"]["THETA"]
        self.UNIT_HEIGHT = self.config["linear_optimization"]["UNIT_HEIGHT"]
        self.UNIT_WIDTH = self.config["linear_optimization"]["UNIT_WIDTH"]
        self.MIRROR = self.config["linear_optimization"]["MIRROR"]
        # OFFSET
        self.TRANSISTOR_OFFSET_X = self.config["linear_optimization"]["TRANSISTOR_OFFSET_X"]
        self.TRANSISTOR_OFFSET_Y = self.config["linear_optimization"]["TRANSISTOR_OFFSET_Y"]
        self.RESISTOR_OFFSET_X = self.config["linear_optimization"]["RESISTOR_OFFSET_X"]
        self.RESISTOR_OFFSET_Y = self.config["linear_optimization"]["RESISTOR_OFFSET_Y"]
        self.CAPACITOR_OFFSET_X = self.config["linear_optimization"]["CAPACITOR_OFFSET_X"]
        self.CAPACITOR_OFFSET_Y = self.config["linear_optimization"]["CAPACITOR_OFFSET_Y"]
        # STOP TOLERANCE
        self.CUSTOM_STOP_TOLERANCE = self.config["linear_optimization"]["CUSTOM_STOP_TOLERANCE"]
        self.STOP_TOLERANCE_STANDARD = self.config["linear_optimization"]["STOP_TOLERANCE_STANDARD"]
        self.STOP_TOLERANCE_TRANSISTORS = self.config["linear_optimization"]["STOP_TOLERANCE_TRANSISTORS"]
        self.STOP_TOLERANCE_RESISTORS = self.config["linear_optimization"]["STOP_TOLERANCE_RESISTORS"]
        self.STOP_TOLERANCE_CAPACITORS = self.config["linear_optimization"]["STOP_TOLERANCE_CAPACITORS"]
        self.RUN = self.config["linear_optimization"]["RUN"]

        self.SOLVER_MSG = self.config["linear_optimization"]["SOLVER_MSG"]
        self.GRID_SIZE = self.config["generate_grid"]["GRID_SIZE"]
        self.VERTICAL_SYMMETRY = self.config["linear_optimization"]["VERTICAL_SYMMETRY"]
        self.HORIZONTAL_SYMMETRY = self.config["linear_optimization"]["HORIZONTAL_SYMMETRY"]


        # Inputs
        self.components = components
        self.overlap_components = overlap_components
        self.connections = component_connections
        self.overlap = overlap
        self.object_type = object_type

        # Data structures
        self.stop_tolerance = 0.001
        self.x_possible = []
        self.y_possible = []
        self.functional_components = []
        self.structural_components = []
        self.component_ids = []
        self.component_names = []
        self.coordinates_x = {}
        self.coordinates_y = {}
        self.width = {}
        self.height = {}
        self.d_x = {}
        self.d_y = {}
        # Setup of problem space and solver
        self.problem_space = pulp.LpProblem("ComponentPlacement", pulp.LpMinimize)
        self.solver = pulp.SCIP_PY(msg=self.SOLVER_MSG, mip=False, warmStart=False,
                                   options=[f"limits/gap={self.stop_tolerance}"])

        # Make lists of functional components and structural components
        for comp in self.components:

            if not isinstance(comp, (Pin, CircuitCell, TraceNet)):

                self.component_ids.append(comp.number_id)
                self.component_names.append(comp.name)
                self.functional_components.append(comp)

            else:
                self.structural_components.append(comp)

        self.__get_stop_tolerance()
        self.__get_offset()

        # Setup of problem space and solver
        self.problem_space = pulp.LpProblem("ComponentPlacement", pulp.LpMinimize)
        self.solver = pulp.SCIP_PY(msg=self.SOLVER_MSG, mip=False, warmStart=False,
                                   options=[f"limits/gap={self.stop_tolerance}"])
        # Constraints
        self.__extract_possible_positions()
        self.x = pulp.LpVariable.dicts(f"x_bin", [(i, xv) for i in self.component_ids for xv in self.x_possible],
                                       cat="Binary")
        self.y = pulp.LpVariable.dicts(f"y_bin", [(i, yv) for i in self.component_ids for yv in self.y_possible],
                                       cat="Binary")
        # Bounds
        self.x_min = pulp.LpVariable("x_min", lowBound=0)
        self.x_max = pulp.LpVariable("x_max", lowBound=0)
        self.y_min = pulp.LpVariable("y_min", lowBound=0)
        self.y_max = pulp.LpVariable("y_max", lowBound=0)

        # Get width and height
        for c in self.functional_components:
            self.width[c.number_id] = c.bounding_box.x2 - c.bounding_box.x1
            self.height[c.number_id] = c.bounding_box.y2 - c.bounding_box.y1

        # Debugging
        if self.MIRROR:
            self.mirrored_components = self.__check_mirrored_components()

            self.logger.info(f"MIRRORED COMP")
            self.logger.info(f"obj1 {self.mirrored_components}")

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def __get_offset(self):
        if self.object_type == "T":
            self.OFFSET_X = self.TRANSISTOR_OFFSET_X
            self.OFFSET_Y = self.TRANSISTOR_OFFSET_Y
        elif self.object_type == "R":
            self.OFFSET_X = self.RESISTOR_OFFSET_X
            self.OFFSET_Y = self.RESISTOR_OFFSET_Y
        elif self.object_type == "C":
            self.OFFSET_X = self.CAPACITOR_OFFSET_X
            self.OFFSET_Y = self.CAPACITOR_OFFSET_Y
        elif self.object_type == "RC":
            self.OFFSET_X = max(self.CAPACITOR_OFFSET_X, self.RESISTOR_OFFSET_X)
            self.OFFSET_Y = max(self.CAPACITOR_OFFSET_Y, self.RESISTOR_OFFSET_Y)

        else:
            self.OFFSET_X = max(self.CAPACITOR_OFFSET_X, self.RESISTOR_OFFSET_X, self.TRANSISTOR_OFFSET_X)
            self.OFFSET_Y = max(self.CAPACITOR_OFFSET_Y, self.RESISTOR_OFFSET_Y, self.TRANSISTOR_OFFSET_Y)

    def __get_stop_tolerance(self):
        if self.CUSTOM_STOP_TOLERANCE:
            if self.object_type == "T":
                self.stop_tolerance = self.STOP_TOLERANCE_TRANSISTORS
            elif self.object_type == "R":
                self.stop_tolerance = self.STOP_TOLERANCE_RESISTORS
            elif self.object_type == "C":
                self.stop_tolerance = self.STOP_TOLERANCE_CAPACITORS
            elif self.object_type == "RC":
                self.stop_tolerance = max(self.STOP_TOLERANCE_RESISTORS, self.STOP_TOLERANCE_CAPACITORS)

        else:
            self.stop_tolerance = self.STOP_TOLERANCE_STANDARD

    def __check_mirrored_components(self) -> list:
        mirrored_objects = []
        components2 = self.functional_components[:]  # shallow copy
        side_check = False
        top_check = False
        for component in self.functional_components:
            group = []
            for component2 in components2:
                if (component.group == component2.group and component != component2 and component.group is not None
                        and component.type == component2.type and component.bounding_box == component2.bounding_box):
                    group.append([component, component2])

            if len(group) == 1 and ([group[0][1], group[0][0]]) not in mirrored_objects:
                mirrored_objects.append([group[0][0], group[0][1]])
                components2.remove(group[0][0])
                components2.remove(group[0][1])

        # Faux mirrored objects:
        for component in self.functional_components:
            group = []
            if not self.__element_in_sublist(component, mirrored_objects):
                for component2 in components2:

                    for pair in self.overlap_components["top"]:
                        if [component.number_id, component2.number_id] == pair.component_ids:
                            top_check = True
                            break

                    for pair in self.overlap_components["side"]:
                        if [component.number_id, component2.number_id] == pair.component_ids:
                            side_check = True
                            break

                    if top_check and side_check:

                        group.append([component, component2])
                        break
                top_check = False
                side_check = False
                if len(group) == 1:
                    if (([group[0][0], group[0][1]]) not in mirrored_objects
                            and ([group[0][1], group[0][0]]) not in mirrored_objects):
                        mirrored_objects.append([group[0][0], group[0][1]])
        return mirrored_objects

    def __constrain_mirror(self):
        if self.VERTICAL_SYMMETRY:
            for component in self.mirrored_components:
                self.problem_space += (self.coordinates_x[component[0].number_id] + self.width[component[0].number_id]
                                       == self.GRID_SIZE - self.coordinates_x[component[1].number_id])
                self.problem_space += (self.coordinates_y[component[0].number_id]
                                       == self.coordinates_y[component[1].number_id])
        if self.HORIZONTAL_SYMMETRY:
            for component in self.mirrored_components:
                self.problem_space += (self.coordinates_x[component[0].number_id] ==  self.coordinates_x[component[1].number_id])
                self.problem_space += (self.coordinates_y[component[0].number_id] + self.height[component[0].number_id]
                                       == self.GRID_SIZE-self.coordinates_y[component[1].number_id])


    @staticmethod
    def __element_in_sublist(element: object, big_list: list) -> bool:
        return any(element in small_list for small_list in big_list)

    def __extract_possible_positions(self):
        x = []
        y = []
        x_intervals = [self.UNIT_WIDTH]
        y_intervals = [self.UNIT_HEIGHT]

        if self.OFFSET_X != 0:
            x_intervals.append(self.OFFSET_X)
        if self.OFFSET_Y != 0:
            x_intervals.append(self.OFFSET_Y)
        for component in self.functional_components:

            h = component.bounding_box.y2 - component.bounding_box.y1
            w = component.bounding_box.x2 - component.bounding_box.x1
            if w not in x_intervals:
                x_intervals.append(w)
                if w+self.OFFSET_X not in x_intervals:
                    x_intervals.append(w+self.OFFSET_X)
            if h not in y_intervals:
                y_intervals.append(h)
                if h+self.OFFSET_Y not in y_intervals:
                    y_intervals.append(h+self.OFFSET_Y)

        for index, value in enumerate(x_intervals):
            for x_pos in range(self.GRID_SIZE//2, self.GRID_SIZE - 1, value):
                x.append(x_pos)

            for x_pos in range(self.GRID_SIZE // 2, 0, -value):
                x.append(x_pos)

        for index, n in enumerate(y_intervals):
            for y_pos in range(self.GRID_SIZE//2, self.GRID_SIZE - 1, n):
                y.append(y_pos)

            for y_pos in range(self.GRID_SIZE//2, -1, -n):
                y.append(y_pos)

        x = list(set(x))
        y = list(set(y))
        x.sort()
        y.sort()
        self.x_possible = x
        self.y_possible = y

    def __get_port_parameters(self, component) -> tuple:
        # staring off utilizing the first point in connections area as point of contact
        port_parameter = []
        port_parameter2 = []

        for c in self.functional_components:
            if c.number_id == int(component.start_comp_id):
                for p in c.layout_ports:
                    if len(component.start_area) > 1:
                        if p.type == component.start_area[0] or p.type == component.start_area[1]:
                            port_parameter.append(p.area)
                    elif p.type == component.start_area:
                        port_parameter.append(p.area)

            if c.number_id == int(component.end_comp_id):
                for p in c.layout_ports:
                    if len(component.end_area) > 1:
                        if p.type == component.end_area[0] or p.type == component.end_area[1]:
                            port_parameter2.append(p.area)
                    elif p.type == component.end_area:
                        port_parameter2.append(p.area)
        return port_parameter, port_parameter2

    def __constraint_minimize_manhattan_distance(self):
        i = 0
        for conn in self.connections:

            if not conn.end_comp_id == '' and conn.start_comp_id != conn.end_comp_id:

                start_port_parameters, end_port_parameters = self.__get_port_parameters(conn)

                self.d_x[(conn.start_comp_id, conn.end_comp_id)] = pulp.LpVariable(
                    f"d_x_{conn.start_comp_id}_{conn.end_comp_id}_{i}", 0, cat='Continuous')
                self.d_y[(conn.start_comp_id, conn.end_comp_id)] = pulp.LpVariable(
                    f"d_y_{conn.start_comp_id}_{conn.end_comp_id}_{i}", 0, cat='Continuous')

                self.x_start_port = start_port_parameters[0].x2 - (start_port_parameters[0].x1 // 2)
                self.y_start_port = start_port_parameters[0].y2 - (start_port_parameters[0].y1 // 2)
                self.x_end_port = end_port_parameters[0].x2 - (end_port_parameters[0].x1 // 2)
                self.y_end_port = end_port_parameters[0].y2 - (end_port_parameters[0].y1 // 2)

                self.problem_space += self.d_x[(conn.start_comp_id, conn.end_comp_id)] >= (
                        self.coordinates_x[int(conn.start_comp_id)] + self.x_start_port) - (
                        self.coordinates_x[int(conn.end_comp_id)] + self.x_end_port)
                self.problem_space += self.d_x[(conn.start_comp_id, conn.end_comp_id)] >= (
                            self.coordinates_x[int(conn.end_comp_id)] + self.x_end_port) - (
                            self.coordinates_x[int(conn.start_comp_id)] + self.x_start_port)
                self.problem_space += self.d_y[(conn.start_comp_id, conn.end_comp_id)] >= (
                            self.coordinates_y[int(conn.start_comp_id)] + self.y_start_port) - (
                            self.coordinates_y[int(conn.end_comp_id)] + self.y_end_port)
                self.problem_space += self.d_y[(conn.start_comp_id, conn.end_comp_id)] >= (
                            self.coordinates_y[int(conn.end_comp_id)] + self.y_end_port) - (
                            self.coordinates_y[int(conn.start_comp_id)] + self.y_start_port)
                i += 1

    def __constraint_overlap(self):
        component_list = self.component_ids[:]
        for c1 in self.component_ids:
            self.problem_space += pulp.lpSum([self.x[c1, xv] for xv in self.x_possible]) == 1
            self.problem_space += pulp.lpSum([self.y[c1, yv] for yv in self.y_possible]) == 1

        for c1 in self.component_ids:
            self.coordinates_x[c1] = pulp.lpSum([xv * self.x[(c1, xv)] for xv in self.x_possible])
            self.coordinates_y[c1] = pulp.lpSum([yv * self.y[(c1, yv)] for yv in self.y_possible])

        for c1 in self.component_ids:
            self.problem_space += self.coordinates_x[c1] + self.width[c1] + (self.OFFSET_X//2) <= self.GRID_SIZE
            self.problem_space += self.coordinates_y[c1] + self.height[c1] + (self.OFFSET_Y//2) <= self.GRID_SIZE

            self.problem_space += self.x_max >= self.coordinates_x[c1] + self.width[c1]
            self.problem_space += self.x_min <= self.coordinates_x[c1]
            self.problem_space += self.y_max >= self.coordinates_y[c1] + self.height[c1]
            self.problem_space += self.y_min <= self.coordinates_y[c1]

            for c2 in component_list:
                if c1 != c2:
                    z1 = pulp.LpVariable(f"z1_{c1}_{c2}", cat='Binary')
                    z2 = pulp.LpVariable(f"z2_{c1}_{c2}", cat='Binary')
                    z3 = pulp.LpVariable(f"z3_{c1}_{c2}", cat='Binary')
                    z4 = pulp.LpVariable(f"z4_{c1}_{c2}", cat='Binary')

                    self.problem_space += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{c1}_{c2}"
                    if any(obj_pair.component_ids == [c1,c2] for obj_pair in self.overlap_components["top"]) and any(obj_pair.component_ids == [c1,c2] for obj_pair in self.overlap_components["side"]) and self.overlap:
                        self.problem_space += (self.coordinates_x[c1] + self.width[c1] <= self.coordinates_x[c2]
                                               + self.GRID_SIZE * (1 - z1), f"LeftOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_x[c2] + self.width[c2] <= self.coordinates_x[c1]
                                               + self.GRID_SIZE * (1 - z2), f"RightOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c1] + self.height[c1] <= self.coordinates_y[c2]
                                               + self.GRID_SIZE * (1 - z3), f"Below_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c2] + self.height[c2] <= self.coordinates_y[c1]
                                               + self.GRID_SIZE * (1 - z4), f"Above_{c1}_{c2}")

                    elif any(obj_pair.component_ids == [c1,c2] for obj_pair in self.overlap_components["side"])and self.overlap:
                        self.problem_space += (self.coordinates_x[c1] + self.width[c1] <= self.coordinates_x[c2]
                                               + self.GRID_SIZE * (1 - z1), f"LeftOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_x[c2] + self.width[c2] <= self.coordinates_x[c1]
                                               + self.GRID_SIZE * (1 - z2), f"RightOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c1] + self.height[c1] + self.OFFSET_Y
                                               <= self.coordinates_y[c2] + self.GRID_SIZE * (1 - z3), f"Below_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c2] + self.height[c2] + self.OFFSET_Y
                                               <= self.coordinates_y[c1] + self.GRID_SIZE * (1 - z4), f"Above_{c1}_{c2}")

                    elif any(obj_pair.component_ids == [c1,c2] for obj_pair in self.overlap_components["top"])and self.overlap:
                        self.problem_space += (self.coordinates_x[c1] + self.width[c1] + self.OFFSET_X
                                               <= self.coordinates_x[c2] + self.GRID_SIZE * (1 - z1), f"LeftOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_x[c2] + self.width[c2] + self.OFFSET_X
                                               <= self.coordinates_x[c1] + self.GRID_SIZE * (1 - z2), f"RightOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c1] + self.height[c1] <= self.coordinates_y[c2]
                                               + self.GRID_SIZE * (1 - z3), f"Below_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c2] + self.height[c2] <= self.coordinates_y[c1]
                                               + self.GRID_SIZE * (1 - z4), f"Above_{c1}_{c2}")
                    else:

                        self.problem_space += (self.coordinates_x[c1] + self.width[c1] + self.OFFSET_X
                                               <= self.coordinates_x[c2] + self.GRID_SIZE * (1 - z1), f"LeftOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_x[c2] + self.width[c2] + self.OFFSET_X
                                               <= self.coordinates_x[c1] + self.GRID_SIZE * (1 - z2), f"RightOf_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c1] + self.height[c1]+ self.OFFSET_Y
                                               <= self.coordinates_y[c2] + self.GRID_SIZE * (1 - z3), f"Below_{c1}_{c2}")
                        self.problem_space += (self.coordinates_y[c2] + self.height[c2]+ self.OFFSET_Y
                                               <= self.coordinates_y[c1] + self.GRID_SIZE * (1 - z4), f"Above_{c1}_{c2}")

            component_list.remove(c1)

    def __solve_linear_optimization_problem(self):
        with open("constraints.txt", "w") as f:
            f.write("Constraints in the model:\n")
            for name, constraint in self.problem_space.constraints.items():
                f.write(f"{name}: {constraint}\n")
        self.problem_space += (pulp.lpSum([self.d_x[(c1.start_comp_id, c1.end_comp_id)] +
                                           self.d_y[(c1.start_comp_id, c1.end_comp_id)] for c1 in self.connections])
                               * self.ALPHA + (self.x_max - self.x_min)
                               * self.BETA + (self.y_max - self.y_min) * self.THETA, "totalWireLength")
        # Warm start
        placement_solution_file = f"{self.current_file_directory}/previous_placement_solution.pkl"
        #self.__warm_start(file=placement_solution_file)

        # Solving
        start_solving_time = time.time()
        self.problem_space.solve(self.solver)
        self.logger.info(f"Solving time: {round(time.time() - start_solving_time, 2)}s")

        # Save variables for found solution
        optimal_solution = {var.name: var.varValue for var in self.problem_space.variables()}
        with open(placement_solution_file, "wb") as f:
            pickle.dump(optimal_solution, f)

        self.logger.info(f"Found solution saved to '{placement_solution_file}'")

    def __warm_start(self, file: str):
        """Attempt to use previous solution to speed up solving"""
        try:
            with open(file, "rb") as f:
                loaded_solution = pickle.load(f)

            self.logger.info("Using previous solution to speed up solving")
            variables_dict = self.problem_space.variablesDict()  # access once to save on compute time
            for var_name, var_value in loaded_solution.items():
                if var_name in variables_dict:
                    variables_dict[var_name].setInitialValue(round(var_value, 2))

        except FileNotFoundError:
            self.logger.warning(f"Could not locate '{file}'. Solving time will likely be longer!")

    def __log_results(self):
        self.logger.info(f"Solution status: {pulp.LpStatus[self.problem_space.status]}")

        for i, number_id in enumerate(self.component_ids):
            self.logger.info(f"Component {self.component_names[i]} placed at "
                             f"(x={pulp.value(self.coordinates_x[number_id])}, "
                             f"y={pulp.value(self.coordinates_y[number_id])})")

        total_length = pulp.value(self.problem_space.objective)
        self.logger.info(f"Total wire length: {round(total_length/10, 2)}um")

    def __update_component_info(self):
        for component in self.functional_components:
            component.transform_matrix.set([1, 0, int(round(pulp.value(self.coordinates_x[component.number_id]))), 0, 1,
                                            int(round(pulp.value(self.coordinates_y[component.number_id])))])

    def solve_placement(self):
        self.logger.info("Starting Linear Optimization")

        self.__constraint_overlap()
        self.__constraint_minimize_manhattan_distance()

        if self.MIRROR:
            self.__constrain_mirror()

        if self.RUN:
            self.__solve_linear_optimization_problem()
            self.__log_results()
            self.__update_component_info()

        self.logger.info("Finished Linear Optimization")

        # Add updated functional components back into list of all components
        return self.coordinates_x, self.coordinates_y










