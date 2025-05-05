import re

input_file = "src/utils/input_log.txt"
output_file = "src/utils/latex_formated_log.txt"

color_map = {
    "\033[38;2;128;128;128m": "grey",
    "\033[38;2;0;153;76m": "green",
    "\033[38;2;102;204;0m": "light_green",
    "\033[38;2;0;102;0m": "dark_green",
    "\033[38;2;255;51;51m": "red",
    "\033[38;2;59;92;222m": "blue",
    "\033[38;2;51;153;255m": "light_blue",
    "\033[38;2;255;153;51m": "orange",
    "\033[38;2;255;204;153m": "light_orange",
    "\033[38;2;255;255;70m": "yellow",
    "\033[38;2;153;51;255m": "purple",
    "\033[38;2;0;204;204m": "cyan",
    "\033[38;2;0;153;153m": "dark_cyan",
    "\033[38;2;255;51;255m": "pink",
}

# Color table using ANSI codes
color_table = {
    "__main__": "\033[38;2;255;51;51m",  # RED
    "circuit.circuit_spice_parser": "\033[38;2;102;204;0m",  # LIGHT_GREEN
    "magic.magic_component_parser": "\033[38;2;51;153;255m",  # LIGHT_BLUE
    "json_converter.json_converter": "\033[38;2;255;153;51m",  # ORANGE
    "magic.magic_layout_creator": "\033[38;2;255;255;70m",  # YELLOW
    "linear_optimization.linear_optimization": "\033[38;2;153;51;255m",  # PURPLE
    "connections.connections": "\033[38;2;0;204;204m",  # CYAN
    "astar.a_star": "\033[38;2;59;92;222m",  # BLUE
    "grid.generate_grid": "\033[38;2;255;51;255m",  # PINK
    "drc.drc_checker": "\033[38;2;0;153;153m",  # DARK_CYAN
    "lvs.lvs_checker": "\033[38;2;0;102;0m",  # DARK_GREEN
    "traces.trace_generator": "\033[38;2;255;204;153m",  # LIGHT_ORANGE
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