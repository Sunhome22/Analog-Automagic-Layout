#======================================================================================================================#
# Copyright (C) 2024 Bjørn K.T. Solheim, Leidulv Tønnesland
#======================================================================================================================#
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
#======================================================================================================================#

# ==================================================== Notes ===========================================================
"""
    Naming conversions for circuit components:
    - R	Resistors
    - C	Capacitors
    - Q	Bipolar transistor
    - M NMOS/PMOS transistor
    - U	Circuit cells/Integrated circuits
"""

# ================================================== Libraries =========================================================
import os
import subprocess
import re
from circuit.circuit_components import *
from logger.logger import get_a_logger

# ================================================== SPICE Parser ======================================================


class SPICEparser:

    def __init__(self, project_properties):
        self.project_name = project_properties.name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.spice_file_content = list()
        self.components = list()
        self.subcircuits = list()
        self.last_cell_found = ''

        self.logger = get_a_logger(__name__)
        self.__parse()

    def __generate_spice_file_for_schematic(self):
        work_directory = os.path.expanduser(f"{self.project_directory}work/")

        # Run SPICE generation command from work directory of project
        try:
            subprocess.run(['make xsch'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    check=True, shell=True, cwd=work_directory)
            self.logger.info("SPICE file generated from schematic")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'make xsch' command failed with: {e.stderr}")

    def __read_spice_file(self):

        try:
            spice_file_path = os.path.expanduser(f"{self.project_directory}work/xsch/{self.project_name}.spice")

            # Copy each line of the file into a list
            with open(spice_file_path, "r") as spice_file:
                for line in spice_file:
                    self.spice_file_content.append(line)
                self.logger.info(f"SPICE content copied into memory")

        except FileNotFoundError:
            self.logger.error(f"The file {self.project_directory}work/xsch/{self.project_name}.spice' was not found.")

    def __rebuild_spice_lines_with_plus_symbol(self):
        # Removes added "+" symbols to long lines in the SPICE file
        updated_spice_lines = []
        previous_line = ""

        for line in self.spice_file_content:

            if re.match(r'^\+', line):
                # Removes "+", any trailing/leading space and '\n' from previous line
                previous_line = previous_line.strip() + " " + line[1:].strip()

            else:
                # Append when previous line has content
                if previous_line:
                    updated_spice_lines.append(previous_line.strip())

                previous_line = line

        if previous_line:
            updated_spice_lines.append(previous_line.strip())

        self.spice_file_content = updated_spice_lines
        self.logger.info("SPICE lines with '+' symbols rebuilt")

    def __get_subcircuit_port_info_for_component_libraries(self, line):
        line_words = line.split()
        subcircuit = SubCircuit(layout_name=line_words[1], ports=line_words[2:])
        self.subcircuits.append(subcircuit)

        self.logger.info(f"SPICE subcircuit port info found for '{subcircuit.layout_name}'")

    def __remove_expanded_subcircuits_for_component_libraries(self):
        in_expanded_symbol = False
        updated_spice_lines = []
        library_names = []

        # Create list of library names
        for item in self.component_libraries:
            library_names.append(item.name)

        for line in self.spice_file_content:

            # Iterate over library names and remove specific subcircuit contents
            if any(re.match(rf'^\.subckt {library_name}', line.strip()) for library_name in library_names):

                # Retrieve specific subcircuit port information before deletions
                self.__get_subcircuit_port_info_for_component_libraries(line)
                in_expanded_symbol = True

            # Check for end of expanded subcircuit
            elif re.match(r'^\.ends', line.strip()) and in_expanded_symbol:
                in_expanded_symbol = False

            elif not in_expanded_symbol and line.strip():
                updated_spice_lines.append(line.strip())

        self.spice_file_content = updated_spice_lines

        self.logger.info("SPICE expanded subcircuits for component libraries removed")

    def __get_current_component_library(self, line):
        library_names = []

        # Create list of library names
        for item in self.component_libraries:
            library_names.append(item.name)

        for index, library in enumerate(library_names):

            # Check for match between library name and layout name
            if re.search(rf"{library}", line.split()[-1]):

                # Return library name from path name
                return re.search(r'[^/]+$', self.component_libraries[index].path).group()

    def __get_subcircuit_port_info_for_cells(self, spice_file_content):
        for line in spice_file_content:
            if re.match(r'\*\*\.subckt', line) or re.match(r'.subckt', line):
                line_words = line.split()
                subcircuit = SubCircuit(layout_name=line_words[1], ports=line_words[2:])
                self.subcircuits.append(subcircuit)

                self.logger.info(f"SPICE subcircuit port info found for '{subcircuit.layout_name}'")

    def __get_current_cell(self, spice_file_line):
        # Update cell information (Any symbol or the schematic itself)
        if re.match(r'\*\*\.subckt', spice_file_line) or re.match(r'.subckt', spice_file_line):
            self.logger.info(f"Found circuit cell '{spice_file_line.split()[1]}'")
            self.last_cell_found = spice_file_line.split()[1]
            return spice_file_line.split()[1]
        else:
            return self.last_cell_found

    def __get_layout_port_definitions(self, line_word: str, subcircuits: list):
        for subcircuit in subcircuits:
            if re.match(line_word, subcircuit.layout_name):
                return subcircuit.ports

        self.logger.error(f"Port definition not found for '{line_word}'")

    def __get_component_category_and_type(self, filtered_name):

        # A map of different category identifiers and type identifiers to their corresponding type words
        component_category_to_type_table = {
            ("M", "N"): "nmos",
            ("M", "P"): "pmos",
            ("Q", "N"): "npn",
            ("Q", "P"): "pnp"
        }

        # The first letter of the filtered name defines category
        component_category = filtered_name[0]

        # The second letter of the filtered name can define type
        component_type = component_category_to_type_table.get((component_category, filtered_name[1]), None)

        return component_category, component_type

    def __get_component(self, spice_line, current_cell, current_library):

        # Check SPICE line for circuit component identifier
        if re.match(r'^[^*.]', spice_line):
            line_words = spice_line.split()

            # Component name = characters after underscore if underscore is present
            filtered_name = (lambda x: re.search(r'_(.*)', x).group(1) if re.search(
                r'_(.*)', x) else x)(line_words[0])

            # Component group = characters until underscore if underscore is present
            filtered_group = (lambda x: re.search(r'^[^_]+(?=_)', x).group() if re.search(
                r'^[^_]+(?=_)', x) else None)(line_words[0])

            # Component category and type
            component_category, component_type = self.__get_component_category_and_type(filtered_name)

            # --- MOS Transistor ---
            if component_category == 'M':

                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[5], self.subcircuits)

                # Create transistor component and add extracted parameters
                transistor = Transistor(name=filtered_name,
                                        type=component_type,
                                        number_id=len(self.components),
                                        cell=current_cell,
                                        group=filtered_group,
                                        schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                               range(min(len(port_definitions), len(line_words) - 1))},
                                        layout_name=line_words[5],
                                        layout_library=current_library)

                transistor.instance = transistor.__class__.__name__  # add instance type
                self.components.append(transistor)

            # --- Resistor ---
            elif component_category == 'R':

                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[4], self.subcircuits)

                # Create resistor component and add extracted parameters
                resistor = Resistor(name=filtered_name,
                                    type=component_type,
                                    number_id=len(self.components),
                                    cell=current_cell,
                                    group=filtered_group,
                                    schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                           range(min(len(port_definitions), len(line_words) - 1))},
                                    layout_name=line_words[4],
                                    layout_library=current_library)

                resistor.instance = resistor.__class__.__name__  # add instance type
                self.components.append(resistor)

            #  --- Capacitor ---
            elif component_category == 'C':

                # Get port definitions for components
                port_definitions = self.__get_layout_port_definitions(line_words[3], self.subcircuits)

                # Create capacitor component and add extracted parameters
                capacitor = Capacitor(name=filtered_name,
                                      type=component_type,
                                      number_id=len(self.components),
                                      cell=current_cell,
                                      group=filtered_group,
                                      schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                             range(min(len(port_definitions), len(line_words) - 1))},
                                      layout_name=line_words[3],
                                      layout_library=current_library)

                capacitor.instance = capacitor.__class__.__name__  # add instance type
                self.components.append(capacitor)

            #  --- Bipolar Transistor ---
            elif component_category == 'Q':

                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[4], self.subcircuits)

                # Create transistor component and add extracted parameters
                transistor = Transistor(name=filtered_name,
                                        type=component_type,
                                        number_id=len(self.components),
                                        cell=current_cell,
                                        group=filtered_group,
                                        schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                               range(min(len(port_definitions), len(line_words) - 1))},
                                        layout_name=line_words[4],
                                        layout_library=current_library)

                transistor.instance = transistor.__class__.__name__  # add instance type
                self.components.append(transistor)

            #  --- Circuit cells ---
            elif component_category == 'U':

                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[-1], self.subcircuits)

                # Create circuit cell component and add extracted parameters
                circuit_cell = CircuitCell(name=line_words[-1],
                                           cell=current_cell,
                                           number_id=len(self.components),
                                           schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                                  range(min(len(port_definitions), len(line_words) - 1)
                                                                        )})

                circuit_cell.instance = circuit_cell.__class__.__name__  # add instance type

                self.components.append(circuit_cell)

            else:
                self.logger.error(f"SPICE line '{spice_line}' is not handled!")

        # Check SPICE line for pin identifier
        if re.match(r'^\*\.', spice_line):
            line_words = spice_line.split()

            pin_type = ''.join(re.findall(r'[a-zA-Z]+', line_words[0]))
            pin = Pin(type=pin_type, cell=current_cell, name=line_words[1], number_id=len(self.components))
            pin.instance = pin.__class__.__name__  # add instance type
            self.components.append(pin)

    def __parse(self):
        self.__generate_spice_file_for_schematic()
        self.__read_spice_file()
        self.__rebuild_spice_lines_with_plus_symbol()
        self.__remove_expanded_subcircuits_for_component_libraries()
        # The only possible subcircuits left in the spice file now are cells.

        # Get port info for these cells
        self.__get_subcircuit_port_info_for_cells(self.spice_file_content)

        # Main component extraction loop
        for line in self.spice_file_content:
            current_library = self.__get_current_component_library(line)
            current_cell = self.__get_current_cell(line)
            self.__get_component(spice_line=line, current_cell=current_cell, current_library=current_library)

        # Summary of parsing
        for component in self.components:
            self.logger.info(f"Found '{component.__class__.__name__}' "
                             f"named '{component.name}' from cell '{component.cell}'")

        self.logger.info("Process complete! Components extracted from SPICE file: "
                         f"{len(self.components)}")

    def get_info(self) -> list:
        return self.components









