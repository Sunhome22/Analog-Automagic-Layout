# ==================================================================================================================== #
# Copyright (C) 2025 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #

from dataclasses import dataclass
from circuit.circuit_components import Pin, CircuitCell, Transistor, Resistor, Capacitor
from logger.logger import get_a_logger



@dataclass
class Nets:
    applicable_nets: list
    pin_nets: list

    def __init__(self, applicable_nets: list, pin_nets:list):
        self.applicable_nets = applicable_nets
        self.pin_nets = pin_nets


@dataclass
class Overlap:
    instance: str
    component_ids: list


@dataclass
class Connection:
    start_comp_id: str
    start_comp_type: str
    start_area: str
    start_comp_name: str
    end_comp_id: str
    end_comp_type: str
    end_area: str
    end_comp_name: str
    cell: str
    net: str

    def __init__(self, start_comp_id: int|str, start_comp_type: str, start_area: str, start_comp_name: str,
                 end_comp_id: int | str, end_comp_type: str, end_area: str, end_comp_name: str, cell: str, net: str):
        self.start_comp_id = str(start_comp_id)
        self.start_comp_type = start_comp_type
        self.start_area = start_area
        self.start_comp_name = start_comp_name
        self.end_comp_id = str(end_comp_id)
        self.end_comp_type = end_comp_type
        self.end_area = end_area
        self.end_comp_name = end_comp_name
        self.cell = cell
        self.net = net


class ConnectionLists:
    logger = get_a_logger(__name__)

    def __init__(self, input_components):

        self.components = []
        self.pins = []
        for component in input_components:
            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.components.append(component)
            elif isinstance(component, Pin):
                self.pins.append(component)

        self.connections = {
            "local_connections": [],
            "component_connections": [],
            "single_connections": []

        }

        self.overlap_dict = {}
        self.local_con_area = {}
        self.net_list = Nets(applicable_nets=[], pin_nets=[])

    def __local_connection_list(self):

        for obj in self.components:

            ports = obj.schematic_connections

            for key in ports:
                for key1 in ports:

                    if key != key1:
                        entry = [Connection(obj.number_id, obj.type, key, obj.name,
                                            obj.number_id, obj.type, key1, obj.name, obj.cell, ports[key]),
                                 Connection(obj.number_id, obj.type, key1, obj.name,
                                            obj.number_id, obj.type, key, obj.name, obj.cell, ports[key])]
                        if ports[key] == ports[key1] and not any(isinstance(obj, Connection) and obj == target
                                                                 for target in entry
                                                                 for obj in self.connections["local_connections"]):

                            self.connections["local_connections"].append(Connection(obj.number_id, obj.type,
                                                                                    key1, obj.name,
                                                                                    obj.number_id, obj.type, key,
                                                                                    obj.name,  obj.cell, ports[key]))

    def __get_local_connection_area(self, object_id, port):

        for connection in self.connections["local_connections"]:

            if connection.start_comp_id == str(object_id) and (port == connection.start_area or
                                                               port == connection.end_area):
                if connection.start_comp_type == "nmos" or connection.start_comp_type == "pmos":
                    if connection.start_area != "B" and connection.end_area != "B":
                        return connection.start_area + connection.end_area
                else:
                    return connection.start_area + connection.end_area

        return port

    def __connection_list(self):

        object_list = self.components[:]

        for component_1 in object_list:
            for component_2 in object_list:
                conditions = [
                            component_1 != component_2,
                            component_1.cell == component_2.cell
                            ]

                if all(conditions):
                    for port_1 in component_1.schematic_connections:
                        if (port_1 == "B" and isinstance(component_1, Transistor)
                                and (component_1.type == "nmos" or component_1.type == "pmos")):
                            continue

                        for port_2 in component_2.schematic_connections:
                            if (port_2 == "B" and isinstance(component_2, Transistor)
                                    and (component_2.type == "nmos" or component_2.type == "pmos")):
                                continue

                            if component_1.schematic_connections[port_1] == component_2.schematic_connections[port_2]:
                                net = component_1.schematic_connections[port_1]
                                cell = component_1.cell

                                port_1_area = self.__get_local_connection_area(component_1.number_id, port_1)
                                port_2_area = self.__get_local_connection_area(component_2.number_id, port_2)
                                # port_1_area = port_1
                                # port_2_area = port_2
                                entry = [Connection(component_1.number_id, component_1.type, port_1_area,
                                                    component_1.name, component_2.number_id, component_2.type,
                                                    port_2_area, component_2.name, cell, net),
                                         Connection(component_2.number_id, component_2.type, port_2_area,
                                                    component_2.name, component_1.number_id, component_1.type,
                                                    port_1_area, component_1.name, cell, net)]

                                if not any(isinstance(obj, Connection) and obj == target for target in entry
                                           for obj in self.connections["component_connections"]):

                                    self.connections["component_connections"].append(entry[0])

    def __single_connection_list(self):

        for component in self.components:
            for port in component.schematic_connections:
                if (port == "B" and isinstance(component, Transistor)
                        and (component.type == "nmos" or component.type == "pmos")):
                    continue
                in_connection_list = False
                for con in self.connections["component_connections"]:

                    if ((con.start_comp_id == str(component.number_id) and port in con.start_area)
                            or (con.end_comp_id == str(component.number_id) and port in con.end_area)):
                        in_connection_list = True
                        break
                if not in_connection_list:
                    self.connections["single_connections"].append(Connection(component.number_id, component.type, port,
                                                                             component.name, "",
                                                                             "", "",
                                                                             "",
                                                                             component.cell,
                                                                             component.schematic_connections[port]))
                    in_connection_list = False

    def __overlap_transistors(self):
        nmos = []
        pmos = []
        npn = []
        pnp = []
        res = []
        cap = []

        for obj in self.components:

            if isinstance(obj, Capacitor):
                cap.append(obj)
            elif isinstance(obj, Transistor):
                if obj.type == "pmos":
                    pmos.append(obj)
                elif obj.type == "nmos":
                    nmos.append(obj)
                elif obj.type == "npn":
                    npn.append(obj)
                elif obj.type == "pnp":
                    pnp.append(obj)

                else:
                    self.logger.error(f"Unknown transistor type for {obj}")
            if isinstance(obj, Resistor):
                res.append(obj)

        nmos_top, nmos_side = overlap_pairs(nmos, component_type="nmos")
        pmos_top, pmos_side = overlap_pairs(pmos, component_type="pmos")
        res_top, res_side = overlap_pairs(res, component_type="res")
        npn_top, npn_side = overlap_pairs(npn, component_type="npn")
        pnp_top, pnp_side = overlap_pairs(pnp, component_type="pnp")
        cap_top, cap_side = overlap_pairs(cap, component_type="cap")

        self.overlap_dict["cmos"] = {"side": nmos_side + pmos_side,
                                     "top": nmos_top + pmos_top}
        # self.overlap_dict["bipolar"] = {"side": npn_side + pnp_side,
        #                                 "top": npn_top + pnp_top}
        self.overlap_dict["bipolar"] = {"side": [],
                                        "top": []}
        self.overlap_dict["resistor"] = {"side": res_side,
                                         "top": res_top}
        self.overlap_dict["capacitor"] = {"side": cap_side,
                                          "top": cap_top}

    def __get_net_list(self):
        self.logger.info("running get_net_list")
        for obj in self.pins:
            if obj.name not in self.net_list.pin_nets:
                self.net_list.pin_nets.append(obj.name)

        for obj in self.components:
            for port_net in obj.schematic_connections.values():
                if port_net not in self.net_list.applicable_nets + self.net_list.pin_nets:
                    self.net_list.applicable_nets.append(port_net)
        self.net_list.applicable_nets = [item for item in self.net_list.applicable_nets
                                         if item not in self.net_list.pin_nets]

    def get(self):

        self.__local_connection_list()
        self.__connection_list()
        self.__single_connection_list()
        self.__overlap_transistors()
        self.__get_net_list()

        return self.connections, self.overlap_dict, self.net_list


def overlap_pairs(list1, component_type):
    top = []

    side = []

    duplicated_list = list1[:]
    for i in list1:
        for j in duplicated_list:
            if i != j:
                if component_type == "nmos" or component_type == "pmos" or component_type == "npn" or component_type == "res":

                    if (i.type == j.type and (i.bounding_box.x2 - i.bounding_box.x1) ==
                            (j.bounding_box.x2 - j.bounding_box.x1)
                            and i.schematic_connections["B"] == j.schematic_connections["B"]):
                        top.append(Overlap(instance = i.instance, component_ids= [i.number_id, j.number_id]))

                    if i.type == j.type and (i.bounding_box.y2 - i.bounding_box.y1) == (j.bounding_box.y2 - j.bounding_box.y1) and i.schematic_connections["B"] == j.schematic_connections["B"]:
                        side.append(Overlap(instance = i.instance, component_ids = [i.number_id, j.number_id]))

                if component_type == "pnp":
                    if i.type == j.type and (i.bounding_box.x2 - i.bounding_box.x1) == (j.bounding_box.x2 - j.bounding_box.x1) and i.schematic_connections["C"] == j.schematic_connections["C"]:
                        top.append(Overlap(instance=i.instance, component_ids=[i.number_id, j.number_id]))

                    if i.type == j.type and (i.bounding_box.y2 - i.bounding_box.y1) == (j.bounding_box.y2 - j.bounding_box.y1) and i.schematic_connections["C"] == j.schematic_connections["C"]:
                        side.append(Overlap(instance=i.instance, component_ids=[i.number_id, j.number_id]))
                if component_type == "cap":
                    if i.type == j.type and (i.bounding_box.x2 - i.bounding_box.x1) == (
                            j.bounding_box.x2 - j.bounding_box.x1) and i.schematic_connections["A"] == \
                            j.schematic_connections["A"] and i.schematic_connections["B"] == \
                            j.schematic_connections["B"]:
                        top.append(Overlap(instance=i.instance, component_ids=[i.number_id, j.number_id]))

                    if i.type == j.type and (i.bounding_box.y2 - i.bounding_box.y1) == (
                            j.bounding_box.y2 - j.bounding_box.y1) and i.schematic_connections["A"] == \
                            j.schematic_connections["A"] and i.schematic_connections["B"] == \
                            j.schematic_connections["B"]:
                        side.append(Overlap(instance=i.instance, component_ids=[i.number_id, j.number_id]))

        duplicated_list.remove(i)
    return top, side

