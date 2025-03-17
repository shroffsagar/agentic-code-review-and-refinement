"""Logging configuration for the GitHub App."""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging() -> None:
    """Configure logging for the application.

    Sets up logging to both file and console with proper formatting.
    File logs are stored in the logs directory with rotation enabled.
    """
    # Create logs directory if it doesn't exist
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Configure logging
    log_file = os.path.join(logs_dir, "github_app.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler - 10MB per file, keep 5 backups
    file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
