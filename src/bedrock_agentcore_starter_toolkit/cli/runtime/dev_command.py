"""Development server command for Bedrock AgentCore CLI."""

import logging
import os
import socket
import subprocess  # nosec B404 - subprocess required for running uvicorn dev server
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer

from ...utils.runtime.config import load_config, load_config_if_exists
from ..common import _handle_error, _handle_warn, assert_valid_aws_creds_or_exit, console

logger = logging.getLogger(__name__)

# Default module path when config is unavailable or invalid
DEFAULT_MODULE_PATH = "src.main:app"


def dev(
    port: Optional[int] = typer.Option(None, "--port", "-p", help="Port for development server (default: 8080)"),
    envs: List[str] = typer.Option(  # noqa: B008
        None, "--env", "-env", help="Environment variables for agent (format: KEY=VALUE)"
    ),
):
    """Start a local development server for your agent with hot reloading."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    _assert_aws_creds_if_required(config_path)
    module_path, agent_name = _get_module_path_and_agent_name(config_path)

    # Setup environment and port
    local_env, port_changed, requested_port_val = _setup_dev_environment(envs, port, config_path)
    devPort = local_env["PORT"]

    console.print("[green]🚀 Starting development server with hot reloading[/green]")
    console.print(f"[blue]Agent: {agent_name}[/blue]")
    console.print(f"[blue]Module: {module_path}[/blue]")

    if port_changed:
        console.print(f"[yellow]⚠️  Port {requested_port_val} is already in use[/yellow]")
        console.print(f"[green]✓ Using port {devPort} instead[/green]")

    console.print(f"[blue]Server will be available at: http://localhost:{devPort}/invocations[/blue]")

    if port_changed:
        console.print(
            f'[cyan]💡 Test your agent with: agentcore invoke --dev --port {devPort} "Hello" '
            "in a new terminal window[/cyan]"
        )
    else:
        console.print('[cyan]💡 Test your agent with: agentcore invoke --dev "Hello" in a new terminal window[/cyan]')

    console.print("[green]ℹ️  This terminal window will be used to run the dev server [/green]")
    console.print("[yellow]Press Ctrl+C to stop the server[/yellow]\n")

    cmd = [
        "uv",
        "run",
        "uvicorn",
        module_path,
        "--reload",
        "--host",
        "0.0.0.0",  # nosec B104 - dev server intentionally binds to all interfaces
        "--port",
        str(devPort),
        "--log-level",
        "info",
    ]

    process = None
    try:
        process = subprocess.Popen(cmd, env=local_env)  # nosec B603 - cmd args are hardcoded uv/uvicorn commands, not user input
        process.wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down development server...[/yellow]")
        _cleanup_process(process)
        console.print("[green]Development server stopped[/green]")
    except Exception as e:
        _cleanup_process(process)
        _handle_error(f"Failed to start development server: {e}")


def _get_module_path_and_agent_name(config_path: Path) -> tuple[str, str]:
    """Get module path and agent name, handling missing YAML gracefully."""
    has_config, has_default_entrypoint = _ensure_config(config_path)

    # Try to load config if it exists
    if has_config:
        try:
            project_config = load_config(config_path, autofill_missing_aws=False)
            agent_config = project_config.get_agent_config()
            if agent_config and agent_config.entrypoint:
                module_path = _get_module_path_from_config(config_path, agent_config)
                return module_path, agent_config.name

            console.print(
                f"[yellow]⚠️ No agent entrypoint specified in configuration, using default module path: "
                f"{DEFAULT_MODULE_PATH}[/yellow]"
            )
            return DEFAULT_MODULE_PATH, "default"
        except Exception as e:
            if not has_default_entrypoint:
                _handle_error(f"Failed to load configuration and no default entrypoint found: {e}")
            console.print(
                f"[yellow]⚠️ Error loading config: {e}, using default module path: {DEFAULT_MODULE_PATH}[/yellow]"
            )
            return DEFAULT_MODULE_PATH, "default"

    # Fall back to default - must have default entrypoint here
    console.print(f"[yellow]⚠️ No configuration file found, using default module path: {DEFAULT_MODULE_PATH}[/yellow]")
    return DEFAULT_MODULE_PATH, "default"


def _get_env_vars(config_path: Path) -> Dict[str, str]:
    env_vars = dict()
    if not config_path.exists():
        return env_vars

    try:
        project_config = load_config(config_path, autofill_missing_aws=False)
        agent_config = project_config.get_agent_config()
        if agent_config and agent_config.memory and agent_config.memory.memory_id:
            env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] = agent_config.memory.memory_id
        if agent_config and agent_config.aws and agent_config.aws.region:
            env_vars["AWS_REGION"] = agent_config.aws.region
    except Exception as e:
        _handle_warn(f"Failed to load configuration: {e}")
        return env_vars
    return env_vars


def _ensure_config(config_path: Path) -> Tuple[bool, bool]:
    """Ensure that project configuration and entrypoint file are defined."""
    has_config = config_path.exists()
    has_default_entrypoint = Path("src/main.py").exists()

    # Fail fast if no project found
    if not has_config and not has_default_entrypoint:
        _handle_error(
            "No agent project found in current directory.\n\n"
            "Expected either:\n"
            "  • .bedrock_agentcore.yaml configuration file, or\n"
            "  • src/main.py entrypoint file\n\n"
            "Run 'agentcore dev' from your agent project directory."
        )

    return has_config, has_default_entrypoint


def _get_module_path_from_config(config_path: Path, agent_config) -> str:
    """Convert config entrypoint to Python module path for uvicorn."""
    entrypoint_path = Path(agent_config.entrypoint.strip())

    if entrypoint_path.is_dir():
        entrypoint_path = entrypoint_path / "main.py"

    project_root = config_path.parent
    try:
        relative_path = entrypoint_path.relative_to(project_root)
        module_path = ".".join(relative_path.with_suffix("").parts)
        return f"{module_path}:app"
    except ValueError:
        return f"{entrypoint_path.stem}:app"


def _setup_dev_environment(envs: List[str], port: Optional[int], config_path: Path) -> tuple[dict, bool, int]:
    """Parse environment variables and setup development environment with port handling.

    Environment variable precedence (lowest to highest):
    1. OS environment variables
    2. Config file values
    3. User-provided --env values (highest priority)

    Returns:
        tuple: (environment dict, port_changed bool, requested_port int)
    """
    # Parse user-provided env vars
    user_env_vars = {}
    if envs:
        for env_var in envs:
            if "=" not in env_var:
                _handle_error(f"Invalid environment variable format: {env_var}. Use KEY=VALUE format.")
            key, value = env_var.split("=", 1)
            user_env_vars[key] = value

    # Build environment with correct precedence
    local_env = dict(os.environ)
    local_env.update(_get_env_vars(config_path))  # Config values
    local_env.update(user_env_vars)  # User values override config
    local_env["LOCAL_DEV"] = "1"

    requested_port = port or local_env.get("PORT", None)
    if isinstance(requested_port, str):
        requested_port = int(requested_port)

    default_port = requested_port or 8080
    actual_port = _find_available_port(default_port)
    port_changed = actual_port != default_port

    local_env["PORT"] = str(actual_port)
    return local_env, port_changed, default_port


def _find_available_port(start_port: int = 8080) -> int:
    """Find an available port starting from the given port."""
    for port in range(start_port, start_port + 101):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("localhost", port))
                return port
        except OSError:
            continue
    _handle_error("Could not find available port in range 8080-8180")


def _assert_aws_creds_if_required(config_path: Path):
    """For dev, only assert creds if using bedrock."""
    config = load_config_if_exists(config_path, autofill_missing_aws=False)
    if not config:
        # There is no config so don't validate
        return
    agent_config = config.agents[config.default_agent]
    if agent_config.api_key_credential_provider_name is not None:
        # If it's an API key based provider, aws creds aren't needed
        return
    else:
        # If it's Bedrock, assert there are valid aws creds.
        assert_valid_aws_creds_or_exit(
            failure_message="Local dev with Bedrock as the model provider requires AWS creds"
        )


def _cleanup_process(process):
    """Gracefully terminate process with fallback to kill."""
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
