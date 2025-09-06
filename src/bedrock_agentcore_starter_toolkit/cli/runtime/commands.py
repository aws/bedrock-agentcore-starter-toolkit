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
    get_status,
    invoke_bedrock_agentcore,
    launch_bedrock_agentcore,
    validate_agent_name,
)
from ...utils.runtime.entrypoint import parse_entrypoint
from ..common import _handle_error, _print_success, console
from .configuration_manager import ConfigurationManager

# Create a module-specific logger
logger = logging.getLogger(__name__)


def _validate_requirements_file(file_path: str) -> str:
    """Validate requirements file and return the path."""
    from ...utils.runtime.entrypoint import validate_requirements_file

    try:
        deps = validate_requirements_file(Path.cwd(), file_path)
        _print_success(f"Using requirements file: [dim]{deps.resolved_path}[/dim]")
        return file_path
    except (FileNotFoundError, ValueError) as e:
        _handle_error(str(e), e)


def _prompt_for_requirements_file(prompt_text: str, default: str = "") -> Optional[str]:
    """Prompt user for requirements file path with validation."""
    response = prompt(prompt_text, completer=PathCompleter(), default=default)

    if response.strip():
        return _validate_requirements_file(response.strip())

    return None


def _handle_requirements_file_display(requirements_file: Optional[str]) -> Optional[str]:
    """Handle requirements file with display logic for CLI."""
    from ...utils.runtime.entrypoint import detect_dependencies

    if requirements_file:
        # User provided file - validate and show confirmation
        return _validate_requirements_file(requirements_file)

    # Auto-detection with interactive prompt
    deps = detect_dependencies(Path.cwd())

    if deps.found:
        console.print(f"\n🔍 [cyan]Detected dependency file:[/cyan] [bold]{deps.file}[/bold]")
        console.print("[dim]Press Enter to use this file, or type a different path (use Tab for autocomplete):[/dim]")

        result = _prompt_for_requirements_file("Path or Press Enter to use detected dependency file: ", default="")

        if result is None:
            # Use detected file
            _print_success(f"Using detected file: [dim]{deps.file}[/dim]")

        return result
    else:
        console.print("\n[yellow]⚠️  No dependency file found (requirements.txt or pyproject.toml)[/yellow]")
        console.print("[dim]Enter path to requirements file (use Tab for autocomplete), or press Enter to skip:[/dim]")

        result = _prompt_for_requirements_file("Path: ")

        if result is None:
            _handle_error("No requirements file specified and none found automatically")

        return result


# Define options at module level to avoid B008
ENV_OPTION = typer.Option(None, "--env", "-env", help="Environment variables for local mode (format: KEY=VALUE)")

# Configure command group
configure_app = typer.Typer(name="configure", help="Configuration management")


@configure_app.command("list")
def list_agents():
    """List configured agents."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    try:
        from ...utils.runtime.config import load_config

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
    entrypoint: Optional[str] = typer.Option(None, "--entrypoint", "-e", help="Python file with BedrockAgentCoreApp"),
    agent_name: Optional[str] = typer.Option(None, "--name", "-n"),
    execution_role: Optional[str] = typer.Option(None, "--execution-role", "-er"),
    ecr_repository: Optional[str] = typer.Option(None, "--ecr", "-ecr"),
    container_runtime: Optional[str] = typer.Option(None, "--container-runtime", "-ctr"),
    requirements_file: Optional[str] = typer.Option(
        None, "--requirements-file", "-rf", help="Path to requirements file"
    ),
    disable_otel: bool = typer.Option(False, "--disable-otel", "-do", help="Disable OpenTelemetry"),
    authorizer_config: Optional[str] = typer.Option(
        None, "--authorizer-config", "-ac", help="OAuth authorizer configuration as JSON string"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    region: Optional[str] = typer.Option(None, "--region", "-r"),
    protocol: Optional[str] = typer.Option(None, "--protocol", "-p", help="Server protocol (HTTP or MCP)"),
):
    """Configure a Bedrock AgentCore agent. The agent name defaults to your Python file name."""
    if ctx.invoked_subcommand is not None:
        return

    if not entrypoint:
        _handle_error("--entrypoint is required")

    if protocol and protocol.upper() not in ["HTTP", "MCP"]:
        _handle_error("Error: --protocol must be either HTTP or MCP")

    console.print("[cyan]Configuring Bedrock AgentCore...[/cyan]")
    try:
        _, file_name = parse_entrypoint(entrypoint)
        agent_name = agent_name or file_name

        valid, error = validate_agent_name(agent_name)
        if not valid:
            _handle_error(error)

        console.print(f"[dim]Agent name: {agent_name}[/dim]")
    except ValueError as e:
        _handle_error(f"Error: {e}", e)

    # Create configuration manager for clean, elegant prompting
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    config_manager = ConfigurationManager(config_path)

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

    # Handle dependency file selection with simplified logic
    final_requirements_file = _handle_requirements_file_display(requirements_file)

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

    try:
        result = configure_bedrock_agentcore(
            agent_name=agent_name,
            entrypoint_path=Path(entrypoint),
            execution_role=execution_role,
            ecr_repository=ecr_repository,
            container_runtime=container_runtime,
            auto_create_ecr=auto_create_ecr,
            enable_observability=not disable_otel,
            requirements_file=final_requirements_file,
            authorizer_configuration=oauth_config,
            verbose=verbose,
            region=region,
            protocol=protocol.upper() if protocol else None,
        )

        # Prepare authorization info for summary
        auth_info = "IAM (default)"
        if oauth_config:
            auth_info = "OAuth (customJWTAuthorizer)"

        console.print(
            Panel(
                f"[green]Configuration Summary[/green]\n\n"
                f"Name: {agent_name}\n"
                f"Runtime: {result.runtime}\n"
                f"Region: {result.region}\n"
                f"Account: {result.account_id}\n"
                f"Execution Role: {result.execution_role}\n"
                f"ECR: {'Auto-create' if result.auto_create_ecr else result.ecr_repository or 'N/A'}\n"
                f"Authorization: {auth_info}\n\n"
                f"Configuration saved to: {result.config_path}",
                title="Bedrock AgentCore Configured",
                border_style="green",
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
        False, "--local", "-l", help="Build locally and run container locally - requires Docker/Finch/Podman"
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
            _print_success(f"CodeBuild completed: [cyan]{result.codebuild_id}[/cyan]")
            _print_success(f"ARM64 image pushed to ECR: [cyan]{result.ecr_uri}:latest[/cyan]")

            # Show deployment success panel
            agent_name = result.tag.split(":")[0].replace("bedrock_agentcore-", "")
            deploy_panel = (
                f"[green]CodeBuild ARM64 Deployment Successful![/green]\n\n"
                f"Agent Name: {agent_name}\n"
                f"CodeBuild ID: [cyan]{result.codebuild_id}[/cyan]\n"
                f"Agent ARN: [cyan]{result.agent_arn}[/cyan]\n"
                f"ECR URI: [cyan]{result.ecr_uri}:latest[/cyan]\n\n"
                f"ARM64 container deployed to Bedrock AgentCore.\n\n"
                f"You can now check the status of your Bedrock AgentCore endpoint with:\n"
                f"[cyan]agentcore status[/cyan]\n\n"
                f"You can now invoke your Bedrock AgentCore endpoint with:\n"
                f'[cyan]agentcore invoke \'{{"prompt": "Hello"}}\'[/cyan]'
            )

            # Add log information if we have agent_id
            if result.agent_id:
                from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands

                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id)
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                deploy_panel += (
                    f"\n\n📋 [cyan]Agent logs available at:[/cyan]\n"
                    f"   {runtime_logs}\n"
                    f"   {otel_logs}\n\n"
                    f"💡 [dim]Tail logs with:[/dim]\n"
                    f"   {follow_cmd}\n"
                    f"   {since_cmd}"
                )

            console.print(
                Panel(
                    deploy_panel,
                    title="CodeBuild Deployment Complete",
                    border_style="green",
                )
            )

        else:  # cloud mode (either CodeBuild default or local-build)
            _print_success(f"Image pushed to ECR: [cyan]{result.ecr_uri}:latest[/cyan]")

            # Show deployment success panel
            agent_name = result.tag.split(":")[0].replace("bedrock_agentcore-", "")

            # Determine deployment type for panel title
            if local_build:
                title = "Local Build Deployment Complete"
                deployment_type = "Local Docker Build Deployment Successful!"
            else:
                title = "CodeBuild Deployment Complete"
                deployment_type = "CodeBuild Deployment Successful!"

            deploy_panel = (
                f"[green]{deployment_type}[/green]\n\n"
                f"Agent Name: {agent_name}\n"
                f"Agent ARN: [cyan]{result.agent_arn}[/cyan]\n"
                f"ECR URI: [cyan]{result.ecr_uri}[/cyan]\n\n"
                f"You can now check the status of your Bedrock AgentCore endpoint with:\n"
                f"[cyan]agentcore status[/cyan]\n\n"
                f"You can now invoke your Bedrock AgentCore endpoint with:\n"
                f'[cyan]agentcore invoke \'{{"prompt": "Hello"}}\'[/cyan]'
            )

            # Add log information if we have agent_id
            if result.agent_id:
                from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands

                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id)
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                deploy_panel += (
                    f"\n\n📋 [cyan]Agent logs available at:[/cyan]\n"
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
                    border_style="green",
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
):
    """Invoke Bedrock AgentCore endpoint."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    try:
        from ...utils.runtime.config import load_config

        # Load project configuration to check if auth is configured
        project_config = load_config(config_path)
        config = project_config.get_agent_config(agent)

        # Parse payload
        try:
            payload_data = json.loads(payload)
        except json.JSONDecodeError:
            payload_data = {"message": payload}

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

        # Display payload
        console.print("[bold]Payload:[/bold]")
        console.print(
            Syntax(
                json.dumps(payload_data, indent=2, ensure_ascii=False),
                "json",
                background_color="default",
                word_wrap=True,
            )
        )

        # Invoke
        result = invoke_bedrock_agentcore(
            config_path=config_path,
            payload=payload_data,
            agent_name=agent,
            session_id=session_id,
            bearer_token=final_bearer_token,
            user_id=user_id,
            local_mode=local_mode,
        )
        console.print(f"Session ID: [cyan]{result.session_id}[/cyan]")
        if result.response != {}:
            console.print("\n[bold]Response:[/bold]")
            console.print(
                Syntax(
                    json.dumps(result.response, indent=2, default=str, ensure_ascii=False),
                    "json",
                    background_color="default",
                    word_wrap=True,
                )
            )

    except FileNotFoundError:
        console.print("[red].bedrock_agentcore.yaml not found[/red]")
        console.print("Run the following commands to get started:")
        console.print("  1. agentcore configure --entrypoint your_agent.py")
        console.print("  2. agentcore launch")
        console.print('  3. agentcore invoke \'{"message": "Hello"}\'')
        raise typer.Exit(1) from None
    except ValueError as e:
        if "not deployed" in str(e):
            console.print("[yellow]Agent not deployed yet[/yellow]")
            console.print("Deploy your agent first:")
            console.print("  agentcore launch                    # Deploy to AWS (recommended)")
            console.print("  agentcore launch --local            # Run locally")
            console.print("Then check status: agentcore status")
            _handle_error("Bedrock AgentCore not deployed. Run 'bedrock_agentcore launch' first", e)
        else:
            _handle_error(f"Invocation failed: {e}", e)
    except Exception as e:
        _handle_error(f"Invocation failed: {e}", e)


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
                            f"[green]Status of the current Agent:[/green]\n\n"
                            f"[green]Agent Name: {status_json['config']['name']}[/green]\n"
                            f"[cyan]Configuration details:[/cyan]\n"
                            f"[cyan]- region: {status_json['config']['region']}[/cyan]\n"
                            f"[cyan]- account: {status_json['config']['account']}[/cyan]\n"
                            f"[cyan]- execution role: {status_json['config']['execution_role']}[/cyan]\n"
                            f"[cyan]- ecr repository: {status_json['config']['ecr_repository']}[/cyan]\n",
                            title="Bedrock AgentCore Agent Status",
                            border_style="green",
                        )
                    )

                    console.print(
                        Panel(
                            "[yellow]Agent is configured, but not launched yet. "
                            "Please use `agentcore launch` to launch the agent. [/yellow]\n\n",
                            title="Bedrock AgentCore Agent Status",
                            border_style="yellow",
                        )
                    )

                elif "agent" in status_json and status_json["agent"] is not None:
                    agent_data = status_json["agent"]
                    console.print(
                        Panel(
                            f"[green]Status of the current Agent:[/green]\n\n"
                            f"[green]Agent Name: {status_json['config']['name']}[/green]\n"
                            f"[green]Agent ID: {status_json['config']['agent_id']}[/green]\n"
                            f"[green]Agent Arn: {status_json['config']['agent_arn']}[/green]\n"
                            f"[green]Created at: {agent_data.get('createdAt', 'Not available')}[/green]\n"
                            f"[green]Last Updated at: {agent_data.get('lastUpdatedAt', 'Not available')}[/green]\n"
                            f"[cyan]Configuration details:[/cyan]\n"
                            f"[cyan]- region: {status_json['config']['region']}[/cyan]\n"
                            f"[cyan]- account: {status_json['config'].get('account', 'Not available')}[/cyan]\n"
                            f"[cyan]- execution role: "
                            f"{status_json['config'].get('execution_role', 'Not available')}[/cyan]\n"
                            f"[cyan]- ecr repository: "
                            f"{status_json['config'].get('ecr_repository', 'Not available')}[/cyan]\n",
                            title="Bedrock AgentCore Agent Status",
                            border_style="green",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            "[green]Please launch agent first![/green]\n\n",
                            title="Bedrock AgentCore Agent Status",
                            border_style="yellow",
                        )
                    )

                if "endpoint" in status_json and status_json["endpoint"] is not None:
                    endpoint_data = status_json["endpoint"]
                    console.print(
                        Panel(
                            f"[green]Status of the current Endpoint:[/green]\n\n"
                            f"[green]Endpoint Id: {endpoint_data.get('id', 'Not available')}[/green]\n"
                            f"[green]Endpoint Name: {endpoint_data.get('name', 'Not available')}[/green]\n"
                            f"[green]Endpoint Arn: "
                            f"{endpoint_data.get('agentRuntimeEndpointArn', 'Not available')}[/green]\n"
                            f"[green]Agent Arn: {endpoint_data.get('agentRuntimeArn', 'Not available')}[/green]\n"
                            f"[green]STATUS: [cyan]{endpoint_data.get('status', 'Unknown')}[/cyan][/green]\n"
                            f"[green]Last Updated at: "
                            f"{endpoint_data.get('lastUpdatedAt', 'Not available')}[/green]\n",
                            title="Bedrock AgentCore Endpoint Status",
                            border_style="green",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            "[yellow]Please launch agent first and make sure endpoint status is READY "
                            "before invoking![/yellow]\n\n",
                            title="Bedrock AgentCore Endpoint Status",
                            border_style="yellow",
                        )
                    )

                # Show log information
                agent_id = status_json.get("config", {}).get("agent_id")
                if agent_id:
                    try:
                        from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands

                        endpoint_name = status_json.get("endpoint", {}).get("name")

                        runtime_logs, otel_logs = get_agent_log_paths(agent_id, endpoint_name)
                        follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)

                        console.print("\n📋 [cyan]Agent logs available at:[/cyan]")
                        console.print(f"   {runtime_logs}")
                        console.print(f"   {otel_logs}")
                        console.print("\n💡 [dim]Tail logs with:[/dim]")
                        console.print(f"   {follow_cmd}")
                        console.print(f"   {since_cmd}")
                    except (ValueError, TypeError) as e:
                        # If logging info fails, log the error and continue
                        logger.debug("Failed to display log paths: %s", str(e))
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
        console.print("[yellow]Configuration not found[/yellow]")
        console.print("Run the following commands to get started:")
        console.print("  1. agentcore configure --entrypoint your_agent.py")
        console.print("  2. agentcore launch")
        console.print('  3. agentcore invoke \'{"message": "Hello"}\'')
        raise typer.Exit(1) from None
    except ValueError as e:
        _handle_error(f"Status failed: {e}", e)
    except Exception as e:
        _handle_error(f"Status failed: {e}", e)


def destroy(
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Agent name (use 'agentcore configure list' to see available agents)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be destroyed without actually destroying anything"
    ),
    force: bool = typer.Option(
        False, "--force", help="Skip confirmation prompts and destroy immediately"
    ),
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
        from ...utils.runtime.config import load_config

        # Load project configuration to get agent details
        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config(agent)
        
        if not agent_config:
            _handle_error(f"Agent '{agent or 'default'}' not found in configuration")
            
        actual_agent_name = agent_config.name

        # Show what will be destroyed
        if dry_run:
            console.print(f"[cyan]🔍 Dry run: Preview of resources that would be destroyed for agent '{actual_agent_name}'[/cyan]\n")
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
                console.print(f"[yellow]⚠️  Destruction completed with errors for agent '{result.agent_name}'[/yellow]\n")
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
            console.print(f"\n[dim]To actually destroy these resources, run:[/dim]")
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
