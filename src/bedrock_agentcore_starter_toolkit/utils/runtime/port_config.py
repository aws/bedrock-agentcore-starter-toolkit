"""Port configuration utilities for Bedrock AgentCore."""

import os


def get_local_port() -> int:
    """Get the local port from environment variable or default to 8080.
    
    Returns:
        int: The port number to use for local runtime
    """
    port_str = os.getenv("AGENTCORE_RUNTIME_LOCAL_PORT", "8080")
    try:
        port = int(port_str)
        if port < 1 or port > 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {port}")
        return port
    except ValueError as e:
        raise ValueError(f"Invalid port value in AGENTCORE_RUNTIME_LOCAL_PORT: {port_str}") from e