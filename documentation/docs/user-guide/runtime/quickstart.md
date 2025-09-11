# QuickStart: Your First Agent in 5 Minutes! 🚀

Get your AI agent running on Amazon Bedrock AgentCore following these steps.

## Prerequisites

Before starting, make sure you have:

- **AWS Account** with credentials configured in your desired region (`aws configure`) ([AWS CLI setup guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html))
- **Python 3.10+** installed
- **AWS Permissions**:
  - `BedrockAgentCoreFullAccess` managed policy
  - `AmazonBedrockFullAccess` managed policy
  - **Caller permissions**: [See detailed policy here](permissions.md#developercaller-permissions)
- **Model access**: Enable Anthropic Claude models in [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/)

## Step 1: Setup and Install

Create a project folder and install the required packages:

### Option A: Using uv (Faster - Recommended)

```bash
# Install uv (one-time setup)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
mkdir agentcore-runtime-quickstart
cd agentcore-runtime-quickstart
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
uv pip install bedrock-agentcore-starter-toolkit strands-agents
```

### Option B: Using Standard Python

```bash
# Setup project
mkdir agentcore-runtime-quickstart
cd agentcore-runtime-quickstart
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install bedrock-agentcore-starter-toolkit strands-agents
```

### Verify Installation

```bash
agentcore --help  # Verify the CLI is installed
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

Create `requirements.txt` (for container deployment):

```bash
echo "strands-agents" > requirements.txt
```

## Step 3: Test Locally

```bash
# Start your agent
python my_agent.py

# Test it (in another terminal)
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

## Step 4: Deploy to Cloud

```bash
# Configure your agent (creates .bedrock_agentcore.yaml config file)
agentcore configure --entrypoint my_agent.py

# Deploy to cloud (reads config from .bedrock_agentcore.yaml)
agentcore launch

# Test your deployed agent
agentcore invoke '{"prompt": "Hello AgentCore!"}'
```

🎉 **Congratulations!** Your agent is now running on Amazon Bedrock AgentCore!

## What Just Happened?

When you ran `agentcore launch`, the toolkit automatically:

1. **Built your container** using AWS CodeBuild (ARM64 architecture)
1. **Created AWS resources** (if first time):
- IAM execution role with required permissions
- ECR repository for your container images
- CodeBuild project for future builds
1. **Deployed your agent** to AgentCore Runtime
1. **Set up logging** in CloudWatch

All resources are named based on your agent name for easy identification.

### Find Your Resources

After deployment, view your resources in AWS Console:

- **Agent Logs**: CloudWatch → Log groups → `/aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT`
- **Container Images**: ECR → Repositories → `bedrock-agentcore-{agent-name}`
- **Build Logs**: CodeBuild → Build history
- **IAM Role**: IAM → Roles → Search for “BedrockAgentCore”

## Region Configuration

By default, the toolkit deploys to `us-west-2`. To use a different region:

```bash
# Option 1: Use --region flag
agentcore configure -e my_agent.py --region us-east-1
agentcore launch

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
|**“Port 8080 in use”** (local only)|`lsof -ti:8080                                         |

## Using Other Frameworks

### LangGraph Example

Create `langgraph_agent.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

app = BedrockAgentCoreApp()

# Define state
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize Bedrock LLM
llm = ChatBedrock(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    model_kwargs={"temperature": 0.7}
)

# Define agent function
def chat_node(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# Build graph
workflow = StateGraph(State)
workflow.add_node("chat", chat_node)
workflow.add_edge(START, "chat")
workflow.add_edge("chat", END)
graph = workflow.compile()

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "Hello!")
    result = graph.invoke({
        "messages": [{"role": "user", "content": user_message}]
    })
    # Extract the assistant's response
    last_message = result["messages"][-1]
    return {"result": last_message.content}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt`:

```bash
echo "langchain-aws
langgraph" > requirements.txt
```

Deploy:

```bash
agentcore configure --entrypoint langgraph_agent.py
agentcore launch
agentcore invoke '{"prompt": "What is LangGraph?"}'
```

### CrewAI Example

Create `crewai_agent.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from crewai import Agent, Task, Crew, Process
import os

app = BedrockAgentCoreApp()

# CrewAI with litellm expects the model in format: bedrock/model-id
# Set AWS region for litellm to use
os.environ["AWS_DEFAULT_REGION"] = os.environ.get("AWS_REGION", "us-west-2")

# Create agent with Bedrock model
researcher = Agent(
    role="Research Assistant",
    goal="Provide helpful and accurate information",
    backstory="You are a knowledgeable research assistant",
    verbose=False,
    llm="bedrock/us.anthropic.claude-3-7-sonnet-20250219-v1:0",  # litellm format
    max_iter=2  # Limit iterations to prevent runaway costs
)

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "Hello!")

    # Create task
    task = Task(
        description=user_message,
        agent=researcher,
        expected_output="A helpful response to the user's question"
    )

    # Create crew
    crew = Crew(
        agents=[researcher],
        tasks=[task],
        process=Process.sequential,
        verbose=False
    )

    # Execute
    result = crew.kickoff()
    return {"result": result.raw}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt`:

```bash
echo "crewai
crewai-tools" > requirements.txt
```

Deploy:

```bash
agentcore configure --entrypoint crewai_agent.py
agentcore launch
agentcore invoke '{"prompt": "What is CrewAI?"}'
```

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

**Note**: Docker is only required for `--local` and `--local-build` modes. The default mode uses AWS CodeBuild.

### Custom Configuration

```bash
# Use existing IAM role
agentcore configure -e my_agent.py --execution-role arn:aws:iam::123456789012:role/MyRole

# Add custom dependencies
# Create requirements.txt with additional packages:
echo "requests>=2.31.0
boto3>=1.34.0" > requirements.txt
agentcore configure -e my_agent.py
```

### Why ARM64?

AgentCore Runtime requires ARM64 containers (AWS Graviton). The toolkit handles this automatically:

- **Default (CodeBuild)**: Builds ARM64 containers in the cloud - no Docker needed
- **Local with Docker**: Uses buildx for cross-platform ARM64 builds on x86 machines

## Next Steps

- **[Add tools with Gateway](../gateway/quickstart.md)** - Connect your agent to APIs and services
- **[Enable memory](../../examples/memory-integration.md)** - Give your agent conversation history
- **[Configure authentication](../runtime/auth.md)** - Set up OAuth/JWT auth
- **[View more examples](../../examples/README.md)** - Learn from complete implementations
