import os
import time
import subprocess
import re
from typing import NamedTuple
# Remember to pip install on the server if you add external libraries


class CircuitComponent(NamedTuple):
    name: str
    ports: list
    type: str

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

        updated_spice_file = []
        previous_line = ""

        for line in self.spice_file_content:

            if re.match(r'^\+', line):
                # Removes "+", any trailing/leading space and '\n' from previous line
                previous_line = previous_line.strip() + " " + line[1:].strip()

            else:
                # Append when previous line has content
                if previous_line:
                    updated_spice_file.append(previous_line.strip())

                previous_line = line

        if previous_line:
            updated_spice_file.append(previous_line.strip())

        self.spice_file_content = updated_spice_file

    def parse(self):
        self._generate_spice_file_for_schematic()
        self._read_spice_file()
        self._rebuild_spice_lines_with_plus_symbol()


        for index, line in enumerate(self.spice_file_content):
            # self.spice_file_content[index] = line

            # Check if the line does not have '*' or '.' as first character.
            if re.match(r'^[^*.]', line):
                line = line.split()

                # TODO: fix the magic 6 number

                # Transistor
                if len(line) == 6:
                    circuit_component = CircuitComponent(name=line[0], ports=line[1:5], type=line[5])
                    self.components.append(circuit_component)



        print(self.components[0])
        print(self.components[1])









