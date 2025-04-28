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
from circuit.circuit_components import RectArea, Transistor, Capacitor, Resistor, Pin, CircuitCell, TraceNet, \
    RectAreaLayer
from logger.logger import get_a_logger
import tomllib
import re
import libraries.atr_sky130a_lib as atr
import libraries.tr_sky130a_lib as tr

# ============================================ ATR SKY130A Handling ====================================================


class LibraryHandling:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties, components):
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.structural_components = []
        self.functional_components = []
        self.transistor_components = []
        self.atr_transistor_components = []
        self.tr_components = []
        self.components = components

        # Load config
        self.config = self.__load_config()
        self.INIT_RAIL_RING_OFFSET_X = self.config["generate_rail_traces"]["INIT_RAIL_RING_OFFSET_X"]
        self.INIT_RAIL_RING_OFFSET_Y = self.config["generate_rail_traces"]["INIT_RAIL_RING_OFFSET_Y"]
        self.RAIL_RING_OFFSET = self.config["generate_rail_traces"]["RAIL_RING_OFFSET"]
        self.RAIL_RING_WIDTH = self.config["generate_rail_traces"]["RAIL_RING_WIDTH"]

        # Make lists of different component types
        for component in self.components:
            if isinstance(component, Transistor) and re.search(r'_ATR_', component.layout_library):
                self.atr_transistor_components.append(component)

            if isinstance(component, (Resistor, Capacitor)) and re.search(r'_TR_', component.layout_library):
                self.tr_components.append(component)

            if isinstance(component, (Pin, CircuitCell)):
                self.structural_components.append(component)
                self.structural_components.sort(key=lambda comp: comp.name)

            if isinstance(component, (Transistor, Resistor, Capacitor)):
                self.functional_components.append(component)

            # There should only be one CircuitCell
            if isinstance(component, CircuitCell):
                self.circuit_cell = component

        # ATR SKY130A library component handling
        if self.atr_transistor_components:
            atr.get_component_group_endpoints_for_atr_sky130a_lib(self=self)
            atr.generate_local_traces_for_atr_sky130a_lib(self=self)

        # TR SKY130A library component handling
        if self.tr_components:
            tr.generate_local_traces_for_tr_sky130a_lib(self=self)

    def __load_config(self, path="pyproject.toml"):
        try:
            with open(path, "rb") as f:
                return tomllib.load(f)
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            self.logger.error(f"Error loading config: {e}")

    def get(self):
        return self.components