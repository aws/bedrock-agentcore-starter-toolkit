"""Processor for working with telemetry data.

This module contains all business logic for processing TraceData, Spans, and RuntimeLogs.
"""

from typing import Any, Dict, List

from .message_parser import UnifiedLogParser
from .telemetry import RuntimeLog, Span, TraceData


class TraceProcessor:
    """Processor for processing and analyzing trace data."""

    @staticmethod
    def group_spans_by_trace(trace_data: TraceData) -> None:
        """Group spans by trace_id for easier navigation.

        Modifies trace_data.traces in-place.
        """
        trace_data.traces = {}
        for span in trace_data.spans:
            if span.trace_id not in trace_data.traces:
                trace_data.traces[span.trace_id] = []
            trace_data.traces[span.trace_id].append(span)

        # Sort spans within each trace by start time
        for trace_id in trace_data.traces:
            trace_data.traces[trace_id].sort(key=lambda s: s.start_time_unix_nano or 0)

    @staticmethod
    def build_span_hierarchy(trace_data: TraceData, trace_id: str) -> List[Span]:
        """Build hierarchical structure of spans for a trace.

        Args:
            trace_data: TraceData containing spans
            trace_id: The trace ID to build hierarchy for

        Returns:
            List of root spans (spans without parents in this trace)
        """
        if trace_id not in trace_data.traces:
            return []

        # Create span map
        span_map = {span.span_id: span for span in trace_data.traces[trace_id]}

        # Build children map and root spans list
        children_map: Dict[str, List[Span]] = {}
        root_spans: List[Span] = []

        for span in trace_data.traces[trace_id]:
            parent_id = span.parent_span_id

            if parent_id and parent_id in span_map:
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(span)
            else:
                root_spans.append(span)

        # Attach children to spans
        for span in trace_data.traces[trace_id]:
            span.children = children_map.get(span.span_id, [])

        return root_spans

    @staticmethod
    def get_messages_by_span(trace_data: TraceData) -> Dict[str, List[Dict[str, Any]]]:
        """Extract messages and exceptions from runtime logs grouped by span ID.

        Returns:
            Dictionary mapping span_id to list of items (messages/exceptions)
        """
        parser = UnifiedLogParser()
        items_by_span: Dict[str, List[Dict[str, Any]]] = {}

        for log in trace_data.runtime_logs:
            if not log.span_id:
                continue

            # Parse all items from this log
            items = parser.parse(log.raw_message, log.timestamp)
            if items:
                items_by_span.setdefault(log.span_id, []).extend(items)

        # Sort items by timestamp within each span
        for items in items_by_span.values():
            items.sort(key=lambda m: m.get("timestamp", ""))

        return items_by_span

    @staticmethod
    def calculate_trace_duration(spans: List[Span]) -> float:
        """Calculate trace duration from earliest start to latest end time.

        Args:
            spans: List of spans in the trace

        Returns:
            Duration in milliseconds
        """
        start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
        end_times = [s.end_time_unix_nano for s in spans if s.end_time_unix_nano]

        if start_times and end_times:
            # Convert nanoseconds to milliseconds
            return (max(end_times) - min(start_times)) / 1_000_000

        # Fallback: use root span duration
        root_spans = [s for s in spans if not s.parent_span_id]
        return sum(s.duration_ms or 0 for s in root_spans)

    @staticmethod
    def count_error_spans(spans: List[Span]) -> int:
        """Count number of spans with ERROR status.

        Args:
            spans: List of spans to check

        Returns:
            Number of spans with status_code == "ERROR"
        """
        return sum(1 for span in spans if span.status_code == "ERROR")

    @staticmethod
    def get_trace_ids(trace_data: TraceData) -> List[str]:
        """Get all unique trace IDs from spans.

        Args:
            trace_data: TraceData containing spans

        Returns:
            List of unique trace IDs
        """
        return list(set(span.trace_id for span in trace_data.spans if span.trace_id))

    @staticmethod
    def filter_error_traces(trace_data: TraceData) -> Dict[str, List[Span]]:
        """Filter traces to only those containing errors.

        Args:
            trace_data: TraceData with grouped traces

        Returns:
            Dictionary mapping trace_id to list of spans for traces with errors
        """
        return {
            trace_id: spans_list
            for trace_id, spans_list in trace_data.traces.items()
            if any(span.status_code == "ERROR" for span in spans_list)
        }

    @staticmethod
    def get_trace_messages(trace_data: TraceData, trace_id: str) -> tuple[str, str]:
        """Extract input and output messages for a trace.

        Args:
            trace_data: TraceData containing logs
            trace_id: The trace ID to extract messages for

        Returns:
            Tuple of (input_text, output_text). Empty strings if not found.
        """
        from ..constants import TruncationConfig

        parser = UnifiedLogParser()
        input_text = ""
        output_text = ""

        # Get runtime logs for this trace
        trace_logs = [log for log in trace_data.runtime_logs if log.trace_id == trace_id]

        if not trace_logs:
            return input_text, output_text

        # Extract and sort messages by timestamp
        messages = []
        for log in trace_logs:
            try:
                items = parser.parse(log.raw_message, log.timestamp)
                msgs = [item for item in items if item.get("type") == "message"]
                messages.extend(msgs)
            except Exception:  # nosec B112  # Skip malformed logs gracefully
                continue

        messages.sort(key=lambda m: m.get("timestamp", ""))

        # Find last user message (trace input)
        user_messages = [m for m in messages if m.get("role") == "user"]
        if user_messages:
            content = user_messages[-1].get("content", "")
            input_text = TruncationConfig.truncate(content, length=TruncationConfig.LIST_PREVIEW_LENGTH)

        # Find last assistant message (trace output)
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        if assistant_messages:
            content = assistant_messages[-1].get("content", "")
            output_text = TruncationConfig.truncate(content, length=TruncationConfig.LIST_PREVIEW_LENGTH)

        return input_text, output_text

    @staticmethod
    def to_dict(trace_data: TraceData) -> Dict[str, Any]:
        """Export complete trace data to dictionary for JSON serialization.

        Args:
            trace_data: TraceData to export

        Returns:
            Dictionary with all trace data including spans, logs, and messages
        """
        parser = UnifiedLogParser()

        def span_to_dict(span: Span) -> Dict[str, Any]:
            """Convert span to dictionary recursively."""
            return {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "span_name": span.span_name,
                "session_id": span.session_id,
                "start_time_unix_nano": span.start_time_unix_nano,
                "end_time_unix_nano": span.end_time_unix_nano,
                "duration_ms": span.duration_ms,
                "status_code": span.status_code,
                "status_message": span.status_message,
                "parent_span_id": span.parent_span_id,
                "kind": span.kind,
                "events": span.events,
                "attributes": span.attributes,
                "resource_attributes": span.resource_attributes,
                "service_name": span.service_name,
                "resource_id": span.resource_id,
                "service_type": span.service_type,
                "timestamp": span.timestamp,
                "children": [span_to_dict(child) for child in span.children],
            }

        def log_to_dict(log: RuntimeLog) -> Dict[str, Any]:
            """Convert log to dictionary with parsed content."""
            result = {
                "timestamp": log.timestamp,
                "message": log.message,
                "span_id": log.span_id,
                "trace_id": log.trace_id,
                "log_stream": log.log_stream,
            }

            # Add parsed items
            items = parser.parse(log.raw_message, log.timestamp)
            if items:
                # Separate by type
                messages = [item for item in items if item.get("type") == "message"]
                exceptions = [item for item in items if item.get("type") == "exception"]

                if messages:
                    result["parsed_gen_ai_message"] = messages

                if exceptions:
                    result["parsed_exception"] = exceptions[0]

            # Include raw message for full details
            if log.raw_message:
                result["raw_message"] = log.raw_message

            return result

        # Build hierarchies for all traces
        traces_with_hierarchy = {}
        for trace_id in trace_data.traces:
            spans = trace_data.traces[trace_id]
            root_spans = TraceProcessor.build_span_hierarchy(trace_data, trace_id)

            traces_with_hierarchy[trace_id] = {
                "trace_id": trace_id,
                "span_count": len(spans),
                "total_duration_ms": TraceProcessor.calculate_trace_duration(spans),
                "error_count": sum(1 for span in spans if span.status_code == "ERROR"),
                "root_spans": [span_to_dict(span) for span in root_spans],
            }

        return {
            "session_id": trace_data.session_id,
            "agent_id": trace_data.agent_id,
            "start_time": trace_data.start_time,
            "end_time": trace_data.end_time,
            "trace_count": len(trace_data.traces),
            "total_span_count": len(trace_data.spans),
            "traces": traces_with_hierarchy,
            "runtime_logs": [log_to_dict(log) for log in trace_data.runtime_logs],
        }
