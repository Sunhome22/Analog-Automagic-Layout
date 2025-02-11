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
from circuit.circuit_components import Pin, CircuitCell, Transistor
from logger.logger import get_a_logger
import time
import pickle
import pyscipopt
import os


class LinearOptimizationSolver:

    UNIT_HEIGHT = 100
    UNIT_WIDTH = 64

    OFFSET_X = 184
    OFFSET_Y = 128

    ALPHA = 0.001
    BETA = 100
    THETA = 1

    MIRROR = True
    RUN = True

    def __init__(self, components, connections, local_connections, grid_size, overlap_dict):
        self.logger = get_a_logger(__name__)
        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))
        self.problem_space = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)
        self.solver = pulp.SCIP_PY(msg=False, warmStart=True, options=["limits/gap=0.05"]) # early stopping tolerance
        self.components = components
        self.component_ids = []
        self.component_names = []
        self.overlap_dict = overlap_dict

        for component in self.components:
            if not isinstance(component, (Pin,CircuitCell)):
                self.component_ids.append(component.number_id)
                self.component_names.append(component.name)

        self.connections = connections
        self.local_connections = local_connections
        self.grid_size = grid_size
        self.width = {}
        self.height = {}

        if self.MIRROR:
            self.mirrored_objects = self._check_mirrored_components()

        self.x_pos, self.y_pos = self._extract_possible_positions()
        self.x = pulp.LpVariable.dicts("x_bin", [(i, xv) for i in self.component_ids for xv in self.x_pos], cat="Binary")
        self.y = pulp.LpVariable.dicts("y_bin", [(i, yv) for i in self.component_ids for yv in self.y_pos], cat="Binary")

        self.coordinates_x = {}
        self.coordinates_y = {}
        self.test_var = pulp.LpVariable("test_var", lowBound=0)

        # bounds
        self.x_min = pulp.LpVariable("x_min", lowBound=0)
        self.x_max = pulp.LpVariable("x_max", lowBound=0)
        self.y_min = pulp.LpVariable("y_min", lowBound=0)
        self.y_max = pulp.LpVariable("y_max", lowBound=0)

        self.d_x = {}
        self.d_y = {}

        # ---------------------------------------- Part from constrain rotation -------------------------------------- #
        for o1 in self.components:
            if not isinstance(o1, (Pin, CircuitCell)):
                self.width[o1.number_id] = o1.bounding_box.x2 - o1.bounding_box.x1
                self.height[o1.number_id] = o1.bounding_box.y2 - o1.bounding_box.y1

    def _check_mirrored_components(self):
        mirrored_objects = []
        comp = self.components[:] # shallow copy

        for component in self.components:
            group = []
            for obj1 in comp:
                if not isinstance(component, (Pin, CircuitCell)) and not isinstance(obj1, (Pin, CircuitCell)):
                    if component.group == obj1.group and component != obj1 and component.group is not None:
                        group.append([component,obj1])

            if len(group) == 1 and ([group[0][1],group[0][0]]) not in mirrored_objects:
                mirrored_objects.append([group[0][0],group[0][1]])
                comp.remove(group[0][0])
                comp.remove(group[0][1])

        #Faux mirrored objects:

        for component in self.components:
            group = []
            if not _element_in_sublist(component, mirrored_objects):
                for obj1 in comp:
                    if not isinstance(component, (Pin, CircuitCell)) and not isinstance(obj1, (Pin, CircuitCell)):
                        if ([component.number_id,obj1.number_id] in self.overlap_dict["top"]
                                and [component.number_id,obj1.number_id] in self.overlap_dict["side"]):
                            group.append([component, obj1])
                            break

                if len(group) == 1:
                    if (([group[0][0], group[0][1]]) not in mirrored_objects
                            and ([group[0][1],group[0][0]]) not in mirrored_objects):
                        mirrored_objects.append([group[0][0], group[0][1]])

        return mirrored_objects

    def _constrain_mirror(self):
        if self.MIRROR:
            for obj in self.mirrored_objects:

                self.problem_space += (self.coordinates_x[obj[0].number_id] + self.width[obj[0].number_id] == self.grid_size - self.coordinates_x[obj[1].number_id])
                self.problem_space += self.coordinates_y[obj[0].number_id] == self.coordinates_y[obj[1].number_id]

    def _extract_possible_positions(self):
        x = []
        y = []
        x_intervals = []
        y_intervals = []

        x_intervals.append(self.UNIT_WIDTH)
        y_intervals.append(self.UNIT_HEIGHT)

        for obj in self.components:
            if isinstance(obj, Transistor):
                h = obj.bounding_box.y2 - obj.bounding_box.y1
                w = obj.bounding_box.x2 - obj.bounding_box.x1
                if w not in x_intervals:
                    x_intervals.append(w)
                if h not in y_intervals:
                    y_intervals.append(h)

        for index, i in enumerate(x_intervals):
            for x_pos in range(self.grid_size//2, self.grid_size - 1, i):

                x.append(x_pos)

            for x_pos in range(self.grid_size // 2, 0, -i):
                x.append(x_pos)

        for index, n in enumerate(y_intervals):
            for y_pos in range(self.grid_size//2, self.grid_size - 1, n):

                y.append(y_pos)
            for y_pos in range(self.grid_size//2, 0, -n):

                y.append(y_pos)

        x = list(set(x))
        y = list(set(y))
        x.sort()
        y.sort()

        return x, y

    def _get_port_parameters(self, obj):
        # staring off utilizing the first point in connections area as point of contact
        port_parameter = []
        port_parameter2 = []

        for o in self.components:

            if o.number_id == int(obj.start_comp_id):

                for p in o.layout_ports:
                    if len(obj.start_area) > 1:
                        if p.type == obj.start_area[0] or p.type == obj.start_area[1]:
                            port_parameter.append(p.area)
                    elif p.type == obj.start_area:
                        port_parameter.append(p.area)

            if o.number_id == int(obj.end_comp_id):
                for p in o.layout_ports:
                    if len(obj.end_area) > 1:

                        if p.type == obj.end_area[0] or p.type == obj.end_area[1]:
                            port_parameter2.append(p.area)
                    elif p.type == obj.end_area:
                        port_parameter2.append(p.area)

        return port_parameter, port_parameter2

    def _constraint_minimize_manhattan_distance(self):
        i = 0
        for conn in self.connections:

            if not conn.end_comp_id == '' and conn.start_comp_id != conn.end_comp_id:
                start_port_parameters, end_port_parameters = self._get_port_parameters(conn)

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

    def _constraint_overlap(self):
        component_list = self.component_ids[:]

        for o1 in self.component_ids:
            self.problem_space += pulp.lpSum([self.x[o1, xv] for xv in self.x_pos]) == 1
            self.problem_space += pulp.lpSum([self.y[o1, yv] for yv in self.y_pos]) == 1

        for o1 in self.component_ids:
            self.coordinates_x[o1] = pulp.lpSum([xv * self.x[(o1, xv)] for xv in self.x_pos])
            self.coordinates_y[o1] = pulp.lpSum([yv * self.y[(o1, yv)] for yv in self.y_pos])

        for o1 in self.component_ids:
            self.problem_space += self.coordinates_x[o1] + self.width[o1] + (self.OFFSET_X//2) <= self.grid_size
            self.problem_space += self.coordinates_y[o1] + self.height[o1]  + (self.OFFSET_Y//2) <= self.grid_size

            self.problem_space += self.x_max >= self.coordinates_x[o1] + self.width[o1]
            self.problem_space += self.x_min <= self.coordinates_x[o1]
            self.problem_space += self.y_max >= self.coordinates_y[o1] + self.height[o1]
            self.problem_space += self.y_min <= self.coordinates_y[o1]

            for o2 in component_list:

                #if o1 != o2 and [(o1,o2) ]not in self.mirrored_objects :
                if o1 != o2:
                    z1 = pulp.LpVariable(f"z1_{o1}_{o2}", cat='Binary')
                    z2 = pulp.LpVariable(f"z2_{o1}_{o2}", cat='Binary')
                    z3 = pulp.LpVariable(f"z3_{o1}_{o2}", cat='Binary')
                    z4 = pulp.LpVariable(f"z4_{o1}_{o2}", cat='Binary')

                    self.problem_space += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{o1}_{o2}"
                    if [o1,o2] in self.overlap_dict["top"] and [o1,o2] in self.overlap_dict["side"]:
                        self.problem_space += (self.coordinates_x[o1] + self.width[o1]  <= self.coordinates_x[o2]
                                               + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_x[o2] + self.width[o2] <= self.coordinates_x[o1]
                                               + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o1] + self.height[o1]  <= self.coordinates_y[o2]
                                               + self.grid_size * (1 - z3), f"Below_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o2] + self.height[o2]  <= self.coordinates_y[o1]
                                               + self.grid_size * (1 - z4), f"Above_{o1}_{o2}")

                    elif [o1,o2] in self.overlap_dict["side"]:
                        self.problem_space += (self.coordinates_x[o1] + self.width[o1]  <= self.coordinates_x[o2]
                                               + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_x[o2] + self.width[o2] <= self.coordinates_x[o1]
                                               + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o1] + self.height[o1] + self.OFFSET_Y
                                               <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o2] + self.height[o2] + self.OFFSET_Y
                                               <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}")

                    elif [o1,o2] in self.overlap_dict["top"]:
                        self.problem_space += (self.coordinates_x[o1] + self.width[o1] + self.OFFSET_X
                                               <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_x[o2] + self.width[o2] + self.OFFSET_X
                                               <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o1] + self.height[o1] <= self.coordinates_y[o2]
                                               + self.grid_size * (1 - z3), f"Below_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o2] + self.height[o2]  <= self.coordinates_y[o1]
                                               + self.grid_size * (1 - z4), f"Above_{o1}_{o2}")
                    else:

                        self.problem_space += (self.coordinates_x[o1] + self.width[o1] +self.OFFSET_X
                                               <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_x[o2] + self.width[o2] +self.OFFSET_X
                                               <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o1] + self.height[o1]+self.OFFSET_Y
                                               <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}")
                        self.problem_space += (self.coordinates_y[o2] + self.height[o2]+self.OFFSET_Y
                                               <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}")

            component_list.remove(o1)

    def _solve_linear_optimization_problem(self):
       # self.problem_space += pulp.lpSum(
       #    [self.d_x[(o1.start_comp_id, o1.end_comp_id)] + self.d_y[(o1.start_comp_id, o1.end_comp_id)] for o1 in
       #    self.connections.values()]) + (self.x_max - self.x_min) * 10000000, "totalWireLength"


        self.problem_space += (pulp.lpSum( [self.d_x[(o1.start_comp_id, o1.end_comp_id)] +
                                            self.d_y[(o1.start_comp_id, o1.end_comp_id)] for o1 in
                                            self.connections]) * self.ALPHA + (self.x_max - self.x_min)
                               * self.BETA + (self.y_max - self.y_min) * self.THETA , "totalWireLength")

        # Warm start
        placement_solution_file = f"{self.current_file_directory}/previous_placement_solution.pkl"
        self.warm_start(file=placement_solution_file)

        # Solving
        start_solving_time = time.time()
        self.problem_space.solve(self.solver)
        self.logger.info(f"Solving time: {round(time.time() - start_solving_time, 2)}s")

        # Save variables for found solution
        optimal_solution = {var.name: var.varValue for var in self.problem_space.variables()}
        with open(placement_solution_file, "wb") as f:
            pickle.dump(optimal_solution, f)

        self.logger.info(f"Found solution saved to '{placement_solution_file}'")

    def warm_start(self, file: str):
        """Attempt to use previous solution to speed up solving"""
        try:
            with open(file, "rb") as f:
                loaded_solution = pickle.load(f)

            self.logger.info("Using previous solution to speed up solving")
            variables_dict = self.problem_space.variablesDict() # access once to save time
            for var_name, var_value in loaded_solution.items():
                if var_name in variables_dict:
                    variables_dict[var_name].setInitialValue(round(var_value, 2))

        except FileNotFoundError:
            self.logger.warning(f"Could not locate '{file}'. Solving time will likely be longer!")

    def _print_status(self):
        self.logger.info(f"Solution status: {pulp.LpStatus[self.problem_space.status]}")

        for i, number_id in enumerate(self.component_ids):

            self.logger.info(f"Component {self.component_names[i]} placed at (x={pulp.value(self.coordinates_x[number_id])}, "
                             f"y={pulp.value(self.coordinates_y[number_id])})")

        total_length = pulp.value(self.problem_space.objective)
        self.logger.info(f"Total wire length: {round(total_length/10,2)}um")

    def _update_object_info(self):
        for component in self.components:
            if not isinstance(component, (Pin, CircuitCell)):
                component.transform_matrix.a = 1
                component.transform_matrix.b = 0
                component.transform_matrix.c = int(pulp.value(self.coordinates_x[component.number_id]))
                component.transform_matrix.d = 0
                component.transform_matrix.e = 1
                component.transform_matrix.f = int(pulp.value(self.coordinates_y[component.number_id]))

    def solve_placement(self):
        self.logger.info("Starting Linear Optimization")

        self._constraint_overlap()
        self._constraint_minimize_manhattan_distance()

        if self.MIRROR:
            self._constrain_mirror()
        if self.RUN:
            self._solve_linear_optimization_problem()
            self._print_status()
            self._update_object_info()

        self.logger.info("Finished Linear Optimization")
        return self.components

def _element_in_sublist(element, big_list):
    for small_list in big_list:
        if element in small_list:
            return True
    return False










