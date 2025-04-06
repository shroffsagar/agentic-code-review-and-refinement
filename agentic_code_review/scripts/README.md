# Agentic Code Review Setup Scripts

This directory contains scripts for setting up and running the Agentic Code Review and Refinement application.

## Setup Script (`setup.py`)

The interactive setup script guides users through setting up the application, including:

- Checking prerequisites (Python 3.10+, Node.js/SMEE)
- Creating a GitHub App with proper permissions
- Configuring SMEE for webhook forwarding
- Setting up LLM credentials (OpenAI)
- Creating a `.env` configuration file

### Usage

To run the setup script:

```bash
# Navigate to the project root
cd /path/to/agentic-code-review-and-refinement

# Install project dependencies
poetry install

# Run the setup script using Poetry
poetry run python -m agentic_code_review.scripts.setup
```

The script provides a guided, interactive experience, with colored output and clear instructions at each step.

### Dependencies

The setup script uses:

- [Typer](https://typer.tiangolo.com/) - For CLI interactions
- [Rich](https://rich.readthedocs.io/) - For formatted console output
- [Jinja2](https://jinja.palletsprojects.com/) - For templating the configuration file

### Platform Support

The script is designed to work on:

- macOS
- Linux (Debian/Ubuntu, RHEL/Fedora/CentOS)
- Windows

Platform-specific installation instructions are provided for each prerequisite.

## SMEE Script (`smee.sh`)

The SMEE script is used to forward GitHub webhooks to your local development environment using smee.io.

### Usage

To run the SMEE client:

```bash
# Navigate to the project root
cd /path/to/agentic-code-review-and-refinement

# Run the SMEE client using Poetry
poetry run sh agentic_code_review/scripts/smee.sh
```

The script reads the SMEE URL and target from your `.env` file, which is created by the setup script.
