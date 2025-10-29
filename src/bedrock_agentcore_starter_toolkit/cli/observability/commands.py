"""Bedrock AgentCore CLI - Observability commands for querying and visualizing traces."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.text import Text

from ...operations.observability import ObservabilityClient, TraceVisualizer
from ...operations.observability.models import TraceData
from ...utils.runtime.config import load_config_if_exists
from ..common import console

# Create a module-specific logger
logger = logging.getLogger(__name__)

# Create a Typer app for observability commands
observability_app = typer.Typer(help="Query and visualize agent observability data (spans, traces, logs)")


def _get_default_time_range(days: int = 7) -> tuple[int, int]:
    """Get default time range for queries."""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    return int(start_time.timestamp() * 1000), int(end_time.timestamp() * 1000)


def _get_agent_config_from_file(agent_name: Optional[str] = None) -> Optional[dict]:
    """Load agent configuration from .bedrock_agentcore.yaml."""
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    config = load_config_if_exists(config_path)

    if not config:
        return None

    try:
        agent_config = config.get_agent_config(agent_name)
        agent_id = agent_config.bedrock_agentcore.agent_id
        agent_arn = agent_config.bedrock_agentcore.agent_arn
        session_id = agent_config.bedrock_agentcore.agent_session_id
        region = agent_config.aws.region

        if not agent_id or not region:
            return None

        return {
            "agent_id": agent_id,
            "agent_arn": agent_arn,
            "session_id": session_id,
            "region": region,
            "runtime_suffix": "DEFAULT",
        }
    except Exception as e:
        logger.debug("Failed to load agent config: %s", e)
        return None


def _create_observability_client(
    agent_id: Optional[str],
    region: Optional[str],
    agent_name: Optional[str] = None,
) -> ObservabilityClient:
    """Create ObservabilityClient from CLI args or config file."""
    # Try CLI args first
    if agent_id and region:
        return ObservabilityClient(region_name=region, agent_id=agent_id, runtime_suffix="DEFAULT")

    # Try config file
    config = _get_agent_config_from_file(agent_name)
    if config:
        return ObservabilityClient(
            region_name=config["region"], agent_id=config["agent_id"], runtime_suffix=config["runtime_suffix"]
        )

    # Neither worked
    console.print("[red]Error:[/red] Missing required parameters")
    console.print("\nProvide agent_id and region via:")
    console.print("  1. CLI arguments: --agent-id <ID> --region <REGION>")
    console.print("  2. Configuration file: .bedrock_agentcore.yaml")
    raise typer.Exit(1)


def _export_trace_data_to_json(trace_data: TraceData, output_path: str, data_type: str = "trace") -> None:
    """Export trace data to JSON file.

    Args:
        trace_data: TraceData to export
        output_path: Path to output JSON file
        data_type: Type of data for success message ("trace" or "session")
    """
    path = Path(output_path)
    try:
        with path.open("w") as f:
            json.dump(trace_data.to_dict(), f, indent=2)
        console.print(f"[green]✓[/green] Exported full {data_type} data to {path}")
    except Exception as e:
        console.print(f"[red]Error exporting to file:[/red] {str(e)}")
        logger.exception("Failed to export %s data", data_type)


@observability_app.command("show")
def show(
    trace_id: Optional[str] = typer.Option(None, "--trace-id", "-t", help="Trace ID to visualize"),
    session_id: Optional[str] = typer.Option(None, "--session-id", "-s", help="Session ID to visualize"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", "-a", help="Agent ID (or read from config)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (or read from config)"),
    agent_name: Optional[str] = typer.Option(None, "--agent-name", help="Agent name from config"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to look back"),
    all_traces: bool = typer.Option(False, "--all", help="[Session only] Show all traces in session with full details"),
    errors_only: bool = typer.Option(False, "--errors", help="[Session only] Show only failed traces"),
    simple: bool = typer.Option(False, "--simple", help="Minimal view without detailed metadata"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export to JSON file"),
    last: int = typer.Option(1, "--last", "-n", help="[Session only] Show Nth most recent trace (default: 1 = latest)"),
) -> None:
    """Show traces and sessions with explicit IDs.

    TRACE COMMANDS:
        # Show specific trace with full details
        agentcore obs show --trace-id 690156557a198c640accf1ab0fae04dd

        # Export trace to JSON
        agentcore obs show --trace-id 690156557a198c... -o trace.json

    SESSION COMMANDS:
        # Show session summary table
        agentcore obs show --session-id eb358f6f-fc68-47ed-b09a-669abfaf4469

        # Show all traces in session with full details
        agentcore obs show --session-id eb358f6f --all

        # Show only failed traces in session
        agentcore obs show --session-id eb358f6f --errors

    CONFIG SESSION COMMANDS (uses .bedrock_agentcore.yaml):
        # Show last trace from config session
        agentcore obs show

        # Show 2nd most recent trace
        agentcore obs show --last 2

        # Show all traces in config session
        agentcore obs show --all

        # Show only failed traces
        agentcore obs show --errors

    Notes:
        - --all, --errors, --last only work with sessions, not individual traces
        - Use --simple for minimal view without verbose metadata
        - Verbose mode is ON by default (shows exceptions, messages, metadata)
    """
    try:
        client = _create_observability_client(agent_id, region, agent_name)
        start_time_ms, end_time_ms = _get_default_time_range(days)

        # Verbose mode by default, unless --simple is specified
        verbose = not simple

        # Validate mutually exclusive options
        if trace_id and session_id:
            console.print("[red]Error:[/red] Cannot specify both --trace-id and --session-id")
            raise typer.Exit(1)

        # Validate incompatible option combinations
        if trace_id and all_traces:
            console.print("[red]Error:[/red] --all flag only works with sessions, not individual traces")
            console.print("[dim]Tip: Remove --all to show the trace, or use --session-id instead[/dim]")
            raise typer.Exit(1)

        if trace_id and last != 1:
            console.print("[red]Error:[/red] --last flag only works with sessions, not individual traces")
            console.print("[dim]Tip: Remove --last to show the trace, or use --session-id instead[/dim]")
            raise typer.Exit(1)

        if all_traces and last != 1:
            console.print("[red]Error:[/red] Cannot use --all and --last together")
            console.print("[dim]Use --all to show all traces, or --last N to show Nth most recent trace[/dim]")
            raise typer.Exit(1)

        # Determine what to show based on arguments
        if trace_id:
            # Show specific trace
            _show_trace_view(client, trace_id, start_time_ms, end_time_ms, verbose, output)

        elif session_id:
            # Show session: summary by default, or all traces if --all
            _show_session_view(
                client, session_id, start_time_ms, end_time_ms, verbose, not all_traces, all_traces, errors_only, output
            )

        else:
            # No ID - show from config session
            config = _get_agent_config_from_file(agent_name)
            if not config or not config.get("session_id"):
                console.print("[yellow]No ID provided and no session_id in config[/yellow]")
                console.print("\nOptions:")
                console.print("  1. Provide --trace-id or --session-id")
                console.print("  2. Set session_id in .bedrock_agentcore.yaml")
                raise typer.Exit(1)

            session_id = config["session_id"]
            console.print(f"[dim]Using session from config: {session_id}[/dim]\n")

            if all_traces:
                # Show all traces with full details
                _show_session_view(
                    client, session_id, start_time_ms, end_time_ms, verbose, False, True, errors_only, output
                )
            else:
                # Default: show last trace from session
                _show_last_trace_from_session(
                    client, session_id, start_time_ms, end_time_ms, verbose, last, errors_only, output
                )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.exception("Failed to show trace/session")
        raise typer.Exit(1) from e


def _show_trace_view(
    client: ObservabilityClient,
    trace_id: str,
    start_time_ms: int,
    end_time_ms: int,
    verbose: bool,
    output: Optional[str],
) -> None:
    """Show a specific trace."""
    console.print(f"[cyan]Fetching trace:[/cyan] {trace_id}\n")

    spans = client.query_spans_by_trace(trace_id, start_time_ms, end_time_ms)

    if not spans:
        console.print(f"[yellow]No spans found for trace {trace_id}[/yellow]")
        return

    trace_data = TraceData(spans=spans)
    trace_data.group_spans_by_trace()

    # Query runtime logs if verbose
    if verbose or output:
        try:
            runtime_logs = client.query_runtime_logs_by_traces([trace_id], start_time_ms, end_time_ms)
            trace_data.runtime_logs = runtime_logs
        except Exception as e:
            logger.warning("Failed to retrieve runtime logs: %s", e)

    if output:
        _export_trace_data_to_json(trace_data, output, data_type="trace")

    visualizer = TraceVisualizer(console)
    visualizer.visualize_trace(trace_data, trace_id, verbose=verbose)

    console.print(f"\n[green]✓[/green] Visualized {len(spans)} spans")


def _show_session_view(
    client: ObservabilityClient,
    session_id: str,
    start_time_ms: int,
    end_time_ms: int,
    verbose: bool,
    summary_only: bool,
    all_traces: bool,
    errors_only: bool,
    output: Optional[str],
) -> None:
    """Show session summary or all traces in session."""
    console.print(f"[cyan]Fetching session:[/cyan] {session_id}\n")

    spans = client.query_spans_by_session(session_id, start_time_ms, end_time_ms)

    if not spans:
        console.print(f"[yellow]No spans found for session {session_id}[/yellow]")
        return

    trace_data = TraceData(session_id=session_id, spans=spans)
    trace_data.group_spans_by_trace()

    # Filter to errors if requested
    if errors_only:
        error_traces = {
            tid: spans_list
            for tid, spans_list in trace_data.traces.items()
            if any(s.status_code == "ERROR" for s in spans_list)
        }
        if not error_traces:
            console.print("[yellow]No failed traces found in session[/yellow]")
            return
        trace_data.traces = error_traces

    # Query runtime logs if needed
    if (verbose or output) and (all_traces and not summary_only):
        try:
            trace_ids = list(trace_data.traces.keys())
            runtime_logs = client.query_runtime_logs_by_traces(trace_ids, start_time_ms, end_time_ms)
            trace_data.runtime_logs = runtime_logs
        except Exception as e:
            logger.warning("Failed to retrieve runtime logs: %s", e)

    if output:
        _export_trace_data_to_json(trace_data, output, data_type="session")

    visualizer = TraceVisualizer(console)

    if summary_only:
        # Show summary table only
        visualizer.print_trace_summary(trace_data)
    elif all_traces:
        # Show all traces with full details
        visualizer.visualize_all_traces(trace_data, verbose=verbose)
    else:
        # Default: show summary table
        visualizer.print_trace_summary(trace_data)
        console.print(
            f"\n💡 [dim]Tip: Use 'agentcore obs show --session-id {session_id} --all' to see detailed traces[/dim]"
        )

    console.print(f"\n[green]✓[/green] Found {len(trace_data.traces)} traces with {len(spans)} total spans")


def _show_last_trace_from_session(
    client: ObservabilityClient,
    session_id: str,
    start_time_ms: int,
    end_time_ms: int,
    verbose: bool,
    nth_last: int,
    errors_only: bool,
    output: Optional[str],
) -> None:
    """Show the Nth most recent trace from a session."""
    spans = client.query_spans_by_session(session_id, start_time_ms, end_time_ms)

    if not spans:
        console.print(f"[yellow]No spans found for session {session_id}[/yellow]")
        return

    trace_data = TraceData(session_id=session_id, spans=spans)
    trace_data.group_spans_by_trace()

    # Filter to errors if requested
    if errors_only:
        error_traces = {
            tid: spans_list
            for tid, spans_list in trace_data.traces.items()
            if any(s.status_code == "ERROR" for s in spans_list)
        }
        if not error_traces:
            console.print("[yellow]No failed traces found in session[/yellow]")
            return
        trace_data.traces = error_traces

    # Sort traces by most recent (using latest end time)
    def get_latest_time(spans_list):
        end_times = [s.end_time_unix_nano for s in spans_list if s.end_time_unix_nano]
        return max(end_times) if end_times else 0

    sorted_traces = sorted(trace_data.traces.items(), key=lambda x: get_latest_time(x[1]), reverse=True)

    if len(sorted_traces) < nth_last:
        console.print(f"[yellow]Only {len(sorted_traces)} trace(s) found, but you requested the {nth_last}th[/yellow]")
        nth_last = len(sorted_traces)

    # Get the Nth most recent trace
    trace_id, trace_spans = sorted_traces[nth_last - 1]

    position_text = "latest" if nth_last == 1 else f"{nth_last}th most recent"
    console.print(f"[cyan]Showing {position_text} trace from session {session_id}[/cyan]\n")

    # Build trace data for just this trace
    single_trace_data = TraceData(session_id=session_id, spans=trace_spans)
    single_trace_data.group_spans_by_trace()

    # Query runtime logs if verbose
    if verbose or output:
        try:
            runtime_logs = client.query_runtime_logs_by_traces([trace_id], start_time_ms, end_time_ms)
            single_trace_data.runtime_logs = runtime_logs
        except Exception as e:
            logger.warning("Failed to retrieve runtime logs: %s", e)

    if output:
        _export_trace_data_to_json(single_trace_data, output, data_type="trace")

    visualizer = TraceVisualizer(console)
    visualizer.visualize_trace(single_trace_data, trace_id, verbose=verbose)

    # Show helpful tips
    console.print(f"\n[green]✓[/green] Showing trace {nth_last} of {len(sorted_traces)}")
    if len(sorted_traces) > 1:
        console.print(f"💡 [dim]Tip: Use 'agentcore obs list' to see all {len(sorted_traces)} traces[/dim]")


@observability_app.command("list")
def list_traces(
    session_id: Optional[str] = typer.Option(
        None, "--session-id", "-s", help="Session ID to list traces from. Omit to use config."
    ),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", "-a", help="Agent ID (or read from config)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (or read from config)"),
    agent_name: Optional[str] = typer.Option(None, "--agent-name", help="Agent name from config"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to look back"),
    errors_only: bool = typer.Option(False, "--errors", help="Show only failed traces"),
) -> None:
    """List all traces in a session with numbered index for easy selection.

    Examples:
        # List traces from config session
        agentcore obs list

        # List traces from specific session
        agentcore obs list --session-id eb358f6f-fc68-47ed-b09a-669abfaf4469

        # List only failed traces
        agentcore obs list --errors
    """
    try:
        client = _create_observability_client(agent_id, region, agent_name)
        start_time_ms, end_time_ms = _get_default_time_range(days)

        # Get session ID from config if not provided
        if not session_id:
            config = _get_agent_config_from_file(agent_name)
            if not config or not config.get("session_id"):
                console.print("[yellow]No session ID provided and no session_id in config[/yellow]")
                console.print("\nOptions:")
                console.print("  1. Provide session ID: agentcore obs list <session-id>")
                console.print("  2. Set session_id in .bedrock_agentcore.yaml")
                raise typer.Exit(1)

            session_id = config["session_id"]
            console.print(f"[dim]Using session from config: {session_id}[/dim]\n")

        # Query spans
        console.print(f"[cyan]Fetching traces from session:[/cyan] {session_id}\n")
        spans = client.query_spans_by_session(session_id, start_time_ms, end_time_ms)

        if not spans:
            console.print(f"[yellow]No spans found for session {session_id}[/yellow]")
            return

        trace_data = TraceData(session_id=session_id, spans=spans)
        trace_data.group_spans_by_trace()

        # Filter to errors if requested
        if errors_only:
            error_traces = {
                tid: spans_list
                for tid, spans_list in trace_data.traces.items()
                if any(s.status_code == "ERROR" for s in spans_list)
            }
            if not error_traces:
                console.print("[yellow]No failed traces found in session[/yellow]")
                return
            trace_data.traces = error_traces

        # Sort traces by most recent
        def get_latest_time(spans_list):
            end_times = [s.end_time_unix_nano for s in spans_list if s.end_time_unix_nano]
            return max(end_times) if end_times else 0

        sorted_traces = sorted(trace_data.traces.items(), key=lambda x: get_latest_time(x[1]), reverse=True)

        # Display numbered list
        from datetime import datetime

        from rich.table import Table

        table = Table(title=f"Traces in Session {session_id[:16]}...")
        table.add_column("#", style="cyan", justify="right")
        table.add_column("Trace ID", style="blue")
        table.add_column("Spans", justify="right", style="dim")
        table.add_column("Duration", justify="right", style="green")
        table.add_column("Status", justify="center")
        table.add_column("Age", style="dim")

        now = datetime.now().timestamp() * 1_000_000_000  # Convert to nanoseconds

        for idx, (trace_id, spans_list) in enumerate(sorted_traces, 1):
            # Calculate duration
            start_times = [s.start_time_unix_nano for s in spans_list if s.start_time_unix_nano]
            end_times = [s.end_time_unix_nano for s in spans_list if s.end_time_unix_nano]

            if start_times and end_times:
                duration_ms = (max(end_times) - min(start_times)) / 1_000_000
            else:
                duration_ms = sum(s.duration_ms or 0 for s in spans_list)

            # Status
            error_count = sum(1 for s in spans_list if s.status_code == "ERROR")
            if error_count > 0:
                status = Text(f"❌ {error_count} err", style="red")
            else:
                status = Text("✓ OK", style="green")

            # Age
            latest_time = max(end_times) if end_times else 0
            age_seconds = (now - latest_time) / 1_000_000_000
            if age_seconds < 60:
                age = f"{int(age_seconds)}s ago"
            elif age_seconds < 3600:
                age = f"{int(age_seconds / 60)}m ago"
            elif age_seconds < 86400:
                age = f"{int(age_seconds / 3600)}h ago"
            else:
                age = f"{int(age_seconds / 86400)}d ago"

            # Mark latest
            marker = " ← Latest" if idx == 1 else ""

            table.add_row(
                str(idx),
                trace_id + marker,
                str(len(spans_list)),
                f"{duration_ms:.1f}ms",
                status,
                age,
            )

        console.print(table)

        # Show helpful tips
        console.print(f"\n[green]✓[/green] Found {len(sorted_traces)} traces")
        console.print("💡 [dim]Tip: Use 'agentcore obs show --last <N>' to view trace #N[/dim]")
        console.print("💡 [dim]     Use 'agentcore obs show --trace-id <trace-id>' to view specific trace[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.exception("Failed to list traces")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    observability_app()
