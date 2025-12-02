"""CLI commands for agent evaluation."""

import json
import logging
from pathlib import Path
from typing import List, Optional

import typer
from botocore.exceptions import ClientError

from ...operations.evaluation import evaluator_processor, online_processor
from ...operations.evaluation.control_plane_client import EvaluationControlPlaneClient
from ...operations.evaluation.data_plane_client import EvaluationDataPlaneClient
from ...operations.evaluation.formatters import (
    display_evaluation_results,
    display_evaluator_details,
    display_evaluator_list,
    save_evaluation_results,
    save_json_output,
)
from ...operations.evaluation.on_demand_processor import EvaluationProcessor
from ...utils.aws import ensure_valid_aws_creds
from ...utils.runtime.config import load_config_if_exists
from ..common import console

# Create a module-specific logger
logger = logging.getLogger(__name__)

# Create a Typer app for evaluation commands
evaluation_app = typer.Typer(help="Evaluate agent performance using built-in and custom evaluators")

# Create a sub-app for evaluator management
evaluator_app = typer.Typer(help="Manage custom evaluators (create, list, update, delete)")
evaluation_app.add_typer(evaluator_app, name="evaluator")

# Create a sub-app for online evaluation config management
online_app = typer.Typer(help="Manage online evaluation configurations for continuous evaluation")
evaluation_app.add_typer(online_app, name="online")


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
    except (KeyError, AttributeError, ValueError, FileNotFoundError) as e:
        logger.debug("Could not load agent config: %s", e)
        return None


# Removed: _display_evaluation_results - now using shared formatters.display_evaluation_results


# Removed: _save_evaluation_results - now using shared formatters.save_evaluation_results


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
    evaluators: List[str] = typer.Option(  # noqa: B008
        [], "--evaluator", "-e", help="Evaluator(s) to use (can specify multiple times)"
    ),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to look back for session data (default: 7)"),
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
    evaluator_list = evaluators if evaluators else ["Builtin.GoalSuccessRate"]

    # Display what we're doing
    console.print(f"\n[cyan]Evaluating session:[/cyan] {session_id}")
    if trace_id:
        console.print(f"[cyan]Trace:[/cyan] {trace_id} (with previous traces for context)")
    else:
        console.print("[cyan]Mode:[/cyan] All traces (most recent 1000 spans)")
    console.print(f"[cyan]Evaluators:[/cyan] {', '.join(evaluator_list)}\n")

    try:
        # Create evaluation clients and processor
        data_plane_client = EvaluationDataPlaneClient(region_name=region)
        control_plane_client = EvaluationControlPlaneClient(region_name=region)
        processor = EvaluationProcessor(data_plane_client, control_plane_client)

        # Run evaluation
        with console.status("[cyan]Running evaluation...[/cyan]"):
            results = processor.evaluate_session(
                session_id=session_id,
                evaluators=evaluator_list,
                agent_id=agent_id,
                region=region,
                trace_id=trace_id,
                days=days,
            )

        # Display results
        display_evaluation_results(results, console)

        # Save to file if requested
        if output:
            save_evaluation_results(results, output, console)

        # Exit with error code if any evaluation failed
        if results.has_errors():
            console.print("\n[yellow]Warning:[/yellow] Some evaluations failed")
            raise typer.Exit(1)

    except RuntimeError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1) from e
    except (ClientError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
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
    # Validate AWS credentials
    valid, error_msg = ensure_valid_aws_creds()
    if not valid:
        console.print(f"[red]Error:[/red] {error_msg}")
        raise typer.Exit(1)

    try:
        # Get region and client
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"
        client = EvaluationControlPlaneClient(region_name=region)

        # Fetch and display
        with console.status("[cyan]Fetching evaluators...[/cyan]"):
            response = evaluator_processor.list_evaluators(client, max_results)

        display_evaluator_list(response.get("evaluators", []), console)

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


@evaluator_app.command("get")
def get_evaluator(
    evaluator_id: str = typer.Option(
        ..., "--evaluator-id", help="Evaluator ID (e.g., Builtin.Helpfulness or custom-id)"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save to JSON file"),
):
    """Get detailed information about an evaluator.

    Examples:
        # Get builtin evaluator
        agentcore eval evaluator get --evaluator-id Builtin.Helpfulness

        # Get custom evaluator
        agentcore eval evaluator get --evaluator-id my-evaluator-abc123

        # Export to JSON
        agentcore eval evaluator get --evaluator-id my-evaluator -o evaluator.json
    """
    try:
        # Get region and client
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"
        client = EvaluationControlPlaneClient(region_name=region)

        # Fetch evaluator
        with console.status(f"[cyan]Fetching evaluator {evaluator_id}...[/cyan]"):
            response = evaluator_processor.get_evaluator(client, evaluator_id)

        # Save or display
        if output:
            save_json_output(response, output, console)
        else:
            display_evaluator_details(response, console)

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


def _interactive_create_evaluator(client: EvaluationControlPlaneClient) -> tuple:
    """Interactive mode to create evaluator by duplicating a custom one.

    Returns:
        Tuple of (source_evaluator_id, new_name, new_description)
    """
    console.print("\n[bold cyan]Interactive Evaluator Creation[/bold cyan]")
    console.print("[dim]Select a custom evaluator to duplicate[/dim]\n")

    # Fetch all evaluators
    with console.status("[cyan]Fetching evaluators...[/cyan]"):
        response = evaluator_processor.list_evaluators(client, max_results=100)

    # Filter to custom only
    evaluators = response.get("evaluators", [])
    custom_evaluators = evaluator_processor.filter_custom_evaluators(evaluators)

    if not custom_evaluators:
        console.print("[yellow]No custom evaluators found to duplicate.[/yellow]")
        console.print("[dim]Note: Built-in evaluators cannot be duplicated as their configuration is read-only.[/dim]")
        raise typer.Exit(1)

    # Display for selection
    console.print("[bold]Available Custom Evaluators:[/bold]\n")
    for idx, ev in enumerate(custom_evaluators, 1):
        name = ev.get("evaluatorName", ev.get("evaluatorId", "Unknown"))
        level = ev.get("level", "N/A")
        desc = ev.get("description", "")
        desc_preview = (desc[:60] + "...") if len(desc) > 60 else desc
        console.print(f"  {idx}. [cyan]{name}[/cyan] ({level}) - {desc_preview}")

    # Get user selection
    console.print()
    selection = typer.prompt("Select evaluator number to duplicate", type=int)

    if selection < 1 or selection > len(custom_evaluators):
        console.print("[red]Error:[/red] Invalid selection")
        raise typer.Exit(1)

    selected_evaluator = custom_evaluators[selection - 1]
    evaluator_id = selected_evaluator.get("evaluatorId", "")

    # Get new evaluator details
    console.print("\n[bold cyan]New Evaluator Details[/bold cyan]\n")

    default_name = f"copy_of_{selected_evaluator.get('evaluatorName', 'evaluator')}"
    new_name = typer.prompt("New evaluator name", default=default_name)

    original_desc = selected_evaluator.get("description", "")
    new_description = typer.prompt("Description", default=original_desc)

    return evaluator_id, new_name, new_description


@evaluator_app.command("create")
def create_evaluator(
    name: Optional[str] = typer.Option(None, "--name", help="Evaluator name"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to evaluator config JSON file or inline JSON"),
    level: Optional[str] = typer.Option(None, "--level", help="Evaluation level (SESSION, TRACE, TOOL_CALL)"),
    description: Optional[str] = typer.Option(None, "--description", help="Evaluator description"),
):
    r"""Create a custom evaluator.

    When --config is not provided, enters interactive mode to duplicate an existing evaluator.

    Examples:
        # Interactive mode - duplicate and edit existing evaluator
        agentcore eval evaluator create

        # Create from file
        agentcore eval evaluator create --name my-helpfulness \
          --config evaluator-config.json \
          --level TRACE \
          --description "Custom helpfulness evaluator"

        # Create from inline JSON
        agentcore eval evaluator create --name my-eval \
          --config '{"llmAsAJudge": {...}}' \
          --level TRACE
    """
    try:
        # Get region and client
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"
        client = EvaluationControlPlaneClient(region_name=region)

        # Interactive mode - duplicate existing evaluator
        if not config:
            source_evaluator_id, name, description = _interactive_create_evaluator(client)

            with console.status(f"[cyan]Creating evaluator '{name}'...[/cyan]"):
                response = evaluator_processor.duplicate_evaluator(client, source_evaluator_id, name, description)

        # Non-interactive mode - create from config
        else:
            if not name:
                console.print("[red]Error:[/red] Name is required when using --config")
                raise typer.Exit(1)

            # Load config from file or inline JSON
            if config.strip().startswith("{"):
                config_data = json.loads(config)
            else:
                config_path = Path(config)
                if not config_path.exists():
                    console.print(f"[red]Error:[/red] Config file not found: {config}")
                    raise typer.Exit(1)
                with open(config_path) as f:
                    config_data = json.load(f)

            # Create evaluator
            with console.status(f"[cyan]Creating evaluator '{name}'...[/cyan]"):
                response = evaluator_processor.create_evaluator(
                    client, name, config_data, level or "TRACE", description
                )

        # Display success
        evaluator_id = response.get("evaluatorId", "")
        evaluator_arn = response.get("evaluatorArn", "")

        console.print("\n[green]✓[/green] Evaluator created successfully!")
        console.print(f"\n[bold]ID:[/bold] {evaluator_id}")
        console.print(f"[bold]ARN:[/bold] {evaluator_arn}")
        console.print(f"\n[dim]Use this ID with: agentcore eval run -e {evaluator_id}[/dim]")

    except json.JSONDecodeError as e:
        console.print(f"[red]Error:[/red] Invalid JSON in config: {e}")
        raise typer.Exit(1) from e
    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


@evaluator_app.command("update")
def update_evaluator(
    evaluator_id: str = typer.Option(..., "--evaluator-id", help="Evaluator ID to update"),
    description: Optional[str] = typer.Option(None, "--description", help="New description"),
    config: Optional[str] = typer.Option(None, "--config", help="Path to new config JSON file"),
):
    r"""Update a custom evaluator.

    Examples:
        # Update description
        agentcore eval evaluator update --evaluator-id my-evaluator-abc123 \
          --description "Updated description"

        # Update config
        agentcore eval evaluator update --evaluator-id my-evaluator-abc123 \
          --config new-config.json

        # Update both
        agentcore eval evaluator update --evaluator-id my-evaluator-abc123 \
          --description "Updated" \
          --config new-config.json
    """
    try:
        if description is None and config is None:
            console.print("[red]Error:[/red] At least one of --description or --config is required")
            raise typer.Exit(1)

        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"

        client = EvaluationControlPlaneClient(region_name=region)

        config_to_update = None
        if config:
            config_path = Path(config)
            if not config_path.exists():
                console.print(f"[red]Error:[/red] Config file not found: {config}")
                raise typer.Exit(1)
            with open(config_path) as f:
                config_to_update = json.load(f)

        with console.status(f"[cyan]Updating evaluator {evaluator_id}...[/cyan]"):
            response = evaluator_processor.update_evaluator(client, evaluator_id, description, config_to_update)

        console.print("\n[green]✓[/green] Evaluator updated successfully!")
        if "updatedAt" in response:
            console.print(f"[dim]Updated at: {response['updatedAt']}[/dim]")

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


@evaluator_app.command("delete")
def delete_evaluator(
    evaluator_id: str = typer.Option(..., "--evaluator-id", help="Evaluator ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Delete a custom evaluator.

    Examples:
        # Delete with confirmation
        agentcore eval evaluator delete --evaluator-id my-evaluator-abc123

        # Force delete without confirmation
        agentcore eval evaluator delete --evaluator-id my-evaluator-abc123 --force
    """
    try:
        if not force:
            confirm = typer.confirm(f"Delete evaluator '{evaluator_id}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Get region from config or use default
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"

        client = EvaluationControlPlaneClient(region_name=region)

        with console.status(f"[cyan]Deleting evaluator {evaluator_id}...[/cyan]"):
            evaluator_processor.delete_evaluator(client, evaluator_id)

        console.print("\n[green]✓[/green] Evaluator deleted successfully")

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


# =============================================================================
# Online Evaluation Config Commands
# =============================================================================


@online_app.command("create")
def create_online_config(
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Agent ID (uses config file if not provided)"),
    config_name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Name for the online evaluation configuration"
    ),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name from config file"),
    endpoint: str = typer.Option("DEFAULT", "--endpoint", help="Agent endpoint (DEFAULT, DRAFT, or alias ARN)"),
    sampling_rate: float = typer.Option(1.0, "--sampling-rate", "-s", help="Sampling rate percentage (0-100)"),
    evaluators: List[str] = typer.Option(  # noqa: B008
        [], "--evaluator", "-e", help="Evaluator ID(s) to use (can specify multiple times)"
    ),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Config description"),
    execution_role: Optional[str] = typer.Option(
        None, "--execution-role", help="IAM role ARN (auto-creates if not provided)"
    ),
    no_auto_create_role: bool = typer.Option(False, "--no-auto-create-role", help="Disable automatic role creation"),
    disabled: bool = typer.Option(False, "--disabled", help="Create config in disabled state"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save config details to JSON file"),
):
    r"""Create online evaluation configuration for continuous agent evaluation.

    Monitors CloudWatch logs and evaluates sampled agent interactions in real-time.

    Examples:
        # Create with defaults (1% sampling, auto-create role)
        agentcore eval online create --agent-id agent-123 -n my-config

        # Create with custom settings
        agentcore eval online create --agent-id agent-123 -n prod-eval \\
            --sampling-rate 5.0 \\
            --evaluator Builtin.Helpfulness \\
            --evaluator Builtin.Accuracy \\
            --description "Production evaluation"

        # Use agent from config file
        agentcore eval online create --agent my-agent -n my-config

        # Create disabled (enable later)
        agentcore eval online create --agent-id agent-123 -n my-config --disabled
    """
    try:
        # Validate required parameters
        if not config_name:
            console.print("[red]Error:[/red] --name/-n is required")
            raise typer.Exit(1)

        # Get agent config from file if agent name provided
        agent_config = None
        if agent:
            agent_config = _get_agent_config_from_file(agent)
            if not agent_config:
                console.print(f"[red]Error:[/red] Agent '{agent}' not found in config file")
                raise typer.Exit(1)
            agent_id = agent_id or agent_config.get("agent_id")
            region = agent_config.get("region")
        elif not agent_id:
            # Try to get from default config
            agent_config = _get_agent_config_from_file()
            if agent_config:
                agent_id = agent_id or agent_config.get("agent_id")
                region = agent_config.get("region")
            else:
                region = None

        if not agent_id:
            console.print("[red]Error:[/red] --agent-id is required (or configure agent in .bedrock_agentcore.yaml)")
            raise typer.Exit(1)

        # Get region
        if not agent_config:
            agent_config = _get_agent_config_from_file()
        region = (agent_config.get("region") if agent_config else None) or "us-east-1"

        console.print(f"\n[cyan]Creating online evaluation config:[/cyan] {config_name}")
        console.print(f"[cyan]Agent ID:[/cyan] {agent_id}")
        console.print(f"[cyan]Region:[/cyan] {region}")
        console.print(f"[cyan]Sampling Rate:[/cyan] {sampling_rate}%")
        console.print(f"[cyan]Evaluators:[/cyan] {evaluators or ['Builtin.GoalSuccessRate']}")
        console.print(f"[cyan]Endpoint:[/cyan] {endpoint}\n")

        client = EvaluationControlPlaneClient(region_name=region)

        with console.status("[cyan]Creating configuration...[/cyan]"):
            response = online_processor.create_online_evaluation_config(
                client=client,
                config_name=config_name,
                agent_id=agent_id,
                agent_endpoint=endpoint,
                config_description=description,
                sampling_rate=sampling_rate,
                evaluator_list=evaluators,
                execution_role=execution_role,
                auto_create_execution_role=not no_auto_create_role,
                enable_on_create=not disabled,
            )

        config_id = response.get("onlineEvaluationConfigId", "")
        status = response.get("status", "ENABLED" if not disabled else "DISABLED")

        # Extract output log group from outputConfig
        output_config = response.get("outputConfig", {})
        cloudwatch_config = output_config.get("cloudWatchConfig", {})
        output_log_group = cloudwatch_config.get("logGroupName", "N/A")

        console.print("\n[green]✓[/green] Online evaluation config created successfully!")
        console.print(f"\n[bold]Config ID:[/bold] {config_id}")
        console.print(f"[bold]Config Name:[/bold] {config_name}")
        console.print(f"[bold]Status:[/bold] {status}")
        console.print(f"[bold]Execution Role:[/bold] {response.get('evaluationExecutionRoleArn', 'N/A')}")
        console.print(f"[bold]Output Log Group:[/bold] {output_log_group}")

        if output:
            save_json_output(response, output, console)

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


@online_app.command("get")
def get_online_config(
    config_id: str = typer.Option(..., "--config-id", help="Online evaluation config ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save config details to JSON file"),
):
    """Get online evaluation configuration details.

    Examples:
        agentcore eval online get --config-id config-abc123
        agentcore eval online get --config-id config-abc123 --output details.json
    """
    try:
        # Get region from config or use default
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"

        client = EvaluationControlPlaneClient(region_name=region)

        with console.status(f"[cyan]Fetching config {config_id}...[/cyan]"):
            response = online_processor.get_online_evaluation_config(
                client=client,
                config_id=config_id,
            )

        # Display config details
        console.print(f"\n[bold]Config Name:[/bold] {response.get('onlineEvaluationConfigName', 'N/A')}")
        console.print(f"[bold]Config ID:[/bold] {response.get('onlineEvaluationConfigId', 'N/A')}")
        console.print(f"[bold]Status:[/bold] {response.get('status', 'N/A')}")
        console.print(f"[bold]Execution Status:[/bold] {response.get('executionStatus', 'N/A')}")

        # Extract sampling rate from rule.samplingConfig.samplingPercentage
        rule = response.get("rule", {})
        sampling_config = rule.get("samplingConfig", {})
        sampling_rate = sampling_config.get("samplingPercentage", "N/A")
        console.print(f"[bold]Sampling Rate:[/bold] {sampling_rate}%")

        # Extract evaluator IDs from evaluators array
        evaluators = response.get("evaluators", [])
        evaluator_ids = [e.get("evaluatorId", "") for e in evaluators if isinstance(e, dict)]
        console.print(f"[bold]Evaluators:[/bold] {', '.join(evaluator_ids) if evaluator_ids else 'N/A'}")

        console.print(f"[bold]Execution Role:[/bold] {response.get('evaluationExecutionRoleArn', 'N/A')}")

        # Extract and display output log group from outputConfig
        output_config = response.get("outputConfig", {})
        cloudwatch_config = output_config.get("cloudWatchConfig", {})
        output_log_group = cloudwatch_config.get("logGroupName", "N/A")
        console.print(f"\n[bold]Output Log Group:[/bold] {output_log_group}")

        if response.get("description"):
            console.print(f"\n[bold]Description:[/bold] {response['description']}")

        if output:
            save_json_output(response, output, console)

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


@online_app.command("list")
def list_online_configs(
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Filter by agent ID"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Filter by agent name from config file"),
    max_results: int = typer.Option(50, "--max-results", help="Maximum number of configs to return"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save configs list to JSON file"),
):
    """List online evaluation configurations.

    Examples:
        agentcore eval online list
        agentcore eval online list --agent-id agent-123
        agentcore eval online list --agent my-agent
        agentcore eval online list --max-results 100 --output configs.json
    """
    try:
        # Get agent ID from config if agent name provided
        if agent:
            agent_config = _get_agent_config_from_file(agent)
            if not agent_config:
                console.print(f"[red]Error:[/red] Agent '{agent}' not found in config file")
                raise typer.Exit(1)
            agent_id = agent_id or agent_config.get("agent_id")

        # Get region from config or use default
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"

        client = EvaluationControlPlaneClient(region_name=region)

        with console.status("[cyan]Fetching online evaluation configs...[/cyan]"):
            response = online_processor.list_online_evaluation_configs(
                client=client,
                agent_id=agent_id,
                max_results=max_results,
            )

        configs = response.get("onlineEvaluationConfigs", [])

        console.print(f"\n[cyan]Found {len(configs)} online evaluation config(s)[/cyan]\n")

        if configs:
            from rich.table import Table

            table = Table(show_header=True)
            table.add_column("Config Name", style="cyan")
            table.add_column("Config ID", style="dim")
            table.add_column("Status", style="green")
            table.add_column("Execution", style="yellow")
            table.add_column("Created", style="dim")

            for config in configs:
                status_color = "green" if config.get("status") == "ACTIVE" else "yellow"
                exec_status_color = "green" if config.get("executionStatus") == "ENABLED" else "red"

                # Format createdAt timestamp
                created_at = config.get("createdAt")
                if created_at:
                    created_at_str = str(created_at) if not isinstance(created_at, str) else created_at
                else:
                    created_at_str = "N/A"

                table.add_row(
                    config.get("onlineEvaluationConfigName", "N/A"),
                    config.get("onlineEvaluationConfigId", "N/A"),
                    f"[{status_color}]{config.get('status', 'N/A')}[/{status_color}]",
                    f"[{exec_status_color}]{config.get('executionStatus', 'N/A')}[/{exec_status_color}]",
                    created_at_str,
                )

            console.print(table)

        if output:
            save_json_output(response, output, console)

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


@online_app.command("update")
def update_online_config(
    config_id: str = typer.Option(..., "--config-id", help="Online evaluation config ID to update"),
    status: Optional[str] = typer.Option(None, "--status", help="New status (ENABLED or DISABLED)"),
    sampling_rate: Optional[float] = typer.Option(None, "--sampling-rate", "-s", help="New sampling rate (0-100)"),
    evaluators: Optional[List[str]] = typer.Option(  # noqa: B008
        None, "--evaluator", "-e", help="New evaluator list (replaces existing, can specify multiple)"
    ),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save updated config to JSON file"),
):
    r"""Update online evaluation configuration.

    Examples:
        # Disable config
        agentcore eval online update --config-id config-abc123 --status DISABLED

        # Change sampling rate
        agentcore eval online update --config-id config-abc123 --sampling-rate 10.0

        # Update evaluators
        agentcore eval online update --config-id config-abc123 \
            --evaluator Builtin.Helpfulness \
            --evaluator Builtin.Correctness

        # Update multiple settings
        agentcore eval online update --config-id config-abc123 \
            --status ENABLED \
            --sampling-rate 5.0 \
            --description "Updated config"
    """
    try:
        # Validate at least one update parameter provided
        if not any([status, sampling_rate is not None, evaluators, description]):
            console.print("[red]Error:[/red] At least one update parameter required")
            console.print("Use --status, --sampling-rate, --evaluator, or --description")
            raise typer.Exit(1)

        # Validate status if provided
        if status and status not in ["ENABLED", "DISABLED"]:
            console.print("[red]Error:[/red] Status must be ENABLED or DISABLED")
            raise typer.Exit(1)

        # Get region from config or use default
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"

        client = EvaluationControlPlaneClient(region_name=region)

        console.print(f"\n[cyan]Updating config:[/cyan] {config_id}")
        if status:
            console.print(f"[cyan]→ Status:[/cyan] {status}")
        if sampling_rate is not None:
            console.print(f"[cyan]→ Sampling Rate:[/cyan] {sampling_rate}%")
        if evaluators:
            console.print(f"[cyan]→ Evaluators:[/cyan] {evaluators}")
        if description:
            console.print(f"[cyan]→ Description:[/cyan] {description}\n")

        with console.status(f"[cyan]Updating config {config_id}...[/cyan]"):
            response = online_processor.update_online_evaluation_config(
                client=client,
                config_id=config_id,
                status=status,
                sampling_rate=sampling_rate,
                evaluator_list=evaluators,
                description=description,
            )

        console.print("\n[green]✓[/green] Online evaluation config updated successfully!")

        if output:
            save_json_output(response, output, console)

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e


@online_app.command("delete")
def delete_online_config(
    config_id: str = typer.Option(..., "--config-id", help="Online evaluation config ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip all confirmation prompts"),
    delete_role: Optional[bool] = typer.Option(
        None, "--delete-role/--no-delete-role", help="Delete IAM execution role"
    ),
):
    """Delete online evaluation configuration.

    By default, prompts whether to delete the config and whether to delete the IAM role.
    Use --force to skip all prompts. Use --delete-role or --no-delete-role to specify role deletion without prompting.

    Examples:
        # Delete config with prompts (asks about config and role)
        agentcore eval online delete --config-id config-abc123

        # Delete config without prompts, keep IAM role
        agentcore eval online delete --config-id config-abc123 --force --no-delete-role

        # Delete config and role without prompts
        agentcore eval online delete --config-id config-abc123 --force --delete-role
    """
    try:
        # Prompt for config deletion confirmation
        if not force:
            confirm = typer.confirm(f"Delete online evaluation config '{config_id}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Prompt for role deletion if not explicitly specified
        if delete_role is None and not force:
            delete_role = typer.confirm("Also delete the IAM execution role?", default=False)
        elif delete_role is None:
            # If force=True and delete_role not specified, default to False
            delete_role = False

        # Get region from config or use default
        agent_config = _get_agent_config_from_file()
        region = agent_config.get("region", "us-east-1") if agent_config else "us-east-1"

        client = EvaluationControlPlaneClient(region_name=region)

        status_msg = f"[cyan]Deleting config {config_id}"
        if delete_role:
            status_msg += " and execution role"
        status_msg += "...[/cyan]"

        with console.status(status_msg):
            online_processor.delete_online_evaluation_config(
                client=client,
                config_id=config_id,
                delete_execution_role=delete_role,
            )

        console.print("\n[green]✓[/green] Online evaluation config deleted successfully")
        if delete_role:
            console.print("[green]✓[/green] IAM execution role deleted successfully")
        else:
            console.print("[dim]IAM execution role preserved for reuse[/dim]")

    except (ClientError, RuntimeError, ValueError, KeyError, TypeError) as e:
        console.print(f"\n[red]Error:[/red] {e}")
        logger.exception("Operation failed")
        raise typer.Exit(1) from e
