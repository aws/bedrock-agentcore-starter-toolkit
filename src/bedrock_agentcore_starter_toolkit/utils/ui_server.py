"""UI server utilities for launching the web interface."""

import logging
import os
import socket
import subprocess  # nosec B404
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_available_port(start_port: int = 8001, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port.

    Args:
        start_port: Port to start searching from
        max_attempts: Maximum number of ports to try

    Returns:
        Available port number

    Raises:
        RuntimeError: If no available port found
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue

    raise RuntimeError("Could not find available port in range %s-%s" % (start_port, start_port + max_attempts))


def start_ui_server(
    config_path: Path,
    agent_name: Optional[str],
    local_mode: bool,
    port: Optional[int] = None,
) -> tuple[subprocess.Popen, int]:
    """Start the FastAPI UI server in a background process.

    Args:
        config_path: Path to the agent configuration file
        agent_name: Name of the agent to use
        local_mode: Whether running in local mode
        port: Port to bind to (if None, will find available port)

    Returns:
        Tuple of (process, port)

    Raises:
        RuntimeError: If server fails to start
    """
    # Find available port if not specified
    if port is None:
        port = find_available_port()

    # Get the UI directory (parent of backend)
    ui_dir = Path(__file__).parent.parent / "ui"
    ui_backend_dir = ui_dir / "backend"

    if not ui_backend_dir.exists():
        raise RuntimeError("UI backend directory not found: %s" % ui_backend_dir)

    # Prepare environment variables
    env = os.environ.copy()
    env["AGENTCORE_CONFIG_PATH"] = str(config_path.absolute())
    env["AGENTCORE_LOCAL_MODE"] = "true" if local_mode else "false"
    env["UVICORN_PORT"] = str(port)  # Pass port for CORS configuration
    if agent_name:
        env["AGENTCORE_AGENT_NAME"] = agent_name

    # Start uvicorn server from ui directory to support package imports
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "info",
    ]

    logger.info("Starting UI server on port %s...", port)

    try:
        process = subprocess.Popen(  # nosec B603
            cmd,
            cwd=ui_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait a moment for server to start
        time.sleep(2)

        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError("UI server failed to start:\nSTDOUT: %s\nSTDERR: %s" % (stdout, stderr))

        logger.info("UI server started successfully on port %s", port)
        return process, port

    except Exception as e:
        logger.error("Failed to start UI server: %s", e)
        raise RuntimeError("Failed to start UI server: %s" % e) from e


def open_browser(url: str, delay: float = 1.0) -> bool:
    """Open the default browser to the specified URL.

    Args:
        url: URL to open
        delay: Delay in seconds before opening browser

    Returns:
        True if browser opened successfully, False otherwise
    """
    time.sleep(delay)

    try:
        webbrowser.open(url)
        logger.info("Opened browser to %s", url)
        return True
    except Exception as e:
        logger.warning("Failed to open browser: %s", e)
        return False


def shutdown_server(process: subprocess.Popen, timeout: int = 5) -> None:
    """Gracefully shutdown the UI server process.

    Args:
        process: Server process to shutdown
        timeout: Timeout in seconds for graceful shutdown
    """
    if process.poll() is not None:
        # Process already terminated
        return

    logger.info("Shutting down UI server...")

    try:
        # Try graceful shutdown first
        process.terminate()
        process.wait(timeout=timeout)
        logger.info("UI server shut down gracefully")
    except subprocess.TimeoutExpired:
        # Force kill if graceful shutdown fails
        logger.warning("UI server did not shut down gracefully, forcing...")
        process.kill()
        process.wait()
        logger.info("UI server forcefully terminated")
    except Exception as e:
        logger.error("Error shutting down UI server: %s", e)


def wait_for_server_ready(port: int, timeout: int = 10) -> bool:
    """Wait for the server to be ready to accept connections.

    Args:
        port: Port to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if server is ready, False if timeout
    """
    start_time = time.time()
    url = "http://127.0.0.1:%s/health" % port

    while time.time() - start_time < timeout:
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=1) as response:  # nosec B310
                if response.status == 200:
                    logger.info("UI server is ready")
                    return True
        except Exception:
            time.sleep(0.5)

    logger.warning("UI server did not become ready within timeout")
    return False
