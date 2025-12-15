# AgentCore Runtime SDK Overview

The Amazon Bedrock AgentCore Runtime SDK transforms your Python functions into production-ready AI agents with built-in HTTP service wrapper, session management, and complete deployment workflows.

## Quick Start

```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def my_agent(payload):
    return {"result": f"Hello {payload.get('name', 'World')}!"}

if __name__ == "__main__":
    app.run()
```

```bash
# Configure and deploy your agent
agentcore configure --entrypoint my_agent.py --non-interactive
agentcore deploy
agentcore invoke '{"name": "Alice"}'
```

## What is the AgentCore Runtime SDK?

The Runtime SDK is a comprehensive Python framework that bridges the gap between your AI agent code and Amazon Bedrock AgentCore's managed infrastructure. It provides HTTP service wrapper, decorator-based programming, session management, authentication integration, streaming support, WebSocket bi-directional streaming, async task management, and complete local development tools.

## Core Components

**BedrockAgentCoreApp** - HTTP service wrapper with:
- `/invocations` endpoint for agent logic
- `/ping` endpoint for health checks
- `/ws` endpoint for WebSocket connections
- Built-in logging, error handling, and session management


**Key Decorators:**
- `@app.entrypoint` - Define your agent's main logic
- `@app.websocket` - Define WebSocket handler for bi-directional streaming
- `@app.ping` - Custom health checks
- `@app.async_task` - Background processing


## Deployment Modes

### 🚀 Direct Code Deploy Deployment (DEFAULT & RECOMMENDED)
```bash
agentcore configure --entrypoint my_agent.py
agentcore deploy                    # Uses CodeBuild for containers, .zip archive for direct deploy
```
- **Works everywhere** - SageMaker Notebooks, Cloud9, laptops
- **Production-ready** - managed Python runtime environment

### 💻 Local Development
```bash
agentcore deploy --local           # Build and run locally
```
- **Fast iteration** - immediate feedback and debugging

### 🔧 Hybrid Build
```bash
agentcore deploy --local-build     # Build locally, deploy to cloud
```
- **For complex scenarios** - large apps, system dependencies
- **Requires:** Docker for local development
- **Requires:** Docker, Finch, or Podman

## Agent Development Patterns

### Synchronous Agents
```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def simple_agent(payload):
    prompt = payload.get("prompt", "")
    if "weather" in prompt.lower():
        return {"result": "It's sunny today!"}
    return {"result": f"You said: {prompt}"}
```

### Streaming Agents
```python
from strands import Agent
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
async def streaming_agent(payload):
    """Streaming agent with real-time responses"""
    user_message = payload.get("prompt", "Hello")

    # Stream responses as they're generated
    stream = agent.stream_async(user_message)
    async for event in stream:
        if "data" in event:
            yield event["data"]          # Stream data chunks
        elif "message" in event:
            yield event["message"]       # Stream message parts

if __name__ == "__main__":
    app.run()
```

**Key Streaming Features:**
- **Server-Sent Events (SSE)**: Automatic SSE formatting for web clients
- **Error Handling**: Graceful error streaming with error events
- **Generator Support**: Both sync and async generators supported
- **Real-time Processing**: Immediate response chunks as they're available


### WebSocket Bi-Directional Streaming Agents

WebSocket agents enable persistent, bi-directional communication where agents can listen and respond simultaneously while handling interruptions and context changes mid-conversation. This is ideal for voice agents and interactive chat applications.

**Basic WebSocket Agent:**
```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.websocket
async def websocket_handler(websocket, context):
    """Bi-directional WebSocket handler."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()

            # Echo back with session context
            await websocket.send_json({
                "echo": data,
                "session": context.session_id
            })

            # Exit on close command
            if data.get("action") == "close":
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    app.run()
```

**Key WebSocket Characteristics:**
- **Port**: WebSocket agents run on port 8080
- **Path**: WebSocket endpoints are mounted at `/ws`
- **Protocol**: Persistent WebSocket connections for real-time streaming
- **Authentication**: Supports SigV4 headers, SigV4 query parameters, and OAuth 2.0

**Understanding the WebSocket Decorator:**
- `@app.websocket` - Registers handler at the `/ws` path on port 8080
- `websocket` parameter - Starlette WebSocket object for send/receive operations
- `context` parameter - Same `RequestContext` with `session_id` for conversation state

**When to Use WebSocket vs HTTP Streaming:**
| Use Case | Recommended Protocol |
|----------|---------------------|
| Interactive voice agents | WebSocket |
| Chat with interruption support | WebSocket |
| Real-time collaboration | WebSocket |
| Simple request-response | HTTP |
| One-way streaming responses | HTTP SSE |


### Framework Integration
The SDK works seamlessly with popular AI frameworks:

**Strands Integration:**
```python
from strands import Agent
from bedrock_agentcore import BedrockAgentCoreApp

agent = Agent(tools=[your_tools])
app = BedrockAgentCoreApp()

@app.entrypoint
def strands_agent(payload):
    result = agent(payload.get("prompt"))
    return {"result": result.message}
```
**Custom Framework Integration:**
```python
@app.entrypoint
async def custom_framework_agent(payload):
    """Works with any async framework"""
    response = await your_framework.process(payload)

    # Can yield for streaming
    for chunk in response.stream():
        yield {"chunk": chunk}
```

## Session Management

Built-in session handling with automatic creation, 15-minute timeout, and cross-invocation persistence:

```python
from bedrock_agentcore.runtime.context import RequestContext

@app.entrypoint
def session_aware_agent(payload, context: RequestContext):
    """Agent with session awareness"""
    session_id = context.session_id
    user_message = payload.get("prompt")

    # Your session-aware logic here
    return {
        "result": f"Session {session_id}: {user_message}",
        "session_id": session_id
    }
```

```bash
# CLI session management
# Using AgentCore CLI with session management
agentcore invoke '{"prompt": "Hello, remember this conversation"}' --session-id "conversation-123"

agentcore invoke '{"prompt": "What did I say earlier?"}' --session-id "conversation-123"
```


### WebSocket Session Management

For WebSocket connections, session state is maintained throughout the connection lifetime. The `context.session_id` is automatically available in your WebSocket handler:

```python
@app.websocket
async def session_aware_websocket(websocket, context):
    """WebSocket with session awareness"""
    await websocket.accept()

    # Session ID available throughout connection
    session_id = context.session_id

    while True:
        data = await websocket.receive_json()
        await websocket.send_json({
            "response": f"Session {session_id} received: {data}",
            "session_id": session_id
        })
```

**Tip:** Use UUIDs or unique identifiers for session IDs to avoid collisions between different users or conversations.


## Middleware and Request Access

The SDK exposes the underlying Starlette request object via `context.request`, enabling middleware to pass data to handlers.

### Using Middleware

```python
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Add custom data to request state
        request.state.authenticated = True
        request.state.user_id = "user-123"
        return await call_next(request)

app = BedrockAgentCoreApp(
    middleware=[Middleware(AuthMiddleware)]
)

@app.entrypoint
def my_agent(payload, context):
    # Access middleware data via context.request.state
    if not context.request.state.authenticated:
        return {"error": "Unauthorized"}

    user_id = context.request.state.user_id
    return {"result": f"Hello {user_id}!"}
```

### Common Middleware Patterns

**Request Timing:**
```python
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.start_time = time.time()
        return await call_next(request)

@app.entrypoint
def handler(payload, context):
    start = context.request.state.start_time
    # ... your logic
    return {"duration": time.time() - start}
```

**Custom Header Parsing:**
```python
class HeaderParserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.tenant_id = request.headers.get('X-Tenant-ID')
        request.state.api_version = request.headers.get('X-API-Version', 'v1')
        return await call_next(request)
```

This follows standard Starlette middleware patterns, so existing Starlette middleware can be used directly.

## Authentication & Authorization


The SDK integrates with AgentCore's identity services providing automatic AWS credential validation (IAM SigV4) by default or JWT Bearer tokens for OAuth-compatible authentication:

```bash
# Configure JWT authorization using AgentCore CLI
agentcore configure --entrypoint my_agent.py \
  --authorizer-config '{"customJWTAuthorizer": {"discoveryUrl": "https://cognito-idp.region.amazonaws.com/pool/.well-known/openid-configuration", "allowedClients": ["your-client-id"], "allowedScopes": ["your-scope-1 your-scope 2"], "customClaims": [{"inboundTokenClaimName": "newCustomClaimName1","inboundTokenClaimValueType": "STRING_ARRAY","authorizingClaimMatchValue": {"claimMatchValue": {"matchValueStringList": ["INVALID_GROUP_NAME"]},"claimMatchOperator": "CONTAINS_ANY"}}]}}'
```

## Asynchronous Processing

AgentCore Runtime supports asynchronous processing for long-running tasks. Your agent can start background work and immediately respond to users, with automatic health status management.

### Key Features

**Automatic Status Management:**
- Agent status changes to "HealthyBusy" during background processing
- Returns to "Healthy" when tasks complete
- Sessions automatically terminate after 15 minutes of inactivity

**Two Processing Approaches:**

1. **Manual Task Management**
```python
@app.entrypoint
def handler(event):
    task_id = app.add_async_task("data_processing", {"batch": 100})

    def background_work():
        time.sleep(30)
        app.complete_async_task(task_id)

    threading.Thread(target=background_work, daemon=True).start()
    return {"task_id": task_id}
```

2. **Custom Ping Handler**
```python
@app.ping
def custom_status():
    if processing_data or system_busy():
        return PingStatus.HEALTHY_BUSY
    return PingStatus.HEALTHY
```

**Common Use Cases:**
- Data processing that takes minutes or hours
- File uploads and conversions
- External API calls with retries
- Batch operations and reports

See the [Async Processing Guide](async.md) for detailed examples and testing strategies.


## Invoking WebSocket Agents

After deploying a WebSocket agent, you can connect to it programmatically using the `AgentCoreRuntimeClient`. There is currently no CLI support for WebSocket connections.

### Client Connection Methods

The SDK provides three authentication methods for WebSocket connections:

**1. SigV4 Signed Headers (AWS Credentials):**
```python
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
import websockets
import asyncio
import os

async def main():
    runtime_arn = os.getenv('AGENT_ARN')
    if not runtime_arn:
        raise ValueError("AGENT_ARN environment variable is required")

    # Initialize client
    client = AgentCoreRuntimeClient(region="us-west-2")

    # Generate WebSocket connection with SigV4 authentication
    ws_url, headers = client.generate_ws_connection(
        runtime_arn=runtime_arn
    )

    # Connect using any WebSocket library
    async with websockets.connect(ws_url, extra_headers=headers) as ws:
        await ws.send('{"inputText": "Hello!"}')
        response = await ws.recv()
        print(f"Received: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

**2. Presigned URL (Frontend/Browser Compatible):**
```python
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
import os

runtime_arn = os.getenv('AGENT_ARN')
client = AgentCoreRuntimeClient(region="us-west-2")

# Generate presigned URL (max 300 seconds expiry)
presigned_url = client.generate_presigned_url(
    runtime_arn=runtime_arn,
    expires=300  # 5 minutes
)

# Share with frontend - JavaScript: new WebSocket(presigned_url)
print(presigned_url)
```

**3. OAuth Bearer Token:**
```python
from bedrock_agentcore.runtime import AgentCoreRuntimeClient
import websockets
import asyncio
import os

async def main():
    runtime_arn = os.getenv('AGENT_ARN')
    bearer_token = os.getenv('BEARER_TOKEN')

    client = AgentCoreRuntimeClient(region="us-west-2")

    # Generate WebSocket connection with OAuth
    ws_url, headers = client.generate_ws_connection_oauth(
        runtime_arn=runtime_arn,
        bearer_token=bearer_token
    )

    async with websockets.connect(ws_url, extra_headers=headers) as ws:
        await ws.send('{"inputText": "Hello!"}')
        response = await ws.recv()
        print(f"Received: {response}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Testing WebSocket Agents Locally

For local development, test your WebSocket agent with a simple client:

```bash
# Terminal 1: Start your agent
python websocket_echo_agent.py
```

```python
# Terminal 2: Test client
import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:8080/ws"

    async with websockets.connect(uri) as websocket:
        await websocket.send('{"message": "Hello!"}')
        response = await websocket.recv()
        print(f"Received: {response}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
```


## Local Development

### Debug Mode
```python
app = BedrockAgentCoreApp(debug=True)  # Enhanced logging

if __name__ == "__main__":
    app.run()  # Auto-detects Docker vs local
```

### Complete Development Workflow
```bash
# 1. Configure
agentcore configure --entrypoint my_agent.py

# 2. Develop locally
agentcore deploy --local

# 3. Test
agentcore invoke '{"prompt": "Hello"}'
agentcore invoke '{"prompt": "Remember this"}' --session-id "test"

# 4. Deploy to cloud
agentcore deploy

# 5. Monitor
agentcore status
```

## WebSocket Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Port conflicts | WebSocket agents must run on port 8080 |
| Connection upgrade failures | Verify agent handles WebSocket upgrade at `/ws` |
| Authentication mismatch | Ensure client uses same auth method (OAuth or SigV4) as configured |
| Message format errors | Check that client sends properly formatted JSON messages |

### WebSocket Close Codes

| Code | Meaning |
|------|---------|
| 1000 | Normal closure |
| 1001 | Going away (server shutdown) |
| 1002 | Protocol error |
| 1011 | Server error |

### Security Considerations

- **Authentication**: All WebSocket connections require SigV4 or OAuth 2.0
- **Session Isolation**: Each connection runs in isolated execution environments
- **Transport Security**: All connections use WSS (WebSocket Secure) over HTTPS
- **Access Control**: IAM policies control WebSocket connection permissions


The AgentCore Runtime SDK provides everything needed to build, test, and deploy production-ready AI agents with minimal setup and maximum flexibility.
