# CLI

Command-line interface for BedrockAgentCore Starter Toolkit.

The `agentcore` CLI provides commands for configuring, launching, and managing agents.

## Main Commands

- `agentcore configure --entrypoint <file>` - Configure agents and runtime environments
- `agentcore launch` - Deploy agents to AWS or run locally
- `agentcore invoke` - Invoke deployed agents
- `agentcore --help` - Show help information
- `agentcore <command> --help` - Show help for specific commands

## Example Usage

```bash
# Configure an agent
agentcore configure --entrypoint agent_example.py --execution-role arn:aws:iam::123456789012:role/MyRole

# Deploy to AWS
agentcore launch

# Invoke the agent
agentcore invoke '{"prompt": "Hello world!"}'
```

For detailed usage, run:
```bash
agentcore --help
```
