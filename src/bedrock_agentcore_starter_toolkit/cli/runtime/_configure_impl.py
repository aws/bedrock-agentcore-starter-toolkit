import json
from pathlib import Path
from typing import Optional

from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from rich.panel import Panel

from ...operations.runtime import (
    configure_bedrock_agentcore,
    detect_entrypoint,
    detect_requirements,
    get_relative_path,
    infer_agent_name,
    validate_agent_name,
)
from ...utils.aws import get_account_id
from ...utils.runtime.config import load_config, load_config_if_exists
from ..common import _handle_error, _print_success, console
from .configuration_manager import ConfigurationManager


def configure_impl(
    *,
    create=False,
    entrypoint=None,
    agent_name=None,
    execution_role=None,
    code_build_execution_role=None,
    ecr_repository=None,
    s3_bucket=None,
    container_runtime=None,
    requirements_file=None,
    disable_otel=False,
    disable_memory=False,
    authorizer_config=None,
    request_header_allowlist=None,
    vpc=False,
    subnets=None,
    security_groups=None,
    idle_timeout=None,
    max_lifetime=None,
    verbose=False,
    region=None,
    protocol=None,
    non_interactive=False,
    deployment_type=None,
    runtime=None,
):
    # Create configuration manager early for consistent prompting
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    config_manager = ConfigurationManager(config_path, non_interactive)

    # fail running config on an iac created project
    existing_config = load_config_if_exists(config_path=config_path, autofill_missing_aws=False)
    if existing_config and existing_config.is_agentcore_create_with_iac:
        _handle_error(
            "Error: Cannot configure a project created with agentcore create monorepo mode"
            "Create a new project monorepo project to provide configure settings"
        )
    # try an operation requiring credentials upfront, so we don't start interactive mode and then fail later.
    try:
        get_account_id()
    except Exception:
        _handle_error("agentcore configure requires valid aws credentials to run successfully.")

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

    # create mode configuration is only passed by CLI
    create_mode_enabled = create

    # Existing agent created via create flow
    is_agentcore_create_agent = (
        existing_config.agents[existing_config.default_agent].is_generated_by_agentcore_create
        if existing_config and existing_config.default_agent in existing_config.agents
        else False
    )

    # If existing create-flow agent detected, use its configuration and inform user
    if is_agentcore_create_agent:
        existing_agent_config = existing_config.agents[existing_config.default_agent]

        console.print(
            Panel(
                f"[bold]Agent:[/bold] {existing_agent_config.name}\n"
                f"[bold]Entrypoint:[/bold] {existing_agent_config.entrypoint}\n"
                f"[bold]Source Path:[/bold] {existing_agent_config.source_path}\n\n"
                "[yellow]Continuing may overwrite your existing configuration for: "
                "deployment type, memory, request headers, VPC, authorizer, and other settings.\n\n"
                "Press Ctrl+C to cancel if you want to keep your current configuration.[/yellow]",
                title="Existing Agent Detected",
                border_style="cyan",
            )
        )

        # Use values from existing config
        entrypoint = existing_agent_config.entrypoint
        agent_name = existing_agent_config.name
        source_path = existing_agent_config.source_path or "."
        # Skip requirements prompt for create-flow agents
        final_requirements_file = None

    # Interactive entrypoint selection (skip if existing create-flow agent)
    if not is_agentcore_create_agent:
        if not entrypoint:
            if non_interactive or create_mode_enabled:
                entrypoint_input = "."
            else:
                console.print("\n📂 [cyan]Entrypoint Selection[/cyan]")
                console.print("[dim]Specify the entry point (use Tab for autocomplete):[/dim]")
                console.print("[dim]  • File path: weather/agent.py[/dim]")
                console.print("[dim]  • Directory: weather/ (auto-detects main.py, agent.py, app.py)[/dim]")
                console.print("[dim]  • Current directory: press Enter[/dim]")

                entrypoint_input = (
                    prompt("Entrypoint: ", completer=PathCompleter(), complete_while_typing=True, default="").strip()
                    or "."
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

        if create_mode_enabled:
            entrypoint = entrypoint_input
            source_path = "."
        elif entrypoint_path.is_file():
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
            entrypoint_path = Path(entrypoint_input).resolve()
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

        # Infer agent name from full entrypoint path (e.g., agents/writer/main.py -> agents_writer_main)
        if not agent_name:
            if create_mode_enabled:
                suggested_name = "create_agent"
            else:
                entrypoint_path = Path(entrypoint)
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
    # Skip for create mode and existing create-flow agents (already set to None above)
    if create_mode_enabled:
        final_requirements_file = None
    elif not is_agentcore_create_agent:
        final_requirements_file = _handle_requirements_file_display(requirements_file, non_interactive, source_path)

    def _validate_cli_args(
        deployment_type, runtime, ecr_repository, s3_bucket, direct_code_deploy_available, prereq_error
    ):
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
        # create only supports container currently
        if create_mode_enabled:
            console.print("Create mode only uses the container deployment type.")
            return "container", None

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
                console.print(
                    f"[yellow]Direct Code Deploy unavailable ({prereq_error}), using Container deployment[/yellow]"
                )
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
        if create_mode_enabled:
            execution_role = None
        else:
            execution_role = config_manager.prompt_execution_role()

    if deployment_type == "container":
        if ecr_repository and ecr_repository.lower() == "auto":
            # User explicitly requested auto-creation
            ecr_repository = None
            auto_create_ecr = True
            _print_success("Will auto-create ECR repository")
        elif not ecr_repository:
            if create_mode_enabled:
                auto_create_ecr = False
            else:
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
            create_mode_enabled=create_mode_enabled,
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
            is_generated_by_agentcore_create=is_agentcore_create_agent,
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
                f"[cyan]agentcore launch[/cyan]{' [cyan]agentcore create[/cyan]' if create_mode_enabled else ''}",
                title="Configuration Success",
                border_style="bright_blue",
            )
        )

    except ValueError as e:
        # Handle validation errors from core layer
        _handle_error(str(e), e)
    except Exception as e:
        _handle_error(f"Configuration failed: {e}", e)


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
