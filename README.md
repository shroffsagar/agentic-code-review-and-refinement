# Agentic Code Review and Refinement System

A sophisticated AI-powered system for automated code review and refinement, integrating with GitHub's ecosystem to provide intelligent code analysis and improvement suggestions.

## System Design

The following diagram illustrates the high-level architecture and workflow of the Agentic Code Review and Refinement System:

[High level flow](https://excalidraw.com/#room=4dd1c0e4005f7423fa9e,y147i26ttB-UIqxbYdifxw)
![High level flow](docs/assets/Design%20-%20Code%20Review%20%26%20Refinement%20Agent.png)

---
[Sequence diagram for refinement](https://excalidraw.com/#json=5ZTVdYF8S7wBNruJcUFj3,w8Nr423cho_GauPzmjNmQw)
![Sequence diagram - AST (using treesitter) + Model based refinement](docs/assets/Seq%20diagram%20-%20Refinement%20agent.png)

## User Workflow

1. Developer opens a Pull Request
2. Developer manually triggers the Review Agent workflow by adding the `agentic-review` label
3. Review Agent analyzes the PR and adds inline review comments
4. Developer reviews the AI-generated comments and resolves any irrelevant ones
5. Developer manually triggers the Refinement Agent workflow by adding the `agentic-refine` label
6. Refinement Agent implements approved suggestions and commits changes

## Project Development Phases

### Phase 1: Core Infrastructure Setup (Completed)
- [x] Project structure and development environment
- [x] Dependency management with Poetry
- [x] Code quality tools integration (Ruff, pre-commit)
- [x] Testing framework and logging setup
- [x] Environment management with Poetry

### Phase 2: GitHub Integration & LLM Infrastructure (Completed)
- [x] GitHub App configuration and authentication
- [x] Webhook handling for PR events
- [x] PR comment and file management
- [x] LLM integration with OpenAI API
- [x] Configuration management with Pydantic

### Phase 3: Review Agent Implementation (Completed)
- [x] LLM-based code review system
- [x] Structured PR analysis
- [x] Detailed inline comment generation
- [x] Comment formatting and categorization

### Phase 4: Advanced Refinement Features (Completed)
- [x] Tree-sitter Integration
  - [x] Language-agnostic code parsing
  - [x] Node-based code structure representation
  - [x] Multi-language support
- [x] Context Extraction
  - [x] Intelligent code unit identification
  - [x] Comprehensive context gathering
  - [x] Code structure analysis
- [x] Incremental Code Patching
  - [x] Node-based code modifications
  - [x] Stable references for tracking changes
  - [x] Robust validation of modifications
- [x] Advanced Comment Processing
  - [x] Semantic grouping of related comments
  - [x] Code-unit aware processing
  - [x] Intelligent comment resolution
- [x] Robust Error Handling
  - [x] Graceful degradation for unsupported languages
  - [x] Detailed error reporting and logging
  - [x] Multiple validation layers

### Scope Limitations
The system has the following scope limitations to maintain reliability and simplicity:
- Does not handle function signature changes or their impacts on dependent code
- Focuses on single-file code modifications
- Requires manual review of changes that affect multiple files
- Does not automatically update test cases

### Phase 5: Testing and Quality Assurance (In Progress)
- [x] Testing framework setup with pytest
- [x] Core component unit tests
- [ ] Integration and E2E tests
- [ ] Performance and security testing

### Phase 6: Documentation and Production Readiness (Not Started)
- [ ] API documentation
- [ ] User and deployment guides
- [ ] Monitoring and production setup

## Current Status

The project has completed Phases 1-4, with all core components implemented and integrated. Key achievements include:

- Complete GitHub App integration with webhooks for PR label events
- Review Agent that generates structured, actionable code review comments
- Refinement Agent with tree-sitter based code analysis and modification
- Language-agnostic implementation supporting multiple programming languages
- Intelligent comment processing that groups related suggestions by code units
- Incremental patching system that preserves code structure
- Robust error handling and validation throughout the process

Currently working on:
1. Testing and Quality Assurance (Phase 5)
   - Implementing integration tests
   - Setting up E2E test scenarios
   - Performance optimization
   - Security testing

Next major milestone: Completing the testing phase with comprehensive integration and E2E tests to ensure the reliability and performance of the entire system.

## Implementation Details

### GitHub App Integration
- Webhook handling for PR label events
- PR comment management and resolution
- File content retrieval and modification
- State management to prevent concurrent operations

### LLM Integration
- OpenAI API integration with structured prompts
- Response validation and parsing
- Type-safe models using Pydantic
- Configurable temperature and token settings

### Code Analysis System
- Tree-sitter based parsing for multiple languages
- Context extraction based on code structure
- Intelligent code unit identification
- Support for imports and structural changes

### Refinement Agent
- Comment grouping by semantic code units
- Multi-stage validation of code changes
- Incremental patching with tree-sitter nodes
- Robust error recovery and detailed reporting

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
