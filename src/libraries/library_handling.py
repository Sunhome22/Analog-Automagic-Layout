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
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, TraceNet, \
    RectAreaLayer
from logger.logger import get_a_logger
import tomllib
import re
import libraries.atr_sky130a_lib as atr
import libraries.tr_sky130a_lib as tr
import libraries.aal_misc_sky130a_lib as aal_misc

# ============================================ ATR SKY130A Handling ====================================================


class LibraryHandling:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties, components, functional_component_order):
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.structural_components = []
        self.functional_components = []
        self.transistor_components = []
        self.aal_misc_mim_capacitor_components = []
        self.circuit_cell = CircuitCell()
        self.components = components
        self.functional_component_order = functional_component_order

        # Load config
        self.config = self.__load_config()
        self.INIT_RAIL_RING_OFFSET_X = self.config["generate_rail_traces"]["INIT_RAIL_RING_OFFSET_X"]
        self.INIT_RAIL_RING_OFFSET_Y = self.config["generate_rail_traces"]["INIT_RAIL_RING_OFFSET_Y"]
        self.RAIL_RING_OFFSET = self.config["generate_rail_traces"]["RAIL_RING_OFFSET"]
        self.RAIL_RING_WIDTH = self.config["generate_rail_traces"]["RAIL_RING_WIDTH"]
        self.RELATIVE_COMPONENT_PLACEMENT = self.config["initiator_lp"]["RELATIVE_COMPONENT_PLACEMENT"]
        self.METAL_LAYERS = self.config["magic_layout_creator"]["METAL_LAYERS"]
        self.VIA_MAP = self.config["magic_layout_creator"]["VIA_MAP"]

        # Make lists of different component types
        for component in self.components:

            if (isinstance(component, Capacitor) and re.search(r'AAL_MISC', component.layout_library)
                    and component.type == "mim"):
                self.aal_misc_mim_capacitor_components.append(component)

            if isinstance(component, (Pin, CircuitCell)):
                self.structural_components.append(component)
                self.structural_components.sort(key=lambda comp: comp.name, reverse=True)  # Reversed alphabetical sort

            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.functional_components.append(component)

            # There should only be one CircuitCell
            if isinstance(component, CircuitCell):
                self.circuit_cell = component

    def pre_trace_generation(self):
        atr.get_component_group_endpoints_for_atr_sky130a_lib(self=self)
        atr.offset_components_by_group_endpoint_and_overlap_distance_for_atr_sky130a_lib(self=self)
        return self.components

    def post_rail_generation(self):
        tr.generate_local_traces_for_tr_sky130a_lib_resistors(self=self)
        atr.generate_local_traces_for_atr_sky130a_lib(self=self)
        aal_misc.generate_local_traces_for_aal_misc_sky130a_lib_pnp_bipolars(self=self)
        aal_misc.generate_local_traces_for_aal_misc_sky130a_lib_mim_capacitors(self=self)
        return self.components

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")



