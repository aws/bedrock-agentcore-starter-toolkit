# QuickStart: Your First Agent in 5 Minutes! 🚀

Get your AI agent running on Amazon Bedrock AgentCore in 3 simple steps.

## Prerequisites

Before starting, make sure you have:

- **AWS Account** with credentials configured in your desired region (`aws configure`) ([AWS CLI setup guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html))
- **Python 3.10+** installed
- **AWS Permissions**:
  - `BedrockAgentCoreFullAccess` managed policy
  - `AmazonBedrockFullAccess` managed policy
  - **Caller permissions**: [See detailed policy here](permissions.md#developercaller-permissions)
- **Model access**: Enable Anthropic Claude models in [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/)

## Step 1: Installation

### Using uv (Recommended - Fastest)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the toolkit
uv pip install bedrock-agentcore-starter-toolkit strands-agents
```

### Using pip (Alternative)

```bash
pip install bedrock-agentcore-starter-toolkit strands-agents
```

### Verify Installation

```bash
agentcore --version
```

## Step 2: Create Your Agent

Create `my_agent.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "Hello!")
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
```

## Step 3: Deploy

```bash
# Configure your agent (creates necessary AWS resources)
agentcore configure --entrypoint my_agent.py

# Deploy to cloud (uses AWS CodeBuild - no Docker required)
agentcore launch

# Test your agent
agentcore invoke '{"prompt": "Hello AgentCore!"}'
```

🎉 **Congratulations!** Your agent is now running on Amazon Bedrock AgentCore!

## What Just Happened?

The toolkit automatically:

- ✅ Built an ARM64 container using AWS CodeBuild (no local Docker needed)
- ✅ Created an IAM execution role with proper permissions
- ✅ Set up an ECR repository for your container
- ✅ Deployed your agent to AgentCore Runtime
- ✅ Configured CloudWatch logging

### Find Your Resources

After deployment, view your resources in AWS Console:

- **Agent Logs**: CloudWatch → Log groups → `/aws/bedrock-agentcore/runtimes/`
- **Container Images**: ECR → Repositories → `bedrock-agentcore-{agent-name}`
- **Build Logs**: CodeBuild → Build history
- **IAM Role**: IAM → Roles → Search for “BedrockAgentCore”

## Region Configuration

By default, the toolkit deploys to `us-west-2`. To use a different region:

```bash
# Option 1: Use --region flag
agentcore configure -e my_agent.py --region us-east-1
agentcore launch --region us-east-1

# Option 2: Set environment variable
export AWS_DEFAULT_REGION=us-east-1
agentcore configure -e my_agent.py
```

## Common Issues & Solutions

|Issue                              |Solution                                               |
|-----------------------------------|-------------------------------------------------------|
|**“Permission denied”**            |Run `aws sts get-caller-identity` to verify credentials|
|**“Model access denied”**          |Enable Claude models in Bedrock console for your region|
|**“Docker not found” warning**     |Ignore it! CodeBuild handles container building        |
|**“Port 8080 in use”** (local only)|`lsof -ti:8080 | xargs kill -9`                        |

## Advanced Options


### Deployment Modes

```bash
# Default - CodeBuild (no Docker needed)
agentcore launch

# Local development (requires Docker/Podman/Finch)
agentcore launch --local

# Local build + cloud deploy (requires Docker)
agentcore launch --local-build
```

### Custom Configuration

```bash
# Use existing IAM role
agentcore configure -e my_agent.py --execution-role arn:aws:iam::123456789012:role/MyRole

# Add custom dependencies
# Create requirements.txt with additional packages:
echo "requests>=2.31.0" > requirements.txt
agentcore configure -e my_agent.py
```

### Why ARM64?

AgentCore Runtime uses AWS Graviton processors for better price-performance. The toolkit handles ARM64 container building automatically via CodeBuild.


## Next Steps

- **[Add tools with Gateway](../gateway/quickstart.md)** - Connect your agent to APIs and services
- **[Enable memory](../../examples/memory-integration.md)** - Give your agent conversation history
- **[Configure authentication](../runtime/auth.md)** - Set up OAuth/JWT auth
- **[View more examples](../../examples/README.md)** - Learn from complete implementations
