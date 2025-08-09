"""BedrockAgentCore CLI main module."""

import typer

from ..cli.gateway.commands import create_mcp_gateway, create_mcp_gateway_target, gateway_app
from ..utils.logging_config import setup_toolkit_logging
from .import_agent.commands import import_agent
from .runtime.commands import configure_app, invoke, launch, status, destroy

app = typer.Typer(name="agentcore", help="BedrockAgentCore CLI", add_completion=False, rich_markup_mode="rich")

# Setup centralized logging for CLI
setup_toolkit_logging(mode="cli")

# runtime
app.command("invoke")(invoke)
app.command("status")(status)
app.command("launch")(launch)
app.command("import-agent")(import_agent)
app.command("destroy")(destroy)
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
