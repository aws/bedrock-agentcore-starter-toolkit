"""Unit tests for telemetry models (Span, RuntimeLog, TraceData)."""

import pytest

from bedrock_agentcore_starter_toolkit.operations.observability.models.telemetry import (
    RuntimeLog,
    Span,
    TraceData,
)


class TestSpan:
    """Test cases for Span model."""

    @pytest.mark.parametrize(
        "cloudwatch_result,expected_trace_id,expected_span_id,expected_span_name",
        [
            (
                [
                    {"field": "traceId", "value": "trace-123"},
                    {"field": "spanId", "value": "span-456"},
                    {"field": "spanName", "value": "TestSpan"},
                ],
                "trace-123",
                "span-456",
                "TestSpan",
            ),
            (
                [
                    {"field": "traceId", "value": "690156557a198c640accf1ab0fae04dd"},
                    {"field": "spanId", "value": "1129b35d7c071f2e"},
                    {"field": "spanName", "value": "AgentCore.Runtime.Invoke"},
                ],
                "690156557a198c640accf1ab0fae04dd",
                "1129b35d7c071f2e",
                "AgentCore.Runtime.Invoke",
            ),
        ],
    )
    def test_span_from_cloudwatch_result_basic_fields(
        self, cloudwatch_result, expected_trace_id, expected_span_id, expected_span_name
    ):
        """Test creating Span from CloudWatch result with basic fields."""
        span = Span.from_cloudwatch_result(cloudwatch_result)

        assert span.trace_id == expected_trace_id
        assert span.span_id == expected_span_id
        assert span.span_name == expected_span_name

    @pytest.mark.parametrize(
        "cloudwatch_result,expected_duration,expected_status_code",
        [
            (
                [
                    {"field": "traceId", "value": "trace-1"},
                    {"field": "spanId", "value": "span-1"},
                    {"field": "spanName", "value": "TestSpan"},
                    {"field": "durationMs", "value": "123.45"},
                    {"field": "statusCode", "value": "OK"},
                ],
                123.45,
                "OK",
            ),
            (
                [
                    {"field": "traceId", "value": "trace-2"},
                    {"field": "spanId", "value": "span-2"},
                    {"field": "spanName", "value": "ErrorSpan"},
                    {"field": "durationMs", "value": "500.0"},
                    {"field": "statusCode", "value": "ERROR"},
                ],
                500.0,
                "ERROR",
            ),
        ],
    )
    def test_span_from_cloudwatch_result_timing_and_status(
        self, cloudwatch_result, expected_duration, expected_status_code
    ):
        """Test Span creation with timing and status fields."""
        span = Span.from_cloudwatch_result(cloudwatch_result)

        assert span.duration_ms == expected_duration
        assert span.status_code == expected_status_code

    def test_span_from_cloudwatch_result_with_message(self):
        """Test Span creation with @message containing attributes."""
        cloudwatch_result = [
            {"field": "traceId", "value": "trace-123"},
            {"field": "spanId", "value": "span-456"},
            {"field": "spanName", "value": "TestSpan"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"gen_ai.request.model": "claude-3"}, '
                    '"resource": {"attributes": {"service.name": "test-service"}}}'
                ),
            },
        ]

        span = Span.from_cloudwatch_result(cloudwatch_result)

        assert span.attributes.get("gen_ai.request.model") == "claude-3"
        assert span.resource_attributes.get("service.name") == "test-service"

    @pytest.mark.parametrize(
        "parent_span_id,expected_parent",
        [
            ("parent-123", "parent-123"),
            (None, None),
            ("", ""),
        ],
    )
    def test_span_hierarchy_fields(self, parent_span_id, expected_parent):
        """Test Span hierarchy fields (parent_span_id, children)."""
        cloudwatch_result = [
            {"field": "traceId", "value": "trace-1"},
            {"field": "spanId", "value": "span-1"},
            {"field": "spanName", "value": "ChildSpan"},
            {"field": "parentSpanId", "value": parent_span_id},
        ]

        span = Span.from_cloudwatch_result(cloudwatch_result)

        assert span.parent_span_id == expected_parent
        assert span.children == []  # Initially empty


class TestRuntimeLog:
    """Test cases for RuntimeLog model."""

    @pytest.mark.parametrize(
        "cloudwatch_result,expected_timestamp,expected_message",
        [
            (
                [
                    {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
                    {"field": "@message", "value": "Test log message"},
                    {"field": "spanId", "value": "span-123"},
                    {"field": "traceId", "value": "trace-456"},
                ],
                "2025-10-28T10:00:00Z",
                "Test log message",
            ),
        ],
    )
    def test_runtime_log_from_cloudwatch_result(self, cloudwatch_result, expected_timestamp, expected_message):
        """Test creating RuntimeLog from CloudWatch result."""
        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)

        assert log.timestamp == expected_timestamp
        assert log.message == expected_message

    def test_runtime_log_get_exception(self):
        """Test extracting exception from runtime log."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"exception.type": "ValueError", "exception.message": "Invalid input", '
                    '"exception.stacktrace": "Traceback..."}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        exception = log.get_exception()

        assert exception is not None
        assert exception["type"] == "exception"
        assert exception["exception_type"] == "ValueError"
        assert exception["message"] == "Invalid input"
        assert exception["stacktrace"] == "Traceback..."

    def test_runtime_log_get_exception_none_when_no_exception(self):
        """Test that get_exception returns None when no exception present."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {"field": "@message", "value": "Regular log message"},
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        exception = log.get_exception()

        assert exception is None

    @pytest.mark.parametrize(
        "event_name,role,expected_role",
        [
            ("gen_ai.system.message", None, "system"),
            ("gen_ai.user.message", None, "user"),
            ("gen_ai.assistant.message", None, "assistant"),
            ("gen_ai.choice", None, "assistant"),
        ],
    )
    def test_runtime_log_get_gen_ai_message(self, event_name, role, expected_role):  # noqa: ARG002
        """Test extracting GenAI messages from runtime log."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    f'{{"attributes": {{"event.name": "{event_name}"}}, "body": {{"content": [{{"text": "Hello"}}]}}}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["type"] == "message"
        assert message["role"] == expected_role
        assert message["content"] == "Hello"

    def test_runtime_log_get_event_payload(self):
        """Test extracting event payload from runtime log."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "custom.event"}, "body": {"key": "value"}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        event = log.get_event_payload()

        assert event is not None
        assert event["type"] == "event"
        assert event["event_name"] == "custom.event"
        assert event["payload"]["key"] == "value"

    def test_runtime_log_event_payload_skips_exceptions(self):
        """Test that event payload extraction skips logs with exceptions."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"exception.type": "ValueError", "event.name": "some.event"}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        event = log.get_event_payload()

        # Should return None because exception is present
        assert event is None

    def test_runtime_log_event_payload_without_event_name(self):
        """Test that events without event.name use message as fallback."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"body": {"message": "Attempting to instrument while already instrumented"}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        event = log.get_event_payload()

        assert event is not None
        assert event["type"] == "event"
        # Should use message as event name
        assert "Attempting to instrument" in event["event_name"]
        assert event["payload"]["message"] == "Attempting to instrument while already instrumented"


class TestTraceData:
    """Test cases for TraceData model."""

    @pytest.fixture
    def sample_spans(self):
        """Create sample spans for testing."""
        return [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="RootSpan",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=2000000000,
                duration_ms=1000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-1",
                span_id="span-2",
                span_name="ChildSpan",
                parent_span_id="span-1",
                start_time_unix_nano=1500000000,
                end_time_unix_nano=1800000000,
                duration_ms=300.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-2",
                span_id="span-3",
                span_name="AnotherTrace",
                start_time_unix_nano=3000000000,
                end_time_unix_nano=4000000000,
                duration_ms=1000.0,
                status_code="ERROR",
            ),
        ]

    def test_trace_data_initialization(self, sample_spans):
        """Test TraceData initialization."""
        trace_data = TraceData(
            session_id="session-123",
            agent_id="agent-456",
            spans=sample_spans,
        )

        assert trace_data.session_id == "session-123"
        assert trace_data.agent_id == "agent-456"
        assert len(trace_data.spans) == 3
        assert trace_data.traces == {}  # Not grouped yet

    def test_trace_data_group_spans_by_trace(self, sample_spans):
        """Test grouping spans by trace ID."""
        trace_data = TraceData(spans=sample_spans)
        trace_data.group_spans_by_trace()

        assert len(trace_data.traces) == 2
        assert "trace-1" in trace_data.traces
        assert "trace-2" in trace_data.traces
        assert len(trace_data.traces["trace-1"]) == 2
        assert len(trace_data.traces["trace-2"]) == 1

    def test_trace_data_get_trace_ids(self, sample_spans):
        """Test getting unique trace IDs."""
        trace_data = TraceData(spans=sample_spans)
        trace_ids = trace_data.get_trace_ids()

        assert len(trace_ids) == 2
        assert "trace-1" in trace_ids
        assert "trace-2" in trace_ids

    def test_trace_data_build_span_hierarchy(self, sample_spans):
        """Test building span hierarchy."""
        trace_data = TraceData(spans=sample_spans)
        trace_data.group_spans_by_trace()

        root_spans = trace_data.build_span_hierarchy("trace-1")

        assert len(root_spans) == 1
        assert root_spans[0].span_id == "span-1"
        assert len(root_spans[0].children) == 1
        assert root_spans[0].children[0].span_id == "span-2"

    @pytest.mark.parametrize(
        "runtime_log_data,expected_item_type",
        [
            (
                {
                    "@timestamp": "2025-10-28T10:00:00Z",
                    "@message": '{"attributes": {"exception.type": "ValueError"}}',
                    "spanId": "span-1",
                    "traceId": "trace-1",
                },
                "exception",
            ),
            (
                {
                    "@timestamp": "2025-10-28T10:00:00Z",
                    "@message": (
                        '{"attributes": {"event.name": "gen_ai.user.message"}, "body": {"content": [{"text": "Hi"}]}}'
                    ),
                    "spanId": "span-1",
                    "traceId": "trace-1",
                },
                "message",
            ),
            (
                {
                    "@timestamp": "2025-10-28T10:00:00Z",
                    "@message": '{"attributes": {"event.name": "custom.event"}, "body": {"data": "test"}}',
                    "spanId": "span-1",
                    "traceId": "trace-1",
                },
                "event",
            ),
        ],
    )
    def test_trace_data_get_messages_by_span(self, runtime_log_data, expected_item_type):
        """Test extracting messages/events/exceptions from runtime logs."""
        cloudwatch_result = [{"field": k, "value": v} for k, v in runtime_log_data.items()]
        runtime_log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)

        trace_data = TraceData(runtime_logs=[runtime_log])
        messages_by_span = trace_data.get_messages_by_span()

        assert "span-1" in messages_by_span
        assert len(messages_by_span["span-1"]) == 1
        assert messages_by_span["span-1"][0]["type"] == expected_item_type

    def test_trace_data_to_dict(self, sample_spans):
        """Test converting TraceData to dictionary."""
        trace_data = TraceData(
            session_id="session-123",
            agent_id="agent-456",
            spans=sample_spans,
        )
        trace_data.group_spans_by_trace()

        result_dict = trace_data.to_dict()

        assert result_dict["session_id"] == "session-123"
        assert result_dict["agent_id"] == "agent-456"
        assert result_dict["trace_count"] == 2
        assert result_dict["total_span_count"] == 3
        assert "traces" in result_dict
        assert "trace-1" in result_dict["traces"]
        assert "trace-2" in result_dict["traces"]

    def test_trace_data_to_dict_includes_hierarchy(self, sample_spans):
        """Test that to_dict includes span hierarchy."""
        trace_data = TraceData(spans=sample_spans)
        trace_data.group_spans_by_trace()

        result_dict = trace_data.to_dict()

        trace_1_data = result_dict["traces"]["trace-1"]
        assert "root_spans" in trace_1_data
        assert len(trace_1_data["root_spans"]) == 1

        root_span = trace_1_data["root_spans"][0]
        assert root_span["span_id"] == "span-1"
        assert "children" in root_span
        assert len(root_span["children"]) == 1
        assert root_span["children"][0]["span_id"] == "span-2"


class TestRuntimeLogEdgeCases:
    """Test edge cases in RuntimeLog parsing."""

    def test_runtime_log_get_gen_ai_message_with_text_field(self):
        """Test extracting GenAI message with direct text field."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "gen_ai.user.message"}, "body": {"text": "Direct text"}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["content"] == "Direct text"

    def test_runtime_log_get_gen_ai_message_with_string_body(self):
        """Test extracting GenAI message when body is a string."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "gen_ai.user.message"}, "body": "String body"}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["content"] == "String body"

    def test_runtime_log_get_gen_ai_message_no_content(self):
        """Test extracting GenAI message when no content available."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "gen_ai.user.message"}, "body": {}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        # Should return None if no content
        assert message is None

    def test_runtime_log_get_gen_ai_message_unknown_role(self):
        """Test extracting GenAI message with unknown event name."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "gen_ai.unknown"}, "body": {"text": "Test"}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        # Should return None for unknown role
        assert message is None

    def test_runtime_log_get_gen_ai_message_with_tool_use(self):
        """Test extracting GenAI message with tool_use block (direct type)."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.assistant.message"}, '
                    '"body": {"content": [{"text": "Let me help"}, '
                    '{"type": "tool_use", "name": "calculate", "input": {"expression": "2+2"}}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["role"] == "assistant"
        assert "Let me help" in message["content"]
        assert "🔧 Tool Use: calculate" in message["content"]
        assert "expression" in message["content"]

    def test_runtime_log_get_gen_ai_message_with_nested_tool_use(self):
        """Test extracting GenAI message with nested tool_use block."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.assistant.message"}, '
                    '"body": {"content": [{"text": "Using the tool"}, '
                    '{"tool_use": {"name": "search", "input": {"query": "test"}}}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["role"] == "assistant"
        assert "Using the tool" in message["content"]
        assert "🔧 Tool Use: search" in message["content"]
        assert "query" in message["content"]

    def test_runtime_log_get_gen_ai_message_tool_use_only(self):
        """Test extracting GenAI message with ONLY tool use (no text)."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.assistant.message"}, '
                    '"body": {"content": [{"type": "tool_use", "name": "calculate", "input": {"x": 5}}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["role"] == "assistant"
        assert "🔧 Tool Use: calculate" in message["content"]
        assert "x" in message["content"]

    def test_runtime_log_get_event_payload_with_string_body(self):
        """Test extracting event payload when body is a string."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "custom.event"}, "body": "String body content"}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        event = log.get_event_payload()

        assert event is not None
        assert event["type"] == "event"
        assert event["payload"]["message"] == "String body content"

    def test_runtime_log_get_event_payload_invalid_json_string(self):
        """Test extracting event payload when body is invalid JSON string."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "custom.event"}, "body": "not valid json {"}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        event = log.get_event_payload()

        assert event is not None
        # Should wrap in message field
        assert "message" in event["payload"]


class TestSpanEdgeCases:
    """Test edge cases in Span parsing."""

    def test_span_from_cloudwatch_with_invalid_json_in_message(self):
        """Test Span creation when @message contains invalid JSON."""
        cloudwatch_result = [
            {"field": "traceId", "value": "trace-123"},
            {"field": "spanId", "value": "span-456"},
            {"field": "spanName", "value": "TestSpan"},
            {
                "field": "@message",
                "value": "not valid json {",
            },
        ]

        span = Span.from_cloudwatch_result(cloudwatch_result)

        assert span.trace_id == "trace-123"
        # Should not crash, attributes should be empty or string
        assert isinstance(span.attributes, dict)

    def test_span_from_cloudwatch_with_invalid_duration(self):
        """Test Span creation with invalid duration value."""
        cloudwatch_result = [
            {"field": "traceId", "value": "trace-123"},
            {"field": "spanId", "value": "span-456"},
            {"field": "spanName", "value": "TestSpan"},
            {"field": "durationMs", "value": "not-a-number"},
        ]

        span = Span.from_cloudwatch_result(cloudwatch_result)

        assert span.duration_ms is None  # Should handle gracefully

    def test_span_from_cloudwatch_with_invalid_timestamps(self):
        """Test Span creation with invalid timestamp values."""
        cloudwatch_result = [
            {"field": "traceId", "value": "trace-123"},
            {"field": "spanId", "value": "span-456"},
            {"field": "spanName", "value": "TestSpan"},
            {"field": "startTimeUnixNano", "value": "invalid"},
            {"field": "endTimeUnixNano", "value": "also-invalid"},
        ]

        span = Span.from_cloudwatch_result(cloudwatch_result)

        assert span.start_time_unix_nano is None
        assert span.end_time_unix_nano is None

    def test_span_from_cloudwatch_with_non_dict_attributes(self):
        """Test Span creation when attributes in @message is not a dict."""
        cloudwatch_result = [
            {"field": "traceId", "value": "trace-123"},
            {"field": "spanId", "value": "span-456"},
            {"field": "spanName", "value": "TestSpan"},
            {
                "field": "@message",
                "value": '{"attributes": "not a dict", "resource": {"attributes": "also not a dict"}}',
            },
        ]

        span = Span.from_cloudwatch_result(cloudwatch_result)

        # Should default to empty dicts
        assert span.attributes == {}
        assert span.resource_attributes == {}


class TestTraceDataHelperMethods:
    """Test TraceData helper methods."""

    def test_calculate_trace_duration_with_timestamps(self):
        """Test calculating trace duration from span timestamps."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Span1",
                start_time_unix_nano=1_000_000_000,  # 1 second
                end_time_unix_nano=3_000_000_000,  # 3 seconds
            ),
            Span(
                trace_id="trace-1",
                span_id="span-2",
                span_name="Span2",
                start_time_unix_nano=2_000_000_000,  # 2 seconds
                end_time_unix_nano=5_000_000_000,  # 5 seconds
            ),
        ]

        duration = TraceData.calculate_trace_duration(spans)

        # Duration should be from earliest start (1s) to latest end (5s) = 4s = 4000ms
        assert duration == 4000.0

    def test_calculate_trace_duration_fallback_to_durations(self):
        """Test calculating trace duration falls back to span durations when no timestamps."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="RootSpan",
                duration_ms=100.0,
                # No parent = root span
            ),
            Span(
                trace_id="trace-1",
                span_id="span-2",
                span_name="ChildSpan",
                parent_span_id="span-1",
                duration_ms=50.0,
            ),
        ]

        duration = TraceData.calculate_trace_duration(spans)

        # Should use root span duration only (not sum of all)
        assert duration == 100.0

    def test_calculate_trace_duration_multiple_root_spans(self):
        """Test calculating trace duration with multiple root spans."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="RootSpan1",
                duration_ms=100.0,
            ),
            Span(
                trace_id="trace-1",
                span_id="span-2",
                span_name="RootSpan2",
                duration_ms=150.0,
            ),
        ]

        duration = TraceData.calculate_trace_duration(spans)

        # Should sum all root spans
        assert duration == 250.0


class TestRuntimeLogRobustness:
    """Test robustness across different model formats and malformed data."""

    def test_extract_text_from_content_string(self):
        """Test extracting text when content is a string (not array)."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "gen_ai.user.message"}, "body": {"content": "Hello world"}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["content"] == "Hello world"
        assert message["role"] == "user"

    def test_extract_tool_with_parameters_field(self):
        """Test extracting tool when using 'parameters' instead of 'input' or 'arguments'."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.assistant.message"}, '
                    '"body": {"content": [{"name": "search", "parameters": {"query": "test"}}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert "🔧 Tool Use: search" in message["content"]
        assert "query" in message["content"]
        assert "test" in message["content"]

    def test_extract_tool_result_with_tool_call_id(self):
        """Test extracting tool result with tool_call_id field (OpenAI style)."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.tool.message"}, '
                    '"body": {"role": "tool", "tool_call_id": "call_123", "content": "Result data"}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert message["role"] == "tool"
        assert "call_123" in message["content"]
        assert "Result data" in message["content"]

    def test_extract_tool_with_malformed_arguments_json(self):
        """Test graceful handling of malformed JSON in arguments."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.assistant.message"}, '
                    '"body": {"content": [{"name": "calculate", "arguments": "not valid json {"}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        # Should not crash, should extract tool with raw_arguments
        assert message is not None
        assert "🔧 Tool Use: calculate" in message["content"]
        assert "raw_arguments" in message["content"]

    def test_extract_tool_with_type_function(self):
        """Test extracting tool when type is 'function' (generic LLM framework style)."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.assistant.message"}, '
                    '"body": {"content": [{"type": "function", "name": "search", "input": {"q": "test"}}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert "🔧 Tool Use: search" in message["content"]
        assert "q" in message["content"]

    def test_extract_mixed_content_array(self):
        """Test extracting from content array with strings and dicts."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.assistant.message"}, '
                    '"body": {"content": ["Text part", {"text": "Another text"}, '
                    '{"name": "tool", "input": {"x": 1}}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert "Text part" in message["content"]
        assert "Another text" in message["content"]
        assert "🔧 Tool Use: tool" in message["content"]

    def test_handle_empty_content(self):
        """Test graceful handling of empty content."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": '{"attributes": {"event.name": "gen_ai.user.message"}, "body": {}}',
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        # Should return None for empty content
        assert message is None

    def test_handle_nested_tool_definitions(self):
        """Test extracting tool definitions from nested structures."""
        cloudwatch_result = [
            {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
            {
                "field": "@message",
                "value": (
                    '{"attributes": {"event.name": "gen_ai.system.message"}, '
                    '"body": {"tools": [{"type": "function", "function": '
                    '{"name": "search", "description": "Search tool"}}]}}'
                ),
            },
            {"field": "spanId", "value": "span-123"},
            {"field": "traceId", "value": "trace-456"},
        ]

        log = RuntimeLog.from_cloudwatch_result(cloudwatch_result)
        message = log.get_gen_ai_message()

        assert message is not None
        assert "🛠️ Available Tools:" in message["content"]
        assert "search: Search tool" in message["content"]


class TestTraceDataEdgeCases:
    """Test edge cases in TraceData."""

    def test_trace_data_build_hierarchy_orphan_children(self):
        """Test building hierarchy when child references non-existent parent."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-child",
                span_name="OrphanChild",
                parent_span_id="non-existent-parent",
                duration_ms=100.0,
            )
        ]

        trace_data = TraceData(spans=spans)
        trace_data.group_spans_by_trace()
        root_spans = trace_data.build_span_hierarchy("trace-1")

        # Orphan should be treated as root
        assert len(root_spans) == 1
        assert root_spans[0].span_id == "span-child"

    def test_trace_data_to_dict_with_no_timestamps(self):
        """Test to_dict when spans have no timestamps."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="NoTimeSpan",
                # No start/end times
                duration_ms=100.0,
            )
        ]

        trace_data = TraceData(spans=spans)
        trace_data.group_spans_by_trace()
        result = trace_data.to_dict()

        assert "traces" in result
        assert "trace-1" in result["traces"]
        # Should use fallback duration calculation
        assert result["traces"]["trace-1"]["total_duration_ms"] >= 0

    def test_trace_data_get_messages_by_span_no_span_id(self):
        """Test get_messages_by_span when logs have no span_id."""
        runtime_log = RuntimeLog(
            timestamp="2025-10-28T10:00:00Z",
            message="Test log",
            span_id=None,  # No span ID
            trace_id="trace-1",
            raw_message={"attributes": {"event.name": "test.event"}, "body": {"data": "test"}},
        )

        trace_data = TraceData(runtime_logs=[runtime_log])
        messages = trace_data.get_messages_by_span()

        # Should not include logs without span_id
        assert len(messages) == 0
