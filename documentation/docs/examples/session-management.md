# Session Management

Agent that maintains conversation state using session IDs.

## Handler Code

```python
# handler.py
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.context import RequestContext

app = BedrockAgentCoreApp()

# Simple in-memory session storage (use database in production)
sessions = {}

@app.entrypoint
def chat_handler(payload, context: RequestContext):
    """Handle chat with session management"""
    session_id = context.session_id or "default"
    message = payload.get("message", "")

    # Initialize session if new
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "count": 0
        }

    # Add message to session
    sessions[session_id]["messages"].append(message)
    sessions[session_id]["count"] += 1

    # Generate response
    count = sessions[session_id]["count"]
    return {
        "response": f"Message {count}: You said '{message}'",
        "session_id": session_id,
        "message_count": count
    }

app.run()
```

## Usage

### CLI
```bash
agentcore configure --entrypoint handler.py
agentcore launch

# Start conversation
agentcore invoke '{"message": "Hello"}' --session-id conv1

# Continue conversation
agentcore invoke '{"message": "How are you?"}' --session-id conv1

# Session id is automatically persisted and reused in .bedrock_agentcore.yaml
agentcore invoke '{"message": "Goodbye"}'

# Start a new conversation
agentcore invoke '{"message": "Hello"}' --session-id conv2
```
