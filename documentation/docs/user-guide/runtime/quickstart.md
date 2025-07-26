# QuickStart: Your First Agent in 5 Minutes! 🚀

Let's get your first AI agent running on Amazon Bedrock AgentCore in just a few minutes!

## What You Need

### Prerequisites

- An AWS account with the following permissions:
  - **AgentCore Full Access**: `AmazonBedrockAgentCoreFullAccess` managed policy
  - **Bedrock Access** (one of the following):
    - **Option 1 (Development)**: `AmazonBedrockFullAccess` managed policy
    - **Option 2 (Production Recommended)**: Custom policy with scoped permissions for specific models
  - **Caller permissions**: [See detailed policy here](permissions.md#developercaller-permissions)
- Python 3.10+ installed
- 5 minutes of your time ⏰

### Development Environment Considerations

**For SageMaker Notebooks, Cloud9, or other cloud environments:**
- Use the `--codebuild` flag for deployment (no Docker required)
- CodeBuild handles ARM64 container builds automatically

**For local development:**
- Docker Desktop (for standard deployment)
- Or use `--codebuild` flag to avoid Docker requirements

## Step 1: Install the SDK

```bash
pip install bedrock-agentcore
```

## Step 2: Create Your Agent

First, install the Strands framework:

```bash
pip install strands-agents
```

Create a file called `my_agent.py` and add this code:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
def invoke(payload):
    """Your AI agent function"""
    user_message = payload.get("prompt", "Hello! How can I help you today?")

    # Let Strands AI handle the response
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
```

## Step 3: Test It Locally

```bash
# Start your agent
python my_agent.py

# In another terminal, test it:
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

You should see something like: `{"result": "Hello! I'm here to help you with any questions or tasks you have. What would you like to know or do today?"}`

🎉 **Congratulations!** Your AI agent is working locally!

> **Note**: To run this example hello world agent you will need to set up credentials for our model provider and enable model access. The default model provider for Strands Agents SDK is [Amazon Bedrock](https://aws.amazon.com/bedrock/) and the default model is Claude 3.7 Sonnet in the US Oregon (us-west-2) region.

> For the default Amazon Bedrock model provider, see the [Boto3 documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) for setting up AWS credentials. Typically for development, AWS credentials are defined in `AWS_` prefixed environment variables or configured with `aws configure`. You will also need to enable Claude 3.7 model access in Amazon Bedrock, following the [AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) to enable access.

## Step 4: Deploy to AWS

Ready to deploy to the cloud? The toolkit makes this incredibly simple with **automatic role creation**!

```bash
# Install the starter toolkit
pip install bedrock-agentcore-starter-toolkit

# Create requirements.txt
echo "bedrock-agentcore
strands-agents" > requirements.txt

# 🎯 Configure your agent - roles are auto-created!
agentcore configure -e my_agent.py

# 🚀 Deploy to AWS with CodeBuild (perfect for SageMaker notebooks!)
agentcore launch --codebuild

# 🎉 Test your deployed agent
agentcore invoke '{"prompt": "tell me a joke"}'
```

### ✨ What Just Happened?

The toolkit automatically handled all the complex setup:

1. **🔐 Auto-Created Execution Role**: The toolkit created `AmazonBedrockAgentCoreSDKRuntime-{region}-{hash}` with all required permissions
2. **🏗️ CodeBuild Resources**: ARM64 build environment and CodeBuild role configured automatically
3. **📦 ECR Repository**: Container registry created automatically

### 🎯 Key Benefits of Auto-Creation

**🚀 Zero Configuration Required**
- No need to manually create IAM roles
- No need to configure trust policies
- No need to attach permissions policies

**📱 Perfect for SageMaker Notebooks**
- No Docker installation needed
- ARM64 builds handled in the cloud
- Works seamlessly in managed environments

### 🔧 Advanced Configuration (Optional)

**If you prefer to use existing roles:**
```bash
# Use existing execution role
agentcore configure -e my_agent.py -er arn:aws:iam::123456789012:role/MyExistingRole

# Use existing ECR repository
agentcore configure -e my_agent.py -ecr my-existing-repo
```

**For local development and testing:**
```bash
# Local development (runs locally)
agentcore launch --local
```

**For standard cloud deployment:**
```bash
# Standard cloud deployment (requires local Docker)
agentcore launch
```

> **💡 Pro Tip**: The auto-creation feature is perfect for getting started quickly, especially in SageMaker notebooks, Cloud9, or any environment where you want to focus on building your agent rather than managing infrastructure!

##  Quick Troubleshooting

**Port 8080 already in use?**
- Stop other services or use a different port

**"Docker not found" error?**
- Install Docker Desktop for deployment

**Permission errors?**
- Make sure your AWS credentials are configured: `aws configure`

**Code build error?**
- Check code build project with agent name as suffix for latest build and its logs

## 🚀 Next Steps

Ready to build something amazing? Check out:

- **[Runtime Overview](overview.md)** - Deep dive into AgentCore features
- **[Memory Guide](../memory/quickstart.md)** - Add persistent memory
- **[Gateway Tools](../gateway/quickstart.md)** - Connect external APIs
- **[Examples](../../examples/README.md)** - More complete examples
