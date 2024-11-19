from fontTools.varLib.models import subList

from circuit.circuit_components import Pin, CircuitCell, Transistor
import pulp


def _element_in_sublist(element, big_list):
    for small_list in big_list:
        if element in small_list:
            return True
    return False


class LinearOptimizationSolver:

    UNIT_HEIGHT = 100
    UNIT_WIDTH = 64

    OFFSET_X = 184
    OFFSET_Y = 128

    MIRROR =True

    RUN = True

    def __init__(self, object_info, connections, local_connections, grid_size, overlap_dict):

        self.problem_space = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)
        self.solver = pulp.PULP_CBC_CMD(msg=True, threads=75, timeLimit=2* 60)
        self.object_info = object_info
        self.objects = []
        self.overlap_dict = overlap_dict

        for obj in self.object_info:
            if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
                self.objects.append(obj.number_id)

        self.connections = connections
        self.local_connections = local_connections
        self.grid_size = grid_size
        self.width = {}
        self.height = {}
        if self.MIRROR:
            self.mirrored_objects = self._check_mirrored_components()



        self.x_pos, self.y_pos = self._extract_possible_positions()
        self.x = pulp.LpVariable.dicts("x_bin", [(i, xv) for i in self.objects for xv in self.x_pos], cat="Binary")
        self.y = pulp.LpVariable.dicts("y_bin", [(i, yv) for i in self.objects for yv in self.y_pos], cat="Binary")

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

        # ----------------------------------------------Part from constrain rotation ------------------------------------------------------------#

        for o1 in self.object_info:
            if not isinstance(o1, Pin) and not isinstance(o1, CircuitCell):
                self.width[o1.number_id] = o1.bounding_box.x2 - o1.bounding_box.x1
                self.height[o1.number_id] = o1.bounding_box.y2 - o1.bounding_box.y1

    def _check_mirrored_components(self):
        mirrored_objects = []
        comp = self.object_info[:]

        for obj in self.object_info:
            group = []
            for obj1 in comp:
                if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell) and not isinstance(obj1, Pin) and not isinstance(obj1, CircuitCell):
                    if obj.group == obj1.group and obj != obj1 and obj.group is not None:

                        group.append([obj,obj1])
            if len(group) == 1 and ([group[0][1],group[0][0]]) not in mirrored_objects:
                mirrored_objects.append([group[0][0],group[0][1]])
                comp.remove(group[0][0])
                comp.remove(group[0][1])

        #Faux mirrored objects:

        for obj in self.object_info:
            group = []
            if not _element_in_sublist(obj, mirrored_objects):
                for obj1 in comp:
                    if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell) and not isinstance(obj1,Pin) and not isinstance(obj1, CircuitCell):
                        if [obj.number_id,obj1.number_id] in self.overlap_dict["top"] and [obj.number_id,obj1.number_id] in self.overlap_dict["side"]:
                            group.append([obj, obj1])
                            break

                if len(group) == 1:
                    if ([group[0][0], group[0][1]]) not in mirrored_objects and ([group[0][1],group[0][0]]) not in mirrored_objects:
                        mirrored_objects.append([group[0][0], group[0][1]])



        return mirrored_objects

    def _constrain_mirror(self):
        if self.MIRROR:
            for obj in self.mirrored_objects:

                self.problem_space += self.coordinates_x[obj[0].number_id] + self.width[obj[0].number_id] == self.grid_size - self.coordinates_x[obj[1].number_id]
                self.problem_space += self.coordinates_y[obj[0].number_id] ==  self.coordinates_y[obj[1].number_id]

    def _extract_possible_positions(self):
        x = []
        y = []
        x_intervals = []
        y_intervals = []

        x_intervals.append(self.UNIT_WIDTH)
        y_intervals.append(self.UNIT_HEIGHT)

        for obj in self.object_info:
            if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell) and isinstance(obj, Transistor):
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

        for o in self.object_info:

            if o.number_id == obj.starting_comp:

                for p in o.layout_ports:
                    if len(obj.starting_area) > 1:
                        if p.type == obj.starting_area[0] or p.type == obj.starting_area[1]:
                            port_parameter.append(p.area)
                    elif p.type == obj.starting_area:
                        port_parameter.append(p.area)

            if o.number_id == obj.end_comp:
                for p in o.layout_ports:
                    if len(obj.end_area) > 1:

                        if p.type == obj.end_area[0] or p.type == obj.end_area[1]:
                            port_parameter2.append(p.area)
                    elif p.type == obj.end_area:
                        port_parameter2.append(p.area)

        return port_parameter, port_parameter2

    def _constraint_minimize_manhattan_distance(self):
        i = 0
        for conn in self.connections.values():

            if not conn.end_comp == '' and conn.starting_comp != conn.end_comp:
                start_port_parameters, end_port_parameters = self._get_port_parameters(conn)

                self.d_x[(conn.starting_comp, conn.end_comp)] = pulp.LpVariable(
                    f"d_x_{conn.starting_comp}_{conn.end_comp}_{i}", 0, cat='Continuous')
                self.d_y[(conn.starting_comp, conn.end_comp)] = pulp.LpVariable(
                    f"d_y_{conn.starting_comp}_{conn.end_comp}_{i}", 0, cat='Continuous')

                self.x_start_port = start_port_parameters[0].x2 - (start_port_parameters[0].x1 // 2)
                self.y_start_port = start_port_parameters[0].y2 - (start_port_parameters[0].y1 // 2)
                self.x_end_port = end_port_parameters[0].x2 - (end_port_parameters[0].x1 // 2)
                self.y_end_port = end_port_parameters[0].y2 - (end_port_parameters[0].y1 // 2)

                self.problem_space += self.d_x[(conn.starting_comp, conn.end_comp)] >= (
                            self.coordinates_x[conn.starting_comp] + self.x_start_port) - (
                                                  self.coordinates_x[conn.end_comp] + self.x_end_port)
                self.problem_space += self.d_x[(conn.starting_comp, conn.end_comp)] >= (
                            self.coordinates_x[conn.end_comp] + self.x_end_port) - (
                                                  self.coordinates_x[conn.starting_comp] + self.x_start_port)

                self.problem_space += self.d_y[(conn.starting_comp, conn.end_comp)] >= (
                            self.coordinates_y[conn.starting_comp] + self.y_start_port) - (
                                                  self.coordinates_y[conn.end_comp] + self.y_end_port)
                self.problem_space += self.d_y[(conn.starting_comp, conn.end_comp)] >= (
                            self.coordinates_y[conn.end_comp] + self.y_end_port) - (
                                                  self.coordinates_y[conn.starting_comp] + self.y_start_port)

                i += 1

    def _constraint_overlap(self):

        object_list = self.objects[:]

        for o1 in self.objects:
            self.problem_space += pulp.lpSum([self.x[o1, xv] for xv in self.x_pos]) == 1
            self.problem_space += pulp.lpSum([self.y[o1, yv] for yv in self.y_pos]) == 1

        for o1 in self.objects:
            self.coordinates_x[o1] = pulp.lpSum([xv * self.x[(o1, xv)] for xv in self.x_pos])
            self.coordinates_y[o1] = pulp.lpSum([yv * self.y[(o1, yv)] for yv in self.y_pos])

        for o1 in self.objects:
            self.problem_space += self.coordinates_x[o1] + self.width[o1] + (self.OFFSET_X//2)   <= self.grid_size
            self.problem_space += self.coordinates_y[o1] + self.height[o1]  + (self.OFFSET_Y//2) <= self.grid_size

            self.problem_space += self.x_max >= self.coordinates_x[o1] + self.width[o1]
            self.problem_space += self.x_min <= self.coordinates_x[o1]
            self.problem_space += self.y_max >= self.coordinates_y[o1] + self.height[o1]
            self.problem_space += self.y_min <= self.coordinates_y[o1]

            for o2 in object_list:

                #if o1 != o2 and [(o1,o2) ]not in self.mirrored_objects :
                if o1 != o2:
                    z1 = pulp.LpVariable(f"z1_{o1}_{o2}", cat='Binary')
                    z2 = pulp.LpVariable(f"z2_{o1}_{o2}", cat='Binary')
                    z3 = pulp.LpVariable(f"z3_{o1}_{o2}", cat='Binary')
                    z4 = pulp.LpVariable(f"z4_{o1}_{o2}", cat='Binary')

                    self.problem_space += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{o1}_{o2}"
                    if [o1,o2] in self.overlap_dict["top"] and [o1,o2] in self.overlap_dict["side"]:
                        self.problem_space += self.coordinates_x[o1] + self.width[o1]  <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_x[o2] + self.width[o2] <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o1] + self.height[o1]  <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o2] + self.height[o2]  <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}"

                    elif [o1,o2] in self.overlap_dict["side"]:
                        self.problem_space += self.coordinates_x[o1] + self.width[o1]  <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_x[o2] + self.width[o2] <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o1] + self.height[o1] + self.OFFSET_Y  <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o2] + self.height[o2] + self.OFFSET_Y  <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}"

                    elif [o1,o2] in self.overlap_dict["top"]:
                        self.problem_space += self.coordinates_x[o1] + self.width[o1] + self.OFFSET_X  <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_x[o2] + self.width[o2] + self.OFFSET_X  <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o1] + self.height[o1] <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o2] + self.height[o2]  <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}"
                    else:

                        self.problem_space += self.coordinates_x[o1] + self.width[o1] +self.OFFSET_X <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_x[o2] + self.width[o2] +self.OFFSET_X <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o1] + self.height[o1]+self.OFFSET_Y <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}"
                        self.problem_space += self.coordinates_y[o2] + self.height[o2]+self.OFFSET_Y <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}"

            object_list.remove(o1)



    def _solve_linear_optimization_problem(self):
       # self.problem_space += pulp.lpSum(
        #    [self.d_x[(o1.starting_comp, o1.end_comp)] + self.d_y[(o1.starting_comp, o1.end_comp)] for o1 in
         #    self.connections.values()]) + (self.x_max - self.x_min) * 10000000, "totalWireLength"
        self.problem_space += pulp.lpSum(
            [self.d_x[(o1.starting_comp, o1.end_comp)] + self.d_y[(o1.starting_comp, o1.end_comp)] for o1 in
            self.connections.values()])*0.001 +(self.x_max - self.x_min) *100  , "totalWireLength"
        self.problem_space.solve(self.solver)

    def _print_status(self):
        print(f"[INFO] Solution status: {pulp.LpStatus[self.problem_space.status]}")
        print("this is self.objects")
        print(self.objects)
        for obj in self.objects:
            print(f"[INFO] Object {obj}")
            print(
                f"[INFO] Object {obj} is placed at ({pulp.value(self.coordinates_x[obj])}, {pulp.value(self.coordinates_y[obj])})")

        total_length = pulp.value(self.problem_space.objective)

        print("These are the mirrored pairs:")
        i = 1
        for obj in self.mirrored_objects:
            print(f"Pair {i}")
            print(obj[0].number_id)
            print(obj[1].number_id)
        print(f"[INFO] Total wire length: {total_length}")

    def _update_object_info(self):
        for obj in self.object_info:
            if not isinstance(obj, Pin) and not isinstance(obj, CircuitCell):
                obj.transform_matrix.a = 1
                obj.transform_matrix.b = 0
                obj.transform_matrix.c = int(pulp.value(self.coordinates_x[obj.number_id]))
                obj.transform_matrix.d = 0
                obj.transform_matrix.e = 1
                obj.transform_matrix.f = int(pulp.value(self.coordinates_y[obj.number_id]))

    def initiate_solver(self):

        self._constraint_overlap()
        self._constraint_minimize_manhattan_distance()
        if self.MIRROR:
            self._constrain_mirror()
        if self.RUN:
            self._solve_linear_optimization_problem()
            self._print_status()
            self._update_object_info()


        return self.object_info











