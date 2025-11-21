# AgentCore UI

A modern web interface for interacting with Amazon Bedrock AgentCore agents.

## Features

- **Chat Interface**: Interactive chat with your agent
- **Session Management**: Create and manage conversation sessions
- **Memory Viewer**: View agent memory resources and strategies
- **Configuration Panel**: View agent configuration details
- **Mock Mode**: Test the UI without a real agent (see [MOCK_MODE.md](MOCK_MODE.md))

## Architecture

The UI consists of two main components:

### Frontend (`frontend/`)

- **Framework**: React 19 with TypeScript
- **Styling**: Tailwind CSS
- **Routing**: React Router
- **State Management**: TanStack Query (React Query)
- **Build Tool**: Vite

### Backend (`backend/`)

- **Framework**: FastAPI
- **API**: REST endpoints for agent interaction
- **Static Serving**: Serves built frontend assets in production

## Development

### Prerequisites

- Python 3.10+
- Node.js 18+
- uv (Python package manager)

### Frontend Development

```bash
cd frontend
npm install

# Create .env file for development (optional)
cp .env.example .env
# Edit .env and set VITE_API_BASE_URL=http://localhost:8001

npm run dev
```

The frontend dev server runs at `http://localhost:5173`

**Note**: When running the frontend dev server separately, set `VITE_API_BASE_URL` in a `.env` file to point to your backend server (e.g., `http://localhost:8001`)

### Backend Development

#### With Real Agent

```bash
# From project root
agentcore launch --local --ui
```

#### With Mock Agent (No Configuration Required)

```bash
cd ui
uv run python run_mock_server.py
```

The backend server runs at `http://localhost:8001`

## Production Build

### Build Frontend

```bash
cd frontend
npm run build
```

This creates optimized assets in `frontend/dist/`

### Run Production Server

The backend automatically serves the built frontend:

```bash
cd ui
uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Or use the integrated launch command:

```bash
agentcore launch --ui
```

## Testing

### Test Mock API

```bash
cd ui
uv run python test_mock_api.py
```

### Test Frontend

```bash
cd frontend
npm run lint
```

## Project Structure

```
ui/
├── frontend/               # React frontend
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── pages/         # Page components
│   │   ├── types/         # TypeScript types
│   │   └── utils/         # Utility functions
│   ├── dist/              # Built assets (generated)
│   └── package.json
│
├── backend/               # FastAPI backend
│   ├── services/          # Business logic services
│   ├── models.py          # Pydantic models
│   ├── main.py            # FastAPI app
│   ├── mock_mode.py       # Mock service for testing
│   └── requirements.txt
│
├── run_mock_server.py     # Helper script for mock mode
├── test_mock_api.py       # API test script
├── MOCK_MODE.md           # Mock mode documentation
└── README.md              # This file
```

## API Endpoints

### GET `/api/config`

Get agent configuration

### POST `/api/invoke`

Invoke the agent with a message

### POST `/api/session/new`

Create a new session

### GET `/api/memory`

Get memory resource details

### GET `/health`

Health check endpoint

## Environment Variables

### Backend

- `AGENTCORE_CONFIG_PATH`: Path to agent configuration file
- `AGENTCORE_LOCAL_MODE`: Set to "true" for local mode
- `AGENTCORE_MOCK_MODE`: Set to "true" for mock mode (testing)
- `UVICORN_PORT`: Port the server is running on (for CORS configuration)

### Frontend

- `VITE_API_BASE_URL`: API base URL for development (e.g., `http://localhost:8001`)
  - Leave empty in production (API served from same origin)
  - Set when running frontend dev server separately from backend

## Mock Mode

Mock mode allows you to test the UI without needing a real agent configuration. See [MOCK_MODE.md](MOCK_MODE.md) for details.

## User Guide

For detailed instructions on using the UI, including:

- How to interact with the chat interface
- Inspecting memory resources
- Understanding authentication options
- Session management
- Troubleshooting common issues

See the comprehensive [User Guide](USER_GUIDE.md).

## Troubleshooting

### Frontend won't connect to backend

Make sure CORS is configured correctly in `backend/main.py`. The default allows:

- `http://localhost:5173` (Vite dev server)
- `http://localhost:8001` (Production)

### Backend fails to start

Check that all dependencies are installed:

```bash
cd ui
pip install -r backend/requirements.txt
```

Or use uv:

```bash
cd ui
uv pip install -r backend/requirements.txt
```

### Build fails

Ensure Node.js dependencies are installed:

```bash
cd frontend
npm install
```

For more troubleshooting help, see the [User Guide](USER_GUIDE.md).

## Contributing

When making changes:

1. Update frontend code in `frontend/src/`
2. Test with mock mode: `cd ui && uv run python run_mock_server.py`
3. Build frontend: `cd frontend && npm run build`
4. Test production build: `cd ui && uv run python -m uvicorn backend.main:app`
5. Test with real agent: `agentcore launch --local --ui`
