"""Unit tests for evaluation transformer."""

from bedrock_agentcore_starter_toolkit.operations.evaluation.transformer import (
    transform_runtime_log_to_otel_event,
    transform_span_to_otel,
    transform_trace_data_to_otel,
    validate_otel_span,
)
from bedrock_agentcore_starter_toolkit.operations.observability.models.telemetry import (
    RuntimeLog,
    Span,
    TraceData,
)


class TestSpanTransformation:
    """Test span-to-OTel transformation."""

    def test_transform_span_basic_fields(self):
        """Test transforming span with basic fields."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
            start_time_unix_nano=1_000_000_000,
            end_time_unix_nano=2_000_000_000,
        )

        otel_span = transform_span_to_otel(span)

        assert otel_span["traceId"] == "trace-123"
        assert otel_span["spanId"] == "span-456"
        assert otel_span["name"] == "TestSpan"
        assert otel_span["startTimeUnixNano"] == 1_000_000_000
        assert otel_span["endTimeUnixNano"] == 2_000_000_000
        assert otel_span["durationNano"] == 1_000_000_000  # 1 second

    def test_transform_span_with_parent(self):
        """Test span with parent ID."""
        span = Span(
            trace_id="trace-123",
            span_id="span-child",
            span_name="ChildSpan",
            parent_span_id="span-parent",
        )

        otel_span = transform_span_to_otel(span)

        assert otel_span["parentSpanId"] == "span-parent"

    def test_transform_span_with_status(self):
        """Test span with status information."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
            status_code="ERROR",
            status_message="Something went wrong",
        )

        otel_span = transform_span_to_otel(span)

        assert otel_span["status"]["code"] == "ERROR"
        assert otel_span["status"]["message"] == "Something went wrong"

    def test_transform_span_with_attributes(self):
        """Test span with custom attributes."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
            attributes={"gen_ai.request.model": "claude-3", "custom.field": "value"},
        )

        otel_span = transform_span_to_otel(span)

        assert otel_span["attributes"]["gen_ai.request.model"] == "claude-3"
        assert otel_span["attributes"]["custom.field"] == "value"

    def test_transform_span_with_session_id(self):
        """Test adding session ID to span."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
        )

        otel_span = transform_span_to_otel(span, session_id="session-789")

        assert otel_span["attributes"]["session.id"] == "session-789"

    def test_transform_span_with_resource_attributes(self):
        """Test span with resource attributes."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
            service_name="my-service",
            resource_attributes={"cloud.region": "us-west-2"},
        )

        otel_span = transform_span_to_otel(span)

        assert otel_span["resource"]["attributes"]["service.name"] == "my-service"
        assert otel_span["resource"]["attributes"]["cloud.region"] == "us-west-2"
        assert otel_span["resource"]["attributes"]["cloud.provider"] == "aws"

    def test_transform_span_with_events(self):
        """Test span with events."""
        events = [{"name": "event1", "timestamp": 123456}]
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
            events=events,
        )

        otel_span = transform_span_to_otel(span)

        assert otel_span["events"] == events


class TestRuntimeLogTransformation:
    """Test runtime log-to-OTel event transformation."""

    def test_transform_runtime_log_basic(self):
        """Test transforming basic runtime log with raw_message (real CloudWatch format)."""
        log = RuntimeLog(
            timestamp="2025-10-28T10:00:00Z",
            message="Test log message",
            span_id="span-123",
            trace_id="trace-456",
            raw_message={
                "timeUnixNano": 1762151100900232448,
                "observedTimeUnixNano": 1762151100900331618,
                "body": {"message": "Test log message"},
            },
        )

        otel_event = transform_runtime_log_to_otel_event(log)

        assert otel_event["spanId"] == "span-123"
        assert otel_event["traceId"] == "trace-456"
        assert otel_event["timeUnixNano"] == 1762151100900232448
        assert otel_event["observedTimeUnixNano"] == 1762151100900331618
        assert otel_event["body"]["message"] == "Test log message"

    def test_transform_runtime_log_with_raw_message(self):
        """Test runtime log with raw message body."""
        raw_message = {
            "attributes": {"event.name": "gen_ai.user.message"},
            "body": {"content": [{"text": "Hello"}]},
        }

        log = RuntimeLog(
            timestamp="2025-10-28T10:00:00Z",
            message="Raw message",
            span_id="span-123",
            trace_id="trace-456",
            raw_message=raw_message,
        )

        otel_event = transform_runtime_log_to_otel_event(log, session_id="session-789")

        # Body is extracted from raw_message["body"]
        assert otel_event["body"] == {"content": [{"text": "Hello"}]}
        assert otel_event["attributes"]["event.name"] == "gen_ai.user.message"
        assert otel_event["attributes"]["session.id"] == "session-789"

    def test_transform_runtime_log_with_service_name(self):
        """Test runtime log with custom service name."""
        log = RuntimeLog(
            timestamp="2025-10-28T10:00:00Z",
            message="Test log",
            span_id="span-123",
            trace_id="trace-456",
        )

        otel_event = transform_runtime_log_to_otel_event(log, service_name="custom-service")

        assert otel_event["resource"]["attributes"]["service.name"] == "custom-service"


class TestTraceDataTransformation:
    """Test complete trace data transformation."""

    def test_transform_trace_data_empty(self):
        """Test transforming empty trace data."""
        trace_data = TraceData()
        otel_items = transform_trace_data_to_otel(trace_data)

        assert otel_items == []

    def test_transform_trace_data_with_spans(self):
        """Test transforming trace data with spans."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Span1",
                start_time_unix_nano=1_000_000_000,
                end_time_unix_nano=2_000_000_000,
            ),
            Span(
                trace_id="trace-1",
                span_id="span-2",
                span_name="Span2",
                start_time_unix_nano=1_500_000_000,
                end_time_unix_nano=1_800_000_000,
            ),
        ]

        trace_data = TraceData(session_id="session-123", spans=spans)
        otel_items = transform_trace_data_to_otel(trace_data)

        assert len(otel_items) == 2
        assert all("traceId" in item for item in otel_items)
        assert all(item["attributes"]["session.id"] == "session-123" for item in otel_items)

    def test_transform_trace_data_with_runtime_logs(self):
        """Test transforming trace data with runtime logs."""
        # Runtime logs need structured body with input/output to be included
        logs = [
            RuntimeLog(
                timestamp="2025-10-28T10:00:00Z",
                message="Log 1",
                span_id="span-1",
                trace_id="trace-1",
                raw_message={"body": {"input": {"message": "Hello"}}},
            ),
            RuntimeLog(
                timestamp="2025-10-28T10:01:00Z",
                message="Log 2",
                span_id="span-2",
                trace_id="trace-1",
                raw_message={"body": {"output": {"message": "Hi"}}},
            ),
        ]

        trace_data = TraceData(session_id="session-123", runtime_logs=logs)
        otel_items = transform_trace_data_to_otel(trace_data)

        assert len(otel_items) == 2
        assert all("body" in item for item in otel_items)

    def test_transform_trace_data_mixed(self):
        """Test transforming trace data with both spans and logs."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Span1",
            )
        ]

        # Runtime log needs structured body with input/output to be included
        logs = [
            RuntimeLog(
                timestamp="2025-10-28T10:00:00Z",
                message="Log 1",
                span_id="span-1",
                trace_id="trace-1",
                raw_message={"body": {"input": {"message": "Test"}}},
            )
        ]

        trace_data = TraceData(session_id="session-123", spans=spans, runtime_logs=logs)
        otel_items = transform_trace_data_to_otel(trace_data)

        assert len(otel_items) == 2


class TestOTelSpanValidation:
    """Test OTel span validation."""

    def test_validate_otel_span_valid(self):
        """Test validating a valid OTel span."""
        otel_span = {
            "traceId": "trace-123",
            "spanId": "span-456",
            "name": "TestSpan",
        }

        assert validate_otel_span(otel_span) is True

    def test_validate_otel_span_missing_trace_id(self):
        """Test validation fails without trace ID."""
        otel_span = {
            "spanId": "span-456",
            "name": "TestSpan",
        }

        assert validate_otel_span(otel_span) is False

    def test_validate_otel_span_missing_span_id(self):
        """Test validation fails without span ID."""
        otel_span = {
            "traceId": "trace-123",
            "name": "TestSpan",
        }

        assert validate_otel_span(otel_span) is False

    def test_validate_otel_span_missing_name(self):
        """Test validation fails without name."""
        otel_span = {
            "traceId": "trace-123",
            "spanId": "span-456",
        }

        assert validate_otel_span(otel_span) is False


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_transform_span_no_timestamps(self):
        """Test span without timestamps."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
        )

        otel_span = transform_span_to_otel(span)

        assert "startTimeUnixNano" not in otel_span
        assert "endTimeUnixNano" not in otel_span
        assert "durationNano" not in otel_span

    def test_transform_span_partial_timestamps(self):
        """Test span with only start timestamp."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan",
            start_time_unix_nano=1_000_000_000,
        )

        otel_span = transform_span_to_otel(span)

        assert otel_span["startTimeUnixNano"] == 1_000_000_000
        assert "endTimeUnixNano" not in otel_span
        assert "durationNano" not in otel_span

    def test_transform_runtime_log_no_trace_context(self):
        """Test runtime log without trace/span IDs."""
        log = RuntimeLog(
            timestamp="2025-10-28T10:00:00Z",
            message="Standalone log",
        )

        otel_event = transform_runtime_log_to_otel_event(log)

        assert "traceId" not in otel_event
        assert "spanId" not in otel_event
        assert otel_event["body"]["message"] == "Standalone log"
