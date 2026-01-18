"""Bedrock AgentCore CLI - Command line interface for Bedrock AgentCore.

TODO: This file has grown to 2000+ lines and should be refactored:
- Split individual commands into separate files (configure_command.py, launch_command.py, invoke_command.py, etc.)
- Move shared helper functions to common.py
"""

import json
import logging
import os
from pathlib import Path
from threading import Thread
from typing import List, Optional

import requests
import typer
from rich.panel import Panel
from rich.syntax import Syntax

from ...operations.identity.oauth2_callback_server import start_oauth2_callback_server
from ...operations.runtime import (
    destroy_bedrock_agentcore,
    get_status,
    invoke_bedrock_agentcore,
    launch_bedrock_agentcore,
    list_agents_for_pull,
    pull_agent,
)
from ...services.runtime import _handle_http_response
from ...utils.runtime.config import load_config
from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands, get_genai_observability_url
from ...utils.server_addresses import build_server_urls
from ..common import _handle_error, _print_success, console, requires_aws_creds
from ._configure_impl import configure_impl

# Create a module-specific logger
logger = logging.getLogger(__name__)


# Define options at module level to avoid B008
ENV_OPTION = typer.Option(None, "--env", "-env", help="Environment variables for local mode (format: KEY=VALUE)")

# Configure command group
configure_app = typer.Typer(name="configure", help="Configuration management")


def _show_configuration_not_found_panel():
    """Show standardized configuration not found panel."""
    console.print(
        Panel(
            "⚠️ [yellow]Configuration Not Found[/yellow]\n\n"
            "No agent configuration found in this directory.\n\n"
            "[bold]Get Started:[/bold]\n"
            "   [cyan]agentcore configure --entrypoint your_agent.py[/cyan]\n"
            "   [cyan]agentcore deploy[/cyan]\n"
            '   [cyan]agentcore invoke \'{"prompt": "Hello"}\'[/cyan]',
            title="⚠️ Setup Required",
            border_style="bright_blue",
        )
    )


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
@requires_aws_creds
def configure(
    ctx: typer.Context,
    *,
    create: bool = typer.Option(False, "--create", "-c"),
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
    configure_impl(
        create=create,
        entrypoint=entrypoint,
        agent_name=agent_name,
        execution_role=execution_role,
        code_build_execution_role=code_build_execution_role,
        ecr_repository=ecr_repository,
        s3_bucket=s3_bucket,
        container_runtime=container_runtime,
        requirements_file=requirements_file,
        disable_otel=disable_otel,
        disable_memory=disable_memory,
        authorizer_config=authorizer_config,
        request_header_allowlist=request_header_allowlist,
        vpc=vpc,
        subnets=subnets,
        security_groups=security_groups,
        idle_timeout=idle_timeout,
        max_lifetime=max_lifetime,
        verbose=verbose,
        region=region,
        protocol=protocol,
        non_interactive=non_interactive,
        deployment_type=deployment_type,
        runtime=runtime,
    )


@requires_aws_creds
def deploy(
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
    """Deploy Bedrock AgentCore with three deployment modes (formerly 'launch').

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
    - OLD: agentcore launch --code-build  →  NEW: agentcore deploy
    - OLD: agentcore launch --local       →  NEW: agentcore deploy --local (unchanged)
    - NEW: agentcore deploy --local-build (build locally + deploy to cloud)
    """
    # Handle deprecated --code-build flag
    if code_build:
        console.print("[yellow]⚠️  DEPRECATION WARNING: --code-build flag is deprecated[/yellow]")
        console.print("[yellow]   CodeBuild is now the default deployment method[/yellow]")
        console.print("[yellow]   MIGRATION: Simply use 'agentcore deploy' (no flags needed)[/yellow]")
        console.print("[yellow]   This flag will be removed in a future version[/yellow]\n")

    # Validate mutually exclusive options
    if sum([local, local_build, code_build]) > 1:
        _handle_error("Error: --local, --local-build, and --code-build cannot be used together")

    config_path = Path.cwd() / ".bedrock_agentcore.yaml"

    # Load config early to determine deployment type for proper messaging
    project_config = load_config(config_path)
    if project_config.is_agentcore_create_with_iac:
        _handle_error("This project is configured to deploy via [Terraform | CDK]. No action has been taken.")
    agent_config = project_config.get_agent_config(agent)
    deployment_type = agent_config.deployment_type

    # Validate deployment type compatibility early
    if local_build or force_rebuild_deps:
        if local_build and deployment_type == "direct_code_deploy":
            _handle_error(
                "Error: --local-build is only supported for container deployment type.\n"
                "For direct_code_deploy deployment, use:\n"
                "  • 'agentcore deploy' (default)\n"
                "  • 'agentcore deploy --local' (local execution)"
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
            console.print(f"[dim]   • agentcore deploy                → {mode_name} (current)[/dim]")
            console.print("[dim]   • agentcore deploy --local        → Local development[/dim]")
            if deployment_type == "container":
                console.print("[dim]   • agentcore deploy --local-build  → Local build + cloud deploy[/dim]")
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
            if result.runtime is None or result.port is None:
                _handle_error("Unable to launch locally")

            port = int(result.port)
            console.print("[blue]Starting server at:[/blue]")
            for label, url in build_server_urls(port):
                console.print(f"[blue]  • {label}: {url}[/blue]")
            console.print("Starting OAuth2 3LO callback server at http://localhost:8081")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]\n")

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
            if result.port is None:
                _handle_error("Unable to launch locally")

            port = int(result.port)
            console.print("[blue]Starting server at:[/blue]")
            for label, url in build_server_urls(port):
                console.print(f"[blue]  • {label}: {url}[/blue]")
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
    dev_mode: Optional[bool] = typer.Option(False, "--dev", "-d", help="Send request to local development server"),
    port: Optional[int] = typer.Option(8080, "--port", help="Port for local development server"),
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

    # Handle dev mode - simple HTTP request to development server
    if dev_mode:
        _invoke_dev_server(payload, port)
        return

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
            _show_error_response("Agent not deployed - run 'agentcore deploy' to deploy")
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
                            f"   [cyan]agentcore deploy[/cyan]",
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
                            runtime_logs, otel_logs = get_agent_log_paths(
                                agent_id, endpoint_name, deployment_type=deployment_type
                            )
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
                f"   [cyan]agentcore deploy[/cyan]",
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
                f"   [cyan]agentcore deploy[/cyan]",
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
            console.print("  • Run 'agentcore deploy' to deploy to Bedrock AgentCore")
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
        console.print("  2. agentcore deploy")
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


def _invoke_dev_server(payload: str, port: int = 8080) -> None:
    """Invoke local development server with simple HTTP request."""
    # Try to parse payload as JSON, fallback to wrapping in prompt
    try:
        payload_data = json.loads(payload)
    except json.JSONDecodeError:
        payload_data = {"prompt": payload}

    url = f"http://localhost:{port}/invocations"

    try:
        session = requests.Session()
        with session.post(url, json=payload_data, timeout=180, stream=True) as response:
            console.print("[green]✓ Response from dev server:[/green]")
            result = _handle_http_response(response)
            if result:
                console.print(result)
    except requests.exceptions.ConnectionError:
        console.print(
            Panel(
                "⚠️ [yellow]Development Server Not Found[/yellow]\n\n"
                f"No development server found on http://localhost:{port}\n\n"
                "[bold]Get Started:[/bold]\n"
                "   [cyan]agentcore create myproject[/cyan]\n"
                "   [cyan]cd myproject[/cyan]\n"
                "   [cyan]agentcore dev[/cyan]\n"
                f'   [cyan]agentcore invoke --dev --port {port} "Hello"[/cyan]',
                title="⚠️ Setup Required",
                border_style="bright_blue",
            )
        )
    except Exception as e:
        console.print(f"[red]Error connecting to dev server: {e}[/red]")


@requires_aws_creds
def pull(
    agent_name: Optional[str] = typer.Option(
        None, "--agent-name", "-n", help="Agent name to pull configuration from"
    ),
    agent_id: Optional[str] = typer.Option(
        None, "--agent-id", "-id", help="Agent ID to pull configuration from"
    ),
    region: Optional[str] = typer.Option(
        None, "--region", "-r", help="AWS region where the agent is deployed"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output path for configuration file (default: .bedrock_agentcore.yaml)"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing configuration file"
    ),
):
    """Pull agent configuration from deployed AgentCore runtime.

    This command retrieves the configuration of a deployed AgentCore agent
    and generates a local .bedrock_agentcore.yaml configuration file.

    Use this to:
    - Replicate an agent configuration to a new environment
    - Make modifications to a deployed agent and redeploy
    - Share agent configurations between team members

    Examples:
        # Pull by agent name
        agentcore pull --agent-name my_agent --region us-east-1

        # Pull by agent ID
        agentcore pull --agent-id abc123xyz --region us-east-1

        # Interactive mode (list and select)
        agentcore pull --region us-east-1

        # Force overwrite existing config
        agentcore pull --agent-name my_agent --region us-east-1 --force

    Note:
        After pulling, you must set the entrypoint:
        agentcore configure --entrypoint your_agent.py
    """
    import os

    import questionary

    # Get region from argument or environment
    effective_region = region or os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION")
    if not effective_region:
        _handle_error(
            "Region is required. Provide --region or set AWS_DEFAULT_REGION/AWS_REGION environment variable."
        )

    # Validate mutually exclusive options
    if agent_name and agent_id:
        _handle_error("Cannot specify both --agent-name and --agent-id. Use one or the other.")

    # Set output path
    output_path = Path(output) if output else Path.cwd() / ".bedrock_agentcore.yaml"

    try:
        # Interactive mode if neither agent_name nor agent_id provided
        if not agent_name and not agent_id:
            console.print(f"[cyan]🔍 Fetching agents in {effective_region}...[/cyan]\n")

            agents = list_agents_for_pull(effective_region)

            if not agents:
                console.print(
                    Panel(
                        f"[yellow]No agents found in region {effective_region}[/yellow]\n\n"
                        "Deploy an agent first with:\n"
                        "   [cyan]agentcore configure --entrypoint your_agent.py[/cyan]\n"
                        "   [cyan]agentcore deploy[/cyan]",
                        title="No Agents Found",
                        border_style="yellow",
                    )
                )
                raise typer.Exit(1)

            # Display agents and let user select
            console.print(f"[bold]Found {len(agents)} agent(s):[/bold]\n")

            choices = []
            for i, agent in enumerate(agents, 1):
                status_color = "green" if agent["status"] == "READY" else "yellow"
                created = agent.get("created_at", "Unknown")
                if hasattr(created, "strftime"):
                    created = created.strftime("%Y-%m-%d")
                display = f"[{i}] {agent['name']} ({agent['status']}) - Created: {created}"
                choices.append({"name": display, "value": agent})
                console.print(f"  [{status_color}][{i}][/{status_color}] {agent['name']} "
                              f"([{status_color}]{agent['status']}[/{status_color}]) - Created: {created}")

            console.print()

            # Use questionary for selection
            selected = questionary.select(
                "Select agent to pull:",
                choices=[c["name"] for c in choices],
            ).ask()

            if selected is None:
                console.print("[yellow]Pull cancelled.[/yellow]")
                raise typer.Exit(0)

            # Extract selected agent
            selected_idx = next(i for i, c in enumerate(choices) if c["name"] == selected)
            selected_agent = choices[selected_idx]["value"]
            agent_id = selected_agent["id"]

        # Execute pull
        console.print("[cyan]🔍 Pulling agent configuration from AgentCore...[/cyan]\n")

        with console.status("[bold]Pulling configuration...[/bold]"):
            result = pull_agent(
                region=effective_region,
                agent_name=agent_name,
                agent_id=agent_id,
                output_path=output_path,
                force=force,
            )

        # Show success panel
        deployment_info = result.deployment_type
        if result.runtime_type:
            deployment_info += f" ({result.runtime_type})"

        panel_content = (
            f"[bold]Agent Details:[/bold]\n"
            f"Agent Name:    [cyan]{result.agent_name}[/cyan]\n"
            f"Agent ID:      [cyan]{result.agent_id}[/cyan]\n"
            f"Region:        [cyan]{result.region}[/cyan]\n"
            f"Deployment:    [cyan]{deployment_info}[/cyan]\n"
            f"Network:       [cyan]{result.network_mode}[/cyan]\n"
            f"Protocol:      [cyan]{result.protocol}[/cyan]\n"
            f"Config File:   [cyan]{result.config_path}[/cyan]"
        )

        console.print(
            Panel(
                panel_content,
                title="✅ Successfully Pulled Configuration",
                border_style="green",
            )
        )

        # Show warnings if any
        if result.has_warnings:
            warning_lines = []

            if result.env_var_keys:
                warning_lines.append("[bold]Environment Variables (keys only - values not pulled):[/bold]")
                for key in result.env_var_keys:
                    warning_lines.append(f"   • {key}")
                warning_lines.append("   Set values with: [cyan]agentcore deploy --env KEY=value[/cyan]\n")

            if result.has_memory:
                warning_lines.append("[bold]Memory Configuration Not Pulled:[/bold]")
                warning_lines.append(f"   This agent uses AgentCore Memory ({result.memory_id}).")
                warning_lines.append("   To enable memory: [cyan]agentcore configure --memory-mode STM_ONLY[/cyan]")

            console.print(
                Panel(
                    "\n".join(warning_lines),
                    title="⚠️  Limitations",
                    border_style="yellow",
                )
            )

        # Show required setup
        console.print(
            Panel(
                "[bold]Entrypoint not set.[/bold]\n\n"
                "Run the following to set your agent file:\n"
                "   [cyan]agentcore configure --entrypoint your_agent.py[/cyan]",
                title="📝 Required Setup",
                border_style="blue",
            )
        )

        # Show next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("   1. Set entrypoint: [cyan]agentcore configure --entrypoint <file>[/cyan]")
        if result.env_var_keys:
            console.print("   2. Set environment variable values")
        if result.has_memory:
            console.print("   3. Configure memory if needed")
        console.print(f"   {3 if not result.has_warnings else 4}. Deploy: [cyan]agentcore deploy[/cyan]")

    except FileExistsError as e:
        console.print(
            Panel(
                f"[red]{str(e)}[/red]\n\n"
                f"To overwrite, use:\n"
                f"   [cyan]agentcore pull --force{' --agent-name ' + agent_name if agent_name else ''}"
                f"{' --agent-id ' + agent_id if agent_id else ''} --region {effective_region}[/cyan]",
                title="❌ Pull Failed",
                border_style="red",
            )
        )
        raise typer.Exit(1) from e
    except ValueError as e:
        console.print(
            Panel(
                f"[red]{str(e)}[/red]",
                title="❌ Pull Failed",
                border_style="red",
            )
        )
        raise typer.Exit(1) from e
    except Exception as e:
        if not isinstance(e, typer.Exit):
            _handle_error(f"Pull failed: {e}", e)
