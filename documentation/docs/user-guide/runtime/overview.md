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
agentcore configure --entrypoint my_agent.py
agentcore launch
agentcore invoke '{"name": "Alice"}'
```

## What is the AgentCore Runtime SDK?

The Runtime SDK is a comprehensive Python framework that bridges the gap between your AI agent code and Amazon Bedrock AgentCore's managed infrastructure. It provides HTTP service wrapper, decorator-based programming, session management, authentication integration, streaming support, async task management, and complete local development tools.

## Core Components

**BedrockAgentCoreApp** - HTTP service wrapper with:
- `/invocations` endpoint for agent logic
- `/ping` endpoint for health checks
- Built-in logging, error handling, and session management

**Key Decorators:**
- `@app.entrypoint` - Define your agent's main logic
- `@app.ping` - Custom health checks
- `@app.async_task` - Background processing

## Deployment Modes

### 🚀 Cloud Build (RECOMMENDED)
```bash
agentcore configure --entrypoint my_agent.py
agentcore launch                    # Uses CodeBuild - no Docker needed
```
- **No Docker required** - builds in the cloud
- **Production-ready** - standardized ARM64 containers
- **Works everywhere** - SageMaker Notebooks, Cloud9, laptops

### 💻 Local Development
```bash
agentcore launch --local           # Build and run locally
```
- **Fast iteration** - immediate feedback and debugging
- **Requires:** Docker, Finch, or Podman

### 🔧 Hybrid Build
```bash
agentcore launch --local-build     # Build locally, deploy to cloud
```
- **Custom builds** with cloud deployment
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

## Authentication & Authorization


The SDK integrates with AgentCore's identity services providing automatic AWS credential validation (IAM SigV4) by default or JWT Bearer tokens for OAuth-compatible authentication:

```bash
# Configure JWT authorization using AgentCore CLI
agentcore configure --entrypoint my_agent.py \
  --authorizer-config '{"customJWTAuthorizer": {"discoveryUrl": "https://cognito-idp.region.amazonaws.com/pool/.well-known/openid-configuration", "allowedClients": ["your-client-id"]}}'
```

## Asynchronous Processing

AgentCore Runtime supports asynchronous processing for long-running tasks. Your agent can start background work and immediately respond to users, with automatic health status management.

### Key Features

**Automatic Status Management:**
- Agent status changes to "HealthyBusy" during background processing
- Returns to "Healthy" when tasks complete
- Sessions automatically terminate after 15 minutes of inactivity

**Three Processing Approaches:**

1. **Async Task Decorator (Recommended)**
```python
@app.async_task
async def background_work():
    await process_data()  # Status becomes "HealthyBusy"
    return "done"

@app.entrypoint
async def handler(event):
    asyncio.create_task(background_work())
    return {"status": "started"}
```

2. **Manual Task Management**
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

3. **Custom Ping Handler**
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
agentcore launch --local

# 3. Test
agentcore invoke '{"prompt": "Hello"}'
agentcore invoke '{"prompt": "Remember this"}' --session-id "test"

# 4. Deploy to cloud
agentcore launch

# 5. Monitor
agentcore status
```

The AgentCore Runtime SDK provides everything needed to build, test, and deploy production-ready AI agents with minimal setup and maximum flexibility.
