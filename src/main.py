#!/pri/bjs1/Analog-Automagic-Layout/venv/bin/python
import re

from cell.cell_creator import CellCreator
# #!/home/bjorn/Analog-Automagic-Layout/venv/bin/python
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
from dataclasses import dataclass, asdict
from magic.magic_component_parser import MagicComponentsParser
from json_converter.json_converter import save_to_json, load_from_json
from logger.logger import get_a_logger
from circuit.circuit_components import TraceNet, RectAreaLayer, RectArea
from draw_result.draw import draw_result
from linear_optimization.linear_optimization import *
from grid.generate_grid import *
from connections.connections import *
from traces import trace_generator
from traces.trace_generate import initiate_write_traces
from drc.drc_checker import DRCchecking
from lvs.lvs_checker import LVSchecking
from collections import defaultdict

from traces.trace_generator import *
import os
# ========================================== Set-up classes and constants ==============================================

grid_size = 4500
scale_factor = 8
draw_name = 'Temporary_check'

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


def main():
    # Create a logger
    logger = get_a_logger(__name__)
    run = True

    if run:
        # Extracts component information from SPICE file
        components = SPICEparser(project_properties=project_properties).get()

        # Updates component attributes with information from it's associated Magic files
        components = MagicComponentsParser(project_properties=project_properties, components=components).get()
        save_to_json(components, file_name="src/json_converter/components_temp_before_cell_creator.json")

        #components = CellCreator(project_properties=project_properties, components=components).get()
        #save_to_json(components, file_name="src/json_converter/components_with_traces_update_1.json")
        #MagicLayoutCreator(project_properties=project_properties, components=components)

        #
        #
        #     print(component.cell, component.parent_cell_chain)

        #Figures out connection types, nets and components that can overlap


        # path, seg_list = initiate_astar(
        #     grid=grid,
        #     connections=connections,
        #    local_connections=local_connections,
        #     components=components,
        #     port_scaled_coords=port_scaled_coords,
        #     net_list=net_list)

        # components = initiate_write_traces(components, path, port_coord, seg_list, scale_factor, net_list)
        # # MagicLayoutCreator(project_properties=project_properties, components=components)
        #
        # # temp setting
        # i = 0
        # for component in components:
        #     if isinstance(component, CircuitCell):
        #         i += 1
        #         component.transform_matrix.set([1, 0, i*1000, 0, 1, i*1000])
        #         component.bounding_box.set(used_area)

        #  draw_result(grid_size=grid_size, objects=components, used_area=used_area, scale_factor=scale_factor,
        #                         draw_name=draw_name)

        # Update components with trace information
        # components = TraceGenerator(components=components, project_properties=project_properties).get()

        # Create layout
        # MagicLayoutCreator(project_properties=project_properties, components=components)

        # DRC handling
        # DRCchecking(project_properties=project_properties)

        # LVS handling
        # LVSchecking(project_properties=project_properties)

    else:
        components = load_from_json(file_name="src/json_converter/components_with_traces_update_1.json")
        #components = load_from_json(file_name="src/json_converter/components_for_comp_circuit_lvs_clean.json")
        # Update components with trace information
        # components = TraceGenerator(components=components, project_properties=project_properties).get()

        # Create layout
        MagicLayoutCreator(project_properties=project_properties, components=components)

        # # DRC handling
        # DRCchecking(project_properties=project_properties)
        #
        # # LVS handling
        # LVSchecking(project_properties=project_properties)
        #
        #
        #
        # used_area = 0
        # for component in components:
        #     if isinstance(component, CircuitCell):
        #         used_area = component.bounding_box
        #
        # draw_result(grid_size=grid_size, objects=components, used_area=used_area, scale_factor=scale_factor,
        #            draw_name=draw_name)
        # #save_to_json(components, file_name="src/json_converter/components_test.json")
        # # Debug log of all components
        # logger.debug(f"Components registered: ")
        # for component in components:
        #     logger.debug(f"- {component}")

        save_to_json(components, file_name="src/json_converter/components_complete.json")
if __name__ == '__main__':
    main()



