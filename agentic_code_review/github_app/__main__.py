"""Main entry point for the GitHub App server."""

import logging
import sys
from typing import NoReturn

import uvicorn

from agentic_code_review.config import settings
from agentic_code_review.github_app.server import app
from agentic_code_review.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def run_app() -> NoReturn:
    """Run the GitHub App server."""
    # Set up logging with debug level if DEBUG is enabled
    log_level = "DEBUG" if settings.DEBUG else settings.LOG_LEVEL
    setup_logging(level=log_level)

    # Log startup information
    logger.info("Starting GitHub App server...")
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Host: %s", settings.HOST)
    logger.info("Port: %d", settings.PORT)
    logger.info("Debug mode: %s", "enabled" if settings.DEBUG else "disabled")

    # Run the server
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=log_level.lower(),
        debug=settings.DEBUG,
    )


if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        logger.info("Shutting down GitHub App server...")
        sys.exit(0)
    except Exception as e:
        logger.error("Error running GitHub App server: %s", str(e))
        sys.exit(1)
