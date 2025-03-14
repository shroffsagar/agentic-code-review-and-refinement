"""Logging configuration for the Agentic Code Review system."""

import logging
import sys
from typing import Optional

from rich.logging import RichHandler


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """Configure logging for the application.
    
    Args:
        level: The logging level to use (default: "INFO")
        log_file: Optional path to a log file (default: None)
    """
    # Create logger
    logger = logging.getLogger("agentic_code_review")
    logger.setLevel(level)

    # Create formatters
    rich_formatter = logging.Formatter(
        "%(message)s",
        datefmt="[%X]",
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create handlers
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=False,
        show_path=False,
    )
    console_handler.setFormatter(rich_formatter)
    logger.addHandler(console_handler)

    # Add file handler if log_file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler) 