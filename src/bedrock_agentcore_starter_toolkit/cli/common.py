"""Common utilities for BedrockAgentCore CLI."""

from typing import NoReturn, Optional

import typer
from prompt_toolkit import prompt
from rich.console import Console

console = Console()


def _handle_error(message: str, exception: Optional[Exception] = None) -> NoReturn:
    """Handle errors with consistent formatting and exit."""
    console.print(f"[red]❌ {message}[/red]")
    if exception:
        raise typer.Exit(1) from exception
    else:
        raise typer.Exit(1)


def _handle_warn(message: str) -> NoReturn:
    """Handle errors with consistent formatting and exit."""
    console.print(f"⚠️  {message}", new_line_start=True, style="bold yellow underline")


def _print_success(message: str) -> None:
    """Print success message with consistent formatting."""
    console.print(f"[green]✓[/green] {message}")


def _prompt_with_default(question: str, default_value: Optional[str] = "") -> str:
    """Prompt user with AWS CLI style [default] format and empty input field."""
    prompt_text = question
    if default_value:
        prompt_text += f" [{default_value}]"
    prompt_text += ": "

    response = prompt(prompt_text, default="")

    # If user pressed Enter without typing, use default
    if not response and default_value:
        return default_value

    return response
