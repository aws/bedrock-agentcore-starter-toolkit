"""BedrockAgentCore CLI main module."""

import typer

from ..cli.gateway.commands import (
    create_mcp_gateway,
    create_mcp_gateway_target,
    delete_mcp_gateway,
    delete_mcp_gateway_target,
    gateway_app,
)
from ..cli.memory.commands import delete as delete_memory
from ..cli.memory.commands import memory_app
from ..cli.observability.commands import observability_app
from ..utils.logging_config import setup_toolkit_logging
from .identity.commands import identity_app
from .import_agent.commands import import_agent
from .runtime.commands import (
    configure_app,
    deploy,
    destroy,
    invoke,
    status,
    stop_session,
)

app = typer.Typer(name="agentcore", help="BedrockAgentCore CLI", add_completion=False, rich_markup_mode="rich")

# Setup centralized logging for CLI
setup_toolkit_logging(mode="cli")


# Placeholder functions for unimplemented subcommands
def remove_idp():
    """Remove Identity Provider configuration."""
    typer.echo("Command not yet implemented")
    raise typer.Exit(1)


def remove_agent_identity():
    """Remove agent identity configuration."""
    typer.echo("Command not yet implemented")
    raise typer.Exit(1)


# runtime
app.command("invoke")(invoke)
app.command("status")(status)
app.command("deploy")(deploy)
app.command("import-agent")(import_agent)
app.add_typer(identity_app, name="identity")
app.add_typer(configure_app)

# remove command group
remove_app = typer.Typer(name="remove", help="Remove AgentCore resources")
remove_app.command("all")(destroy)
remove_app.command("gateway")(delete_mcp_gateway)
remove_app.command("gateway-target")(delete_mcp_gateway_target)
remove_app.command("memory")(delete_memory)
remove_app.command("idp")(remove_idp)
remove_app.command("agent-identity")(remove_agent_identity)
app.add_typer(remove_app, name="remove")

# session command group
session_app = typer.Typer(name="session", help="Manage runtime sessions")
session_app.command("stop")(stop_session)
app.add_typer(session_app, name="session")

# gateway
app.command("create_mcp_gateway")(create_mcp_gateway)
app.command("create_mcp_gateway_target")(create_mcp_gateway_target)
app.add_typer(gateway_app, name="gateway")

# memory
app.add_typer(memory_app, name="memory")

# observability
app.add_typer(observability_app, name="obs")

# import-agent
app.command("import-agent")(import_agent)


def main():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
