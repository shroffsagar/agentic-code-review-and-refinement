"""Tests for logging configuration."""

import logging
from pathlib import Path

from agentic_code_review.utils.logging import setup_logging


def test_logging_setup(tmp_path: Path) -> None:
    """Test that logging is properly configured."""
    # Set up logging with a temporary log file
    log_file = tmp_path / "test.log"
    setup_logging(level="DEBUG", log_file=str(log_file))

    # Get the logger
    logger = logging.getLogger("agentic_code_review")

    # Test that logging works
    test_message = "Test log message"
    logger.info(test_message)

    # Verify log file exists and contains the message
    assert log_file.exists()
    log_content = log_file.read_text()
    assert test_message in log_content
