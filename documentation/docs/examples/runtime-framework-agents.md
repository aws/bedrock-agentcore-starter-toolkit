# Framework Agents Examples

This guide shows how to use popular AI agent frameworks with Amazon Bedrock AgentCore Runtime.

## Prerequisites

Before starting, ensure you've completed the [QuickStart guide](../runtime/quickstart.md) and have:
- AWS credentials configured
- AgentCore CLI installed (`agentcore --help` works)
- A project folder with virtual environment activated

## LangGraph Agent

LangGraph enables building stateful, multi-actor applications with LLMs.

### Installation

```bash
pip install langchain-aws langgraph
```

### Create the Agent

Create `langgraph_agent.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

app = BedrockAgentCoreApp()

# Define state for conversation memory
class State(TypedDict):
    messages: Annotated[list, add_messages]

# Initialize Bedrock LLM
llm = ChatBedrock(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    model_kwargs={"temperature": 0.7}
)

# Define the chat node that processes messages
def chat_node(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# Build the graph
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

### Deploy

```bash
# Create requirements.txt for container
echo "langchain-aws
langgraph" > requirements.txt

# Configure and deploy
agentcore configure --entrypoint langgraph_agent.py
agentcore launch

# Test
agentcore invoke '{"prompt": "Explain LangGraph in one sentence"}'
```

## CrewAI Agent

CrewAI enables building collaborative AI agent teams.

### Installation

```bash
pip install crewai crewai-tools
```

### Create the Agent

Create `crewai_agent.py`:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from crewai import Agent, Task, Crew, Process
import os

app = BedrockAgentCoreApp()

# Set AWS region for litellm (used by CrewAI)
os.environ["AWS_DEFAULT_REGION"] = os.environ.get("AWS_REGION", "us-west-2")

# Create an agent with specific role and capabilities
researcher = Agent(
    role="Research Assistant",
    goal="Provide helpful and accurate information",
    backstory="You are a knowledgeable research assistant with expertise in many domains",
    verbose=False,
    llm="bedrock/us.anthropic.claude-3-7-sonnet-20250219-v1:0",  # litellm format required
    max_iter=2  # Limit iterations to control costs
)

@app.entrypoint
def invoke(payload):
    user_message = payload.get("prompt", "Hello!")

    # Create a task for the agent
    task = Task(
        description=user_message,
        agent=researcher,
        expected_output="A helpful and informative response"
    )

    # Create and run the crew
    crew = Crew(
        agents=[researcher],
        tasks=[task],
        process=Process.sequential,
        verbose=False
    )

    result = crew.kickoff()
    return {"result": result.raw}

if __name__ == "__main__":
    app.run()
```

### Deploy

```bash
# Create requirements.txt for container
echo "crewai
crewai-tools" > requirements.txt

# Configure and deploy
agentcore configure --entrypoint crewai_agent.py
agentcore launch

# Test
agentcore invoke '{"prompt": "What are the benefits of using CrewAI?"}'
```

## Key Differences Between Frameworks

| Framework | Best For | Key Features |
|-----------|----------|--------------|
| **Strands** | Simple agents | Minimal setup, built-in tools, great for beginners |
| **LangGraph** | Stateful workflows | Graph-based flows, state management, complex routing |
| **CrewAI** | Multi-agent teams | Role-based agents, collaborative tasks, delegation |

## Common Patterns

### Adding Tools

All frameworks support tools. Here's an example with Strands:

```python
from strands import Agent, tool

@tool
def get_weather(location: str) -> str:
    """Get weather for a location."""
    return f"Weather in {location}: Sunny, 72°F"

agent = Agent(tools=[get_weather])
```

### Error Handling

Always include error handling in production:

```python
@app.entrypoint
def invoke(payload):
    try:
        user_message = payload.get("prompt", "Hello!")
        # Your agent logic here
        return {"result": response}
    except Exception as e:
        app.logger.error(f"Agent error: {e}")
        return {"error": "An error occurred processing your request"}
```

### Using Environment Variables

For API keys or configuration:

```python
import os

@app.entrypoint
def invoke(payload):
    api_key = os.environ.get("MY_API_KEY")
    # Use the API key in your agent logic
```

Then set the environment variable during deployment:

```bash
agentcore launch --env MY_API_KEY=your-key-here
```

## Troubleshooting

### Model Access Issues

If you see "model access denied":
1. Ensure Claude models are enabled in Bedrock console
2. Check you're using the correct model ID format
3. Verify your AWS region matches where models are enabled

### CrewAI Specific Issues

CrewAI uses litellm, which requires:
- Model format: `bedrock/model-id` (not just `model-id`)
- AWS_DEFAULT_REGION environment variable set
