

from path.a_star import *

from circuit.circuit_components import Pin


class LinearOptimizationSolver:

    UNIT_HEIGHT = 400
    UNIT_WIDTH = 540
    ROTATION_ENABLE = False
    PADDING = 0

    def __init__(self, object_info, connections, local_connections, grid_size):

        self.problem_space = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)
        self.solver = pulp.PULP_CBC_CMD(msg=True, threads=50)
        self.object_info = object_info
        self.objects = []


        for obj in self.object_info:
            if not isinstance(obj, Pin):
                self.objects.append(obj.number_id)
        print("this is self.objects")
        print(self.objects)
        self.connections = connections
        self.local_connections = local_connections
        self.grid_size = grid_size
        self.rotated_width = {}
        self.rotated_height = {}

        #self.x = pulp.LpVariable.dicts("x", self.objects, 0, grid_size-1, cat='Integer')
        #self.y = pulp.LpVariable.dicts("y", self.objects, 0, grid_size-1, cat='Integer')


        self.x_pos, self.y_pos = self._extract_possible_positions()

        self.x = pulp.LpVariable.dicts("x_bin", [(i,xv) for i in self.objects for xv in self.x_pos], cat="Binary")
        self.y = pulp.LpVariable.dicts("y_bin", [(i, yv) for i in self.objects for yv in self.y_pos], cat="Binary")
        self.coordinates_x = {}
        self.coordinates_y = {}

        if self.ROTATION_ENABLE:
            self.r0 = (pulp.LpVariable.dicts(f"r0", self.objects, cat='Binary'))
            self.r90 = pulp.LpVariable.dicts(f"r90", self.objects, cat='Binary')
            self.r180 = pulp.LpVariable.dicts(f"r180", self.objects, cat='Binary')
            self.r270 = pulp.LpVariable.dicts(f"r270", self.objects, cat='Binary')

        self.x_min = pulp.LpVariable("x_min", lowBound=0)
        self.x_max = pulp.LpVariable("x_max", lowBound=0)
        self.y_min = pulp.LpVariable("y_min", lowBound=0)
        self.y_max = pulp.LpVariable("y_max", lowBound=0)
        self.d_x = {}
        self.d_y = {}


    def _extract_possible_positions(self):
        x = []
        y = []

        for  x_pos in range(0, self.grid_size-1, self.UNIT_WIDTH):
            x.append(x_pos)

        for y_pos in range(0,self.grid_size-1, self.UNIT_HEIGHT):
            y.append(y_pos)

        return x, y

    def _constraint_rotation(self):
        for o1 in self.object_info:
            if not isinstance(o1, Pin):

            # Decision variables: rotation


                width = o1.bounding_box.x2 - o1.bounding_box.x1
                height = o1.bounding_box.y2 - o1.bounding_box.y1
                if self.ROTATION_ENABLE:
                    self.problem_space += self.r0[o1.number_id] + self.r90[o1.number_id] + self.r180[o1.number_id] + self.r270[o1.number_id] == 1, f"OneRotation_object_{o1.number_id}"
                    self.rotated_width[o1.number_id] = self.r0[o1.number_id] * width + self.r90[o1.number_id] * height + self.r180[o1.number_id] * width + self.r270[o1.number_id] * height
                    self.rotated_height[o1.number_id] = self.r0[o1.number_id] * height + self.r90[o1.number_id] * width + self.r180[o1.number_id] * height + self.r270[o1.number_id] * width
                else:
                    self.rotated_width[o1.number_id] = width
                    self.rotated_height[o1.number_id] = height
    def _get_port_parameters(self, obj):
        #staring off utilizing the first point in connections area as point of contact
        port_parameter = []
        port_parameter2 = []


        for o in self.object_info:

            if o.number_id == obj.starting_comp:

                for  p in o.layout_ports:
                    if len(obj.starting_area)>1:
                        if p.type == obj.starting_area[0] or p.type == obj.starting_area[1]:
                            port_parameter.append(p.area)
                    elif p.type == obj.starting_area:
                        port_parameter.append(p.area)

            if o.number_id == obj.end_comp:
                for p in o.layout_ports:
                    if len(obj.end_area)>1:

                        if p.type == obj.end_area[0] or p.type == obj.end_area[1]:
                            port_parameter2.append(p.area)
                    elif p.type == obj.end_area:
                        port_parameter2.append(p.area)


        return port_parameter, port_parameter2

    def _constraint_minimize_manhattan_distance(self):
        i = 0
        for o1 in self.connections.values():

            if not o1.end_comp == '' and o1.starting_comp != o1.end_comp:

                start_port_parameters, end_port_parameters = self._get_port_parameters(o1)

                self.d_x[(o1.starting_comp, o1.end_comp)] = pulp.LpVariable(f"d_x_{o1.starting_comp}_{o1.end_comp}_{i}", 0, cat='Continuous')
                self.d_y[(o1.starting_comp, o1.end_comp)] = pulp.LpVariable(f"d_y_{o1.starting_comp}_{o1.end_comp}_{i}", 0, cat='Continuous')
                self.x_start_port = pulp.LpVariable(f"x_start_port_{o1.starting_comp}_{i}", 0, cat='Continuous')
                self.y_start_port = pulp.LpVariable(f"y_start_port_{o1.starting_comp}_{i}", 0, cat='Continuous')
                self.x_end_port = pulp.LpVariable(f"x_end_port_{o1.end_comp}_{i}", 0, cat='Continuous')
                self.y_end_port = pulp.LpVariable(f"y_end_port_{o1.end_comp}_{i}", 0, cat='Continuous')


                self.problem_space += self.x_start_port <= (start_port_parameters[0].x2 - start_port_parameters[0].x1)
                self.problem_space += self.y_start_port <= (start_port_parameters[0].y2-start_port_parameters[0].y1)

                self.problem_space += self.x_end_port <= (end_port_parameters[0].x2 - end_port_parameters[0].x1)
                self.problem_space += self.y_end_port <= (end_port_parameters[0].y2-end_port_parameters[0].y1)



                self.problem_space += self.d_x[(o1.starting_comp, o1.end_comp)] >= (self.coordinates_x[o1.starting_comp] + self.x_start_port) - (self.coordinates_x[o1.end_comp] + self.x_end_port)
                self.problem_space += self.d_x[(o1.starting_comp, o1.end_comp)] >= (self.coordinates_x[o1.end_comp] + self.x_end_port) - (self.coordinates_x[o1.starting_comp] + self.x_start_port)

                self.problem_space += self.d_y[(o1.starting_comp, o1.end_comp)] >= (self.coordinates_y[o1.starting_comp] + self.y_start_port) - (self.coordinates_y[o1.end_comp] + self.y_end_port)
                self.problem_space += self.d_y[(o1.starting_comp, o1.end_comp)] >= (self.coordinates_y[o1.end_comp] + self.y_end_port) - (self.coordinates_y[o1.starting_comp] + self.y_start_port)

                i += 1

    def _constraint_overlap(self):

        object_list = self.objects[:]

        for o1 in self.objects:
            self.problem_space += pulp.lpSum([self.x[o1, xv] for xv in self.x_pos]) == 1
            self.problem_space += pulp.lpSum([self.y[o1, yv] for yv in self.y_pos]) == 1

        for o1 in self.objects:
            self.coordinates_x[o1] = pulp.lpSum([xv * self.x[(o1, xv)] for xv in self.x_pos])

            self.coordinates_y[o1] = pulp.lpSum([yv * self.y[(o1, yv)] for yv in self.y_pos])



        # for i in self.objects:
        #     for j in object_list:
        #         for k in self.x_pos:
        #             for p in self.y_pos:
        #
        #
        #                 if i != j:
        #
        #
        #                     self.problem_space += self.x[i,k] + self.x[j,k] + self.y[i,p] + self.y[j,p] <= 3
        #     object_list.remove(i)

       # object_list = self.objects
        for o1 in self.objects:


            self.problem_space += self.coordinates_x[o1] + self.rotated_width[o1] <= self.grid_size
            self.problem_space += self.coordinates_y[o1] + self.rotated_height[o1] <= self.grid_size
            # self.problem_space += self.x_max >= self.coordinates_x[o1] + self.rotated_width[o1]
            # self.problem_space += self.x_min <= self.coordinates_x[o1]
            # self.problem_space += self.y_max >= self.coordinates_y[o1] + self.rotated_height[o1]
            # self.problem_space += self.y_min <= self.coordinates_y[o1]
            for o2 in object_list:
                if o1 != o2:
                    z1 = pulp.LpVariable(f"z1_{o1}_{o2}", cat='Binary')
                    z2 = pulp.LpVariable(f"z2_{o1}_{o2}", cat='Binary')
                    z3 = pulp.LpVariable(f"z3_{o1}_{o2}", cat='Binary')
                    z4 = pulp.LpVariable(f"z4_{o1}_{o2}", cat='Binary')

                    self.problem_space += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{o1}_{o2}"

                    self.problem_space += self.coordinates_x[o1] + self.rotated_width[o1] + self.PADDING <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}"
                    self.problem_space += self.coordinates_x[o2] + self.rotated_width[o2] + self.PADDING <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}"
                    self.problem_space += self.coordinates_y[o1] + self.rotated_height[o1] + self.PADDING <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}"
                    self.problem_space += self.coordinates_y[o2] + self.rotated_height[o2] + self.PADDING <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}"


            object_list.remove(o1)



    def _solve_linear_optimization_problem(self):
      #  self.problem_space += pulp.lpSum([self.d_x[(o1.starting_comp, o1.end_comp)] + self.d_y[(o1.starting_comp, o1.end_comp)] for o1 in self.connections.values()]) + (self.x_max - self.x_min) + (
       #             self.x_max - self.x_min) + (self.y_max - self.y_min) + (self.y_max - self.y_min), "totalWireLength"

        self.problem_space += pulp.lpSum(
          [self.d_x[(o1.starting_comp, o1.end_comp)] + self.d_y[(o1.starting_comp, o1.end_comp)] for o1 in
           self.connections.values()]), "totalWireLength"
        self.problem_space.solve(self.solver)

    def _print_status(self):
        print(f"[INFO] Solution status: {pulp.LpStatus[self.problem_space.status]}")
        print("this is self.objects")
        print(self.objects)
        for obj in self.objects:
            print(f"[INFO] Object {obj}")
            print(f"[INFO] Object {obj} is placed at ({pulp.value(self.coordinates_x[obj])}, {pulp.value(self.coordinates_y[obj])})")


        total_length = pulp.value(self.problem_space.objective)
        print(f"[INFO] Total wire length: {total_length}")

    def _update_object_info(self):
        for obj in self.object_info:
            if not isinstance(obj, Pin):
                if not self.ROTATION_ENABLE:
                    obj.transform_matrix.a = 1
                    obj.transform_matrix.b = 0
                    obj.transform_matrix.c = int(pulp.value(self.coordinates_x[obj.number_id]))
                    obj.transform_matrix.d = 0
                    obj.transform_matrix.e = 1
                    obj.transform_matrix.f = int(pulp.value(self.coordinates_y[obj.number_id]))
                else:
                    if pulp.value(self.r0[obj.number_id]) == 1:
                        obj.transform_matrix.a = 1
                        obj.transform_matrix.b = 0
                        obj.transform_matrix.c = int(pulp.value(self.x[obj.number_id]))
                        obj.transform_matrix.d = 0
                        obj.transform_matrix.e = 1
                        obj.transform_matrix.f = int(pulp.value(self.x[obj.number_id]))
                    elif pulp.value(self.r90[obj.number_id]) == 1:
                        obj.transform_matrix.a = 0
                        obj.transform_matrix.b = 1
                        obj.transform_matrix.c = int(pulp.value(self.rotated_width[obj.number_id]) + pulp.value(self.x[obj.number_id]))
                        obj.transform_matrix.d = -1
                        obj.transform_matrix.e = 0
                        obj.transform_matrix.f = int(pulp.value(self.rotated_height[obj.number_id]) + pulp.value(self.y[obj.number_id]))
                    elif pulp.value(self.r180[obj.number_id]) == 1:
                        obj.transform_matrix.a = -1
                        obj.transform_matrix.b = 0
                        obj.transform_matrix.c = int(pulp.value(self.rotated_width[obj.number_id]) + pulp.value(self.x[obj.number_id]))
                        obj.transform_matrix.d = 0
                        obj.transform_matrix.e = -1
                        obj.transform_matrix.f = int(pulp.value(self.rotated_height[obj.number_id]) + pulp.value(self.y[obj.number_id]))

                    elif pulp.value(self.r270[obj.number_id]) == 1:
                        obj.transform_matrix.a = 0
                        obj.transform_matrix.b = -1
                        obj.transform_matrix.c = int(pulp.value(self.rotated_width[obj.number_id]) + pulp.value(self.x[obj.number_id]))
                        obj.transform_matrix.d = 1
                        obj.transform_matrix.e = 0
                        obj.transform_matrix.f = int(pulp.value(self.rotated_height[obj.number_id]) + pulp.value(self.y[obj.number_id]))

                    else:
                        print("[ERROR]: Rotation Variable not found")
                        print("[ERROR]: for variable: ")
                        print(obj)
                        print("[END ERROR] ")



    def initiate_solver(self):
        self._constraint_rotation()
        self._constraint_overlap()
        self._constraint_minimize_manhattan_distance()




        self._solve_linear_optimization_problem()
        self._print_status()
        self._update_object_info()

        return self.object_info











