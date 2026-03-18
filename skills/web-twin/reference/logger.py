"""Logging configuration for webtwin."""

import logging
import sys

# Create logger
logger = logging.getLogger("webtwin")


def setup_logger(level: int = logging.INFO, format_style: str = "simple") -> None:
    """
    Setup webtwin logger.

    Args:
        level: Logging level (default: INFO)
        format_style: "simple" for minimal output, "detailed" for debug info
    """
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Choose format
    if format_style == "detailed":
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        datefmt = "%H:%M:%S"
    else:
        fmt = "%(message)s"
        datefmt = None

    formatter = logging.Formatter(fmt, datefmt=datefmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# Default setup
setup_logger()
