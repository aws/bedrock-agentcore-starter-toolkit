"""BedrockAgentCore CLI main module."""

import typer

from ..cli.gateway.commands import (
    create_mcp_gateway,
    create_mcp_gateway_target,
    gateway_app,
)
from ..cli.memory.commands import memory_app
from ..cli.observability.commands import observability_app
from ..utils.logging_config import setup_toolkit_logging
from .create.commands import create_app
from .create.import_agent.commands import import_agent
from .identity.commands import identity_app
from .runtime.commands import (
    configure_app,
    deploy,
    destroy,
    invoke,
    status,
    stop_session,
)
from .runtime.dev_command import dev

app = typer.Typer(name="agentcore", help="BedrockAgentCore CLI", add_completion=False, rich_markup_mode="rich")

# Setup centralized logging for CLI
setup_toolkit_logging(mode="cli")

# runtime
app.command("invoke")(invoke)
app.command("status")(status)
app.command("deploy")(deploy)
app.command("dev")(dev)
app.command("destroy")(destroy)
app.command("stop-session")(stop_session)
app.add_typer(identity_app, name="identity")
app.add_typer(configure_app)

# gateway
app.command("create_mcp_gateway")(create_mcp_gateway)
app.command("create_mcp_gateway_target")(create_mcp_gateway_target)
app.add_typer(gateway_app, name="gateway")

# memory
app.add_typer(memory_app, name="memory")

# observability
app.add_typer(observability_app, name="obs")

# create
app.add_typer(create_app, name="create")
create_app.command("import")(import_agent)

# Alias: agentcore import-agent -> agentcore create import
app.command("import-agent")(import_agent)


# Backward compatibility aliases
app.command("launch", hidden=True)(deploy)


def main():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
