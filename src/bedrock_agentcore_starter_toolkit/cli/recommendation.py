"""Shared AgentCore CLI migration recommendation.

The starter toolkit is no longer the recommended entry point; the AgentCore CLI
(``@aws/agentcore``) is. This module is the single source of truth for that
message so every surface (the per-command banner and the ``create`` success
screen) and the install/uninstall commands stay in sync.
"""

import os

from rich.console import Console

AGENTCORE_CLI_PACKAGE = "@aws/agentcore"
INSTALL_CMD = "npm install -g @aws/agentcore"
UNINSTALL_CMD = "pip uninstall bedrock-agentcore-starter-toolkit"
IMPORT_CMD = "agentcore import"

SUPPRESS_ENV_VAR = "AGENTCORE_SUPPRESS_RECOMMENDATION"


def is_recommendation_suppressed() -> bool:
    """Return True when the user has opted out of the recommendation."""
    return os.environ.get(SUPPRESS_ENV_VAR, "").lower() in ("1", "true", "yes")


def recommendation_text() -> str:
    """Rich-markup recommendation block recommending the AgentCore CLI."""
    return (
        f"\n[yellow bold]⚠️  The AgentCore CLI ({AGENTCORE_CLI_PACKAGE}) is now the recommended way to create,"
        " develop, and deploy agents on Amazon Bedrock AgentCore.[/yellow bold]\n"
        f"[yellow]   We recommend migrating to the new CLI:[/yellow] [cyan]{INSTALL_CMD}[/cyan]\n"
        f"[yellow]   To import existing agents, run:[/yellow] [cyan]{IMPORT_CMD}[/cyan]\n"
        f"[yellow]   To uninstall this starter toolkit, run:[/yellow] [cyan]{UNINSTALL_CMD}[/cyan]\n"
        f"[dim]   Set {SUPPRESS_ENV_VAR}=1 to silence this warning.[/dim]\n"
    )


def print_recommendation(console: Console) -> None:
    """Print the recommendation to ``console`` unless the user suppressed it."""
    if is_recommendation_suppressed():
        return
    console.print(recommendation_text())
