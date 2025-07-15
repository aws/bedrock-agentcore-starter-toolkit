"""BedrockAgentCore CLI main module."""

import logging

import typer
from rich.logging import RichHandler

from ..cli.gateway.commands import create_mcp_gateway, create_mcp_gateway_target, gateway_app
from .common import console
from .runtime.commands import configure_app, invoke, launch, status

app = typer.Typer(name="agentcore", help="BedrockAgentCore CLI", add_completion=False)

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO",
    format=FORMAT,
    handlers=[RichHandler(show_time=False, show_path=False, show_level=False, console=console)],
)

# runtime
app.command("invoke")(invoke)
app.command("status")(status)
app.command("launch")(launch)
app.add_typer(configure_app)

# gateway
app.command("create_mcp_gateway")(create_mcp_gateway)
app.command("create_mcp_gateway_target")(create_mcp_gateway_target)
app.add_typer(gateway_app, name="gateway")


def main():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
