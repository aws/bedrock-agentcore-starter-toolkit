"""Data models for observability spans, traces, and logs.

These are pure data classes (POJOs) with no business logic.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    """Represents an OpenTelemetry span with trace and timing information."""

    trace_id: str
    span_id: str
    span_name: str
    session_id: str | None = None
    start_time_unix_nano: int | None = None
    end_time_unix_nano: int | None = None
    duration_ms: float | None = None
    status_code: str | None = None
    status_message: str | None = None
    parent_span_id: str | None = None
    kind: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    resource_attributes: dict[str, Any] = field(default_factory=dict)
    service_name: str | None = None
    resource_id: str | None = None
    service_type: str | None = None
    timestamp: str | None = None
    raw_message: dict[str, Any] | None = None
    children: list["Span"] = field(default_factory=list, repr=False)


@dataclass
class RuntimeLog:
    """Represents a runtime log entry from agent-specific log groups."""

    timestamp: str
    message: str
    span_id: str | None = None
    trace_id: str | None = None
    log_stream: str | None = None
    raw_message: dict[str, Any] | None = None


@dataclass
class TraceData:
    """Complete trace/session data including spans and runtime logs."""

    session_id: str | None = None
    agent_id: str | None = None
    spans: list[Span] = field(default_factory=list)
    runtime_logs: list[RuntimeLog] = field(default_factory=list)
    traces: dict[str, list[Span]] = field(default_factory=dict)
    start_time: int | None = None
    end_time: int | None = None
