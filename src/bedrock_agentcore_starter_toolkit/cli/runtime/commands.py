"""Bedrock AgentCore CLI - Command line interface for Bedrock AgentCore."""

import json
import logging
import os
from pathlib import Path
from threading import Thread
from typing import List, Optional

import typer
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from rich.panel import Panel
from rich.syntax import Syntax

from ...operations.identity.oauth2_callback_server import start_oauth2_callback_server
from ...operations.runtime import (
    configure_bedrock_agentcore,
    destroy_bedrock_agentcore,
    detect_entrypoint,
    detect_requirements,
    get_relative_path,
    get_status,
    infer_agent_name,
    invoke_bedrock_agentcore,
    launch_bedrock_agentcore,
    validate_agent_name,
)
from ...utils.runtime.config import load_config
from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands, get_genai_observability_url
from ..common import _handle_error, _print_success, console
from .configuration_manager import ConfigurationManager

# Create a module-specific logger
logger = logging.getLogger(__name__)


def _show_configuration_not_found_panel():
    """Show standardized configuration not found panel."""
    console.print(
        Panel(
            "⚠️ [yellow]Configuration Not Found[/yellow]\n\n"
            "No agent configuration found in this directory.\n\n"
            "[bold]Get Started:[/bold]\n"
            "   [cyan]agentcore configure --entrypoint your_agent.py[/cyan]\n"
            "   [cyan]agentcore launch[/cyan]\n"
            '   [cyan]agentcore invoke \'{"prompt": "Hello"}\'[/cyan]',
            title="⚠️ Setup Required",
            border_style="bright_blue",
        )
    )


def _validate_requirements_file(file_path: str) -> str:
    """Validate requirements file and return the absolute path."""
    from ...utils.runtime.entrypoint import validate_requirements_file

    try:
        deps = validate_requirements_file(Path.cwd(), file_path)
        rel_path = get_relative_path(Path(deps.resolved_path))
        _print_success(f"Using requirements file: [dim]{rel_path}[/dim]")
        # Return absolute path for consistency with entrypoint handling
        return str(Path(deps.resolved_path).resolve())
    except (FileNotFoundError, ValueError) as e:
        _handle_error(str(e), e)


def _prompt_for_requirements_file(prompt_text: str, source_path: str, default: str = "") -> Optional[str]:
    """Prompt user for requirements file path with validation.

    Args:
        prompt_text: Prompt message to display
        source_path: Source directory path for validation
        default: Default path to pre-populate
    """
    # Pre-populate with relative source directory path if no default provided
    if not default:
        rel_source = get_relative_path(Path(source_path))
        default = f"{rel_source}/"

    # Use PathCompleter without filter - allow navigation anywhere
    response = prompt(prompt_text, completer=PathCompleter(), complete_while_typing=True, default=default)

    if response.strip():
        # Validate file exists and is within project boundaries
        req_file = Path(response.strip()).resolve()
        project_root = Path.cwd().resolve()

        # Check if requirements file is within project root (allows shared requirements)
        try:
            if not req_file.is_relative_to(project_root):
                console.print("[red]Error: Requirements file must be within project directory[/red]")
                return _prompt_for_requirements_file(prompt_text, source_path, default)
        except (ValueError, AttributeError):
            # is_relative_to not available or other error - skip validation
            pass

        return _validate_requirements_file(response.strip())

    return None


def _handle_requirements_file_display(
    requirements_file: Optional[str], non_interactive: bool = False, source_path: Optional[str] = None
) -> Optional[str]:
    """Handle requirements file with display logic for CLI.

    Args:
        requirements_file: Explicit requirements file path
        non_interactive: Whether to skip interactive prompts
        source_path: Optional source code directory
    """
    if requirements_file:
        # User provided file - validate and show confirmation
        return _validate_requirements_file(requirements_file)

    # Use operations layer for detection - source_path is always provided
    deps = detect_requirements(Path(source_path))

    if non_interactive:
        # Auto-detection for non-interactive mode
        if deps.found:
            rel_deps_path = get_relative_path(Path(deps.resolved_path))
            _print_success(f"Using detected requirements file: [cyan]{rel_deps_path}[/cyan]")
            return None  # Use detected file
        else:
            _handle_error("No requirements file specified and none found automatically")

    # Auto-detection with interactive prompt
    if deps.found:
        rel_deps_path = get_relative_path(Path(deps.resolved_path))

        console.print(f"\n🔍 [cyan]Detected dependency file:[/cyan] [bold]{rel_deps_path}[/bold]")
        console.print("[dim]Press Enter to use this file, or type a different path (use Tab for autocomplete):[/dim]")

        result = _prompt_for_requirements_file(
            "Path or Press Enter to use detected dependency file: ", source_path=source_path, default=rel_deps_path
        )

        if result is None:
            # Use detected file
            _print_success(f"Using detected requirements file: [cyan]{rel_deps_path}[/cyan]")

        return result
    else:
        console.print("\n[yellow]⚠️  No dependency file found (requirements.txt or pyproject.toml)[/yellow]")
        console.print("[dim]Enter path to requirements file (use Tab for autocomplete), or press Enter to skip:[/dim]")

        result = _prompt_for_requirements_file("Path: ", source_path=source_path)

        if result is None:
            _handle_error("No requirements file specified and none found automatically")

        return result


def _detect_entrypoint_in_source(source_path: str, non_interactive: bool = False) -> str:
    """Detect entrypoint file in source directory with CLI display."""
    source_dir = Path(source_path)

    # Use operations layer for detection
    detected = detect_entrypoint(source_dir)

    if len(detected) == 0:
        # No files found - error
        rel_source = get_relative_path(source_dir)
        _handle_error(
            f"No entrypoint file found in {rel_source}\n"
            f"Expected one of: main.py, agent.py, app.py, __main__.py\n"
            f"Please specify full file path (e.g., {rel_source}/your_agent.py)"
        )
    elif len(detected) > 1:
        # Multiple files found - error with list
        rel_source = get_relative_path(source_dir)
        files_list = ", ".join(f.name for f in detected)
        _handle_error(
            f"Multiple entrypoint files found in {rel_source}: {files_list}\n"
            f"Please specify full file path (e.g., {rel_source}/main.py)"
        )

    # Exactly one file - show detection and confirm
    rel_entrypoint = get_relative_path(detected[0])

    _print_success(f"Using entrypoint file: [cyan]{rel_entrypoint}[/cyan]")
    return str(detected[0])


# Define options at module level to avoid B008
ENV_OPTION = typer.Option(None, "--env", "-env", help="Environment variables for local mode (format: KEY=VALUE)")

# Configure command group
configure_app = typer.Typer(name="configure", help="Configuration management")


@configure_app.command("list")
def list_agents():
    """List configured agents."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    try:
        project_config = load_config(config_path)
        if not project_config.agents:
            console.print("[yellow]No agents configured.[/yellow]")
            return

        console.print("[bold]Configured Agents:[/bold]")
        for name, agent in project_config.agents.items():
            default_marker = " (default)" if name == project_config.default_agent else ""
            status_icon = "✅" if agent.bedrock_agentcore.agent_arn else "⚠️"
            status_text = "Ready" if agent.bedrock_agentcore.agent_arn else "Config only"

            console.print(f"  {status_icon} [cyan]{name}[/cyan]{default_marker} - {status_text}")
            console.print(f"     Entrypoint: {agent.entrypoint}")
            console.print(f"     Region: {agent.aws.region}")
            console.print()
    except FileNotFoundError:
        console.print("[red].bedrock_agentcore.yaml not found.[/red]")


@configure_app.command("set-default")
def set_default(name: str = typer.Argument(...)):
    """Set default agent."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    try:
        from ...utils.runtime.config import load_config, save_config

        project_config = load_config(config_path)
        if name not in project_config.agents:
            available = list(project_config.agents.keys())
            _handle_error(f"Agent '{name}' not found. Available: {available}")

        project_config.default_agent = name
        save_config(project_config, config_path)
        _print_success(f"Set '{name}' as default")
    except Exception as e:
        _handle_error(f"Failed: {e}")


@configure_app.callback(invoke_without_command=True)
def configure(
    ctx: typer.Context,
    entrypoint: Optional[str] = typer.Option(
        None,
        "--entrypoint",
        "-e",
        help="Entry point: file path (e.g., agent.py) or directory path (auto-detects main.py, agent.py, app.py)",
    ),
    agent_name: Optional[str] = typer.Option(None, "--name", "-n"),
    execution_role: Optional[str] = typer.Option(None, "--execution-role", "-er"),
    code_build_execution_role: Optional[str] = typer.Option(None, "--code-build-execution-role", "-cber"),
    ecr_repository: Optional[str] = typer.Option(None, "--ecr", "-ecr"),
    s3_bucket: Optional[str] = typer.Option(None, "--s3", "-s3", help="S3 bucket for direct_code_deploy deployment"),
    container_runtime: Optional[str] = typer.Option(None, "--container-runtime", "-ctr"),
    requirements_file: Optional[str] = typer.Option(
        None, "--requirements-file", "-rf", help="Path to requirements file"
    ),
    disable_otel: bool = typer.Option(False, "--disable-otel", "-do", help="Disable OpenTelemetry"),
    disable_memory: bool = typer.Option(False, "--disable-memory", "-dm", help="Disable memory"),
    authorizer_config: Optional[str] = typer.Option(
        None, "--authorizer-config", "-ac", help="OAuth authorizer configuration as JSON string"
    ),
    request_header_allowlist: Optional[str] = typer.Option(
        None,
        "--request-header-allowlist",
        "-rha",
        help="Comma-separated list of allowed request headers "
        "(Authorization or X-Amzn-Bedrock-AgentCore-Runtime-Custom-*)",
    ),
    vpc: bool = typer.Option(
        False, "--vpc", help="Enable VPC networking mode (requires --subnets and --security-groups)"
    ),
    subnets: Optional[str] = typer.Option(
        None,
        "--subnets",
        help="Comma-separated list of subnet IDs (e.g., subnet-abc123,subnet-def456). Required with --vpc.",
    ),
    security_groups: Optional[str] = typer.Option(
        None,
        "--security-groups",
        help="Comma-separated list of security group IDs (e.g., sg-xyz789). Required with --vpc.",
    ),
    idle_timeout: Optional[int] = typer.Option(
        None,
        "--idle-timeout",
        help="Idle runtime session timeout in seconds (60-28800, default: 900)",
        min=60,
        max=28800,
    ),
    max_lifetime: Optional[int] = typer.Option(
        None,
        "--max-lifetime",
        help="Maximum instance lifetime in seconds (60-28800, default: 28800)",
        min=60,
        max=28800,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    region: Optional[str] = typer.Option(None, "--region", "-r"),
    protocol: Optional[str] = typer.Option(None, "--protocol", "-p", help="Server protocol (HTTP or MCP or A2A)"),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-ni", help="Skip prompts; use defaults unless overridden"
    ),
    deployment_type: Optional[str] = typer.Option(
        None, "--deployment-type", "-dt", help="Deployment type (container or direct_code_deploy)"
    ),
    runtime: Optional[str] = typer.Option(
        None, "--runtime", "-rt", help="Python runtime version for direct_code_deploy (e.g., PYTHON_3_10, PYTHON_3_11)"
    ),
):
    """Configure a Bedrock AgentCore agent interactively or with parameters.

    Examples:
      agentcore configure                          # Fully interactive (current directory)
      agentcore configure --entrypoint writer/   # Directory (auto-detect entrypoint)
      agentcore configure --entrypoint agent.py    # File (use as entrypoint)
    """
    if ctx.invoked_subcommand is not None:
        return

    if protocol and protocol.upper() not in ["HTTP", "MCP", "A2A"]:
        _handle_error("Error: --protocol must be either HTTP or MCP or A2A")

    # Validate VPC configuration
    vpc_subnets = None
    vpc_security_groups = None

    if vpc:
        # VPC mode requires both subnets and security groups
        if not subnets or not security_groups:
            _handle_error(
                "VPC mode requires both --subnets and --security-groups.\n"
                "Example: agentcore configure --entrypoint my_agent.py --vpc "
                "--subnets subnet-abc123,subnet-def456 --security-groups sg-xyz789"
            )

        # Parse and validate subnet IDs - UPDATED VALIDATION
        vpc_subnets = [s.strip() for s in subnets.split(",") if s.strip()]
        for subnet_id in vpc_subnets:
            # Format: subnet-{8-17 hex characters}
            if not subnet_id.startswith("subnet-"):
                _handle_error(
                    f"Invalid subnet ID format: {subnet_id}\nSubnet IDs must start with 'subnet-' (e.g., subnet-abc123)"
                )
            # Check minimum length (subnet- + at least 8 chars)
            if len(subnet_id) < 15:  # "subnet-" (7) + 8 chars = 15
                _handle_error(
                    f"Invalid subnet ID format: {subnet_id}\nSubnet ID is too short. Expected format: subnet-xxxxxxxx"
                )

        # Parse and validate security group IDs - UPDATED VALIDATION
        vpc_security_groups = [sg.strip() for sg in security_groups.split(",") if sg.strip()]
        for sg_id in vpc_security_groups:
            # Format: sg-{8-17 hex characters}
            if not sg_id.startswith("sg-"):
                _handle_error(
                    f"Invalid security group ID format: {sg_id}\n"
                    f"Security group IDs must start with 'sg-' (e.g., sg-abc123)"
                )
            # Check minimum length (sg- + at least 8 chars)
            if len(sg_id) < 11:  # "sg-" (3) + 8 chars = 11
                _handle_error(
                    f"Invalid security group ID format: {sg_id}\n"
                    f"Security group ID is too short. Expected format: sg-xxxxxxxx"
                )

        _print_success(
            f"VPC mode enabled with {len(vpc_subnets)} subnets and {len(vpc_security_groups)} security groups"
        )

    elif subnets or security_groups:
        # Error: VPC resources provided without --vpc flag
        _handle_error(
            "The --subnets and --security-groups flags require --vpc flag.\n"
            "Use: agentcore configure --entrypoint my_agent.py --vpc --subnets ... --security-groups ..."
        )
    # Validate lifecycle configuration
    if idle_timeout is not None and max_lifetime is not None:
        if idle_timeout > max_lifetime:
            _handle_error(f"Error: --idle-timeout ({idle_timeout}s) must be <= --max-lifetime ({max_lifetime}s)")

    console.print("[cyan]Configuring Bedrock AgentCore...[/cyan]")

    # Create configuration manager early for consistent prompting
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    config_manager = ConfigurationManager(config_path, non_interactive)

    # Interactive entrypoint selection
    if not entrypoint:
        if non_interactive:
            entrypoint_input = "."
        else:
            console.print("\n📂 [cyan]Entrypoint Selection[/cyan]")
            console.print("[dim]Specify the entry point (use Tab for autocomplete):[/dim]")
            console.print("[dim]  • File path: weather/agent.py[/dim]")
            console.print("[dim]  • Directory: weather/ (auto-detects main.py, agent.py, app.py)[/dim]")
            console.print("[dim]  • Current directory: press Enter[/dim]")

            entrypoint_input = (
                prompt("Entrypoint: ", completer=PathCompleter(), complete_while_typing=True, default="").strip() or "."
            )
    else:
        entrypoint_input = entrypoint

    # Resolve the entrypoint_input (handles both file and directory)
    entrypoint_path = Path(entrypoint_input).resolve()

    # Validate that the path is within the current directory
    current_dir = Path.cwd().resolve()
    try:
        entrypoint_path.relative_to(current_dir)
    except ValueError:
        _handle_error(
            f"Path must be within the current directory: {entrypoint_input}\n"
            f"External paths are not supported for project portability.\n"
            f"Consider copying the file into your project directory."
        )

    if entrypoint_path.is_file():
        # It's a file - use directly as entrypoint
        entrypoint = str(entrypoint_path)
        source_path = str(entrypoint_path.parent)
        if not non_interactive:
            rel_path = get_relative_path(entrypoint_path)
            _print_success(f"Using file: {rel_path}")
    elif entrypoint_path.is_dir():
        # It's a directory - detect entrypoint within it
        source_path = str(entrypoint_path)
        entrypoint = _detect_entrypoint_in_source(source_path, non_interactive)
    else:
        _handle_error(f"Path not found: {entrypoint_input}")

    # Process agent name
    entrypoint_path = Path(entrypoint)

    # Infer agent name from full entrypoint path (e.g., agents/writer/main.py -> agents_writer_main)
    if not agent_name:
        suggested_name = infer_agent_name(entrypoint_path)
        agent_name = config_manager.prompt_agent_name(suggested_name)

    valid, error = validate_agent_name(agent_name)
    if not valid:
        _handle_error(error)

    def _validate_deployment_type_compatibility(agent_name: str, deployment_type: str):
        """Validate that deployment type is compatible with existing agent configuration."""
        if config_manager.existing_config and config_manager.existing_config.name == agent_name:
            existing_deployment_type = config_manager.existing_config.deployment_type
            if deployment_type and deployment_type != existing_deployment_type:
                _handle_error(
                    f"Cannot change deployment type from '{existing_deployment_type}' to "
                    f"'{deployment_type}' for existing agent '{agent_name}'.\n"
                    f"To change deployment types, first destroy the existing agent:\n"
                    f"  agentcore destroy --agent {agent_name}\n"
                    f"Then reconfigure with the new deployment type."
                )

    # Check for existing agent configuration and validate deployment type compatibility
    _validate_deployment_type_compatibility(agent_name, deployment_type)

    # Handle dependency file selection with simplified logic
    final_requirements_file = _handle_requirements_file_display(requirements_file, non_interactive, source_path)

    def _validate_cli_args(deployment_type, runtime, ecr_repository, s3_bucket, direct_code_deploy_available, prereq_error):
        """Validate CLI arguments."""
        if deployment_type and deployment_type not in ["container", "direct_code_deploy"]:
            _handle_error("Error: --deployment-type must be either 'container' or 'direct_code_deploy'")

        if runtime:
            valid_runtimes = ["PYTHON_3_10", "PYTHON_3_11", "PYTHON_3_12", "PYTHON_3_13"]
            if runtime not in valid_runtimes:
                _handle_error(f"Error: --runtime must be one of: {', '.join(valid_runtimes)}")

        if runtime and deployment_type and deployment_type != "direct_code_deploy":
            _handle_error("Error: --runtime can only be used with --deployment-type direct_code_deploy")

        # Check for incompatible ECR and runtime flags
        if ecr_repository and runtime:
            _handle_error(
                "Error: --ecr and --runtime are incompatible. "
                "Use --ecr for container deployment or --runtime for direct_code_deploy deployment."
            )

        if ecr_repository and deployment_type == "direct_code_deploy":
            _handle_error("Error: --ecr can only be used with container deployment, not direct_code_deploy")

        # Check for incompatible S3 and ECR flags
        if s3_bucket and ecr_repository:
            _handle_error(
                "Error: --s3 and --ecr are incompatible. "
                "Use --s3 for direct_code_deploy deployment or --ecr for container deployment."
            )

        if s3_bucket and deployment_type == "container":
            _handle_error("Error: --s3 can only be used with direct_code_deploy deployment, not container")

        # Only fail if user explicitly requested direct_code_deploy deployment
        if (deployment_type == "direct_code_deploy" or runtime or s3_bucket) and not direct_code_deploy_available:
            _handle_error(f"Error: Direct Code Deploy deployment unavailable ({prereq_error})")

        return runtime

    def _get_default_runtime():
        """Get default runtime based on current Python version."""
        import sys

        current_py_version = f"{sys.version_info.major}.{sys.version_info.minor}"

        if current_py_version in ["3.10", "3.11", "3.12", "3.13"]:
            return f"PYTHON_{sys.version_info.major}_{sys.version_info.minor}"
        else:
            console.print(f"[dim]Note: Current Python {current_py_version} not supported, using python3.11[/dim]")
            return "PYTHON_3_11"

    def _prompt_for_runtime():
        """Interactive runtime selection."""
        import sys

        runtime_options = ["PYTHON_3_10", "PYTHON_3_11", "PYTHON_3_12", "PYTHON_3_13"]

        console.print("\n[dim]Select Python runtime version:[/dim]")
        for idx, runtime in enumerate(runtime_options, 1):
            console.print(f"  {idx}. {runtime}")

        default_runtime = _get_default_runtime()
        default_idx = str(runtime_options.index(default_runtime) + 1)

        while True:
            choice = prompt(f"Choice [{default_idx}]: ", default=default_idx).strip()
            if choice in ["1", "2", "3", "4"]:
                return runtime_options[int(choice) - 1]
            console.print("[red]Invalid choice. Please enter 1-4.[/red]")

    def _determine_deployment_config(
        deployment_type, runtime, ecr_repository, s3_bucket, non_interactive, direct_code_deploy_available, prereq_error
    ):
        """Determine final deployment_type and runtime_type."""
        # Case 3: Only runtime provided -> default to direct_code_deploy
        if runtime and not deployment_type:
            deployment_type = "direct_code_deploy"

        # Case 4: Only ECR repository provided -> default to container
        if ecr_repository and not deployment_type:
            deployment_type = "container"

        # Case 5: Only S3 bucket provided -> default to direct_code_deploy
        if s3_bucket and not deployment_type:
            deployment_type = "direct_code_deploy"

        # Case 1 & 3: Both provided or runtime-only
        if deployment_type == "direct_code_deploy" and runtime:
            return "direct_code_deploy", runtime

        # Case 2: Only deployment_type=direct_code_deploy provided
        if deployment_type == "direct_code_deploy":
            if non_interactive:
                return "direct_code_deploy", _get_default_runtime()
            else:
                return "direct_code_deploy", _prompt_for_runtime()

        # Container deployment
        if deployment_type == "container":
            return "container", None

        # Non-interactive mode with no CLI args - use defaults
        if non_interactive:
            if direct_code_deploy_available:
                return "direct_code_deploy", _get_default_runtime()
            else:
                console.print(f"[yellow]Direct Code Deploy unavailable ({prereq_error}), using Container deployment[/yellow]")
                return "container", None

        # Interactive mode with no CLI args - use existing logic
        return None, None

    # Check direct_code_deploy prerequisites (uv and zip availability)
    def _check_direct_code_deploy_available():
        """Check if direct_code_deploy prerequisites are met."""
        import shutil

        if not shutil.which("uv"):
            return False, "uv not found (install from: https://docs.astral.sh/uv/)"
        if not shutil.which("zip"):
            return False, "zip utility not found"
        return True, None

    direct_code_deploy_available, prereq_error = _check_direct_code_deploy_available()

    # Validate CLI arguments
    runtime = _validate_cli_args(
        deployment_type, runtime, ecr_repository, s3_bucket, direct_code_deploy_available, prereq_error
    )

    # Determine deployment configuration
    console.print("\n🚀 [cyan]Deployment Configuration[/cyan]")
    final_deployment_type, runtime_type = _determine_deployment_config(
        deployment_type,
        runtime,
        ecr_repository,
        s3_bucket,
        non_interactive,
        direct_code_deploy_available,
        prereq_error,
    )

    if final_deployment_type:
        # CLI args provided or non-interactive with defaults
        deployment_type = final_deployment_type
        if deployment_type == "direct_code_deploy":
            # Convert PYTHON_3_11 -> python3.11 for display
            display_version = runtime_type.lower().replace("python_", "python").replace("_", ".")
            _print_success(f"Using: Direct Code Deploy ({display_version})")
        else:
            _print_success("Using: Container")
    else:
        # Interactive mode
        if direct_code_deploy_available:
            deployment_options = [
                ("Direct Code Deploy (recommended) - Python only, no Docker required", "direct_code_deploy"),
                ("Container - For custom runtimes or complex dependencies", "container"),
            ]
        else:
            console.print(
                f"[yellow]Warning: Direct Code Deploy deployment unavailable ({prereq_error}). "
                f"Falling back to Container deployment.[/yellow]"
            )
            deployment_options = [
                ("Container - Docker-based deployment", "container"),
            ]

        console.print("[dim]Select deployment type:[/dim]")
        for idx, (desc, _) in enumerate(deployment_options, 1):
            console.print(f"  {idx}. {desc}")

        if len(deployment_options) == 1:
            deployment_type = "container"
            _print_success("Deployment type: Container")
            runtime_type = None
        else:
            while True:
                choice = prompt("Choice [1]: ", default="1").strip()
                if choice in ["1", "2"]:
                    deployment_type = deployment_options[int(choice) - 1][1]
                    break
                console.print("[red]Invalid choice. Please enter 1 or 2.[/red]")

            if deployment_type == "direct_code_deploy":
                runtime_type = _prompt_for_runtime()
                display_version = runtime_type.lower().replace("_", ".")
                _print_success(f"Deployment type: Direct Code Deploy ({display_version})")
            else:
                runtime_type = None
                _print_success("Deployment type: Container")

    # Validate deployment type compatibility with existing configuration (for interactive mode)
    _validate_deployment_type_compatibility(agent_name, deployment_type)

    # Interactive prompts for missing values - clean and elegant
    if not execution_role:
        execution_role = config_manager.prompt_execution_role()

    # Handle ECR repository (only for container deployments)
    auto_create_ecr = True
    if deployment_type == "container":
        if ecr_repository and ecr_repository.lower() == "auto":
            # User explicitly requested auto-creation
            ecr_repository = None
            auto_create_ecr = True
            _print_success("Will auto-create ECR repository")
        elif not ecr_repository:
            ecr_repository, auto_create_ecr = config_manager.prompt_ecr_repository()
        else:
            # User provided a specific ECR repository
            auto_create_ecr = False
            _print_success(f"Using existing ECR repository: [dim]{ecr_repository}[/dim]")
    else:
        # Code zip doesn't need ECR
        ecr_repository = None
        auto_create_ecr = False

    # Handle S3 bucket (only for direct_code_deploy deployments)
    final_s3_bucket = None
    auto_create_s3 = True
    if deployment_type == "direct_code_deploy":
        if s3_bucket and s3_bucket.lower() == "auto":
            # User explicitly requested auto-creation
            final_s3_bucket = None
            auto_create_s3 = True
            _print_success("Will auto-create S3 bucket")
        elif not s3_bucket:
            final_s3_bucket, auto_create_s3 = config_manager.prompt_s3_bucket()
        else:
            # User provided a specific S3 bucket
            final_s3_bucket = s3_bucket
            auto_create_s3 = False
            _print_success(f"Using existing S3 bucket: [dim]{s3_bucket}[/dim]")
    else:
        # Container doesn't need S3 bucket
        final_s3_bucket = None
        auto_create_s3 = False

    # Handle OAuth authorization configuration
    oauth_config = None
    if authorizer_config:
        # Parse provided JSON configuration
        try:
            oauth_config = json.loads(authorizer_config)
            _print_success("Using provided OAuth authorizer configuration")
        except json.JSONDecodeError as e:
            _handle_error(f"Invalid JSON in --authorizer-config: {e}", e)
    else:
        oauth_config = config_manager.prompt_oauth_config()

    # Handle request header allowlist configuration
    request_header_config = None
    if request_header_allowlist:
        # Parse comma-separated headers and create configuration
        headers = [header.strip() for header in request_header_allowlist.split(",") if header.strip()]
        if headers:
            request_header_config = {"requestHeaderAllowlist": headers}
            _print_success(f"Configured request header allowlist with {len(headers)} headers")
        else:
            _handle_error("Empty request header allowlist provided")
    else:
        request_header_config = config_manager.prompt_request_header_allowlist()

    if disable_memory:
        memory_mode_value = "NO_MEMORY"
    else:
        memory_mode_value = "STM_ONLY"

    try:
        result = configure_bedrock_agentcore(
            agent_name=agent_name,
            entrypoint_path=Path(entrypoint),
            execution_role=execution_role,
            code_build_execution_role=code_build_execution_role,
            ecr_repository=ecr_repository,
            s3_path=final_s3_bucket,
            container_runtime=container_runtime,
            auto_create_ecr=auto_create_ecr,
            auto_create_s3=auto_create_s3,
            enable_observability=not disable_otel,
            memory_mode=memory_mode_value,
            requirements_file=final_requirements_file,
            authorizer_configuration=oauth_config,
            request_header_configuration=request_header_config,
            verbose=verbose,
            region=region,
            protocol=protocol.upper() if protocol else None,
            non_interactive=non_interactive,
            source_path=source_path,
            vpc_enabled=vpc,
            vpc_subnets=vpc_subnets,
            vpc_security_groups=vpc_security_groups,
            idle_timeout=idle_timeout,
            max_lifetime=max_lifetime,
            deployment_type=deployment_type,
            runtime_type=runtime_type,
        )

        # Prepare authorization info for summary
        auth_info = "IAM (default)"
        if oauth_config:
            auth_info = "OAuth (customJWTAuthorizer)"

        # Prepare request headers info for summary
        headers_info = ""
        if request_header_config:
            headers = request_header_config.get("requestHeaderAllowlist", [])
            headers_info = f"Request Headers Allowlist: [dim]{len(headers)} headers configured[/dim]\n"

        network_info = "Public"
        if vpc:
            network_info = f"VPC ({len(vpc_subnets)} subnets, {len(vpc_security_groups)} security groups)"

        execution_role_display = "Auto-create" if not result.execution_role else result.execution_role
        saved_config = load_config(result.config_path)
        saved_agent = saved_config.get_agent_config(agent_name)

        # Display memory status based on actual configuration
        if saved_agent.memory.mode == "NO_MEMORY":
            memory_info = "Disabled"
        elif saved_agent.memory.mode == "STM_AND_LTM":
            memory_info = "Short-term + Long-term memory (30-day retention)"
        else:  # STM_ONLY
            memory_info = "Short-term memory (30-day retention)"

        lifecycle_info = ""
        if idle_timeout or max_lifetime:
            lifecycle_info = "\n[bold]Lifecycle Settings:[/bold]\n"
            if idle_timeout:
                lifecycle_info += f"Idle Timeout: [cyan]{idle_timeout}s ({idle_timeout // 60} minutes)[/cyan]\n"
            if max_lifetime:
                lifecycle_info += f"Max Lifetime: [cyan]{max_lifetime}s ({max_lifetime // 3600} hours)[/cyan]\n"

        # Prepare deployment-specific info
        agent_details_info = ""
        config_info = ""
        if deployment_type == "container":
            ecr_display = "Auto-create" if result.auto_create_ecr else result.ecr_repository or "N/A"
            config_info = f"ECR Repository: [cyan]{ecr_display}[/cyan]\n"
        else:  # direct_code_deploy
            runtime_display = (
                result.runtime_type.lower().replace("python_", "python").replace("_", ".")
                if result.runtime_type
                else "N/A"
            )
            s3_display = "Auto-create" if result.auto_create_s3 else result.s3_path or "N/A"
            agent_details_info = f"Runtime: [cyan]{runtime_display}[/cyan]\n"
            config_info = f"S3 Bucket: [cyan]{s3_display}[/cyan]\n"

        console.print(
            Panel(
                f"[bold]Agent Details[/bold]\n"
                f"Agent Name: [cyan]{agent_name}[/cyan]\n"
                f"Deployment: [cyan]{deployment_type}[/cyan]\n"
                f"Region: [cyan]{result.region}[/cyan]\n"
                f"Account: [cyan]{result.account_id}[/cyan]\n"
                f"{agent_details_info}\n"
                f"[bold]Configuration[/bold]\n"
                f"Execution Role: [cyan]{execution_role_display}[/cyan]\n"
                f"ECR Repository: [cyan]"
                f"{'Auto-create' if result.auto_create_ecr else result.ecr_repository or 'N/A'}"
                f"[/cyan]\n"
                f"Network Mode: [cyan]{network_info}[/cyan]\n"
                f"{config_info}"
                f"Authorization: [cyan]{auth_info}[/cyan]\n\n"
                f"{headers_info}\n"
                f"Memory: [cyan]{memory_info}[/cyan]\n\n"
                f"{lifecycle_info}\n"
                f"📄 Config saved to: [dim]{result.config_path}[/dim]\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"   [cyan]agentcore launch[/cyan]",
                title="Configuration Success",
                border_style="bright_blue",
            )
        )

    except ValueError as e:
        # Handle validation errors from core layer
        _handle_error(str(e), e)
    except Exception as e:
        _handle_error(f"Configuration failed: {e}", e)


def launch(
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Agent name (use 'agentcore configure list' to see available agents)"
    ),
    local: bool = typer.Option(False, "--local", "-l", help="Run locally for development and testing"),
    local_build: bool = typer.Option(
        False,
        "--local-build",
        "-lb",
        help="Build locally and deploy to cloud (container deployment only)",
    ),
    auto_update_on_conflict: bool = typer.Option(
        False,
        "--auto-update-on-conflict",
        "-auc",
        help="Automatically update existing agent instead of failing with ConflictException",
    ),
    force_rebuild_deps: bool = typer.Option(
        False,
        "--force-rebuild-deps",
        "-frd",
        help="Force rebuild of dependencies even if cached (direct_code_deploy deployments only)",
    ),
    envs: List[str] = typer.Option(  # noqa: B008
        None, "--env", "-env", help="Environment variables for agent (format: KEY=VALUE)"
    ),
    code_build: bool = typer.Option(
        False,
        "--code-build",
        help="[DEPRECATED] CodeBuild is now the default. Use no flags for CodeBuild deployment.",
        hidden=True,
    ),
):
    """Launch Bedrock AgentCore with three deployment modes.

    🚀 DEFAULT (no flags): Cloud runtime (RECOMMENDED)
       - direct_code_deploy deployment: Direct deploy Python code to runtime
       - Container deployment: Build ARM64 containers in the cloud with CodeBuild
       - Deploy to Bedrock AgentCore runtime
       - No local Docker required

    💻 --local: Local runtime
       - Container deployment: Build and run container locally (requires Docker/Finch/Podman)
       - direct_code_deploy deployment: Run Python script locally with uv
       - For local development and testing

    🔧 --local-build: Local build + cloud runtime
       - Build container locally with Docker
       - Deploy to Bedrock AgentCore runtime
       - Only supported for container deployment type
       - requires Docker/Finch/Podman
       - Use when you need custom build control but want cloud deployment

    MIGRATION GUIDE:
    - OLD: agentcore launch --code-build  →  NEW: agentcore launch
    - OLD: agentcore launch --local       →  NEW: agentcore launch --local (unchanged)
    - NEW: agentcore launch --local-build (build locally + deploy to cloud)
    """
    # Handle deprecated --code-build flag
    if code_build:
        console.print("[yellow]⚠️  DEPRECATION WARNING: --code-build flag is deprecated[/yellow]")
        console.print("[yellow]   CodeBuild is now the default deployment method[/yellow]")
        console.print("[yellow]   MIGRATION: Simply use 'agentcore launch' (no flags needed)[/yellow]")
        console.print("[yellow]   This flag will be removed in a future version[/yellow]\n")

    # Validate mutually exclusive options
    if sum([local, local_build, code_build]) > 1:
        _handle_error("Error: --local, --local-build, and --code-build cannot be used together")

    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    # Load config early to determine deployment type for proper messaging
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent)
    deployment_type = agent_config.deployment_type

    # Validate deployment type compatibility early
    if local_build or force_rebuild_deps:
        if local_build and deployment_type == "direct_code_deploy":
            _handle_error(
                "Error: --local-build is only supported for container deployment type.\n"
                "For direct_code_deploy deployment, use:\n"
                "  • 'agentcore launch' (default)\n"
                "  • 'agentcore launch --local' (local execution)"
            )

        if force_rebuild_deps and deployment_type != "direct_code_deploy":
            _handle_error(
                "Error: --force-rebuild-deps is only supported for direct_code_deploy deployment type.\n"
                "Container deployments always rebuild dependencies."
            )

    try:
        # Show launch mode with enhanced migration guidance
        if local:
            mode = "local"
            console.print(f"[cyan]🏠 Launching Bedrock AgentCore ({mode} mode)...[/cyan]")
            console.print("[dim]   • Build and run container locally[/dim]")
            console.print("[dim]   • Requires Docker/Finch/Podman to be installed[/dim]")
            console.print("[dim]   • Perfect for development and testing[/dim]\n")
        elif local_build:
            mode = "local-build"
            console.print(f"[cyan]🔧 Launching Bedrock AgentCore ({mode} mode - NEW!)...[/cyan]")
            console.print("[dim]   • Build container locally with Docker[/dim]")
            console.print("[dim]   • Deploy to Bedrock AgentCore cloud runtime[/dim]")
            console.print("[dim]   • Requires Docker/Finch/Podman to be installed[/dim]")
            console.print("[dim]   • Use when you need custom build control[/dim]\n")
        elif code_build:
            # Handle deprecated flag - treat as default
            mode = "codebuild" if deployment_type == "container" else "cloud"
            console.print(f"[cyan]🚀 Launching Bedrock AgentCore ({mode} mode - RECOMMENDED)...[/cyan]")
            if deployment_type == "direct_code_deploy":
                console.print("[dim]   • Deploy Python code directly to runtime[/dim]")
                console.print("[dim]   • No Docker required[/dim]")
            else:
                console.print("[dim]   • Build ARM64 containers in the cloud with CodeBuild[/dim]")
                console.print("[dim]   • No local Docker required[/dim]")
            console.print("[dim]   • Production-ready deployment[/dim]\n")
        else:
            mode = "codebuild" if deployment_type == "container" else "cloud"
            console.print(f"[cyan]🚀 Launching Bedrock AgentCore ({mode} mode - RECOMMENDED)...[/cyan]")
            if deployment_type == "direct_code_deploy":
                console.print("[dim]   • Deploy Python code directly to runtime[/dim]")
                console.print("[dim]   • No Docker required (DEFAULT behavior)[/dim]")
            else:
                console.print("[dim]   • Build ARM64 containers in the cloud with CodeBuild[/dim]")
                console.print("[dim]   • No local Docker required (DEFAULT behavior)[/dim]")
            console.print("[dim]   • Production-ready deployment[/dim]\n")

            # Show deployment options hint for first-time users
            console.print("[dim]💡 Deployment options:[/dim]")
            mode_name = "CodeBuild" if deployment_type == "container" else "Cloud"
            console.print(f"[dim]   • agentcore launch                → {mode_name} (current)[/dim]")
            console.print("[dim]   • agentcore launch --local        → Local development[/dim]")
            if deployment_type == "container":
                console.print("[dim]   • agentcore launch --local-build  → Local build + cloud deploy[/dim]")
            console.print()

        # Use the operations module
        with console.status("[bold]Launching Bedrock AgentCore...[/bold]"):
            # Parse environment variables for local mode
            env_vars = None
            if envs:
                env_vars = {}
                for env_var in envs:
                    if "=" not in env_var:
                        _handle_error(f"Invalid environment variable format: {env_var}. Use KEY=VALUE format.")
                    key, value = env_var.split("=", 1)
                    env_vars[key] = value

            # Call the operation - CodeBuild is now default, unless --local-build is specified
            result = launch_bedrock_agentcore(
                config_path=config_path,
                agent_name=agent,
                local=local,
                use_codebuild=not local_build,
                env_vars=env_vars,
                auto_update_on_conflict=auto_update_on_conflict,
                console=console,
                force_rebuild_deps=force_rebuild_deps,
            )

        # Handle result based on mode
        if result.mode == "local":
            _print_success(f"Docker image built: {result.tag}")
            _print_success("Ready to run locally")
            console.print("Starting server at http://localhost:8080")
            console.print("Starting OAuth2 3LO callback server at http://localhost:8081")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

            if result.runtime is None or result.port is None:
                _handle_error("Unable to launch locally")

            try:
                oauth2_callback_endpoint = Thread(
                    target=start_oauth2_callback_server,
                    args=(
                        config_path,
                        agent,
                    ),
                    name="OAuth2 3LO Callback Server",
                    daemon=True,
                )
                oauth2_callback_endpoint.start()
                result.runtime.run_local(result.tag, result.port, result.env_vars)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped[/yellow]")

        elif result.mode == "local_direct_code_deploy":
            _print_success("Ready to run locally with uv run")
            console.print(f"Starting server at http://localhost:{result.port}")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

            try:
                # The process was started in the launch function, just wait for it
                import subprocess  # nosec B404

                # Re-run the command in foreground for proper signal handling
                source_dir = Path(agent_config.source_path) if agent_config.source_path else Path.cwd()
                entrypoint_abs = Path(agent_config.entrypoint)

                try:
                    entrypoint_path = str(entrypoint_abs.relative_to(source_dir))
                except ValueError:
                    entrypoint_path = entrypoint_abs.name

                # Prepare environment
                local_env = dict(os.environ)
                if result.env_vars:
                    local_env.update(result.env_vars)
                local_env.setdefault("PORT", str(result.port))

                # Use the same dependency detection as direct_code_deploy deployment
                from ...utils.runtime.entrypoint import detect_dependencies

                dep_info = detect_dependencies(source_dir)

                if not dep_info.found:
                    _handle_error(
                        f"No dependencies file found in {source_dir}.\n"
                        "direct_code_deploy deployment requires either requirements.txt or pyproject.toml"
                    )

                # Use the configured Python version (e.g., PYTHON_3_11 -> 3.11)
                python_version = agent_config.runtime_type.replace("PYTHON_", "").replace("_", ".")
                cmd = [
                    "uv",
                    "run",
                    "--isolated",
                    "--python",
                    python_version,
                    "--with-requirements",
                    dep_info.resolved_path,
                    entrypoint_path,
                ]

                # Run from source directory (same as direct_code_deploy)
                subprocess.run(cmd, cwd=source_dir, env=local_env, check=False)  # nosec B603
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped[/yellow]")

        elif result.mode == "direct_code_deploy":
            # Code zip deployment success
            agent_name = agent_config.name if agent_config else "unknown"
            region = agent_config.aws.region if agent_config else "us-east-1"

            deploy_panel = (
                f"[bold]Agent Details:[/bold]\n"
                f"Agent Name: [cyan]{agent_name}[/cyan]\n"
                f"Agent ARN: [cyan]{result.agent_arn}[/cyan]\n"
                f"Deployment Type: [cyan]Direct Code Deploy[/cyan]\n\n"
                f"📦 Code package deployed to Bedrock AgentCore\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"   [cyan]agentcore status[/cyan]\n"
                f'   [cyan]agentcore invoke \'{{"prompt": "Hello"}}\'[/cyan]'
            )

            # Add log information if we have agent_id
            if result.agent_id:
                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id, deployment_type="direct_code_deploy")
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                deploy_panel += f"\n\n📋 [cyan]CloudWatch Logs:[/cyan]\n   {runtime_logs}\n   {otel_logs}\n\n"
                # Only show GenAI Observability Dashboard if OTEL is enabled
                if agent_config and agent_config.aws.observability.enabled:
                    deploy_panel += (
                        f"🔍 [cyan]GenAI Observability Dashboard:[/cyan]\n"
                        f"   {get_genai_observability_url(region)}\n\n"
                        f"⏱️  [dim]Note: Observability data may take up to 10 minutes to appear "
                        f"after first launch[/dim]\n\n"
                    )
                deploy_panel += f"💡 [dim]Tail logs with:[/dim]\n   {follow_cmd}\n   {since_cmd}"

            console.print(
                Panel(
                    deploy_panel,
                    title="Deployment Success",
                    border_style="bright_blue",
                )
            )

        elif result.mode == "codebuild":
            # Show deployment success panel
            agent_name = result.tag.split(":")[0].replace("bedrock_agentcore-", "")

            # Get region from configuration
            region = agent_config.aws.region if agent_config else "us-east-1"

            deploy_panel = (
                f"[bold]Agent Details:[/bold]\n"
                f"Agent Name: [cyan]{agent_name}[/cyan]\n"
                f"Agent ARN: [cyan]{result.agent_arn}[/cyan]\n"
                f"ECR URI: [cyan]{result.ecr_uri}:latest[/cyan]\n"
                f"CodeBuild ID: [dim]{result.codebuild_id}[/dim]\n\n"
                f"🚀 ARM64 container deployed to Bedrock AgentCore\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"   [cyan]agentcore status[/cyan]\n"
                f'   [cyan]agentcore invoke \'{{"prompt": "Hello"}}\'[/cyan]'
            )

            # Add log information if we have agent_id
            if result.agent_id:
                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id)
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                deploy_panel += f"\n\n📋 [cyan]CloudWatch Logs:[/cyan]\n   {runtime_logs}\n   {otel_logs}\n\n"
                # Only show GenAI Observability Dashboard if OTEL is enabled
                if agent_config and agent_config.aws.observability.enabled:
                    deploy_panel += (
                        f"🔍 [cyan]GenAI Observability Dashboard:[/cyan]\n"
                        f"   {get_genai_observability_url(region)}\n\n"
                        f"[dim]Note: Observability data may take up to 10 minutes to appear "
                        f"after first launch[/dim]\n\n"
                    )
                deploy_panel += f"💡 [dim]Tail logs with:[/dim]\n   {follow_cmd}\n   {since_cmd}"

            console.print(
                Panel(
                    deploy_panel,
                    title="Deployment Success",
                    border_style="bright_blue",
                )
            )

        else:  # cloud mode (either CodeBuild default or local-build)
            agent_name = result.tag.split(":")[0].replace("bedrock_agentcore-", "")

            if local_build:
                title = "Local Build Success"
                icon = "🔧"
            else:
                title = "Deployment Success"
                icon = "🚀"

            deploy_panel = (
                f"[bold]Agent Details:[/bold]\n"
                f"Agent Name: [cyan]{agent_name}[/cyan]\n"
                f"Agent ARN: [cyan]{result.agent_arn}[/cyan]\n"
                f"ECR URI: [cyan]{result.ecr_uri}[/cyan]\n\n"
                f"{icon} Container deployed to Bedrock AgentCore\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"   [cyan]agentcore status[/cyan]\n"
                f'   [cyan]agentcore invoke \'{{"prompt": "Hello"}}\'[/cyan]'
            )

            if result.agent_id:
                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id)
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                deploy_panel += (
                    f"\n\n📋 [cyan]CloudWatch Logs:[/cyan]\n"
                    f"   {runtime_logs}\n"
                    f"   {otel_logs}\n\n"
                    f"💡 [dim]Tail logs with:[/dim]\n"
                    f"   {follow_cmd}\n"
                    f"   {since_cmd}"
                )

            console.print(
                Panel(
                    deploy_panel,
                    title=title,
                    border_style="bright_blue",
                )
            )

    except FileNotFoundError:
        _handle_error(".bedrock_agentcore.yaml not found. Run 'agentcore configure --entrypoint <file>' first")
    except ValueError as e:
        _handle_error(str(e), e)
    except RuntimeError as e:
        _handle_error(str(e), e)
    except Exception as e:
        if not isinstance(e, typer.Exit):
            _handle_error(f"Launch failed: {e}", e)
        raise


def _show_invoke_info_panel(agent_name: str, invoke_result=None, config=None):
    """Show consistent panel with invoke information (session, request_id, arn, logs)."""
    info_lines = []
    # Session ID
    if invoke_result and invoke_result.session_id:
        info_lines.append(f"Session: [cyan]{invoke_result.session_id}[/cyan]")
    # Request ID
    if invoke_result and isinstance(invoke_result.response, dict):
        request_id = invoke_result.response.get("ResponseMetadata", {}).get("RequestId")
        if request_id:
            info_lines.append(f"Request ID: [cyan]{request_id}[/cyan]")
    # Agent ARN
    if invoke_result and invoke_result.agent_arn:
        info_lines.append(f"ARN: [cyan]{invoke_result.agent_arn}[/cyan]")
    # CloudWatch logs and GenAI Observability Dashboard (if we have config with agent_id)
    if config and hasattr(config, "bedrock_agentcore") and config.bedrock_agentcore.agent_id:
        try:
            # Get deployment type and session ID for direct_code_deploy specific logging
            deployment_type = getattr(config, "deployment_type", None)
            session_id = invoke_result.session_id if invoke_result else None

            runtime_logs, _ = get_agent_log_paths(
                config.bedrock_agentcore.agent_id, deployment_type=deployment_type, session_id=session_id
            )
            follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
            info_lines.append(f"Logs: {follow_cmd}")
            info_lines.append(f"      {since_cmd}")

            # Only show GenAI Observability Dashboard if OTEL is enabled
            if config.aws.observability.enabled:
                info_lines.append(f"GenAI Dashboard: {get_genai_observability_url(config.aws.region)}")
        except Exception:
            pass  # nosec B110
    panel_content = "\n".join(info_lines) if info_lines else "Invoke information unavailable"
    console.print(
        Panel(
            panel_content,
            title=f"{agent_name}",
            border_style="bright_blue",
            padding=(0, 1),
        )
    )


def _show_success_response(content):
    """Show success response content below panel."""
    if content:
        console.print("\n[bold]Response:[/bold]")
        console.print(content)


def _show_error_response(error_msg: str):
    """Show error message in red below panel."""
    console.print(f"\n[red]{error_msg}[/red]")


def _parse_custom_headers(headers_str: str) -> dict:
    """Parse custom headers string and apply prefix logic.

    Args:
        headers_str: String in format "Header1:value,Header2:value2"

    Returns:
        dict: Dictionary of processed headers with proper prefixes

    Raises:
        ValueError: If header format is invalid
    """
    if not headers_str or not headers_str.strip():
        return {}

    headers = {}
    header_pairs = [pair.strip() for pair in headers_str.split(",")]

    for pair in header_pairs:
        if ":" not in pair:
            raise ValueError(f"Invalid header format: '{pair}'. Expected format: 'Header:value'")

        header_name, header_value = pair.split(":", 1)
        header_name = header_name.strip()
        header_value = header_value.strip()

        if not header_name:
            raise ValueError(f"Empty header name in: '{pair}'")

        # Apply prefix logic: if header doesn't start with the custom prefix, add it
        prefix = "X-Amzn-Bedrock-AgentCore-Runtime-Custom-"
        if not header_name.startswith(prefix):
            header_name = prefix + header_name

        headers[header_name] = header_value

    return headers


def invoke(
    payload: str = typer.Argument(..., help="JSON payload to send"),
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Agent name (use 'bedrock_agentcore configure list' to see available)"
    ),
    session_id: Optional[str] = typer.Option(None, "--session-id", "-s"),
    bearer_token: Optional[str] = typer.Option(
        None, "--bearer-token", "-bt", help="Bearer token for OAuth authentication"
    ),
    local_mode: Optional[bool] = typer.Option(False, "--local", "-l", help="Send request to a running local container"),
    user_id: Optional[str] = typer.Option(None, "--user-id", "-u", help="User id for authorization flows"),
    headers: Optional[str] = typer.Option(
        None,
        "--headers",
        help="Custom headers (format: 'Header1:value,Header2:value2'). "
        "Headers will be auto-prefixed with 'X-Amzn-Bedrock-AgentCore-Runtime-Custom-' if not already present.",
    ),
):
    """Invoke Bedrock AgentCore endpoint."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    try:
        # Load project configuration to check if auth is configured
        project_config = load_config(config_path)
        config = project_config.get_agent_config(agent)

        # Parse payload
        try:
            payload_data = json.loads(payload)
        except json.JSONDecodeError:
            payload_data = {"prompt": payload}

        # Handle bearer token - only use if auth config is defined in .bedrock_agentcore.yaml
        final_bearer_token = None
        if config.authorizer_configuration is not None:
            # Auth is configured, check for bearer token
            final_bearer_token = bearer_token
            if not final_bearer_token:
                final_bearer_token = os.getenv("BEDROCK_AGENTCORE_BEARER_TOKEN")

            if final_bearer_token:
                console.print("[dim]Using bearer token for OAuth authentication[/dim]")
            else:
                console.print("[yellow]Warning: OAuth is configured but no bearer token provided[/yellow]")
        elif bearer_token or os.getenv("BEDROCK_AGENTCORE_BEARER_TOKEN"):
            console.print(
                "[yellow]Warning: Bearer token provided but OAuth is not configured in .bedrock_agentcore.yaml[/yellow]"
            )

        # Process custom headers
        custom_headers = {}
        if headers:
            try:
                custom_headers = _parse_custom_headers(headers)
                if custom_headers:
                    header_names = list(custom_headers.keys())
                    console.print(f"[dim]Using custom headers: {', '.join(header_names)}[/dim]")
            except ValueError as e:
                _handle_error(f"Invalid headers format: {e}")

        # Invoke
        result = invoke_bedrock_agentcore(
            config_path=config_path,
            payload=payload_data,
            agent_name=agent,
            session_id=session_id,
            bearer_token=final_bearer_token,
            user_id=user_id,
            local_mode=local_mode,
            custom_headers=custom_headers,
        )
        agent_display = config.name if config else (agent or "unknown")
        _show_invoke_info_panel(agent_display, result, config)
        if result.response != {}:
            content = result.response
            if isinstance(content, dict) and "response" in content:
                content = content["response"]
            if isinstance(content, list):
                if len(content) == 1:
                    content = content[0]
                else:
                    # Handle mix of strings and bytes
                    string_items = []
                    for item in content:
                        if isinstance(item, bytes):
                            string_items.append(item.decode("utf-8", errors="replace"))
                        else:
                            string_items.append(str(item))
                    content = "".join(string_items)
            # Parse JSON string if needed (handles escape sequences)
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "response" in parsed:
                        content = parsed["response"]
                    elif isinstance(parsed, str):
                        content = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
            _show_success_response(content)

    except FileNotFoundError:
        _show_configuration_not_found_panel()
        raise typer.Exit(1) from None
    except ValueError as e:
        try:
            agent_display = config.name if config else (agent or "unknown")
            agent_config = config
        except NameError:
            agent_display = agent or "unknown"
            agent_config = None
        _show_invoke_info_panel(agent_display, invoke_result=None, config=agent_config)
        if "not deployed" in str(e):
            _show_error_response("Agent not deployed - run 'agentcore launch' to deploy")
        else:
            _show_error_response(f"Invocation failed: {str(e)}")
        raise typer.Exit(1) from e
    except Exception as e:
        try:
            agent_config = config
            agent_name = config.name if config else (agent or "unknown")
        except (NameError, AttributeError):
            try:
                fallback_project_config = load_config(config_path)
                agent_config = fallback_project_config.get_agent_config(agent)
                agent_name = agent_config.name if agent_config else (agent or "unknown")
            except Exception:
                agent_config = None
                agent_name = agent or "unknown"

        from ...operations.runtime.models import InvokeResult

        request_id = getattr(e, "response", {}).get("ResponseMetadata", {}).get("RequestId")
        effective_session = session_id or (
            agent_config.bedrock_agentcore.agent_session_id
            if agent_config and hasattr(agent_config, "bedrock_agentcore")
            else None
        )

        error_result = (
            InvokeResult(
                response={"ResponseMetadata": {"RequestId": request_id}} if request_id else {},
                session_id=effective_session or "unknown",
                agent_arn=agent_config.bedrock_agentcore.agent_arn
                if agent_config and hasattr(agent_config, "bedrock_agentcore")
                else None,
            )
            if (request_id or effective_session or agent_config)
            else None
        )

        _show_invoke_info_panel(agent_name, invoke_result=error_result, config=agent_config)
        _show_error_response(f"Invocation failed: {str(e)}")
        raise typer.Exit(1) from e


def status(
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Agent name (use 'bedrock_agentcore configure list' to see available)"
    ),
    verbose: Optional[bool] = typer.Option(
        None, "--verbose", "-v", help="Verbose json output of config, agent and endpoint status"
    ),
):
    """Get Bedrock AgentCore status including config and runtime details."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    # Get status
    result = get_status(config_path, agent)

    # Output JSON
    status_json = result.model_dump()

    try:
        if not verbose:
            if "config" in status_json:
                if status_json["agent"] is None:
                    console.print(
                        Panel(
                            f"⚠️ [yellow]Configured but not deployed[/yellow]\n\n"
                            f"[bold]Agent Details:[/bold]\n"
                            f"Agent Name: [cyan]{status_json['config']['name']}[/cyan]\n"
                            f"Region: [cyan]{status_json['config']['region']}[/cyan]\n"
                            f"Account: [cyan]{status_json['config']['account']}[/cyan]\n\n"
                            f"[bold]Configuration:[/bold]\n"
                            f"Execution Role: [dim]{status_json['config']['execution_role']}[/dim]\n"
                            f"ECR Repository: [dim]{status_json['config']['ecr_repository']}[/dim]\n\n"
                            f"Your agent is configured but not yet launched.\n\n"
                            f"[bold]Next Steps:[/bold]\n"
                            f"   [cyan]agentcore launch[/cyan]",
                            title=f"Agent Status: {status_json['config']['name']}",
                            border_style="bright_blue",
                        )
                    )

                elif "agent" in status_json and status_json["agent"] is not None:
                    agent_data = status_json["agent"]
                    endpoint_data = status_json.get("endpoint", {})

                    # Determine overall status
                    endpoint_status = endpoint_data.get("status", "Unknown") if endpoint_data else "Not Ready"
                    if endpoint_status == "READY":
                        status_text = "Ready - Agent deployed and endpoint available"
                    else:
                        status_text = "Deploying - Agent created, endpoint starting"

                    # Build consolidated panel with logs
                    panel_content = (
                        f"{status_text}\n\n"
                        f"[bold]Agent Details:[/bold]\n"
                        f"Agent Name: [cyan]{status_json['config']['name']}[/cyan]\n"
                        f"Agent ARN: [cyan]{status_json['config']['agent_arn']}[/cyan]\n"
                        f"Endpoint: [cyan]{endpoint_data.get('name', 'DEFAULT')}[/cyan] "
                        f"([cyan]{endpoint_status}[/cyan])\n"
                        f"Region: [cyan]{status_json['config']['region']}[/cyan] | "
                        f"Account: [dim]{status_json['config'].get('account', 'Not available')}[/dim]\n\n"
                    )

                    # Add network information
                    network_mode = status_json.get("agent", {}).get("networkConfiguration", {}).get("networkMode")
                    if network_mode == "VPC":
                        # Get VPC info from agent response (not config)
                        network_config = (
                            status_json.get("agent", {}).get("networkConfiguration", {}).get("networkModeConfig", {})
                        )
                        vpc_subnets = network_config.get("subnets", [])
                        vpc_security_groups = network_config.get("securityGroups", [])
                        subnet_count = len(vpc_subnets)
                        sg_count = len(vpc_security_groups)
                        vpc_id = status_json.get("config", {}).get("network_vpc_id", "unknown")
                        if vpc_id:
                            panel_content += f"Network: [cyan]VPC[/cyan] ([dim]{vpc_id}[/dim])\n"
                            panel_content += f"         {subnet_count} subnets, {sg_count} security groups\n\n"
                        else:
                            panel_content += "Network: [cyan]VPC[/cyan]\n\n"
                    else:
                        panel_content += "Network: [cyan]Public[/cyan]\n\n"

                    # Add memory status with proper provisioning indication
                    if "memory_id" in status_json.get("config", {}) and status_json["config"]["memory_id"]:
                        memory_type = status_json["config"].get("memory_type", "Unknown")
                        memory_id = status_json["config"]["memory_id"]
                        memory_status = status_json["config"].get("memory_status", "Unknown")

                        # Color-code based on status
                        if memory_status == "ACTIVE":
                            panel_content += f"Memory: [green]{memory_type}[/green] ([dim]{memory_id}[/dim])\n"
                        elif memory_status in ["CREATING", "UPDATING"]:
                            panel_content += f"Memory: [yellow]{memory_type}[/yellow] ([dim]{memory_id}[/dim])\n"
                            panel_content += (
                                "         [yellow]⚠️  Memory is provisioning. "
                                "STM will be available once ACTIVE.[/yellow]\n"
                            )
                        else:
                            panel_content += f"Memory: [red]{memory_type}[/red] ([dim]{memory_id}[/dim])\n"

                        panel_content += "\n"

                    # Continue building the panel
                    panel_content += (
                        f"[bold]Deployment Info:[/bold]\n"
                        f"Created: [dim]{agent_data.get('createdAt', 'Not available')}[/dim]\n"
                        f"Last Updated: [dim]"
                        f"{endpoint_data.get('lastUpdatedAt') or agent_data.get('lastUpdatedAt', 'Not available')}"
                        f"[/dim]\n\n"
                    )

                    if status_json["config"].get("idle_timeout") or status_json["config"].get("max_lifetime"):
                        panel_content += "[bold]Lifecycle Settings:[/bold]\n"

                        idle = status_json["config"].get("idle_timeout")
                        if idle:
                            panel_content += f"Idle Timeout: [cyan]{idle}s ({idle // 60} minutes)[/cyan]\n"

                        max_life = status_json["config"].get("max_lifetime")
                        if max_life:
                            panel_content += f"Max Lifetime: [cyan]{max_life}s ({max_life // 3600} hours)[/cyan]\n"

                        panel_content += "\n"

                    # Add CloudWatch logs information
                    agent_id = status_json.get("config", {}).get("agent_id")
                    if agent_id:
                        try:
                            endpoint_name = endpoint_data.get("name")
                            project_config = load_config(config_path)
                            agent_config = project_config.get_agent_config(agent)
                            deployment_type = agent_config.deployment_type if agent_config else "container"
                            runtime_logs, otel_logs = get_agent_log_paths(agent_id, endpoint_name, deployment_type=deployment_type)
                            follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)

                            panel_content += f"📋 [cyan]CloudWatch Logs:[/cyan]\n   {runtime_logs}\n   {otel_logs}\n\n"

                            # Only show GenAI Observability Dashboard if OTEL is enabled
                            if agent_config and agent_config.aws.observability.enabled:
                                panel_content += (
                                    f"🔍 [cyan]GenAI Observability Dashboard:[/cyan]\n"
                                    f"   {get_genai_observability_url(status_json['config']['region'])}\n\n"
                                    f"[dim]Note: Observability data may take up to 10 minutes to appear "
                                    f"after first launch[/dim]\n\n"
                                )

                            panel_content += f"💡 [dim]Tail logs with:[/dim]\n   {follow_cmd}\n   {since_cmd}\n\n"
                        except Exception:  # nosec B110
                            # If log retrieval fails, continue without logs section
                            pass

                    # Add ready-to-invoke message if endpoint is ready
                    if endpoint_status == "READY":
                        panel_content += (
                            '[bold]Ready to invoke:[/bold]\n   [cyan]agentcore invoke \'{"prompt": "Hello"}\'[/cyan]'
                        )
                    else:
                        panel_content += (
                            "[bold]Next Steps:[/bold]\n"
                            "   [cyan]agentcore status[/cyan]   # Check when endpoint is ready"
                        )

                    console.print(
                        Panel(
                            panel_content,
                            title=f"Agent Status: {status_json['config']['name']}",
                            border_style="bright_blue",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            "[green]Please launch agent first![/green]\n\n",
                            title="Bedrock AgentCore Agent Status",
                            border_style="bright_blue",
                        )
                    )

        else:  # full json verbose output
            console.print(
                Syntax(
                    json.dumps(status_json, indent=2, default=str, ensure_ascii=False),
                    "json",
                    background_color="default",
                    word_wrap=True,
                )
            )

    except FileNotFoundError:
        _show_configuration_not_found_panel()
        raise typer.Exit(1) from None
    except ValueError as e:
        console.print(
            Panel(
                f"❌ [red]Status Check Failed[/red]\n\n"
                f"Error: {str(e)}\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"   [cyan]agentcore configure --entrypoint your_agent.py[/cyan]\n"
                f"   [cyan]agentcore launch[/cyan]",
                title="❌ Status Error",
                border_style="bright_blue",
            )
        )
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(
            Panel(
                f"❌ [red]Status Check Failed[/red]\n\n"
                f"Unexpected error: {str(e)}\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"   [cyan]agentcore configure --entrypoint your_agent.py[/cyan]\n"
                f"   [cyan]agentcore launch[/cyan]",
                title="❌ Status Error",
                border_style="bright_blue",
            )
        )
        raise typer.Exit(1) from e


def stop_session(
    session_id: Optional[str] = typer.Option(
        None,
        "--session-id",
        "-s",
        help="Runtime session ID to stop. If not provided, stops the last active session from invoke.",
    ),
    agent: Optional[str] = typer.Option(
        None,
        "--agent",
        "-a",
        help="Agent name (use 'agentcore configure list' to see available agents)",
    ),
):
    """Stop an active runtime session.

    Terminates the compute session for the running agent. This frees up resources
    and ends any ongoing agent processing for that session.

    🔍 How to find session IDs:
       • Last invoked session is automatically tracked (no flag needed)
       • Check 'agentcore status' to see the tracked session ID
       • Check CloudWatch logs for session IDs from previous invokes
       • Session IDs are also visible in the config file: .bedrock_agentcore.yaml

    Session Lifecycle:
       • Runtime sessions are created when you invoke an agent
       • They automatically expire after the configured idle timeout
       • Stopping a session immediately frees resources without waiting for timeout

    Examples:
        # Stop the last invoked session (most common)
        agentcore stop-session

        # Stop a specific session by ID
        agentcore stop-session --session-id abc123xyz

        # Stop last session for a specific agent
        agentcore stop-session --agent my-agent

        # Get current session ID before stopping
        agentcore status  # Shows tracked session ID
        agentcore stop-session
    """
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    try:
        from ...operations.runtime import stop_runtime_session

        result = stop_runtime_session(
            config_path=config_path,
            session_id=session_id,
            agent_name=agent,
        )

        # Show result panel
        status_icon = "✅" if result.status_code == 200 else "⚠️"
        status_color = "green" if result.status_code == 200 else "yellow"

        console.print(
            Panel(
                f"[{status_color}]{status_icon} {result.message}[/{status_color}]\n\n"
                f"[bold]Session Details:[/bold]\n"
                f"Session ID: [cyan]{result.session_id}[/cyan]\n"
                f"Agent: [cyan]{result.agent_name}[/cyan]\n"
                f"Status Code: [cyan]{result.status_code}[/cyan]\n\n"
                f"[dim]💡 Runtime sessions automatically expire after idle timeout.\n"
                f"   Manually stopping frees resources immediately.[/dim]",
                title="Session Stopped",
                border_style="bright_blue",
            )
        )

    except FileNotFoundError:
        _show_configuration_not_found_panel()
        raise typer.Exit(1) from None
    except ValueError as e:
        console.print(
            Panel(
                f"[red]❌ Failed to Stop Session[/red]\n\n"
                f"Error: {str(e)}\n\n"
                f"[bold]How to find session IDs:[/bold]\n"
                f"  • Check 'agentcore status' for the tracked session ID\n"
                f"  • Check CloudWatch logs for session IDs\n"
                f"  • Invoke the agent first to create a session\n\n"
                f"[dim]Note: Runtime sessions cannot be listed. You can only stop\n"
                f"the session from your last invoke or a specific session ID.[/dim]",
                title="Stop Session Error",
                border_style="red",
            )
        )
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(
            Panel(
                f"[red]❌ Unexpected Error[/red]\n\n{str(e)}",
                title="Stop Session Error",
                border_style="red",
            )
        )
        raise typer.Exit(1) from e


def destroy(
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Agent name (use 'agentcore configure list' to see available agents)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be destroyed without actually destroying anything"
    ),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompts and destroy immediately"),
    delete_ecr_repo: bool = typer.Option(
        False, "--delete-ecr-repo", help="Also delete the ECR repository after removing images"
    ),
) -> None:
    """Destroy Bedrock AgentCore resources.

    This command removes the following AWS resources for the specified agent:
    - Bedrock AgentCore endpoint (if exists)
    - Bedrock AgentCore agent runtime
    - ECR images (all images in the agent's repository)
    - CodeBuild project
    - IAM execution role (only if not used by other agents)
    - Agent deployment configuration
    - ECR repository (only if --delete-ecr-repo is specified)

    CAUTION: This action cannot be undone. Use --dry-run to preview changes first.
    """
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    try:
        # Load project configuration to get agent details
        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config(agent)

        if not agent_config:
            _handle_error(f"Agent '{agent or 'default'}' not found in configuration")

        actual_agent_name = agent_config.name

        # Show what will be destroyed
        if dry_run:
            console.print(
                f"[cyan]🔍 Dry run: Preview of resources that would be destroyed for agent "
                f"'{actual_agent_name}'[/cyan]\n"
            )
        else:
            console.print(f"[yellow]⚠️  About to destroy resources for agent '{actual_agent_name}'[/yellow]\n")

        # Check if agent is deployed
        if not agent_config.bedrock_agentcore:
            console.print("[yellow]Agent is not deployed, nothing to destroy[/yellow]")
            return

        # Show deployment details
        console.print("[cyan]Current deployment:[/cyan]")
        if agent_config.bedrock_agentcore.agent_arn:
            console.print(f"  • Agent ARN: {agent_config.bedrock_agentcore.agent_arn}")
        if agent_config.bedrock_agentcore.agent_id:
            console.print(f"  • Agent ID: {agent_config.bedrock_agentcore.agent_id}")
        if agent_config.aws.ecr_repository:
            console.print(f"  • ECR Repository: {agent_config.aws.ecr_repository}")
        if agent_config.aws.execution_role:
            console.print(f"  • Execution Role: {agent_config.aws.execution_role}")
        console.print()

        # Confirmation prompt (unless force or dry_run)
        if not dry_run and not force:
            console.print("[red]This will permanently delete AWS resources and cannot be undone![/red]")
            if delete_ecr_repo:
                console.print("[red]This includes deleting the ECR repository itself![/red]")
            response = typer.confirm(
                f"Are you sure you want to destroy the agent '{actual_agent_name}' and all its resources?"
            )
            if not response:
                console.print("[yellow]Destruction cancelled[/yellow]")
                return

        # Perform the destroy operation
        with console.status(f"[bold]{'Analyzing' if dry_run else 'Destroying'} Bedrock AgentCore resources...[/bold]"):
            result = destroy_bedrock_agentcore(
                config_path=config_path,
                agent_name=actual_agent_name,
                dry_run=dry_run,
                force=force,
                delete_ecr_repo=delete_ecr_repo,
            )

        # Display results
        if dry_run:
            console.print(f"[cyan]📋 Dry run completed for agent '{result.agent_name}'[/cyan]\n")
            title = "Resources That Would Be Destroyed"
            color = "cyan"
        else:
            if result.errors:
                console.print(
                    f"[yellow]⚠️  Destruction completed with errors for agent '{result.agent_name}'[/yellow]\n"
                )
                title = "Destruction Results (With Errors)"
                color = "yellow"
            else:
                console.print(f"[green]✅ Successfully destroyed resources for agent '{result.agent_name}'[/green]\n")
                title = "Resources Successfully Destroyed"
                color = "green"

        # Show resources removed
        if result.resources_removed:
            resources_text = "\n".join([f"  ✓ {resource}" for resource in result.resources_removed])
            console.print(Panel(resources_text, title=title, border_style=color))
        else:
            console.print(Panel("No resources were found to destroy", title="Results", border_style="yellow"))

        # Show warnings
        if result.warnings:
            warnings_text = "\n".join([f"  ⚠️  {warning}" for warning in result.warnings])
            console.print(Panel(warnings_text, title="Warnings", border_style="yellow"))

        # Show errors
        if result.errors:
            errors_text = "\n".join([f"  ❌ {error}" for error in result.errors])
            console.print(Panel(errors_text, title="Errors", border_style="red"))

        # Next steps
        if not dry_run and not result.errors:
            console.print("\n[dim]Next steps:[/dim]")
            console.print("  • Run 'agentcore configure --entrypoint <file>' to set up a new agent")
            console.print("  • Run 'agentcore launch' to deploy to Bedrock AgentCore")
        elif dry_run:
            console.print("\n[dim]To actually destroy these resources, run:[/dim]")
            destroy_cmd = f"  agentcore destroy{f' --agent {actual_agent_name}' if agent else ''}"
            if delete_ecr_repo:
                destroy_cmd += " --delete-ecr-repo"
            console.print(destroy_cmd)

    except FileNotFoundError:
        console.print("[red].bedrock_agentcore.yaml not found[/red]")
        console.print("Run the following commands to get started:")
        console.print("  1. agentcore configure --entrypoint your_agent.py")
        console.print("  2. agentcore launch")
        console.print('  3. agentcore invoke \'{"message": "Hello"}\'')
        raise typer.Exit(1) from None
    except ValueError as e:
        if "not found" in str(e):
            _handle_error("Agent not found. Use 'agentcore configure list' to see available agents", e)
        else:
            _handle_error(f"Destruction failed: {e}", e)
    except RuntimeError as e:
        _handle_error(f"Destruction failed: {e}", e)
    except Exception as e:
        _handle_error(f"Destruction failed: {e}", e)
