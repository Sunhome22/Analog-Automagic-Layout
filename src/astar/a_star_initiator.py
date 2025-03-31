from astar.a_star import AstarAlgorithm
from draw_result.visualize_grid import heatmap_test
from traces.trace_generator import segment_path
from circuit.circuit_components import CircuitCell, Pin
from logger.logger import get_a_logger
import tomllib
import re
from copy import deepcopy
import cProfile
import pstats



class AstarInitiator:
    logger = get_a_logger(__name__)
    TRACE_ON_GRID = 0.9
    def __init__(self, components, grid, connections, port_scaled_coordinates, port_coordinates, net_list,
                 routing_parameters):


        self.config = self.__load_config()
        self.RUN_MULTIPLE_ASTAR = self.config["a_star_initiator"]["RUN_MULTIPLE_ASTAR"]
        self.CUSTOM_NET_ORDER = self.config["a_star_initiator"]["CUSTOM_NET_ORDER"]
        self.NET_ORDER = self.config["a_star_initiator"]["NET_ORDER"]

        self.routing_parameters = routing_parameters
        self.components = components
        self.grid_vertical = deepcopy(grid)
        self.grid_horizontal = deepcopy(grid)
        self.connections = connections
        self.port_scaled_coordinates = port_scaled_coordinates
        self.port_coordinates = port_coordinates
        self.net_list = net_list
        self.goal_nodes = []
        self.real_goal_nodes = []
        self.path = {}
        self.seg_list = {}


    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def __extract_goal_nodes(self, connection_list, net):
        self.goal_nodes = []
        self.real_goal_nodes = []
        for con in connection_list:
            start = None
            end = None
            real_start = None
            real_end = None
            if con.net == net:
                for placed_object in self.components:

                    instance_condition = {
                        "instance": [isinstance(placed_object, (Pin, CircuitCell))]
                    }

                    if not all(instance_condition["instance"]):

                        if placed_object.number_id == int(con.start_comp_id):
                            start = (int(self.port_scaled_coordinates[con.start_comp_id + con.start_area[0]][0]),
                                     int(self.port_scaled_coordinates[con.start_comp_id + con.start_area[0]][2]))
                            real_start = (int(self.port_coordinates[con.start_comp_id + con.start_area[0]][0]),
                                          int(self.port_coordinates[con.start_comp_id + con.start_area[0]][1]))



                        if con.end_comp_id != "" and placed_object.number_id == int(con.end_comp_id):
                            end = (int(self.port_scaled_coordinates[con.end_comp_id + con.end_area[0]][0]),
                                   int(self.port_scaled_coordinates[con.end_comp_id + con.end_area[0]][2]))
                            real_end = (int(self.port_coordinates[con.end_comp_id + con.end_area[0]][0]),
                                        int(self.port_coordinates[con.end_comp_id + con.end_area[0]][1]))


                    break_condition = {
                        "component_connection": [start is not None, end is not None],
                        "single_connection": [start is not None, con.end_comp_id == ""]
                    }
                    if all(break_condition["component_connection"]):

                        if len(con.start_area) >= 2 or len(con.end_area) >= 2:

                            start, real_start, end, real_end = check_start_end_port(con, self.port_scaled_coordinates,
                                                                                    self.port_coordinates)

                        self.goal_nodes.extend([start, end])
                        self.real_goal_nodes.extend([real_start, real_end])

                        break
                    elif all(break_condition["single_connection"]):
                        self.goal_nodes.append(start)
                        self.real_goal_nodes.append(real_start)
                        break

        self.goal_nodes =  list(dict.fromkeys(self.goal_nodes))

        self.real_goal_nodes =  list(dict.fromkeys(self.real_goal_nodes))


    def __lock_or_unlock_port(self, lock):

        h = self.routing_parameters.port_height_scaled
        w = self.routing_parameters.port_width_scaled
        for node in self.goal_nodes:
            for key in self.port_scaled_coordinates:
                if (int(self.port_scaled_coordinates[key][0]), int(self.port_scaled_coordinates[key][2])) == node:
                    w = self.routing_parameters.gate_width_scaled if key[1] == "G" else self.routing_parameters.port_width_scaled

                    break

            for y in range(node[1] - h, node[1] + h + 1):
                for x in range(node[0] - w, node[0] + w + 1):
                    if not self.grid_vertical[y][x] == self.TRACE_ON_GRID:
                        self.grid_vertical[y][x] = lock
                    if not self.grid_horizontal[y][x] == self.TRACE_ON_GRID:
                        self.grid_horizontal[y][x] = lock

    def __update_grid(self, net):

        for segment in self.seg_list[net]:
            # vertical

            if segment[0][0] - segment[-1][0] == 0:

                for x, y in segment:
                    for i in range(-self.routing_parameters.trace_width_scaled,
                                   self.routing_parameters.trace_width_scaled + 1):
                        for p in range(-self.routing_parameters.trace_width_scaled-4, self.routing_parameters.trace_width_scaled +  5):
                            self.grid_vertical[y + p][x + i] = self.TRACE_ON_GRID

            # horizontal
            if segment[0][1] - segment[-1][1] == 0:


                for x, y in segment:
                    for i in range(-self.routing_parameters.trace_width_scaled,
                                   self.routing_parameters.trace_width_scaled + 1):
                        for p in range(-self.routing_parameters.trace_width_scaled-4, self.routing_parameters.trace_width_scaled +5):
                            self.grid_horizontal[y + i][x + p] = self.TRACE_ON_GRID





    def __run_multiple_astar_multiple_times(self, net):
        best_path = None
        best_length = float('inf')
        best_start = None
        path = []
        if self.RUN_MULTIPLE_ASTAR:
            self.logger.info(f"Running A* multiple times for net: {net}")
            for start in self.goal_nodes:
                self.logger.info(f"Starting A* with start node: {start}")
                path, length =AstarAlgorithm(self.grid_vertical, self.grid_horizontal,start, self.goal_nodes,
                                      self.routing_parameters.port_width_scaled).a_star()
                self.logger.info(f"Finished running A* with start node: {start}")

                if path is not None and length < best_length:
                    best_start = start
                    best_path = path
                    best_length = length
            self.logger.info(f"Best start for net: {net} is node: {best_start}")
            return best_path
        else:
            self.logger.info(f"Running A* one time for net: {net}")
            for start in self.goal_nodes:

                path, _ = AstarAlgorithm(self.grid_vertical, self.grid_horizontal, start, self.goal_nodes,
                             self.routing_parameters.port_width_scaled).a_star()

                if not path is None:
                    break
                else:
                    self.logger.info(f"Viable path not found, rerunning with different start node")
            if not path:
                self.logger.info(f"Finished running A* no path found for net: {net}")
            else:
                self.logger.info(f"Finished running A* one time for net: {net}")

            return path



    @staticmethod
    def __check_vdd_vss(net):
        return re.search(".*VSS.*", net, re.IGNORECASE) or re.search(".*VDD.*", net, re.IGNORECASE)

    def __initiate_astar(self):
        self.logger.info("Starting Initiate A*")


        local_net_order = self.NET_ORDER if self.CUSTOM_NET_ORDER else self.net_list.pin_nets + self.net_list.applicable_nets

        for net in local_net_order:
            # Skipping these nets, that are handled by other routing algorithm
            if self.__check_vdd_vss(net):
                continue

            self.logger.info(net)
            self.__extract_goal_nodes(connection_list=self.connections["component_connections"], net=net)

            if len(self.goal_nodes) == 0:
                self.__extract_goal_nodes(connection_list=self.connections["single_connections"], net=net)

            # Make goal nodes walkable
            self.__lock_or_unlock_port(lock=0)

            if len(self.goal_nodes) > 1:
                p = self.__run_multiple_astar_multiple_times(net = net)
            elif len(self.goal_nodes) == 0:
                self.logger.error(f"No goal nodes found in net: {net}")
                p = []
            else:
                self.logger.info(f"No pair of goal nodes found for net: {net}")
                p = []

            self.path.setdefault(net, {})["goal_nodes"] = self.goal_nodes
            self.path.setdefault(net, {})["real_goal_nodes"] = self.real_goal_nodes
            # Make goal nodes non-walkable
            self.__lock_or_unlock_port(lock=1)

            segments = segment_path(p)
            self.path.setdefault(net, {})["segments"] = segments
            self.seg_list.setdefault(net, []).extend(segments)

            self.__update_grid(net=net)

        self.logger.info("Finished A*")

    def get(self):
        self.__initiate_astar()
        return self.path


"""Helper function deciding which of two connected ports should be routed from"""


def check_start_end_port(con, port_scaled_coordinates: dict, port_coordinates: dict):
    start_ports = con.start_area
    end_ports = con.end_area
    port_combinations = {}

    for x in start_ports:
        for y in end_ports:
            point1 = [port_scaled_coordinates[con.start_comp_id + x][0],
                      port_scaled_coordinates[con.start_comp_id + x][2]]
            point2 = [port_scaled_coordinates[con.end_comp_id + y][0], port_scaled_coordinates[con.end_comp_id + y][2]]
            port_combinations[x + y] = sum(abs(a - b) for a, b in zip(point1, point2))

    designated_ports = min(port_combinations, key=port_combinations.get)

    start = (int(port_scaled_coordinates[con.start_comp_id + designated_ports[0]][0]),
             int(port_scaled_coordinates[con.start_comp_id + designated_ports[0]][2]))
    real_start = (int(port_coordinates[con.start_comp_id + designated_ports[0]][0]),
                  int(port_coordinates[con.start_comp_id + designated_ports[0]][1]))
    end = (int(port_scaled_coordinates[con.end_comp_id + designated_ports[1]][0]),
           int(port_scaled_coordinates[con.end_comp_id + designated_ports[1]][2]))
    real_end = (int(port_coordinates[con.end_comp_id + designated_ports[1]][0]),
                int(port_coordinates[con.end_comp_id + designated_ports[1]][1]))

    return start, real_start, end, real_end