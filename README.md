# GitHub AI Agent: Automated Code Review & Refinement

<p align="center">
  <img src="docs/assets/branding/logo.png" alt="GitHub AI Agent Logo" width="300"/>
</p>

## Overview

GitHub AI Agent is an advanced AI-powered system that integrates seamlessly with GitHub's ecosystem to provide automated code review and intelligent code refinement. Leveraging the latest LLM technology, the system analyzes pull requests, provides actionable feedback, and automatically implements approved suggestions.

## Key Features

- **Intelligent Code Review**: Automatically analyzes pull requests and provides detailed, contextual code review comments
- **Automated Code Refinement**: Implements approved suggestions directly into your codebase
- **GitHub Integration**: Seamlessly works within the GitHub PR workflow using labels and comments
- **Language Agnostic**: Supports multiple programming languages through tree-sitter integration (Python, JavaScript/TypeScript, Java)
- **Human-in-the-Loop**: Maintains human oversight with approval mechanisms for all automated changes
- **Context-Aware Analysis**: Understands code structure and relationships between components

## Getting Started

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
