# Async Processing

This example demonstrates how to use Bedrock AgentCore's manual task management for automatic health status tracking during long-running operations.

## Overview

Bedrock AgentCore provides automatic ping status management based on tracked async tasks:

- **Automatic Health Reporting**: Ping status automatically reflects system busyness
- **Manual Task Tracking**: Use `add_async_task` and `complete_async_task` for explicit control
- **Flexible Integration**: Works with any async pattern (threading, asyncio, etc.)

## Key Concepts

- `Healthy`: System ready for new work
- `HealthyBusy`: System busy with async tasks

## Simple Agent Example

```python
#!/usr/bin/env python3
"""
Simple agent demonstrating manual task management with threading.
"""

import time
import threading
from datetime import datetime

from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

def process_data(data_id: str, task_id: int):
    """Process data synchronously in background thread."""
    print(f"[{datetime.now()}] Processing data: {data_id}")

    # Simulate processing work
    time.sleep(30)  # Long-running task

    print(f"[{datetime.now()}] Completed processing: {data_id}")

    # Mark task as complete
    app.complete_async_task(task_id)
    return f"Processed {data_id}"

def cleanup_task(task_id: int):
    """Cleanup task running in background thread."""
    print(f"[{datetime.now()}] Starting cleanup...")
    time.sleep(10)
    print(f"[{datetime.now()}] Cleanup completed")

    # Mark task as complete
    app.complete_async_task(task_id)
    return "Cleanup done"

@app.entrypoint
def handler(event):
    """Main handler - starts background tasks with manual tracking."""
    action = event.get("action", "info")

    if action == "process":
        data_id = event.get("data_id", "default_data")

        # Start tracking the task (status becomes HealthyBusy)
        task_id = app.add_async_task("data_processing", {"data_id": data_id})

        # Start the task in background thread
        threading.Thread(
            target=process_data,
            args=(data_id, task_id),
            daemon=True
        ).start()

        return {
            "message": f"Started processing {data_id}",
            "task_id": task_id,
            "status": "processing"
        }

    elif action == "cleanup":
        # Start tracking cleanup task
        task_id = app.add_async_task("cleanup", {})

        # Start cleanup in background thread
        threading.Thread(
            target=cleanup_task,
            args=(task_id,),
            daemon=True
        ).start()

        return {
            "message": "Started cleanup",
            "task_id": task_id
        }

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

1. **Register the task** with `app.add_async_task(name, metadata)` - Returns a task_id
2. **Start background work** in a thread, passing the task_id
3. **Complete the task** with `app.complete_async_task(task_id)` when done
4. **Status updates automatically**:
   - `Healthy` when no tracked tasks are running
   - `HealthyBusy` when any tracked tasks are active

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

1. **Automatic Status Tracking**: Ping status updates automatically based on tracked tasks
2. **Cost Control**: Status prevents new work assignment when busy
3. **Flexible Integration**: Works with threading, asyncio, or any background processing
4. **Explicit Control**: You decide when to start and stop tracking tasks
5. **Task Metadata**: Associate custom metadata with each task for debugging

This manual task management pattern provides automatic health monitoring with full control over task lifecycle.
