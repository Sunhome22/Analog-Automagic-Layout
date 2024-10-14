# TODO: Add copyright/license notice

# ==== Temporary personal notes ====:
# CMOS Transistors need to be from Carsten's generated transistor library ATR
# BJT Transistors not handled yet
# Capacitors need to be from the standard technology library or from Carsten's generated TR library
# Resistors need to be from the standard technology library or from Carsten's generated TR library

# ================================================== Libraries =========================================================
import os
import subprocess
import re
import circuit_components
from utilities import Text
from circuit_components import *

# ==================================================== Constants =======================================================
TRANSISTOR_PARAM_COUNT = 6
RESISTOR_PARAM_COUNT = 5
CAPACITOR_PARAM_COUNT = 4

# ================================================== SPICE Parser ======================================================


class SPICEparser:

    def __init__(self, project_properties):
        self.project_name = project_properties.name
        self.project_directory = project_properties.directory
        self.component_libraries = project_properties.component_libraries
        self.spice_file_content = list()
        self.components = list()
        self.subcircuits = list()
        self.circuitcells = list()
        self.last_cell_found = ''

        self._parse()

    def _generate_spice_file_for_schematic(self):
        work_directory = os.path.expanduser(f"{self.project_directory}work/")

        # Run SPICE generation command from work directory of project
        try:
            subprocess.run(['make xsch'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    check=True, shell=True, cwd=work_directory)
            print(f"{Text.INFO} SPICE file generated from schematic")

        except subprocess.CalledProcessError as e:
            print(f"{Text.ERROR}: 'make xsch' command failed with: {e.stderr}")

    def _read_spice_file(self):

        try:
            spice_file_path = os.path.expanduser(f"{self.project_directory}work/xsch/{self.project_name}.spice")

            # Copy each line of the file into a list
            with open(spice_file_path, "r") as spice_file:
                for line in spice_file:
                    self.spice_file_content.append(line)
                print(f"{Text.INFO} SPICE content copied into memory")

        except FileNotFoundError:
            print(f"{Text.ERROR} The file '"
                  f"{self.project_directory}work/xsch/{self.project_name}.spice' was not found.")

    def _rebuild_spice_lines_with_plus_symbol(self):
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

        print(f"{Text.INFO} SPICE lines with '+' symbols rebuilt")

    def _get_subcircuit_port_info_for_component_libraries(self, line):
        line_words = line.split()
        subcircuit = SubCircuit(layout_name=line_words[1], ports=line_words[2:])
        self.subcircuits.append(subcircuit)

        print(f"{Text.INFO} SPICE subcircuit port info extracted for '{subcircuit.layout_name}'")

    def _remove_expanded_subcircuits_for_component_libraries(self):
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
                self._get_subcircuit_port_info_for_component_libraries(line)
                in_expanded_symbol = True

            # Check for end of expanded subcircuit
            elif re.match(r'^\.ends', line.strip()) and in_expanded_symbol:
                in_expanded_symbol = False

            elif not in_expanded_symbol and line.strip():
                updated_spice_lines.append(line.strip())

        self.spice_file_content = updated_spice_lines

        print(f"{Text.INFO} SPICE expanded subcircuits for component libraries removed")

    def _get_current_component_library(self, spice_file_line_words):
        library_names = []

        # Create list of library names
        for item in self.component_libraries:
            library_names.append(item.name)

        for index, library in enumerate(library_names):

            # Check for match between library name and layout name
            if re.search(rf"{library}", spice_file_line_words[-1]):

                # Return library name from path name
                return re.search(r'[^/]+$', self.component_libraries[index].path).group()

    def _get_current_cell(self, spice_file_line):
        # Update cell information (Any symbol or the schematic itself)
        if re.match(r'\*\*\.subckt', spice_file_line) or re.match(r'.subckt', spice_file_line):
            print(f"{Text.INFO} Circuit cell '{spice_file_line.split()[1]}' found")
            self.last_cell_found = spice_file_line.split()[1]
            return spice_file_line.split()[1]
        else:
            return self.last_cell_found

    def _get_layout_port_definitions(self, line_word: str, subcircuits: list):
        for circuit in subcircuits:
            if re.match(line_word, circuit.layout_name):
                return circuit.ports

        print(f"{Text.ERROR} Port definition not found for '{line_word}'")

    def _get_components(self, spice_line, current_cell):

        # Check spice line for component identifier
        if re.match(r'^[^*.]', spice_line):
            line_words = spice_line.split()

            current_library = self._get_current_component_library(line_words)

            # --- Transistor ---
            if len(line_words) == TRANSISTOR_PARAM_COUNT:
                # Get port definitions for component
                port_definitions = self._get_layout_port_definitions(line_words[5], self.subcircuits)

                # Create transistor component and add extracted parameters
                transistor = Transistor(name=re.search(r'_(.*)', line_words[0]).group(1) if re.search(r'_(.*)',
                                            line_words[0]) else line_words[0], # chars after underscore if present
                                        cell=current_cell,
                                        group=re.search(r'^[^_]+', line_words[0]).group(),  # chars until underscore
                                        schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                               range(min(len(port_definitions), len(line_words), 4))},
                                        layout_name=line_words[5],
                                        layout_library=current_library)

                transistor.instance = transistor.__class__.__name__  # add instance type
                self.components.append(transistor)

            # --- Resistor ---
            if len(line_words) == RESISTOR_PARAM_COUNT:
                # Get port definitions for component
                port_definitions = self._get_layout_port_definitions(line_words[4], self.subcircuits)

                # Create resistor component and add extracted parameters
                resistor = Resistor(name=re.search(r'_(.*)', line_words[0]).group(1) if re.search(r'_(.*)',
                                            line_words[0]) else line_words[0], # chars after underscore if present
                                    cell=current_cell,
                                    group=re.search(r'^[^_]+', line_words[0]).group() if re.search(r'^[^_]+', line_words[0])
                                                    else '',  # chars until underscore
                                    schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                           range(min(len(port_definitions), len(line_words), 3))},
                                    layout_name=line_words[4],
                                    layout_library=current_library)

                resistor.instance = resistor.__class__.__name__  # add instance type
                self.components.append(resistor)

            #  --- Capacitor ---
            if len(line_words) == CAPACITOR_PARAM_COUNT:
                # Get port definitions for component
                port_definitions = self._get_layout_port_definitions(line_words[3], self.subcircuits)

                # Create capacitor component and add extracted parameters
                capacitor = Capacitor(name=re.search(r'_(.*)', line_words[0]).group(1) if re.search(r'_(.*)',
                                            line_words[0]) else line_words[0], # chars after underscore if present
                                      cell=current_cell,
                                      group=re.search(r'^[^_]+', line_words[0]).group(),  # chars until underscore
                                      schematic_connections={port_definitions[i]: line_words[i + 1] for i in
                                                             range(min(len(port_definitions), len(line_words), 2))},
                                      layout_name=line_words[3],
                                      layout_library=current_library)

                capacitor.instance = capacitor.__class__.__name__  # add instance type
                self.components.append(capacitor)



    def _get_pins(self, spice_line, current_cell):

        # Check spice line for pin identifier
        if re.match(r'^\*\.', spice_line):
            line_words = spice_line.split()

            pin_type = ''.join(re.findall(r'[a-zA-Z]+', line_words[0]))
            pin = Pin(type=pin_type, cell=current_cell, name=line_words[1])
            pin.instance = pin.__class__.__name__  # add instance type
            self.components.append(pin)

    def _parse(self):
        self._generate_spice_file_for_schematic()
        self._read_spice_file()
        self._rebuild_spice_lines_with_plus_symbol()
        self._remove_expanded_subcircuits_for_component_libraries()

        for line in self.spice_file_content:

            current_cell = self._get_current_cell(line)  # Update cell type
            self._get_components(spice_line=line, current_cell=current_cell)
            self._get_pins(spice_line=line, current_cell=current_cell)

        # Summary of parsing
        for component in self.components:
            print(f"{Text.INFO} Component '{component.__class__.__name__}' named '{component.name}' found")
        print(f"{Text.INFO} Components extracted from SPICE file: {len(self.components)}")

    def get_info(self) -> list:
        return self.components








