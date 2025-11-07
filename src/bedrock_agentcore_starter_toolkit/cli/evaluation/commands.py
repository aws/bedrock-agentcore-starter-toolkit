"""CLI commands for agent evaluation."""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...operations.evaluation.client import EvaluationClient
from ...operations.evaluation.models.evaluation import EvaluationResults
from ...utils.runtime.config import load_config_if_exists
from ..common import console

# Create a module-specific logger
logger = logging.getLogger(__name__)

# Create a Typer app for evaluation commands
evaluation_app = typer.Typer(help="Evaluate agent performance using built-in and custom evaluators")


def _get_agent_config_from_file(agent_name: Optional[str] = None) -> Optional[dict]:
    """Load agent configuration from .bedrock_agentcore.yaml."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    config = load_config_if_exists(config_path)

    if not config:
        return None

    try:
        agent_config = config.get_agent_config(agent_name)
        agent_id = agent_config.bedrock_agentcore.agent_id
        region = agent_config.aws.region
        session_id = agent_config.bedrock_agentcore.agent_session_id

        if not agent_id or not region:
            return None

        return {
            "agent_id": agent_id,
            "session_id": session_id,
            "region": region,
        }
    except Exception as e:
        logger.debug("Failed to load agent config: %s", e)
        return None


def _display_evaluation_results(results: EvaluationResults) -> None:
    """Display evaluation results in a formatted way.

    Args:
        results: EvaluationResults object
    """
    # Header
    header = Text()
    header.append("Evaluation Results\n", style="bold cyan")
    if results.session_id:
        header.append(f"Session: {results.session_id}\n", style="dim")
    if results.trace_id:
        header.append(f"Trace: {results.trace_id}\n", style="dim")

    console.print(Panel(header, border_style="cyan"))

    # Display successful results
    successful = results.get_successful_results()
    if successful:
        console.print("\n[bold green]✓ Successful Evaluations[/bold green]\n")

        for result in successful:
            # Create panel for each result
            content = Text()

            # Evaluator name
            content.append("Evaluator: ", style="bold")
            content.append(f"{result.evaluator_name}\n\n", style="cyan")

            # Score/Label
            if result.value is not None:
                content.append("Score: ", style="bold")
                content.append(f"{result.value:.2f}\n", style="green")

            if result.label:
                content.append("Label: ", style="bold")
                content.append(f"{result.label}\n", style="green")

            # Explanation
            if result.explanation:
                content.append("\nExplanation:\n", style="bold")
                content.append(f"{result.explanation}\n")

            # Token usage
            if result.token_usage:
                content.append("\nToken Usage:\n", style="bold")
                content.append(f"  - Input: {result.token_usage.get('inputTokens', 0):,}\n", style="dim")
                content.append(f"  - Output: {result.token_usage.get('outputTokens', 0):,}\n", style="dim")
                content.append(f"  - Total: {result.token_usage.get('totalTokens', 0):,}\n", style="dim")

            # Evaluation-specific context (from API response)
            if result.context:
                content.append("\nEvaluation Context:\n", style="bold")
                for key, value in result.context.items():
                    content.append(f"  - {key}: {value}\n", style="dim")

            console.print(Panel(content, border_style="green", padding=(1, 2)))

    # Display failed results
    failed = results.get_failed_results()
    if failed:
        console.print("\n[bold red]✗ Failed Evaluations[/bold red]\n")

        for result in failed:
            content = Text()
            content.append("Evaluator: ", style="bold")
            content.append(f"{result.evaluator_name}\n\n", style="cyan")
            content.append("Error: ", style="bold red")
            content.append(f"{result.error}\n", style="red")

            console.print(Panel(content, border_style="red", padding=(1, 2)))


def _save_evaluation_results(results: EvaluationResults, output_file: str) -> None:
    """Save evaluation results to a JSON file.

    Args:
        results: EvaluationResults object
        output_file: Path to output file
    """
    output_path = Path(output_file)

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save results to file
    results_dict = results.to_dict()

    # Separate input_data if present
    input_data = results_dict.pop("input_data", None)

    # Save results
    with open(output_path, "w") as f:
        json.dump(results_dict, f, indent=2, default=str)

    console.print(f"\n[green]✓[/green] Results saved to: {output_path}")

    # Save input data to separate file if present
    if input_data is not None:
        # Create input file path (add _input before extension)
        stem = output_path.stem
        suffix = output_path.suffix
        input_path = output_path.parent / f"{stem}_input{suffix}"

        with open(input_path, "w") as f:
            json.dump(input_data, f, indent=2, default=str)

        console.print(f"[green]✓[/green] Input data saved to: {input_path}")


@evaluation_app.command("run")
def run_evaluation(
    session_id: Optional[str] = typer.Option(
        None, "--session-id", help="Session ID to evaluate (uses config if not provided)"
    ),
    trace_id: Optional[str] = typer.Option(
        None, "--trace-id", help="Specific trace ID to evaluate (defaults to latest trace)"
    ),
    all_traces: bool = typer.Option(
        False,
        "--all-traces",
        help="Evaluate all traces in the session (sends all traces in single API call, limited to 100 most recent items)",
    ),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Agent ID (optional, for filtering session data)"),
    evaluators: Optional[List[str]] = typer.Option(
        ["Builtin.Helpfulness"], "--evaluator", "-e", help="Evaluator(s) to use (can specify multiple times)"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save results to JSON file"),
    region: Optional[str] = typer.Option(None, "--region", help="AWS region for evaluation API (overrides env var)"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", help="Evaluation API endpoint URL (overrides env var)"),
    agent_name: Optional[str] = typer.Option(None, "--agent-name", help="Agent name from config file"),
):
    """Run evaluation on a session.

    Examples:
        # Evaluate latest trace from config with default evaluator
        agentcore eval run

        # Evaluate specific session
        agentcore eval run --session-id eb358f6f

        # Evaluate specific trace
        agentcore eval run --session-id eb358f6f --trace-id abc123

        # Evaluate all traces in session (one API call per trace)
        agentcore eval run --session-id eb358f6f --all-traces

        # Use multiple evaluators
        agentcore eval run --session-id eb358f6f -e Builtin.Helpfulness -e Builtin.Accuracy

        # Save results to file
        agentcore eval run --session-id eb358f6f -o results.json
    """
    # Validate mutually exclusive options
    if trace_id and all_traces:
        console.print("[red]Error:[/red] Cannot specify both --trace-id and --all-traces")
        raise typer.Exit(1)

    # Get session ID, agent_id, and region from config if not provided
    config = _get_agent_config_from_file(agent_name)

    if not session_id:
        if config and config.get("session_id"):
            session_id = config["session_id"]
            console.print(f"[dim]Using session from config: {session_id}[/dim]")
        else:
            console.print("[red]Error:[/red] No session ID provided")
            console.print("\nProvide session_id via:")
            console.print("  1. CLI argument: --session-id <ID>")
            console.print("  2. Configuration file: .bedrock_agentcore.yaml")
            raise typer.Exit(1)

    # Get agent_id from CLI arg or config
    if not agent_id:
        if config and config.get("agent_id"):
            agent_id = config["agent_id"]
        else:
            console.print("[red]Error:[/red] No agent ID provided")
            console.print("\nProvide agent_id via:")
            console.print("  1. CLI argument: --agent-id <ID>")
            console.print("  2. Configuration file: .bedrock_agentcore.yaml")
            raise typer.Exit(1)

    # Get region from CLI arg or config
    if not region:
        if config and config.get("region"):
            region = config["region"]
        else:
            console.print("[red]Error:[/red] No region provided")
            console.print("\nProvide region via:")
            console.print("  1. CLI argument: --region <REGION>")
            console.print("  2. Configuration file: .bedrock_agentcore.yaml")
            raise typer.Exit(1)

    # Convert evaluators to list (Typer returns list or None)
    evaluator_list = evaluators if evaluators else ["Builtin.Helpfulness"]

    # Display what we're doing
    console.print(f"\n[cyan]Evaluating session:[/cyan] {session_id}")
    if trace_id:
        console.print(f"[cyan]Trace ID:[/cyan] {trace_id}")
    elif all_traces:
        console.print("[cyan]Mode:[/cyan] All traces (single API call with all traces)")
    else:
        console.print("[cyan]Mode:[/cyan] Latest trace only")
    console.print(f"[cyan]Evaluators:[/cyan] {', '.join(evaluator_list)}\n")

    try:
        # Create evaluation client with optional config
        client_kwargs = {}
        if region:
            client_kwargs["region"] = region
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint

        eval_client = EvaluationClient(**client_kwargs)

        # Show endpoint being used
        if os.getenv("AGENTCORE_EVAL_ENDPOINT") or endpoint:
            console.print(f"[dim]Using endpoint: {eval_client.endpoint_url}[/dim]\n")

        # Run evaluation
        with console.status("[cyan]Running evaluation...[/cyan]"):
            results = eval_client.evaluate_session(
                session_id=session_id,
                evaluators=evaluator_list,
                agent_id=agent_id,
                region=region,
                trace_id=trace_id,
                all_traces=all_traces,
            )

        # Display results
        _display_evaluation_results(results)

        # Save to file if requested
        if output:
            _save_evaluation_results(results, output)

        # Exit with error code if any evaluation failed
        if results.has_errors():
            console.print("\n[yellow]Warning:[/yellow] Some evaluations failed")
            raise typer.Exit(1)

    except RuntimeError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/red] {e}")
        logger.exception("Evaluation failed")
        raise typer.Exit(1) from e


@evaluation_app.command("config")
def show_config():
    """Show evaluation configuration (endpoint, region)."""
    config_table = Table(title="Evaluation Configuration", show_header=True)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")

    # Get current config
    region = os.getenv("AGENTCORE_EVAL_REGION", EvaluationClient.DEFAULT_REGION)
    endpoint = os.getenv("AGENTCORE_EVAL_ENDPOINT", EvaluationClient.DEFAULT_ENDPOINT)

    config_table.add_row("Region", region)
    config_table.add_row("Endpoint", endpoint)

    console.print(config_table)

    # Show environment variable hints
    console.print("\n[dim]Configuration can be set via environment variables:[/dim]")
    console.print("[dim]  - AGENTCORE_EVAL_REGION[/dim]")
    console.print("[dim]  - AGENTCORE_EVAL_ENDPOINT[/dim]")
