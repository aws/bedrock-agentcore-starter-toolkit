# AgentCore Runtime SDK Overview

The Amazon Bedrock AgentCore Runtime SDK transforms your Python functions into production-ready AI agents that can be deployed, scaled, and managed in the cloud. At its core, the SDK provides `BedrockAgentCoreApp` - a powerful HTTP service wrapper that handles all the complexity of agent deployment while letting you focus on your agent's logic.

## What is the AgentCore Runtime SDK?

The Runtime SDK is a comprehensive Python framework that bridges the gap between your AI agent code and Amazon Bedrock AgentCore's managed infrastructure. It provides HTTP service wrapper, decorator-based programming, session management, authentication integration, streaming support, async task management, and complete local development tools.

## Core SDK Components

### BedrockAgentCoreApp: The Foundation

`BedrockAgentCoreApp` extends Starlette to provide an agent-optimized web server with built-in endpoints:

- **`/invocations`** - Main endpoint for processing agent requests
- **`/ping`** - Health check endpoint with status reporting
- **Built-in logging** - Request tracking with correlation IDs
- **Error handling** - Automatic error formatting and status codes
- **Concurrency control** - Request limiting and thread pool management

```python
from bedrock_agentcore import BedrockAgentCoreApp

# Initialize with optional debug mode
app = BedrockAgentCoreApp(debug=True)
```

### Core Decorators

The SDK uses a decorator-based approach that makes agent development intuitive:

#### @app.entrypoint - Main Agent Function

The fundamental decorator that registers your primary agent logic:

```python
@app.entrypoint
def invoke(payload):
    """Process requests synchronously"""
    user_message = payload.get("prompt", "Hello")
    # Your agent logic here
    return {"result": "Response"}

# Async version for streaming
@app.entrypoint
async def invoke_async(payload):
    """Process requests asynchronously with streaming"""
    user_message = payload.get("prompt", "Hello")
    # Can yield for streaming responses
    yield {"chunk": "Partial response"}
```

#### @app.ping - Custom Health Checks

Override default health status logic:

```python
from bedrock_agentcore.runtime.models import PingStatus

@app.ping
def custom_health():
    """Custom health logic"""
    if system_busy():
        return PingStatus.HEALTHY_BUSY
    return PingStatus.HEALTHY
```

#### @app.async_task - Background Processing

Automatically track long-running operations:

```python
@app.async_task
async def background_processing():
    """Automatically tracked async task"""
    await asyncio.sleep(30)  # Status becomes HEALTHY_BUSY
    return "completed"       # Status returns to HEALTHY
```

## Agent Development Patterns

### Synchronous Agents

Perfect for quick, deterministic responses:

```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def simple_agent(payload):
    """Basic request-response agent"""
    prompt = payload.get("prompt", "")

    # Simple processing logic
    if "weather" in prompt.lower():
        return {"result": "It's sunny today!"}

    return {"result": f"You said: {prompt}"}

if __name__ == "__main__":
    app.run()
```

### Streaming Agents

For real-time, dynamic responses that build over time:

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

### Framework Integration

The SDK works seamlessly with popular AI frameworks:

**Strands Integration:**
```python
from strands import Agent, tool
from bedrock_agentcore import BedrockAgentCoreApp

agent = Agent(tools=[your_tools])
app = BedrockAgentCoreApp()

@app.entrypoint
def strands_agent(payload):
    """Strands-powered agent"""
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

The SDK provides built-in session handling for stateful conversations with automatic session creation and management, 15-minute timeout, cross-invocation context persistence, and complete session isolation for security:

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
# Using AgentCore CLI with session management
agentcore invoke '{"prompt": "Hello, remember this conversation"}' --session-id "conversation-123"
agentcore invoke '{"prompt": "What did I say earlier?"}' --session-id "conversation-123"
```

## Authentication and Authorization

The SDK integrates with AgentCore's identity services providing automatic AWS credential validation (IAM SigV4) by default or JWT Bearer tokens for OAuth-compatible authentication:

```bash
# Configure JWT authorization using AgentCore CLI
agentcore configure --entrypoint my_agent.py \
  --authorizer-config '{"customJWTAuthorizer": {"discoveryUrl": "https://cognito-idp.region.amazonaws.com/pool/.well-known/openid-configuration", "allowedClients": ["your-client-id"]}}'
```

## Asynchronous Processing

For long-running operations, the SDK provides comprehensive async support with automatic task tracking that transitions agent status to HEALTHY_BUSY during processing, or fine-grained manual control:

```python
# Automatic task tracking
@app.async_task
async def long_running_task():
    """Automatically tracked - agent status becomes BUSY"""
    await process_large_dataset()
    return "completed"

@app.entrypoint
async def start_processing(payload):
    """Start background task"""
    asyncio.create_task(long_running_task())
    return {"status": "Processing started in background"}

# Manual task management
@app.entrypoint
def manual_task_control(payload):
    """Manual async task management"""
    task_id = app.add_async_task("data_processing", {"batch_size": 1000})

    def background_work():
        time.sleep(60)
        app.complete_async_task(task_id)

    threading.Thread(target=background_work, daemon=True).start()
    return {"task_id": task_id, "status": "started"}
```

## Local Development

The SDK provides a complete local development environment with debug mode for additional capabilities and comprehensive logging with automatic request correlation:

```python
# Development server with debug mode
app = BedrockAgentCoreApp(debug=True)

if __name__ == "__main__":
    app.run()  # Default port 8080, auto-detects Docker vs local

# Custom logging
import logging
logger = logging.getLogger("my_agent")

@app.entrypoint
def my_agent(payload):
    logger.info("Processing request: %s", payload)
    # Your logic here
```

```bash
# Configure and test locally using AgentCore CLI
agentcore configure --entrypoint my_agent.py --name my-agent
agentcore launch --local
agentcore invoke '{"prompt": "Hello world"}'
agentcore invoke '{"prompt": "Remember this"}' --session-id "test-session"
agentcore invoke '{"prompt": "Hello"}' --bearer-token "your-jwt-token"
```
