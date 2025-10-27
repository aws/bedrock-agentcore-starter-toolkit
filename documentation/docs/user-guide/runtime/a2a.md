# Deploy A2A servers in AgentCore Runtime

Amazon Bedrock AgentCore AgentCore Runtime lets you deploy and run Agent-to-Agent (A2A)
servers in the AgentCore Runtime. This guide walks you through creating, testing, and deploying your
first A2A server.

In this section, you learn:

* How
  Amazon Bedrock AgentCore supports A2A
* How to create an A2A server with agent capabilities
* How to test your server locally
* How to deploy your server to AWS
* How to invoke your deployed server
* How to retrieve agent cards for discovery

###### Topics

* [How
  Amazon Bedrock AgentCore supports A2A](#runtime-a2a-how-agentcore-supports "#runtime-a2a-how-agentcore-supports")
* [Using A2A with AgentCore Runtime](#runtime-a2a-steps "#runtime-a2a-steps")
* [Appendix](#runtime-a2a-appendix "#runtime-a2a-appendix")

## How Amazon Bedrock AgentCore supports A2A

Amazon Bedrock AgentCore's A2A protocol support enables seamless integration with
A2A servers by acting as a transparent proxy layer. When configured for A2A,
Amazon Bedrock AgentCore expects containers to run stateless, streamable HTTP servers on port
`9000` at the root path (`0.0.0.0:9000/`), which aligns with the default A2A server
configuration.

The service provides enterprise-grade session isolation while maintaining protocol
transparency - JSON-RPC payloads from the [InvokeAgentRuntime](https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_InvokeAgentRuntime.html "https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_InvokeAgentRuntime.html") API are passed
through directly to the A2A container without modification. This architecture preserves
the standard A2A protocol features like built-in agent discovery through Agent Cards at
`/.well-known/agent-card.json` and JSON-RPC communication, while adding enterprise
authentication (SigV4/OAuth 2.0) and scalability.

The key differentiators from other protocols are the port (9000 vs 8080 for HTTP),
mount path (`/` vs `/invocations`), and the standardized agent discovery mechanism, making
Amazon Bedrock AgentCore an ideal deployment platform for A2A agents in production
environments.

Key differences from other
protocols:

**Port**
:   A2A servers run on port 9000 (vs 8080 for HTTP, 8000 for MCP)

**Path**
:   A2A servers are mounted at `/` (vs
    `/invocations` for HTTP, `/mcp` for
    MCP)

**Agent Cards**
:   A2A provides built-in agent discovery through Agent Cards at
    `/.well-known/agent-card.json`

**Protocol**
:   Uses JSON-RPC for agent-to-agent communication

**Authentication**
:   Supports both SigV4 and OAuth 2.0 authentication schemes

For more information, see [https://a2a-protocol.org/](https://a2a-protocol.org/ "https://a2a-protocol.org/").

## Using A2A with AgentCore Runtime

In this tutorial you create, test, and deploy an A2A server.

###### Topics

* [Prerequisites](#runtime-a2a-prerequisites "#runtime-a2a-prerequisites")
* [Step 1: Create your A2A server](#runtime-a2a-create-server "#runtime-a2a-create-server")
* [Step 2: Test your A2A server locally](#runtime-a2a-test-locally "#runtime-a2a-test-locally")
* [Step 3: Deploy your A2A server to Bedrock
  AgentCore Runtime](#runtime-a2a-deploy "#runtime-a2a-deploy")
* [Step 4: Get the agent card](#runtime-a2a-step-4 "#runtime-a2a-step-4")
* [Step 5: Invoke your deployed A2A server](#runtime-a2a-step-5 "#runtime-a2a-step-5")

### Prerequisites

* Python 3.10 or higher installed and basic understanding of Python
* An AWS account with appropriate permissions and local credentials
  configured
* Understanding of the A2A protocol and agent-to-agent communication
  concepts

### Step 1: Create your A2A server

We are showing an example with strands, but you can use other ways to build with
A2A.

#### Install required packages

First, install the required packages for A2A:

```
pip install strands-agents[a2a]
pip install bedrock-agentcore
pip install strands-agents-tools
```

#### Create your first A2A server

Create a new file called `my_a2a_server.py`:

```

import logging
import os
from strands_tools.calculator import calculator
from strands import Agent
from strands.multiagent.a2a import A2AServer
import uvicorn
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)

# Use the complete runtime URL from environment variable, fallback to local
runtime_url = os.environ.get('AGENTCORE_RUNTIME_URL', 'http://127.0.0.1:9000/')

logging.info(f"Runtime URL: {runtime_url}")

strands_agent = Agent(
    name="Calculator Agent",
    description="A calculator agent that can perform basic arithmetic operations.",
    tools=[calculator],
    callback_handler=None
)

host, port = "0.0.0.0", 9000

# Pass runtime_url to http_url parameter AND use serve_at_root=True
a2a_server = A2AServer(
    agent=strands_agent,
    http_url=runtime_url,
    serve_at_root=True  # Serves locally at root (/) regardless of remote URL path complexity
)

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "healthy"}

app.mount("/", a2a_server.to_fastapi_app())

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)

```

#### Understanding the code

**Strands Agent**
:   Creates an agent with specific tools and capabilities

**A2AServer**
:   Wraps the agent to provide A2A protocol compatibility

**Agent Card URL**
:   Dynamically constructs the correct URL based on deployment context
    using the `AGENTCORE_RUNTIME_URL` environment
    variable

**Port 9000**
:   A2A servers run on port 9000 by default in AgentCore Runtime

### Step 2: Test your A2A server locally

Run and test your A2A server in a local development environment.

#### Start your A2A server

Run your A2A server locally:

```
python my_a2a_server.py
```

You should see output indicating the server is running on port
`9000`.

#### Invoke agent

```
curl -X POST http://0.0.0.0:9000 \\
-H "Content-Type: application/json" \\
-d '{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "what is 101 * 11?"
        }
      ],
      "messageId": "12345678-1234-1234-1234-123456789012"
    }
  }
}' | jq .
```

#### Test agent card retrieval

You can test the agent card endpoint locally:

```
curl http://localhost:9000/.well-known/agent-card.json | jq .
```

You can also test your deployed server using the A2A Inspector as described in
[Remote testing with A2A inspector](https://github.com/a2aproject/a2a-inspector "https://github.com/a2aproject/a2a-inspector").

### Step 3: Deploy your A2A server to Bedrock AgentCore Runtime

Deploy your A2A server to AWS using the Amazon Bedrock AgentCore starter toolkit.

#### Install deployment tools

Install the Amazon Bedrock AgentCore starter toolkit:

```
pip install bedrock-agentcore-starter-toolkit
```

Start by creating a project folder with the following structure:

```
## Project Folder Structure
your_project_directory/
├── a2a_server.py          # Your main agent code
├── requirements.txt       # Dependencies for your agent
```

Create a new file called `requirements.txt`, add the
following to it:

```
strands-agents[a2a]
bedrock-agentcore
strands-agents-tools
```

#### Set up Cognito user pool for authentication

Configure authentication for secure access to your deployed
server. For detailed Cognito setup instructions, see [Set up Cognito user
pool for authentication](./runtime-mcp.html#runtime-mcp-appendix-a "./runtime-mcp.html#runtime-mcp-appendix-a"). This provides the OAuth tokens required for
secure access to your deployed server.

#### Configure your A2A server for deployment

After setting up authentication, create the deployment configuration:

```
agentcore configure -e my_a2a_server.py --protocol A2A
```

* Select protocol as A2A
* Configure with OAuth configuration as setup in the previous
  step

#### Deploy to AWS

Deploy your agent:

```
agentcore launch
```

After deployment, you'll receive an agent runtime ARN that looks like:

```
arn:aws:bedrock-agentcore:us-west-2:accountId:runtime/my_a2a_server-xyz123
```

### Step 4: Get the agent card

Agent Cards are JSON metadata documents that describe an A2A server's identity, capabilities, skills, service endpoint, and authentication requirements. They enable automatic agent discovery in the A2A ecosystem.

#### Set up environment variables

Set up environment variables

1. Export bearer token as an environment variable. For bearer token setup, see [Bearer token setup](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html#runtime-mcp-appendix "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html#runtime-mcp-appendix").

   ```
   export BEARER_TOKEN="<BEARER_TOKEN>"
   ```
2. Export the agent ARN.

   ```
   export AGENT_ARN="arn:aws:bedrock-agentcore:us-west-2:accountId:runtime/my_a2a_server-xyz123"
   ```

#### Retrieve agent card

```
import os
import json
import requests
from uuid import uuid4
from urllib.parse import quote

def fetch_agent_card():
    # Get environment variables
    agent_arn = os.environ.get('AGENT_ARN')
    bearer_token = os.environ.get('BEARER_TOKEN')

    if not agent_arn:
        print("Error: AGENT_ARN environment variable not set")
        return

    if not bearer_token:
        print("Error: BEARER_TOKEN environment variable not set")
        return

    # URL encode the agent ARN
    escaped_agent_arn = quote(agent_arn, safe='')

    # Construct the URL
    url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{escaped_agent_arn}/invocations/.well-known/agent-card.json"

    # Generate a unique session ID
    session_id = str(uuid4())
    print(f"Generated session ID: {session_id}")

    # Set headers
    headers = {
        'Accept': '*/*',
        'Authorization': f'Bearer {bearer_token}',
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': session_id
    }

    try:
        # Make the request
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Parse and pretty print JSON
        agent_card = response.json()
        print(json.dumps(agent_card, indent=2))

        return agent_card

    except requests.exceptions.RequestException as e:
        print(f"Error fetching agent card: {e}")
        return None

if __name__ == "__main__":
    fetch_agent_card()
```

After you get the URL from the Agent Card, export `AGENTCORE_RUNTIME_URL` as an environment variable:

```
export AGENTCORE_RUNTIME_URL="https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/<ARN>/invocations/"
```

### Step 5: Invoke your deployed A2A server

Create client code to invoke your deployed Amazon Bedrock AgentCore A2A server and send
messages to test the functionality.

Create a new file `my_a2a_client_remote.py` to invoke your deployed A2A server:

```

import asyncio
import logging
import os
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # set request timeout to 5 minutes

def create_message(*, role: Role = Role.user, text: str) -> Message:
    return Message(
        kind="message",
        role=role,
        parts=[Part(TextPart(kind="text", text=text))],
        message_id=uuid4().hex,
    )

async def send_sync_message(message: str):
    # Get runtime URL from environment variable
    runtime_url = os.environ.get('AGENTCORE_RUNTIME_URL')

    # Generate a unique session ID
    session_id = str(uuid4())
    print(f"Generated session ID: {session_id}")

    # Add authentication headers for Amazon Bedrock AgentCore
    headers = {"Authorization": f"Bearer {os.environ.get('BEARER_TOKEN')}",
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': session_id}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, headers=headers) as httpx_client:
        # Get agent card from the runtime URL
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=runtime_url)
        agent_card = await resolver.get_agent_card()

        # Agent card contains the correct URL (same as runtime_url in this case)
        # No manual override needed - this is the path-based mounting pattern

        # Create client using factory
        config = ClientConfig(
            httpx_client=httpx_client,
            streaming=False,  # Use non-streaming mode for sync response
        )
        factory = ClientFactory(config)
        client = factory.create(agent_card)

        # Create and send message
        msg = create_message(text=message)

        # With streaming=False, this will yield exactly one result
        async for event in client.send_message(msg):
            if isinstance(event, Message):
                logger.info(event.model_dump_json(exclude_none=True, indent=2))
                return event
            elif isinstance(event, tuple) and len(event) == 2:
                # (Task, UpdateEvent) tuple
                task, update_event = event
                logger.info(f"Task: {task.model_dump_json(exclude_none=True, indent=2)}")
                if update_event:
                    logger.info(f"Update: {update_event.model_dump_json(exclude_none=True, indent=2)}")
                return task
            else:
                # Fallback for other response types
                logger.info(f"Response: {str(event)}")
                return event

# Usage - Uses AGENTCORE_RUNTIME_URL environment variable
asyncio.run(send_sync_message("what is 101 * 11"))

```

## Appendix

###### Topics

* [Set up Cognito user pool for
  authentication](#runtime-a2a-setup-cognito-appendix "#runtime-a2a-setup-cognito-appendix")
* [Remote testing with A2A
  inspector](#runtime-a2a-remote-testing "#runtime-a2a-remote-testing")
* [Troubleshooting](#runtime-a2a-troubleshooting "#runtime-a2a-troubleshooting")

### Set up Cognito user pool for authentication

For detailed Cognito setup instructions, see Set up
[Cognito user pool for authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html#set-up-cognito-user-pool-for-authentication "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html#set-up-cognito-user-pool-for-authentication")
in the MCP documentation.

### Remote testing with A2A inspector

See [https://github.com/a2aproject/a2a-inspector](https://github.com/a2aproject/a2a-inspector "https://github.com/a2aproject/a2a-inspector").

### Troubleshooting

###### Common A2A-specific issues

The following are common issues you might encounter:

Port conflicts
:   A2A servers must run on port 9000 in the AgentCore Runtime environment

JSON-RPC errors
:   Check that your client is sending properly formatted JSON-RPC 2.0
    messages

Authorization method mismatch
:   Make sure your request uses the same authentication method (OAuth or
    SigV4) that the agent was configured with

###### Exception handling

A2A specifications for Error handling: [https://a2a-protocol.org/latest/specification/#81-standard-json-rpc-errors](https://a2a-protocol.org/latest/specification/#81-standard-json-rpc-errors "https://a2a-protocol.org/latest/specification/#81-standard-json-rpc-errors")

A2A servers return errors as standard JSON-RPC error responses with HTTP 200
status codes. Internal Runtime errors are automatically translated to JSON-RPC
internal errors to maintain protocol compliance.

The service now provides proper A2A-compliant error responses with standardized
JSON-RPC error codes:

JSON-RPC Error Codes

| JSON-RPC Error Code | Runtime Exception | HTTP Error Code | JSON-RPC Error Message |
| --- | --- | --- | --- |
| N/A | `AccessDeniedException` | 403 | N/A |
| -32501 | `ResourceNotFoundException` | 404 | Resource not found – Requested resource does not exist |
| -32502 | `ValidationException` | 400 | Validation error – Invalid request data |
| -32503 | `ThrottlingException` | 429 | Rate limit exceeded – Too many requests |
| -32503 | `ServiceQuotaExceededException` | 429 | Rate limit exceeded – Too many requests |
| -32504 | `ResourceConflictException` | 409 | Resource conflict – Resource already exists |
| -32505 | `RuntimeClientError` | 424 | Runtime client error – Check your CloudWatch logs for more information. |
