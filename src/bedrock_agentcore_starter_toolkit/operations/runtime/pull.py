"""Pull operation - pulls agent configuration from deployed AgentCore runtime."""

import logging
import re
from pathlib import Path
from typing import Optional

from ...services.runtime import BedrockAgentCoreClient
from ...utils.runtime.config import save_config
from ...utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    LifecycleConfiguration,
    NetworkConfiguration,
    NetworkModeConfig,
    ProtocolConfiguration,
)
from .models import PullResult

log = logging.getLogger(__name__)


def pull_agent(
    region: str,
    agent_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    output_path: Optional[Path] = None,
    force: bool = False,
) -> PullResult:
    """Pull agent configuration from deployed AgentCore runtime.

    Args:
        region: AWS region where the agent is deployed
        agent_name: Agent name to pull (mutually exclusive with agent_id)
        agent_id: Agent ID to pull (mutually exclusive with agent_name)
        output_path: Output path for configuration file (default: .bedrock_agentcore.yaml)
        force: Overwrite existing configuration file

    Returns:
        PullResult with pulled configuration details

    Raises:
        ValueError: If agent not found or invalid arguments
        FileExistsError: If configuration file exists and force is False
    """
    log.info("Starting agent pull from region: %s", region)

    # Set default output path
    if output_path is None:
        output_path = Path.cwd() / ".bedrock_agentcore.yaml"

    # Check if output file already exists
    if output_path.exists() and not force:
        raise FileExistsError(
            f"Configuration file already exists: {output_path}\n"
            f"Use --force to overwrite."
        )

    # Initialize AWS client
    client = BedrockAgentCoreClient(region)

    # Get agent data
    if agent_id:
        log.info("Fetching agent by ID: %s", agent_id)
        agent_data = client.get_agent_runtime(agent_id)
    elif agent_name:
        log.info("Searching for agent by name: %s", agent_name)
        agent_info = client.find_agent_by_name(agent_name)
        if not agent_info:
            raise ValueError(f"Agent '{agent_name}' not found in region {region}")
        agent_data = client.get_agent_runtime(agent_info["agentRuntimeId"])
    else:
        raise ValueError("Either agent_name or agent_id must be provided")

    # Convert API response to config schema
    agent_config, warnings = _convert_to_schema(agent_data, region)

    # Build project config
    project_config = BedrockAgentCoreConfigSchema(
        default_agent=agent_config.name,
        agents={agent_config.name: agent_config},
    )

    # Save configuration file
    save_config(project_config, output_path)
    log.info("Configuration saved to: %s", output_path)

    return PullResult(
        agent_name=agent_config.name,
        agent_id=agent_config.bedrock_agentcore.agent_id,
        config_path=output_path,
        deployment_type=agent_config.deployment_type,
        runtime_type=agent_config.runtime_type,
        network_mode=agent_config.aws.network_configuration.network_mode,
        protocol=agent_config.aws.protocol_configuration.server_protocol,
        region=region,
        env_var_keys=warnings.get("env_var_keys", []),
        has_memory=warnings.get("has_memory", False),
        memory_id=warnings.get("memory_id"),
    )


def list_agents_for_pull(region: str) -> list:
    """List all agents in a region for interactive selection.

    Args:
        region: AWS region to list agents from

    Returns:
        List of agent summaries with id, name, status, and created date
    """
    client = BedrockAgentCoreClient(region)
    agents = client.list_agents()

    return [
        {
            "id": agent.get("agentRuntimeId"),
            "name": agent.get("agentRuntimeName"),
            "status": agent.get("status", "UNKNOWN"),
            "created_at": agent.get("createdAt"),
        }
        for agent in agents
    ]


def _convert_to_schema(agent_data: dict, region: str) -> tuple[BedrockAgentCoreAgentSchema, dict]:
    """Convert API response to BedrockAgentCoreAgentSchema.

    Args:
        agent_data: Response from get_agent_runtime API
        region: AWS region

    Returns:
        Tuple of (agent_config, warnings_dict)
    """
    warnings = {}

    # Extract basic info
    agent_name = agent_data.get("agentRuntimeName", "pulled_agent")
    agent_id = agent_data.get("agentRuntimeId")
    agent_arn = agent_data.get("agentRuntimeArn")
    role_arn = agent_data.get("roleArn")

    # Extract account ID from ARN
    account_id = None
    if agent_arn:
        # ARN format: arn:aws:bedrock-agentcore:region:account:agent-runtime/id
        arn_match = re.match(r"arn:aws:bedrock-agentcore:[^:]+:(\d+):", agent_arn)
        if arn_match:
            account_id = arn_match.group(1)

    # Determine deployment type and runtime from artifact configuration
    artifact = agent_data.get("agentRuntimeArtifact", {})
    deployment_type = "direct_code_deploy"
    runtime_type = None
    ecr_repository = None

    if "codeConfiguration" in artifact:
        deployment_type = "direct_code_deploy"
        code_config = artifact["codeConfiguration"]
        runtime_type = code_config.get("runtime", "PYTHON_3_11")
    elif "containerConfiguration" in artifact:
        deployment_type = "container"
        container_config = artifact["containerConfiguration"]
        container_uri = container_config.get("containerUri", "")
        # Extract ECR repository from URI (remove tag)
        if container_uri:
            ecr_repository = container_uri.split(":")[0] if ":" in container_uri else container_uri

    # Extract network configuration
    network_data = agent_data.get("networkConfiguration", {})
    network_mode = network_data.get("networkMode", "PUBLIC")
    network_mode_config = None

    if network_mode == "VPC":
        mode_config_data = network_data.get("networkModeConfig", {})
        network_mode_config = NetworkModeConfig(
            subnets=mode_config_data.get("subnets", []),
            security_groups=mode_config_data.get("securityGroups", []),
        )

    network_configuration = NetworkConfiguration(
        network_mode=network_mode,
        network_mode_config=network_mode_config,
    )

    # Extract protocol configuration
    protocol_data = agent_data.get("protocolConfiguration", {})
    protocol = protocol_data.get("serverProtocol", "HTTP")
    protocol_configuration = ProtocolConfiguration(server_protocol=protocol)

    # Extract lifecycle configuration
    lifecycle_data = agent_data.get("lifecycleConfiguration", {})
    lifecycle_configuration = LifecycleConfiguration(
        idle_runtime_session_timeout=lifecycle_data.get("idleRuntimeSessionTimeout"),
        max_lifetime=lifecycle_data.get("maxLifetime"),
    )

    # Check for environment variables (warning: values not available)
    env_vars = agent_data.get("environmentVariables", {})
    if env_vars:
        warnings["env_var_keys"] = list(env_vars.keys())
        log.warning("Environment variables detected but values cannot be pulled: %s", list(env_vars.keys()))

    # Check for memory configuration (warning: not pulled)
    memory_config = agent_data.get("memoryConfiguration", {})
    memory_id = memory_config.get("memoryId")
    if memory_id:
        warnings["has_memory"] = True
        warnings["memory_id"] = memory_id
        log.warning("Memory configuration detected but not pulled: %s", memory_id)

    # Build agent config with placeholder entrypoint
    agent_config = BedrockAgentCoreAgentSchema(
        name=agent_name,
        entrypoint="TODO:set_with_configure",  # Must be set by user
        deployment_type=deployment_type,
        runtime_type=runtime_type,
        aws=AWSConfig(
            execution_role=role_arn,
            account=account_id,
            region=region,
            ecr_repository=ecr_repository,
            network_configuration=network_configuration,
            protocol_configuration=protocol_configuration,
            lifecycle_configuration=lifecycle_configuration,
        ),
        bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
            agent_id=agent_id,
            agent_arn=agent_arn,
        ),
    )

    return agent_config, warnings
