"""Notebook interface for observability - thin wrappers over operations."""

import logging
from typing import Optional

from rich.console import Console

from ...operations.constants import DEFAULT_LOOKBACK_DAYS, DEFAULT_RUNTIME_SUFFIX
from ...operations.observability import TraceVisualizer
from ...operations.observability.telemetry import TraceData
from ...operations.observability.trace_processor import TraceProcessor

# Configure logger
log = logging.getLogger(__name__)


class Observability:
    """Notebook interface for observability - mirrors CLI commands.

    Thin wrappers over operations that the CLI uses.

    Example:
        >>> from bedrock_agentcore_starter_toolkit.notebook import Observability
        >>>
        >>> obs = Observability(agent_id="my-agent", region="us-east-1")
        >>>
        >>> # Mirror CLI commands
        >>> obs.list(session_id="abc123")
        >>> obs.show(session_id="abc123")
        >>> obs.show(trace_id="def456")
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        region: Optional[str] = None,
        runtime_suffix: str = DEFAULT_RUNTIME_SUFFIX,
    ):
        """Initialize observability interface.

        Args:
            agent_id: Agent ID (required if agent_name not provided)
            agent_name: Agent name to load from config
            region: AWS region (auto-detected if not provided)
            runtime_suffix: Runtime log group suffix
        """
        self.console = Console()

        # Reuse CLI's client creation logic to avoid duplication
        from ...cli.observability.commands import _create_observability_client

        # Get stateless client + agent context
        # Helper returns tuple: (client, agent_id, endpoint_name)
        self.client, self.agent_id, self.endpoint_name = _create_observability_client(
            agent=agent_name,
            agent_id=agent_id,
            region=region,
            runtime_suffix=runtime_suffix,
        )

        # Store region for reference
        self.region = self.client.region

        # Initialize visualizer
        self.visualizer = TraceVisualizer(self.console)

    def list(
        self,
        session_id: Optional[str] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        errors: bool = False,
    ) -> TraceData:
        """List traces (equivalent to `agentcore obs list`).

        Args:
            session_id: Session ID (auto-discovers if None)
            days: Number of days to look back
            errors: Show only failed traces

        Returns:
            TraceData with traces and runtime logs

        Example:
            >>> obs.list(session_id="abc123")
            >>> obs.list(errors=True)
        """
        # Reuse CLI logic
        from ...cli.observability.commands import _get_default_time_range

        start_time_ms, end_time_ms = _get_default_time_range(days)

        # Auto-discover session if needed
        if not session_id:
            self.console.print("[dim]Fetching latest session...[/dim]")
            session_id = self.client.get_latest_session_id(start_time_ms, end_time_ms, agent_id=self.agent_id)
            if not session_id:
                self.console.print(f"[yellow]No sessions found (last {days} days)[/yellow]")
                return TraceData(spans=[])
            self.console.print(f"[dim]Using session: {session_id}[/dim]\n")

        # Query and display - reuse CLI display logic
        self.console.print(f"[cyan]Fetching traces from session:[/cyan] {session_id}\n")
        spans = self.client.query_spans_by_session(session_id, start_time_ms, end_time_ms, agent_id=self.agent_id)

        if not spans:
            self.console.print("[yellow]No spans found[/yellow]")
            return TraceData(session_id=session_id, spans=[])

        trace_data = TraceData(session_id=session_id, spans=spans, agent_id=self.agent_id)
        TraceProcessor.group_spans_by_trace(trace_data)

        # Filter errors if requested
        if errors:
            error_traces = TraceProcessor.filter_error_traces(trace_data)
            if not error_traces:
                self.console.print("[yellow]No failed traces found[/yellow]")
                return trace_data
            trace_data.traces = error_traces

        # Fetch runtime logs for display
        self.console.print("[dim]Fetching runtime logs...[/dim]")
        trace_ids = list(trace_data.traces.keys())
        runtime_logs = self.client.query_runtime_logs_by_traces(
            trace_ids, start_time_ms, end_time_ms, agent_id=self.agent_id, endpoint_name=self.endpoint_name
        )
        trace_data.runtime_logs = runtime_logs

        # Display using same function as CLI
        from ...cli.observability.commands import _display_trace_list

        _display_trace_list(trace_data, session_id)

        return trace_data

    def show(
        self,
        trace_id: Optional[str] = None,
        session_id: Optional[str] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
        all: bool = False,
        last: int = 1,
        errors: bool = False,
        verbose: bool = False,
        output: Optional[str] = None,
    ) -> TraceData:
        """Show traces (equivalent to `agentcore obs show`).

        Args:
            trace_id: Show specific trace
            session_id: Session ID (auto-discovers if None)
            days: Number of days to look back
            all: Show all traces in session
            last: Show Nth most recent trace
            errors: Show only failed traces
            verbose: Show full payloads without truncation
            output: Export to JSON file

        Returns:
            TraceData object

        Examples:
            >>> obs.show(session_id="abc123")
            >>> obs.show(session_id="abc123", all=True)
            >>> obs.show(trace_id="def456")
            >>> obs.show(trace_id="def456", output="trace.json")
        """
        # Reuse CLI logic
        from ...cli.observability.commands import (
            _get_default_time_range,
            _show_session_view,
            _show_trace_view,
        )

        start_time_ms, end_time_ms = _get_default_time_range(days)

        # Validate conflicting options
        if trace_id and session_id:
            raise ValueError("Cannot specify both trace_id and session_id")
        if trace_id and all:
            raise ValueError("--all only works with sessions")
        if trace_id and last != 1:
            raise ValueError("--last only works with sessions")
        if all and last != 1:
            raise ValueError("Cannot use --all and --last together")

        # Show specific trace
        if trace_id:
            _show_trace_view(
                self.client,
                trace_id,
                start_time_ms,
                end_time_ms,
                verbose,
                output,
                agent_id=self.agent_id,
                endpoint_name=self.endpoint_name,
            )
            # Return TraceData for programmatic use
            spans = self.client.query_spans_by_trace(trace_id, start_time_ms, end_time_ms, agent_id=self.agent_id)
            trace_data = TraceData(spans=spans, agent_id=self.agent_id)
            TraceProcessor.group_spans_by_trace(trace_data)
            runtime_logs = self.client.query_runtime_logs_by_traces(
                [trace_id], start_time_ms, end_time_ms, agent_id=self.agent_id, endpoint_name=self.endpoint_name
            )
            trace_data.runtime_logs = runtime_logs
            return trace_data

        # Auto-discover session if needed
        if not session_id:
            self.console.print("[dim]Fetching latest session...[/dim]")
            session_id = self.client.get_latest_session_id(start_time_ms, end_time_ms, agent_id=self.agent_id)
            if not session_id:
                self.console.print(f"[yellow]No sessions found (last {days} days)[/yellow]")
                return TraceData(spans=[])
            self.console.print(f"[dim]Using session: {session_id}[/dim]\n")

        # Show traces from session (all or Nth most recent)
        _show_session_view(
            self.client,
            session_id,
            start_time_ms,
            end_time_ms,
            verbose,
            errors,
            output,
            agent_id=self.agent_id,
            endpoint_name=self.endpoint_name,
            show_all=all,
            nth_last=last,
        )

        # Return TraceData for programmatic use
        spans = self.client.query_spans_by_session(session_id, start_time_ms, end_time_ms, agent_id=self.agent_id)
        trace_data = TraceData(session_id=session_id, spans=spans, agent_id=self.agent_id)
        TraceProcessor.group_spans_by_trace(trace_data)

        if errors:
            trace_data.traces = TraceProcessor.filter_error_traces(trace_data)

        if all:
            # Return all traces
            trace_ids = list(trace_data.traces.keys())
            runtime_logs = self.client.query_runtime_logs_by_traces(
                trace_ids, start_time_ms, end_time_ms, agent_id=self.agent_id, endpoint_name=self.endpoint_name
            )
            trace_data.runtime_logs = runtime_logs
            return trace_data
        else:
            # Return Nth most recent trace
            def get_latest_time(spans_list):
                end_times = [s.end_time_unix_nano for s in spans_list if s.end_time_unix_nano]
                return max(end_times) if end_times else 0

            sorted_traces = sorted(trace_data.traces.items(), key=lambda x: get_latest_time(x[1]), reverse=True)
            if sorted_traces and last <= len(sorted_traces):
                trace_id, trace_spans = sorted_traces[last - 1]
                single_trace_data = TraceData(session_id=session_id, spans=trace_spans, agent_id=self.agent_id)
                TraceProcessor.group_spans_by_trace(single_trace_data)
                runtime_logs = self.client.query_runtime_logs_by_traces(
                    [trace_id], start_time_ms, end_time_ms, agent_id=self.agent_id, endpoint_name=self.endpoint_name
                )
                single_trace_data.runtime_logs = runtime_logs
                return single_trace_data

            return trace_data
