#!/pri/bjs1/Analog-Automagic-Layout/venv/bin/python
# #!/home/bjorn/Analog-Automagic-Layout/venv/bin/python

import re
from cell.cell_creator import CellCreator

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
from traces import generate_astar_path_traces
from drc.drc_checker import DRCchecking
from lvs.lvs_checker import LVSchecking
from collections import defaultdict

from traces.generate_astar_path_traces import *
import os
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


def main():
    components = SPICEparser(project_properties=project_properties).get()
    components = MagicComponentsParser(project_properties=project_properties, components=components).get()
    save_to_json(components, file_name="src/results/temp_components_before_cell_creator.json")

    components = CellCreator(project_properties=project_properties, components=components).get()
    MagicLayoutCreator(project_properties=project_properties, components=components)
    save_to_json(components, file_name="src/results/complete_component_info.json")

    DRCchecking(project_properties=project_properties)
    LVSchecking(project_properties=project_properties)


if __name__ == '__main__':
    main()



