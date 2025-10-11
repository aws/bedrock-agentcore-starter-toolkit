"""Configure operation - creates BedrockAgentCore configuration and Dockerfile."""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple

from ...cli.runtime.configuration_manager import ConfigurationManager
from ...services.ecr import get_account_id, get_region
from ...utils.runtime.config import merge_agent_config, save_config
from ...utils.runtime.container import ContainerRuntime
from ...utils.runtime.entrypoint import detect_dependencies
from ...utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreDeploymentInfo,
    CodeBuildConfig,
    MemoryConfig,
    NetworkConfiguration,
    ObservabilityConfig,
    ProtocolConfiguration,
)
from .models import ConfigureResult

log = logging.getLogger(__name__)


def get_relative_path(path: Path, base: Optional[Path] = None) -> str:
    """Convert path to relative format with OS-native separators.

    Args:
        path: Absolute or relative path
        base: Base directory (defaults to current working directory)

    Returns:
        Path relative to base with OS-native separators

    Raises:
        ValueError: If path is empty or invalid
    """
    # Validate input
    if not path or str(path).strip() == "":
        raise ValueError("Path cannot be empty")

    # Ensure path is a Path object
    path_obj = Path(path) if not isinstance(path, Path) else path
    base = base or Path.cwd()

    try:
        rel_path = path_obj.relative_to(base)
        return str(rel_path)
    except ValueError:
        # Path is outside base - keep full path for clarity
        # Don't lose directory structure by showing just the filename
        return str(path_obj)


def detect_entrypoint(source_path: Path) -> Optional[Path]:
    """Detect entrypoint file in source directory.

    Args:
        source_path: Directory to search for entrypoint

    Returns:
        Path to detected entrypoint file, or None if not found
    """
    ENTRYPOINT_CANDIDATES = ["agent.py", "app.py", "main.py", "__main__.py"]

    source_dir = Path(source_path)
    for candidate in ENTRYPOINT_CANDIDATES:
        candidate_path = source_dir / candidate
        if candidate_path.exists():
            log.debug("Detected entrypoint: %s", candidate_path)
            return candidate_path

    log.debug("No entrypoint found in %s", source_path)
    return None


def detect_requirements(source_path: Path):
    """Detect requirements file in the source directory.

    Args:
        source_path: Source directory (where entrypoint is located)

    Returns:
        DependencyInfo object with detection results
    """
    # Resolve to absolute path for consistent behavior
    source_path_resolved = Path(source_path).resolve()
    log.debug("Checking for requirements in source directory: %s", source_path_resolved)

    deps = detect_dependencies(source_path_resolved)
    if deps.found:
        log.debug("Found requirements in source directory: %s", deps.resolved_path)
    else:
        log.debug("No requirements file found in source directory: %s", source_path_resolved)

    return deps


def infer_agent_name(entrypoint_path: Path, base: Optional[Path] = None) -> str:
    """Infer agent name from entrypoint path.

    Args:
        entrypoint_path: Path to agent entrypoint file
        base: Base directory for relative path (defaults to cwd)

    Returns:
        Suggested agent name (e.g., 'agents_writer_main' from 'agents/writer/main.py')
    """
    rel_entrypoint = get_relative_path(entrypoint_path, base)

    # Remove .py extension if present (only at the end)
    if rel_entrypoint.endswith(".py"):
        rel_entrypoint = rel_entrypoint[:-3]

    # Replace spaces and OS path separators with underscores
    suggested_name = rel_entrypoint.replace(" ", "_").replace(os.sep, "_")

    log.debug("Inferred agent name: %s from %s", suggested_name, get_relative_path(entrypoint_path, base))
    return suggested_name


def configure_bedrock_agentcore(
    agent_name: str,
    entrypoint_path: Path,
    execution_role: Optional[str] = None,
    code_build_execution_role: Optional[str] = None,
    ecr_repository: Optional[str] = None,
    container_runtime: Optional[str] = None,
    auto_create_ecr: bool = True,
    auto_create_execution_role: bool = True,
    enable_observability: bool = True,
    memory_mode: Literal["NO_MEMORY", "STM_ONLY", "STM_AND_LTM"] = "STM_ONLY",
    requirements_file: Optional[str] = None,
    authorizer_configuration: Optional[Dict[str, Any]] = None,
    request_header_configuration: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    region: Optional[str] = None,
    protocol: Optional[str] = None,
    non_interactive: bool = False,
    source_path: Optional[str] = None,
) -> ConfigureResult:
    """Configure Bedrock AgentCore application with deployment settings.

    Args:
        agent_name: name of the agent,
        entrypoint_path: Path to the entrypoint file
        execution_role: AWS execution role ARN or name (auto-created if not provided)
        code_build_execution_role: CodeBuild execution role ARN or name (uses execution_role if not provided)
        ecr_repository: ECR repository URI
        container_runtime: Container runtime to use
        auto_create_ecr: Whether to auto-create ECR repository
        auto_create_execution_role: Whether to auto-create execution role if not provided
        enable_observability: Whether to enable observability
        memory_mode: Memory configuration mode - "NO_MEMORY", "STM_ONLY" (default), or "STM_AND_LTM"
        requirements_file: Path to requirements file
        authorizer_configuration: JWT authorizer configuration dictionary
        request_header_configuration: Request header configuration dictionary
        verbose: Whether to provide verbose output during configuration
        region: AWS region for deployment
        protocol: agent server protocol, must be either HTTP or MCP or A2A
        non_interactive: Skip interactive prompts and use defaults
        source_path: Optional path to agent source code directory

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

    # Build directory is always project root for module validation and dependency detection
    build_dir = Path.cwd()

    if verbose:
        log.debug("Build directory: %s", build_dir)
        log.debug("Source path: %s", source_path or "None (using build directory)")
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

    # Pass region to ConfigurationManager so it can check for existing memories
    config_manager = ConfigurationManager(build_dir / ".bedrock_agentcore.yaml", non_interactive)

    # Handle memory configuration
    memory_config = MemoryConfig()

    # Check if memory is explicitly disabled FIRST (works in both interactive and non-interactive modes)
    if memory_mode == "NO_MEMORY":
        memory_config.mode = "NO_MEMORY"
        log.info("Memory disabled")
    elif non_interactive:
        # Non-interactive mode: use explicit memory_mode parameter
        memory_config.mode = memory_mode
        memory_config.event_expiry_days = 30
        memory_config.memory_name = f"{agent_name}_memory"
        log.info("Will create new memory with mode: %s", memory_mode)

        if memory_mode == "STM_AND_LTM":
            log.info("Memory configuration: Short-term + Long-term memory enabled")
        else:  # STM_ONLY
            log.info("Memory configuration: Short-term memory only")
    else:
        # Interactive mode: prompt user (only if memory not explicitly disabled)
        action, value = config_manager.prompt_memory_selection()

        if action == "USE_EXISTING":
            # Using existing memory - just store the ID
            memory_config.memory_id = value
            memory_config.mode = "STM_AND_LTM"  # Assume existing has strategies
            memory_config.memory_name = f"{agent_name}_memory"
            log.info("Using existing memory resource: %s", value)
        elif action == "CREATE_NEW":
            # Create new with specified mode
            memory_config.mode = value
            memory_config.event_expiry_days = 30
            memory_config.memory_name = f"{agent_name}_memory"
            log.info("Will create new memory with mode: %s", value)

            if value == "STM_AND_LTM":
                log.info("Memory configuration: Short-term + Long-term memory enabled")
            else:  # STM_ONLY
                log.info("Memory configuration: Short-term memory only")
        elif action == "SKIP":
            # User chose to skip memory setup
            memory_config.mode = "NO_MEMORY"
            log.info("Memory disabled by user choice")

    # Check for existing memory configuration from previous launch
    config_path = build_dir / ".bedrock_agentcore.yaml"
    memory_id = None
    memory_name = None

    if config_path.exists():
        try:
            from ...utils.runtime.config import load_config

            existing_config = load_config(config_path)
            existing_agent = existing_config.get_agent_config(agent_name)
            if existing_agent and existing_agent.memory and existing_agent.memory.memory_id:
                memory_id = existing_agent.memory.memory_id
                memory_name = existing_agent.memory.memory_name
                log.info("Found existing memory ID from previous launch: %s", memory_id)
        except Exception as e:
            log.debug("Unable to read existing memory configuration: %s", e)

    # Handle CodeBuild execution role - use separate role if provided, otherwise use execution_role
    codebuild_execution_role_arn = None
    if code_build_execution_role:
        # User provided a separate CodeBuild role
        if code_build_execution_role.startswith("arn:aws:iam::"):
            codebuild_execution_role_arn = code_build_execution_role
        else:
            codebuild_execution_role_arn = f"arn:aws:iam::{account_id}:role/{code_build_execution_role}"

        if verbose:
            log.debug("Using separate CodeBuild execution role: %s", codebuild_execution_role_arn)
    else:
        # No separate CodeBuild role provided - use None
        codebuild_execution_role_arn = None

        if verbose and execution_role_arn:
            log.debug("Using same role for CodeBuild: %s", codebuild_execution_role_arn)

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
        if memory_id:
            log.debug("  Memory ID: %s", memory_id)

    # Determine output directory for Dockerfile based on source_path
    # If source_path provided: write to .bedrock_agentcore/{agent_name}/ directly
    # Otherwise: write to project root (legacy)
    if source_path:
        from ...utils.runtime.config import get_agentcore_directory

        dockerfile_output_dir = get_agentcore_directory(Path.cwd(), agent_name, source_path)
    else:
        dockerfile_output_dir = build_dir

    # Generate Dockerfile in the correct location (no moving needed)
    dockerfile_path = runtime.generate_dockerfile(
        entrypoint_path,
        dockerfile_output_dir,
        bedrock_agentcore_name or "bedrock_agentcore",
        region,
        enable_observability,
        requirements_file,
        memory_id,
        memory_name,
        source_path,
        protocol,
    )
    # Log with relative path for better readability
    rel_dockerfile_path = get_relative_path(Path(dockerfile_path))
    log.info("Generated Dockerfile: %s", rel_dockerfile_path)

    # Ensure .dockerignore exists at Docker build context location
    if source_path:
        # For source_path: .dockerignore at source directory (Docker build context)
        source_dockerignore = Path(source_path) / ".dockerignore"
        if not source_dockerignore.exists():
            template_path = (
                Path(__file__).parent.parent.parent / "utils" / "runtime" / "templates" / "dockerignore.template"
            )
            if template_path.exists():
                source_dockerignore.write_text(template_path.read_text())
                log.info("Generated .dockerignore: %s", source_dockerignore)
        dockerignore_path = source_dockerignore
    else:
        # Legacy: .dockerignore at project root
        dockerignore_path = build_dir / ".dockerignore"
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
        log.debug("  Request header configuration: %s", request_header_configuration)

    # Create new agent configuration
    config = BedrockAgentCoreAgentSchema(
        name=agent_name,
        entrypoint=entrypoint,
        platform=ContainerRuntime.DEFAULT_PLATFORM,
        container_runtime=runtime.runtime,
        source_path=str(Path(source_path).resolve()) if source_path else None,
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
        codebuild=CodeBuildConfig(
            execution_role=codebuild_execution_role_arn,
        ),
        authorizer_configuration=authorizer_configuration,
        request_header_configuration=request_header_configuration,
        memory=memory_config,
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
