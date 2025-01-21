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
import subprocess
import re
from logger.logger import get_a_logger
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict
# ================================================= DRC checker ========================================================


@dataclass
class Area:
    x1: int
    y1: int
    x2: int
    y2: int

@dataclass
class Rule:
    rule: Dict[str, List[Area]] = field(default_factory=list)

class DRCchecking:

    def __init__(self, project_properties):
        self.project_directory = project_properties.directory
        self.project_lib_name = project_properties.lib_name
        self.project_cell_name = project_properties.cell_name
        self.main_file_directory = project_properties.main_file_directory
        self.logger = get_a_logger(__name__)

        self.__create_drc_log()
        raw_drc_log = self.__read_drc_log()
        self.__parse_drc_data(raw_data_log=raw_drc_log[2]) # item nr. 2 is the detailed raw log


        # Create a new figure and axis
        fig, ax = plt.subplots(figsize=(12, 12))

        # Save the plot to an image file
        # plt.savefig('drc_erros_plot.png', dpi=300, bbox_inches='tight')  # Save as PNG with high resolution

    def __create_drc_log(self):
        """Runs a Tcl script that creates a result log from running a series of DRC related magic commands"""

        tcl_script_path = os.path.join(self.main_file_directory, 'drc/log_drc_info.tcl')

        work_directory = os.path.expanduser(f"{self.project_directory}work/")

        try:
            subprocess.run([f'magic ../design/{self.project_lib_name}/{self.project_cell_name}.mag '
                            f'-dnull -noconsole < {tcl_script_path}'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, check=True, shell=True, cwd=work_directory)
            self.logger.info("DRC log created")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'magic ../design/{self.project_lib_name}/{self.project_cell_name}.mag "
                              f"-dnull -noconsole < {tcl_script_path}' failed with {e.stderr}")

    def __read_drc_log(self) -> list:
        work_directory = os.path.expanduser(f"{self.project_directory}work/")
        drc_log = []
        try:
            with open(f"{work_directory}/drc_output.log", "r") as drc_output_log:
                for text_line in drc_output_log:
                    drc_log.append(text_line)
                return drc_log

        except FileNotFoundError:
            self.logger.error(f"The file {work_directory}/drc_output.log was not found.")

    def __parse_drc_data(self, raw_data_log):

        # Regex patterns for constraints and coordinates
        constraint_pattern = r"\{(.+?)\}\s*\{\{"
        coordinates_pattern = r"\{(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\}"

        # Parse constraints
        constraints = re.findall(constraint_pattern, raw_data_log)

        # Parse coordinate sets
        all_coordinates = re.findall(r"\{.+?}\s*\{\{(.*?)}}", raw_data_log, re.DOTALL)
        parsed_data = defaultdict(list)

        for constraint, coord_block in zip(constraints, all_coordinates):
            coords = re.findall(coordinates_pattern, coord_block)
            parsed_data[constraint] = [{"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)} for x1, y1, x2, y2
                                       in coords]

        data_log = dict(parsed_data)

        rule_data = Rule(
            rule={
                rule_name: [Area(**constraint) for constraint in constraints]
                for rule_name, constraints in data_log.items()
            }
        )

        print(rule_data)

        #print("First Rule Name:", first_rule_name)
        #print("First Constraint:", first_constraint)
        #print("First Constraint x1:", first_constraint.x1)




