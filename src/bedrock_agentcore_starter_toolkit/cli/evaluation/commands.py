"""CLI commands for agent evaluation."""

import json
import logging
from pathlib import Path
from typing import List, Optional

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...operations.evaluation.client import EvaluationClient
from ...operations.evaluation.cp_client import EvaluationControlPlaneClient
from ...operations.evaluation.models.evaluation import EvaluationResults
from ...utils.runtime.config import load_config_if_exists
from ..common import console

# Create a module-specific logger
logger = logging.getLogger(__name__)

# Create a Typer app for evaluation commands
evaluation_app = typer.Typer(help="Evaluate agent performance using built-in and custom evaluators")

# Create a sub-app for evaluator management
evaluator_app = typer.Typer(help="Manage custom evaluators (create, list, update, delete)")
evaluation_app.add_typer(evaluator_app, name="evaluator")


def _get_agent_config_from_file(agent_name: Optional[str] = None) -> Optional[dict]:
    """Get agent configuration from .bedrock_agentcore.yaml file.

    Args:
        agent_name: Optional agent name to load (uses first agent if not specified)

    Returns:
        Dict with agent_id, region, session_id if config found, None otherwise
    """
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    if not config_path.exists():
        return None

    try:
        config = load_config_if_exists(config_path)
        if not config:
            return None

        agent_config = config.get_agent_config(agent_name)

        return {
            "agent_id": agent_config.bedrock_agentcore.agent_id,
            "region": agent_config.aws.region,
            "session_id": agent_config.bedrock_agentcore.agent_session_id,
        }
    except Exception:
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

            # Extract and display context IDs (from spanContext)
            if result.context and "spanContext" in result.context:
                span_context = result.context["spanContext"]
                content.append("\nEvaluated:\n", style="bold")
                if "sessionId" in span_context:
                    content.append(f"  - Session: {span_context['sessionId']}\n", style="dim")
                if "traceId" in span_context:
                    content.append(f"  - Trace: {span_context['traceId']}\n", style="dim")
                if "spanId" in span_context:
                    content.append(f"  - Span: {span_context['spanId']}\n", style="dim")

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
    agent: Optional[str] = typer.Option(
        None,
        "--agent",
        "-a",
        help="Agent name (use 'agentcore configure list' to see available agents)",
    ),
    session_id: Optional[str] = typer.Option(None, "--session-id", "-s", help="Override session ID from config"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Override agent ID from config"),
    trace_id: Optional[str] = typer.Option(
        None,
        "--trace-id",
        "-t",
        help="Evaluate only this trace (includes spans from all previous traces for context)",
    ),
    evaluators: Optional[List[str]] = typer.Option(  # noqa: B008
        None, "--evaluator", "-e", help="Evaluator(s) to use (can specify multiple times)"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save results to JSON file"),
):
    """Run evaluation on a session.

    Default behavior: Evaluates all traces (most recent 1000 spans).
    With --trace-id: Evaluates only that trace (includes spans from all previous traces for context).

    Examples:
        # Evaluate all traces from default agent config
        agentcore eval run

        # Evaluate specific agent
        agentcore eval run -a my-agent

        # Evaluate specific trace only (with previous traces for context)
        agentcore eval run -t abc123

        # Override session from config
        agentcore eval run -s eb358f6f

        # Use multiple evaluators
        agentcore eval run -e Builtin.Helpfulness -e Builtin.Accuracy

        # Save results to file
        agentcore eval run -o results.json
    """
    # Get config from agent
    config = _get_agent_config_from_file(agent)

    # Get session_id from CLI or config
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

    # Get agent_id from CLI or config
    if agent_id:
        # Explicit --agent-id provided
        pass
    elif config and config.get("agent_id"):
        agent_id = config["agent_id"]
    elif agent:
        # User provided --agent but no config found - clear error
        console.print(f"[red]Error:[/red] Agent '{agent}' not found in config")
        console.print("\nOptions:")
        console.print("  1. Check agent name: agentcore configure list")
        console.print("  2. Use --agent-id instead if you have the agent ID")
        raise typer.Exit(1)
    else:
        console.print("[red]Error:[/red] No agent specified")
        console.print("\nProvide agent via:")
        console.print("  1. --agent-id AGENT_ID")
        console.print("  2. --agent AGENT_NAME (requires config)")
        raise typer.Exit(1)

    # Get region from config or boto3 default
    if config and config.get("region"):
        region = config["region"]
    else:
        # Use boto3's default region resolution (env vars, AWS config, etc.)
        import boto3

        session = boto3.Session()
        region = session.region_name or "us-east-1"
        console.print(f"[dim]Using AWS region: {region}[/dim]")

    # Convert evaluators to list (Typer returns list or None)
    evaluator_list = evaluators if evaluators else ["Builtin.Helpfulness"]

    # Display what we're doing
    console.print(f"\n[cyan]Evaluating session:[/cyan] {session_id}")
    if trace_id:
        console.print(f"[cyan]Trace:[/cyan] {trace_id} (with previous traces for context)")
    else:
        console.print("[cyan]Mode:[/cyan] All traces (most recent 1000 spans)")
    console.print(f"[cyan]Evaluators:[/cyan] {', '.join(evaluator_list)}\n")

    try:
        # Create evaluation client
        eval_client = EvaluationClient()

        # Run evaluation
        with console.status("[cyan]Running evaluation...[/cyan]"):
            results = eval_client.evaluate_session(
                session_id=session_id,
                evaluators=evaluator_list,
                agent_id=agent_id,
                region=region,
                trace_id=trace_id,
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


# ===========================
# Evaluator Management Commands
# ===========================


@evaluator_app.command("list")
def list_evaluators(
    max_results: int = typer.Option(50, "--max-results", help="Maximum number of evaluators to return"),
):
    """List all evaluators (builtin and custom).

    Examples:
        # List all evaluators
        agentcore eval evaluator list

        # List more evaluators
        agentcore eval evaluator list --max-results 100
    """
    try:
        client = EvaluationControlPlaneClient()

        with console.status("[cyan]Fetching evaluators...[/cyan]"):
            response = client.list_evaluators(max_results=max_results)

        evaluators = response.get("evaluators", [])

        if not evaluators:
            console.print("[yellow]No evaluators found[/yellow]")
            return

        # Separate builtin and custom
        builtin = [e for e in evaluators if e.get("evaluatorId", "").startswith("Builtin.")]
        custom = [e for e in evaluators if not e.get("evaluatorId", "").startswith("Builtin.")]

        # Display builtin evaluators
        if builtin:
            console.print(f"\n[bold cyan]Built-in Evaluators ({len(builtin)})[/bold cyan]\n")

            builtin_table = Table(show_header=True)
            builtin_table.add_column("ID", style="cyan", no_wrap=True, width=30)
            builtin_table.add_column("Name", style="white", width=30)
            builtin_table.add_column("Description", style="dim")

            for ev in sorted(builtin, key=lambda x: x.get("evaluatorId", "")):
                builtin_table.add_row(ev.get("evaluatorId", ""), ev.get("evaluatorName", ""), ev.get("description", ""))

            console.print(builtin_table)

        # Display custom evaluators
        if custom:
            console.print(f"\n[bold green]Custom Evaluators ({len(custom)})[/bold green]\n")

            custom_table = Table(show_header=True)
            custom_table.add_column("ID", style="green", no_wrap=True)
            custom_table.add_column("Name", style="white")
            custom_table.add_column("Created", style="dim")

            for ev in sorted(custom, key=lambda x: x.get("createdAt", ""), reverse=True):
                created = ev.get("createdAt", "")
                if created:
                    created = str(created).split("T")[0]  # Just the date

                custom_table.add_row(ev.get("evaluatorId", ""), ev.get("evaluatorName", ""), created)

            console.print(custom_table)

        console.print(f"\n[dim]Total: {len(evaluators)} ({len(builtin)} builtin, {len(custom)} custom)[/dim]")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Failed to list evaluators")
        raise typer.Exit(1) from e


@evaluator_app.command("get")
def get_evaluator(
    evaluator_id: str = typer.Argument(..., help="Evaluator ID (e.g., Builtin.Helpfulness or custom-id)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save to JSON file"),
):
    """Get detailed information about an evaluator.

    Examples:
        # Get builtin evaluator
        agentcore eval evaluator get Builtin.Helpfulness

        # Get custom evaluator
        agentcore eval evaluator get my-evaluator-abc123

        # Export to JSON
        agentcore eval evaluator get my-evaluator -o evaluator.json
    """
    try:
        client = EvaluationControlPlaneClient()

        with console.status(f"[cyan]Fetching evaluator {evaluator_id}...[/cyan]"):
            response = client.get_evaluator(evaluator_id=evaluator_id)

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(response, f, indent=2, default=str)
            console.print(f"\n[green]✓[/green] Saved to: {output_path}")
            return

        # Display details
        console.print("\n[bold cyan]Evaluator Details[/bold cyan]\n")

        # Metadata
        metadata = {
            "ID": response.get("evaluatorId", ""),
            "Name": response.get("evaluatorName", ""),
            "ARN": response.get("evaluatorArn", ""),
            "Level": response.get("level", ""),
        }

        if "description" in response:
            metadata["Description"] = response["description"]
        if "createdAt" in response:
            metadata["Created"] = str(response["createdAt"])
        if "updatedAt" in response:
            metadata["Updated"] = str(response["updatedAt"])

        for key, value in metadata.items():
            console.print(f"[bold]{key}:[/bold] {value}")

        # Config details
        if "evaluatorConfig" in response:
            config = response["evaluatorConfig"]
            console.print("\n[bold]Configuration:[/bold]")

            if "llmAsAJudge" in config:
                llm_config = config["llmAsAJudge"]

                # Model
                if "modelConfig" in llm_config:
                    model = llm_config["modelConfig"].get("bedrockEvaluatorModelConfig", {})
                    console.print(f"  Model: {model.get('modelId', 'N/A')}")

                # Rating scale
                if "ratingScale" in llm_config:
                    scale = llm_config["ratingScale"].get("numerical", [])
                    min_val = scale[0].get("value", 0)
                    max_val = scale[-1].get("value", 1)
                    console.print(f"  Rating Scale: {len(scale)} levels ({min_val} - {max_val})")

                # Instructions (truncated)
                if "instructions" in llm_config:
                    instructions = llm_config["instructions"]
                    preview = instructions[:200] + "..." if len(instructions) > 200 else instructions
                    console.print(f"  Instructions: {preview}")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Failed to get evaluator %s", evaluator_id)
        raise typer.Exit(1) from e


@evaluator_app.command("create")
def create_evaluator(
    name: str = typer.Argument(..., help="Evaluator name"),
    config: str = typer.Option(..., "--config", help="Path to evaluator config JSON file or inline JSON"),
    level: str = typer.Option("TRACE", "--level", help="Evaluation level (TRACE, SPAN, SESSION)"),
    description: Optional[str] = typer.Option(None, "--description", help="Evaluator description"),
):
    r"""Create a custom evaluator.

    Examples:
        # Create from file
        agentcore eval evaluator create my-helpfulness \
          --config evaluator-config.json \
          --level TRACE \
          --description "Custom helpfulness evaluator"

        # Create from inline JSON
        agentcore eval evaluator create my-eval \
          --config '{"llmAsAJudge": {...}}' \
          --level TRACE
    """
    try:
        # Load config (from file or inline JSON)
        config_data = None
        if config.strip().startswith("{"):
            # Inline JSON
            config_data = json.loads(config)
        else:
            # File path
            config_path = Path(config)
            if not config_path.exists():
                console.print(f"[red]Error:[/red] Config file not found: {config}")
                raise typer.Exit(1)
            with open(config_path) as f:
                config_data = json.load(f)

        # Validate required structure
        if "llmAsAJudge" not in config_data:
            console.print("[red]Error:[/red] Config must contain 'llmAsAJudge' key")
            raise typer.Exit(1)

        client = EvaluationControlPlaneClient()

        with console.status(f"[cyan]Creating evaluator '{name}'...[/cyan]"):
            response = client.create_evaluator(name=name, config=config_data, level=level, description=description)

        evaluator_id = response.get("evaluatorId", "")
        evaluator_arn = response.get("evaluatorArn", "")

        console.print("\n[green]✓[/green] Evaluator created successfully!")
        console.print(f"\n[bold]ID:[/bold] {evaluator_id}")
        console.print(f"[bold]ARN:[/bold] {evaluator_arn}")
        console.print(f"\n[dim]Use this ID with: agentcore eval run -e {evaluator_id}[/dim]")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON in config: {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Failed to create evaluator")
        raise typer.Exit(1) from e


@evaluator_app.command("update")
def update_evaluator(
    evaluator_id: str = typer.Argument(..., help="Evaluator ID to update"),
    description: Optional[str] = typer.Option(None, "--description", help="New description"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to new config JSON file"),
):
    r"""Update a custom evaluator.

    Examples:
        # Update description
        agentcore eval evaluator update my-evaluator-abc123 \
          --description "Updated description"

        # Update config
        agentcore eval evaluator update my-evaluator-abc123 \
          --config new-config.json

        # Update both
        agentcore eval evaluator update my-evaluator-abc123 \
          --description "Updated" \
          --config new-config.json
    """
    try:
        if not description and not config:
            console.print("[yellow]No updates specified. Provide --description or --config[/yellow]")
            return

        client = EvaluationControlPlaneClient()

        config_data = None
        if config:
            config_path = Path(config)
            if not config_path.exists():
                console.print(f"[red]Error:[/red] Config file not found: {config}")
                raise typer.Exit(1)
            with open(config_path) as f:
                config_data = json.load(f)

        with console.status(f"[cyan]Updating evaluator {evaluator_id}...[/cyan]"):
            response = client.update_evaluator(evaluator_id=evaluator_id, description=description, config=config_data)

        console.print("\n[green]✓[/green] Evaluator updated successfully!")
        if "updatedAt" in response:
            console.print(f"[dim]Updated at: {response['updatedAt']}[/dim]")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Failed to update evaluator %s", evaluator_id)
        raise typer.Exit(1) from e


@evaluator_app.command("delete")
def delete_evaluator(
    evaluator_id: str = typer.Argument(..., help="Evaluator ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Delete a custom evaluator.

    Examples:
        # Delete with confirmation
        agentcore eval evaluator delete my-evaluator-abc123

        # Force delete without confirmation
        agentcore eval evaluator delete my-evaluator-abc123 --force
    """
    try:
        if not force:
            confirm = typer.confirm(f"Delete evaluator '{evaluator_id}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        client = EvaluationControlPlaneClient()

        with console.status(f"[cyan]Deleting evaluator {evaluator_id}...[/cyan]"):
            client.delete_evaluator(evaluator_id=evaluator_id)

        console.print("\n[green]✓[/green] Evaluator deleted successfully")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Failed to delete evaluator %s", evaluator_id)
        raise typer.Exit(1) from e
