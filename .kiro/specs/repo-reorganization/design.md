# Design Document

## Overview

This design document outlines the technical approach for reorganizing the fraud detection system repository into a professional, maintainable structure. The reorganization will transform the current organically-grown structure into a clean, logical hierarchy that follows Python best practices and industry standards.

The design focuses on three key principles:
1. **Zero-breakage**: All functionality continues working through automated import updates
2. **Clear separation of concerns**: Core system, infrastructure, tooling, and examples are distinctly organized
3. **Professional presentation**: The repository structure immediately communicates quality and maintainability

## Architecture

### Current State Analysis

The repository currently has:
- 30+ demo files scattered across root and subdirectories
- Duplicate documentation in `docs/`, `documentation/`, and various README files
- Tests in multiple locations (`tests/`, `tests_integ/`, module-level test files)
- Overlapping functionality (web_interface vs stress_testing/dashboards)
- 15+ task completion summaries cluttering directories
- Unclear boundaries between core system, AWS infrastructure, and tooling
- 40+ standalone scripts and files in the root directory

### Target State Architecture

```
fraud-detection-system/
├── src/
│   └── fraud_detection/
│       ├── core/                    # Core fraud detection logic
│       ├── agents/                  # AI agent implementations
│       ├── memory/                  # Memory system
│       ├── reasoning/               # Reasoning engine
│       ├── streaming/               # Event streaming
│       ├── external/                # External tool integrations
│       └── web/                     # Web interfaces & APIs
├── infrastructure/
│   ├── aws/                         # AWS deployment configs
│   ├── cdk/                         # CDK infrastructure code
│   └── terraform/                   # Terraform configs (if any)
├── tests/
│   ├── unit/                        # Unit tests mirroring src/
│   ├── integration/                 # Integration tests
│   └── fixtures/                    # Test fixtures and utilities
├── examples/
│   ├── basic/                       # Basic usage examples
│   ├── advanced/                    # Advanced scenarios
│   └── dashboards/                  # Dashboard demos
├── docs/
│   ├── architecture/                # Architecture documentation
│   ├── api/                         # API reference
│   ├── guides/                      # User guides
│   └── operations/                  # Operations runbooks
├── scripts/                         # Utility scripts
├── .archive/                        # Historical artifacts
├── .github/                         # GitHub workflows
├── .kiro/                           # Kiro specs
└── [config files]                   # Root-level configs only
```


## Components and Interfaces

### 1. Source Code Organization (`src/fraud_detection/`)

The core application code will be organized as a proper Python package:

**Structure:**
```
src/fraud_detection/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── fraud_detection_agent.py
│   ├── transaction_processing_pipeline.py
│   ├── unified_fraud_detection_system.py
│   ├── fraud_detection_api.py
│   └── models.py
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── coordination/
│   ├── specialized/
│   └── bedrock/
├── memory/
│   ├── __init__.py
│   ├── memory_manager.py
│   ├── context_manager.py
│   └── pattern_learning.py
├── reasoning/
│   ├── __init__.py
│   ├── adaptive_reasoning.py
│   ├── explanation_generator.py
│   └── audit_trail.py
├── streaming/
│   ├── __init__.py
│   ├── transaction_stream_processor.py
│   └── event_response_system.py
├── external/
│   ├── __init__.py
│   ├── fraud_database.py
│   ├── geolocation_services.py
│   └── identity_verification.py
└── web/
    ├── __init__.py
    ├── dashboards/
    └── api/
```

**Key Decisions:**
- All application code moves under `src/fraud_detection/` for proper packaging
- Follows Python src-layout pattern for better isolation
- Each module has clear responsibility and proper `__init__.py` files
- Consolidates `web_interface/` and `stress_testing/dashboards/` into `web/`


### 2. Infrastructure Organization (`infrastructure/`)

All deployment and infrastructure code consolidated:

**Structure:**
```
infrastructure/
├── README.md
├── aws/
│   ├── bedrock/
│   │   ├── agent_config.py
│   │   ├── deploy_agent.py
│   │   └── setup_agent.py
│   ├── cloudformation/
│   │   └── template.yaml
│   ├── deployment/
│   │   ├── deploy_full_infrastructure.py
│   │   ├── deploy_blue_green.sh
│   │   └── rollback_deployment.sh
│   ├── config/
│   │   ├── data_storage_config.py
│   │   ├── monitoring_config.py
│   │   └── streaming_config.py
│   └── iam/
│       ├── roles.py
│       └── permissions.py
└── cdk/
    └── cdk_app.py
```

**Key Decisions:**
- Merges `aws_infrastructure/`, `aws_bedrock_agent/`, and `infrastructure/`
- Groups by AWS service/function rather than flat structure
- Deployment scripts co-located with infrastructure code
- Clear separation between configuration and deployment logic

### 3. Test Organization (`tests/`)

Unified test structure mirroring source code:

**Structure:**
```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── core/
│   ├── agents/
│   ├── memory/
│   ├── reasoning/
│   ├── streaming/
│   ├── external/
│   └── web/
├── integration/
│   ├── test_integration.py
│   ├── test_load_performance.py
│   ├── test_ai_agent_validation.py
│   ├── cli/
│   ├── gateway/
│   ├── identity/
│   ├── memory/
│   └── tools/
└── fixtures/
    ├── data/
    └── utils/
```

**Key Decisions:**
- Merges `tests/` and `tests_integ/` into unified structure
- Unit tests mirror `src/` structure for easy correlation
- Integration tests grouped by integration type
- Module-level test files moved to appropriate subdirectories
- Shared fixtures and utilities in dedicated directory


### 4. Examples and Demos (`examples/`)

All demonstration code consolidated:

**Structure:**
```
examples/
├── README.md
├── basic/
│   ├── simple_fraud_detection.py
│   ├── transaction_stream.py
│   └── api_usage.py
├── agents/
│   ├── agent_communication.py
│   ├── workload_distribution.py
│   ├── pattern_detector.py
│   └── risk_assessor.py
├── reasoning/
│   ├── adaptive_reasoning.py
│   ├── explanation_system.py
│   └── audit_trail.py
├── memory/
│   ├── memory_manager.py
│   ├── pattern_learning.py
│   └── context_aware_decisions.py
├── dashboards/
│   ├── admin_dashboard.py
│   ├── agent_dashboard.py
│   ├── analytics_dashboard.py
│   └── realtime_streaming.py
└── stress_testing/
    ├── README.md
    ├── graceful_degradation.py
    ├── resilience_validation.py
    ├── business_metrics.py
    └── competitive_benchmarks.py
```

**Key Decisions:**
- All `demo_*.py` files from root moved here
- Organized by feature area for easy discovery
- Stress testing examples kept together but moved from root module
- Each category has clear purpose and documentation

### 5. Documentation (`docs/`)

Unified documentation structure:

**Structure:**
```
docs/
├── README.md
├── architecture/
│   ├── ARCHITECTURE.md
│   ├── system-design.md
│   └── diagrams/
├── api/
│   ├── API_REFERENCE.md
│   ├── API_DOCUMENTATION.md
│   └── endpoints.md
├── guides/
│   ├── getting-started.md
│   ├── deployment-guide.md
│   ├── stress-testing.md
│   ├── dashboards.md
│   └── security.md
├── operations/
│   ├── OPERATIONS_RUNBOOK.md
│   ├── TROUBLESHOOTING.md
│   └── monitoring.md
└── project/
    ├── CHANGELOG.md
    ├── CONTRIBUTING.md
    ├── CODE-OF-CONDUCT.md
    └── SECURITY.md
```

**Key Decisions:**
- Merges `docs/` and `documentation/` directories
- Consolidates duplicate API documentation
- Quick-start guides merged into comprehensive getting-started
- Project meta-documentation grouped separately
- MkDocs configuration moved to `documentation/` for site generation


### 6. Scripts and Utilities (`scripts/`)

Organized utility scripts:

**Structure:**
```
scripts/
├── README.md
├── security/
│   ├── security_audit.py
│   ├── security_check.py
│   └── quick_security_check.sh
├── release/
│   ├── bump-version.py
│   ├── prepare-release.py
│   └── validate-release.py
├── development/
│   ├── setup-branch-protection.sh
│   └── run_all_tests.py
└── utilities/
    ├── currency_converter.py
    ├── data_loader.py
    ├── transaction_generator.py
    └── check_models.py
```

**Key Decisions:**
- Groups scripts by purpose (security, release, development, utilities)
- Moves root-level utility scripts here
- Each category documented in scripts/README.md
- Deployment scripts moved to `infrastructure/aws/deployment/`

### 7. Archive (`archive/`)

Historical development artifacts:

**Structure:**
```
.archive/
├── README.md
├── task-summaries/
│   ├── TASK_*.md
│   └── *_COMPLETION_SUMMARY.md
├── project-reports/
│   ├── PROJECT_COMPLETION_SUMMARY.md
│   ├── PROJECT_STATUS_REPORT.md
│   ├── FINAL_PROJECT_SUMMARY.md
│   └── MOBILE_UPDATE_SUMMARY.md
└── deprecated/
    └── [any deprecated code]
```

**Key Decisions:**
- Hidden directory (`.archive/`) to keep out of main view
- Preserves project history without cluttering active codebase
- Organized by artifact type
- Includes README explaining archive purpose


## Data Models

### File Movement Mapping

The reorganization requires tracking file movements for import updates:

```python
FileMovement = {
    "old_path": str,           # Original file path
    "new_path": str,           # New file path
    "file_type": str,          # "python" | "config" | "doc" | "test"
    "imports_to_update": List[str],  # Files that import this module
    "dependencies": List[str]   # Files this module imports
}

MovementPlan = {
    "movements": List[FileMovement],
    "validation_required": bool,
    "estimated_import_updates": int
}
```

### Import Update Tracking

```python
ImportUpdate = {
    "file_path": str,
    "old_import": str,
    "new_import": str,
    "import_type": str,  # "absolute" | "relative"
    "line_number": int
}

UpdateReport = {
    "total_files_scanned": int,
    "total_imports_updated": int,
    "files_modified": List[str],
    "validation_status": str,
    "errors": List[str]
}
```

### Configuration Update Tracking

```python
ConfigUpdate = {
    "config_file": str,
    "config_type": str,  # "pyproject.toml" | "pytest" | "github_actions"
    "old_value": str,
    "new_value": str,
    "section": str
}
```


## Error Handling

### Pre-Migration Validation

Before any files are moved:

1. **Dependency Analysis**
   - Scan all Python files for import statements
   - Build dependency graph
   - Identify circular dependencies
   - Flag potential issues

2. **Test Baseline**
   - Run full test suite
   - Record passing tests as baseline
   - Ensure clean starting state

3. **Git Status Check**
   - Verify clean working directory
   - Ensure no uncommitted changes
   - Create backup branch

### Migration Safety Mechanisms

1. **Atomic Operations**
   - Group related file movements
   - Use git mv to preserve history
   - Rollback capability for each phase

2. **Incremental Validation**
   - Validate imports after each major group
   - Run subset of tests after each phase
   - Stop on first failure

3. **Rollback Strategy**
   - Maintain rollback script
   - Document each change
   - Enable quick reversion if needed

### Post-Migration Validation

1. **Import Verification**
   - Attempt to import all modules
   - Check for missing dependencies
   - Validate relative imports

2. **Test Execution**
   - Run full test suite
   - Compare against baseline
   - Investigate any new failures

3. **CI/CD Validation**
   - Trigger CI pipeline
   - Verify all workflows pass
   - Check deployment processes

### Error Recovery

**Common Issues and Solutions:**

| Issue | Detection | Resolution |
|-------|-----------|------------|
| Missing import update | Import error at runtime | Automated scan and fix |
| Circular dependency | Import analysis | Refactor or document |
| Test path mismatch | pytest discovery failure | Update pytest.ini paths |
| CI/CD path error | Workflow failure | Update workflow YAML |
| Broken relative import | Import error | Convert to absolute import |


## Testing Strategy

### Test Organization Approach

1. **Unit Test Migration**
   - Move module-level test files to `tests/unit/`
   - Mirror source structure: `src/fraud_detection/core/` → `tests/unit/core/`
   - Update test imports to reference new module paths
   - Preserve test logic without modification

2. **Integration Test Consolidation**
   - Merge `tests_integ/` into `tests/integration/`
   - Group by integration type (CLI, gateway, memory, etc.)
   - Update fixture paths and imports
   - Maintain test isolation

3. **Test Discovery Configuration**
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   python_files = ["test_*.py", "*_test.py"]
   python_classes = ["Test*"]
   python_functions = ["test_*"]
   ```

### Validation Testing

**Phase 1: Pre-Migration Baseline**
```bash
# Run all tests and record results
pytest tests/ tests_integ/ --cov=. --cov-report=json
# Save coverage report as baseline
```

**Phase 2: Post-Migration Validation**
```bash
# Run tests with new structure
pytest tests/ --cov=src/fraud_detection --cov-report=json
# Compare coverage against baseline
```

**Phase 3: Import Validation**
```python
# Automated import checker
def validate_all_imports():
    """Attempt to import all modules in src/fraud_detection/"""
    for module in discover_modules("src/fraud_detection"):
        try:
            importlib.import_module(module)
        except ImportError as e:
            log_error(f"Failed to import {module}: {e}")
```

### Continuous Validation

1. **Pre-commit Hooks**
   - Run import validation
   - Check for broken imports
   - Verify test discovery

2. **CI Pipeline Updates**
   - Update test paths in workflows
   - Add import validation step
   - Verify package installation

3. **Documentation Tests**
   - Validate code examples in docs
   - Check import statements in examples
   - Ensure examples run successfully


## Implementation Approach

### Phase-Based Migration

The reorganization will be executed in carefully sequenced phases to minimize risk:

**Phase 1: Preparation**
- Create target directory structure
- Generate file movement plan
- Build dependency graph
- Create backup branch
- Run baseline tests

**Phase 2: Core Source Code**
- Move core fraud detection modules to `src/fraud_detection/core/`
- Update imports within moved files
- Validate core functionality

**Phase 3: Supporting Modules**
- Move agents, memory, reasoning, streaming, external modules
- Update cross-module imports
- Validate each module group

**Phase 4: Tests**
- Reorganize test files
- Update test imports
- Verify test discovery
- Run full test suite

**Phase 5: Infrastructure**
- Consolidate AWS infrastructure code
- Update deployment scripts
- Verify infrastructure references

**Phase 6: Examples and Docs**
- Move demo files to examples/
- Consolidate documentation
- Update all documentation links

**Phase 7: Scripts and Archive**
- Organize utility scripts
- Archive historical artifacts
- Clean root directory

**Phase 8: Configuration Updates**
- Update pyproject.toml
- Update CI/CD workflows
- Update pytest configuration
- Update pre-commit hooks

**Phase 9: Final Validation**
- Run complete test suite
- Validate all imports
- Test CI/CD pipeline
- Generate migration documentation

### Automation Tools

**Import Update Script**
```python
def update_imports(file_path, movement_map):
    """
    Automatically update import statements in a file
    based on the movement map.
    """
    # Read file content
    # Parse import statements
    # Replace old paths with new paths
    # Handle both absolute and relative imports
    # Write updated content
```

**Dependency Scanner**
```python
def scan_dependencies(directory):
    """
    Scan all Python files and build dependency graph.
    """
    # Find all .py files
    # Parse imports using ast module
    # Build directed graph of dependencies
    # Identify circular dependencies
    # Return dependency map
```

**Validation Script**
```python
def validate_reorganization():
    """
    Comprehensive validation after reorganization.
    """
    # Check all imports resolve
    # Verify test discovery
    # Run test suite
    # Check CI/CD configs
    # Generate validation report
```


## Migration Documentation

### MIGRATION.md Structure

The migration guide will include:

1. **Overview**
   - Purpose of reorganization
   - Benefits of new structure
   - Timeline and phases

2. **File Movement Map**
   ```
   Old Location → New Location
   
   Root Level:
   - fraud_detection_agent.py → src/fraud_detection/core/fraud_detection_agent.py
   - demo_*.py → examples/[category]/
   - test_*.py → tests/unit/
   
   Modules:
   - agent_coordination/ → src/fraud_detection/agents/coordination/
   - memory_system/ → src/fraud_detection/memory/
   - [complete mapping...]
   ```

3. **Import Update Guide**
   ```python
   # Old imports
   from fraud_detection_agent import FraudDetectionAgent
   from memory_system.memory_manager import MemoryManager
   
   # New imports
   from fraud_detection.core.fraud_detection_agent import FraudDetectionAgent
   from fraud_detection.memory.memory_manager import MemoryManager
   ```

4. **Configuration Changes**
   - Updated pyproject.toml paths
   - New pytest configuration
   - CI/CD workflow updates

5. **Developer Checklist**
   - [ ] Pull latest changes
   - [ ] Update local imports
   - [ ] Run tests locally
   - [ ] Update any custom scripts
   - [ ] Review new structure

6. **Troubleshooting**
   - Common import errors and fixes
   - Test discovery issues
   - IDE configuration updates

### README.md Updates

The main README will be updated to reflect:

1. **Project Structure Section**
   ```markdown
   ## Project Structure
   
   ```
   fraud-detection-system/
   ├── src/fraud_detection/    # Core application code
   ├── infrastructure/          # AWS deployment configs
   ├── tests/                   # All tests
   ├── examples/                # Usage examples
   ├── docs/                    # Documentation
   └── scripts/                 # Utility scripts
   ```
   ```

2. **Quick Start Updates**
   - Updated installation instructions
   - New import examples
   - Updated example commands

3. **Navigation Links**
   - Links to key documentation
   - Links to examples
   - Links to API reference


## Design Decisions and Rationale

### 1. Why src-layout?

**Decision:** Use `src/fraud_detection/` instead of top-level package

**Rationale:**
- Prevents accidental imports from development directory
- Forces proper package installation for testing
- Industry best practice for Python projects
- Better isolation between source and tests
- Clearer distinction between package code and project code

### 2. Why consolidate web interfaces?

**Decision:** Merge `web_interface/` and `stress_testing/dashboards/` into `src/fraud_detection/web/`

**Rationale:**
- Eliminates duplicate dashboard implementations
- Single source of truth for web components
- Easier maintenance and updates
- Clearer API structure
- Reduces confusion for new developers

### 3. Why separate infrastructure?

**Decision:** Dedicated `infrastructure/` directory outside `src/`

**Rationale:**
- Infrastructure code is not part of the application package
- Different deployment lifecycle
- Clearer separation of concerns
- Easier for DevOps engineers to locate
- Follows cloud-native project patterns

### 4. Why archive instead of delete?

**Decision:** Move task summaries to `.archive/` instead of deleting

**Rationale:**
- Preserves project history
- Useful for understanding evolution
- Hidden directory keeps out of main view
- Can reference for future decisions
- Respects work done

### 5. Why unified test directory?

**Decision:** Merge `tests/` and `tests_integ/` into single `tests/` with subdirectories

**Rationale:**
- Single test discovery configuration
- Clearer test organization
- Easier to run all tests
- Standard Python testing pattern
- Reduces configuration complexity

### 6. Why examples/ instead of demos/?

**Decision:** Use `examples/` directory name

**Rationale:**
- More professional terminology
- Aligns with industry standards
- Clearer purpose (learning/reference)
- Better for documentation
- Common in open-source projects

### 7. Why automated import updates?

**Decision:** Build automation for import statement updates

**Rationale:**
- Hundreds of import statements to update
- Manual updates error-prone
- Ensures consistency
- Faster migration
- Enables validation

### 8. Why phase-based approach?

**Decision:** Execute reorganization in 9 distinct phases

**Rationale:**
- Reduces risk of breaking changes
- Enables incremental validation
- Easier to rollback if needed
- Clear progress tracking
- Manageable scope per phase


## Risk Mitigation

### High-Risk Areas

1. **Import Statement Updates**
   - **Risk:** Missing or incorrect import updates causing runtime errors
   - **Mitigation:** 
     - Automated scanning and replacement
     - Comprehensive import validation script
     - Test suite execution after each phase
     - Manual review of critical modules

2. **Test Discovery**
   - **Risk:** Tests not discovered after reorganization
   - **Mitigation:**
     - Update pytest configuration before moving tests
     - Validate test discovery after each test move
     - Maintain consistent naming conventions
     - Document test organization clearly

3. **CI/CD Pipeline Breakage**
   - **Risk:** GitHub Actions workflows fail due to path changes
   - **Mitigation:**
     - Update workflows before merging
     - Test on feature branch first
     - Use variables for paths where possible
     - Validate all workflows pass

4. **Circular Dependencies**
   - **Risk:** Reorganization exposes hidden circular dependencies
   - **Mitigation:**
     - Pre-migration dependency analysis
     - Identify and document circular dependencies
     - Refactor if necessary
     - Use lazy imports where appropriate

5. **Lost Git History**
   - **Risk:** File movements lose git blame/history
   - **Mitigation:**
     - Use `git mv` for all file movements
     - Document movements in MIGRATION.md
     - Preserve original file paths in comments
     - Create comprehensive movement map

### Rollback Plan

If critical issues arise:

1. **Immediate Rollback**
   ```bash
   git reset --hard backup-branch
   git push --force origin main
   ```

2. **Partial Rollback**
   - Identify problematic phase
   - Revert specific commits
   - Fix issues
   - Resume from that phase

3. **Forward Fix**
   - For minor issues, fix forward
   - Document fixes in MIGRATION.md
   - Update automation scripts
   - Continue validation

### Success Criteria

The reorganization is successful when:

1. ✅ All tests pass (same or better than baseline)
2. ✅ All imports resolve correctly
3. ✅ CI/CD pipelines pass
4. ✅ Package installs correctly (`pip install -e .`)
5. ✅ Examples run without errors
6. ✅ Documentation is accurate and complete
7. ✅ No regression in functionality
8. ✅ Code coverage maintained or improved
9. ✅ Git history preserved for moved files
10. ✅ Migration documentation complete

