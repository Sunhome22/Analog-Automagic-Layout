import pulp
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from AstarPathAlgorithm import *
from SimplifyPath import *


class LinearOptimizationSolver1:
    def __init__(self, objects, connections, grid_size, height, width, padding):
        self.problem_space = pulp.LpProblem("ObjectPlacementWithSizes", pulp.LpMinimize)
        self.solver = pulp.PULP_CBC_CMD(msg=True, threads=50, timeLimit=300)

        self.objects = objects
        self.connections = connections
        self.grid_size = grid_size
        self.height = height
        self.width = width
        self.padding = padding

        self.rotated_width = {}
        self.rotated_height = {}

        self.x = pulp.LpVariable.dicts("x", self.objects, 0, grid_size-1, cat='Integer')
        self.y = pulp.LpVariable.dicts("y", self.objects, 0, grid_size-1, cat='Integer')
        self.x_min = pulp.LpVariable("x_min", lowBound=0)
        self.x_max = pulp.LpVariable("x_max", lowBound=0)
        self.y_min = pulp.LpVariable("y_min", lowBound=0)
        self.y_max = pulp.LpVariable("y_max", lowBound=0)
        self.d_x = {}
        self.d_y = {}



    def constraint_rotation(self):
        for o1 in self.objects:
            # Decision variables: rotation
            r0 = pulp.LpVariable(f"r0_{o1}", self.objects, cat='Binary')
            r90 = pulp.LpVariable(f"r90_{o1}", self.objects, cat='Binary')
            r180 = pulp.LpVariable(f"r180_{o1}", self.objects, cat='Binary')
            r270 = pulp.LpVariable(f"r270_{o1}", self.objects, cat='Binary')

            self.problem_space += r0 + r90 + r180 + r270 == 1, f"OneRotation_object_{o1}"
            self.rotated_width[o1] = r0 * self.width[o1] + r90 * self.height[o1] + r180 * self.width[o1] + r270 * self.height[o1]
            self.rotated_height[o1] = r0 * self.height[o1] + r90 * self.width[o1] + r180 * self.height[o1] + r270 * self.width[o1]

    def constraint_minimize_manhattan_distance(self):

        for o1, o2 in self.connections:
            self.d_x[(o1, o2)] = pulp.LpVariable(f"d_x_{o1}_{o2}", 0)
            self.d_y[(o1, o2)] = pulp.LpVariable(f"d_y_{o1}_{o2}", 0)

            self.problem_space += self.d_x[(o1, o2)] >= self.x[o1] - self.x[o2]
            self.problem_space += self.d_x[(o1, o2)] >= self.x[o2] - self.x[o1]

            self.problem_space += self.d_y[(o1, o2)] >= self.y[o1] - self.y[o2]
            self.problem_space += self.d_y[(o1, o2)] >= self.y[o2] - self.y[o1]

    def constraint_overlap(self):


        for o1 in self.objects:
            for o2 in self.objects:
                if o1 != o2:
                    z1 = pulp.LpVariable(f"z1_{o1}_{o2}", cat='Binary')
                    z2 = pulp.LpVariable(f"z2_{o1}_{o2}", cat='Binary')
                    z3 = pulp.LpVariable(f"z3_{o1}_{o2}", cat='Binary')
                    z4 = pulp.LpVariable(f"z4_{o1}_{o2}", cat='Binary')

                    self.problem_space += z1 + z2 + z3 + z4 == 1, f"NonOverlap_{o1}_{o2}"

                    self.problem_space += self.x[o1] + self.rotated_width[o1] + self.padding <= self.x[o2] + self.grid_size * (1 - z1), f"LeftOf_{o1}_{o2}"
                    self.problem_space += self.x[o2] + self.rotated_width[o2] + self.padding <= self.x[o1] + self.grid_size * (1 - z2), f"RightOf_{o1}_{o2}"
                    self.problem_space += self.y[o1] + self.rotated_height[o1] + self.padding <= self.y[o2] + self.grid_size * (1 - z3), f"Below_{o1}_{o2}"
                    self.problem_space += self.y[o2] + self.rotated_height[o2] + self.padding <= self.y[o1] + self.grid_size * (1 - z4), f"Above_{o1}_{o2}"

                    self.problem_space += self.x[o1] + self.rotated_width[o1] <= self.grid_size
                    self.problem_space += self.x[o2] + self.rotated_width[o2] <= self.grid_size
                    self.problem_space += self.y[o1] + self.rotated_height[o1] <= self.grid_size
                    self.problem_space += self.y[o2] + self.rotated_height[o2] <= self.grid_size

                    self.problem_space += self.x_max >= self.x[o1]
                    self.problem_space += self.x_max >= self.x[o2]
                    self.problem_space += self.x_min <= self.x[o2]
                    self.problem_space += self.x_min <= self.x[o1]

                    self.problem_space += self.y_max >= self.y[o1]
                    self.problem_space += self.y_max >= self.y[o2]
                    self.problem_space += self.y_min <= self.y[o2]
                    self.problem_space += self.y_min <= self.y[o1]


    def solve_linear_optimization_problem(self):
        self.problem_space += pulp.lpSum([self.d_x[(o1, o2)] + self.d_y[(o1, o2)] for o1, o2 in self.connections]) + (self.x_max - self.x_min) + (
                    self.x_max - self.x_min) + (self.y_max - self.y_min) + (self.y_max - self.y_min), "totalWireLength"
        print(self.problem_space)
        self.problem_space.solve(self.solver)

    def print_status(self):
        print(f"[INFO] Solution status: {pulp.LpStatus[self.problem_space.status]}")

        for obj in self.objects:
            print(f"[INFO] Object {obj} is placed at ({pulp.value(self.x[obj])}, {pulp.value(self.y[obj])})")


        total_length = pulp.value(self.problem_space.objective)
        print(f"[INFO] Total wire length: {total_length}")


    def initiate_solver(self):
        self.constraint_minimize_manhattan_distance()
        self.constraint_rotation()
        self.constraint_overlap()
        self.solve_linear_optimization_problem()
        self.print_status()
        return self.x, self.y, self.rotated_width, self.rotated_width




