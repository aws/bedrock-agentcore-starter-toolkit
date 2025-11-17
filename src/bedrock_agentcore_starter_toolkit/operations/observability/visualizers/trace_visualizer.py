"""Trace visualization with hierarchical tree views."""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from ...constants import GenAIAttributes, LLMAttributes, TruncationConfig
from ..formatters import (
    format_duration_ms,
    get_duration_style,
    get_status_icon,
    get_status_style,
)
from ..models.telemetry import Span, TraceData


class TraceVisualizer:
    """Visualizer for displaying traces in an intuitive hierarchical format."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the trace visualizer.

        Args:
            console: Optional Rich console for output
        """
        self.console = console or Console()

    def visualize_trace(
        self,
        trace_data: TraceData,
        trace_id: str,
        show_details: bool = True,
        show_messages: bool = False,
        verbose: bool = False,
    ) -> None:
        """Visualize a single trace as a hierarchical tree.

        Args:
            trace_data: TraceData containing the spans
            trace_id: The trace ID to visualize
            show_details: Whether to show detailed span information
            show_messages: Whether to show chat messages and invocation payloads
            verbose: Whether to show full details without truncation
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

        # Get messages grouped by span if show_messages is enabled
        messages_by_span = trace_data.get_messages_by_span() if show_messages else {}

        # Create the tree
        trace_tree = Tree(
            self._format_trace_header(trace_id, trace_data.traces[trace_id]),
            guide_style="cyan",
        )

        # Track seen messages to avoid duplication across hierarchy
        seen_messages: set = set()

        # Add each root span and its children
        for root_span in root_spans:
            self._add_span_to_tree(
                trace_tree, root_span, show_details, show_messages, messages_by_span, seen_messages, verbose
            )

        self.console.print(trace_tree)

    def visualize_all_traces(
        self,
        trace_data: TraceData,
        show_details: bool = False,
        show_messages: bool = False,
        verbose: bool = False,
    ) -> None:
        """Visualize all traces in the trace data.

        Args:
            trace_data: TraceData containing the spans
            show_details: Whether to show detailed span information
            show_messages: Whether to show chat messages and invocation payloads
            verbose: Whether to show full details without truncation
        """
        trace_data.group_spans_by_trace()

        if not trace_data.traces:
            self.console.print("[yellow]No traces found[/yellow]")
            return

        self.console.print(f"\n[bold cyan]Found {len(trace_data.traces)} traces:[/bold cyan]\n")

        for trace_id in trace_data.traces:
            self.visualize_trace(trace_data, trace_id, show_details, show_messages, verbose)
            self.console.print()  # Empty line between traces

    def _format_trace_header(self, trace_id: str, spans: List[Span]) -> Text:
        """Format the trace header with summary information.

        Args:
            trace_id: The trace ID
            spans: List of spans in the trace

        Returns:
            Formatted Rich Text object
        """
        total_duration = TraceData.calculate_trace_duration(spans)
        error_count = TraceData.count_error_spans(spans)

        header = Text()
        header.append("🔍 Trace: ", style="bold cyan")
        header.append(trace_id[:16] + "...", style="bright_blue")
        header.append(f" ({len(spans)} spans", style="dim")
        header.append(f", {format_duration_ms(total_duration)}", style="green")

        if error_count > 0:
            header.append(f", {error_count} errors", style="red bold")

        header.append(")", style="dim")

        return header

    def _has_meaningful_data(
        self,
        span: Span,
        show_messages: bool,
        messages_by_span: Dict[str, List[Dict[str, Any]]],
    ) -> bool:
        """Check if a span has meaningful data worth showing in non-verbose mode.

        Only show spans with:
        - ERROR status (for debugging)
        - Conversation messages (actual user/assistant interaction)
        - LLM interactions (gen_ai attributes with prompts/completions)

        Hide infrastructure spans (ListEvents, CreateEvent, etc.) unless they error.

        Args:
            span: Span to check
            show_messages: Whether messages are being shown
            messages_by_span: Dictionary mapping span IDs to messages

        Returns:
            True if span has meaningful data
        """
        # Always show root spans (no parent) to maintain hierarchy visibility
        if not span.parent_span_id:
            return True

        # Always show error spans for debugging
        if span.status_code == "ERROR":
            return True

        # Show if has conversation messages (user/assistant interaction)
        if show_messages and span.span_id in messages_by_span:
            items = messages_by_span[span.span_id]
            if items:
                # Check if any items are actual messages (not just events)
                for item in items:
                    if item.get("type") == "message":
                        return True

        # Show if has LLM interaction (gen_ai attributes with prompts/completions)
        if span.attributes:
            llm_attrs = [
                # Modern OpenTelemetry GenAI attributes (OpenAI, Anthropic, etc.)
                GenAIAttributes.REQUEST_MODEL_INPUT,
                GenAIAttributes.RESPONSE_MODEL_OUTPUT,
                # Legacy attributes
                GenAIAttributes.PROMPT,
                GenAIAttributes.COMPLETION,
                LLMAttributes.PROMPTS,
                LLMAttributes.RESPONSES,
                # Provider-specific invocation attributes
                GenAIAttributes.INVOCATION_BEDROCK,
                GenAIAttributes.INVOCATION_INPUT,
                GenAIAttributes.INVOCATION_OUTPUT,
            ]
            if any(attr in span.attributes for attr in llm_attrs):
                return True

        # Show parent if any children have meaningful data (maintain hierarchy)
        for child in span.children:
            if self._has_meaningful_data(child, show_messages, messages_by_span):
                return True

        return False

    def _add_span_to_tree(
        self,
        parent: Tree,
        span: Span,
        show_details: bool,
        show_messages: bool,
        messages_by_span: Dict[str, List[Dict[str, Any]]],
        seen_messages: set,
        verbose: bool,
    ) -> None:
        """Recursively add a span and its children to the tree.

        Args:
            parent: Parent Tree node
            span: Span to add
            show_details: Whether to show detailed information
            show_messages: Whether to show chat messages and payloads
            messages_by_span: Dictionary mapping span IDs to messages/events/exceptions
            seen_messages: Set of message IDs already shown (to prevent duplication)
            verbose: Whether to show full details without truncation
        """
        # In non-verbose mode WITHOUT show_details, skip spans without meaningful data
        # If show_details is True, always show spans (for debugging)
        if not verbose and not show_details and not self._has_meaningful_data(span, show_messages, messages_by_span):
            # Still process children in case they have meaningful data
            for child in span.children:
                self._add_span_to_tree(
                    parent, child, show_details, show_messages, messages_by_span, seen_messages, verbose
                )
            return

        span_node = parent.add(
            self._format_span(span, show_details, show_messages, messages_by_span, seen_messages, verbose)
        )

        # Add children recursively
        for child in span.children:
            self._add_span_to_tree(
                span_node, child, show_details, show_messages, messages_by_span, seen_messages, verbose
            )

    def _format_span(
        self,
        span: Span,
        show_details: bool,
        show_messages: bool,
        messages_by_span: Dict[str, List[Dict[str, Any]]],
        seen_messages: set,
        verbose: bool = False,
    ) -> Text:
        """Format a span for display.

        Args:
            span: Span to format
            show_details: Whether to show detailed information
            show_messages: Whether to show chat messages and invocation payloads
            messages_by_span: Dictionary mapping span IDs to messages/events/exceptions
            seen_messages: Set of message IDs already shown (to prevent duplication)
            verbose: Whether to show full details without truncation

        Returns:
            Formatted Rich Text object
        """
        text = Text()

        # Span icon based on status
        if span.status_code:
            icon = get_status_icon(span.status_code)
            style = get_status_style(span.status_code)
            text.append(icon, style=style)
        else:
            text.append("◦ ", style="dim")

        # Span name
        span_name = span.span_name or "Unnamed Span"
        text.append(span_name, style="bold white")

        # Duration
        if span.duration_ms is not None:
            duration_style = get_duration_style(span.duration_ms)
            text.append(f" [{format_duration_ms(span.duration_ms)}]", style=duration_style)

        # Status
        if span.status_code:
            status_style = get_status_style(span.status_code)
            text.append(f" ({span.status_code})", style=status_style)

        # Show details if requested
        if show_details:
            # Span ID - show full ID for debugging
            text.append(f"\n  └─ ID: {span.span_id}", style="dim")

            # Events
            if span.events:
                text.append(f"\n  └─ Events: {len(span.events)}", style="dim yellow")

        # Show messages if requested
        if show_messages and span.attributes:
            # Extract chat messages from span attributes (using configured truncation)
            prompt = span.attributes.get(GenAIAttributes.PROMPT) or span.attributes.get(LLMAttributes.PROMPTS)
            if prompt:
                prompt_str = str(prompt)
                if not verbose:
                    prompt_str = TruncationConfig.truncate(prompt_str)
                text.append(f"\n  └─ 💬 User: {prompt_str}", style="cyan")

            completion = span.attributes.get(GenAIAttributes.COMPLETION) or span.attributes.get(LLMAttributes.RESPONSES)
            if completion:
                completion_str = str(completion)
                if not verbose:
                    completion_str = TruncationConfig.truncate(completion_str)
                text.append(f"\n  └─ 🤖 Assistant: {completion_str}", style="green")

            # Extract invocation payloads (provider-agnostic)
            # Try multiple attribute names in priority order
            invocation = (
                span.attributes.get(GenAIAttributes.REQUEST_MODEL_INPUT)  # Standard GenAI
                or span.attributes.get(GenAIAttributes.INVOCATION_BEDROCK)  # AWS Bedrock
                or span.attributes.get(GenAIAttributes.INVOCATION_REQUEST_BODY)  # Generic HTTP
                or span.attributes.get(GenAIAttributes.INVOCATION_INPUT)  # Generic input
            )
            if invocation:
                invocation_str = str(invocation)
                if not verbose:
                    invocation_str = TruncationConfig.truncate(invocation_str)
                text.append(f"\n  └─ 📦 Payload: {invocation_str}", style="yellow")

            # Show input/output if available (provider-agnostic)
            input_data = (
                span.attributes.get(GenAIAttributes.REQUEST_MODEL_INPUT)
                or span.attributes.get(GenAIAttributes.INVOCATION_INPUT)
                or span.attributes.get("input")  # Legacy fallback
            )
            if input_data:
                input_str = str(input_data)
                if not verbose:
                    input_str = TruncationConfig.truncate(input_str)
                text.append(f"\n  └─ 📥 Input: {input_str}", style="bright_blue")

            output_data = (
                span.attributes.get(GenAIAttributes.RESPONSE_MODEL_OUTPUT)
                or span.attributes.get(GenAIAttributes.INVOCATION_OUTPUT)
                or span.attributes.get("output")  # Legacy fallback
            )
            if output_data:
                output_str = str(output_data)
                if not verbose:
                    output_str = TruncationConfig.truncate(output_str)
                text.append(f"\n  └─ 📤 Output: {output_str}", style="magenta")

        # Show messages from runtime logs if available
        if show_messages and span.span_id in messages_by_span:
            items = messages_by_span[span.span_id]
            if items:
                # Filter out items that have already been shown
                new_items = []
                for item in items:
                    item_id = self._get_message_id(item)
                    if item_id not in seen_messages:
                        new_items.append(item)
                        seen_messages.add(item_id)

                if new_items:
                    # Count different types
                    messages = [i for i in new_items if i.get("type") == "message"]
                    events = [i for i in new_items if i.get("type") == "event"]
                    exceptions = [i for i in new_items if i.get("type") == "exception"]

                    # Show exceptions first (most important)
                    for exc in exceptions:
                        exc_type = exc.get("exception_type", "Exception")
                        exc_msg = exc.get("message", "")
                        stacktrace = exc.get("stacktrace", "")

                        text.append(f"\n  └─ 💥 {exc_type}: {exc_msg}", style="bold red")

                        # Show stacktrace (no truncation in verbose mode)
                        if stacktrace:
                            stacktrace_lines = stacktrace.strip().split("\n")
                            for line in stacktrace_lines[:10]:  # Show first 10 lines
                                text.append(f"\n      {line}", style="dim red")

                    # Show messages
                    for msg in messages:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")

                        # Apply truncation in non-verbose mode
                        # For tool use content (contains 🔧), show summary line only
                        if not verbose:
                            if "🔧" in content:
                                # Extract just the tool name and truncate heavily
                                lines = content.split("\n")
                                first_line = lines[0] if lines else content
                                content = (
                                    TruncationConfig.truncate(first_line, is_tool_use=True) + " [truncated tool use]"
                                )
                            else:
                                content = TruncationConfig.truncate(content)

                        if role == "user":
                            text.append(f"\n  └─ 👤 User: {content}", style="cyan")
                        elif role == "assistant":
                            text.append(f"\n  └─ 🤖 Assistant: {content}", style="green")
                        elif role == "system":
                            text.append(f"\n  └─ ⚙️ System: {content}", style="bright_white")
                        elif role == "tool":
                            text.append(f"\n  └─ {content}", style="yellow")

                    # Show events with payload
                    for evt in events:
                        event_name = evt.get("event_name", "unknown")
                        payload = evt.get("payload", {})

                        # Skip generic wrapper events that just contain input/output messages
                        # Show them only if they have unique information
                        if self._is_generic_wrapper_event(event_name, payload):
                            continue

                        text.append(f"\n  └─ 📦 Event: {event_name}", style="yellow")

                        # Show payload data if available
                        if payload and isinstance(payload, dict):
                            # Format payload more intelligently
                            self._format_event_payload_display(text, payload, verbose)

        return text

    def _get_message_id(self, item: Dict[str, Any]) -> str:
        """Create a unique identifier for a message/event/exception for deduplication.

        Args:
            item: Message, event, or exception dictionary

        Returns:
            Unique string identifier
        """
        item_type = item.get("type", "unknown")
        timestamp = item.get("timestamp", "")

        if item_type == "message":
            role = item.get("role", "")
            content = str(item.get("content", ""))
            # Use hash of content for uniqueness
            return f"msg_{role}_{hash(content)}"
        elif item_type == "event":
            event_name = item.get("event_name", "")
            payload = item.get("payload", {})
            # For events, use event name and payload hash
            return f"evt_{event_name}_{hash(str(payload))}"
        elif item_type == "exception":
            exc_type = item.get("exception_type", "")
            message = item.get("message", "")
            return f"exc_{exc_type}_{hash(message)}"

        return f"{item_type}_{timestamp}_{hash(str(item))}"

    def _is_generic_wrapper_event(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Check if an event is a generic wrapper that doesn't add new information.

        Args:
            event_name: Name of the event
            payload: Event payload

        Returns:
            True if this is a generic wrapper event that should be skipped
        """
        # Skip strands.telemetry.tracer events - they're just wrappers
        # The actual messages are already extracted and shown separately
        if event_name == "strands.telemetry.tracer":
            return True

        # If payload only contains input/output with messages, it's likely redundant
        if set(payload.keys()) == {"input", "output"}:
            input_data = payload.get("input", {})
            output_data = payload.get("output", {})
            # If both only have "messages" key, this is redundant with chat messages
            if (
                isinstance(input_data, dict)
                and set(input_data.keys()) == {"messages"}
                and isinstance(output_data, dict)
                and set(output_data.keys()) == {"messages"}
            ):
                return True

        return False

    def _format_event_payload_display(self, text: Text, payload: Dict[str, Any], verbose: bool = False) -> None:
        """Format event payload for display in a more readable way.

        Args:
            text: Rich Text object to append to
            payload: Event payload dictionary
            verbose: Whether to show full details without truncation
        """
        # Special handling for common payload structures
        if "input" in payload or "output" in payload:
            # This looks like an input/output pair, format specially
            if "input" in payload:
                input_data = payload["input"]
                if isinstance(input_data, dict):
                    # Extract key information
                    if "messages" in input_data:
                        # Already handled by message extraction, skip
                        pass
                    else:
                        # Show other input fields (using configured truncation)
                        input_str = str(input_data)
                        if not verbose:
                            input_str = TruncationConfig.truncate(input_str)
                        text.append(f"\n      Input: {input_str}", style="dim yellow")

            if "output" in payload:
                output_data = payload["output"]
                if isinstance(output_data, dict):
                    # Extract key information
                    if "messages" in output_data:
                        # Already handled by message extraction, skip
                        pass
                    else:
                        # Show other output fields (using configured truncation)
                        output_str = str(output_data)
                        if not verbose:
                            output_str = TruncationConfig.truncate(output_str)
                        text.append(f"\n      Output: {output_str}", style="dim yellow")
        else:
            # Generic payload - show all fields (using configured truncation)
            for key, value in payload.items():
                if key in ("message", "messages"):
                    # Already handled, skip
                    continue
                value_str = str(value)
                if not verbose:
                    value_str = TruncationConfig.truncate(value_str)
                text.append(f"\n      {key}: {value_str}", style="dim yellow")
