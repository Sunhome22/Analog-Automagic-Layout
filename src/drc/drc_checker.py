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
# ================================================= DRC checker ========================================================


class DRCchecking:

    def __init__(self, project_properties):
        self.project_directory = project_properties.directory
        self.project_lib_name = project_properties.lib_name
        self.project_cell_name = project_properties.cell_name
        self.main_file_directory = project_properties.main_file_directory
        self.logger = get_a_logger(__name__)

        self.__create_drc_log()
        drc_log = self.__read_drc_log()

        detailed_errors = drc_log[2]
        new_detailed_errors = ""

        for i in detailed_errors:
            if i == "{{":
                new_detailed_errors = detailed_errors.replace(" ", ",")
        #print(new)


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



