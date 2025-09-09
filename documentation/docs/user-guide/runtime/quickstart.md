# QuickStart: Your First Agent in 5 Minutes! 🚀

Get your AI agent running on Amazon Bedrock AgentCore in 3 simple steps.

## Prerequisites

Before starting, make sure you have:

- **AWS Account** with credentials configured (`aws configure`)
- **Python 3.10+** installed
- **AWS Permissions**:
  - `BedrockAgentCoreFullAccess` managed policy
  - `AmazonBedrockFullAccess` managed policy
  - **Caller permissions**: [See detailed policy here](permissions.md#developercaller-permissions)
- **Model Access**: Anthropic Claude 4.0 enabled in [Amazon Bedrock console](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html)


## Step 0: Setup folder and virtual environment

Create a new folder for this quickstart, create and initialize a new python virtual environment

```bash
mkdir agentcore-runtime-quickstart
cd agentcore-runtime-quickstart
python3 -m venv venv
source venv/bin/activate
```


## Step 1: Install and Create Your Agent

```bash
# Install both packages
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

Create `my_agent.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
def invoke(payload):
    """Your AI agent function"""
    user_message = payload.get("prompt", "Hello! How can I help you today?")
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt`:
```
bedrock-agentcore
strands-agents
```

Run
```bash
cat > requirements.txt << EOF
bedrock-agentcore
strands-agents
EOF
```

## Step 2: Test Locally

```bash
# Start your agent
python my_agent.py

# Test it (in another terminal)
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

✅ **Success**: You should see a response like `{"result": "Hello! I'm here to help..."}`

## Step 3: Deploy to AWS

```bash
# Configure and deploy (auto-creates all required resources)
agentcore configure -e my_agent.py
agentcore launch

# Test your deployed agent
agentcore invoke '{"prompt": "tell me a joke"}'
```

🎉 **Congratulations!** Your agent is now running on Amazon Bedrock AgentCore!

---
> **💡 Tip**: The toolkit auto-creates IAM roles and ECR repositories - no manual setup needed!

---

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
- **[Memory Guide](../memory/quickstart.md)** - Add persistent memory
- **[Gateway Tools](../gateway/quickstart.md)** - Connect external APIs
- **[Examples](../../examples/README.md)** - More complete examples
