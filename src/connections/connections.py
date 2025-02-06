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

from dataclasses import dataclass
from circuit.circuit_components import Pin, CircuitCell, Transistor
from logger.logger import get_a_logger


@dataclass
class Nets:
    applicable_nets:list
    pin_nets: list

    def __init__(self, applicable_nets: list, pin_nets:list):
        self.applicable_nets = applicable_nets
        self.pin_nets = pin_nets

@dataclass
class Connection:
    start_comp_id: str
    start_area: str
    start_comp_name: str
    end_comp_id: str
    end_area: str
    end_comp_name: str
    cell: str
    net: str
    def __init__(self, start_comp_id: str, start_area: str, start_comp_name: str, end_comp_id: str, end_area: str, end_comp_name: str, cell: str, net: str):

        self.start_comp_id = str(start_comp_id)
        self.start_area = start_area
        self.start_comp_name = start_comp_name
        self.end_comp_id = str(end_comp_id)
        self.end_area = end_area
        self.end_comp_name = end_comp_name
        self.cell = cell
        self.net = net


class ConnectionLists:

    def __init__(self, components):
        self.logger = get_a_logger(__name__)
        self.components = components


        self.local_connections = []
        self.component_connections = []
        self.single_connection = []
        self.overlap_dict = {}
        self.local_con_area = {}
        self.net_list = Nets(applicable_nets=[], pin_nets=[])

    def _update_local_nets(self, object_id: int, start_port: str, end_port: str):
        if object_id not in self.local_con_area:
            self.local_con_area[object_id] = start_port + end_port
        elif isinstance(self.local_con_area[object_id],list):
            self.local_con_area[object_id].append(start_port+end_port)
        else:
            self.local_con_area[object_id] = [self.local_con_area[object_id], start_port+end_port]

    def _local_connection_list(self):

        for obj in self.components:
            if not isinstance(obj, (Pin, CircuitCell)):
                ports = obj.schematic_connections

                for key in ports:
                    for key1 in ports:

                        if key != key1:
                            entry = [Connection(obj.number_id, key, obj.name, obj.number_id, obj.name, obj.cell, key1,ports[key]),
                                     Connection(obj.number_id, key1, obj.name, obj.number_id, key, obj.name, obj.cell, ports[key])]
                            if ports[key] == ports[key1] and not any(isinstance(obj, Connection) and obj == target for target in entry for obj in self.local_connections):
                                self.local_connections.append(Connection(obj.number_id, key, obj.name, obj.number_id, key1, obj.name, obj.cell, "local:"+ports[key]))

                                self._update_local_nets(obj.number_id, key, key1)



    def _connection_list(self):

        object_list = self.components
        test_run = 0
        for object1 in object_list:
            for object2 in object_list:

                if not isinstance(object1, (Pin, CircuitCell)) and not isinstance(object2, (Pin,CircuitCell)):

                    if object1 != object2 and object1.cell == object2.cell:
                        object1_ports = object1.schematic_connections
                        object2_ports = object2.schematic_connections

                        for p1 in object1_ports:
                            element_appended = False
                            local_net_obj1 = p1

                            for p2 in object2_ports:
                                local_net_obj2 = p2
                                if object1_ports[p1] == object2_ports[p2]:

                                    if object1.number_id in self.local_con_area:
                                        
                                        if isinstance(self.local_con_area[object1.number_id], list):

                                            index = next((index for index, item in enumerate(self.local_con_area[object1.number_id]) if p1 or "local:"+p1 in item), None)

                                            local_net_obj1 = self.local_con_area[object1.number_id][index]

                                        elif p1 in self.local_con_area[object1.number_id]:
                                            local_net_obj1 = self.local_con_area[object1.number_id]
                                        else:
                                            local_net_obj1 = p1
                                    if object2.number_id in self.local_con_area:
                                        if isinstance(self.local_con_area[object2.number_id], list):
                                            index = next((index for index, item in enumerate(self.local_con_area[object2.number_id]) if p2 or "local:"+p2 in item), None)
                                            local_net_obj2 = self.local_con_area[object2.number_id][index]
                                        elif p2 in self.local_con_area[object2.number_id]:
                                            local_net_obj2 = self.local_con_area[object2.number_id]
                                        else:
                                            local_net_obj2 = p2

                                    entry = [Connection(object1.number_id, local_net_obj1, object1.name, object2.number_id, local_net_obj2, object2.name, object1.cell, object1_ports[p1]),
                                             Connection(object2.number_id, local_net_obj2, object2.name, object1.number_id, local_net_obj1, object1.name, object1.cell, object2_ports[p2])]

                                    if not any(isinstance(obj, Connection) and obj == target for target in entry for obj in self.component_connections):

                                        self.component_connections.append(Connection(object1.number_id,local_net_obj1, object1.name, object2.number_id, local_net_obj2, object2.name, object1.cell, object1_ports[p1]))

                                        element_appended = True



                            if not element_appended:
                                self.single_connection.append(Connection(object1.number_id, p1, object1.name,"", "", "", object1.cell, object1_ports[p1]))

    def _overlap_transistors(self):
        n_transistors = []
        p_transistors = []

        for obj in self.components:
            if isinstance(obj, Transistor):
                if obj.type == "pmos":
                    p_transistors.append(obj)
                elif obj.type== "nmos":
                    n_transistors.append(obj)
                else:
                    self.logger.error(f"Transistor type '{obj.type}' not handled yet")


        top, side = overlap_pairs(n_transistors)
        new_top, new_side = overlap_pairs(p_transistors)

        self.overlap_dict["side"] = side + new_side
        self.overlap_dict["top"] = top + new_top

    def _get_net_list(self):
        for obj in self.components:
            if isinstance(obj, Pin):
                self.net_list.pin_nets.append(obj.name)
            elif not isinstance(obj, CircuitCell):
                for port_net in obj.schematic_connections.values():
                    if port_net not in self.net_list.applicable_nets:
                        self.net_list.applicable_nets.append(port_net)
        self.net_list.applicable_nets = [item for item in self.net_list.applicable_nets if item not in self.net_list.pin_nets]



    def initialize_connections(self):

        self._local_connection_list()
        self._connection_list()
        self._overlap_transistors()
        self._get_net_list()



        return self.single_connection, self.local_connections, self.component_connections, self.overlap_dict, self.net_list





###----------Usikker på om denne blir brukt---------------####
def diff_components(components):
    diff_pairs = []
    comp = components[:]
    for obj in components:
        for obj1 in comp:
            if obj.group == obj1.group and "diff" in obj.type:
                diff_pairs.append([obj, obj1])
        comp.remove(obj)
    return diff_pairs


def overlap_pairs(list1):
    top = []
    side = []
    duplicated_list = list1[:]
    for i in list1:
        for j in duplicated_list:
            if i != j:

                if (i.bounding_box.x2 - i.bounding_box.x1) == (j.bounding_box.x2 - j.bounding_box.x1) and i.schematic_connections["B"] == j.schematic_connections["B"]:
                    top.append([i.number_id, j.number_id])

                if (i.bounding_box.y2 - i.bounding_box.y1) == (j.bounding_box.y2 - j.bounding_box.y1) and i.schematic_connections["B"] == j.schematic_connections["B"]:
                    side.append([i.number_id, j.number_id])
        duplicated_list.remove(i)
    return top, side

