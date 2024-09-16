import os
import time
import subprocess
# Remember to pip install on the server if you add external libraries


class SPICEparser:

    def __init__(self, project_name: str, project_dir: str):
        self.project_name = project_name
        self.project_dir = project_dir
        self.spice_file_content = list()
        self.components = dict()

        self.parse()

    def _generate_spice_file_for_schematic(self):
        work_dir = os.path.expanduser(f"{self.project_dir}work/")

        # Run SPICE generation script from work directory of project
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
            print(f"Error: The file '{self.project_dir}work/xsch/{self.project_name}.spice' was not found.")

    def parse(self):
        self._generate_spice_file_for_schematic()
        # self._read_spice_file()

        # temp printing
        #for index, line in enumerate(self.spice_file_content):
        #    print(self.spice_file_content[index])






