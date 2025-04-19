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

# ===================================================== Libraries ======================================================
import re

# ======================================================================================================================
# ================================================= TR SKY130A handling ================================================
# ======================================================================================================================

# ========================================== Magic component parser functions ==========================================


def get_component_bounding_box_for_tr_sky130a_lib(self, text_line: str, component):
    if re.search(r'string FIXED_BBOX', text_line):
        text_line_words = text_line.split()
        component.bounding_box.set(map(int, text_line_words[2:6]))
        self.found_bounding_box = True


def magic_component_parsing_for_tr_sky130a_lib(self, layout_file_path: str, component):
    try:
        with open(layout_file_path, "r") as magic_file:
            for text_line in magic_file:
                get_component_bounding_box_for_tr_sky130a_lib(text_line=text_line, component=component, self=self)
    except FileNotFoundError:
        self.logger.error(f"The file {layout_file_path} was not found.")
