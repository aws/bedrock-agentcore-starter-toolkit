# Handle Asynchronous and Long Running Agents

AgentCore Runtime can handle asynchronous processing and long running agents. Asynchronous tasks allow your agent to continue processing after responding to the client and handle long-running operations without blocking responses.

With async processing, your agent can:

- Start a task that might take minutes or hours
- Immediately respond to the user saying "I've started working on this"
- Continue processing in the background
- Allow the user to check back later for results

## Key Concepts

### Asynchronous Processing Model

The Amazon Bedrock AgentCore SDK supports both synchronous and asynchronous processing through a unified API. This creates a flexible implementation pattern for both clients and agent developers. Agent clients can work with the same API without differentiating between synchronous and asynchronous on the client side. With the ability to invoke the same session across invocations, agent developers can reuse context and build upon this context incrementally without implementing complex task management logic.

### Runtime Session Lifecycle Management

Agent code communicates its processing status using the "/ping" health status:

- **"Healthy"**: Ready for new work, no background tasks running
- **"HealthyBusy"**: Currently processing background tasks

A session in idle state for 15 minutes gets automatically terminated.

## Three Ways to Manage Async Tasks

### 1. Async Task Decorator (Recommended)

The simplest way to track asynchronous functions. The SDK automatically manages the ping status:

```python
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.async_task
async def background_work():
    await asyncio.sleep(10)  # Status becomes "HealthyBusy"
    return "done"

@app.entrypoint
async def handler(event):
    asyncio.create_task(background_work())
    return {"status": "started"}

if __name__ == "__main__":
    app.run()
```

**How it works:**
- The `@app.async_task` decorator tracks function execution
- When the function runs, ping status changes to "HealthyBusy"
- When the function completes, status returns to "Healthy"

### 2. Manual Task Management

For more control over task tracking, use the API methods directly:

```python
from bedrock_agentcore import BedrockAgentCoreApp
import threading
import time

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(event):
    """Start tracking a task manually"""
    # Start tracking the task
    task_id = app.add_async_task("data_processing", {"batch": 100})

    # Start background work
    def background_work():
        time.sleep(30)  # Simulate work
        app.complete_async_task(task_id)  # Mark as complete

    threading.Thread(target=background_work, daemon=True).start()

    return {"status": "Task started", "task_id": task_id}

if __name__ == "__main__":
    app.run()
```

**API Methods:**
- `app.add_async_task(name, metadata)` - Start tracking a task
- `app.complete_async_task(task_id)` - Mark task as complete
- `app.get_async_task_info()` - Get information about running tasks

### 3. Custom Ping Handler

Override automatic status with custom logic:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.runtime.models import PingStatus

app = BedrockAgentCoreApp()

# Global state to track custom conditions
processing_data = False

@app.ping
def custom_status():
    """Custom ping handler with your own logic"""
    if processing_data or system_busy():
        return PingStatus.HEALTHY_BUSY
    return PingStatus.HEALTHY

@app.entrypoint
def handler(event):
    global processing_data

    if event.get("action") == "start_processing":
        processing_data = True
        # Start your processing...
        return {"status": "Processing started"}

    return {"status": "Ready"}

if __name__ == "__main__":
    app.run()
```

## Complete Example with Strands

Here's a practical example combining async tasks with the Strands AI framework:

```python
import threading
import time
from strands import Agent, tool
from bedrock_agentcore import BedrockAgentCoreApp

# Initialize app with debug mode for task management
app = BedrockAgentCoreApp(debug=True)

@tool
def start_background_task(duration: int = 5) -> str:
    """Start a simple background task that runs for specified duration."""
    # Start tracking the async task
    task_id = app.add_async_task("background_processing", {"duration": duration})

    # Run task in background thread
    def background_work():
        time.sleep(duration)  # Simulate work
        app.complete_async_task(task_id)  # Mark as complete

    threading.Thread(target=background_work, daemon=True).start()
    return f"Started background task (ID: {task_id}) for {duration} seconds. Agent status is now BUSY."

# Create agent with the tool
agent = Agent(tools=[start_background_task])

@app.entrypoint
def main(payload):
    """Main entrypoint - handles user messages."""
    user_message = payload.get("prompt", "Try: start_background_task(3)")
    return {"message": agent(user_message).message}

if __name__ == "__main__":
    print("🚀 Simple Async Strands Example")
    print("Test: curl -X POST http://localhost:8080/invocations -H 'Content-Type: application/json' -d '{\"prompt\": \"start a 3 second task\"}'")
    app.run()
```

This example demonstrates:
- Creating a background task that runs asynchronously
- Tracking the task's status with `add_async_task` and `complete_async_task`
- Responding immediately to the user while processing continues
- Managing the agent's health status automatically

## Ping Status Priority

The ping status is determined in this priority order:

1. **Forced Status** (debug actions like `force_busy`)
2. **Custom Handler** (`@app.ping` decorator)
3. **Automatic** (based on active `@app.async_task` functions)

## Debug and Testing Features

Enable debug mode for additional testing capabilities:

```python
app = BedrockAgentCoreApp(debug=True)
```

**Debug Actions** (via POST with `"_agent_core_app_action"`):
- `"ping_status"` - Check current status
- `"job_status"` - List running tasks
- `"force_busy"` / `"force_healthy"` - Force status
- `"clear_forced_status"` - Clear forced status

**API Methods**:
```python
task_id = app.add_async_task("task_name", metadata={})
success = app.complete_async_task(task_id)
status = app.get_current_ping_status()
info = app.get_async_task_info()
```

## Testing Your Async Agent

### Local Testing with curl

```bash
# Start your agent
python my_async_agent.py

# Test ping endpoint
curl http://localhost:8080/ping

# Start a background task
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "start a background task"}'

# Check if status changed to HealthyBusy
curl http://localhost:8080/ping
```

### Local Testing with AgentCore CLI

```bash
# Configure and test locally
agentcore configure -e my_async_agent.py
agentcore launch -l

# Test in another terminal
agentcore invoke '{"prompt": "start processing"}' -l

# Check status via ping
curl http://localhost:8080/ping
```

## Common Patterns

**Long-Running Processing:**
```python
@tool
def start_data_processing(dataset_size: str = "medium") -> str:
    task_id = app.add_async_task("data_processing", {"size": dataset_size})

    def process_data():
        time.sleep(1800)  # Simulate processing
        app.complete_async_task(task_id)

    threading.Thread(target=process_data, daemon=True).start()
    return f"🚀 Processing started (Task {task_id}). I'll continue in the background!"
```

**Progress Monitoring:**
```python
def save_progress(task_id: int, progress: dict):
    with open(f"task_progress_{task_id}.json", 'w') as f:
        json.dump(progress, f)

@tool
def get_progress(task_id: int = None) -> str:
    # Find and read progress file
    # Return formatted status
    pass
```
