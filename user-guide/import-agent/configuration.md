# Import Agent Configuration Reference

This document provides detailed information about all configuration options available for the `import-agent` utility.

## Command Syntax

```
agentcore import-agent [OPTIONS]
```

## Configuration Options

### Required Parameters

These parameters are required for the import process. If not provided via command line flags, the utility will prompt you interactively.

#### `--agent-id`

- **Type**: String
- **Description**: ID of the Bedrock Agent to import
- **Example**: `--agent-id ABCD1234EFGH`

#### `--agent-alias-id`

- **Type**: String
- **Description**: ID of the Agent Alias to use
- **Example**: `--agent-alias-id TSTALIASID`

#### `--target-platform`

- **Type**: String
- **Options**: `langchain`, `strands`
- **Description**: Target platform for code generation
- **Example**: `--target-platform strands`

### Optional Parameters

#### AWS Configuration

##### `--region`

- **Type**: String
- **Description**: AWS Region to use when fetching Bedrock Agents
- **Default**: Uses your default AWS configuration
- **Example**: `--region us-east-1`

#### Output Configuration

##### `--output-dir`

- **Type**: String
- **Description**: Output directory for generated code
- **Default**: `./output/`
- **Example**: `--output-dir ./my-agent`

#### AgentCore Primitives

##### `--disable-memory`

- **Type**: Boolean flag
- **Description**: Disable AgentCore Memory primitive integration
- **Default**: `false` (Memory is enabled by default)
- **Usage**: `--disable-memory`

##### `--disable-code-interpreter`

- **Type**: Boolean flag
- **Description**: Disable AgentCore Code Interpreter primitive integration
- **Default**: `false` (Code Interpreter is enabled by default)
- **Usage**: `--disable-code-interpreter`

##### `--disable-observability`

- **Type**: Boolean flag
- **Description**: Disable AgentCore Observability primitive integration
- **Default**: `false` (Observability is enabled by default)
- **Usage**: `--disable-observability`

##### `--disable-gateway`

- **Type**: Boolean flag
- **Description**: Disable AgentCore Gateway primitive integration
- **Default**: `false` (Gateway is enabled by default)
- **Usage**: `--disable-gateway`

#### Deployment Options

##### `--deploy-runtime`

- **Type**: Boolean flag
- **Description**: Deploy the generated agent to AgentCore Runtime
- **Default**: `false`
- **Usage**: `--deploy-runtime`

##### `--run-option`

- **Type**: String
- **Options**: `locally`, `runtime`, `none`
- **Description**: How to run the agent after generation
- **Default**: Interactive prompt if not specified
- **Examples**:
- `--run-option locally` - Run the agent on your local machine
- `--run-option runtime` - Run on AgentCore Runtime (requires `--deploy-runtime`)
- `--run-option none` - Generate code only, don't run

#### Debugging Options

##### `--verbose`

- **Type**: Boolean flag
- **Description**: Enable verbose output mode
- **Default**: `false`
- **Usage**: `--verbose`

## Configuration Examples

### Basic Import

```
agentcore import-agent \
  --agent-id ABCD1234 \
  --agent-alias-id TSTALIASID \
  --target-platform strands
```

### Full Configuration with Deployment

```
agentcore import-agent \
  --region us-west-2 \
  --agent-id ABCD1234 \
  --agent-alias-id PRODALIASID \
  --target-platform langchain \
  --output-dir ./production-agent \
  --deploy-runtime \
  --run-option runtime \
  --verbose
```

### Minimal Setup without Primitives

```
agentcore import-agent \
  --agent-id ABCD1234 \
  --agent-alias-id TSTALIASID \
  --target-platform strands \
  --disable-memory \
  --disable-code-interpreter \
  --disable-observability \
  --run-option none
```

### Debug Mode for Troubleshooting

```
agentcore import-agent \
  --agent-id ABCD1234 \
  --agent-alias-id TSTALIASID \
  --target-platform strands \
  --output-dir ./debug-output
```

## Interactive vs Non-Interactive Mode

### Interactive Mode

When required parameters are missing, the utility enters interactive mode:

```
agentcore import-agent
```

This will prompt you for:

- AWS Region selection
- Agent selection from your available Bedrock Agents
- Agent alias selection
- Target platform choice
- AgentCore primitives configuration
- Deployment and run options

### Non-Interactive Mode

Provide all required parameters to run without prompts:

```
agentcore import-agent \
  --agent-id ABCD1234 \
  --agent-alias-id TSTALIASID \
  --target-platform strands \
  --deploy-runtime \
  --run-option runtime
```

## Default Behavior

| Option           | Default Value | Behavior                                               |
| ---------------- | ------------- | ------------------------------------------------------ |
| Memory           | Enabled       | AgentCore Memory primitive is integrated               |
| Code Interpreter | Enabled       | AgentCore Code Interpreter primitive is integrated     |
| Observability    | Enabled       | AgentCore Observability primitive is integrated        |
| Gateway          | Enabled       | AgentCore Gateway is not used as a proxy to AG Lambdas |
| Deployment       | Disabled      | Generated code is not deployed to runtime              |
| Output Directory | `./output/`   | Code is generated in this directory                    |
| Verbose Mode     | Disabled      | Standard output level                                  |

## Environment Variables

The utility respects standard AWS environment variables:

- `AWS_REGION` - Default region for AWS operations
- `AWS_PROFILE` - AWS profile to use
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` - AWS credentials

## Configuration File Support

Currently, the import-agent utility does not support configuration files. All options must be provided via command line flags or interactive prompts.

## Troubleshooting

### Common Issues

**Missing AWS Permissions** Use ADA or the AWS CLI to authenticate. Ensure that you have environment variables for your AWS credentials and these can be used by Boto3 appropriately.

**Agent Not Found**

```
# Verify your agent ID and region
agentcore import-agent --region us-east-1 --agent-id YOUR_AGENT_ID
```

**Output Directory Issues**

```
# Specify a custom output directory
agentcore import-agent --output-dir ./custom-path
```
