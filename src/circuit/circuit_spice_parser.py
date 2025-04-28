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

# ==================================================== Notes ===========================================================
"""
    Naming conversions for circuit components:
    - RH/RX HPO/XHPO Resistors
    - CM/CV MIM/VPP Capacitors
    - QN/QP	NPN/PNP Bipolar transistor
    - MN/MP NMOS/PMOS transistor
    - U	Circuit cells/Integrated circuits
"""

# ================================================== Libraries =========================================================
import os
import subprocess
import re
import sys
from collections import Counter
from circuit.circuit_components import *
from logger.logger import get_a_logger
import copy

# ================================================== SPICE Parser ======================================================


class SPICEparser:
    logger = get_a_logger(__name__)

    def __init__(self, project_properties):
        self.project_top_cell_name = project_properties.top_cell_name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.spice_file_content = list()
        self.components = list()
        self.subcircuits = list()
        self.circuit_cells = list()
        self.last_cell_found = ''
        self.visited_cells = list()
        self.cell_chain_list = list()

        self.__parse()

    def __generate_spice_file_for_schematic(self):
        work_directory = os.path.expanduser(f"{self.project_directory}/work/")

        # Run SPICE generation command from work directory of project
        try:
            subprocess.run(['make xsch'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                           check=True, shell=True, cwd=work_directory)
            self.logger.info("SPICE file generated from schematic")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"'make xsch' command failed with: {e.stderr}")

    def __read_spice_file(self):

        try:
            spice_file_path = os.path.expanduser(f"{self.project_directory}/work/xsch/"
                                                 f"{self.project_top_cell_name}.spice")

            # Copy each line of the file into a list
            with open(spice_file_path, "r") as spice_file:

                for line in spice_file:
                    # Check for missing symbols
                    if re.search(r'\bIS MISSING\b', line):
                        self.logger.error(f"Component '{line.split()[1]}' is missing the symbol '{line.split()[3]}'")
                    else:
                        self.spice_file_content.append(line)

                self.logger.info(f"SPICE content copied into program")

        except FileNotFoundError:
            self.logger.error(f"The file {self.project_directory}/work/xsch/"
                              f"{self.project_top_cell_name}.spice' was not found.")

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

    def __get_subcircuit_port_info_for_component_libraries(self, line: str):
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

    def __get_current_component_library(self, line: str):
        library_names = []

        # Create list of library names
        for item in self.component_libraries:
            library_names.append(item.name)

        for index, library in enumerate(library_names):

            # Check for match between library name and layout name
            if re.search(rf"{library}", line.split()[-1]):

                # Return library name from path name
                return re.search(r'[^/]+$', self.component_libraries[index].path).group()

    def __get_port_info_for_circuit_cells(self, spice_file_content: list):
        for line in spice_file_content:
            if re.match(r'\*\*\.subckt', line) or re.match(r'.subckt', line):
                line_words = line.split()

                subcircuit = SubCircuit(layout_name=line_words[1], ports=line_words[2:])
                self.subcircuits.append(subcircuit)

                self.logger.info(f"SPICE subcircuit port info found for '{subcircuit.layout_name}'")

    def __get_current_circuit_cell_name(self, spice_file_line: str):
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

    @staticmethod
    def __get_component_category_and_type(filtered_name):
        # A map of different category identifiers and type identifiers to their corresponding type words
        component_category_to_type_table = {
            ("M", "N"): "nmos",
            ("M", "P"): "pmos",
            ("Q", "N"): "npn",
            ("Q", "P"): "pnp",
            ("C", "M"): "mim",
            ("C", "V"): "vpp",
            ("R", "H"): "hpo",
            ("R", "X"): "xhpo"
        }

        # The first letter of the filtered name defines category
        component_category = filtered_name[0]

        # The second letter of the filtered name can define type
        component_type = component_category_to_type_table.get((component_category, filtered_name[1]), None)

        return component_category, component_type

    def __get_component(self, spice_line: str, cell: str, named_cell: str, parent_cell: str, cell_chain: str,
                        current_library: str):

        # Check SPICE line for circuit component identifier
        if re.match(r'^[^*.]', spice_line):
            line_words = spice_line.split()

            # Remove first letter of string containing group + name as a general rule
            line_words[0] = line_words[0][1:]

            # Component name = characters after underscore if underscore is present
            filtered_name = (lambda x: re.search(r'_(.*)', x).group(1) if re.search(
                r'_(.*)', x) else x)(line_words[0])

            # Component group = characters until underscore if underscore is present. First char is skipped
            filtered_group = (lambda x: re.search(r'^[^_]+(?=_)', x[:]).group() if re.search(
                r'^[^_]+(?=_)', x[1:]) else None)(line_words[0])

            # Error handling incase component category or component type is invalid
            try:
                component_category, component_type = self.__get_component_category_and_type(filtered_name=filtered_name)
            except IndexError as e:
                self.logger.error(f"Incorrect naming of component on spice line: '{spice_line}'")
                self.logger.error(f"Naming conversions for circuit components: ")
                self.logger.error(f"- xRH?/xRX? HPO/XHPO Resistors")
                self.logger.error(f"- xCM?/xCV MIM/VPP Capacitors")
                self.logger.error(f"- xQN?/xQP? NPN/PNP")
                self.logger.error(f"- xMN?/xMP? NMOS/PMOS")
                self.logger.error(f"- xD? Digital Blocks")
                self.logger.error(f"- xU? Circuit Cells")
                sys.exit()

            # --- MOS Transistor / Bipolar Transistor ---
            if component_category == 'M' or component_category == 'Q':

                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[-1], self.subcircuits)

                # Create transistor component and add extracted parameters
                transistor = Transistor(name=filtered_name,
                                        type=component_type,
                                        number_id=len(self.components),
                                        cell=cell,
                                        named_cell=named_cell,
                                        parent_cell=parent_cell,
                                        cell_chain=cell_chain,
                                        group=filtered_group,
                                        schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                               range(min(len(port_definitions), len(line_words) - 1))},
                                        layout_name=line_words[-1],
                                        layout_library=current_library)

                transistor.instance = transistor.__class__.__name__  # add instance type
                self.components.append(transistor)

            # --- Resistor ---
            elif component_category == 'R':

                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[-1], self.subcircuits)

                # Create resistor component and add extracted parameters
                resistor = Resistor(name=filtered_name,
                                    type=component_type,
                                    number_id=len(self.components),
                                    cell=cell,
                                    named_cell=named_cell,
                                    parent_cell=parent_cell,
                                    cell_chain=cell_chain,
                                    group=filtered_group,
                                    schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                           range(min(len(port_definitions), len(line_words) - 1))},
                                    layout_name=line_words[-1],
                                    layout_library=current_library)

                resistor.instance = resistor.__class__.__name__  # add instance type
                self.components.append(resistor)

            #  --- Capacitor ---
            elif component_category == 'C':

                # Get port definitions for components
                port_definitions = self.__get_layout_port_definitions(line_words[-1], self.subcircuits)

                # Create capacitor component and add extracted parameters
                capacitor = Capacitor(name=filtered_name,
                                      type=component_type,
                                      number_id=len(self.components),
                                      cell=cell,
                                      named_cell=named_cell,
                                      parent_cell=parent_cell,
                                      cell_chain=cell_chain,
                                      group=filtered_group,
                                      schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                             range(min(len(port_definitions), len(line_words) - 1))},
                                      layout_name=line_words[-1],
                                      layout_library=current_library)

                capacitor.instance = capacitor.__class__.__name__  # add instance type
                self.components.append(capacitor)

            #  --- Digital Blocks ---
            elif component_category == 'D':

                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[-1], self.subcircuits)

                # Create digital block component and add extracted parameters
                digital_block = DigitalBlock(name=filtered_name,
                                             type="digital",
                                             number_id=len(self.components),
                                             cell=cell,
                                             named_cell=named_cell,
                                             parent_cell=parent_cell,
                                             cell_chain=cell_chain,
                                             group=filtered_group,
                                             schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                                    range(min(len(port_definitions),
                                                                              len(line_words) - 1))},
                                             layout_name=line_words[-1],
                                             layout_library=current_library)

                digital_block.instance = digital_block.__class__.__name__  # add instance type
                self.components.append(digital_block)

        # Check SPICE line for pin identifier
        if re.match(r'^\*\.', spice_line):
            line_words = spice_line.split()

            pin_type = ''.join(re.findall(r'[a-zA-Z]+', line_words[0]))
            pin = Pin(type=pin_type, cell=cell, named_cell=named_cell, parent_cell=parent_cell,
                      cell_chain=cell_chain, name=line_words[1], number_id=len(self.components))
            pin.instance = pin.__class__.__name__  # add instance type
            self.components.append(pin)

    def __build_list_of_circuit_cells(self, spice_line, current_cell_name):
        # Check SPICE line for circuit component identifier
        if re.match(r'^[^*.]', spice_line):
            line_words = spice_line.split()

            # Remove first letter of string containing group + name as a general rule
            line_words[0] = line_words[0][1:]

            # Component name = characters after underscore if underscore is present
            filtered_name = (lambda x: re.search(r'_(.*)', x).group(1) if re.search(
                r'_(.*)', x) else x)(line_words[0])

            # Component group = characters until underscore if underscore is present. First char is skipped
            filtered_group = (lambda x: re.search(r'^[^_]+(?=_)', x[:]).group() if re.search(
                r'^[^_]+(?=_)', x[1:]) else None)(line_words[0])

            # Error handling incase component category or component type is invalid
            try:
                component_category, _ = self.__get_component_category_and_type(filtered_name=filtered_name)
            except IndexError as e:
                self.logger.error(f"Incorrect naming of component on spice line: '{spice_line}'")
                self.logger.error(f"Naming conversions for circuit components: ")
                self.logger.error(f"- xRH?/xRX? HPO/XHPO Resistors")
                self.logger.error(f"- xCM?/xCV? MIM/VPP Capacitors")
                self.logger.error(f"- xQN?/xQP? NPN/PNP")
                self.logger.error(f"- xMN?/xMP? NMOS/PMOS")
                self.logger.error(f"- xD? Digital Blocks")
                self.logger.error(f"- xU? Circuit Cells")
                sys.exit()

            #  --- Circuit cells ---
            if component_category == 'U':
                # Get port definitions for component
                port_definitions = self.__get_layout_port_definitions(line_words[-1], self.subcircuits)

                # Create circuit cell component and add extracted parameters
                circuit_cell = CircuitCell(name=f"{line_words[0]}",
                                           cell=line_words[-1],
                                           named_cell=f"{line_words[0]}_{line_words[-1]}",
                                           parent_cell=current_cell_name,
                                           cell_chain=f"", # not added yet
                                           group=filtered_group,
                                           number_id=0, # not added yet
                                           schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                                  range(min(len(port_definitions), len(line_words) - 1)
                                                                        )})
                circuit_cell.instance = circuit_cell.__class__.__name__  # add instance type
                self.circuit_cells.append(circuit_cell)

    def __add_components_for_each_circuit_cell(self, current_parent_cell):
        """Recursive adding of components within each circuit cell"""

        for circuit_cell in self.circuit_cells:

            if circuit_cell.parent_cell == current_parent_cell:
                inside_cell = False

                # Cell chain algorithm
                self.visited_cells.append(circuit_cell.cell)
                self.cell_chain_list.append(f"{circuit_cell.name}_{circuit_cell.cell}")

                while True:
                    found = False
                    # Check for any match where last cell equals any earlier cell
                    for n in range(2, len(self.visited_cells)):

                        # Check if the current parent cells is the same as one n steps back
                        if circuit_cell.parent_cell == self.visited_cells[-n]:
                            # Remove everything between the match and the current cell
                            for _ in range(n - 2):
                                self.cell_chain_list.pop(-2)
                                self.visited_cells.pop(-2)

                        # Check if the most recent cell is the same as one n steps back
                        if self.visited_cells[-1] == self.visited_cells[-n]:
                            # Remove everything between the match and the current cell
                            for _ in range(n - 1):
                                self.cell_chain_list.pop(-2)
                                self.visited_cells.pop(-2)
                            found = True
                            break  # Restart after each change

                    if not found:
                        break

                circuit_cell.cell_chain = '--'.join(self.cell_chain_list)
                circuit_cell.number_id = len(self.components)
                self.components.append(copy.deepcopy(circuit_cell))

                # Extract components inside current cell
                for line in self.spice_file_content:
                    line_words = line.split()

                    if len(line_words) > 1 and line_words[1] == circuit_cell.cell:
                        inside_cell = True
                    elif line_words[0] == '.ends':
                        inside_cell = False
                    elif inside_cell:
                        current_library = self.__get_current_component_library(line)
                        self.__get_component(spice_line=line,
                                             cell=circuit_cell.cell,
                                             named_cell=f"{circuit_cell.name}_{circuit_cell.cell}",
                                             parent_cell=circuit_cell.parent_cell,
                                             cell_chain='--'.join(self.cell_chain_list),
                                             current_library=current_library)

                print(circuit_cell.cell_chain)
                self.__add_components_for_each_circuit_cell(current_parent_cell=circuit_cell.cell)

    def __parse(self):
        self.__generate_spice_file_for_schematic()
        self.__read_spice_file()
        self.__rebuild_spice_lines_with_plus_symbol()
        self.__remove_expanded_subcircuits_for_component_libraries()
        # The only possible subcircuits left in the spice file now are cells.

        self.__get_port_info_for_circuit_cells(self.spice_file_content)

        for line in self.spice_file_content:
            current_cell_name = self.__get_current_circuit_cell_name(line)

            # Append the highest hierarchical circuit cell to the list of circuit cells
            # "ROOT_CELL" is not a real cell and is taught of as one level above the highest defined cell
            if current_cell_name == self.project_top_cell_name:
                if re.match(r'\*\*\.subckt', line) or re.match(r'.subckt', line):
                    if line.split()[1] == self.project_top_cell_name:
                        self.__build_list_of_circuit_cells(spice_line=f"xUTOP " + f" ".join(line.split()[2:])
                                                           + f" {line.split()[1]}", current_cell_name="ROOT_CELL")

            self.__build_list_of_circuit_cells(spice_line=line, current_cell_name=current_cell_name)

        self.__add_components_for_each_circuit_cell(current_parent_cell="ROOT_CELL")

        # Summary of parsing
        for component in self.components:
            self.logger.info(f"Found '{component.__class__.__name__}' "
                             f"named '{component.name}' from named cell '{component.named_cell}' of parent cell "
                             f"'{component.parent_cell}'")

        self.logger.info("Process complete! Components extracted from SPICE file: "
                         f"{len(self.components)}")

    def get(self) -> list:
        return self.components