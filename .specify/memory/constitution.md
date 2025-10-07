<!--
Sync Impact Report:
Version: 1.0.0 (Initial constitution)
Modified Principles: N/A (Initial creation)
Added Sections: All sections (initial creation)
Removed Sections: N/A
Templates Status:
- ✅ .specify/templates/plan-template.md (No updates needed - constitution-agnostic)
- ✅ .specify/templates/spec-template.md (No updates needed - constitution-agnostic)
- ✅ .specify/templates/tasks-template.md (No updates needed - constitution-agnostic)
- ✅ .specify/templates/agent-file-template.md (No updates needed - constitution-agnostic)
Follow-up TODOs: None
-->

# Bedrock AgentCore Starter Toolkit Constitution

## Core Principles

### I. Three-Layer Architecture

All code MUST follow the CLI → Operations → Services → Utilities layer separation. Each layer has a single responsibility: CLI handles user interaction and display; Operations orchestrate business logic and multi-step workflows; Services provide AWS API abstractions; Utilities offer pure functions with no external dependencies.

**Rationale**: Clear separation prevents business logic leakage into presentation layers, enables independent testing of each layer, and maintains clean dependency flows that support maintainability and extensibility.

### II. Idempotent Operations

All resource management operations MUST follow the check-then-create pattern. Operations can be safely executed multiple times without side effects. Resource existence checks precede creation attempts, and configuration updates are persisted immediately after successful operations.

**Rationale**: Idempotent operations ensure reliable deployment workflows, enable safe retry mechanisms, and prevent resource duplication or inconsistent states during partial failures.

### III. Test-First Quality (NON-NEGOTIABLE)

Minimum 90% test coverage with branch coverage is MANDATORY. All functions MUST have complete type annotations. Pre-commit hooks enforce: linting (ruff), formatting, type checking (mypy), security scanning (bandit), and test execution. No code merges without passing all quality gates.

**Rationale**: High test coverage prevents regressions, type safety reduces runtime errors, and automated quality gates maintain consistent code standards across all contributors.

### IV. CLI-First Interface

All functionality MUST be accessible via command-line interface. Commands follow the pattern: `agentcore <verb> [options]` with consistent error handling, rich console output, and help documentation. No functionality exists only in library form.

**Rationale**: CLI-first design ensures all features are user-accessible, provides consistent interaction patterns, and enables automation through scripting and CI/CD integration.

### V. AWS-Native Integration

All AWS operations MUST use boto3 sessions for testability and credential management. Resource naming follows AWS conventions with consistent prefixes. IAM roles use least-privilege access patterns. All resources support tagging for cost allocation and governance.

**Rationale**: AWS-native integration ensures enterprise-grade security, compliance with AWS best practices, and seamless integration with existing AWS infrastructure and tooling.

### VI. Security by Design

Security scanning (bandit) runs on every commit. Credentials are never logged or stored in configuration files. All HTTP operations use secure protocols. Input validation occurs at CLI boundaries. AWS operations follow principle of least privilege.

**Rationale**: Security-first design prevents vulnerabilities from reaching production, protects sensitive data through secure handling practices, and ensures compliance with enterprise security requirements.

## Development Standards

### Code Quality Requirements

All code MUST maintain these standards:
- 90% test coverage with branch coverage analysis
- Complete type annotations for all functions and methods
- Google-style docstrings for all public APIs
- Ruff linting compliance with 120-character line limits
- Bandit security scanning with no high/medium findings
- Pre-commit hook validation before any commits

### Architecture Compliance

Layer violations are PROHIBITED:
- CLI layer CANNOT import from Services layer directly
- Utilities layer CANNOT make AWS API calls
- Services layer CANNOT handle user interaction
- Cross-layer imports MUST follow the defined dependency hierarchy

### Configuration Management

Configuration persistence follows strict patterns:
- YAML configuration files with Pydantic validation
- Immediate persistence after successful resource operations
- Legacy format support with automatic migration
- No sensitive data stored in configuration files

## Deployment Standards

### Resource Management

All AWS resources MUST be managed through consistent patterns:
- Idempotent creation with existence checking
- Standardized naming conventions with project prefixes
- Automatic tagging for cost allocation and governance
- Proper IAM role management with least-privilege access
- Lifecycle management with cleanup capabilities

### Build and Deployment

Container builds MUST follow optimized patterns:
- ARM64-native builds on CodeBuild for performance
- Layered Dockerfile templates for cache efficiency
- Source packaging with .dockerignore compliance
- ECR integration with automated push/pull operations

## Governance

All development activities MUST comply with this constitution. Code reviews verify architectural compliance, security requirements, and quality standards. Complexity additions require explicit justification and documentation. Breaking changes require version increment and migration planning.

Pre-commit hooks enforce constitutional compliance automatically. Manual overrides are PROHIBITED except for documented emergency situations with post-incident remediation plans.

**Version**: 1.0.0 | **Ratified**: 2025-01-06 | **Last Amended**: 2025-01-06