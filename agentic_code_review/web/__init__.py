"""GitHub App web package.

This package provides the web server implementation for the GitHub App.
"""

import logging

from dotenv import load_dotenv

from .github_app import GitHubApp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_app(host: str = "0.0.0.0", port: int = 3000) -> None:
    """Run the GitHub App server.

    Args:
        host: The host to bind to
        port: The port to listen on
    """
    try:
        app = GitHubApp()
        logger.info("GitHub App server initialized successfully")
        app.run(host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start GitHub App server: {e}")
        raise


__all__ = ["GitHubApp", "run_app"]
