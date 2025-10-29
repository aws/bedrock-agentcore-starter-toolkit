"""Trace visualization with hierarchical tree views."""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from ..models.telemetry import Span, TraceData


class TraceVisualizer:
    """Visualizer for displaying traces in an intuitive hierarchical format."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the trace visualizer.

        Args:
            console: Optional Rich console for output
        """
        self.console = console or Console()

    def visualize_trace(self, trace_data: TraceData, trace_id: str, verbose: bool = False) -> None:
        """Visualize a single trace as a hierarchical tree.

        Args:
            trace_data: TraceData containing the spans
            trace_id: The trace ID to visualize
            verbose: Whether to show detailed span info, chat messages, event payloads, and metadata
        """
        # Ensure spans are grouped and hierarchy is built
        if trace_id not in trace_data.traces:
            trace_data.group_spans_by_trace()

        if trace_id not in trace_data.traces:
            self.console.print(f"[red]Trace {trace_id} not found[/red]")
            return

        # Build span hierarchy
        root_spans = trace_data.build_span_hierarchy(trace_id)

        if not root_spans:
            self.console.print(f"[yellow]No spans found for trace {trace_id}[/yellow]")
            return

        # Get messages grouped by span if verbose is enabled
        messages_by_span = trace_data.get_messages_by_span() if verbose else {}

        # Extract common fields to avoid repeating them
        spans = trace_data.traces[trace_id]
        session_ids = {s.attributes.get("session.id") for s in spans if s.attributes.get("session.id")}
        service_names = {s.service_name for s in spans if s.service_name}

        # Use common values if all spans share them, otherwise None
        common_session_id = next(iter(session_ids)) if len(session_ids) == 1 else None
        common_service_name = next(iter(service_names)) if len(service_names) == 1 else None

        # Create the tree
        trace_tree = Tree(
            self._format_trace_header(trace_id, trace_data.traces[trace_id]),
            guide_style="cyan",
        )

        # Add each root span and its children
        for root_span in root_spans:
            self._add_span_to_tree(
                trace_tree,
                root_span,
                verbose,
                messages_by_span,
                common_session_id=common_session_id,
                common_service_name=common_service_name,
            )

        self.console.print(trace_tree)

    def visualize_all_traces(self, trace_data: TraceData, verbose: bool = False) -> None:
        """Visualize all traces in the trace data.

        Args:
            trace_data: TraceData containing the spans
            verbose: Whether to show detailed span info, chat messages, event payloads, and metadata
        """
        trace_data.group_spans_by_trace()

        if not trace_data.traces:
            self.console.print("[yellow]No traces found[/yellow]")
            return

        self.console.print(f"\n[bold cyan]Found {len(trace_data.traces)} traces:[/bold cyan]\n")

        # Get messages once for all traces
        messages_by_span = trace_data.get_messages_by_span() if verbose else {}

        for trace_id in trace_data.traces:
            # Build hierarchy
            root_spans = trace_data.build_span_hierarchy(trace_id)

            if not root_spans:
                continue

            # Extract common fields to avoid repeating them
            spans = trace_data.traces[trace_id]
            session_ids = {s.attributes.get("session.id") for s in spans if s.attributes.get("session.id")}
            service_names = {s.service_name for s in spans if s.service_name}

            # Use common values if all spans share them, otherwise None
            common_session_id = next(iter(session_ids)) if len(session_ids) == 1 else None
            common_service_name = next(iter(service_names)) if len(service_names) == 1 else None

            # Create the tree
            trace_tree = Tree(
                self._format_trace_header(trace_id, trace_data.traces[trace_id]),
                guide_style="cyan",
            )

            # Add each root span and its children
            for root_span in root_spans:
                self._add_span_to_tree(
                    trace_tree,
                    root_span,
                    verbose,
                    messages_by_span,
                    common_session_id=common_session_id,
                    common_service_name=common_service_name,
                )

            self.console.print(trace_tree)
            self.console.print()  # Empty line between traces

    def _format_trace_header(self, trace_id: str, spans: List[Span]) -> Text:
        """Format the trace header with summary information.

        Args:
            trace_id: The trace ID
            spans: List of spans in the trace

        Returns:
            Formatted Rich Text object
        """
        # Calculate actual trace duration from earliest start to latest end
        # Don't sum spans as that double-counts nested spans
        start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
        end_times = [s.end_time_unix_nano for s in spans if s.end_time_unix_nano]

        if start_times and end_times:
            # Convert nanoseconds to milliseconds
            total_duration = (max(end_times) - min(start_times)) / 1_000_000
        else:
            # Fallback: use root span duration if available
            root_spans = [
                s for s in spans if not s.parent_span_id or s.parent_span_id not in [sp.span_id for sp in spans]
            ]
            total_duration = sum(s.duration_ms or 0 for s in root_spans)

        error_count = sum(1 for span in spans if span.status_code == "ERROR")

        header = Text()
        header.append("🔍 Trace: ", style="bold cyan")
        header.append(trace_id, style="blue")
        header.append(f" ({len(spans)} spans", style="dim")
        header.append(f", {total_duration:.2f}ms", style="green")

        if error_count > 0:
            header.append(f", {error_count} errors", style="red bold")

        header.append(")", style="dim")

        return header

    def _add_span_to_tree(
        self,
        parent: Tree,
        span: Span,
        verbose: bool = False,
        messages_by_span: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        seen_messages: Optional[set] = None,
        common_session_id: Optional[str] = None,
        common_service_name: Optional[str] = None,
    ) -> None:
        """Recursively add a span and its children to the tree.

        Args:
            parent: Parent Tree node
            span: Span to add
            verbose: Whether to show detailed information, chat messages, events, and payloads
            messages_by_span: Dictionary mapping span IDs to messages
            seen_messages: Set of message identifiers already shown in parent spans
            common_session_id: Session ID common to all spans (to avoid repetition)
            common_service_name: Service name common to all spans (to avoid repetition)
        """
        if messages_by_span is None:
            messages_by_span = {}
        if seen_messages is None:
            seen_messages = set()

        span_node = parent.add(
            self._format_span(span, verbose, messages_by_span, seen_messages, common_session_id, common_service_name)
        )

        # Update seen_messages with messages from this span for child spans
        if verbose and span.span_id in messages_by_span:
            for item in messages_by_span[span.span_id]:
                # Create unique identifier for each message/event
                item_id = self._get_item_id(item)
                seen_messages.add(item_id)

        # Add children recursively
        for child in span.children:
            self._add_span_to_tree(
                span_node, child, verbose, messages_by_span, seen_messages, common_session_id, common_service_name
            )

    def _get_item_id(self, item: Dict[str, Any]) -> str:
        """Create unique identifier for a message, event, or exception.

        Args:
            item: Message, event, or exception dictionary

        Returns:
            Unique string identifier
        """
        item_type = item.get("type", "unknown")
        timestamp = item.get("timestamp", "")

        if item_type == "message":
            role = item.get("role", "")
            content = item.get("content", "")[:50]  # First 50 chars for uniqueness
            return f"msg_{timestamp}_{role}_{hash(content)}"
        elif item_type == "event":
            event_name = item.get("event_name", "")
            payload_str = str(item.get("payload", {}))[:50]
            return f"evt_{timestamp}_{event_name}_{hash(payload_str)}"
        elif item_type == "exception":
            exception_type = item.get("exception_type", "")
            message = item.get("message", "")[:50]
            return f"exc_{timestamp}_{exception_type}_{hash(message)}"

        return f"{item_type}_{timestamp}_{hash(str(item))}"

    def _format_span(
        self,
        span: Span,
        verbose: bool,
        messages_by_span: Dict[str, List[Dict[str, Any]]],
        seen_messages: set,
        common_session_id: Optional[str] = None,
        common_service_name: Optional[str] = None,
    ) -> Text:
        """Format a span for display.

        Args:
            span: Span to format
            verbose: Whether to show detailed information, chat messages, event payloads, and metadata
            messages_by_span: Dictionary mapping span IDs to messages (already initialized)
            seen_messages: Set of message identifiers already shown (already initialized)
            common_session_id: Session ID common to all spans (to avoid repetition)
            common_service_name: Service name common to all spans (to avoid repetition)

        Returns:
            Formatted Rich Text object
        """
        text = Text()

        # Span icon based on status
        if span.status_code == "ERROR":
            text.append("❌ ", style="red")
        elif span.status_code == "OK":
            text.append("✓ ", style="green")
        else:
            text.append("◦ ", style="dim")

        # Span name
        span_name = span.span_name or "Unnamed Span"
        text.append(span_name, style="bold white")

        # Duration
        if span.duration_ms is not None:
            duration_style = self._get_duration_style(span.duration_ms)
            text.append(f" [{span.duration_ms:.2f}ms]", style=duration_style)

        # Status - only show if it's explicitly OK or ERROR (skip UNSET as it's not useful)
        if span.status_code == "ERROR":
            text.append(" (ERROR)", style="red")
        elif span.status_code == "OK":
            text.append(" (OK)", style="green")

        # Show verbose details if requested
        if verbose:
            # Span ID
            text.append(f"\n  └─ ID: {span.span_id}", style="dim")

            # Service name (skip if it's common to all spans)
            if span.service_name and span.service_name != common_service_name:
                text.append(f"\n  └─ Service: {span.service_name}", style="dim cyan")

            # Events
            if span.events:
                text.append(f"\n  └─ Events: {len(span.events)}", style="dim yellow")

        # Show LLM/API metadata if verbose is requested
        if verbose and span.attributes:
            # Show GenAI model information
            model = span.attributes.get("gen_ai.request.model")
            if model:
                text.append(f"\n  └─ 🤖 Model: {model}", style="cyan")

            # Show token usage
            input_tokens = span.attributes.get("gen_ai.usage.input_tokens") or span.attributes.get(
                "gen_ai.usage.prompt_tokens"
            )
            output_tokens = span.attributes.get("gen_ai.usage.output_tokens") or span.attributes.get(
                "gen_ai.usage.completion_tokens"
            )
            if input_tokens or output_tokens:
                tokens_info = []
                if input_tokens:
                    tokens_info.append(f"in: {input_tokens}")
                if output_tokens:
                    tokens_info.append(f"out: {output_tokens}")
                text.append(f"\n  └─ 🎯 Tokens: {', '.join(tokens_info)}", style="yellow")

            # Show finish reasons if available
            finish_reasons = span.attributes.get("gen_ai.response.finish_reasons")
            if finish_reasons:
                text.append(f"\n  └─ ✓ Finish: {finish_reasons}", style="green")

            # Show RPC service and operation details
            rpc_service = span.attributes.get("rpc.service")
            remote_operation = span.attributes.get("aws.remote.operation")
            if rpc_service or remote_operation:
                if rpc_service and remote_operation:
                    text.append(f"\n  └─ ⚙️  API: {rpc_service}.{remote_operation}", style="blue")
                elif remote_operation:
                    text.append(f"\n  └─ ⚙️  Operation: {remote_operation}", style="blue")

            # Show AWS request ID for correlation
            request_id = span.attributes.get("aws.request_id")
            if request_id:
                text.append(f"\n  └─ 🔑 Request: {request_id}", style="dim cyan")

            # Show server/target address
            server_addr = span.attributes.get("server.address")
            if server_addr:
                text.append(f"\n  └─ 🌐 Server: {server_addr}", style="dim blue")

            # Show HTTP details
            http_method = span.attributes.get("http.method")
            http_target = span.attributes.get("http.target") or span.attributes.get("http.route")
            status_code = span.attributes.get("http.status_code") or span.attributes.get("http.response.status_code")

            if http_method or http_target or status_code:
                http_parts = []
                if http_method:
                    http_parts.append(http_method)
                if http_target:
                    http_parts.append(http_target)
                if status_code:
                    status_style = "green" if status_code in [200, 201] else "red" if status_code >= 400 else "yellow"
                    http_parts.append(f"[{status_code}]")
                    text.append(f"\n  └─ 📡 HTTP: {' '.join(http_parts)}", style=status_style)
                elif http_method or http_target:
                    text.append(f"\n  └─ 📡 HTTP: {' '.join(http_parts)}", style="blue")

            # Show session ID if present (skip if it's common to all spans)
            session_id = span.attributes.get("session.id")
            if session_id and session_id != common_session_id:
                text.append(f"\n  └─ 🔖 Session: {session_id}", style="dim")

            # Show chat messages and event payloads from runtime logs
            if span.span_id in messages_by_span:
                all_items = messages_by_span[span.span_id]

                # Filter to only show new items (delta - not seen in parent spans)
                new_items = []
                for item in all_items:
                    item_id = self._get_item_id(item)
                    if item_id not in seen_messages:
                        new_items.append(item)

                if new_items:
                    # Count messages, events, and exceptions
                    messages = [i for i in new_items if i.get("type") == "message"]
                    events = [i for i in new_items if i.get("type") == "event"]
                    exceptions = [i for i in new_items if i.get("type") == "exception"]

                    label_parts = []
                    if exceptions:
                        label_parts.append(f"{len(exceptions)} exception")
                    if messages:
                        label_parts.append(f"{len(messages)} msg")
                    if events:
                        label_parts.append(f"{len(events)} event")

                    text.append(f"\n  └─ 📋 Data ({', '.join(label_parts)}):", style="bold magenta")

                    for item in new_items:
                        item_type = item.get("type")

                        if item_type == "exception":
                            # Display exception prominently
                            exception_type = item.get("exception_type", "Exception")
                            exception_msg = item.get("message", "")
                            stacktrace = item.get("stacktrace", "")

                            text.append(f"\n      💥 {exception_type}: {exception_msg}", style="bold red")

                            # Show stacktrace (truncated if too long)
                            if stacktrace:
                                # Get last few lines of stacktrace (most relevant)
                                stacktrace_lines = stacktrace.strip().split("\n")
                                if len(stacktrace_lines) > 10:
                                    # Show first 2 lines and last 8 lines
                                    preview_lines = stacktrace_lines[:2] + ["         ..."] + stacktrace_lines[-8:]
                                else:
                                    preview_lines = stacktrace_lines

                                for line in preview_lines:
                                    text.append(f"\n         {line}", style="dim red")

                        elif item_type == "message":
                            # Display chat message
                            role = item.get("role", "unknown")
                            content = item.get("content", "")

                            # Truncate long messages
                            content_preview = content[:200]
                            if len(content) > 200:
                                content_preview += "..."

                            # Style based on role
                            if role == "system":
                                role_icon = "⚙️"
                                role_style = "dim blue"
                            elif role == "user":
                                role_icon = "👤"
                                role_style = "cyan"
                            elif role == "assistant":
                                role_icon = "🤖"
                                role_style = "green"
                            else:
                                role_icon = "•"
                                role_style = "white"

                            text.append(f"\n      {role_icon} {role.title()}: {content_preview}", style=role_style)

                        elif item_type == "event":
                            # Display event payload
                            event_name = item.get("event_name", "unknown")
                            payload = item.get("payload", {})

                            # Format payload preview
                            if isinstance(payload, dict):
                                # Show key fields from payload
                                if payload:
                                    payload_preview = self._format_event_payload(payload)
                                else:
                                    payload_preview = "(empty)"
                            else:
                                payload_preview = str(payload)[:200]

                            text.append(f"\n      📦 Event: {event_name}", style="yellow")
                            if payload_preview and payload_preview != "(empty)":
                                text.append(f"\n         {payload_preview}", style="dim yellow")

        return text

    def _format_event_payload(self, payload: Dict[str, Any]) -> str:
        """Format event payload for display.

        Args:
            payload: Payload dictionary

        Returns:
            Formatted string preview
        """
        # Extract key fields that are commonly useful
        important_keys = ["type", "name", "id", "status", "message", "error", "result", "count", "data"]

        parts = []
        for key in important_keys:
            if key in payload:
                value = payload[key]
                value_str = str(value)[:100]  # Limit each field
                parts.append(f"{key}={value_str}")

        if parts:
            return ", ".join(parts[:3])  # Show up to 3 fields

        # If no important keys, show first few keys
        keys = list(payload.keys())[:3]
        for key in keys:
            value_str = str(payload[key])[:50]
            parts.append(f"{key}={value_str}")

        return ", ".join(parts) if parts else str(payload)[:100]

    def _get_duration_style(self, duration_ms: float) -> str:
        """Get the style for duration based on its value.

        Args:
            duration_ms: Duration in milliseconds

        Returns:
            Rich style string
        """
        if duration_ms < 100:
            return "green"
        elif duration_ms < 1000:
            return "yellow"
        elif duration_ms < 5000:
            return "orange1"
        else:
            return "red"

    def print_trace_summary(self, trace_data: TraceData) -> None:
        """Print a summary of all traces.

        Args:
            trace_data: TraceData containing the spans
        """
        trace_data.group_spans_by_trace()

        if not trace_data.traces:
            self.console.print("[yellow]No traces found[/yellow]")
            return

        from rich.table import Table

        table = Table(title="Trace Summary")
        table.add_column("Trace ID", style="cyan", no_wrap=True)
        table.add_column("Spans", justify="right", style="blue")
        table.add_column("Duration (ms)", justify="right", style="green")
        table.add_column("Errors", justify="right", style="red")
        table.add_column("Status", style="yellow")

        for trace_id, spans in trace_data.traces.items():
            # Calculate actual trace duration from earliest start to latest end
            start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
            end_times = [s.end_time_unix_nano for s in spans if s.end_time_unix_nano]

            if start_times and end_times:
                # Convert nanoseconds to milliseconds
                total_duration = (max(end_times) - min(start_times)) / 1_000_000
            else:
                # Fallback: use root span duration if available
                root_spans = [
                    s for s in spans if not s.parent_span_id or s.parent_span_id not in [sp.span_id for sp in spans]
                ]
                total_duration = sum(s.duration_ms or 0 for s in root_spans)

            error_count = sum(1 for span in spans if span.status_code == "ERROR")
            status = "❌ ERROR" if error_count > 0 else "✓ OK"
            status_style = "red" if error_count > 0 else "green"

            table.add_row(
                trace_id,
                str(len(spans)),
                f"{total_duration:.2f}",
                str(error_count) if error_count > 0 else "-",
                Text(status, style=status_style),
            )

        self.console.print(table)
