# Quickstart: Enhanced Configuration Management with Backward Compatibility

This quickstart validates the enhanced configuration management system while ensuring complete backward compatibility with existing configurations.

## Prerequisites

- AgentCore Starter Toolkit installed and configured
- AWS credentials configured
- Existing `.bedrock_agentcore.yaml` configuration file (for backward compatibility testing)
- Sample agent project for testing enhancements

## Test Scenario 1: Backward Compatibility Validation

**Purpose**: Verify that existing configurations work unchanged

```bash
# Step 1: Use existing configuration without changes
cd /path/to/existing/project/
cat .bedrock_agentcore.yaml  # Verify existing configuration

# Step 2: Run existing commands unchanged
agentcore configure list
agentcore status

# Expected: All existing functionality works identically
# Expected: No errors or warnings about configuration format
# Expected: Existing agent information displays correctly

# Step 3: Launch existing agent configuration
agentcore launch

# Expected: Launch process works exactly as before
# Expected: No new prompts or configuration requirements
# Expected: Agent deploys successfully using existing configuration
```

## Test Scenario 2: Enhanced Configuration with Source Path Tracking

**Purpose**: Verify new source path tracking functionality

```bash
# Step 1: Configure new agent with source path
cd /path/to/new/agent/
agentcore configure --entrypoint agent.py --name enhanced-agent

# Expected: Option to specify source path during configuration
# Expected: System tracks source path in configuration
# Expected: Configuration saved with source path information

# Step 2: Verify source path tracking
agentcore status --agent-name enhanced-agent

# Expected: Status shows source path information
# Expected: Clear display of where source code is located
# Expected: Source path validation confirmation

# Step 3: Launch with source path tracking
agentcore launch --agent-name enhanced-agent

# Expected: System uses tracked source path consistently
# Expected: Clear feedback about source location being used
# Expected: Launch process references correct source directory
```

## Test Scenario 3: Build Artifact Organization

**Purpose**: Verify automatic build artifact organization

```bash
# Step 1: Launch agent and observe artifact creation
agentcore launch --agent-name enhanced-agent

# Expected: Build artifacts created in predictable location
# Expected: Artifacts organized under .packages/enhanced-agent/
# Expected: Source code copied to organized location

# Step 2: Verify artifact organization
ls -la .packages/
ls -la .packages/enhanced-agent/

# Expected: Clear directory structure
# Expected: Source copy in src/ subdirectory
# Expected: Generated Dockerfile in predictable location
# Expected: Build metadata file present

# Step 3: Check artifact isolation
agentcore configure --entrypoint agent.py --name second-agent
agentcore launch --agent-name second-agent

ls -la .packages/

# Expected: Separate directories for each agent
# Expected: No interference between agent artifacts
# Expected: Clear separation and organization
```

## Test Scenario 4: Enhanced Status Information

**Purpose**: Verify improved status and information display

```bash
# Step 1: Check enhanced agent status
agentcore status --agent-name enhanced-agent

# Expected: Source path information displayed
# Expected: Build artifact location shown
# Expected: Enhanced information easy to understand

# Step 2: List all agents with enhanced info
agentcore configure list

# Expected: Source path shown for agents that have it
# Expected: Build artifact status indicated
# Expected: Clear, organized display of information

# Step 3: Verify information accuracy
agentcore status

# Expected: Accurate source path references
# Expected: Correct build artifact locations
# Expected: Helpful information for troubleshooting
```

## Test Scenario 5: Mixed Configuration Compatibility

**Purpose**: Verify old and new configurations work together

```bash
# Step 1: Verify mixed agent configurations
agentcore configure list

# Expected: Both legacy and enhanced agents listed
# Expected: Legacy agents show appropriate information
# Expected: Enhanced agents show additional information

# Step 2: Launch different types of agents
agentcore launch --agent-name legacy-agent
agentcore launch --agent-name enhanced-agent

# Expected: Both launch successfully
# Expected: Each uses appropriate configuration approach
# Expected: No conflicts between legacy and enhanced workflows

# Step 3: Verify coexistence
agentcore status

# Expected: All agents display appropriate status
# Expected: Enhanced features don't break legacy agents
# Expected: Clear differentiation between agent types
```

## Validation Checklist

After completing all test scenarios, verify these outcomes:

### Backward Compatibility
- [ ] Existing `.bedrock_agentcore.yaml` files load without changes
- [ ] All existing CLI commands work identically
- [ ] Legacy agent configurations deploy successfully
- [ ] No migration required for existing setups

### Source Path Enhancement
- [ ] Source path can be specified during configuration
- [ ] Source path information is tracked and displayed
- [ ] Source path validation works correctly
- [ ] Source path used consistently across operations

### Build Artifact Organization
- [ ] Build artifacts created in predictable locations
- [ ] Artifacts organized under `.packages/{agent-name}/`
- [ ] Source code copied to organized structure
- [ ] Build metadata maintained properly

### User Experience
- [ ] Enhanced information is clear and helpful
- [ ] Status commands show useful source/artifact info
- [ ] Default behaviors are intuitive
- [ ] Troubleshooting information is accessible

### Configuration Management
- [ ] New fields are optional with sensible defaults
- [ ] Configuration loading handles missing fields gracefully
- [ ] Configuration saving preserves all existing information
- [ ] Schema validation works for both old and new formats

## Success Criteria

✅ **Complete backward compatibility maintained**
✅ **Source path tracking works seamlessly**
✅ **Build artifacts organized predictably**
✅ **Enhanced status information is helpful**
✅ **Mixed configurations coexist properly**
✅ **No new commands required**
✅ **User experience is simplified, not complicated**

## Next Steps

After successful quickstart validation:

1. Run full test suite: `uv run pytest tests/`
2. Verify 90% test coverage: `uv run pytest --cov=src --cov-report=term-missing tests/`
3. Execute pre-commit validation: `uv run pre-commit run --all-files`
4. Test with various existing configurations to ensure compatibility
5. Deploy to staging environment for integration testing
