# QuickStart: Your First Agent in 5 Minutes! 🚀

Get your AI agent running on Amazon Bedrock AgentCore in 3 simple steps.

## Prerequisites

Before starting, make sure you have:

- **AWS Account** with credentials configured  in your desired region (`aws configure`)
- **Python 3.10+** installed
- **AWS CLI** configured with your preferred region
- **AWS Permissions**:
  - `BedrockAgentCoreFullAccess` managed policy
  - `AmazonBedrockFullAccess` managed policy
  - **Caller permissions**: [See detailed policy here](permissions.md#developercaller-permissions)


## Region Configuration
By default, the AgentCore CLI deploys to `us-west-2`. To deploy to a different region:
- Use `--region` flag: `agentcore configure -e my_agent.py --region us-east-1`
- Or set AWS_DEFAULT_REGION environment variable: `export AWS_DEFAULT_REGION=us-east-1`


## Architecture Requirements
⚠️ **Important**: AgentCore Runtime requires ARM64 architecture containers. This is because:
- Runtime uses AWS Graviton processors for cost-efficiency and performance
- All containers must be built for `linux/arm64` platform
- Local development on x86 machines requires Docker buildx or CodeBuild deployment

**Solutions for x86 machines:**
- Use default CodeBuild deployment (recommended): `agentcore launch`
- Use Docker buildx for cross-platform builds: `docker buildx build --platform linux/arm64`

## Step 1: Installation

### Recommended: Using uv (Fastest)

The toolkit uses [`uv`](https://github.com/astral-sh/uv) for ultra-fast Python package management:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
uv pip install bedrock-agentcore-starter-toolkit
```

### Alternative: Using pip

```bash
pip install bedrock-agentcore-starter-toolkit
```

> **Note:** The toolkit uses `uv` internally for containerization, providing 4x faster dependency installation during deployments.

### Verify Installation

```bash
agentcore --version
```


## Step 2: Create Your First Agent

Create a file `hello_agent.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    user_message = payload.get("prompt", "Hello!")
    return {"response": f"You said: {user_message}. I'm your agent running on AgentCore!"}

if __name__ == "__main__":
    app.run()
```

## Step 3: Configure and Deploy

```bash
# Configure your agent (creates necessary AWS resources)
agentcore configure --entrypoint hello_agent.py

# Deploy to cloud (uses CodeBuild, no Docker required)
agentcore launch

# Test your agent
agentcore invoke '{"prompt": "Hello AgentCore!"}'
```


🎉 **Congratulations!** Your agent is now running on Amazon Bedrock AgentCore!


## Understanding Your Deployment

After deployment, the toolkit validates your setup and provides:

- ✅ Execution role with proper permissions (Memory, Identity, Runtime access)
- ✅ ECR repository for your container images
- ✅ CloudWatch logs automatically configured
- ✅ Session management enabled
- ✅ Network configuration set to PUBLIC by default

## Quick Links to AWS Console Resources

After deployment, find your resources at:
- [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch/home#logsV2:log-groups)
- [ECR Repositories](https://console.aws.amazon.com/ecr/repositories)
- [IAM Roles](https://console.aws.amazon.com/iam/home#/roles)
- [CodeBuild Projects](https://console.aws.amazon.com/codesuite/codebuild/projects)

### What’s Happening Behind the Scenes?

1. **Container Build**: Your Python code is containerized for ARM64
1. **Resource Creation**: IAM roles, ECR repositories created automatically
1. **Deployment**: Container deployed to managed AgentCore infrastructure
1. **Isolation**: Each session runs in isolated microVM for security


## Troubleshooting

### Common Issues

**"Port 8080 already in use"**
```bash
# Find and stop the process using port 8080
lsof -ti:8080 | xargs kill -9
```

**"Permission denied" errors**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check you have the required managed policies attached
- Review [caller permissions policy](permissions.md#required-caller-policy) for detailed requirements

**"Docker not found" warnings**
- ✅ **Ignore this!** Default deployment uses CodeBuild (no Docker needed)
- Only install Docker/Finch/Podman if you want to use `--local` or `--local-build` flags

**"Model access denied"**
- Enable Anthropic Claude 4.0 in the [Bedrock console](https://console.aws.amazon.com/bedrock/)
- Make sure you're in the correct AWS region (us-west-2 by default)

**"CodeBuild build error"**
- Check CodeBuild project logs in AWS console
- Verify your [caller permissions](permissions.md#developercaller-permissions) include CodeBuild access


### Getting Help

- **Detailed permissions**: [Runtime Permissions Guide](permissions.md)
- **Advanced deployment**: [Runtime Overview](overview.md)
- **More examples**: [Examples Directory](../../examples/README.md)

---

## Advanced Options (Optional)

<details>
<summary>🔧 Click to expand advanced configuration options</summary>

### Deployment Modes

Choose the right deployment approach for your needs:

**🚀 Default: CodeBuild + Cloud Runtime (RECOMMENDED)**
```bash
agentcore launch  # Uses CodeBuild (no Docker needed)
```
Perfect for production, managed environments, teams without Docker

**💻 Local Development**
```bash
agentcore launch --local  # Build and run locally (requires Docker/Finch/Podman)
```
Perfect for development, rapid iteration, debugging

**🔧 Hybrid: Local Build + Cloud Runtime**
```bash
agentcore launch --local-build  # Build locally, deploy to cloud (requires Docker/Finch/Podman)
```
Perfect for teams with Docker expertise needing build customization

### Custom Roles
```bash
# Use existing IAM role
agentcore configure -e my_agent.py --execution-role arn:aws:iam::123456789012:role/MyRole
```

</details>

---

## Next Steps

Ready to build something more advanced?

- **[Runtime Overview](overview.md)** - Deep dive into AgentCore features
- **[Add tools with Gateway](../gateway/quickstart.md)**
- **[Enable memory for your agent](../../examples/memory-integration.md)**
- **[Configure OAuth authentication](../runtime/auth.md)**
- **[Examples](../../examples/README.md)** - More complete examples
