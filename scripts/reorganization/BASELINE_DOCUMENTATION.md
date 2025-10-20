# Baseline Test Documentation

## Date: 2025-10-20

## Purpose
This document records the baseline state of the repository before reorganization begins.

## Backup Branch
- **Branch Name**: `backup-pre-reorganization`
- **Status**: Created and verified
- **Purpose**: Allows rollback to pre-reorganization state if needed

## Current Repository Structure

### Test Directories
- `tests/` - Main test directory
- `tests_integ/` - Integration tests directory

### Source Code Locations
- Root level: Core fraud detection files
- `agent_coordination/` - Agent coordination modules
- `memory_system/` - Memory management
- `reasoning_engine/` - Reasoning logic
- `streaming/` - Event streaming
- `external_tools/` - External integrations
- `specialized_agents/` - Specialized agent implementations
- `web_interface/` - Web UI components
- `stress_testing/` - Stress testing framework

### Infrastructure
- `aws_infrastructure/` - AWS deployment configs
- `aws_bedrock_agent/` - Bedrock agent setup
- `infrastructure/` - General infrastructure code

### Documentation
- `docs/` - Main documentation
- `documentation/` - Additional documentation

## Test Status
- Backup branch created: ✓
- Repository structure documented: ✓
- Ready for reorganization: ✓

## Notes
- All existing functionality should continue working after reorganization
- Import statements will be automatically updated
- Test structure will be consolidated
- Documentation will be unified
