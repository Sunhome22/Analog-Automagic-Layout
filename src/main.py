#!/pri/leto/Analog-Automagic-Layout/venv/bin/python
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
# ================================================== Libraries =========================================================
from fontTools.misc.bezierTools import rectArea

from circuit.circuit_spice_parser import SPICEparser
from linear_optimization.initiator_lp import LPInitiator
from magic.magic_layout_creator import MagicLayoutCreator
from magic.magic_component_parser import MagicComponentsParser
from json_tool.json_converter import save_to_json, load_from_json
from logger.logger import get_a_logger
from draw_result.draw import draw_result
from linear_optimization.linear_optimization import *
from grid.generate_grid import GridGeneration
from connections.connections import *
from circuit.circuit_components import Transistor, RectArea
from astar.a_star_initiator import AstarInitiator
import cProfile

import os

from traces.trace_generator import TraceGenerator


# ========================================== Set-up classes and constants ==============================================



@dataclass
class ComponentLibrary:
    name: str
    path: str


@dataclass
class ProjectProperties:
    directory: str
    top_cell_name: str
    top_lib_name: str
    component_libraries: list[ComponentLibrary]



# Component libraries
atr_lib = ComponentLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130A/design/JNW_ATR_SKY130A")
tr_lib = ComponentLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130A/design/JNW_TR_SKY130A")
misc_lib = ComponentLibrary(name="AALMISC", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_MISC_SKY130A")


project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130A",
                                       top_cell_name="JNW_BKLE",
                                       top_lib_name="JNW_BKLE_SKY130A",
                                       component_libraries=[atr_lib, tr_lib, misc_lib])


# ===================================================== Main ===========================================================
# Define grid size and objects

def main():

    # Create a logger
    logger = get_a_logger(__name__)

    # # # Extracts component information from SPICE file
    components = SPICEparser(project_properties=project_properties)
    # #
    # # # Update component attributes with information from it's associated Magic files
    components = MagicComponentsParser(project_properties=project_properties,
                                         components=components.get()).get()



    # # Algorithms
    # #components = load_from_json(file_name=f"{os.path.dirname(os.path.abspath(__file__))}/results/SpeedTest.json")
    connections, overlap_dict, net_list= ConnectionLists(input_components = components).get()

    components =  LPInitiator(components, connections,  overlap_dict).initiate_linear_optimization()




    # save_to_json(objects=components, file_name=f"{os.path.dirname(os.path.abspath(__file__))}/results/"
    #                                            f"Components_Placement.json")
    #
    grid, scaled_port_coordinates, used_area, port_coordinates, routing_parameters, component_ports= GridGeneration(components=components).initialize_grid_generation()
    #
    # for obj in components:
    #     if isinstance(obj, CircuitCell):
    #         obj.transform_matrix.set([1, 0, 0, 0, 1, 0])
    #         obj.bounding_box = used_area
    path = AstarInitiator(grid = grid,
                                    connections = connections,
                                    components = components,
                                    scaled_port_coordinates = scaled_port_coordinates,
                                    port_coordinates = port_coordinates,
                                    net_list = net_list,
                                    routing_parameters = routing_parameters,
                                    component_ports = component_ports
                                    ).get()

    #
    #
    #
    components = TraceGenerator(project_properties= project_properties,
                                components = components,
                                paths = path,
                                net_list=net_list,
                                used_area= used_area
                                        ).get()

    # #logger.info("Starting Drawing results")
    # #path true:
    # draw_result( components, path, used_area,  "new_test")
    #path false:
    #draw_result(grid_size, components, connections, used_area)
    #logger.info("Finished Drawing results")

    save_to_json(objects=components, file_name=f"{os.path.dirname(os.path.abspath(__file__))}/results/"
                                               f"Full_test_traces_4.json")



    # Create layout
    MagicLayoutCreator(project_properties=project_properties, components=components)

    # Save found components to JSON file
    save_to_json(objects=components, file_name=f"{os.path.dirname(os.path.abspath(__file__))}/results/"
                                          f"Full_test_traces_3.json")

    # Debug log of all components
    logger.debug(f"Components registered: ")
    for component in components:
        logger.debug(f"- {component}")


if __name__ == '__main__':
    main()



