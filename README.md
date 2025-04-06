# GitHub AI Agent: Automated Code Review & Refinement

<p align="center">
  <img src="docs/assets/branding/logo.png" alt="GitHub AI Agent Logo" width="300"/>
</p>

## Overview

GitHub AI Agent is an advanced AI-powered system that integrates seamlessly with GitHub's ecosystem to provide automated code review and intelligent code refinement. Leveraging the latest LLM technology, the system analyzes pull requests, provides actionable feedback, and automatically implements approved suggestions.

## System Workflow

Our system follows a structured workflow that ensures thorough code analysis and safe code modifications:

<p align="center">
  <img src="docs/assets/Review-Refine Agentic Workflow.png" alt="Agentic Workflow Diagram" width="800"/>
</p>

The workflow consists of several key stages:
1. **Review Agent** analyzes code changes and generates contextual review comments
2. **Human Review** allows developers to review and filter AI-generated suggestions
3. **Refinement Agent** implements approved suggestions with AST-based code modifications
4. **Validation & Patching** ensures all changes are syntactically correct and safe

You can view and edit this workflow diagram in Excalidraw: [Agentic Workflow Diagram](https://excalidraw.com/#json=j_Ux1w5GRoAXlZYd1Bg7H,7BO-L7FDAoX4mqf93yQ8-Q)

## Key Features

- **Intelligent Code Review**: Automatically analyzes pull requests and provides detailed, contextual code review comments
- **Automated Code Refinement**: Implements approved suggestions directly into your codebase
- **GitHub Integration**: Seamlessly works within the GitHub PR workflow using labels and comments
- **Language Agnostic**: Supports multiple programming languages through tree-sitter integration (Python, JavaScript/TypeScript, Java)
- **Human-in-the-Loop**: Maintains human oversight with approval mechanisms for all automated changes
- **Context-Aware Analysis**: Understands code structure and relationships between components

## Getting Started

### Local Installation

Follow these steps to set up and run the GitHub AI Agent on your local machine:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/shroffsagar/agentic-code-review-and-refinement.git
   cd agentic-code-review-and-refinement
   ```

2. **Run the interactive setup script**:
   ```bash
   python agentic_code_review/scripts/setup.py
   ```
   
   This script will guide you through:
   - Checking and installing prerequisites (Python 3.10+, Poetry, SMEE client)
   - Creating a GitHub App and configuring permissions
   - Setting up SMEE for webhook forwarding
   - Configuring your LLM provider credentials
   - Creating the environment configuration file
   
   The script will help install any missing prerequisites with your permission.

3. **Start the application**:
   
   In one terminal, start the SMEE webhook forwarder:
   ```bash
   poetry run sh agentic_code_review/scripts/smee.sh
   ```

   In another terminal, run the GitHub App server:
   ```bash
   poetry run python -m agentic_code_review.github_app
   ```

4. **Install your GitHub App** on the repositories you want to review

5. **Trigger a review** by adding the `agentic-review` label to a pull request

For more detailed setup instructions, see the [Installation Guide](docs/installation.md).

### Installing the GitHub AI Agent (Coming Soon)

> **Note:** The GitHub AI Agent is currently in beta. The following installation steps will be available once the service is publicly launched.

1. Visit our [GitHub App installation page](https://github.com/shroffsagar/agentic-code-review-and-refinement)
2. Click "Install" and select the repositories you want to enable the agent on
3. Grant the required permissions when prompted
4. You're all set! The agent is now ready to review your pull requests
5. No local setup, configuration, or API keys required - everything is managed by our centrally hosted service.

## Usage

### Triggering Code Review

1. Open a Pull Request in your repository
2. Add the `agentic-review` label to the PR
3. The Review Agent will analyze the code and add comments

### Triggering Code Refinement

1. Review the AI-generated comments
2. Resolve any comments you disagree with
3. Add the `agentic-refine` label to the PR
4. The Refinement Agent will implement the remaining suggestions

## Review Comment Categories

Review comments are categorized into:
- **Bugs**: Potential logic errors or runtime issues
- **Security**: Security vulnerabilities or concerns
- **Performance**: Code efficiency and performance issues
- **Style**: Code style and formatting concerns
- **Architecture**: Design and structural improvements

## Current Limitations and Future Improvements

The GitHub AI Agent is powerful but has some current limitations we're actively working to address:

| Limitation | Details | Status |
|------------|---------|--------|
| **Function Signature Changes** | The Refinement Agent skips suggestions that would modify function signatures to avoid breaking dependent code | Planned for future release |
| **Single-file Focus** | Currently limited to modifications within one file at a time | Planned for future release |
| **Test Generation** | Does not automatically create or update test cases for modified code | Under consideration |
| **Manual Review Required** | Changes affecting multiple files need human review and manual implementation | By design (safety feature) |

These limitations ensure safe, reliable operation while we continue to enhance the system's capabilities.

## Support

For issues, questions, or feature requests, please open an issue on the GitHub repository.
