"""Main entry point for the GitHub App server."""

import logging
import sys

from dotenv import load_dotenv

from . import GitHubApp
from .config import setup_logging


def init() -> None:
    """Initialize the application environment.

    This function:
    1. Loads environment variables from .env file
    2. Sets up logging configuration
    """
    # Load environment variables
    load_dotenv()

    # Configure logging
    setup_logging()


def run_app(host: str = "0.0.0.0", port: int = 3000) -> None:
    """Run the GitHub App server.

    Args:
        host: The host to bind to
        port: The port to listen on
    """
    app = GitHubApp()
    app.run(host=host, port=port)


def main() -> None:
    """Main entry point for the GitHub App server.

    This function:
    1. Initializes the application environment
    2. Starts the GitHub App server
    3. Handles any startup errors
    """
    try:
        # Initialize environment
        init()

        # Get logger after setup
        logger = logging.getLogger(__name__)
        logger.info("Starting GitHub App server...")

        # Run the application
        run_app()
        return None

    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("Failed to start GitHub App server:")
        sys.exit(1)


if __name__ == "__main__":
    main()
