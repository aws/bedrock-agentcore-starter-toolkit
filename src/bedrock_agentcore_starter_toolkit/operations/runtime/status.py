"""Status operations for Bedrock AgentCore SDK."""

from pathlib import Path
from typing import Optional

from ...services.runtime import BedrockAgentCoreClient
from ...utils.runtime.config import load_config
from .models import StatusConfigInfo, StatusResult


def get_status(config_path: Path, agent_name: Optional[str] = None) -> StatusResult:
    """Get Bedrock AgentCore status including config and runtime details.

    Args:
        config_path: Path to BedrockAgentCore configuration file
        agent_name: Name of agent to get status for (for project configurations)

    Returns:
        StatusResult with config, agent, and endpoint status

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If Bedrock AgentCore is not deployed or configuration is invalid
    """
    # Load project configuration
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent_name)

    # Build config info
    config_info = StatusConfigInfo(
        name=agent_config.name,
        entrypoint=agent_config.entrypoint,
        region=agent_config.aws.region,
        account=agent_config.aws.account,
        execution_role=agent_config.aws.execution_role,
        ecr_repository=agent_config.aws.ecr_repository,
        agent_id=agent_config.bedrock_agentcore.agent_id,
        agent_arn=agent_config.bedrock_agentcore.agent_arn,
    )

    # Initialize status result
    agent_details = None
    endpoint_details = None

    # If agent is deployed, get runtime status
    if agent_config.bedrock_agentcore.agent_id and agent_config.aws.region:
        try:
            client = BedrockAgentCoreClient(agent_config.aws.region)

            # Get agent runtime details
            try:
                agent_details = client.get_agent_runtime(agent_config.bedrock_agentcore.agent_id)
            except Exception as e:
                agent_details = {"error": str(e)}

            # Get endpoint details
            try:
                endpoint_details = client.get_agent_runtime_endpoint(agent_config.bedrock_agentcore.agent_id)
            except Exception as e:
                endpoint_details = {"error": str(e)}

        except Exception as e:
            agent_details = {"error": f"Failed to initialize Bedrock AgentCore client: {e}"}
            endpoint_details = {"error": f"Failed to initialize Bedrock AgentCore client: {e}"}

    return StatusResult(config=config_info, agent=agent_details, endpoint=endpoint_details)
