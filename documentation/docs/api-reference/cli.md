# CLI

Command-line interface for BedrockAgentCore Starter Toolkit.

The `agentcore` CLI provides commands for configuring, launching, managing agents, and working with gateways.

## Runtime Commands

### Configure

Configure agents and runtime environments.

```bash
agentcore configure [OPTIONS]
```

Options:

- `--entrypoint, -e TEXT`: Python file of agent

- `--name, -n TEXT`: Agent name (defaults to Python file name)

- `--execution-role, -er TEXT`: IAM execution role ARN

- `--ecr, -ecr TEXT`: ECR repository name (use "auto" for automatic creation)

- `--container-runtime, -ctr TEXT`: Container runtime

- `--requirements-file, -rf TEXT`: Path to requirements file of agent

- `--disable-otel, -do`: Disable OpenTelemetry

- `--authorizer-config, -ac TEXT`: OAuth authorizer configuration as JSON string

- `--verbose, -v`: Enable verbose output

- `--region, -r TEXT`: AWS region

- `--protocol, -p TEXT`: Agent server protocol (HTTP or MCP)

Subcommands:

- `list`: List configured agents

- `set-default`: Set default agent

### Launch

Deploy agents to AWS or run locally.

```bash
agentcore launch [OPTIONS]
```

Options:

- `--agent, -a TEXT`: Agent name

- `--local, -l`: Run locally

- `--detach, -d`: Run in detached mode (background) - only works with --local

- `--log-file TEXT`: Redirect logs to file (implies --detach) - only works with --local

- `--push-ecr, -p`: Build and push to ECR only (no deployment)

- `--env, -env TEXT`: Environment variables for agent (format: KEY=VALUE)

### Invoke

Invoke deployed agents.

```bash
agentcore invoke [PAYLOAD] [OPTIONS]
```

Arguments:

- `PAYLOAD`: JSON payload to send

Options:

- `--agent, -a TEXT`: Agent name

- `--session-id, -s TEXT`: Session ID

- `--bearer-token, -bt TEXT`: Bearer token for OAuth authentication

- `--local, -l`: Send request to a running local container

- `--user-id, -u TEXT`: User ID for authorization flows

### Status

Get Bedrock AgentCore status including config and runtime details.

```bash
agentcore status [OPTIONS]
```

Options:

- `--agent, -a TEXT`: Agent name

- `--verbose, -v`: Verbose JSON output of config, agent, and endpoint status

## Gateway Commands

Access gateway subcommands:

```bash
agentcore gateway [COMMAND]
```

### Create MCP Gateway

```bash
agentcore gateway create-mcp-gateway [OPTIONS]
```

Options:

- `--region TEXT`: Region to use (defaults to us-west-2)

- `--name TEXT`: Name of the gateway (defaults to TestGateway)

- `--role-arn TEXT`: Role ARN to use (creates one if none provided)

- `--authorizer-config TEXT`: Serialized authorizer config

- `--enable-semantic-search, -sem`: Whether to enable search tool (defaults to True)

### Create MCP Gateway Target

```bash
agentcore gateway create-mcp-gateway-target [OPTIONS]
```

Options:

- `--gateway-arn TEXT`: ARN of the created gateway

- `--gateway-url TEXT`: URL of the created gateway

- `--role-arn TEXT`: Role ARN of the created gateway

- `--region TEXT`: Region to use (defaults to us-west-2)

- `--name TEXT`: Name of the target (defaults to TestGatewayTarget)

- `--target-type TEXT`: Type of target (lambda, openApiSchema, smithyModel)

- `--target-payload TEXT`: Specification of the target (required for openApiSchema)

- `--credentials TEXT`: Credentials for calling this target (API key or OAuth2)

## Example Usage

### Configure an Agent

```bash
# Basic configuration
agentcore configure --entrypoint agent_example.pt

# Configure with execution role
agentcore configure --entrypoint agent_example.py --execution-role arn:aws:iam::123456789012:role/MyRole

# List configured agents
agentcore configure list

# Set default agent
agentcore configure set-default my_agent
```

### Deploy and Run Agents

```bash
# Deploy to AWS
agentcore launch

# Run locally
agentcore launch --local

# Run locally in background (detached mode)
agentcore launch --local --detach
agentcore launch --local -d

# Run locally with custom log file (auto-detaches)
agentcore launch --local --log-file my-agent.log

# Launch with environment variables
agentcore launch --env API_KEY=abc123 --env DEBUG=true
```

### Invoke Agents

```bash
# Basic invocation
agentcore invoke '{"prompt": "Hello world!"}'

# Invoke with session ID
agentcore invoke '{"prompt": "Continue our conversation"}' --session-id abc123

# Invoke with OAuth authentication
agentcore invoke '{"prompt": "Secure request"}' --bearer-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Invoke local agent
agentcore invoke '{"prompt": "Test locally"}' --local
```

### Check Status

```bash
# Get status of default agent
agentcore status

# Get status of specific agent
agentcore status --agent my-agent
```

### Gateway Operations

```bash
# Create MCP Gateway
agentcore gateway create-mcp-gateway --name MyGateway

# Create MCP Gateway Target
agentcore gateway create-mcp-gateway-target \
  --gateway-arn arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/abcdef \
  --gateway-url https://gateway-url.us-west-2.amazonaws.com \
  --role-arn arn:aws:iam::123456789012:role/GatewayRole
```

### Importing from Bedrock Agents

```bash
# Interactive Mode
agentcore import-agent

# For Automation
agentcore import-agent \
  --region us-east-1 \
  --agent-id ABCD1234 \
  --agent-alias-id TSTALIASID \
  --target-platform strands \
  --output-dir ./my-agent \
  --deploy-runtime \
  --run-option runtime

# AgentCore Primitive Opt-out
agentcore import-agent --disable-gateway --disable-memory --disable-code-interpreter --disable-observability
```

## Common Issues and Solutions

### Detach Mode Validation Errors

**Error**: `--detach can only be used with --local`
```bash
# ❌ Invalid - detach without local
agentcore launch --detach

# ✅ Correct - detach with local
agentcore launch --local --detach
```

**Error**: `--log-file can only be used with --local`
```bash
# ❌ Invalid - log-file without local
agentcore launch --log-file agent.log

# ✅ Correct - log-file with local
agentcore launch --local --log-file agent.log
```

### Terminal Blocking Issues

**Problem**: Agent blocks terminal, can't run other commands

**Solution**: Use detach mode
```bash
# Instead of this (blocks terminal)
agentcore launch --local

# Use this (runs in background)
agentcore launch --local --detach
```

### Background Process Management

**Check if agent is running**:
```bash
# Look for Python processes running your agent
ps aux | grep "my_agent.py"

# Check port 8080 usage
lsof -i :8080
```

**Stop background agent**:
```bash
# Find and stop the process
pkill -f "my_agent.py"

# Or kill by port
lsof -ti:8080 | xargs kill
```
