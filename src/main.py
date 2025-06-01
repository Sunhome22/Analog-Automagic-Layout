# #!/user_defined_path/Analog-Automagic-Layout/venv/bin/python

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

# ================================================== Libraries =========================================================
from circuit.circuit_spice_parser import SPICEparser
from magic.magic_layout_creator import MagicLayoutCreator
from dataclasses import dataclass, asdict
from magic.magic_component_parser import MagicComponentsParser
from json_converter.json_converter import save_to_json, load_from_json
from drc.drc_checker import DRCchecking
from lvs.lvs_checker import LVSchecking
from traces.generate_astar_path_traces import *
from utils.layout_to_svg import LayoutToSVG
from cell.cell_creator import CellCreator


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


# For use with SKY130

# Component libraries
atr_lib = ComponentLibrary(name="JNWATR", path="~/aicex/ip/jnw_bkle_sky130a/design/JNW_ATR_SKY130A")
tr_lib = ComponentLibrary(name="JNWTR", path="~/aicex/ip/jnw_bkle_sky130a/design/JNW_TR_SKY130A")
misc_lib = ComponentLibrary(name="AALMISC", path="~/aicex/ip/jnw_bkle_sky130a/design/AAL_MISC_SKY130A")


project_properties = ProjectProperties(directory="~/aicex/ip/jnw_bkle_sky130a",
                                       top_cell_name="JNW_BKLE",
                                       top_lib_name="JNW_BKLE_SKY130A",
                                       component_libraries=[atr_lib, tr_lib, misc_lib])

# For use with SG13G2

# Component libraries
# atr_lib = ComponentLibrary(name="LELOATR", path="~/aicex/ip/lelo_bkle_ihp13g2/design/LELO_ATR_IHP13G2")
# tr_lib = ComponentLibrary(name="LELOTR", path="~/aicex/ip/lelo_bkle_ihp13g2/design/LELO_TR_IHP13G2")
#
#
# project_properties = ProjectProperties(directory="~/aicex/ip/lelo_bkle_ihp13g2",
#                                        top_cell_name="LELO_BKLE",
#                                        top_lib_name="LELO_BKLE_IHP13G2",
#                                        component_libraries=[atr_lib, tr_lib])


# ===================================================== Main ===========================================================


def main():
    components = SPICEparser(project_properties=project_properties).get()
    components = MagicComponentsParser(project_properties=project_properties, components=components).get()
    save_to_json(components, file_name="src/results/components_before_cell_creator.json")
    components = CellCreator(project_properties=project_properties, components=components).get()
    MagicLayoutCreator(project_properties=project_properties, components=components)
    save_to_json(components, file_name="src/results/complete_component_info.json")

    DRCchecking(project_properties=project_properties)
    LVSchecking(project_properties=project_properties)


if __name__ == '__main__':
    main()



