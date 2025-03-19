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

# ================================================= LVS checker ========================================================

class LVSchecking:

    def __init__(self, project_properties):
        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))
        self.project_directory = project_properties.directory
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_cell_name = project_properties.top_cell_name
        self.logger = get_a_logger(__name__)
        self.__run_lvs_checker()

    def __run_lvs_checker(self):
        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        # Runs LVS command from work directory of project
        try:
            subprocess.run(['make lvsall'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           check=True, shell=True, cwd=work_directory)
            self.logger.info("TBD!")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"'make lvsall' command had problems: {e.stderr}")