# QuickStart: Your First Agent in 5 Minutes! 🚀

Let's get your first AI agent running on Amazon Bedrock AgentCore in just a few minutes!

## What You Need

- An AWS account
- Python 3.10+ installed
- 5 minutes of your time ⏰

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

Ready to deploy to the cloud? First, install the starter toolkit and set up your project:

```bash
# Install the starter toolkit
pip install bedrock-agentcore-starter-toolkit

# Create requirements.txt
echo "bedrock-agentcore
strands-agents" > requirements.txt

# Configure your agent
agentcore configure -e my_agent.py -er <AGENT_IAM_EXECUTION_ROLE>

# Test locally with the toolkit
agentcore launch -l

# In another terminal, test it:
agentcore invoke '{"prompt": "Hello!"}' -l

# Deploy to AWS
agentcore launch

# Test your deployed agent
agentcore invoke '{"prompt": "tell me a joke"}'
```

## 🎯 What Just Happened?

1. **BedrockAgentCoreApp** - This wraps your function into an HTTP service
2. **@app.entrypoint** - This decorator tells AgentCore "this is my main function"
3. **Local Testing** - Your agent runs on `http://localhost:8080`
4. **Cloud Deploy** - The toolkit packages everything and deploys to AWS

## 🆘 Quick Troubleshooting

**Port 8080 already in use?**
- Stop other services or use a different port

**"Docker not found" error?**
- Install Docker Desktop for deployment

**Permission errors?**
- Make sure your AWS credentials are configured: `aws configure`

## 🚀 Next Steps

Ready to build something amazing? Check out:

- **[Runtime Overview](overview.md)** - Deep dive into AgentCore features
- **[Memory Guide](../memory/quickstart.md)** - Add persistent memory
- **[Gateway Tools](../gateway/quickstart.md)** - Connect external APIs
- **[Examples](../../examples/README.md)** - More complete examples
