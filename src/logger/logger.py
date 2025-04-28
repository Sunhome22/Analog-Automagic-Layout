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
import logging
import logging.config
import argparse
import sys
# ============================================ Custom Color constants ==================================================
WHITE = "\033[0m"
GREY = "\033[38;2;128;128;128m"
GREEN = "\033[38;2;0;153;76m"
LIGHT_GREEN = "\033[38;2;102;204;0m"
DARK_GREEN = "\033[38;2;0;102;0m"
RED = "\033[38;2;255;51;51m"
BLUE = "\033[38;2;59;92;222m"
LIGHT_BLUE = "\033[38;2;51;153;255m"
ORANGE = "\033[38;2;255;153;51m"
LIGHT_ORANGE = "\033[38;2;255;204;153m"
YELLOW = "\033[38;2;255;255;70m"
PURPLE = "\033[38;2;153;51;255m"
CYAN = "\033[38;2;0;204;204m"
DARK_CYAN = "\033[38;2;0;153;153m"
PINK = "\033[38;2;255;51;255m"
# =================================================== Logging ==========================================================


def get_a_logger(name):
    """Returns a custom dynamic logger with the given file name"""

    color_table = {
        "__main__": RED,
        "circuit.circuit_spice_parser": LIGHT_GREEN,
        "magic.magic_component_parser": LIGHT_BLUE,
        "json_converter.json_converter": ORANGE,
        "magic.magic_layout_creator": YELLOW,
        "linear_optimization.linear_optimization": PURPLE,
        "connections.connections": CYAN,
        "astar.a_star": BLUE,
        "grid.generate_grid": PINK,
        "drc.drc_checker": DARK_CYAN,
        "lvs.lvs_checker": DARK_GREEN,
        "traces.trace_generator": LIGHT_ORANGE
    }

    file_specific_color = color_table.get(name, WHITE)

    # Create a logger and set default level
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create a custom formatter with the dynamic file color
    formatter = CustomFormatter(file_color=file_specific_color)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Get log-level options in command line
    parser = argparse.ArgumentParser(description="Set log level from command line")
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log-level override'
    )
    args = parser.parse_args()

    # Override if log level argument is provided
    if args.log_level:
        log_level = getattr(logging, args.log_level)
        logger.setLevel(log_level)

    return logger


class CustomFormatter(logging.Formatter):

    def __init__(self, file_color):
        super().__init__()
        self.file_color = file_color

        self.FORMATS = {
            logging.DEBUG: f"{GREY}[%(asctime)s] {BLUE}[%(levelname)s] {self.file_color}[%(name)s]:{WHITE} %(message)s",

            logging.INFO: f"{GREY}[%(asctime)s] {GREEN}[%(levelname)s] {self.file_color}[%(name)s]:{WHITE} %(message)s",

            logging.WARNING: f"{GREY}[%(asctime)s] {YELLOW}[%(levelname)s] "
                             f"{self.file_color}[%(name)s]:{WHITE} %(message)s",

            logging.ERROR: f"{GREY}[%(asctime)s] {RED}[%(levelname)s] {self.file_color}[%(name)s]:{WHITE} %(message)s",

            logging.CRITICAL: f"{GREY}[%(asctime)s] {RED}[%(levelname)s] "
                              f"{self.file_color}[%(name)s]:{WHITE} %(message)s"
        }

    def format(self, log_record):
        log_format = self.FORMATS.get(log_record.levelno, self.FORMATS[logging.DEBUG])

        # Create a formatter using the selected format
        formatter = logging.Formatter(log_format)
        return formatter.format(log_record)

