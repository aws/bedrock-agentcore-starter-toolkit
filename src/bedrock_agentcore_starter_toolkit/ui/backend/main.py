"""
FastAPI backend server for AgentCore UI.

This server provides REST API endpoints for the frontend to interact with
AgentCore agents and memory resources. It also serves the built frontend
assets in production mode.

To run the server:
    cd ui && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import traceback

from bedrock_agentcore_starter_toolkit.services.runtime import generate_session_id

from .models import (
    AgentConfigResponse,
    InvokeRequest,
    InvokeResponse,
    MemoryResourceResponse,
    NewSessionResponse,
)
from .services.config_service import ConfigService
from .services.invoke_service import InvokeService
from .services.memory_service import MemoryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AgentCore UI Backend", version="0.1.0")

# Configure CORS for local development
# Allow all localhost origins to support dynamic ports
cors_origins = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

# Add the current server port from environment if available
server_port = os.getenv("UVICORN_PORT", "8001")
cors_origins.extend(
    [
        f"http://localhost:{server_port}",
        f"http://127.0.0.1:{server_port}",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine the path to the frontend build directory
FRONTEND_BUILD_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# Global state
config_service: Optional[ConfigService] = None
invoke_service: Optional[InvokeService] = None
memory_service: Optional[MemoryService] = None
current_session_id: Optional[str] = None
local_mode: bool = False
mock_mode: bool = False
mock_service = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global config_service, invoke_service, memory_service, current_session_id, local_mode, mock_mode, mock_service

    # Read configuration from environment variables
    config_path_str = os.getenv("AGENTCORE_CONFIG_PATH")
    local_mode_str = os.getenv("AGENTCORE_LOCAL_MODE", "false")
    mock_mode_str = os.getenv("AGENTCORE_MOCK_MODE", "false")
    agent_name = os.getenv("AGENTCORE_AGENT_NAME")

    local_mode = local_mode_str.lower() == "true"
    mock_mode = mock_mode_str.lower() == "true"

    # If mock mode is enabled, use mock service
    if mock_mode:
        from .mock_mode import MockAgentService

        mock_service = MockAgentService()
        logger.info("🎭 Mock mode enabled - using simulated agent responses")
        current_session_id = mock_service.session_id
        return

    # Use provided config path or default
    if config_path_str:
        config_path = Path(config_path_str)
    else:
        config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    logger.info(f"Loading configuration from: {config_path}")
    logger.info(f"Local mode: {local_mode}")
    if agent_name:
        logger.info(f"Agent name: {agent_name}")

    config_service = ConfigService(config_path, agent_name=agent_name)
    invoke_service = InvokeService(
        config_path, agent_name=agent_name, local_mode=local_mode
    )

    # Initialize memory service if region is available
    region = config_service.get_region() if config_service.is_configured() else None
    if region:
        memory_service = MemoryService(region=region)

    current_session_id = generate_session_id()
    logger.info(f"Backend started with session ID: {current_session_id}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/config", response_model=AgentConfigResponse)
async def get_config():
    """Get current agent configuration.

    Returns:
        AgentConfigResponse with current configuration
    """
    global config_service, current_session_id, local_mode, mock_mode, mock_service

    # If mock mode is enabled, return mock config
    if mock_mode and mock_service:
        config = mock_service.get_config()
        return AgentConfigResponse(**config)

    if not config_service or not config_service.is_configured():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CONFIG_NOT_FOUND",
                "message": "No configuration file found. Please create a project_config.yaml file.",
            },
        )

    agent_name = config_service.get_agent_name()
    agent_arn = config_service.get_agent_arn()
    region = config_service.get_region()
    memory_id = config_service.get_memory_id()
    has_oauth = config_service.has_oauth_config()

    # Determine mode and auth method
    mode = "local" if local_mode else "remote"
    if local_mode:
        auth_method = "none"
    elif has_oauth:
        auth_method = "oauth"
    else:
        auth_method = "iam"

    return AgentConfigResponse(
        mode=mode,
        agent_name=agent_name or "unknown",
        agent_arn=agent_arn,
        region=region,
        session_id=current_session_id,
        auth_method=auth_method,
        memory_id=memory_id,
    )


@app.post("/api/invoke", response_model=InvokeResponse)
async def invoke_agent(request: InvokeRequest):
    """Invoke the agent with a message.

    Args:
        request: InvokeRequest with message and session_id

    Returns:
        InvokeResponse with agent response, session_id, and timestamp
    """
    global invoke_service, mock_mode, mock_service

    # If mock mode is enabled, use mock service
    if mock_mode and mock_service:
        try:
            # Parse the message to get the prompt
            message_data = json.loads(request.message)
            prompt = message_data.get("prompt", request.message)
        except (json.JSONDecodeError, AttributeError):
            prompt = request.message

        result = mock_service.invoke(prompt, request.session_id)
        return InvokeResponse(
            response=result["response"],
            session_id=result["session_id"],
            timestamp=result["timestamp"],
        )

    if not invoke_service:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICE_NOT_INITIALIZED",
                "message": "Invoke service not initialized",
            },
        )

    try:
        result = invoke_service.invoke(
            message=request.message,
            session_id=request.session_id,
            bearer_token=request.bearer_token,
            user_id=request.user_id,
        )
        if result["response"] != {}:
            content = result["response"]
            if isinstance(content, dict) and "response" in content:
                content = content["response"]
            if isinstance(content, list):
                if len(content) == 1:
                    content = content[0]
                else:
                    # Handle mix of strings and bytes
                    string_items = []
                    for item in content:
                        if isinstance(item, bytes):
                            string_items.append(item.decode("utf-8", errors="replace"))
                        else:
                            string_items.append(str(item))
                    content = "".join(string_items)
            # Parse JSON string if needed (handles escape sequences)
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "response" in parsed:
                        content = parsed["response"]
                    elif isinstance(parsed, str):
                        content = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
        return InvokeResponse(
            response=content,
            session_id=result["session_id"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"Error invoking agent: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INVOCATION_FAILED",
                "message": f"Failed to invoke agent: {str(e)}",
            },
        )


@app.post("/api/session/new", response_model=NewSessionResponse)
async def create_new_session():
    """Create a new session ID.

    Returns:
        NewSessionResponse with new session_id
    """
    global invoke_service, current_session_id, mock_mode, mock_service

    # If mock mode is enabled, use mock service
    if mock_mode and mock_service:
        result = mock_service.create_new_session()
        current_session_id = result["session_id"]
        logger.info(f"Created new mock session: {current_session_id}")
        return NewSessionResponse(session_id=current_session_id)

    if not invoke_service:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICE_NOT_INITIALIZED",
                "message": "Invoke service not initialized",
            },
        )

    try:
        new_session_id = invoke_service.generate_new_session_id()
        current_session_id = new_session_id
        logger.info(f"Created new session: {new_session_id}")

        return NewSessionResponse(session_id=new_session_id)

    except Exception as e:
        logger.error(f"Error creating new session: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SESSION_CREATION_FAILED",
                "message": f"Failed to create new session: {str(e)}",
            },
        )


@app.get("/api/memory", response_model=MemoryResourceResponse)
async def get_memory():
    """Get memory resource details.

    Returns:
        MemoryResourceResponse with memory details and strategies
    """
    global config_service, memory_service, mock_mode, mock_service

    # If mock mode is enabled, return mock memory
    if mock_mode and mock_service:
        memory_data = mock_service.get_memory()
        if memory_data:
            return MemoryResourceResponse(**memory_data)
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "MEMORY_NOT_CONFIGURED",
                    "message": "Memory is not configured for this mock agent",
                },
            )

    if not config_service or not config_service.is_configured():
        raise HTTPException(
            status_code=404,
            detail={
                "code": "CONFIG_NOT_FOUND",
                "message": "No configuration file found",
            },
        )

    # Get memory ID from configuration
    memory_id = config_service.get_memory_id()
    if not memory_id:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "MEMORY_NOT_CONFIGURED",
                "message": "Memory is not configured for this agent",
            },
        )

    if not memory_service:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SERVICE_NOT_INITIALIZED",
                "message": "Memory service not initialized",
            },
        )

    try:
        memory_details = memory_service.get_memory_details(memory_id)

        return MemoryResourceResponse(
            memory_id=memory_details["memory_id"],
            name=memory_details["name"],
            status=memory_details["status"],
            event_expiry_days=memory_details["event_expiry_days"],
            memory_type=memory_details["memory_type"],
            strategies=memory_details["strategies"],
        )

    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "MEMORY_RETRIEVAL_FAILED",
                "message": f"Failed to retrieve memory details: {traceback.format_exc()}",
            },
        )


# Mount static files for production build
if FRONTEND_BUILD_DIR.exists():
    # Mount static assets (JS, CSS, images, etc.)
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_BUILD_DIR / "assets"),
        name="static",
    )

    # SPA fallback - serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes.

        This enables client-side routing to work properly.
        """
        # Don't serve index.html for API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Check if the requested file exists in the build directory (e.g., vite.svg, favicon, etc.)
        requested_file = FRONTEND_BUILD_DIR / full_path
        if requested_file.is_file():
            return FileResponse(requested_file)

        # Serve index.html for all other routes (SPA routing)
        index_file = FRONTEND_BUILD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        else:
            raise HTTPException(
                status_code=500,
                detail="Frontend build not found. Please run 'npm run build' in ui/frontend/",
            )

else:
    logger.warning(
        f"Frontend build directory not found at {FRONTEND_BUILD_DIR}. "
        "Static file serving disabled. Run 'npm run build' in ui/frontend/ to build the frontend."
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)
