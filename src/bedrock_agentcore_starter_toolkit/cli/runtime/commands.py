"""Bedrock AgentCore CLI - Command line interface for Bedrock AgentCore."""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import typer
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from rich.panel import Panel
from rich.syntax import Syntax

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
        # Validate file exists and is in source directory
        req_file = Path(response.strip()).resolve()
        source_dir = Path(source_path).resolve()

        # Check if requirements file is within source directory
        try:
            if not req_file.is_relative_to(source_dir):
                rel_source = get_relative_path(source_dir)
                console.print(f"[red]Error: Requirements file must be in source directory: {rel_source}[/red]")
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

    if not detected:
        # No fallback prompt - fail with clear error message
        rel_source = get_relative_path(source_dir)
        _handle_error(
            f"No entrypoint file found in {rel_source}\n"
            f"Expected one of: main.py, agent.py, app.py, __main__.py\n"
            f"Please specify full file path (e.g., {rel_source}/your_agent.py)"
        )

    # Show detection and confirm
    rel_entrypoint = get_relative_path(detected)

    _print_success(f"Using entrypoint file: [cyan]{rel_entrypoint}[/cyan]")
    return str(detected)


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
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    region: Optional[str] = typer.Option(None, "--region", "-r"),
    protocol: Optional[str] = typer.Option(None, "--protocol", "-p", help="Server protocol (HTTP or MCP or A2A)"),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-ni", help="Skip prompts; use defaults unless overridden"
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

    # Handle dependency file selection with simplified logic
    final_requirements_file = _handle_requirements_file_display(requirements_file, non_interactive, source_path)

    # Interactive prompts for missing values - clean and elegant
    if not execution_role:
        execution_role = config_manager.prompt_execution_role()

    # Handle ECR repository
    auto_create_ecr = True
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
            container_runtime=container_runtime,
            auto_create_ecr=auto_create_ecr,
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

        execution_role_display = "Auto-create" if not result.execution_role else result.execution_role
        memory_info = "Short-term memory (30-day retention)"
        if disable_memory:
            memory_info = "Disabled"

        console.print(
            Panel(
                f"[bold]Agent Details[/bold]\n"
                f"Agent Name: [cyan]{agent_name}[/cyan]\n"
                f"Runtime: [cyan]{result.runtime}[/cyan]\n"
                f"Region: [cyan]{result.region}[/cyan]\n"
                f"Account: [cyan]{result.account_id}[/cyan]\n\n"
                f"[bold]Configuration[/bold]\n"
                f"Execution Role: [cyan]{execution_role_display}[/cyan]\n"
                f"ECR Repository: [cyan]"
                f"{'Auto-create' if result.auto_create_ecr else result.ecr_repository or 'N/A'}"
                f"[/cyan]\n"
                f"Authorization: [cyan]{auth_info}[/cyan]\n\n"
                f"{headers_info}\n"
                f"Memory: [cyan]{memory_info}[/cyan]\n\n"
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
    local: bool = typer.Option(
        False, "--local", "-l", help="Local build + local runtime - requires Docker/Finch/Podman"
    ),
    local_build: bool = typer.Option(
        False,
        "--local-build",
        "-lb",
        help="Build locally and deploy to cloud runtime - requires Docker/Finch/Podman",
    ),
    auto_update_on_conflict: bool = typer.Option(
        False,
        "--auto-update-on-conflict",
        "-auc",
        help="Automatically update existing agent instead of failing with ConflictException",
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

    🚀 DEFAULT (no flags): CodeBuild + cloud runtime (RECOMMENDED)
       - Build ARM64 containers in the cloud with CodeBuild
       - Deploy to Bedrock AgentCore runtime
       - No local Docker required
       - CHANGED: CodeBuild is now the default (previously required --code-build flag)

    💻 --local: Local build + local runtime
       - Build container locally and run locally
       - requires Docker/Finch/Podman
       - For local development and testing

    🔧 --local-build: Local build + cloud runtime
       - Build container locally with Docker
       - Deploy to Bedrock AgentCore runtime
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
            mode = "codebuild"
            console.print(f"[cyan]🚀 Launching Bedrock AgentCore ({mode} mode - RECOMMENDED)...[/cyan]")
            console.print("[dim]   • Build ARM64 containers in the cloud with CodeBuild[/dim]")
            console.print("[dim]   • No local Docker required[/dim]")
            console.print("[dim]   • Production-ready deployment[/dim]\n")
        else:
            mode = "codebuild"
            console.print(f"[cyan]🚀 Launching Bedrock AgentCore ({mode} mode - RECOMMENDED)...[/cyan]")
            console.print("[dim]   • Build ARM64 containers in the cloud with CodeBuild[/dim]")
            console.print("[dim]   • No local Docker required (DEFAULT behavior)[/dim]")
            console.print("[dim]   • Production-ready deployment[/dim]\n")

            # Show deployment options hint for first-time users
            console.print("[dim]💡 Deployment options:[/dim]")
            console.print("[dim]   • agentcore launch                → CodeBuild (current)[/dim]")
            console.print("[dim]   • agentcore launch --local        → Local development[/dim]")
            console.print("[dim]   • agentcore launch --local-build  → Local build + cloud deploy[/dim]\n")

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
            )

        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config(agent)
        # Handle result based on mode
        if result.mode == "local":
            _print_success(f"Docker image built: {result.tag}")
            _print_success("Ready to run locally")
            console.print("Starting server at http://localhost:8080")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

            if result.runtime is None or result.port is None:
                _handle_error("Unable to launch locally")

            try:
                result.runtime.run_local(result.tag, result.port, result.env_vars)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped[/yellow]")

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
            runtime_logs, _ = get_agent_log_paths(config.bedrock_agentcore.agent_id)
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
                    # memory_info = ""
                    # if hasattr(status_json["config"], "memory_id") and status_json["config"].get("memory_id"):
                    #    memory_type = status_json["config"].get("memory_type", "Short-term")
                    #    memory_id = status_json["config"].get("memory_id")
                    #    memory_info = f"Memory: [cyan]{memory_type}[/cyan] ([dim]{memory_id}[/dim])\n"
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

                    # Add CloudWatch logs information
                    agent_id = status_json.get("config", {}).get("agent_id")
                    if agent_id:
                        try:
                            endpoint_name = endpoint_data.get("name")
                            runtime_logs, otel_logs = get_agent_log_paths(agent_id, endpoint_name)
                            follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)

                            panel_content += f"📋 [cyan]CloudWatch Logs:[/cyan]\n   {runtime_logs}\n   {otel_logs}\n\n"

                            # Only show GenAI Observability Dashboard if OTEL is enabled
                            project_config = load_config(config_path)
                            agent_config = project_config.get_agent_config(agent)
                            if agent_config and agent_config.aws.observability.enabled:
                                panel_content += (
                                    f"🔍 [cyan]GenAI Observability Dashboard:[/cyan]\n"
                                    f"   {get_genai_observability_url(status_json['config']['region'])}\n\n"
                                    f"⏱️  [dim]Note: Observability data may take up to 10 minutes to appear "
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
