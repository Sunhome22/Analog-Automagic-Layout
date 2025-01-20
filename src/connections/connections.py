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

logger = get_a_logger(__name__)

@dataclass
class Connection:
    starting_comp: str
    starting_area: str
    end_comp: str
    end_area: str
    net: str
    def __init__(self, starting_comp: str, starting_area: str, end_comp: str, end_area: str, net: str):

        self.starting_comp = starting_comp
        self.starting_area = starting_area
        self.end_comp = end_comp
        self.end_area = end_area
        self.net = net


class ConnectionLists:

    def __init__(self, components):
        self.components = components


        self.local_connections = []
        self.connections = []
        self.single_connection = []
        self.overlap_dict = {}



    def _local_connection_list(self):

        for obj in self.components:
            if not isinstance(obj, (Pin, CircuitCell)):
                ports = obj.schematic_connections

                for key in ports:
                    for key1 in ports:

                        if key != key1:
                            entry = [Connection(obj.number_id, key, obj.number_id,key1,ports[key]), Connection(obj.number_id, key1, obj.number_id, key, ports[key])]
                            if ports[key] == ports[key1] and not any(isinstance(obj, Connection) and obj == target for target in entry for obj in self.local_connections):
                                self.local_connections.append(Connection(obj.number_id, key, obj.number_id, key1, ports[key]))


    def _connection_list(self):

        object_list = self.components



        i=0
        for object1 in object_list:
            for object2 in object_list:
                if not isinstance(object1, (Pin, CircuitCell)) and not isinstance(object2, (Pin,CircuitCell)):

                    object1_ports = object1.schematic_connections
                    object2_ports = object2.schematic_connections


                    if object1 != object2 and object1.cell == object2.cell:

                        for p1 in object1_ports:
                            element_appended = False
                            for p2 in object2_ports:
                                if object1_ports[p1] == object2_ports[p2]:

                                    entry = [Connection(object1.number_id, p1,  object2.number_id, p2,  object1_ports[p1]),Connection(object2.number_id, p2, object1.number_id, p1, object2_ports[p2])]

                                    if not any(isinstance(obj, Connection) and obj == target for target in entry for obj in self.connections):

                                        self.connections.append(Connection(object1.number_id,p1,object2.number_id, p2, object1_ports[p1]))

                                        element_appended = True


                            if not element_appended:
                                self.single_connection.append(Connection(object1.number_id, p1, "", "", object1_ports[p1]))

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
                    logger.error(f"Transistor type '{obj.type}' not handled yet")


        top, side = overlap_pairs(n_transistors, n_transistors)
        new_top, new_side = overlap_pairs(p_transistors,p_transistors)

        self.overlap_dict["side"] = side + new_side
        self.overlap_dict["top"] = top + new_top
    def initialize_connections(self):
        self._local_connection_list()
        self._connection_list()
        self._overlap_transistors()

        return self.single_connection, self.local_connections, self.connections, self.overlap_dict





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


def overlap_pairs(list1, list2):
    top = []
    side = []
    for i in list1:
        for j in list2:
            if i != j:

                if (i.bounding_box.x2 - i.bounding_box.x1) == (j.bounding_box.x2 - j.bounding_box.x1):
                    top.append([i.number_id, j.number_id])

                if (i.bounding_box.y2 - i.bounding_box.y1) == (j.bounding_box.y2 - j.bounding_box.y1):
                    side.append([i.number_id, j.number_id])
    return top, side

def _remove_duplicates_from_list(dictionary):
    temp = {}

    for key, value in dictionary.items():
        if value not in temp.values():
            temp[key] = value

    return temp