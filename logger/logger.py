
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
RED = "\033[38;2;255;51;51m"
BLUE = "\033[38;2;59;92;222m"
LIGHT_BLUE = "\033[38;2;51;153;255m"
ORANGE = "\033[38;2;255;153;51m"
YELLOW = "\033[38;2;255;255;70m"
# =================================================== Logging ==========================================================


def get_a_logger(name):
    """Returns a custom dynamic logger with the given name"""

    color_table = {
        "__main__": RED,
        "circuit.circuit_spice_parser": LIGHT_GREEN,
        "magic.magic_component_parser": LIGHT_BLUE,
        "json_tool.json_converter": ORANGE,
        "magic.magic_layout_creator": YELLOW
    }

    file_spcific_color = color_table.get(name, WHITE)

    # Create a logger and set default level
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Create a custom formatter with the dynmaic file color
    formatter = CustomFormatter(file_color=file_spcific_color)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Get log-level from command line option
    parser = argparse.ArgumentParser(description="Set log level from command line")
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log-level override'
    )
    args = parser.parse_args()

    # Override log level if log level argument is provided
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

