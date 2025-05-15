# ==================================================================================================================== #
# Copyright (C) 2025 Bjørn K.T. Solheim, Leidulv Tønnesland
# ==================================================================================================================== #
# This program is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.
# ==================================================================================================================== #

import re

input_file = "src/utils/input_log.txt"
output_file = "src/utils/latex_formated_log.txt"

WHITE = "\033[0m"
GREY = "\033[38;2;128;128;128m"
GREEN = "\033[38;2;0;153;76m"
LIGHT_GREEN = "\033[38;2;102;204;0m"
DARK_GREEN = "\033[38;2;0;102;0m"
RED = "\033[38;2;255;51;51m"
BLUE = "\033[38;2;59;92;222m"
LIGHT_BLUE = "\033[38;2;51;153;255m"
VERY_LIGHT_BLUE = "\033[38;2;204;229;255m"
ORANGE = "\033[38;2;255;153;51m"
LIGHT_ORANGE = "\033[38;2;255;204;153m"
YELLOW = "\033[38;2;255;255;70m"
LIGHT_YELLOW = "\033[38;2;255;255;102m"
PURPLE = "\033[38;2;153;51;255m"
LIGHT_PURPLE = "\033[38;2;153;153;255m"
CYAN = "\033[38;2;0;204;204m"
DARK_CYAN = "\033[38;2;0;153;153m"

color_map = {
    GREY: "grey",
    GREEN: "green",
    LIGHT_GREEN: "light_green",
    DARK_GREEN: "dark_green",
    RED: "red",
    BLUE: "blue",
    LIGHT_BLUE: "light_blue",
    VERY_LIGHT_BLUE: "very_light_blue",
    ORANGE: "orange",
    LIGHT_ORANGE: "light_orange",
    YELLOW: "yellow",
    LIGHT_YELLOW: "light_yellow",
    PURPLE: "purple",
    LIGHT_PURPLE: "light_purple",
    CYAN: "cyan",
    DARK_CYAN: "dark_cyan",
}

# Color table using ANSI codes
color_table = {
        "__main__": RED,
        "circuit.circuit_spice_parser": LIGHT_GREEN,
        "magic.magic_component_parser": LIGHT_BLUE,
        "json_converter.json_converter": ORANGE,
        "magic.magic_layout_creator": LIGHT_YELLOW,
        "linear_optimization.linear_optimization": VERY_LIGHT_BLUE,
        "connections.connections": CYAN,
        "astar.a_star_initiator": BLUE,
        "grid.generate_grid": LIGHT_PURPLE,
        "drc.drc_checker": DARK_CYAN,
        "lvs.lvs_checker": DARK_GREEN,
        "libraries.library_handling": LIGHT_ORANGE
    }


timestamp_re = re.compile(r"^\[(.*?)\]")
level_re = re.compile(r"\[(INFO|DEBUG|WARNING|ERROR|CRITICAL)\]")
module_re = re.compile(r"\[([a-zA-Z0-9_.]+)\]:")


def escape_latex(text):
    return text.replace('_', r'\_')


def get_latex_color_for_module(module_name):
    ansi_color = color_table.get(module_name, "\033[38;2;0;0;0m")  # fallback black
    return color_map.get(ansi_color, "black")  # fallback LaTeX color


output_lines = []

with open(input_file, 'r') as infile:
    for line in infile:
        timestamp_match = timestamp_re.search(line)
        level_match = level_re.search(line)
        module_match = module_re.search(line)

        if not (timestamp_match and level_match and module_match):
            print(f"Skipping malformed line: {line.strip()}")
            continue

        timestamp = f"[{timestamp_match.group(1)}]"
        level = level_match.group(0)
        module = module_match.group(1)
        module_display = f"[{module}]:"

        message_start = line.find(module_display) + len(module_display)
        message = line[message_start:].strip()

        timestamp_latex = escape_latex(timestamp)
        level_latex = escape_latex(level)
        module_latex = escape_latex(module_display)

        module_color = get_latex_color_for_module(module)

        formatted_line = (
            f"(*@\\textcolor{{grey}}{{{timestamp_latex}}}@*) "
            f"(*@\\textcolor{{green}}{{{level_latex}}}@*) "
            f"(*@\\textcolor{{{module_color}}}{{{module_latex}}}@*) "
            f"{message}"
        )

        output_lines.append(formatted_line + "\n")

with open(output_file, 'w') as outfile:
    outfile.writelines(output_lines)

print(f"Formatted log saved to '{output_file}'")
