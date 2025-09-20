# Amazon Bedrock AgentCore Quickstart

## Introduction

Amazon Bedrock AgentCore is a suite of services designed to accelerate AI agent development, deployment, and management. Unlike traditional ML platforms, AgentCore offers specialized infrastructure for agentic workflows with memory persistence, tool connectivity, and secure runtime environments.

This quickstart guide will show you how to build and deploy a fully-functional AI agent with:

- **Short-term and long-term memory** to recall conversations within and across sessions
- **Gateway integration** for tool access (with a calculator example)
- **Secure runtime deployment** for production-ready hosting

By the end, you'll have an agent that remembers user preferences, accesses tools, and runs in a secure, scalable environment—all without managing complex infrastructure.

## Prerequisites

Before starting, ensure you have:

- An AWS account with appropriate permissions
- AWS CLI configured with credentials (`aws configure`)
- Access to Amazon Bedrock models (Claude 3.7 Sonnet)
- Python 3.10 or newer

### Installation

Set up your environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install required packages
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

## Let's Define Our Agent

First, we'll create an AI agent with memory capabilities using the Strands framework. This agent will form the foundation for our memory and gateway integrations.

Create a file named `agent.py`:

```python
"""
This is your AI agent with memory capabilities.
It uses Strands framework and can optionally connect to AgentCore Memory.
"""

import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent

# Initialize the AgentCore runtime app
app = BedrockAgentCoreApp()

# Connect to memory service (if MEMORY_ID is set)
memory_client = MemoryClient(region_name='us-west-2')
MEMORY_ID = os.getenv('MEMORY_ID')

class MemoryHook(HookProvider):
    """
    This hook automatically handles memory operations:
    - Loads previous conversation when agent starts
    - Saves each message after it's processed
    """

    def on_agent_initialized(self, event):
        """Runs when agent starts - loads conversation history"""
        if not MEMORY_ID: return

        # Get last 3 conversation turns from memory
        turns = memory_client.get_last_k_turns(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id", "default"),
            k=3  # Number of previous exchanges to remember
        )

        # Add conversation history to agent's context
        if turns:
            context = "\n".join([f"{m['role']}: {m['content']['text']}"
                               for t in turns for m in t])
            event.agent.system_prompt += f"\n\nPrevious:\n{context}"

    def on_message_added(self, event):
        """Runs after each message - saves it to memory"""
        if not MEMORY_ID: return

        # Save the latest message to memory
        msg = event.agent.messages[-1]
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id", "default"),
            messages=[(str(msg["content"]), msg["role"])]
        )

    def register_hooks(self, registry):
        """Registers both hooks with the agent"""
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)

# Create the Strands agent
agent = Agent(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",  # Bedrock Claude model
    system_prompt="You're a helpful assistant with memory.",
    hooks=[MemoryHook()] if MEMORY_ID else [],  # Add memory hook if configured
    state={"session_id": "default"}
)

@app.entrypoint
def invoke(payload, context):
    """
    Main entry point - this function runs for each user message.
    - payload: Contains the user's prompt
    - context: Contains runtime info like session_id
    """
    # Use the session ID from runtime (for session isolation)
    if hasattr(context, 'session_id'):
        agent.state.set("session_id", context.session_id)

    # Process the user's message and return response
    response = agent(payload.get("prompt", "Hello"))
    return response.message['content'][0]['text']

if __name__ == "__main__":
    app.run()  # Start the agent locally for testing
```

Let's also create a `requirements.txt` file for deployment:

```
bedrock-agentcore
strands-agents
```

## Let's Add Short-term and Long-term Memory

Now, let's create memory resources for our agent. AgentCore Memory provides two types of memory:

1. **Short-term memory (STM)**: Stores raw conversation turns within a session
2. **Long-term memory (LTM)**: Intelligently extracts and retains information across sessions

Create a file named `setup_memory.py`:

```python
"""
This script creates two types of memory resources:
1. STM (Short-Term Memory): Remembers within session only
2. LTM (Long-Term Memory): Extracts and remembers across sessions

Run this once to create your memory resources.
"""

from bedrock_agentcore.memory import MemoryClient
import uuid

# Connect to AgentCore Memory service
client = MemoryClient(region_name='us-west-2')

print("Creating memory resources...\n")

# === SHORT-TERM MEMORY ===
# Only stores raw conversation, no intelligent extraction
stm = client.create_memory_and_wait(
    name=f"Demo_STM_{uuid.uuid4().hex[:8]}",  # Unique name
    strategies=[],  # Empty = no extraction strategies
    event_expiry_days=7  # Keep conversations for 7 days
)
print(f"✅ STM Memory Created: {stm['id']}")
print("   What it does:")
print("   - Stores exact conversation messages")
print("   - Remembers within the same session only")
print("   - Instant retrieval (no processing needed)")

# === LONG-TERM MEMORY ===
# Intelligently extracts preferences and facts
ltm = client.create_memory_and_wait(
    name=f"Demo_LTM_{uuid.uuid4().hex[:8]}",
    strategies=[
        # Extracts user preferences like "I prefer Python"
        {"userPreferenceMemoryStrategy": {
            "name": "prefs",
            "namespaces": ["/user/preferences"]
        }},
        # Extracts facts like "My birthday is in January"
        {"semanticMemoryStrategy": {
            "name": "facts",
            "namespaces": ["/user/facts"]
        }}
    ],
    event_expiry_days=30  # Keep for 30 days
)
print(f"\n✅ LTM Memory Created: {ltm['id']}")
print("   What it does:")
print("   - Everything STM does PLUS:")
print("   - Extracts preferences and facts automatically")
print("   - Remembers across different sessions")
print("   - Needs 5-10 seconds to process extractions")

print("\n" + "="*60)
print("Choose which memory to use:")
print(f"  export MEMORY_ID={stm['id']}  # For STM demo")
print(f"  export MEMORY_ID={ltm['id']}  # For LTM demo")
print("="*60)
```

Run the memory setup script:

```bash
python setup_memory.py
```

You'll see output showing the IDs for both memory types. Note these IDs—you'll use them to set the `MEMORY_ID` environment variable when deploying your agent.

## Let's Add Gateway with a Calculator Tool

Now we'll add a gateway with a calculator tool. Gateway allows your agent to access tools securely.

Create `setup_gateway.py`:

```python
"""
This script creates a gateway with a calculator tool.
The gateway provides a secure way for your agent to access tools.
"""

from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json
import logging
import uuid

# Create a unique name for the gateway
gateway_name = f"Demo_Gateway_{uuid.uuid4().hex[:8]}"

# Initialize client
client = GatewayClient(region_name="us-west-2")
client.logger.setLevel(logging.INFO)

# Create OAuth authorizer with Cognito
print("Creating OAuth authorization server...")
cognito_response = client.create_oauth_authorizer_with_cognito(gateway_name)
print("✅ Authorization server created\n")

# Create Gateway
print("Creating Gateway...")
gateway = client.create_mcp_gateway(
    name=gateway_name,
    role_arn=None,  # Auto-creates IAM role
    authorizer_config=cognito_response["authorizer_config"],
    enable_semantic_search=True,
)
print(f"✅ Gateway created: {gateway['gatewayUrl']}\n")

# Fix IAM permissions
print("Fixing IAM permissions...")
client.fix_iam_permissions(gateway)
print("⏳ Waiting 30s for IAM propagation...")
import time
time.sleep(30)
print("✅ IAM permissions configured\n")

# Add calculator Lambda target
print("Adding calculator Lambda target...")
calculator_schema = {
    "inlinePayload": [
        {
            "name": "calculate",
            "description": "Perform a mathematical calculation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "The mathematical operation to perform"
                    },
                    "a": {"type": "number", "description": "First operand"},
                    "b": {"type": "number", "description": "Second operand"}
                },
                "required": ["operation", "a", "b"]
            }
        }
    ]
}

lambda_target = client.create_mcp_gateway_target(
    gateway=gateway,
    name="CalculatorTool",
    target_type="lambda",
    target_payload={"toolSchema": calculator_schema}
)
print("✅ Calculator target added\n")

# Get access token
print("Getting access token...")
access_token = client.get_access_token_for_cognito(cognito_response["client_info"])
print("✅ Access token obtained\n")

# Save configuration for agent
config = {
    "gateway_url": gateway["gatewayUrl"],
    "gateway_id": gateway["gatewayId"],
    "access_token": access_token
}

with open("gateway_config.json", "w") as f:
    json.dump(config, f, indent=2)

print("=" * 60)
print("✅ Gateway setup complete!")
print(f"Gateway URL: {gateway['gatewayUrl']}")
print(f"Gateway ID: {gateway['gatewayId']}")
print("\nConfiguration saved to: gateway_config.json")
print("=" * 60)
```

Run the gateway setup script:

```bash
python setup_gateway.py
```

The script creates a gateway with a calculator tool and saves the configuration to `gateway_config.json`.

## Let's Update Our Agent to Use the Gateway

Now, let's update our agent to use the gateway. Create `agent_with_gateway.py`:

```python
"""
Enhanced agent with both memory and gateway integration.
"""

import os
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import asyncio
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent

# Initialize the AgentCore runtime app
app = BedrockAgentCoreApp()

# Connect to memory service (if MEMORY_ID is set)
memory_client = MemoryClient(region_name='us-west-2')
MEMORY_ID = os.getenv('MEMORY_ID')

# Load gateway configuration
gateway_config = {}
try:
    with open("gateway_config.json", "r") as f:
        gateway_config = json.load(f)
    print(f"Loaded gateway config: {gateway_config['gateway_url']}")
except:
    print("Gateway config not found. Only memory features will be available.")


class MemoryHook(HookProvider):
    """Handles memory operations - same as before"""

    def on_agent_initialized(self, event):
        if not MEMORY_ID: return

        turns = memory_client.get_last_k_turns(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id", "default"),
            k=3
        )

        if turns:
            context = "\n".join([f"{m['role']}: {m['content']['text']}"
                               for t in turns for m in t])
            event.agent.system_prompt += f"\n\nPrevious:\n{context}"

    def on_message_added(self, event):
        if not MEMORY_ID: return

        msg = event.agent.messages[-1]
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id="user",
            session_id=event.agent.state.get("session_id", "default"),
            messages=[(str(msg["content"]), msg["role"])]
        )

    def register_hooks(self, registry):
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(MessageAddedEvent, self.on_message_added)


async def get_gateway_tools():
    """Get tools from gateway using MCP"""
    if not gateway_config:
        return None

    try:
        gateway_url = gateway_config["gateway_url"]
        access_token = gateway_config["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}

        async with streamablehttp_client(gateway_url, headers=headers) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                print(f"Found {len(tools_result.tools)} tools in Gateway")
                return tools_result.tools
    except Exception as e:
        print(f"Gateway error: {e}")
        return None


# Create the Strands agent
agent = Agent(
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    system_prompt="You're a helpful assistant with memory and calculation abilities.",
    hooks=[MemoryHook()] if MEMORY_ID else [],
    state={"session_id": "default"}
)

@app.entrypoint
def invoke(payload, context):
    """Main entry point with gateway integration"""
    # Use the session ID from runtime
    if hasattr(context, 'session_id'):
        agent.state.set("session_id", context.session_id)

    # Try to get gateway tools
    gateway_tools = None
    if gateway_config:
        try:
            gateway_tools = asyncio.run(get_gateway_tools())
            if gateway_tools:
                # Update agent with gateway tools
                agent.tools = gateway_tools
        except Exception as e:
            print(f"Error getting gateway tools: {e}")

    # Process the user's message
    response = agent(payload.get("prompt", "Hello"))
    return response.message['content'][0]['text']

if __name__ == "__main__":
    app.run()
```

Update `requirements.txt` to include MCP:

```
bedrock-agentcore
strands-agents
mcp
```

## Deploying to AgentCore Runtime

Now, let's deploy our agent to AgentCore Runtime. Runtime provides a secure, managed environment for your agent.

```bash
# Configure the agent for deployment
agentcore configure -e agent_with_gateway.py

# Deploy with short-term memory
export MEMORY_ID=<your-stm-id>  # Use the STM ID from the setup_memory.py output
agentcore launch
```

AgentCore CLI will handle:
1. Creating a container image with your agent code
2. Setting up necessary IAM roles and permissions
3. Deploying to a secure, managed runtime environment

After deployment completes (it may take a few minutes), you'll see output with your agent's ARN and endpoint details.

## Testing Your Agent

Now let's test our agent's memory and gateway capabilities!

### Testing Short-Term Memory

```bash
# First interaction - tell agent your name
agentcore invoke '{"prompt": "My name is Bob"}'

# Second interaction - see if agent remembers
agentcore invoke '{"prompt": "What is my name?"}'
```

You should see the agent respond with "Your name is Bob" in the second interaction, demonstrating short-term memory within the session.

### Testing Gateway Calculator

```bash
# Test calculator functionality
agentcore invoke '{"prompt": "Calculate 25 multiplied by 18"}'

# Try addition
agentcore invoke '{"prompt": "What is 42 + 28?"}'
```

The agent should use the gateway calculator tool to perform these calculations and return the correct results.

### Testing Long-Term Memory

Now, let's deploy with long-term memory and test cross-session memory:

```bash
# Update deployment with long-term memory
export MEMORY_ID=<your-ltm-id>  # Use the LTM ID from setup_memory.py output
agentcore launch

# Tell agent your preferences in one session
SESSION1="first-session-12345678901234567890123456"
agentcore invoke '{"prompt": "I prefer Python and short answers"}' --session-id $SESSION1

# Wait for extraction (async process)
echo "Waiting 10 seconds for LTM extraction..."
sleep 10

# Different session still remembers!
SESSION2="second-session-98765432109876543210987654"
agentcore invoke '{"prompt": "What are my preferences?"}' --session-id $SESSION2
```

Even though you're using a completely different session, the agent should remember that you prefer Python and short answers, demonstrating long-term memory extraction and recall.

## What's Happening Behind the Scenes?

1. **Short-Term Memory**: The `MemoryHook` class automatically saves each message to AgentCore Memory and loads recent conversation turns when the agent starts.

2. **Long-Term Memory**: The memory strategies you created automatically extract user preferences and facts from conversations. These extracted memories persist across different sessions.

3. **Gateway**: The agent connects to the gateway you created and discovers the calculator tool using the MCP (Model Context Protocol). When you ask calculation questions, the agent invokes this tool to get accurate results.

4. **Runtime**: AgentCore Runtime provides a secure, isolated environment for your agent with automatic scaling and session management.

## Conclusion

Congratulations! In just 15 minutes, you've built and deployed a production-ready AI agent with:

- **Memory capabilities** that persist both within and across sessions
- **Tool access** through Gateway for accurate calculations
- **Secure runtime deployment** for production use

This foundation can be extended with additional tools, more sophisticated memory strategies, and integration with other AWS services to build powerful, context-aware AI applications.

## Next Steps

- Add more tools to your gateway (e.g., weather API, database access)
- Implement more complex memory strategies
- Build a web interface for your agent using API Gateway and Lambda
- Explore AgentCore Browser for web browsing capabilities
