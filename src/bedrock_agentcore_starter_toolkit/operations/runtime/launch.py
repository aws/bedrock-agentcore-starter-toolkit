"""Launch operation - deploys Bedrock AgentCore locally or to cloud."""

import logging
from pathlib import Path
from typing import Optional

from ...services.ecr import create_ecr_repository, deploy_to_ecr
from ...services.runtime import BedrockAgentCoreClient
from ...utils.runtime.config import load_config, save_config
from ...utils.runtime.container import ContainerRuntime
from .models import LaunchResult

log = logging.getLogger(__name__)


def launch_bedrock_agentcore(
    config_path: Path,
    agent_name: Optional[str] = None,
    local: bool = False,
    push_ecr_only: bool = False,
    env_vars: Optional[dict] = None,
) -> LaunchResult:
    """Launch Bedrock AgentCore locally or to cloud.

    Args:
        config_path: Path to BedrockAgentCore configuration file
        agent_name: Name of agent to launch (for project configurations)
        local: Whether to run locally
        push_ecr_only: Whether to only build and push to ECR without deploying
        env_vars: Environment variables to pass to local container (dict of key-value pairs)

    Returns:
        LaunchResult model with launch details
    """
    # Load project configuration
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent_name)

    # Log which agent is being launched
    mode = "locally" if local else "to ECR only" if push_ecr_only else "to cloud"
    log.info("Launching Bedrock AgentCore agent '%s' %s", agent_config.name, mode)

    # Validate configuration
    errors = agent_config.validate(for_local=local)
    if errors:
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")

    # Initialize container runtime
    runtime = ContainerRuntime(agent_config.container_runtime)

    # Get build context - always use project root (where config and Dockerfile are)
    build_dir = config_path.parent

    bedrock_agentcore_name = agent_config.name
    tag = f"bedrock_agentcore-{bedrock_agentcore_name}:latest"

    # Step 1: Build Docker image
    success, output = runtime.build(build_dir, tag)
    if not success:
        error_lines = output[-10:] if len(output) > 10 else output
        raise RuntimeError(f"Build failed: {' '.join(error_lines)}")

    log.info("Docker image built: %s", tag)

    if local:
        # Return info for local deployment
        return LaunchResult(
            mode="local",
            tag=tag,
            port=8080,
            runtime=runtime,
            env_vars=env_vars,
        )

    # Step 2: Push to ECR
    log.info("Uploading to ECR...")

    region = agent_config.aws.region
    if not region:
        raise ValueError("Region not found in configuration")

    # Handle ECR repository
    ecr_uri = agent_config.aws.ecr_repository
    if not ecr_uri and agent_config.aws.ecr_auto_create:
        repo_name = f"bedrock_agentcore-{bedrock_agentcore_name}"
        ecr_uri = create_ecr_repository(repo_name, region)

        # Update the config
        agent_config.aws.ecr_repository = ecr_uri
        agent_config.aws.ecr_auto_create = False

        # Update the project config and save
        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)

    if not ecr_uri:
        raise ValueError("ECR repository not configured and auto-create not enabled")

    # Deploy to ECR
    repo_name = ecr_uri.split("/")[-1]
    deploy_to_ecr(tag, repo_name, region, runtime)

    log.info("Image uploaded to ECR: %s", ecr_uri)

    # If push_ecr_only, return early
    if push_ecr_only:
        return LaunchResult(
            mode="push-ecr",
            tag=tag,
            ecr_uri=ecr_uri,
            build_output=output,
        )

    # Step 3: Deploy agent
    log.info("Creating/updating agent...")

    bedrock_agentcore_client = BedrockAgentCoreClient(region)

    # Transform network configuration to AWS API format
    network_config = agent_config.aws.network_configuration.to_aws_dict()
    protocol_config = agent_config.aws.protocol_configuration.to_aws_dict()

    if not agent_config.aws.execution_role:
        raise ValueError("Execution role not configured")

    agent_info = bedrock_agentcore_client.create_or_update_agent(
        agent_id=agent_config.bedrock_agentcore.agent_id,
        agent_name=bedrock_agentcore_name,
        image_uri=f"{ecr_uri}:latest",
        execution_role_arn=agent_config.aws.execution_role,
        network_config=network_config,
        authorizer_config=agent_config.get_authorizer_configuration(),
        protocol_config=protocol_config,
        env_vars=env_vars,
    )

    # Save deployment info
    agent_id = agent_info["id"]
    agent_arn = agent_info["arn"]

    # Update the config
    agent_config.bedrock_agentcore.agent_id = agent_id
    agent_config.bedrock_agentcore.agent_arn = agent_arn

    # Update the project config and save
    project_config.agents[agent_config.name] = agent_config
    save_config(project_config, config_path)

    log.info("Agent created/updated: %s", agent_arn)

    # Step 4: Wait for agent to be ready
    log.info("Polling for endpoint to be ready...")
    result = bedrock_agentcore_client.wait_for_agent_endpoint_ready(agent_id)
    log.info("Agent endpoint: %s", result)

    return LaunchResult(
        mode="cloud",
        tag=tag,
        agent_arn=agent_arn,
        agent_id=agent_id,
        ecr_uri=ecr_uri,
        build_output=output,
    )
