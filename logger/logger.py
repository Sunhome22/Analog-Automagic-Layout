import logging
import logging.config
import argparse
import sys

class CustomFormatter(logging.Formatter):
    INFO = f"\033[38;2;{0};{255};{150}\033[0m"
    ERROR = f"\033[38;2;{220};{0};{0}m{'[ERROR]:'}\033[0m"
    DEBUG = f"\033[38;2;0;100;255m"
    WHITE = f"\033[0m"
    SPICE_PARSER = f"\033[38;2;{0};{160};{140}m{'|SPICE_PARSER|'}\033[0m"
    MAGIC_PARSER = f"\033[38;2;{0};{120};{200}m{'|MAGIC_PARSER|'}\033[0m"
    LAYOUT_CREATOR = f"\033[38;2;{232};{232};{24}m{'|LAYOUT_CREATOR|'}\033[0m"
    JSON_CONVERTER = f"\033[38;2;{136};{39};{220}m{'|JSON_CONVERTER|'}\033[0m"

    reset = "\x1b[1m"
    log_format = f"[%(asctime)s] [%(name)s] [%(levelname)s]:{WHITE} %(message)s"

    FORMATS = {
        logging.DEBUG: f"{DEBUG}{log_format}",
        logging.INFO: INFO + log_format + reset,
        logging.WARNING: ERROR + log_format + reset,
        logging.ERROR: ERROR + log_format + reset,
        logging.CRITICAL: ERROR + log_format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.reset + self.log_format + self.reset)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# Get log-level from command line option
parser = argparse.ArgumentParser(description="Set log level from command line")
parser.add_argument(
    '--log-level',
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    help='Log-level override'
)
args = parser.parse_args()

# Configure logging
def configure_logging():
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Default level

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Handler level
    console_handler.setFormatter(CustomFormatter())  # Set custom formatter

    # Add handler to the logger
    logger.addHandler(console_handler)

    # Override log level if --log-level argument is provided
    if args.log_level:
        log_level = getattr(logging, args.log_level)
        logger.setLevel(log_level)

configure_logging()

def get_logger(name):
    """Return a logger with the specified name."""
    return logging.getLogger(name)


