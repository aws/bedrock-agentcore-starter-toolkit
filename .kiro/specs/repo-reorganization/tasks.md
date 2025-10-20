# Implementation Plan

- [x] 1. Pre-Migration Preparation






  - Create backup branch and baseline
  - Build dependency analysis tools
  - Generate file movement plan
  - _Requirements: 1.6, 13.5_


- [x] 1.1 Create backup branch and run baseline tests


  - Create `backup-pre-reorganization` branch
  - Run full test suite and record results
  - Save test coverage report as baseline
  - Document current test pass/fail status
  - _Requirements: 1.6_


- [x] 1.2 Build dependency scanner script

  - Create `scripts/reorganization/scan_dependencies.py`
  - Implement AST-based import parser
  - Build dependency graph of all modules
  - Identify circular dependencies
  - Generate dependency report
  - _Requirements: 1.5, 11.5_


- [x] 1.3 Create file movement mapping

  - Create `scripts/reorganization/movement_plan.json`
  - Map all source files to target locations
  - Map all test files to target locations
  - Map all demo files to target locations
  - Map all documentation files to target locations
  - Document files to archive
  - _Requirements: 2.1, 2.2, 12.2_

- [x] 1.4 Create automated import update script




  - Create `scripts/reorganization/update_imports.py`
  - Implement import statement parser
  - Implement import path replacement logic
  - Handle both absolute and relative imports
  - Add validation and dry-run mode
  - _Requirements: 11.1, 11.2, 11.3_

- [x] 2. Create target directory structure



  - Create all new directories with proper __init__.py files
  - Set up package structure
  - _Requirements: 2.1, 2.5, 13.1_


- [x] 2.1 Create src/fraud_detection/ package structure

  - Create `src/fraud_detection/` directory
  - Create `src/fraud_detection/__init__.py`
  - Create subdirectories: core/, agents/, memory/, reasoning/, streaming/, external/, web/
  - Create __init__.py in each subdirectory
  - _Requirements: 2.1, 2.3, 13.1_


- [x] 2.2 Create infrastructure/ directory structure

  - Create `infrastructure/` directory
  - Create subdirectories: aws/bedrock/, aws/cloudformation/, aws/deployment/, aws/config/, aws/iam/, cdk/
  - Create README.md for infrastructure
  - _Requirements: 6.1, 6.2_


- [x] 2.3 Create tests/ directory structure

  - Create `tests/unit/` mirroring src structure
  - Create `tests/integration/` directory
  - Create `tests/fixtures/` directory
  - Create tests/__init__.py and conftest.py
  - _Requirements: 4.1, 4.2, 4.5_


- [x] 2.4 Create examples/ directory structure

  - Create `examples/` directory
  - Create subdirectories: basic/, agents/, reasoning/, memory/, dashboards/, stress_testing/
  - Create examples/README.md
  - _Requirements: 5.1, 5.2_


- [x] 2.5 Create docs/ directory structure

  - Create `docs/` directory
  - Create subdirectories: architecture/, api/, guides/, operations/, project/
  - Create docs/README.md with navigation
  - _Requirements: 3.1, 3.2, 3.5_

- [x] 2.6 Create scripts/ and .archive/ directories


  - Create `scripts/` with subdirectories: security/, release/, development/, utilities/
  - Create `.archive/` with subdirectories: task-summaries/, project-reports/, deprecated/
  - Create README.md files for both
  - _Requirements: 7.1, 7.4, 9.1_

- [-] 3. Move core source code to src/fraud_detection/



  - Move main fraud detection modules
  - Update internal imports
  - Validate core functionality
  - _Requirements: 1.1, 2.1, 11.1_


- [x] 3.1 Move core fraud detection files

  - Move fraud_detection_agent.py to src/fraud_detection/core/
  - Move transaction_processing_pipeline.py to src/fraud_detection/core/
  - Move unified_fraud_detection_system.py to src/fraud_detection/core/
  - Move fraud_detection_api.py to src/fraud_detection/core/
  - Use `git mv` to preserve history
  - _Requirements: 1.1, 2.1_




- [x] 3.2 Update imports in moved core files


  - Run import update script on core files
  - Update relative imports to absolute imports
  - Verify all imports resolve

  - _Requirements: 11.1, 11.2_

- [x] 3.3 Move agent modules to src/fraud_detection/agents/

  - Move agent_coordination/ to src/fraud_detection/agents/coordination/
  - Move specialized_agents/ to src/fraud_detection/agents/specialized/
  - Move aws_bedrock_agent/ content to src/fraud_detection/agents/bedrock/
  - Update __init__.py files
  - _Requirements: 2.1, 2.2_




- [x] 3.4 Move memory system to src/fraud_detection/memory/


  - Move memory_system/ contents to src/fraud_detection/memory/
  - Update imports in memory modules
  - Verify memory system functionality
  - _Requirements: 2.1, 11.1_



- [x] 3.5 Move reasoning engine to src/fraud_detection/reasoning/

  - Move reasoning_engine/ contents to src/fraud_detection/reasoning/
  - Update imports in reasoning modules
  - Verify reasoning functionality
  - _Requirements: 2.1, 11.1_


- [x] 3.6 Move streaming and external modules




  - Move streaming/ to src/fraud_detection/streaming/
  - Move external_tools/ to src/fraud_detection/external/
  - Update imports in both modules
  - _Requirements: 2.1, 11.1_

- [x] 3.7 Consolidate web interfaces






  - Analyze web_interface/ and stress_testing/dashboards/ for duplicates
  - Move unique components to src/fraud_detection/web/dashboards/
  - Move API files to src/fraud_detection/web/api/
  - Merge duplicate implementations (keep most complete)
  - Update imports
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 3.8 Update src/fraud_detection/__init__.py





  - Expose public API from __init__.py
  - Import key classes and functions
  - Add version information
  - _Requirements: 13.2_

- [ ] 4. Reorganize test files
  - Move all tests to unified structure
  - Update test imports
  - Verify test discovery
  - _Requirements: 4.1, 4.2, 4.6_

- [x] 4.1 Move unit tests to tests/unit/




  - Move module-level test files to appropriate tests/unit/ subdirectories
  - Mirror src/ structure in tests/unit/
  - Update test imports to reference new module paths
  - _Requirements: 4.1, 4.2_

- [x] 4.2 Move integration tests to tests/integration/





  - Move tests_integ/ contents to tests/integration/
  - Organize by integration type (cli/, gateway/, identity/, memory/, tools/)
  - Update test imports and fixture paths
  - _Requirements: 4.2, 4.4_

- [ ] 4.3 Move test utilities and fixtures
  - Move shared test utilities to tests/fixtures/utils/
  - Move test data to tests/fixtures/data/
  - Update conftest.py with fixture paths
  - _Requirements: 4.5_

- [ ] 4.4 Update pytest configuration
  - Update pyproject.toml [tool.pytest.ini_options]
  - Set testpaths = ["tests"]
  - Update coverage source paths
  - Verify test discovery works
  - _Requirements: 4.6, 15.2_

- [ ] 4.5 Run test suite validation
  - Run pytest with new structure
  - Compare results against baseline
  - Fix any test discovery issues
  - Document any test changes needed
  - _Requirements: 1.3, 4.6_

- [ ] 5. Consolidate infrastructure code
  - Merge AWS infrastructure directories
  - Organize deployment scripts
  - Update infrastructure references
  - _Requirements: 6.1, 6.2, 6.3_

- [ ] 5.1 Merge AWS infrastructure directories
  - Move aws_infrastructure/ contents to infrastructure/aws/
  - Move aws_bedrock_agent/ deployment files to infrastructure/aws/bedrock/
  - Move infrastructure/cdk_app.py to infrastructure/cdk/
  - Organize by AWS service/function
  - _Requirements: 6.1, 6.2_

- [ ] 5.2 Organize deployment scripts
  - Move deployment scripts to infrastructure/aws/deployment/
  - Move scripts/deploy_blue_green.sh to infrastructure/aws/deployment/
  - Move scripts/rollback_deployment.sh to infrastructure/aws/deployment/
  - Update script paths in CI/CD
  - _Requirements: 6.3, 9.3_

- [ ] 5.3 Update infrastructure configuration
  - Move config files to infrastructure/aws/config/
  - Update import paths in infrastructure code
  - Create infrastructure/README.md with usage guide
  - _Requirements: 6.5, 6.6_

- [ ] 6. Move examples and demos
  - Consolidate all demo files
  - Organize by feature area
  - Update demo imports
  - _Requirements: 5.1, 5.2, 5.6_

- [ ] 6.1 Move basic examples
  - Move demo_transaction_stream.py to examples/basic/
  - Move simple fraud detection demos to examples/basic/
  - Move agent_example.py to examples/basic/
  - Update imports in example files
  - _Requirements: 5.1, 5.6_

- [ ] 6.2 Move agent examples
  - Move demo_agent_*.py files to examples/agents/
  - Move demo_workload_distribution.py to examples/agents/
  - Update imports
  - _Requirements: 5.1, 5.2_

- [ ] 6.3 Move reasoning and memory examples
  - Move demo_reasoning*.py to examples/reasoning/
  - Move demo_memory*.py to examples/memory/
  - Move demo_pattern*.py to examples/memory/
  - Update imports
  - _Requirements: 5.1, 5.2_

- [ ] 6.4 Move dashboard examples
  - Move demo_*_dashboard.py to examples/dashboards/
  - Move demo_analytics*.py to examples/dashboards/
  - Move HTML demo files with their Python counterparts
  - Update imports
  - _Requirements: 5.1, 5.4_

- [ ] 6.5 Move stress testing examples
  - Move stress_testing/demo_*.py to examples/stress_testing/
  - Keep stress_testing core functionality in src/
  - Create examples/stress_testing/README.md
  - Update imports
  - _Requirements: 5.1, 5.3_

- [ ] 6.6 Create examples/README.md
  - Document all available examples
  - Provide usage instructions for each category
  - Include prerequisites and dependencies
  - _Requirements: 5.5_

- [ ] 7. Consolidate documentation
  - Merge documentation directories
  - Organize by purpose
  - Update all links
  - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [ ] 7.1 Merge API documentation
  - Move API_DOCUMENTATION.md to docs/api/
  - Move docs/API_REFERENCE.md to docs/api/
  - Merge duplicate content
  - Create unified API reference
  - _Requirements: 3.2, 3.3_

- [ ] 7.2 Organize architecture documentation
  - Move docs/ARCHITECTURE.md to docs/architecture/
  - Add system design diagrams if available
  - Create architecture overview
  - _Requirements: 3.2_

- [ ] 7.3 Consolidate user guides
  - Move quick-start guides to docs/guides/
  - Merge ADMIN_DASHBOARD_QUICK_START.md, AGENT_DASHBOARD_QUICK_START.md, etc.
  - Create unified getting-started.md
  - Move DEPLOYMENT_GUIDE.md to docs/guides/
  - _Requirements: 3.2, 3.4_

- [ ] 7.4 Organize operations documentation
  - Move docs/OPERATIONS_RUNBOOK.md to docs/operations/
  - Move docs/TROUBLESHOOTING.md to docs/operations/
  - Add monitoring and maintenance guides
  - _Requirements: 3.2_

- [ ] 7.5 Move project meta-documentation
  - Move CONTRIBUTING.md, CODE-OF-CONDUCT.md to docs/project/
  - Move CHANGELOG.md to docs/project/
  - Keep LICENSE.txt and SECURITY.md in root
  - _Requirements: 3.2_

- [ ] 7.6 Create docs/README.md navigation
  - Create documentation index
  - Link to all major documentation sections
  - Provide quick navigation
  - _Requirements: 3.5_

- [ ] 7.7 Update documentation links
  - Scan all markdown files for internal links
  - Update links to reflect new paths
  - Verify all links work
  - _Requirements: 3.6_

- [ ] 8. Organize scripts and utilities
  - Categorize utility scripts
  - Move to appropriate locations
  - Document script purposes
  - _Requirements: 9.1, 9.2, 9.5_

- [ ] 8.1 Organize security scripts
  - Move security_check.py to scripts/security/
  - Move run_security_audit.py to scripts/security/
  - Move scripts/security_audit.py (already there)
  - Move quick_security_check.sh to scripts/security/
  - _Requirements: 9.1, 9.2_

- [ ] 8.2 Organize release scripts
  - Keep scripts/bump-version.py, prepare-release.py, validate-release.py
  - Group in scripts/release/ subdirectory
  - _Requirements: 9.1_

- [ ] 8.3 Organize development scripts
  - Move scripts/setup-branch-protection.sh to scripts/development/
  - Move tests/run_all_tests.py to scripts/development/
  - _Requirements: 9.1_

- [ ] 8.4 Organize utility scripts
  - Move currency_converter.py to scripts/utilities/
  - Move data_loader.py to scripts/utilities/
  - Move transaction_generator.py to scripts/utilities/
  - Move check_models.py to scripts/utilities/
  - Move test_*.py files (root level) to appropriate test directories
  - _Requirements: 9.1, 9.4_

- [ ] 8.5 Create scripts/README.md
  - Document purpose of each script
  - Provide usage examples
  - Document dependencies
  - _Requirements: 9.5_

- [ ] 9. Archive historical artifacts
  - Move task summaries to archive
  - Move project reports to archive
  - Clean root directory
  - _Requirements: 7.1, 7.2, 7.5_

- [ ] 9.1 Archive task completion summaries
  - Move all TASK_*.md files to .archive/task-summaries/
  - Move *_COMPLETION_SUMMARY.md files to .archive/task-summaries/
  - Move *_SUMMARY.md files to .archive/task-summaries/
  - Organize by date or task number
  - _Requirements: 7.1, 7.2_

- [ ] 9.2 Archive project reports
  - Move PROJECT_COMPLETION_SUMMARY.md to .archive/project-reports/
  - Move PROJECT_STATUS_REPORT.md to .archive/project-reports/
  - Move FINAL_PROJECT_SUMMARY.md to .archive/project-reports/
  - Move MOBILE_UPDATE_SUMMARY.md to .archive/project-reports/
  - Move other status reports
  - _Requirements: 7.2_

- [ ] 9.3 Create .archive/README.md
  - Explain purpose of archive
  - Document what's archived and why
  - Provide index of archived content
  - _Requirements: 7.4_

- [ ] 10. Update configuration files
  - Update pyproject.toml
  - Update CI/CD workflows
  - Update other configs
  - _Requirements: 8.1, 8.4, 15.1, 15.2_

- [ ] 10.1 Update pyproject.toml
  - Update [tool.hatch.build.targets.wheel] packages path
  - Update [tool.ruff] include paths
  - Update [tool.pytest.ini_options] testpaths
  - Update [tool.coverage.run] source paths
  - _Requirements: 8.1, 8.4_

- [ ] 10.2 Update GitHub Actions workflows
  - Update .github/workflows/ci-cd.yml paths
  - Update test execution commands
  - Update deployment script paths
  - Use variables for maintainability
  - _Requirements: 15.1, 15.2, 15.5_

- [ ] 10.3 Update pre-commit configuration
  - Update .pre-commit-config.yaml if needed
  - Verify hooks work with new structure
  - _Requirements: 8.2_

- [ ] 10.4 Update ruff and mypy configurations
  - Verify linting works with new paths
  - Update any path-specific ignores
  - _Requirements: 8.4_

- [ ] 11. Run comprehensive validation
  - Validate all imports
  - Run full test suite
  - Test CI/CD pipeline
  - _Requirements: 1.3, 1.4, 11.5, 15.4_

- [ ] 11.1 Create and run import validation script
  - Create scripts/reorganization/validate_imports.py
  - Attempt to import all modules in src/fraud_detection/
  - Check for missing dependencies
  - Generate validation report
  - _Requirements: 1.6, 11.5_

- [ ] 11.2 Run full test suite
  - Execute pytest tests/
  - Compare results against baseline
  - Verify coverage maintained
  - Document any failures
  - _Requirements: 1.3, 1.4_

- [ ] 11.3 Test package installation
  - Run `pip install -e .` in clean environment
  - Verify package installs correctly
  - Test importing from installed package
  - _Requirements: 13.3_

- [ ] 11.4 Validate examples run successfully
  - Run each example in examples/
  - Verify no import errors
  - Document any issues
  - _Requirements: 5.6_

- [ ] 11.5 Test CI/CD pipeline
  - Push to feature branch
  - Verify all GitHub Actions workflows pass
  - Check deployment processes
  - _Requirements: 15.4, 15.6_

- [ ] 12. Create migration documentation
  - Write MIGRATION.md
  - Update README.md
  - Document changes
  - _Requirements: 12.1, 12.2, 12.3, 14.1, 14.2_

- [ ] 12.1 Create MIGRATION.md
  - Document complete file movement map
  - Provide import update examples
  - Include configuration changes
  - Add developer checklist
  - Add troubleshooting section
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [ ] 12.2 Update README.md
  - Add project structure section with directory tree
  - Update quick start instructions
  - Update import examples
  - Add navigation links to docs
  - Update badges and links
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

- [ ] 12.3 Create reorganization summary document
  - Document rationale for major decisions
  - Summarize what changed and why
  - Provide before/after comparison
  - _Requirements: 12.3_

- [ ] 13. Final cleanup and verification
  - Remove empty directories
  - Verify git history preserved
  - Final validation
  - _Requirements: 1.3, 2.6, 13.5_

- [ ] 13.1 Clean up empty directories
  - Remove old empty directories
  - Verify no orphaned files
  - Check for leftover __pycache__
  - _Requirements: 2.6_

- [ ] 13.2 Verify git history preservation
  - Check git log for moved files
  - Verify git blame works
  - Document any history issues
  - _Requirements: 12.2_

- [ ] 13.3 Run final comprehensive validation
  - Run all tests one final time
  - Verify all imports work
  - Test package installation
  - Run examples
  - Check CI/CD
  - _Requirements: 1.3, 1.4, 11.5, 13.5_

- [ ] 13.4 Create validation report
  - Document all validation results
  - List any known issues
  - Provide success metrics
  - _Requirements: 1.6_

- [ ] 13.5 Merge to main branch
  - Create pull request
  - Review all changes
  - Merge reorganization
  - Tag release if appropriate
  - _Requirements: 15.6_
