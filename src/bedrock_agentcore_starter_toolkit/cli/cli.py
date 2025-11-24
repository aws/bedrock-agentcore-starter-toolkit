"""BedrockAgentCore CLI main module."""

import typer

from ..cli.gateway.commands import (
    create_mcp_gateway,
    create_mcp_gateway_target,
    delete_mcp_gateway,
    delete_mcp_gateway_target,
    list_mcp_gateway_targets,
    list_mcp_gateways,
)
from ..cli.memory.commands import create as create_memory
from ..cli.memory.commands import delete as delete_memory
from ..cli.memory.commands import list as list_memory
from ..cli.observability.commands import observability_app
from ..utils.logging_config import setup_toolkit_logging
from .identity.commands import (
    cleanup_identity,
    create_credential_provider,
    create_workload_identity,
    list_credential_providers,
)
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


# runtime
app.command("invoke")(invoke)
app.command("status")(status)
app.command("deploy")(deploy)
app.command("import-agent")(import_agent)
app.add_typer(configure_app)

# remove command group
remove_app = typer.Typer(name="remove", help="Remove AgentCore resources")
remove_app.command("all")(destroy)
remove_app.command("gateway")(delete_mcp_gateway)
remove_app.command("gateway-target")(delete_mcp_gateway_target)
remove_app.command("memory")(delete_memory)
remove_app.command("idp")(cleanup_identity)
remove_app.command("agent-identity")(cleanup_identity)
app.add_typer(remove_app, name="remove")

# add command group
add_app = typer.Typer(name="add", help="Add AgentCore resources")
add_app.command("gateway")(create_mcp_gateway)
add_app.command("gateway-target")(create_mcp_gateway_target)
add_app.command("memory")(create_memory)
add_app.command("idp")(create_credential_provider)
add_app.command("agent-identity")(create_workload_identity)
app.add_typer(add_app, name="add")

# list command group
list_app = typer.Typer(name="list", help="List AgentCore resources")
list_app.command("gateway")(list_mcp_gateways)
list_app.command("gateway-target")(list_mcp_gateway_targets)
list_app.command("memory")(list_memory)
list_app.command("idp")(list_credential_providers)
app.add_typer(list_app, name="list")

# session command group
session_app = typer.Typer(name="session", help="Manage runtime sessions")
session_app.command("stop")(stop_session)
app.add_typer(session_app, name="session")

# observability
app.add_typer(observability_app, name="obs")

# import-agent
app.command("import-agent")(import_agent)


def main():
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
