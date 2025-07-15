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
    local: bool = typer.Option(False, "--local", "-l", help="Run locally"),
    push_ecr: bool = typer.Option(False, "--push-ecr", "-p", help="Build and push to ECR only (no deployment)"),
    envs: List[str] = typer.Option(  # noqa: B008
        None, "--env", "-env", help="Environment variables for agent (format: KEY=VALUE)"
    ),
):
    """Launch Bedrock AgentCore locally or to cloud."""
    # Validate mutually exclusive options
    if local and push_ecr:
        _handle_error("Error: --local and --push-ecr cannot be used together")

    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    try:
        # Show launch mode
        if local:
            mode = "local"
        elif push_ecr:
            mode = "push-ecr"
        else:
            mode = "cloud"

        console.print(f"[cyan]Launching Bedrock AgentCore ({mode} mode)...[/cyan]\n")

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

            # Call the operation
            result = launch_bedrock_agentcore(
                config_path=config_path,
                agent_name=agent,
                local=local,
                push_ecr_only=push_ecr,
                env_vars=env_vars,
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

        elif result.mode == "push-ecr":
            _print_success(f"Image pushed to ECR: [cyan]{result.ecr_uri}:latest[/cyan]")
            console.print(
                Panel(
                    f"[green]ECR Push Successful![/green]\n\n"
                    f"Image: [cyan]{result.tag}[/cyan]\n"
                    f"ECR URI: [cyan]{result.ecr_uri}:latest[/cyan]\n\n"
                    f"Your image is now available in ECR.\n"
                    f"Run [cyan]agentcore launch[/cyan] to deploy to Bedrock AgentCore.",
                    title="Push to ECR Complete",
                    border_style="green",
                )
            )

        else:  # cloud mode
            _print_success(f"Image pushed to ECR: [cyan]{result.ecr_uri}:latest[/cyan]")

            # Show deployment success panel
            agent_name = result.tag.split(":")[0].replace("bedrock_agentcore-", "")
            deploy_panel = (
                f"[green]Deployment Successful![/green]\n\n"
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
                    title="Bedrock AgentCore Deployed",
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
        console.print(Syntax(json.dumps(payload_data, indent=2), "json", background_color="default", word_wrap=True))

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
        console.print("\n[bold]Response:[/bold]")
        console.print(
            Syntax(
                json.dumps(result.response, indent=2, default=str), "json", background_color="default", word_wrap=True
            )
        )

    except FileNotFoundError:
        _handle_error(".bedrock_agentcore.yaml not found. Run 'bedrock_agentcore configure --entrypoint <file>' first")
    except ValueError as e:
        if "not deployed" in str(e):
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
                print(f"Getting Status for {status_json['config']['name']}")

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
                    json.dumps(status_json, indent=2, default=str), "json", background_color="default", word_wrap=True
                )
            )

    except FileNotFoundError:
        _handle_error(".bedrock_agentcore.yaml not found. Run 'bedrock_agentcore configure --entrypoint <file>' first")
    except ValueError as e:
        _handle_error(f"Status failed: {e}", e)
    except Exception as e:
        _handle_error(f"Status failed: {e}", e)
