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
2. Developer manually triggers the Review Agent workflow by assigning the PR to it using label
3. Review Agent analyzes the PR and adds inline review comments.
4. Developer reviews the AI-generated comments and approves/rejects them
5. Developer manually triggers the Refinement Agent workflow by assigning the PR to it using label
6. Refinement Agent implements approved suggestions and commits changes

## Project Development Phases

### Phase 1: Core Infrastructure Setup (Completed)
- [x] Project structure and development environment
- [x] Dependency management with Poetry
- [x] Code quality tools and standards
- [x] Testing framework and logging
- [x] Pre-commit hooks

### Phase 2: GitHub Integration & LLM Infrastructure (Completed)
- [x] GitHub App setup and authentication
- [x] Webhook handling and PR management
- [x] Agent infrastructure and state management
- [x] LLM integration with GPT-4
- [x] Review comment structure and templates

### Phase 3: Review Agent Implementation (Completed)
- [x] Code review system with LLM
- [x] PR analysis and comment posting
- [x] Response validation and parsing
- [x] Test PR creation and validation

### Phase 4: Advanced Features (Completed)
- [x] Code Analysis Foundation
  - [x] Tree-sitter-graph integration
  - [x] Graph-based code structure
  - [x] Language-agnostic analysis
  - [x] Comment processing system
- [x] Refinement Agent Core
  - [x] LLM Integration
    - [x] Code refinement prompts
    - [x] Change validation
    - [x] Test generation
  - [x] Graph-based code refinement
  - [x] Change generation and validation
  - [x] Test generation
  - [x] Comment resolution
- [x] Webhook Integration
  - [x] Event handling for refinement
  - [x] State management
  - [x] Error handling and logging
- [x] Advanced Features
  - [x] Robust node tracking with stable references
  - [x] Comprehensive code context analysis
  - [x] Multi-level validation system
  - [x] Graceful error recovery

### Scope Limitations
The system has the following scope limitations to maintain reliability and simplicity:
- Does not handle function signature changes or their impacts on dependent code
- Focuses on single-file code modifications
- Requires manual review of changes that affect multiple files
- Does not automatically update test cases

### Phase 5: Testing and Quality Assurance (In Progress)
- [x] Testing framework setup
- [x] Core component tests
- [ ] Integration and E2E tests
- [ ] Performance and security testing

### Phase 6: Documentation and Production Readiness (Not Started)
- [ ] API documentation
- [ ] User and deployment guides
- [ ] Monitoring and production setup

## Current Status

The project has completed Phases 1-4, with all core components implemented and integrated. Key achievements include:

- Complete GitHub App integration with webhook handling and PR management
- Review Agent with structured comment generation and validation
- Refinement Agent with tree-sitter-graph based code analysis and modification
- LLM integration for both review and refinement operations
- Automated workflow triggered by PR labels
- Robust error handling and validation systems
- Advanced code context analysis and signature change management

Currently working on:
1. Testing and Quality Assurance (Phase 5)
   - Implementing integration tests
   - Setting up E2E test scenarios
   - Performance optimization
   - Security testing

Next major milestone: Completing the testing phase with comprehensive integration and E2E tests to ensure the reliability and performance of the entire system.

## Implementation Details

### Code Analysis System
- Tree-sitter based parsing with stable node references
- Graph-based code structure analysis
- Language-agnostic code analysis
- Robust node validation and tracking
- Comprehensive context gathering

### Refinement Agent
- Intelligent comment grouping by code context
- Multi-level validation of code changes
- Signature change detection and handling
- Graceful error recovery and logging
- Automated comment resolution

### Error Handling
- Comprehensive error logging
- Graceful degradation
- Validation at multiple levels
- Clear error messages and recovery paths
- Transaction-like change management

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
