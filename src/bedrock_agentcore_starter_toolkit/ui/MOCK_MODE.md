# Mock Mode for UI Testing

Mock mode allows you to test the AgentCore UI without needing a real agent configuration or AWS credentials.

## Features

- **Simulated Agent Responses**: Returns random mock responses to test the chat interface
- **Session Management**: Creates and manages mock session IDs
- **Memory Simulation**: Provides mock memory resource information
- **No Configuration Required**: Works without `.bedrock_agentcore.yaml` file

## Running Mock Mode

### Option 1: Using the helper script (Recommended)

```bash
cd ui
uv run python run_mock_server.py
```

### Option 2: Using uvicorn directly with uv

```bash
cd ui
export AGENTCORE_MOCK_MODE=true
uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload
```

### Option 3: Using environment variable inline

```bash
cd ui
AGENTCORE_MOCK_MODE=true uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

## Accessing the UI

Once the server is running, open your browser to:

```
http://localhost:8001
```

The UI will automatically use mock mode and you can:

- Send messages and receive simulated responses
- Test the chat interface
- Create new sessions
- View mock memory information
- Test all UI features without a real agent

## Mock Responses

The mock agent provides various types of responses including:

- Simple text responses
- Markdown formatted responses
- Code blocks
- Lists (numbered and bulleted)
- Multi-line content

Responses are randomly selected to provide variety during testing.

## Development Workflow

Mock mode is perfect for:

1. **Frontend Development**: Test UI changes without backend dependencies
2. **UI/UX Testing**: Verify layouts and interactions
3. **Integration Testing**: Test the full stack locally
4. **Demo/Presentation**: Show the UI without live AWS resources

## Disabling Mock Mode

To run with a real agent, simply don't set the `AGENTCORE_MOCK_MODE` environment variable, or set it to `false`:

```bash
cd ui
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Or use the normal launch command:

```bash
agentcore launch --ui
```
