# Gateway CLI Overview

Bedrock AgentCore Gateway provides a simple CLI for creating and managing gateways.

## Installation

```bash
# Install Bedrock AgentCore SDK with Gateway support
pip install -e .
# or
uv pip install -e .

# Verify installation
agentcore --help
```

## Create a Gateway

The `agentcore gateway` command creates a new Gateway with automatic setup:

```bash
agentcore gateway \
  --name my-gateway \
  --target arn:aws:lambda:us-west-2:123456789012:function:MyFunction \
  --execution-role MyExecutionRole
```

### Command Syntax

```bash
agentcore gateway [OPTIONS]
```

### Options

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--name` | `-n` | Yes | Gateway name |
| `--target` | `-t` | Yes | Target source (Lambda ARN, file path, or S3 URI) |
| `--execution-role` | `-r` | Yes | IAM execution role (ARN or name) |
| `--type` | | No | Target type (auto-detected if not specified) |
| `--description` | `-d` | No | Gateway description |
| `--region` | | No | AWS region (auto-detected from credentials) |

### Examples

#### Lambda Gateway (Auto-detected)

```bash
# Full command
agentcore gateway \
  --name weather-gateway \
  --target arn:aws:lambda:us-west-2:123456789012:function:WeatherFunction \
  --execution-role WeatherExecutionRole

# Short form
agentcore gateway \
  -n weather-gateway \
  -t arn:aws:lambda:us-west-2:123456789012:function:WeatherFunction \
  -r WeatherExecutionRole
```

#### OpenAPI Gateway

```bash
# From local file (auto-detected by .json extension)
agentcore gateway \
  -n api-gateway \
  -t ./openapi.json \
  -r ApiExecutionRole

# From S3 (auto-detected by s3:// prefix)
agentcore gateway \
  -n s3-api-gateway \
  -t s3://my-bucket/openapi.json \
  -r ApiExecutionRole
```

#### With Explicit Type

```bash
# Force Smithy type for a JSON file
agentcore gateway \
  -n smithy-gateway \
  -t ./model.json \
  -r ExecutionRole \
  --type smithy
```

## Auto-Detection Features

The CLI automatically detects:

### Region and Account

- Uses AWS credentials to determine region
- Builds full role ARN from role name

```bash
# These are equivalent (assuming account 123456789012 and region us-west-2):
-r MyRole
-r arn:aws:iam::123456789012:role/MyRole
```

### Target Type

**Lambda**: Detects from ARN pattern `arn:aws:lambda:*`
**S3**: Detects from URI pattern `s3://`
**OpenAPI**: Detects from file extensions `.json`, `.yaml`, `.yml`

## Output

The command returns:
- Gateway ID
- MCP Endpoint URL
- OAuth Client Credentials

Example output:
```
Using region: us-west-2
Auto-detected target type: lambda
Setting up authentication for weather-gateway...
✓ Created User Pool: us-west-2_ABC123
✓ Created domain: bedrock-agentcore-abc123
✓ Created resource server: weather-gateway
✓ Created client: 1a2b3c4d5e
✓ EZ Auth setup complete!
Creating gateway weather-gateway...
✓ Created Gateway: XYZ789
✓ Gateway is ready
✓ Added target successfully

✅ Gateway setup complete!
MCP Endpoint: <fill>

OAuth Credentials:
Client ID: 1a2b3c4d5e
Client Secret: [hidden]
Scope: weather-gateway/invoke

Save these credentials - you'll need them to get access tokens.
```

## Lambda Function Schema

When creating a Lambda gateway without custom tools, the CLI auto-generates a default tool:

```json
{
  "name": "invoke_function",
  "description": "Invoke the Lambda function",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

To specify custom tools, create a Lambda configuration file:

```json
{
  "arn": "arn:aws:lambda:us-west-2:123456789012:function:MyFunction",
  "tools": [
    {
      "name": "process_data",
      "description": "Process input data",
      "inputSchema": {
        "type": "object",
        "properties": {
          "input": {"type": "string"}
        },
        "required": ["input"]
      }
    }
  ]
}
```

Then use it:
```bash
agentcore gateway -n my-gateway -t lambda-config.json -r MyRole --type lambda
```

## Best Practices

**Use Role Names**: Let the CLI build full ARNs
**Leverage Auto-detection**: Omit `--type` when possible
**Save Credentials**: Store OAuth credentials securely
**Use Short Forms**: `-n`, `-t`, `-r` for faster commands

## Troubleshooting

### DNS Propagation
After creating a gateway, wait 60 seconds for Cognito domain DNS to propagate before requesting tokens.

### Permission Errors
Ensure your execution role has:
Trust relationship with Bedrock AgentCore service
Permissions to invoke Lambda or read S3
Proper resource-based policies for cross-account access

### Auto-detection Not Working
Explicitly specify `--type` if:
File doesn't have standard extension
Content type is ambiguous
You want to override detection
