"""Data models for observability spans, traces, and logs."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Span:
    """Represents an OpenTelemetry span with trace and timing information."""

    trace_id: str
    span_id: str
    span_name: str
    session_id: Optional[str] = None
    start_time_unix_nano: Optional[int] = None
    end_time_unix_nano: Optional[int] = None
    duration_ms: Optional[float] = None
    status_code: Optional[str] = None
    status_message: Optional[str] = None
    parent_span_id: Optional[str] = None
    kind: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    resource_attributes: Dict[str, Any] = field(default_factory=dict)
    service_name: Optional[str] = None
    resource_id: Optional[str] = None
    service_type: Optional[str] = None
    timestamp: Optional[str] = None
    raw_message: Optional[Dict[str, Any]] = None
    children: List["Span"] = field(default_factory=list, repr=False)  # Child spans for hierarchy

    @classmethod
    def from_cloudwatch_result(cls, result: Any) -> "Span":
        """Create a Span from CloudWatch Logs Insights query result.

        Args:
            result: List of field dictionaries from CloudWatch query result

        Returns:
            Span object populated from the result
        """
        # CloudWatch returns a list of field objects directly
        fields = result if isinstance(result, list) else result.get("fields", [])

        # Helper to safely get field value
        def get_field(field_name: str, default: Any = None) -> Any:
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        # Helper to parse JSON string fields
        def parse_json_field(field_name: str) -> Any:
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    import json

                    return json.loads(value)
                except Exception:
                    return value
            return value

        # Helper to convert to float safely
        def get_float_field(field_name: str) -> Optional[float]:
            value = get_field(field_name)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            return None

        # Helper to convert to int safely
        def get_int_field(field_name: str) -> Optional[int]:
            value = get_field(field_name)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            return None

        # Parse @message to get attributes and resource.attributes
        raw_message = parse_json_field("@message")
        attributes = {}
        resource_attributes = {}

        if raw_message and isinstance(raw_message, dict):
            # Extract attributes from @message
            attributes = raw_message.get("attributes", {})
            if not isinstance(attributes, dict):
                attributes = {}

            # Extract resource.attributes from @message
            resource_data = raw_message.get("resource", {})
            if isinstance(resource_data, dict):
                resource_attributes = resource_data.get("attributes", {})
                if not isinstance(resource_attributes, dict):
                    resource_attributes = {}

        return cls(
            trace_id=get_field("traceId", ""),
            span_id=get_field("spanId", ""),
            span_name=get_field("spanName", ""),
            session_id=get_field("sessionId"),
            start_time_unix_nano=get_int_field("startTimeUnixNano"),
            end_time_unix_nano=get_int_field("endTimeUnixNano"),
            duration_ms=get_float_field("durationMs"),
            status_code=get_field("statusCode"),
            status_message=get_field("statusMessage"),
            parent_span_id=get_field("parentSpanId"),
            kind=get_field("kind"),
            events=parse_json_field("events") or [],
            attributes=attributes,
            resource_attributes=resource_attributes,
            service_name=get_field("serviceName"),
            resource_id=get_field("resourceId"),
            service_type=get_field("serviceType"),
            timestamp=get_field("@timestamp"),
            raw_message=raw_message,
        )


@dataclass
class RuntimeLog:
    """Represents a runtime log entry from agent-specific log groups."""

    timestamp: str
    message: str
    span_id: Optional[str] = None
    trace_id: Optional[str] = None
    log_stream: Optional[str] = None
    raw_message: Optional[Dict[str, Any]] = None

    def get_gen_ai_message(self) -> Optional[Dict[str, Any]]:
        """Extract GenAI message from runtime log if present.

        Returns:
            Dictionary with message details (role, content, timestamp) or None
        """
        if not self.raw_message or not isinstance(self.raw_message, dict):
            return None

        attributes = self.raw_message.get("attributes", {})
        if not attributes:
            return None

        event_name = attributes.get("event.name", "")
        if not event_name.startswith("gen_ai."):
            return None

        # Extract role from event name
        role = None
        if "system.message" in event_name:
            role = "system"
        elif "user.message" in event_name:
            role = "user"
        elif "assistant.message" in event_name or "choice" in event_name:
            role = "assistant"

        if not role:
            return None

        # Extract content from body
        body = self.raw_message.get("body", {})
        content = None

        if isinstance(body, dict):
            # Check for content array (typical format)
            if "content" in body and isinstance(body["content"], list):
                content_items = []
                for item in body["content"]:
                    if isinstance(item, dict) and "text" in item:
                        content_items.append(item["text"])
                content = "\n".join(content_items) if content_items else None
            # Check for direct text field
            elif "text" in body:
                content = body["text"]
        elif isinstance(body, str):
            content = body

        if content:
            return {
                "type": "message",
                "role": role,
                "content": content,
                "timestamp": self.timestamp,
                "event_name": event_name,
            }

        return None

    def get_exception(self) -> Optional[Dict[str, Any]]:
        """Extract exception information from runtime log if present.

        Returns:
            Dictionary with exception details or None
        """
        if not self.raw_message or not isinstance(self.raw_message, dict):
            return None

        attributes = self.raw_message.get("attributes", {})
        if not attributes:
            return None

        # Check for exception attributes
        exception_type = attributes.get("exception.type")
        exception_message = attributes.get("exception.message")
        exception_stacktrace = attributes.get("exception.stacktrace")

        if exception_type or exception_message or exception_stacktrace:
            return {
                "type": "exception",
                "exception_type": exception_type,
                "message": exception_message,
                "stacktrace": exception_stacktrace,
                "timestamp": self.timestamp,
            }

        return None

    def get_event_payload(self) -> Optional[Dict[str, Any]]:
        """Extract event payload from runtime log.

        Returns:
            Dictionary with event details or None
        """
        if not self.raw_message or not isinstance(self.raw_message, dict):
            return None

        attributes = self.raw_message.get("attributes", {})
        body = self.raw_message.get("body", {})

        if not attributes and not body:
            return None

        # Skip if this is an exception (handled by get_exception)
        if attributes.get("exception.type") or attributes.get("exception.message"):
            return None

        # Get event name
        event_name = attributes.get("event.name", "")

        # Skip gen_ai messages (handled separately)
        if event_name.startswith("gen_ai."):
            return None

        # Extract meaningful payload data
        payload_data = {}

        # Try to get structured body
        if isinstance(body, dict):
            # For events, the body often contains the actual payload
            payload_data = body
        elif isinstance(body, str):
            # Try to parse as JSON
            try:
                import json

                payload_data = json.loads(body)
            except (json.JSONDecodeError, ValueError, TypeError):
                payload_data = {"message": body}

        if payload_data or event_name:
            return {
                "type": "event",
                "event_name": event_name or "unknown",
                "payload": payload_data,
                "timestamp": self.timestamp,
                "attributes": attributes,
            }

        return None

    @classmethod
    def from_cloudwatch_result(cls, result: Any) -> "RuntimeLog":
        """Create a RuntimeLog from CloudWatch Logs Insights query result.

        Args:
            result: List of field dictionaries from CloudWatch query result

        Returns:
            RuntimeLog object populated from the result
        """
        # CloudWatch returns a list of field objects directly
        fields = result if isinstance(result, list) else result.get("fields", [])

        def get_field(field_name: str, default: Any = None) -> Any:
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        def parse_json_field(field_name: str) -> Any:
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    import json

                    return json.loads(value)
                except Exception:
                    return value
            return value

        return cls(
            timestamp=get_field("@timestamp", ""),
            message=get_field("@message", ""),
            span_id=get_field("spanId"),
            trace_id=get_field("traceId"),
            log_stream=get_field("@logStream"),
            raw_message=parse_json_field("@message"),
        )


@dataclass
class TraceData:
    """Complete trace/session data including spans and runtime logs."""

    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    spans: List[Span] = field(default_factory=list)
    runtime_logs: List[RuntimeLog] = field(default_factory=list)
    traces: Dict[str, List[Span]] = field(default_factory=dict)
    start_time: Optional[int] = None
    end_time: Optional[int] = None

    def group_spans_by_trace(self) -> None:
        """Group spans by trace_id for easier navigation."""
        self.traces = {}
        for span in self.spans:
            if span.trace_id not in self.traces:
                self.traces[span.trace_id] = []
            self.traces[span.trace_id].append(span)

        # Sort spans within each trace by start time
        for trace_id in self.traces:
            self.traces[trace_id].sort(key=lambda s: s.start_time_unix_nano or 0)

    def get_trace_ids(self) -> List[str]:
        """Get all unique trace IDs from spans."""
        return list(set(span.trace_id for span in self.spans if span.trace_id))

    def get_messages_by_span(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract chat messages, exceptions, and event payloads from runtime logs grouped by span ID.

        Returns:
            Dictionary mapping span_id to list of messages/events/exceptions with type, content, etc.
        """
        items_by_span: Dict[str, List[Dict[str, Any]]] = {}

        for log in self.runtime_logs:
            if not log.span_id:
                continue

            # Try to get exception first (highest priority for errors)
            exception = log.get_exception()
            if exception:
                if log.span_id not in items_by_span:
                    items_by_span[log.span_id] = []
                items_by_span[log.span_id].append(exception)
                continue

            # Try to get chat message
            message = log.get_gen_ai_message()
            if message:
                if log.span_id not in items_by_span:
                    items_by_span[log.span_id] = []
                items_by_span[log.span_id].append(message)
                continue

            # Try to get event payload
            event = log.get_event_payload()
            if event:
                if log.span_id not in items_by_span:
                    items_by_span[log.span_id] = []
                items_by_span[log.span_id].append(event)

        # Sort items by timestamp within each span
        for span_id in items_by_span:
            items_by_span[span_id].sort(key=lambda m: m.get("timestamp", ""))

        return items_by_span

    def build_span_hierarchy(self, trace_id: str) -> List[Span]:
        """Build hierarchical structure of spans for a trace.

        Args:
            trace_id: The trace ID to build hierarchy for

        Returns:
            List of root spans (spans without parents in this trace)
        """
        if trace_id not in self.traces:
            return []

        # Create a map of span_id to span
        span_map = {span.span_id: span for span in self.traces[trace_id]}

        # Create a map of parent_span_id to list of children
        children_map: Dict[Optional[str], List[Span]] = {}
        root_spans: List[Span] = []

        for span in self.traces[trace_id]:
            parent_id = span.parent_span_id

            # Check if parent exists in this trace
            if parent_id and parent_id in span_map:
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(span)
            else:
                # No parent or parent not in trace = root span
                root_spans.append(span)

        # Attach children to each span
        for span in self.traces[trace_id]:
            span.children = children_map.get(span.span_id, [])

        return root_spans

    def to_dict(self) -> Dict[str, Any]:
        """Export complete trace data to dictionary for JSON serialization.

        Returns:
            Dictionary with all trace data including spans, logs, and messages
        """

        # Helper to convert span to dict recursively
        def span_to_dict(span: Span) -> Dict[str, Any]:
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

        # Convert runtime logs to dict
        def log_to_dict(log: RuntimeLog) -> Dict[str, Any]:
            result = {
                "timestamp": log.timestamp,
                "message": log.message,
                "span_id": log.span_id,
                "trace_id": log.trace_id,
                "log_stream": log.log_stream,
            }

            # Add parsed exception data (highest priority)
            exception = log.get_exception()
            if exception:
                result["parsed_exception"] = exception

            # Add parsed message and event data
            gen_ai_message = log.get_gen_ai_message()
            if gen_ai_message:
                result["parsed_gen_ai_message"] = gen_ai_message

            event_payload = log.get_event_payload()
            if event_payload:
                result["parsed_event_payload"] = event_payload

            # Include raw message for full details
            if log.raw_message:
                result["raw_message"] = log.raw_message

            return result

        # Build hierarchies for all traces
        traces_with_hierarchy = {}
        for trace_id in self.traces:
            root_spans = self.build_span_hierarchy(trace_id)

            # Calculate actual trace duration from earliest start to latest end
            spans = self.traces[trace_id]
            start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
            end_times = [s.end_time_unix_nano for s in spans if s.end_time_unix_nano]

            if start_times and end_times:
                # Convert nanoseconds to milliseconds
                total_duration_ms = (max(end_times) - min(start_times)) / 1_000_000
            else:
                # Fallback: use root span duration
                total_duration_ms = sum(s.duration_ms or 0 for s in root_spans)

            traces_with_hierarchy[trace_id] = {
                "trace_id": trace_id,
                "span_count": len(spans),
                "total_duration_ms": total_duration_ms,
                "error_count": sum(1 for span in spans if span.status_code == "ERROR"),
                "root_spans": [span_to_dict(span) for span in root_spans],
            }

        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "trace_count": len(self.traces),
            "total_span_count": len(self.spans),
            "traces": traces_with_hierarchy,
            "runtime_logs": [log_to_dict(log) for log in self.runtime_logs],
        }
