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

# ================================================= DRC checker ========================================================


@dataclass
class Area:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class RuleViolations:
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

        # Item nr. 2 = detailed violations
        drc_violations = self.__parse_out_detailed_drc_violations(raw_data_log=raw_drc_log[2])

        self.__plot_drc_violations(drc_violations=drc_violations)


    def __create_drc_log(self):
        """Runs a Tcl script that creates a result log from running a series of DRC related magic commands"""

        tcl_script_path = os.path.join(self.main_file_directory, 'drc/log_drc_info.tcl')

        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        try:
            subprocess.run([f'magic ../design/{self.project_lib_name}/{self.project_cell_name}.mag '
                            f'-dnull -noconsole < {tcl_script_path}'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, check=True, shell=True, cwd=work_directory)
            self.logger.info(f"DRC log created from executing 'magic ../design/{self.project_lib_name}/"
                             f"{self.project_cell_name}.mag -dnull -noconsole < {tcl_script_path}'")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'magic ../design/{self.project_lib_name}/{self.project_cell_name}.mag "
                              f"-dnull -noconsole < {tcl_script_path}' failed with {e.stderr}")

    def __read_drc_log(self) -> list:
        work_directory = os.path.expanduser(f"{self.project_directory}/work/")
        drc_log = []
        try:
            with open(f"{work_directory}drc_output.log", "r") as drc_output_log:
                for text_line in drc_output_log:
                    drc_log.append(text_line)
                self.logger.info(f"DRC log '{work_directory}drc_output.log' read")
                return drc_log

        except FileNotFoundError:
            self.logger.error(f"The file {work_directory}/drc_output.log was not found.")

    def __parse_out_detailed_drc_violations(self, raw_data_log) -> RuleViolations:
        general_info_pattern = r"\{([^{}]*)\}"
        all_data_listed = re.findall(general_info_pattern, raw_data_log)

        rule_violations = RuleViolations(rule=defaultdict(list))
        current_rule = None

        for item in all_data_listed:
            # New rule
            if any(char.isalpha() for char in item):
                current_rule = item

            # Coordinates
            else:
                x1, y1, x2, y2 = map(int, item.split())
                area = Area(x1=x1, y1=y1, x2=x2, y2=y2)
                rule_violations.rule[current_rule].append(area)

        self.logger.info("Detailed DRC violations parsed")
        return rule_violations

    def __plot_drc_violations(self, drc_violations: RuleViolations):
        fig, ax = plt.subplots()

        # Add rectangles
        for rule, areas in drc_violations.rule.items():
            for area in areas:
                rect = patches.Rectangle((area.x1, area.y1), area.x2 - area.x1, area.y2 - area.y1,
                                         linewidth=0.1, edgecolor='black', facecolor='red')
                ax.add_patch(rect)

        # Set limits
        ax.set_xlim([min(area.x1 for areas in drc_violations.rule.values() for area in areas),
                     max(area.x2 for areas in drc_violations.rule.values() for area in areas)])

        ax.set_ylim([min(area.y1 for areas in drc_violations.rule.values() for area in areas),
                     max(area.y2 for areas in drc_violations.rule.values() for area in areas)])

        ax.set_xlabel('X-axis')
        ax.set_ylabel('Y-axis')
        ax.set_title('DRC Violations')
        self.logger.info(f"Detailed DRC violations plotted and saved to '{self.main_file_directory}/drc_erros_plot.png'")
        plt.savefig(f"{self.main_file_directory}/drc/drc_erros_plot.png", dpi=500)








