"""Data models for observability spans, traces, and logs.

These are pure data classes (POJOs) with no business logic.
"""

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
    children: List["Span"] = field(default_factory=list, repr=False)


@dataclass
class RuntimeLog:
    """Represents a runtime log entry from agent-specific log groups."""

    timestamp: str
    message: str
    span_id: Optional[str] = None
    trace_id: Optional[str] = None
    log_stream: Optional[str] = None
    raw_message: Optional[Dict[str, Any]] = None


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
