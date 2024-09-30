# TODO: Add copyright/license notice

# ==== Temporary personal notes ====:
# CMOS Transistors need to be from Carsten's generated transistor library ATR
# BJT Transistors not handled yet
# Capacitors need to be from the standard technology library or from Carsten's generated TR library
# Resistors need to be from the standard technology library or from Carsten's generated TR library
# Remember to pip install external libraries to the server if used

# =================================================== Libraries ========================================================
import os
import subprocess
import re

from utilities import Text
from circuit_components import *

# ==================================================== Constants =======================================================
# "STD" refers to the generated transistors/capacitors/resistors from Carsten's ATR/TR libraries.
STD_LIB_TRANSISTOR_PARAMS = 6
STD_LIB_RESISTOR_PARAMS = 5
STD_LIB_CAPACITOR_PARAMS = 4

# ================================================== SPICE Parser ======================================================


class SPICEparser:

    def __init__(self, project_properties):
        self.project_name = project_properties.name
        self.project_directory = project_properties.directory
        self.standard_libraries = project_properties.standard_libraries
        self.spice_file_content = list()
        self.components = list()
        self.subcircuits = list()

        self.parse()

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
                previous_line = previous_line.strip() +" "+ line[1:].strip()

            else:
                # Append when previous line has content
                if previous_line:
                    updated_spice_lines.append(previous_line.strip())

                previous_line = line

        if previous_line:
            updated_spice_lines.append(previous_line.strip())

        self.spice_file_content = updated_spice_lines

    def _get_subcircuit_port_info_for_standard_libraries(self, line):
        line_words = line.split()
        subcircuit = SubCircuit(layout_name=line_words[1], ports=line_words[2:])
        self.subcircuits.append(subcircuit)

    def _remove_expanded_subcircuits_for_standard_libraries(self):
        in_expanded_symbol = False
        updated_spice_lines = []
        library_names = []

        # Create list of library names
        for item in self.standard_libraries:
            library_names.append(item.name)

        for line in self.spice_file_content:
            # Iterate over library names and remove specific subcircuit contents
            if any(re.match(rf'^\.subckt {library_name}', line.strip()) for library_name in library_names):

                # Retrieve specific subcircuit port information before deletion
                self._get_subcircuit_port_info_for_standard_libraries(line)

                in_expanded_symbol = True

            elif re.match(r'^\.ends', line.strip()) and in_expanded_symbol:
                in_expanded_symbol = False

            elif not in_expanded_symbol and line.strip():
                updated_spice_lines.append(line.strip())

        self.spice_file_content = updated_spice_lines

    def _get_current_component_library(self, spice_file_line_words):
        library_names = []

        # Create list of library names
        for item in self.standard_libraries:
            library_names.append(item.name)

        for index, library in enumerate(library_names):

            # Check for match between library name and layout name
            if re.search(rf"{library}", spice_file_line_words[-1]):

                # Return library name from path name
                return re.search(r'[^/]+$', self.standard_libraries[index].path).group()

    def _get_layout_port_definitions(self, line_word: str, subcircuits: list):
        for circuit in subcircuits:
            if re.match(line_word, circuit.layout_name):
                return circuit.ports

    def parse(self):
        self._generate_spice_file_for_schematic()
        self._read_spice_file()
        self._rebuild_spice_lines_with_plus_symbol()
        self._remove_expanded_subcircuits_for_standard_libraries()

        for line in self.spice_file_content:

            # Check for components
            if re.match(r'^[^*.]', line):
                line_words = line.split()
                current_library = self._get_current_component_library(line_words)

                # Transistor
                if len(line_words) == STD_LIB_TRANSISTOR_PARAMS:

                    # Get port definitions for component
                    port_definitions = self._get_layout_port_definitions(line_words[5], self.subcircuits)

                    # Create transistor component and add extracted parameters
                    transistor = Transistor(name=line_words[0],
                                            schematic_connections={port_definitions[i]: line_words[i+1] for i in
                                                         range(min(len(port_definitions), len(line_words), 4))},
                                            layout_name=line_words[5],
                                            layout_library=current_library)

                    self.components.append(transistor)

                # Resistor
                if len(line_words) == STD_LIB_RESISTOR_PARAMS:

                    # Get port definitions for component
                    port_definitions = self._get_layout_port_definitions(line_words[4], self.subcircuits)

                    # Create resistor component and add extracted parameters
                    resistor = Resistor(name=line_words[0],
                                        schematic_connections={port_definitions[i]: line_words[i+1] for i in
                                                     range(min(len(port_definitions), len(line_words), 3))},
                                        layout_name=line_words[4],
                                        layout_library=current_library)

                    self.components.append(resistor)

                # Capacitor
                if len(line_words) == STD_LIB_CAPACITOR_PARAMS:

                    # Get port definitions for component
                    port_definitions = self._get_layout_port_definitions(line_words[3], self.subcircuits)

                    # Create capacitor component and add extracted parameters
                    capacitor = Capacitor(name=line_words[0],
                                          schematic_connections={port_definitions[i]: line_words[i+1] for i in
                                                       range(min(len(port_definitions), len(line_words), 2))},
                                          layout_name=line_words[3],
                                          layout_library=current_library)

                    self.components.append(capacitor)

                # SKY130_FD_PR_MIM capacitor
                if re.search(r'sky130_fd_pr__cap_mim', line):

                    # Create capacitor component and add extracted parameters
                    capacitor = SKY130Capacitor(name=line_words[0],
                                                schematic_connections=line_words[1:3],
                                                layout_name=re.split(r"__", line_words[3])[-1],
                                                layout_library=re.split(r"__", line_words[3])[0],
                                                width=int(''.join(re.findall(r'\d+', line_words[4]))),
                                                length=int(''.join(re.findall(r'\d+', line_words[5]))),
                                                multiplier_factor=int(''.join(re.findall(r'\d+', line_words[6]))),
                                                instance_multiplier=int(''.join(re.findall(r'\d+', line_words[7]))))

                    self.components.append(capacitor)

                # SKY130_FD_PR_HIGH_PO resistor
                if re.search(r'sky130_fd_pr__res_high_po', line):

                    # Create resistor component and add extracted parameters
                    resistor = SKY130Resistor(name=line_words[0],
                                              schematic_connections=line_words[1:4],
                                              layout_name=re.split(r"__", line_words[4])[-1],
                                              layout_library=re.split(r"__", line_words[4])[0],
                                              length=float(''.join(re.findall(r'\d.', line_words[5]))),
                                              multiplier_factor=int(''.join(re.findall(r'\d+', line_words[6]))),
                                              instance_multiplier=int(''.join(re.findall(r'\d+', line_words[7]))))

                    self.components.append(resistor)

            # Check for pins
            if re.match(r'^\*\.', line):
                line_words = line.split()

                pin_type = ''.join(re.findall(r'[a-zA-Z]+', line_words[0]))
                pin = Pin(type=pin_type, name=line_words[1])
                self.components.append(pin)

        print(f"{Text.INFO} {len(self.components)} components extracted from SPICE file")

    def get(self) -> list:
        return self.components









