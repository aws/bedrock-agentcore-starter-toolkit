"""Get agent card operation - retrieves A2A agent card from deployed agent."""

import logging
from pathlib import Path
from typing import Optional

from ...services.runtime import BedrockAgentCoreClient
from ...utils.runtime.config import load_config
from .models import GetAgentCardResult

log = logging.getLogger(__name__)


def get_agent_card(
    config_path: Path,
    agent_name: Optional[str] = None,
    bearer_token: Optional[str] = None,
) -> GetAgentCardResult:
    """Retrieve agent card from deployed A2A agent.

    Args:
        config_path: Path to configuration file
        agent_name: Name of agent (optional, uses default if not provided)
        bearer_token: OAuth bearer token for authentication (if agent uses OAuth)

    Returns:
        GetAgentCardResult with agent card JSON

    Raises:
        ValueError: If agent not configured or not deployed
        RuntimeError: If GetAgentCard API call fails
    """
    # Load configuration
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent_name)

    log.debug("Retrieving agent card for agent: %s", agent_config.name)

    # Check if agent is deployed
    if not agent_config.bedrock_agentcore or not agent_config.bedrock_agentcore.agent_arn:
        raise ValueError(f"Agent '{agent_config.name}' is not deployed. Run 'agentcore launch' first.")

    agent_arn = agent_config.bedrock_agentcore.agent_arn
    region = agent_config.aws.region

    if not region:
        raise ValueError("Region not found in configuration")

    # Determine if we need OAuth or SigV4
    if bearer_token:
        # Use HTTP client with bearer token
        from ...services.runtime import HttpBedrockAgentCoreClient

        client = HttpBedrockAgentCoreClient(region)

        try:
            agent_card = client.get_agent_card(
                agent_arn=agent_arn,
                bearer_token=bearer_token,
            )
        except Exception as e:
            log.error("Failed to get agent card with OAuth: %s", e)
            raise RuntimeError(f"GetAgentCard failed: {e}") from e
    else:
        # Use SigV4 client
        client = BedrockAgentCoreClient(region)

        try:
            agent_card = client.get_agent_card(agent_arn=agent_arn)
        except Exception as e:
            log.error("Failed to get agent card with SigV4: %s", e)
            raise RuntimeError(f"GetAgentCard failed: {e}") from e

    return GetAgentCardResult(
        agent_card=agent_card,
        agent_name=agent_config.name,
    )
