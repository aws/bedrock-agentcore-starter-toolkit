"""Utilities for agentcore identity."""

import logging
from pathlib import Path
from typing import Dict, Optional

from .schema import BedrockAgentCoreAgentSchema

log = logging.getLogger(__name__)


def _parse_env_file(env_file_path: Path) -> Dict[str, str]:
    """Parse a .env file and return a dictionary of environment variables.

    Args:
        env_file_path: Path to the .env file

    Returns:
        Dictionary of environment variable names to values
    """
    env_vars = {}

    try:
        with env_file_path.open("r") as f:
            for line in f:
                # Strip whitespace
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=VALUE format
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]

                    env_vars[key] = value

    except Exception as e:
        log.warning("Error parsing .env file: %s", e)

    return env_vars


def _load_api_key_from_env_if_configured(
    agent_config: BedrockAgentCoreAgentSchema,
    project_dir: Path,
) -> Optional[str]:
    """Load API key from .env file if api_key_env_var_name is configured.

    This function checks if the agent is configured to use API key-based authentication
    (e.g., OpenAI) and loads the appropriate environment variable from .env file.

    IMPORTANT: Does NOT add the API key to env_vars dict for security reasons.
    The API key should only be stored in AgentCore Identity service.

    Args:
        agent_config: Agent configuration containing api_key_env_var_name
        project_dir: Path to the project directory containing .env file

    Returns:
        The API key value if found, None otherwise
    """
    # Only process if API key authentication is configured
    if not agent_config.api_key_env_var_name:
        return None

    env_var_name = agent_config.api_key_env_var_name

    # Look for .env file in project directory
    env_file = project_dir / ".env"

    if not env_file.exists():
        log.warning(
            "API key authentication configured (%s) but .env file not found at %s\n"
            "   Please create a .env file with: %s=your_api_key",
            env_var_name,
            env_file,
            env_var_name,
        )
        return None

    # Parse .env file and get the specific variable
    log.info("Loading API key from .env file: %s", env_file)
    parsed_env = _parse_env_file(env_file)

    api_key = parsed_env.get(env_var_name)

    if api_key:
        log.info("Loaded %s from .env file", env_var_name)
        return api_key
    else:
        log.warning(
            "️ .env file found but %s is not set\n   Please add: %s=your_api_key to %s",
            env_var_name,
            env_var_name,
            env_file,
        )
        return None
