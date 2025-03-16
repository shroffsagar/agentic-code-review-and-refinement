"""Main entry point for the GitHub App web server."""

from . import run_app


def main() -> None:
    """Main entry point for the GitHub App server."""
    run_app()


if __name__ == "__main__":
    main()
