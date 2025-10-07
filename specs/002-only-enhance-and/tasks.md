# Tasks: Enhanced Configuration Management with Backward Compatibility

**Input**: Design documents from `/specs/002-only-enhance-and/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: backward compatibility validation, linting
   → Tests: contract tests, integration tests
   → Core: schema enhancements, operations enhancements
   → Integration: CLI integration, artifact management
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have enhancements?
   → All operations implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- CLI project with three-layer architecture (CLI → Operations → Services → Utilities)

## Phase 3.1: Setup
- [x] T001 Create backward compatibility validation utilities in `src/bedrock_agentcore_starter_toolkit/utils/runtime/backward_compat.py`
- [x] T002 Extend Pydantic schema for source path tracking in `src/bedrock_agentcore_starter_toolkit/utils/runtime/schema.py`
- [x] T003 [P] Configure enhanced linting rules for new optional field patterns

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test for configureAgentEnhanced operation in `tests/contract/test_configure_agent_enhanced.py`
- [ ] T005 [P] Contract test for launchAgentEnhanced operation in `tests/contract/test_launch_agent_enhanced.py`
- [ ] T006 [P] Contract test for getAgentStatusEnhanced operation in `tests/contract/test_status_agent_enhanced.py`
- [ ] T007 [P] Contract test for listAgentsEnhanced operation in `tests/contract/test_list_agents_enhanced.py`
- [ ] T008 [P] Integration test for backward compatibility validation in `tests/integration/test_backward_compatibility.py`
- [ ] T009 [P] Integration test for source path tracking in `tests/integration/test_source_path_tracking.py`
- [ ] T010 [P] Integration test for build artifact organization in `tests/integration/test_build_artifact_organization.py`
- [ ] T011 [P] Integration test for enhanced status information in `tests/integration/test_enhanced_status.py`
- [ ] T012 [P] Integration test for mixed configuration compatibility in `tests/integration/test_mixed_configuration.py`

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Data Models and Schema Extensions
- [ ] T013 [P] Implement BuildArtifactInfo Pydantic model in `src/bedrock_agentcore_starter_toolkit/utils/runtime/schema.py`
- [ ] T014 Add optional source_path field to BedrockAgentCoreAgentSchema in `src/bedrock_agentcore_starter_toolkit/utils/runtime/schema.py`
- [ ] T015 Add optional build_artifacts field to BedrockAgentCoreAgentSchema in `src/bedrock_agentcore_starter_toolkit/utils/runtime/schema.py`

### Build Artifact Management
- [ ] T016 [P] Create build artifact management utilities in `src/bedrock_agentcore_starter_toolkit/utils/runtime/artifacts.py`
- [ ] T017 Enhance container.py with artifact organization in `src/bedrock_agentcore_starter_toolkit/utils/runtime/container.py`

### Enhanced Configuration Operations
- [ ] T018 Enhance configure operation with source path tracking in `src/bedrock_agentcore_starter_toolkit/operations/runtime/configure.py`
- [ ] T019 Enhance launch operation with artifact organization in `src/bedrock_agentcore_starter_toolkit/operations/runtime/launch.py`
- [ ] T020 Create enhanced status operation in `src/bedrock_agentcore_starter_toolkit/operations/runtime/status.py`

### Enhanced CLI Commands
- [ ] T021 Enhance configure command with source path options in `src/bedrock_agentcore_starter_toolkit/cli/runtime/commands.py`
- [ ] T022 Enhance launch command with artifact reporting in `src/bedrock_agentcore_starter_toolkit/cli/runtime/commands.py`
- [ ] T023 Enhance status command with source path and artifact display in `src/bedrock_agentcore_starter_toolkit/cli/runtime/commands.py`
- [ ] T024 Enhance list command with enhanced agent information in `src/bedrock_agentcore_starter_toolkit/cli/runtime/commands.py`

### Configuration Management Enhancements
- [ ] T025 Enhance config loading with backward compatibility in `src/bedrock_agentcore_starter_toolkit/utils/runtime/config.py`
- [ ] T026 Enhance config saving with optional field preservation in `src/bedrock_agentcore_starter_toolkit/utils/runtime/config.py`

## Phase 3.4: Integration
- [ ] T027 Integrate source path validation with configuration operations in `src/bedrock_agentcore_starter_toolkit/operations/runtime/configure.py`
- [ ] T028 Integrate artifact organization with launch operations in `src/bedrock_agentcore_starter_toolkit/operations/runtime/launch.py`
- [ ] T029 Connect enhanced status information with CLI display in `src/bedrock_agentcore_starter_toolkit/cli/runtime/commands.py`
- [ ] T030 Integrate backward compatibility validation throughout configuration loading
- [ ] T031 Connect build artifact cleanup with destroy operations in `src/bedrock_agentcore_starter_toolkit/operations/runtime/destroy.py`

## Phase 3.5: Polish
- [ ] T032 [P] Unit tests for BuildArtifactInfo model in `tests/unit/test_build_artifact_info.py`
- [ ] T033 [P] Unit tests for source path validation in `tests/unit/test_source_path_validation.py`
- [ ] T034 [P] Unit tests for backward compatibility utilities in `tests/unit/test_backward_compatibility.py`
- [ ] T035 [P] Unit tests for artifact organization in `tests/unit/test_artifact_organization.py`
- [ ] T036 [P] Unit tests for enhanced configuration loading in `tests/unit/test_enhanced_config.py`
- [ ] T037 Performance tests for configuration operations (<5 seconds requirement)
- [ ] T038 Execute quickstart validation scenarios from `specs/002-only-enhance-and/quickstart.md`
- [ ] T039 [P] Update CLI help documentation for enhanced features
- [ ] T040 Remove code duplication across enhanced operations

## Dependencies
- Setup (T001-T003) before all other phases
- Tests (T004-T012) before implementation (T013-T031)
- Schema changes (T013-T015) must run sequentially (same file modifications), before all other implementation
- T016 (artifact utilities) before T017 (container enhancements) and T019 (launch enhancements)
- T018-T020 (operations) before T021-T024 (CLI enhancements)
- T025-T026 (config management) before T027 (configuration operations)
- Core implementation (T013-T026) before integration (T027-T031)
- Integration (T027-T031) before polish (T032-T040)

## Parallel Execution Examples

### Phase 3.2 - Contract Tests (All Parallel)
```
Task: "Contract test for configureAgentEnhanced operation in tests/contract/test_configure_agent_enhanced.py"
Task: "Contract test for launchAgentEnhanced operation in tests/contract/test_launch_agent_enhanced.py"
Task: "Contract test for getAgentStatusEnhanced operation in tests/contract/test_status_agent_enhanced.py"
Task: "Contract test for listAgentsEnhanced operation in tests/contract/test_list_agents_enhanced.py"
```

### Phase 3.2 - Integration Tests (All Parallel)
```
Task: "Integration test for backward compatibility validation in tests/integration/test_backward_compatibility.py"
Task: "Integration test for source path tracking in tests/integration/test_source_path_tracking.py"
Task: "Integration test for build artifact organization in tests/integration/test_build_artifact_organization.py"
Task: "Integration test for enhanced status information in tests/integration/test_enhanced_status.py"
Task: "Integration test for mixed configuration compatibility in tests/integration/test_mixed_configuration.py"
```

### Phase 3.5 - Unit Tests (All Parallel)
```
Task: "Unit tests for BuildArtifactInfo model in tests/unit/test_build_artifact_info.py"
Task: "Unit tests for source path validation in tests/unit/test_source_path_validation.py"
Task: "Unit tests for backward compatibility utilities in tests/unit/test_backward_compatibility.py"
Task: "Unit tests for artifact organization in tests/unit/test_artifact_organization.py"
Task: "Unit tests for enhanced configuration loading in tests/unit/test_enhanced_config.py"
```

## Task Details

### Enhanced Schema Tasks
- **T013**: Create BuildArtifactInfo model with fields: base_directory, source_copy_path, dockerfile_path, build_timestamp, organized
- **T014**: Add source_path: Optional[str] = None to BedrockAgentCoreAgentSchema with validation
- **T015**: Add build_artifacts: Optional[BuildArtifactInfo] = None to BedrockAgentCoreAgentSchema

### Artifact Management Tasks
- **T016**: Implement artifact creation, organization, and cleanup utilities with .packages/{agent-name}/ pattern
- **T017**: Extend existing container functionality to use organized artifact directories

### CLI Enhancement Tasks
- **T021-T024**: Enhance existing commands to show source path and build artifact information without changing command signatures
- **T029**: Add Rich console formatting for enhanced status display

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing (TDD requirement)
- Maintain 90% test coverage throughout implementation
- Each task should be atomic and completable in <2 hours
- Commit after each completed task
- Follow constitutional principles: three-layer architecture, idempotent operations, CLI-first interface
- All file paths are absolute and reference existing codebase structure
- Backward compatibility validation required for all configuration operations
- Source path tracking is optional and must not break existing workflows

## Task Generation Rules
- Each contract operation → contract test task [P]
- Each entity in data-model → schema enhancement task
- Each quickstart scenario → integration test [P]
- Each user story → implementation task (sequential if same file)
- Different files = parallel execution allowed [P]
- Same file = sequential execution (no [P])
- Tests must be written first and must fail (TDD)
