"""Display formatters for evaluation operations.

Centralized formatting logic for CLI and notebook interfaces.
All display/UI logic that was duplicated between CLI and notebook is consolidated here.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import EvaluationResults


def display_evaluator_list(evaluators: List[Dict[str, Any]], console: Console) -> None:
    """Display formatted list of evaluators.

    Args:
        evaluators: List of evaluator dicts from API
        console: Rich console for output
    """
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
        builtin_table.add_column("ID", style="cyan", no_wrap=True)
        builtin_table.add_column("Name", style="white")
        builtin_table.add_column("Level", style="yellow", width=10)
        builtin_table.add_column("Description", style="dim")

        for ev in sorted(builtin, key=lambda x: x.get("evaluatorId", "")):
            level = ev.get("level", "N/A")
            builtin_table.add_row(
                ev.get("evaluatorId", ""), ev.get("evaluatorName", ""), level, ev.get("description", "")
            )

        console.print(builtin_table)

    # Display custom evaluators
    if custom:
        console.print(f"\n[bold green]Custom Evaluators ({len(custom)})[/bold green]\n")

        custom_table = Table(show_header=True)
        custom_table.add_column("ID", style="green", no_wrap=True)
        custom_table.add_column("Name", style="white")
        custom_table.add_column("Level", style="yellow", width=10)
        custom_table.add_column("Description", style="dim")

        for ev in sorted(custom, key=lambda x: x.get("createdAt", ""), reverse=True):
            level = ev.get("level", "N/A")

            custom_table.add_row(
                ev.get("evaluatorId", ""), ev.get("evaluatorName", ""), level, ev.get("description", "")
            )

        console.print(custom_table)

    console.print(f"\n[dim]Total: {len(evaluators)} ({len(builtin)} builtin, {len(custom)} custom)[/dim]")


def display_evaluator_details(details: Dict[str, Any], console: Console) -> None:
    """Display detailed evaluator information.

    Args:
        details: Evaluator details dict from API
        console: Rich console for output
    """
    console.print("\n[bold cyan]Evaluator Details[/bold cyan]\n")

    # Basic metadata
    console.print(f"[bold]ID:[/bold] {details.get('evaluatorId', '')}")
    console.print(f"[bold]Name:[/bold] {details.get('evaluatorName', '')}")
    console.print(f"[bold]ARN:[/bold] {details.get('evaluatorArn', '')}")
    console.print(f"[bold]Level:[/bold] {details.get('level', '')}")

    if "createdAt" in details:
        console.print(f"[bold]Created:[/bold] {details['createdAt']}")
    if "updatedAt" in details:
        console.print(f"[bold]Updated:[/bold] {details['updatedAt']}")

    # Description (full text)
    if "description" in details:
        console.print(f"\n[bold]Description:[/bold]\n{details['description']}")

    # Config details
    if "evaluatorConfig" in details:
        config = details["evaluatorConfig"]
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
                if scale:
                    min_val = scale[0].get("value", 0)
                    max_val = scale[-1].get("value", 1)
                    console.print(f"  Rating Scale: {len(scale)} levels ({min_val} - {max_val})")

            # Instructions (full text)
            if "instructions" in llm_config:
                instructions = llm_config["instructions"]
                console.print(f"\n[bold]Instructions:[/bold]\n{instructions}")


def display_evaluation_results(results: EvaluationResults, console: Console) -> None:
    """Display evaluation results in formatted way.

    Args:
        results: EvaluationResults object
        console: Rich console for output
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


# =============================================================================
# File Operations
# =============================================================================


def save_evaluation_results(results: EvaluationResults, output_file: str, console: Console) -> None:
    """Save evaluation results to a JSON file.

    Args:
        results: EvaluationResults object
        output_file: Path to output file
        console: Rich console for output
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


def save_json_output(data: Dict[str, Any], output_file: str, console: Console) -> None:
    """Save JSON data to file.

    Args:
        data: Data to save
        output_file: Path to output file
        console: Rich console for output
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    console.print(f"\n[green]✓[/green] Saved to: {output_path}")
