# TODO: Add copyright/license notice

# ==== Personal Notes ====:
# CMOS Transistors need to be from Carsten's generated transistor library (JNWATR)
# BJT Transistors not handled yet
# Capacitors need to be of the standard library type or from Carsten's generated library (JNWTR)
# Resistors need to be of the standard  library type or from Carsten's generated library (JNWTR)

# Remember to pip install external libraries to the server if used

# Libraries
import os
import subprocess
import re
from dataclasses import dataclass
from typing import List


# Constants
TRANSISTOR_PARAMS = 6
RESISTOR_PARAMS = 5
CAPACITOR_PARAMS = 4
STD_CAPACITOR_PARAMS = 8
STD_RESISTOR_PARAMS = 8

# Circuit component classes
@dataclass
class CircuitComponent:
    name: str
    connections: List[str]
    layout: str

@dataclass
class Transistor(CircuitComponent):
    pass

@dataclass
class Resistor(CircuitComponent):
    pass

@dataclass
class Capacitor(CircuitComponent):
    pass

@dataclass
class STDCapacitor(CircuitComponent):
    width : int
    length: int
    multiplier_factor: int
    instance_multiplier: int

@dataclass
class STDResistor(CircuitComponent):
    pass

@dataclass
class Pin:
    type: str
    name: str


class SPICEparser:

    def __init__(self, project_name: str, project_dir: str):
        self.project_name = project_name
        self.project_dir = project_dir
        self.spice_file_content = list()
        self.components = list()

        self.parse()

    def _generate_spice_file_for_schematic(self):
        work_dir = os.path.expanduser(f"{self.project_dir}work/")

        # Run SPICE generation command from work directory of project
        try:
            subprocess.run(['make xsch'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                    check=True, shell=True, cwd=work_dir)
            print("[INFO]: SPICE file generated from schematic")

        except subprocess.CalledProcessError as e:
            print(f"[ERROR]: 'make xsch' command failed with: {e.stderr}")

    def _read_spice_file(self):

        try:
            spice_file_path = os.path.expanduser(f"{self.project_dir}work/xsch/{self.project_name}.spice")

            # Copy each line of the file into a list
            with open(spice_file_path, "r") as spice_file:
                for line in spice_file:
                    self.spice_file_content.append(line)

        except FileNotFoundError:
            print(f"[ERROR]: The file '{self.project_dir}work/xsch/{self.project_name}.spice' was not found.")

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

    def _remove_expanded_spice_file_symbols(self):
        in_expanded_symbol = False
        updated_spice_lines = []

        for line in self.spice_file_content:

            if re.match(r'^\* expanding', line.strip()):
                in_expanded_symbol = True

            elif re.match(r'^\.ends', line.strip()) and in_expanded_symbol:
                in_expanded_symbol = False

            elif not in_expanded_symbol and line.strip():
                updated_spice_lines.append(line.strip())

        self.spice_file_content = updated_spice_lines


    def parse(self):
        self._generate_spice_file_for_schematic()
        self._read_spice_file()
        self._rebuild_spice_lines_with_plus_symbol()
        self._remove_expanded_spice_file_symbols()

        for line in self.spice_file_content:

            # Check for components
            if re.match(r'^[^*.]', line):
                line_words = line.split()

                # Transistor
                if len(line_words) == TRANSISTOR_PARAMS:
                    transistor = Transistor(name=line_words[0], connections=line_words[1:5], layout=line_words[5])
                    self.components.append(transistor)

                # Resistor
                if len(line_words) == RESISTOR_PARAMS:
                    resistor = Resistor(name=line_words[0], connections=line_words[1:4], layout=line_words[4])
                    self.components.append(resistor)

                # Capacitor
                if len(line_words) == CAPACITOR_PARAMS:
                    capacitor = Capacitor(name=line_words[0], connections=line_words[1:3], layout=line_words[3])
                    self.components.append(capacitor)

                # Standard capacitor
                if len(line_words) == STD_CAPACITOR_PARAMS:
                    capacitor = STDCapacitor(name=line_words[0],
                                          connections=line_words[1:3],
                                          layout=line_words[3],
                                          width=int(''.join(re.findall(r'\d+', line_words[4]))),
                                          length=int(''.join(re.findall(r'\d+', line_words[5]))),
                                          multiplier_factor=int(''.join(re.findall(r'\d+', line_words[6]))),
                                          instance_multiplier=int(''.join(re.findall(r'\d+', line_words[7]))))

                    self.components.append(capacitor)

                # Standard resistor
                # TBD

            # Check for pins
            if re.match(r'^\*\.', line):
                line_words = line.split()

                # Minimum length for self-defined pins is 2 chars
                if len(line_words[1]) > 1:
                    pin_type = ''.join(re.findall(r'[a-zA-Z]+', line_words[0]))
                    pin = Pin(type=pin_type, name=line_words[1])
                    self.components.append(pin)

        print(f"[INFO]: {len(self.components)} components extracted from SPICE file")

    def get(self):
        return self.components









