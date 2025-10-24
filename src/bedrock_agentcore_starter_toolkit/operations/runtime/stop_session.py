"""Stop session operation - terminates active runtime sessions."""

import logging
from pathlib import Path
from typing import Optional

from botocore.exceptions import ClientError

from ...services.runtime import BedrockAgentCoreClient
from ...utils.runtime.config import load_config, save_config
from ...utils.runtime.schema import BedrockAgentCoreAgentSchema, BedrockAgentCoreConfigSchema
from .models import StopSessionResult

log = logging.getLogger(__name__)


def stop_runtime_session(
    config_path: Path,
    session_id: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> StopSessionResult:
    """Stop an active runtime session.

    Args:
        config_path: Path to BedrockAgentCore configuration file
        session_id: Session ID to stop (if None, uses tracked session from config)
        agent_name: Name of agent (for project configurations)

    Returns:
        StopSessionResult with operation details

    Raises:
        ValueError: If no session ID provided or found, or agent not deployed
        FileNotFoundError: If configuration file doesn't exist
    """
    # Load project configuration
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent_name)

    log.info("Stopping session for agent: %s", agent_config.name)

    # Check if agent is deployed
    if not agent_config.bedrock_agentcore.agent_arn:
        raise ValueError(
            f"Agent '{agent_config.name}' is not deployed. Run 'agentcore launch' to deploy the agent first."
        )

    # Determine session ID to stop
    target_session_id = session_id
    if not target_session_id:
        # Try to use tracked session from config
        target_session_id = agent_config.bedrock_agentcore.agent_session_id
        if not target_session_id:
            raise ValueError(
                "No active session found. Please provide --session-id or invoke the agent first to create a session."
            )
        log.info("Using tracked session ID from config: %s", target_session_id)
    else:
        log.info("Using provided session ID: %s", target_session_id)

    region = agent_config.aws.region
    agent_arn = agent_config.bedrock_agentcore.agent_arn

    # Stop the session
    client = BedrockAgentCoreClient(region)

    try:
        response = client.stop_runtime_session(
            agent_arn=agent_arn,
            session_id=target_session_id,
        )

        status_code = response.get("statusCode", 200)

        # Success case
        log.info("Session stopped successfully: %s", target_session_id)

        # Clear the session ID from config if it matches
        if agent_config.bedrock_agentcore.agent_session_id == target_session_id:
            _clear_session_from_config(agent_config, project_config, config_path)

        return StopSessionResult(
            session_id=target_session_id,
            agent_name=agent_config.name,
            status_code=status_code,
            message="Session stopped successfully",
        )

    except ClientError as e:
        # Case 2: Error propagated as ClientError (defense in depth)
        error_code = e.response.get("Error", {}).get("Code", "")
        error_message = e.response.get("Error", {}).get("Message", "")
        status_code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 500)

        if error_code in ["ResourceNotFoundException", "NotFound"]:
            log.warning("Session not found (may have already been terminated): %s", target_session_id)

            # Still clear from config if it matches
            if agent_config.bedrock_agentcore.agent_session_id == target_session_id:
                _clear_session_from_config(agent_config, project_config, config_path)

            return StopSessionResult(
                session_id=target_session_id,
                agent_name=agent_config.name,
                status_code=404,
                message="Session not found (may have already been terminated)",
            )
        else:
            # Re-raise other client errors
            log.error("Failed to stop session %s: %s - %s", target_session_id, error_code, error_message)
            raise


def _clear_session_from_config(
    agent_config: BedrockAgentCoreAgentSchema,
    project_config: BedrockAgentCoreConfigSchema,
    config_path: Path,
) -> None:
    """Clear session ID from agent configuration."""
    agent_config.bedrock_agentcore.agent_session_id = None
    project_config.agents[agent_config.name] = agent_config
    save_config(project_config, config_path)
    log.info("Cleared session ID from configuration")
