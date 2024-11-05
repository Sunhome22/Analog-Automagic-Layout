from circuit.circuit_components import Pin, CircuitCell, Transistor
import pulp
class LinearOptimizationSolver:

    PADDING = 30
    UNIT_HEIGHT = 128
    UNIT_WIDTH = 128


    OFFSET_X = 184
    OFFSET_Y = 128

    RUN = True
    def __init__(self, object_info, connections, local_connections, grid_size, overlap_dict):

        self.problem_space = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)
        self.solver = pulp.PULP_CBC_CMD(msg=True, threads=75, timeLimit= 12*60*60)
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

        self.x_pos, self.y_pos, self.x_ov, self.y_ov = self._extract_possible_positions()
        self.x = pulp.LpVariable.dicts("x_bin", [(i,xv) for i in self.objects for xv in self.x_pos], cat="Binary")
        self.y = pulp.LpVariable.dicts("y_bin", [(i, yv) for i in self.objects for yv in self.y_pos], cat="Binary")
        self.x_overlap = pulp.LpVariable.dicts("x_bin_ov", [(i, xv) for i in self.objects for xv in self.x_ov], cat="Binary")
        self.y_overlap = pulp.LpVariable.dicts("y_bin_ov", [(i, yv) for i in self.objects for yv in self.y_ov], cat="Binary")
        self.coordinates_x = {}
        self.coordinates_y = {}


        #bounds
        self.x_min = pulp.LpVariable("x_min", lowBound=0)
        self.x_max = pulp.LpVariable("x_max", lowBound=0)
        self.y_min = pulp.LpVariable("y_min", lowBound=0)
        self.y_max = pulp.LpVariable("y_max", lowBound=0)

        self.d_x = {}
        self.d_y = {}

        #----------------------------------------------Part from constrain rotation ------------------------------------------------------------#

        for o1 in self.object_info:
            if not isinstance(o1, Pin) and not isinstance(o1, CircuitCell):
                self.width[o1.number_id] = o1.bounding_box.x2 - o1.bounding_box.x1
                self.height[o1.number_id] = o1.bounding_box.y2 - o1.bounding_box.y1



    def _extract_possible_positions(self):
        x = []
        y = []
        x_ov = []
        y_ov = []
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

        print(x_intervals)
        print(y_intervals)

        for index, i in enumerate(x_intervals):
            for  x_pos in range(0, self.grid_size-1, i):
                if index == 0:
                    x.append(x_pos)
                    x.append(x_pos + self.PADDING)
                else:
                    x_ov.append(x_pos)

        for index, n in enumerate(y_intervals):
            for y_pos in range(0,self.grid_size-1, n):
                if index == 0:
                    y.append(y_pos)
                    y.append(y_pos + self.PADDING)
                else:
                    y_ov.append(y_pos)



        x = list(set(x))
        y = list(set(y))
        x.sort()
        y.sort()



        return x, y, x_ov, y_ov


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
        for conn in self.connections.values():

            if not conn.end_comp == '' and conn.starting_comp != conn.end_comp:

                start_port_parameters, end_port_parameters = self._get_port_parameters(conn)

                self.d_x[(conn.starting_comp, conn.end_comp)] = pulp.LpVariable(f"d_x_{conn.starting_comp}_{conn.end_comp}_{i}", 0, cat='Continuous')
                self.d_y[(conn.starting_comp, conn.end_comp)] = pulp.LpVariable(f"d_y_{conn.starting_comp}_{conn.end_comp}_{i}", 0, cat='Continuous')

                self.x_start_port = start_port_parameters[0].x2 - (start_port_parameters[0].x1//2)
                self.y_start_port = start_port_parameters[0].y2-(start_port_parameters[0].y1//2)
                self.x_end_port = end_port_parameters[0].x2 - (end_port_parameters[0].x1//2)
                self.y_end_port =  end_port_parameters[0].y2-(end_port_parameters[0].y1//2)

                self.problem_space += self.d_x[(conn.starting_comp, conn.end_comp)] >= (self.coordinates_x[conn.starting_comp] + self.x_start_port) - (self.coordinates_x[conn.end_comp] + self.x_end_port)
                self.problem_space += self.d_x[(conn.starting_comp, conn.end_comp)] >= (self.coordinates_x[conn.end_comp] + self.x_end_port) - (self.coordinates_x[conn.starting_comp] + self.x_start_port)

                self.problem_space += self.d_y[(conn.starting_comp, conn.end_comp)] >= (self.coordinates_y[conn.starting_comp] + self.y_start_port) - (self.coordinates_y[conn.end_comp] + self.y_end_port)
                self.problem_space += self.d_y[(conn.starting_comp, conn.end_comp)] >= (self.coordinates_y[conn.end_comp] + self.y_end_port) - (self.coordinates_y[conn.starting_comp] + self.y_start_port)

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

            if self.width[o1] >= self.UNIT_WIDTH:
                self.problem_space += self.coordinates_x[o1] + self.width[o1] <= self.grid_size
            elif self.height[o1] >= self.UNIT_HEIGHT:
                self.problem_space += self.coordinates_y[o1] + self.height[o1] <= self.grid_size

            self.problem_space += self.x_max >= self.coordinates_x[o1] + self.width[o1]
            self.problem_space += self.x_min <= self.coordinates_x[o1]
            self.problem_space += self.y_max >= self.coordinates_y[o1] + self.height[o1]
            self.problem_space += self.y_min <= self.coordinates_y[o1]

            for o2 in object_list:






                if o1 != o2:
                    z1 = pulp.LpVariable(f"z1_{o1}_{o2}", cat='Binary')
                    z2 = pulp.LpVariable(f"z2_{o1}_{o2}", cat='Binary')
                    z3 = pulp.LpVariable(f"z3_{o1}_{o2}", cat='Binary')
                    z4 = pulp.LpVariable(f"z4_{o1}_{o2}", cat='Binary')

                    self.problem_space += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{o1}_{o2}"

                    self.problem_space += self.coordinates_x[o1] + self.width[o1]  <= self.coordinates_x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}"
                    self.problem_space += self.coordinates_x[o2] + self.width[o2]  <= self.coordinates_x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}"
                    self.problem_space += self.coordinates_y[o1] + self.height[o1]  <= self.coordinates_y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}"
                    self.problem_space += self.coordinates_y[o2] + self.height[o2]  <= self.coordinates_y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}"


            object_list.remove(o1)



    def _solve_linear_optimization_problem(self):
        self.problem_space +=  pulp.lpSum([self.d_x[(o1.starting_comp, o1.end_comp)] + self.d_y[(o1.starting_comp, o1.end_comp)] for o1 in self.connections.values()]) + (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min)+ (self.x_max - self.x_min) + (self.y_max - self.y_min), "totalWireLength"
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
        if self.RUN:
            self._solve_linear_optimization_problem()
            self._print_status()
            self._update_object_info()

        return self.object_info











