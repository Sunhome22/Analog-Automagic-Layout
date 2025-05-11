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
import itertools
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
class RuleErrors:
    rule: Dict[str, List[Area]] = field(default_factory=list)


class DRCchecking:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties):
        self.current_file_directory = os.path.dirname(os.path.abspath(__file__))
        self.project_directory = project_properties.directory
        self.project_top_lib_name = project_properties.top_lib_name
        self.project_top_cell_name = project_properties.top_cell_name

        self.__create_standard_drc_logs()
        self.__create_custom_drc_log()
        raw_drc_log = self.__read_custom_drc_log()

        # Item nr. 2 = detailed violations
        drc_errors = self.__parse_out_custom_detailed_drc_errors(raw_data_log=raw_drc_log[2])

        self.__plot_custom_drc_errors(drc_errors=drc_errors)
        self.logger.info(f"{raw_drc_log[0].rstrip()}")
        self.logger.info(f"{raw_drc_log[1].rstrip()}")

    def __create_standard_drc_logs(self):
        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        try:
            subprocess.run([f'make drc {work_directory}'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, check=True, shell=True, cwd=work_directory)
            self.logger.info(f"Standard DRC logs created from running 'make drc'")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'Could not run 'make drc {work_directory}'")

    def __create_custom_drc_log(self):
        """Runs a Tcl script that creates a result log from running a series of DRC related magic commands"""

        tcl_script_path = os.path.join(self.current_file_directory, 'log_drc_info.tcl')

        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        try:
            subprocess.run([f'magic ../design/{self.project_top_lib_name}/{self.project_top_cell_name}.mag '
                            f'-dnull -noconsole < {tcl_script_path}'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, check=True, shell=True, cwd=work_directory)
            self.logger.info(f"Custom DRC log created from running 'magic ../design/{self.project_top_lib_name}/"
                             f"{self.project_top_cell_name}.mag -dnull -noconsole < {tcl_script_path}'")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'magic ../design/{self.project_top_lib_name}/{self.project_top_cell_name}.mag "
                              f"-dnull -noconsole < {tcl_script_path}' failed with {e.stderr}")

    def __read_custom_drc_log(self) -> list:
        work_drc_directory = os.path.expanduser(f"{self.project_directory}/work/drc")
        drc_log = []
        try:
            with open(f"{work_drc_directory}/AAL_DRC_OUTPUT.log", "r") as drc_output_log:
                for text_line in drc_output_log:
                    drc_log.append(text_line)
                self.logger.info(f"Custom DRC log '{work_drc_directory}/AAL_DRC_OUTPUT.log' read")
                return drc_log

        except FileNotFoundError:
            self.logger.error(f"The file {work_drc_directory}/AAL_DRC_OUTPUT.log was not found.")

    def __parse_out_custom_detailed_drc_errors(self, raw_data_log) -> RuleErrors:
        general_info_pattern = r"\{([^{}]*)\}"
        all_data_listed = re.findall(general_info_pattern, raw_data_log)

        rule_errors = RuleErrors(rule=defaultdict(list))
        current_rule = None

        for item in all_data_listed:
            # New rule
            if any(char.isalpha() for char in item):
                current_rule = item

            # Coordinates
            else:
                x1, y1, x2, y2 = map(int, item.split())
                area = Area(x1=x1, y1=y1, x2=x2, y2=y2)
                rule_errors.rule[current_rule].append(area)

        self.logger.info("Detailed DRC errors parsed from custom log")
        return rule_errors

    def __plot_custom_drc_errors(self, drc_errors: RuleErrors):
        fig, ax = plt.subplots()

        # Add rectangles
        for rule, areas in drc_errors.rule.items():
            for area in areas:
                rect = patches.Rectangle((area.x1, area.y1), area.x2 - area.x1, area.y2 - area.y1,
                                         linewidth=0.1, edgecolor='black', facecolor='red')
                ax.add_patch(rect)

        # Set plot limits
        areas = list(itertools.chain.from_iterable(drc_errors.rule.values()))
        if areas:
            ax.set_xlim([min(area.x1 for area in areas), max(area.x2 for area in areas)])
            ax.set_ylim([min(area.y1 for area in areas), max(area.y2 for area in areas)])

        ax.set_xlabel('X-axis')
        ax.set_ylabel('Y-axis')
        ax.set_title('DRC Errors')
        self.logger.info(f"Detailed DRC errors plotted from custom log and saved to "
                         f"'{self.current_file_directory}/drc_errors_plot.png'")
        plt.savefig(f"{self.current_file_directory}/drc_errors_plot.png", dpi=500)








