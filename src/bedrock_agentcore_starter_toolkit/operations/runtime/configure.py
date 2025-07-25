"""Configure operation - creates BedrockAgentCore configuration and Dockerfile."""

import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ...services.ecr import get_account_id, get_region
from ...utils.runtime.config import merge_agent_config, save_config
from ...utils.runtime.container import ContainerRuntime
from ...utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
    ProtocolConfiguration,
)
from .models import ConfigureResult

log = logging.getLogger(__name__)


def configure_bedrock_agentcore(
    agent_name: str,
    entrypoint_path: Path,
    execution_role: Optional[str] = None,
    ecr_repository: Optional[str] = None,
    container_runtime: Optional[str] = None,
    auto_create_ecr: bool = True,
    auto_create_execution_role: bool = True,
    enable_observability: bool = True,
    requirements_file: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    region: Optional[str] = None,
    protocol: Optional[str] = None,
) -> ConfigureResult:
    """Configure Bedrock AgentCore application with deployment settings.

    Args:
        agent_name: name of the agent,
        entrypoint_path: Path to the entrypoint file
        execution_role: AWS execution role ARN or name (auto-created if not provided)
        ecr_repository: ECR repository URI
        container_runtime: Container runtime to use
        auto_create_ecr: Whether to auto-create ECR repository
        auto_create_execution_role: Whether to auto-create execution role if not provided
        enable_observability: Whether to enable observability
        requirements_file: Path to requirements file
        authorizer_configuration: JWT authorizer configuration dictionary
        verbose: Whether to provide verbose output during configuration
        region: AWS region for deployment
        protocol: agent server protocol, must be either HTTP or MCP

    Returns:
        ConfigureResult model with configuration details
    """
    # Set logging level based on verbose flag
    if verbose:
        log.setLevel(logging.DEBUG)
        log.debug("Verbose mode enabled")
    else:
        log.setLevel(logging.INFO)
    # Log agent name at the start of configuration
    log.info("Configuring BedrockAgentCore agent: %s", agent_name)
    build_dir = Path.cwd()

    if verbose:
        log.debug("Build directory: %s", build_dir)
        log.debug("Bedrock AgentCore name: %s", agent_name)
        log.debug("Entrypoint path: %s", entrypoint_path)

    # Get AWS info
    if verbose:
        log.debug("Retrieving AWS account information...")
    account_id = get_account_id()
    region = region or get_region()

    if verbose:
        log.debug("AWS account ID: %s", account_id)
        log.debug("AWS region: %s", region)

    # Initialize container runtime
    if verbose:
        log.debug("Initializing container runtime with: %s", container_runtime or "default")
    runtime = ContainerRuntime(container_runtime)

    # Handle execution role - convert to ARN if provided, otherwise use auto-create setting
    execution_role_arn = None
    execution_role_auto_create = auto_create_execution_role

    if execution_role:
        # User provided a role - convert to ARN format if needed
        if execution_role.startswith("arn:aws:iam::"):
            execution_role_arn = execution_role
        else:
            execution_role_arn = f"arn:aws:iam::{account_id}:role/{execution_role}"

        if verbose:
            log.debug("Using execution role: %s", execution_role_arn)
    else:
        # No role provided - use auto_create_execution_role parameter
        if verbose:
            if execution_role_auto_create:
                log.debug("Execution role will be auto-created during launch")
            else:
                log.debug("No execution role provided and auto-create disabled")

    # Generate Dockerfile and .dockerignore
    bedrock_agentcore_name = None
    # Try to find the variable name for the Bedrock AgentCore instance in the file
    if verbose:
        log.debug("Attempting to find Bedrock AgentCore instance name in %s", entrypoint_path)

    if verbose:
        log.debug("Generating Dockerfile with parameters:")
        log.debug("  Entrypoint: %s", entrypoint_path)
        log.debug("  Build directory: %s", build_dir)
        log.debug("  Bedrock AgentCore name: %s", bedrock_agentcore_name or "bedrock_agentcore")
        log.debug("  Region: %s", region)
        log.debug("  Enable observability: %s", enable_observability)
        log.debug("  Requirements file: %s", requirements_file)

    dockerfile_path = runtime.generate_dockerfile(
        entrypoint_path,
        build_dir,
        bedrock_agentcore_name or "bedrock_agentcore",
        region,
        enable_observability,
        requirements_file,
    )

    # Check if .dockerignore was created
    dockerignore_path = build_dir / ".dockerignore"

    log.info("Generated Dockerfile: %s", dockerfile_path)
    if dockerignore_path.exists():
        log.info("Generated .dockerignore: %s", dockerignore_path)

    # Handle project configuration (named agents)
    config_path = build_dir / ".bedrock_agentcore.yaml"

    if verbose:
        log.debug("Agent name from BedrockAgentCoreApp: %s", agent_name)
        log.debug("Config path: %s", config_path)

    # Convert to POSIX for cross-platform compatibility
    entrypoint_path_str = entrypoint_path.as_posix()

    # Determine entrypoint format
    if bedrock_agentcore_name:
        entrypoint = f"{entrypoint_path_str}:{bedrock_agentcore_name}"
    else:
        entrypoint = entrypoint_path_str

    if verbose:
        log.debug("Using entrypoint format: %s", entrypoint)

    # Create new configuration
    ecr_auto_create_value = bool(auto_create_ecr and not ecr_repository)

    if verbose:
        log.debug("ECR auto-create: %s", ecr_auto_create_value)

    if verbose:
        log.debug("Creating BedrockAgentCoreConfigSchema with following parameters:")
        log.debug("  Name: %s", agent_name)
        log.debug("  Entrypoint: %s", entrypoint)
        log.debug("  Platform: %s", ContainerRuntime.DEFAULT_PLATFORM)
        log.debug("  Container runtime: %s", runtime.runtime)
        log.debug("  Execution role: %s", execution_role_arn)
        ecr_repo_display = ecr_repository if ecr_repository else "Auto-create" if ecr_auto_create_value else "N/A"
        log.debug("  ECR repository: %s", ecr_repo_display)
        log.debug("  Enable observability: %s", enable_observability)

    # Create new agent configuration
    config = BedrockAgentCoreAgentSchema(
        name=agent_name,
        entrypoint=entrypoint,
        platform=ContainerRuntime.DEFAULT_PLATFORM,
        container_runtime=runtime.runtime,
        aws=AWSConfig(
            execution_role=execution_role_arn,
            execution_role_auto_create=execution_role_auto_create,
            account=account_id,
            region=region,
            ecr_repository=ecr_repository,
            ecr_auto_create=ecr_auto_create_value,
            network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
            protocol_configuration=ProtocolConfiguration(server_protocol=protocol or "HTTP"),
            observability=ObservabilityConfig(enabled=enable_observability),
        ),
        bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        authorizer_configuration=authorizer_configuration,
    )

    # Use simplified config merging
    project_config = merge_agent_config(config_path, agent_name, config)
    save_config(project_config, config_path)

    if verbose:
        log.debug("Configuration saved with agent: %s", agent_name)

    return ConfigureResult(
        config_path=config_path,
        dockerfile_path=dockerfile_path,
        dockerignore_path=dockerignore_path if dockerignore_path.exists() else None,
        runtime=runtime.get_name(),
        region=region,
        account_id=account_id,
        execution_role=execution_role_arn,
        ecr_repository=ecr_repository,
        auto_create_ecr=auto_create_ecr and not ecr_repository,
    )


AGENT_NAME_REGEX = r"^[a-zA-Z][a-zA-Z0-9_]{0,47}$"
AGENT_NAME_ERROR = (
    "Invalid agent name. Must start with a letter, contain only letters/numbers/underscores, "
    "and be 1-48 characters long."
)


def validate_agent_name(name: str) -> Tuple[bool, str]:
    """Check if name matches the pattern [a-zA-Z][a-zA-Z0-9_]{0,47}.

    This pattern requires:
    - First character: letter (a-z or A-Z)
    - Remaining 0-47 characters: letters, digits, or underscores
    - Total maximum length: 48 characters

    Args:
        name: The string to validate

    Returns:
        bool: True if the string matches the pattern, False otherwise
    """
    match = bool(re.match(AGENT_NAME_REGEX, name))

    if match:
        return match, ""
    else:
        return match, AGENT_NAME_ERROR
