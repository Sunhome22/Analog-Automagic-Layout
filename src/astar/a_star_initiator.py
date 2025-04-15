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
from grid.generate_grid import get_obj_id_and_types, check_ignorable_port


class AstarInitiator:
    logger = get_a_logger(__name__)
    TRACE_ON_GRID = 0.9
    def __init__(self, components, grid, connections, scaled_port_coordinates, port_coordinates, net_list,
                 routing_parameters, component_ports):


        self.config = self.__load_config()
        self.RUN_MULTIPLE_ASTAR = self.config["a_star_initiator"]["RUN_MULTIPLE_ASTAR"]
        self.CUSTOM_NET_ORDER = self.config["a_star_initiator"]["CUSTOM_NET_ORDER"]
        self.NET_ORDER = self.config["a_star_initiator"]["NET_ORDER"]
        self.component_ports = component_ports
        self.routing_parameters = routing_parameters
        self.components = components
        self.grid_vertical = deepcopy(grid)
        self.grid_horizontal = deepcopy(grid)
        self.connections = connections
        self.scaled_port_coordinates = scaled_port_coordinates
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
                            start = (self.scaled_port_coordinates[con.start_comp_id + con.start_comp_type+ con.start_area[0]].x,
                                     self.scaled_port_coordinates[con.start_comp_id + con.start_comp_type+ con.start_area[0]].y)
                            real_start = (self.port_coordinates[con.start_comp_id + con.start_comp_type + con.start_area[0]].x,
                                          self.port_coordinates[con.start_comp_id + con.start_comp_type+ con.start_area[0]].y)



                        if con.end_comp_id != "" and placed_object.number_id == int(con.end_comp_id):
                            end = (self.scaled_port_coordinates[con.end_comp_id + con.end_comp_type + con.end_area[0]].x,
                                   self.scaled_port_coordinates[con.end_comp_id + con.end_comp_type + con.end_area[0]].y)
                            real_end = (self.port_coordinates[con.end_comp_id + con.end_comp_type + con.end_area[0]].x,
                                        self.port_coordinates[con.end_comp_id + con.end_comp_type + con.end_area[0]].y)


                    break_condition = {
                        "component_connection": [start is not None, end is not None],
                        "single_connection": [start is not None, con.end_comp_id == ""]
                    }
                    if all(break_condition["component_connection"]):

                        if len(con.start_area) >= 2 or len(con.end_area) >= 2:

                            start, real_start, end, real_end = check_start_end_port(con, self.scaled_port_coordinates,
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
        object_type = None
        port_type = None
        object_id = None
        h = 0
        w = 0
        for node in self.goal_nodes:
            for key in self.scaled_port_coordinates:
                if (self.scaled_port_coordinates[key].x, self.scaled_port_coordinates[key].y) == node:

                    object_id, object_type, port_type = get_obj_id_and_types(key)
                    if not object_type or not object_id or not port_type:
                        self.logger.error("Could not find port type, object id or object type")

                    break
            component_types = ["nmos", "pmos", "npn", "pnp", "mim", "vpp", "hpo", "xhpo"]

            if object_type == "nmos" or object_type == "pmos":
                if check_ignorable_port(self.logger,components=self.components, object_id = object_id, port = port_type ):
                    sizing = getattr(self.component_ports.cmos, "V"+port_type)
                else:
                    sizing = getattr(self.component_ports.cmos, port_type)
                h = sizing.height
                w = sizing.width
            elif object_type == "npn" or object_type == "pnp":
                sizing = getattr(self.component_ports.bipolar, port_type)
                h = sizing.height
                w = sizing.width
            elif object_type == "mim" or object_type == "vpp":
                sizing = getattr(self.component_ports.capacitor, port_type)
                h = sizing.height
                w = sizing.width
            elif object_type == "hpo" or object_type == "xhpo":
                sizing = getattr(self.component_ports.resistor, port_type)
                h = sizing.height
                w = sizing.width
            else:
                self.logger.error("No matching component type")

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
                            if y+p < len(self.grid_vertical)-1 and x+i < len(self.grid_vertical[0])-1:
                                self.grid_vertical[y + p][x + i] = self.TRACE_ON_GRID

            # horizontal
            if segment[0][1] - segment[-1][1] == 0:


                for x, y in segment:
                    for i in range(-self.routing_parameters.trace_width_scaled,
                                   self.routing_parameters.trace_width_scaled + 1):
                        for p in range(-self.routing_parameters.trace_width_scaled-4, self.routing_parameters.trace_width_scaled +5):
                            if y + i < len(self.grid_horizontal)-1 and x + p < len(self.grid_horizontal[0])-1:
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
                                      self.routing_parameters.minimum_segment_length).a_star()
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
                             self.routing_parameters.minimum_segment_length).a_star()

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


def check_start_end_port(con, scaled_port_coordinates: dict, port_coordinates: dict):
    start_ports = con.start_area
    end_ports = con.end_area
    port_combinations = {}

    for x in start_ports:
        for y in end_ports:
            point1 = [scaled_port_coordinates[con.start_comp_id+con.start_comp_type + x].x,
                      scaled_port_coordinates[con.start_comp_id+con.start_comp_type + x].y]
            point2 = [scaled_port_coordinates[con.end_comp_id+con.end_comp_type + y].x,
                      scaled_port_coordinates[con.end_comp_id+con.end_comp_type + y].y]
            port_combinations[x + y] = sum(abs(a - b) for a, b in zip(point1, point2))

    designated_ports = min(port_combinations, key=port_combinations.get)

    start = (scaled_port_coordinates[con.start_comp_id + con.start_comp_type + designated_ports[0]].x,
             scaled_port_coordinates[con.start_comp_id + con.start_comp_type + designated_ports[0]].y)
    real_start = (port_coordinates[con.start_comp_id + con.start_comp_type + designated_ports[0]].x,
                  port_coordinates[con.start_comp_id + con.start_comp_type + designated_ports[0]].y)
    end = (scaled_port_coordinates[con.end_comp_id + con.end_comp_type + designated_ports[1]].x,
           scaled_port_coordinates[con.end_comp_id + con.end_comp_type + designated_ports[1]].y)
    real_end = (port_coordinates[con.end_comp_id + con.end_comp_type + designated_ports[1]].x,
                port_coordinates[con.end_comp_id + con.end_comp_type + designated_ports[1]].y)

    return start, real_start, end, real_end