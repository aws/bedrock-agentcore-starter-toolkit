# Async Processing

This example demonstrates how to use Bedrock AgentCore's `@async_task` decorator for automatic health status management.

## Overview

Bedrock AgentCore provides automatic ping status management based on running async tasks:

- **Automatic Health Reporting**: Ping status automatically reflects system busyness
- **Simple Integration**: Just use the `@async_task` decorator
- **Zero Configuration**: Status tracking works out of the box

## Key Concepts

- `Healthy`: System ready for new work
- `HealthyBusy`: System busy with async tasks

## Simple Agent Example

```python
#!/usr/bin/env python3
"""
Simple agent demonstrating @async_task decorator usage.
"""

import asyncio
from datetime import datetime

from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

# Long-running task that automatically affects ping status
@app.async_task
async def process_data(data_id: str):
    """Process data asynchronously - status becomes 'HealthyBusy' during execution."""
    print(f"[{datetime.now()}] Processing data: {data_id}")

    # Simulate processing work
    await asyncio.sleep(30)  # Long-running task

    print(f"[{datetime.now()}] Completed processing: {data_id}")
    return f"Processed {data_id}"

# Another background task
@app.async_task
async def cleanup_task():
    """Cleanup task that also affects ping status."""
    print(f"[{datetime.now()}] Starting cleanup...")
    await asyncio.sleep(10)
    print(f"[{datetime.now()}] Cleanup completed")
    return "Cleanup done"

@app.entrypoint
async def handler(event):
    """Main handler - starts async tasks."""
    action = event.get("action", "info")

    if action == "process":
        data_id = event.get("data_id", "default_data")
        # Start the async task (status will become HealthyBusy)
        await process_data(data_id)
        return {"message": f"Processing {data_id}", "status": "completed"}

    elif action == "cleanup":
        # Start cleanup task
        await cleanup_task()
        return {"message": "Cleanup completed"}

    elif action == "status":
        # Get current status
        task_info = app.get_async_task_info()
        current_status = app.get_current_ping_status()

        return {
            "ping_status": current_status.value,
            "active_tasks": task_info["active_count"],
            "running_jobs": task_info["running_jobs"]
        }

    else:
        return {
            "message": "Simple BedrockAgentCore Agent",
            "available_actions": ["process", "cleanup", "status"],
            "usage": "Send {'action': 'process', 'data_id': 'my_data'}"
        }

if __name__ == "__main__":
    print("Starting simple BedrockAgentCore agent...")
    print("The agent will automatically report 'HealthyBusy' when processing tasks")
    app.run()
```

## How It Works

1. **Decorate async functions** with `@app.async_task`
2. **Call the functions** normally in your handler
3. **Status updates automatically**:
   - `Healthy` when no tasks are running
   - `HealthyBusy` when any `@async_task` function is executing

## Usage Examples

```bash
# Check current ping status
curl http://localhost:8080/ping

# Start processing (status will become HealthyBusy)
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"action": "process", "data_id": "sample_data"}'

# Check status while processing
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"action": "status"}'

# Run cleanup task
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"action": "cleanup"}'
```

## Key Benefits

1. **Automatic Status Tracking**: No manual ping status management needed
2. **Cost Control**: Status automatically prevents new work assignment when busy
3. **Simple to Use**: Just add `@async_task` decorator to long-running functions
4. **Error Handling**: Status correctly updates even if tasks fail

This simple pattern provides automatic health monitoring for your BedrockAgentCore applications without any additional configuration.
