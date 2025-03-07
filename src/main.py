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
from circuit.circuit_spice_parser import SPICEparser
from magic.magic_layout_creator import MagicLayoutCreator
from magic.magic_component_parser import MagicComponentsParser
from json_tool.json_converter import save_to_json, load_from_json
from logger.logger import get_a_logger
from astar.a_star import initiate_astar
from draw_result.draw import draw_result
from linear_optimization.linear_optimization import *
from grid.generate_grid import GridGeneration
from connections.connections import *
from circuit.circuit_components import Transistor


from traces.trace_generate import initiate_write_traces
import os

# ========================================== Set-up classes and constants ==============================================



@dataclass
class ComponentLibrary:
    name: str
    path: str


@dataclass
class ProjectProperties:
    directory: str
    cell_name: str
    lib_name: str
    component_libraries: list[ComponentLibrary]
    main_file_directory: str


# Component libraries
atr_lib = ComponentLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_ATR_SKY130A")
tr_lib = ComponentLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/JNW_TR_SKY130A")
misc_lib = ComponentLibrary(name="AALMISC", path="~/aicex/ip/jnw_bkle_sky130A/design/AAL_COMP_LIBS/AAL_MISC_SKY130A")


project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130A/",
                                       cell_name="JNW_BKLE",
                                       lib_name="JNW_BKLE_SKY130A",
                                       component_libraries=[atr_lib, tr_lib, misc_lib],
                                       main_file_directory=os.path.dirname(os.path.abspath(__file__))
                                       )

# ===================================================== Main ===========================================================
# Define grid size and objects
grid_size = 3000
scale_factor =16
time_limit = 2
draw_name = 'Temporary_check'
trace_width = 30
via_minimum_distance = 20
added_via_size = 7
run_multiple_astar = False
def main():

    # Create a logger
    logger = get_a_logger(__name__)

    # Extracts component information from SPICE file
   # components = SPICEparser(project_properties=project_properties)

    # Update component attributes with information from it's associated Magic files
    #components = MagicComponentsParser(project_properties=project_properties,
     #                                  components=components.get_info()).get_info()
    components = load_from_json(file_name=f"{project_properties.main_file_directory}/results/"f""f"Full_test.json")



    # Algorithms
    con_obj = ConnectionLists(components)
    single_connection, local_connections, connections, overlap_dict, net_list = con_obj.initialize_connections()




   # result = LinearOptimizationSolver(components, connections, local_connections, grid_size, overlap_dict, time_limit)
   # components = result.initiate_solver()


    grid, port_scaled_coordinates, used_area, port_coordinates, routing_sizing_area = GridGeneration(grid_size=grid_size,
                                                                        objects=components,
                                                                        scale=scale_factor,
                                                                        trace_width= trace_width,
                                                                        via_minimum_distance = via_minimum_distance,
                                                                        added_via_size = added_via_size
                                                                     ).initialize_grid_generation()




    path, seg_list = initiate_astar(grid = grid,
                                    connections = connections,
                                    components = components,
                                    port_scaled_coordinates = port_scaled_coordinates,
                                    port_coordinates = port_coordinates,
                                    net_list = net_list,
                                    run_multiple_astar = run_multiple_astar,
                                    routing_sizing_area = routing_sizing_area
                                    )
    components = initiate_write_traces(components = components,
                                       all_paths = path,
                                       scale_factor= scale_factor,
                                       trace_width= trace_width,
                                       used_area= used_area
                                       )

    logger.info("Starting Drawing results")
    #path true:
    #draw_result(grid_size, components, path, used_area, scale_factor, draw_name)
    #path false:
    #draw_result(grid_size, components, connections, used_area)
    logger.info("Finished Drawing results")

    # Create layout
    MagicLayoutCreator(project_properties=project_properties, components=components)

    # Save found components to JSON file
    save_to_json(objects=components, file_name=f"{project_properties.main_file_directory}/results/"
                                          f"Full_test_traces.json")

    # Debug log of all components
    logger.debug(f"Components registered: ")
    for component in components:
        logger.debug(f"- {component}")


if __name__ == '__main__':
    main()



