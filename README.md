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
2. Developer manually triggers the Review Agent workflow from GitHub Actions
3. Review Agent analyzes the PR and adds inline review comments
4. Developer reviews the AI-generated comments and approves/rejects them
5. Developer manually triggers the Refinement Agent workflow
6. Refinement Agent implements approved suggestions and commits changes

## Project Development Phases

### Phase 1: Core Infrastructure Setup (Completed)
- [x] Project structure initialization
- [x] Development environment configuration
- [x] Dependency management setup with `Poetry`
- [x] Code quality tools integration (Ruff)
- [x] Type hinting and documentation standards
- [x] Testing framework setup with pytest
- [x] Logging system implementation
- [x] Pre-commit hooks for automated quality checks

### Phase 2: GitHub Integration & LLM Infrastructure (Completed)
- [x] Basic GitHub API integration for PR access
  - [x] GitHub App setup and authentication
  - [x] Webhook handling and event processing
  - [x] PR state management and context handling
- [x] Agent infrastructure implementation:
  - [x] Base agent handler structure
  - [x] PR manager for GitHub operations
  - [x] Decorator-based state management
  - [x] Configuration management
- [x] Basic error handling and logging
- [x] Core LLM Infrastructure
  - [x] OpenAI GPT-4 client setup with secure authentication
  - [x] Review comment structure definition
  - [x] Basic prompt templates for code review

### Phase 3: Review Agent Implementation (Completed)
- [x] LLM-based code review system
  - [x] Code diff analysis architecture
  - [x] Context-aware prompt generation
  - [x] Structured review comment formatting
- [x] Review process implementation
  - [x] PR content analysis
  - [x] Comment posting system
  - [x] Test PR creation and agent interaction
- [x] Response validation and parsing

### Phase 4: Refinement Agent Implementation (In Progress)
- [ ] Refinement agent prompt design
  - [ ] Core refinement prompt template
  - [ ] Structured suggestion format
  - [ ] Function signature change detection
- [ ] Comment processing system
  - [ ] Retrieval of unresolved comments
  - [ ] Comment categorization and prioritization
  - [ ] Grouping suggestions by syntactic unit
- [ ] Code refinement implementation
  - [ ] Design of two-stage approach for handling signature changes
  - [ ] Tree-sitter integration for code analysis
    - [ ] Syntactic unit extraction
    - [ ] Function signature parsing
    - [ ] Dependency identification
  - [ ] Syntactic unit-based refinement
    - [ ] Unit-level change generation
    - [ ] Structural integrity validation
    - [ ] Dependency update handling
  - [ ] AST-based structural patching for applying changes
  - [ ] Test generation for code changes
  - [ ] Change validation
- [ ] Automated comment resolution after successful changes

### Phase 5: Workflow Automation & Integration (Not Started)
- [ ] GitHub Actions workflows implementation
  - [ ] Review workflow
  - [ ] Refinement workflow
  - [ ] Combined workflow with manual approval step
- [ ] Authentication and security enhancements
- [ ] Error handling and retry mechanisms

### Phase 6: Testing and Quality Assurance (In Progress)
- [x] Initial testing framework setup
- [x] Unit test suite for core components
- [ ] Integration tests
- [ ] End-to-end testing
- [ ] Performance testing
- [ ] Security testing

### Phase 7: Documentation and Production Readiness (Not Started)
- [ ] API documentation
- [ ] User guides
- [ ] Deployment guides
- [ ] Monitoring setup
- [ ] Production environment configuration

## Current Status

The project has completed Phases 1-3 and is now in the early stages of Phase 4, designing the Refinement Agent. Key components include:

- GitHub App infrastructure with authentication and webhook handling
- PR state management and context handling system
- Base agent structure for review operations
- Decorator-based operation management
- Logging and configuration systems
- LLM integration with OpenAI's GPT-4
- Structured review comment formatting
- End-to-end PR review process with comment posting

Currently working on:
1. Designing the Refinement Agent (Phase 4)
   - Defining refinement prompt templates for code modification
   - Planning the syntactic unit-based approach for more coherent changes
   - Evaluating Tree-sitter integration for syntactic code analysis
   - Designing the comment processing system to handle unresolved suggestions

Next major milestone: Implementing the core Refinement Agent functionality with the ability to process unresolved review comments and make targeted code modifications.
