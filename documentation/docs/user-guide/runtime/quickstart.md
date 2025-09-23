# QuickStart: Your First Agent in 5 Minutes! 🚀

Get your AI agent running on Amazon Bedrock AgentCore following these steps.

## Prerequisites

Before starting, make sure you have:

- **AWS Account** with credentials configured. To configure your AWS credentials, see [Configuration and credential file settings in the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).
- **Python 3.10+ installed**
- **AWS Permissions:** To create and deploy an agent with the starter toolkit, you must have appropriate permissions. For information, see [Use the starter toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-starter-toolkit).
- **Model access:** Anthropic Claude Sonnet 4.0 [enabled](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) in the Amazon Bedrock console. For information about using a different model with the Strands Agents see the Model Providers section in the [Strands Agents SDK](https://strandsagents.com/latest/documentation/docs/) documentation.


## Step 1: Setup project and Install dependencies

Create a project folder and install the required packages:

```bash
mkdir agentcore-runtime-quickstart
cd agentcore-runtime-quickstart
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use: `.venv\Scripts\activate`

Install packages:

```bash
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

Verify installation:

```bash
agentcore --help
```

## Step 2: Create Your Agent

Create a source file for your agent code named my_agent.py. Add the following code:


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

Create requirements.txt file and add the following:

```
bedrock-agentcore
strands-agents
```

## Step 3: Test Locally

Open a terminal window and start your agent with the following command:

```bash
python my_agent.py
```

Test your agent by opening another terminal window and enter the following command:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

You should see a response like `{"result": "Hello! I'm here to help..."}`.

Stop the agent with `Ctrl+C` when done testing.

**Important**: Make sure port 8080 is free before starting.

## Step 4: Configure Your Agent

Configure and deploy your agent to AWS using the starter toolkit. The toolkit automatically creates the [IAM execution role](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-execution-role), container image, and Amazon Elastic Container Registry repository needed to host the agent in AgentCore Runtime. By default the toolkit hosts the agent in an AgentCore Runtime that is in the us-west-2 AWS Region.

```bash
agentcore configure -e my_agent.py
```

- The `-e` or `-entrypoint` flag specifies the entrypoint file for your agent (the Python file containing your agent code)
- This command creates configuration for deployment to AWS
- Accept the default values unless you have specific requirements
- The configuration step creates a `.bedrock_agentcore.yaml` file that defines your agent's deployment settings.

### Using a Different Region

By default, the toolkit deploys to `us-west-2`. To use a different region:

Use the `-r` or `--region` flag during configuration:
```bash
agentcore configure -e my_agent.py -r us-east-1
```

## Step 5: Deploy to Cloud

Deploy your agent to AgentCore Runtime:

```bash
agentcore launch
```

This command:
- Builds your container using AWS CodeBuild (no Docker required locally)
- Creates necessary AWS resources (ECR repository, IAM roles, etc.)
- Deploys your agent to AgentCore Runtime
- Configures CloudWatch logging

**Note the output** - it will show:
- Your agent's ARN (needed for invoking the agent)
- CloudWatch log group location

## Step 6: Test Your Deployed Agent

Test that your agent is running in the cloud:

```bash
agentcore invoke '{"prompt": "tell me a joke"}'
```

If you see a joke in the response, your agent is successfully running in AgentCore Runtime!

If not, check the CloudWatch logs mentioned in the deployment output or see [Common Issues](#common-issues).

### Find Your Resources

After deployment, view your resources in AWS Console:

- **Agent Logs**: CloudWatch → Log groups → `/aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT`
- **Container Images**: ECR → Repositories → `bedrock-agentcore-{agent-name}`
- **Build Logs**: CodeBuild → Build history
- **IAM Role**: IAM → Roles → Search for "BedrockAgentCore"

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **"Permission denied"** | Run `aws sts get-caller-identity` to verify credentials. Check IAM policies are attached. |
| **"Model access denied"** | Enable Claude models in Bedrock console for your region |
| **"Docker not found" warning** | Ignore it! CodeBuild handles container building |
| **"Port 8080 in use"** (local only) | Use `lsof -ti:8080 \| xargs kill -9` (Mac/Linux) or find and stop the process on Windows |
| **"Region mismatch"** | Verify region with `aws configure get region` and ensure resources are in same region |

## Advanced Setup

### Deployment Modes

```bash
# Default - CodeBuild (no Docker needed)
agentcore launch

# Local development (requires Docker/Podman/Finch)
agentcore launch --local

# Local build + cloud deploy (requires Docker)
agentcore launch --local-build
```

**Note**: Docker is only required for `--local` and `--local-build` modes. The default mode uses AWS CodeBuild.

### Custom Configuration

Use an existing IAM role:

```bash
agentcore configure -e my_agent.py --execution-role arn:aws:iam::123456789012:role/MyRole
```

### Why ARM64?

AgentCore Runtime requires ARM64 containers (AWS Graviton). The toolkit handles this automatically:

- **Default (CodeBuild)**: Builds ARM64 containers in the cloud - no Docker needed
- **Local with Docker**: Only containers built on ARM64 machines will work when deployed to agentcore runtime

## Next Steps

- **[Framework Examples](../../examples/runtime-framework-agents.md)** - Use LangGraph, CrewAI, and other frameworks
- **[Add tools with Gateway](../gateway/quickstart.md)** - Connect your agent to APIs and services
- **[Enable memory](../../examples/memory-integration.md)** - Give your agent conversation history
- **[Configure authentication](../runtime/auth.md)** - Set up OAuth/JWT auth
- **[View more examples](../../examples/README.md)** - Learn from complete implementations
