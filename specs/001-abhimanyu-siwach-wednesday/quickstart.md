# Quickstart: Multi-Agent Configuration Safeguards

This quickstart validates the enhanced multi-agent configuration system with safeguards, error handling, and build artifact isolation.

## Prerequisites

- AgentCore Starter Toolkit installed and configured
- AWS credentials configured
- Two sample agent projects for testing multi-agent scenarios

## Test Scenario 1: Configuration Isolation

**Purpose**: Verify that multiple agents can be configured without conflicts

```bash
# Step 1: Configure first agent
cd /path/to/first-agent/
agentcore configure --entrypoint main.py --name first-agent

# Expected: Configuration created successfully
# Expected: Build directory created at .packages/first-agent/

# Step 2: Configure second agent in different directory
cd /path/to/second-agent/
agentcore configure --entrypoint agent.py --name second-agent

# Expected: Configuration created successfully
# Expected: Both agents listed in global configuration
# Expected: No overwrite of first agent's configuration

# Step 3: Verify both agents are configured
agentcore configure list

# Expected: Shows both first-agent and second-agent
# Expected: Each has correct entrypoint and source path
```

## Test Scenario 2: Name Collision Handling

**Purpose**: Verify user confirmation workflow for agent name conflicts

```bash
# Step 1: Attempt to configure agent with existing name
agentcore configure --entrypoint new_main.py --name first-agent

# Expected: Prompt asking to confirm overwrite
# Expected: Clear warning about existing configuration
# Expected: Option to cancel or proceed

# Step 2: Cancel the operation
# Select "No" or press Ctrl+C

# Expected: Operation cancelled
# Expected: Original configuration preserved

# Step 3: Confirm overwrite
agentcore configure --entrypoint new_main.py --name first-agent
# Select "Yes" to confirm

# Expected: Configuration updated
# Expected: New entrypoint reflected in configuration
```

## Test Scenario 3: Build Artifact Isolation

**Purpose**: Verify that each agent gets isolated build artifacts during launch

```bash
# Step 1: Launch first agent
agentcore launch --agent-name first-agent

# Expected: Progress indicators for operations >5 seconds
# Expected: Build artifacts created in isolated directory
# Expected: Source code copied to prevent modifications
# Expected: Agent deployed successfully

# Step 2: Launch second agent
agentcore launch --agent-name second-agent

# Expected: Separate build artifacts created
# Expected: No interference with first agent's artifacts
# Expected: Both agents deploy from correct source code

# Step 3: Verify artifact isolation
ls .packages/
# Expected: Separate directories for first-agent and second-agent
# Expected: Each contains Dockerfile and source copy
```

## Test Scenario 4: Error Handling and Recovery

**Purpose**: Verify comprehensive error handling with resource tracking

```bash
# Step 1: Simulate failure during launch (disconnect network)
# Disconnect network or simulate AWS API failure
agentcore launch --agent-name test-agent

# Expected: Clear error message explaining what went wrong
# Expected: Report of resources created before failure
# Expected: Guidance on cleanup actions needed

# Step 2: Verify resource tracking
# Reconnect network and check resources

# Expected: Partial resources properly identified
# Expected: Cleanup instructions provided
# Expected: System left in consistent state
```

## Test Scenario 5: Complete Cleanup

**Purpose**: Verify that agent destruction removes all artifacts

```bash
# Step 1: Destroy agent with cleanup verification
agentcore destroy --agent-name first-agent

# Expected: Confirmation prompt for destructive operation
# Expected: Complete removal of build artifacts
# Expected: Cleanup of AWS resources
# Expected: Summary of removed resources

# Step 2: Verify cleanup completeness
ls .packages/
# Expected: first-agent directory removed
# Expected: Other agents' artifacts preserved

agentcore configure list
# Expected: first-agent no longer listed
# Expected: second-agent still present and functional
```

## Validation Checklist

After completing all test scenarios, verify these outcomes:

### Configuration Management
- [ ] Multiple agents can be configured without conflicts
- [ ] Each agent maintains isolated configuration files
- [ ] Name collisions trigger user confirmation prompts
- [ ] Global configuration correctly tracks all agents

### Build Isolation
- [ ] Each agent gets separate build artifact directories
- [ ] Source code is copied to prevent modifications
- [ ] Docker files are generated per-agent
- [ ] Build artifacts are created automatically during launch

### Error Handling
- [ ] Operations >5 seconds show progress indicators
- [ ] Errors include clear, actionable messages
- [ ] Resource tracking reports AWS and local resources created
- [ ] Partial failures provide cleanup guidance

### Cleanup and Recovery
- [ ] Agent destruction removes all associated artifacts
- [ ] AWS resources are properly cleaned up
- [ ] Other agents remain unaffected by cleanup operations
- [ ] System maintains consistent state after errors

## Success Criteria

✅ **All test scenarios complete without errors**
✅ **Multi-agent configurations remain isolated**
✅ **User confirmations prevent accidental overwrites**
✅ **Build artifacts are properly isolated and cleaned up**
✅ **Error handling provides comprehensive resource tracking**
✅ **Progress indicators show for appropriate operations**

## Next Steps

After successful quickstart validation:

1. Run full test suite: `uv run pytest tests/`
2. Verify 90% test coverage: `uv run pytest --cov=src --cov-report=term-missing tests/`
3. Execute pre-commit validation: `uv run pre-commit run --all-files`
4. Deploy to staging environment for integration testing
