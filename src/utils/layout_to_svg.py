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
import os
import re
import subprocess
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from dataclasses import dataclass, field
from typing import List, Dict
from collections import defaultdict
from logger.logger import get_a_logger
import gdspy

# ================================================= LVS checker ========================================================


style = {
    # Highlighted Metal Layers
    (70, 20): {'fill': '#1f77b4', 'fill-opacity': 1.0},  # Metal 2 - Strong blue
    (69, 20): {'fill': '#d62728', 'fill-opacity': 1.0},  # Metal 3 - Strong red

    # All other layers faded (nearly invisible)
    (64, 20): {'fill': '#FFC3A0', 'fill-opacity': 0.2},
    (65, 20): {'fill': '#FFC3A0', 'fill-opacity': 0.4},
    (65, 44): {'fill': '#3E3E3E', 'fill-opacity': 0.1},
    (66, 13): {'fill': '#000000', 'fill-opacity': 0.02},
    (66, 20): {'fill': '#000000', 'fill-opacity': 0.02},
    (66, 44): {'fill': '#000000', 'fill-opacity': 0.02},
    (67, 16): {'fill': '#000000', 'fill-opacity': 0.02},
    (67, 20): {'fill': '#000000', 'fill-opacity': 0.02},
    (67, 44): {'fill': '#000000', 'fill-opacity': 0.02},
    (68, 16): {'fill': '#000000', 'fill-opacity': 0.02},
    (68, 20): {'fill': '#000000', 'fill-opacity': 0.02},
    (68, 44): {'fill': '#000000', 'fill-opacity': 0.02},
    (69, 16): {'fill': '#000000', 'fill-opacity': 0.02},
    (69, 44): {'fill': '#000000', 'fill-opacity': 0.02},
    (86, 20): {'fill': '#000000', 'fill-opacity': 0.02},
    (93, 44): {'fill': '#000000', 'fill-opacity': 0.02},
    (94, 20): {'fill': '#000000', 'fill-opacity': 0.02},
    (95, 20): {'fill': '#000000', 'fill-opacity': 0.02},
    (235, 4): {'fill': '#000000', 'fill-opacity': 0.02},
}


class LayoutToSVG:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties):
        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))
        self.project_directory = project_properties.directory
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_cell_name = project_properties.top_cell_name
        self.__run_layout_to_svg_creator()

    def __run_layout_to_svg_creator(self):
        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        # Runs GDS command from work directory of project
        try:
            output = subprocess.run(['make gds'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    check=True, shell=True, cwd=work_directory)
            print("yo")
            self.logger.info(output.stdout)

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'make gds' command had problems: {e.stderr}")

        lib = gdspy.GdsLibrary()
        lib.read_gds(f'{work_directory}gds/OTA.gds')
        cell = lib.top_level()[0]

        used_layers = set()
        for polygon in cell.get_polygons(by_spec=True).items():
            used_layers.add(polygon[0])

        print("Used layers in this cell:", sorted(used_layers))

        cell.write_svg('OTA_horizontal_config.svg',
                       style=style,
                       background='#ffffff',
                       pad=10)
        self.logger.info("Created SVG successfully")



