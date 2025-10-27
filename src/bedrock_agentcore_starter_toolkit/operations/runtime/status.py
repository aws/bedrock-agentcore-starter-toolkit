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

    # ADD NETWORK CONFIGURATION EXTRACTION
    network_mode = agent_config.aws.network_configuration.network_mode
    vpc_id = None

    if network_mode == "VPC" and agent_config.aws.network_configuration.network_mode_config:
        network_config = agent_config.aws.network_configuration.network_mode_config

        # Try to get VPC ID from subnets (best effort - don't fail if can't retrieve)
        try:
            import boto3

            ec2_client = boto3.client("ec2", region_name=agent_config.aws.region)
            subnet_response = ec2_client.describe_subnets(SubnetIds=network_config.subnets[:1])
            if subnet_response["Subnets"]:
                vpc_id = subnet_response["Subnets"][0]["VpcId"]
        except Exception:
            pass  # nosec B110 # Ignore errors - VPC ID is nice-to-have

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
        network_mode=agent_config.aws.network_configuration.network_mode,
        network_subnets=agent_config.aws.network_configuration.network_mode_config.subnets
        if agent_config.aws.network_configuration.network_mode_config
        else None,
        network_security_groups=agent_config.aws.network_configuration.network_mode_config.security_groups
        if agent_config.aws.network_configuration.network_mode_config
        else None,
        network_vpc_id=vpc_id,
    )

    if agent_config.aws.lifecycle_configuration.has_custom_settings:
        config_info.idle_timeout = agent_config.aws.lifecycle_configuration.idle_runtime_session_timeout
        config_info.max_lifetime = agent_config.aws.lifecycle_configuration.max_lifetime

    # Check if memory is disabled first
    if agent_config.memory and agent_config.memory.mode == "NO_MEMORY":
        config_info.memory_type = "Disabled"
        config_info.memory_enabled = False
    elif agent_config.memory and agent_config.memory.memory_id:
        try:
            from ...operations.memory.manager import MemoryManager

            memory_manager = MemoryManager(region_name=agent_config.aws.region)

            # Get full memory details
            memory_status = memory_manager.get_memory_status(agent_config.memory.memory_id)
            memory = memory_manager.get_memory(agent_config.memory.memory_id)
            strategies = memory_manager.get_memory_strategies(agent_config.memory.memory_id)

            # Build detailed memory info
            memory_details = {
                "id": memory.get("id"),
                "name": memory.get("name"),
                "status": memory_status,
                "description": memory.get("description"),
                "event_expiry_days": memory.get("eventExpiryDuration"),
                "created_at": memory.get("createdAt"),
                "updated_at": memory.get("updatedAt"),
                "strategies": [],
            }

            # Get strategy details
            for strategy in strategies:
                strategy_info = {
                    "id": strategy.get("strategyId"),
                    "name": strategy.get("name"),
                    "type": strategy.get("type"),
                    "status": strategy.get("status"),
                    "namespaces": strategy.get("namespaces", []),
                }
                memory_details["strategies"].append(strategy_info)

            # Set the status info fields
            if memory_status == "ACTIVE":
                if strategies and len(strategies) > 0:
                    config_info.memory_type = f"STM+LTM ({len(strategies)} strategies)"
                else:
                    config_info.memory_type = "STM only"
                config_info.memory_enabled = True
            elif memory_status in ["CREATING", "UPDATING"]:
                if agent_config.memory.has_ltm:
                    config_info.memory_type = "STM+LTM (provisioning...)"
                else:
                    config_info.memory_type = "STM (provisioning...)"
                config_info.memory_enabled = False
            else:
                config_info.memory_type = f"Error ({memory_status})"
                config_info.memory_enabled = False

            config_info.memory_id = agent_config.memory.memory_id
            config_info.memory_status = memory_status
            config_info.memory_details = memory_details

        except Exception as e:
            config_info.memory_type = f"Error checking: {str(e)}"
            config_info.memory_enabled = False

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
