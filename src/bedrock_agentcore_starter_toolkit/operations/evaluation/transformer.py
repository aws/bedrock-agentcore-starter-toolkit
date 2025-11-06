"""Transform observability data to OpenTelemetry format for evaluation API."""

from typing import Any, Dict, List, Optional

from ..observability.models.telemetry import RuntimeLog, Span, TraceData


def transform_span_to_otel(span: Span, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Transform a Span to OpenTelemetry format for evaluation API.

    Args:
        span: Span object from observability module
        session_id: Optional session ID to add to attributes

    Returns:
        Dictionary in OpenTelemetry span format
    """
    # Extract resource from raw_message if available, otherwise build minimal
    if span.raw_message and isinstance(span.raw_message, dict) and "resource" in span.raw_message:
        resource = span.raw_message["resource"]
    else:
        # Fallback: build minimal resource
        resource_attrs = {
            "service.name": span.service_name or span.resource_attributes.get("service.name", "unknown"),
            "cloud.provider": "aws",
            "cloud.platform": "aws_bedrock_agentcore",
        }
        resource_attrs.update(span.resource_attributes)
        resource = {"attributes": resource_attrs}

    # Extract scope from raw_message if available, otherwise use default
    if span.raw_message and isinstance(span.raw_message, dict) and "scope" in span.raw_message:
        scope = span.raw_message["scope"]
    else:
        scope = {"name": "", "version": ""}

    # Build span attributes - merge existing and add session if provided
    span_attrs = dict(span.attributes)
    if session_id and "session.id" not in span_attrs:
        span_attrs["session.id"] = session_id

    # Extract flags from raw_message if available
    flags = 256  # Default flag value
    if span.raw_message and isinstance(span.raw_message, dict) and "flags" in span.raw_message:
        flags = span.raw_message["flags"]

    # Build OTel span structure
    otel_span = {
        "resource": resource,
        "scope": scope,
        "traceId": span.trace_id,
        "spanId": span.span_id,
        "flags": flags,
        "name": span.span_name,
        "kind": span.kind or "INTERNAL",
        "attributes": span_attrs,
        "status": {"code": span.status_code or "UNSET"},
    }

    # Add parent span ID if present
    if span.parent_span_id:
        otel_span["parentSpanId"] = span.parent_span_id

    # Add timing information
    if span.start_time_unix_nano:
        otel_span["startTimeUnixNano"] = span.start_time_unix_nano

    if span.end_time_unix_nano:
        otel_span["endTimeUnixNano"] = span.end_time_unix_nano

    # Calculate duration in nanoseconds
    if span.start_time_unix_nano and span.end_time_unix_nano:
        otel_span["durationNano"] = span.end_time_unix_nano - span.start_time_unix_nano

    # Add status message if present
    if span.status_message:
        otel_span["status"]["message"] = span.status_message

    # Add events if present
    if span.events:
        otel_span["events"] = span.events

    return otel_span


def transform_runtime_log_to_otel_event(
    log: RuntimeLog, session_id: Optional[str] = None, service_name: str = "unknown"
) -> Dict[str, Any]:
    """Transform a RuntimeLog to OpenTelemetry log event format.

    Args:
        log: RuntimeLog object from observability module
        session_id: Optional session ID
        service_name: Service name for resource attributes

    Returns:
        Dictionary in OpenTelemetry log event format
    """
    # Extract resource from raw_message if available
    if log.raw_message and isinstance(log.raw_message, dict) and "resource" in log.raw_message:
        resource = log.raw_message["resource"]
    else:
        # Fallback: build minimal resource
        resource = {
            "attributes": {
                "service.name": service_name,
                "cloud.provider": "aws",
                "cloud.platform": "aws_bedrock_agentcore",
            }
        }

    # Extract scope from raw_message if available
    if log.raw_message and isinstance(log.raw_message, dict) and "scope" in log.raw_message:
        scope = log.raw_message["scope"]
    else:
        scope = {"name": "", "version": ""}

    # Extract attributes from raw_message if available
    if log.raw_message and isinstance(log.raw_message, dict) and "attributes" in log.raw_message:
        log_attrs = dict(log.raw_message["attributes"])
        # Add session ID if not already present
        if session_id and "session.id" not in log_attrs:
            log_attrs["session.id"] = session_id
    else:
        # Fallback: build minimal attributes
        log_attrs = {}
        if session_id:
            log_attrs["session.id"] = session_id

    # Extract severity from raw_message if available
    severity_number = 9  # Default: INFO level
    severity_text = ""
    if log.raw_message and isinstance(log.raw_message, dict):
        if "severityNumber" in log.raw_message:
            severity_number = log.raw_message["severityNumber"]
        if "severityText" in log.raw_message:
            severity_text = log.raw_message["severityText"]

    # Extract timing from raw_message (required for OTel logs)
    time_unix_nano = None
    observed_time_unix_nano = None
    if log.raw_message and isinstance(log.raw_message, dict):
        time_unix_nano = log.raw_message.get("timeUnixNano")
        observed_time_unix_nano = log.raw_message.get("observedTimeUnixNano", time_unix_nano)

    # Extract trace context from raw_message if available
    trace_id = log.trace_id
    span_id = log.span_id
    flags = 1  # Default flag value
    if log.raw_message and isinstance(log.raw_message, dict):
        if "traceId" in log.raw_message:
            trace_id = log.raw_message["traceId"]
        if "spanId" in log.raw_message:
            span_id = log.raw_message["spanId"]
        if "flags" in log.raw_message:
            flags = log.raw_message["flags"]

    # Build OTel log event structure
    otel_event = {
        "resource": resource,
        "scope": scope,
        "severityNumber": severity_number,
        "severityText": severity_text,
        "attributes": log_attrs,
        "flags": flags,
    }

    # Add timing
    if time_unix_nano:
        otel_event["timeUnixNano"] = time_unix_nano
    if observed_time_unix_nano:
        otel_event["observedTimeUnixNano"] = observed_time_unix_nano

    # Add trace context if available
    if trace_id:
        otel_event["traceId"] = trace_id
    if span_id:
        otel_event["spanId"] = span_id

    # Add body - extract from raw_message or use simple message
    if log.raw_message and isinstance(log.raw_message, dict):
        # Extract the actual body content from the CloudWatch log entry
        # The raw_message has structure: {body: {input: {...}, output: {...}}}
        if "body" in log.raw_message:
            otel_event["body"] = log.raw_message["body"]
        else:
            # Fallback: use the whole raw_message if no body field
            otel_event["body"] = log.raw_message
    else:
        # No structured data, use plain message
        otel_event["body"] = {"message": log.message}

    return otel_event


def transform_trace_data_to_otel(
    trace_data: TraceData, latest_trace_only: bool = True, trace_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Transform complete TraceData to list of OpenTelemetry spans and log events.

    By default, only transforms data from the latest trace to stay within
    the evaluation API's 100 span limit.

    Args:
        trace_data: TraceData object containing spans and runtime logs
        latest_trace_only: If True, only include data from the latest trace (default: True)
        trace_id: Optional specific trace ID to filter to (overrides latest_trace_only)

    Returns:
        List of OpenTelemetry-formatted spans and log events
    """
    otel_items = []

    # Get session ID if available
    session_id = trace_data.session_id

    # Get service name from first span if available
    service_name = "unknown"
    if trace_data.spans:
        service_name = trace_data.spans[0].service_name or "unknown"

    # Filter to specific trace or latest trace
    spans_to_transform = trace_data.spans
    logs_to_transform = trace_data.runtime_logs
    target_trace_id = None

    # If specific trace_id is provided, use that
    if trace_id:
        target_trace_id = trace_id
        spans_to_transform = [s for s in trace_data.spans if s.trace_id == trace_id]
        logs_to_transform = [log for log in trace_data.runtime_logs if log.trace_id == trace_id]

    # Otherwise, if latest_trace_only is requested, find the latest trace
    elif latest_trace_only and trace_data.spans:
        # Get all unique trace IDs
        trace_ids = trace_data.get_trace_ids()
        if trace_ids:
            # Find the latest trace by looking at the most recent span timestamp
            latest_timestamp = None

            for tid in trace_ids:
                # Get spans for this trace
                trace_spans = [s for s in trace_data.spans if s.trace_id == tid]
                if not trace_spans:
                    continue

                # Find the most recent end time in this trace
                for span in trace_spans:
                    if span.end_time_unix_nano:
                        if latest_timestamp is None or span.end_time_unix_nano > latest_timestamp:
                            latest_timestamp = span.end_time_unix_nano
                            target_trace_id = tid

            # Filter to only spans and logs from the latest trace
            if target_trace_id:
                spans_to_transform = [s for s in trace_data.spans if s.trace_id == target_trace_id]
                logs_to_transform = [log for log in trace_data.runtime_logs if log.trace_id == target_trace_id]

    # Transform spans - prioritize spans with gen_ai attributes
    # These are the spans that contain AI interaction data needed for evaluation
    spans_with_genai = []
    spans_without_genai = []

    for span in spans_to_transform:
        has_genai = any(k.startswith("gen_ai") for k in span.attributes.keys())
        if has_genai:
            spans_with_genai.append(span)
        else:
            spans_without_genai.append(span)

    # Transform gen_ai spans first (most important for evaluation)
    for span in spans_with_genai:
        otel_span = transform_span_to_otel(span, session_id)
        otel_items.append(otel_span)

    # Then add infrastructure spans if there's room
    for span in spans_without_genai:
        otel_span = transform_span_to_otel(span, session_id)
        otel_items.append(otel_span)

    # Transform runtime logs to OTel log events
    # Only include logs with structured message data (input/output)
    for log in logs_to_transform:
        # Check if log has structured body with input/output messages
        if log.raw_message and isinstance(log.raw_message, dict):
            body = log.raw_message.get("body", {})
            # Only include if body has input or output (actual conversation data)
            if isinstance(body, dict) and ("input" in body or "output" in body):
                otel_event = transform_runtime_log_to_otel_event(log, session_id, service_name)
                otel_items.append(otel_event)

    return otel_items


def validate_otel_span(otel_span: Dict[str, Any]) -> bool:
    """Validate that an OTel span has required fields.

    Args:
        otel_span: OpenTelemetry span dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["traceId", "spanId", "name"]
    return all(field in otel_span for field in required_fields)
