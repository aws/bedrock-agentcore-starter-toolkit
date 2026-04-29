"""BedrockAgentCore CLI main module."""

import os

import typer
from rich.console import Console

from ..cli.evaluation.commands import evaluation_app
from ..cli.gateway.commands import (
    create_mcp_gateway,
    create_mcp_gateway_target,
    gateway_app,
)
from ..cli.memory.commands import memory_app
from ..cli.observability.commands import observability_app
from ..cli.policy.commands import policy_app
from ..utils.logging_config import setup_toolkit_logging
from .create.commands import create, create_app
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

_stderr_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def _deprecation_banner(ctx: typer.Context) -> None:
    """Show deprecation warning before every command."""
    if os.environ.get("AGENTCORE_SUPPRESS_DEPRECATION", "").lower() in ("1", "true", "yes"):
        return
    if ctx.invoked_subcommand is None and not ctx.protected_args:
        return
    _stderr_console.print(
        "\n[yellow bold]⚠️  The AgentCore CLI (@aws/agentcore) is now the recommended way to create, develop,"
        " and deploy agents on Amazon Bedrock AgentCore.[/yellow bold]\n"
        "[yellow]   We recommend migrating to the new CLI:[/yellow] [cyan]npm install -g @aws/agentcore[/cyan]\n"
        "[dim]   Set AGENTCORE_SUPPRESS_DEPRECATION=1 to silence this warning.[/dim]\n"
    )

app.command("create")(create)
app.add_typer(create_app, name="create")
create_app.command("import")(import_agent)
app.command("dev")(dev)
app.command("deploy")(deploy)
app.command("invoke")(invoke)
app.command("status")(status)
app.command("destroy")(destroy)
app.command("stop-session")(stop_session)
app.add_typer(configure_app)

# Services
app.add_typer(identity_app, name="identity")
app.add_typer(gateway_app, name="gateway")
app.add_typer(memory_app, name="memory")
app.add_typer(observability_app, name="obs")
app.add_typer(policy_app, name="policy")
app.add_typer(evaluation_app, name="eval")
app.command("create_mcp_gateway")(create_mcp_gateway)
app.command("create_mcp_gateway_target")(create_mcp_gateway_target)

# Hidden Aliases
app.command("launch", hidden=True)(deploy)
app.command("import-agent", hidden=True)(import_agent)


def main():  # pragma: no cover
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
