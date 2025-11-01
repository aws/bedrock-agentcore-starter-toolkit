"""Unit tests for TraceVisualizer."""

from io import StringIO

import pytest
from rich.console import Console

from bedrock_agentcore_starter_toolkit.operations.observability.models.telemetry import (
    RuntimeLog,
    Span,
    TraceData,
)
from bedrock_agentcore_starter_toolkit.operations.observability.visualizers.trace_visualizer import TraceVisualizer


class TestTraceVisualizer:
    """Test cases for TraceVisualizer."""

    @pytest.fixture
    def console(self):
        """Create a Rich console that captures output."""
        return Console(file=StringIO(), width=120, legacy_windows=False)

    @pytest.fixture
    def visualizer(self, console):
        """Create a TraceVisualizer instance."""
        return TraceVisualizer(console=console)

    @pytest.fixture
    def sample_span(self):
        """Create a sample span."""
        return Span(
            trace_id="trace-123",
            span_id="span-1",
            span_name="TestSpan",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000.0,
            status_code="OK",
        )

    @pytest.fixture
    def sample_trace_data(self):
        """Create sample trace data with hierarchy."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="RootSpan",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=3000000000,
                duration_ms=2000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-1",
                span_id="span-2",
                span_name="ChildSpan",
                parent_span_id="span-1",
                start_time_unix_nano=1500000000,
                end_time_unix_nano=2500000000,
                duration_ms=1000.0,
                status_code="OK",
            ),
        ]
        trace_data = TraceData(spans=spans)
        trace_data.group_spans_by_trace()
        return trace_data

    # Test initialization
    def test_initialization_with_console(self, console):
        """Test TraceVisualizer initialization with custom console."""
        visualizer = TraceVisualizer(console=console)
        assert visualizer.console == console

    def test_initialization_without_console(self):
        """Test TraceVisualizer initialization with default console."""
        visualizer = TraceVisualizer()
        assert visualizer.console is not None

    # Test _get_duration_style
    @pytest.mark.parametrize(
        "duration_ms,expected_style",
        [
            (50, "green"),
            (99, "green"),
            (100, "yellow"),
            (500, "yellow"),
            (999, "yellow"),
            (1000, "orange1"),
            (3000, "orange1"),
            (4999, "orange1"),
            (5000, "red"),
            (10000, "red"),
        ],
    )
    def test_get_duration_style(self, visualizer, duration_ms, expected_style):
        """Test duration style based on different durations."""
        assert visualizer._get_duration_style(duration_ms) == expected_style

    # Test _format_trace_header
    @pytest.mark.parametrize(
        "spans_data,expected_span_count,expected_error_count",
        [
            # Single OK span
            (
                [
                    {
                        "trace_id": "trace-1",
                        "span_id": "span-1",
                        "span_name": "Test",
                        "start_time_unix_nano": 1000000000,
                        "end_time_unix_nano": 2000000000,
                        "duration_ms": 1000.0,
                        "status_code": "OK",
                    }
                ],
                1,
                0,
            ),
            # Multiple spans with error
            (
                [
                    {
                        "trace_id": "trace-1",
                        "span_id": "span-1",
                        "span_name": "Test1",
                        "start_time_unix_nano": 1000000000,
                        "end_time_unix_nano": 2000000000,
                        "duration_ms": 1000.0,
                        "status_code": "OK",
                    },
                    {
                        "trace_id": "trace-1",
                        "span_id": "span-2",
                        "span_name": "Test2",
                        "start_time_unix_nano": 1500000000,
                        "end_time_unix_nano": 2500000000,
                        "duration_ms": 1000.0,
                        "status_code": "ERROR",
                    },
                ],
                2,
                1,
            ),
        ],
    )
    def test_format_trace_header(self, visualizer, spans_data, expected_span_count, expected_error_count):
        """Test trace header formatting with various span configurations."""
        spans = [Span(**data) for data in spans_data]
        trace_id = spans_data[0]["trace_id"]

        header = visualizer._format_trace_header(trace_id, spans)

        # Check header contains expected elements
        header_str = header.plain
        assert trace_id in header_str
        assert f"{expected_span_count} spans" in header_str

        if expected_error_count > 0:
            assert f"{expected_error_count} errors" in header_str

    # Test _get_item_id
    @pytest.mark.parametrize(
        "item,expected_prefix",
        [
            ({"type": "message", "role": "user", "content": "Hello", "timestamp": "2025-10-28T10:00:00Z"}, "msg_"),
            (
                {
                    "type": "event",
                    "event_name": "custom.event",
                    "payload": {"key": "value"},
                    "timestamp": "2025-10-28T10:00:00Z",
                },
                "evt_",
            ),
            (
                {
                    "type": "exception",
                    "exception_type": "ValueError",
                    "message": "Invalid input",
                    "timestamp": "2025-10-28T10:00:00Z",
                },
                "exc_",
            ),
        ],
    )
    def test_get_item_id(self, visualizer, item, expected_prefix):
        """Test unique ID generation for different item types."""
        item_id = visualizer._get_item_id(item)
        assert item_id.startswith(expected_prefix)
        assert item["timestamp"] in item_id

    def test_get_item_id_consistency(self, visualizer):
        """Test that same item produces same ID."""
        item = {"type": "message", "role": "user", "content": "Hello", "timestamp": "2025-10-28T10:00:00Z"}

        id1 = visualizer._get_item_id(item)
        id2 = visualizer._get_item_id(item)

        assert id1 == id2

    # Test _format_event_payload
    @pytest.mark.parametrize(
        "payload,expected_content",
        [
            ({"type": "test", "status": "ok"}, "type=test"),
            ({"name": "event1", "id": "123"}, "name=event1"),
            ({"message": "test message", "count": 5}, "message=test message"),
            ({"custom_field": "value"}, "custom_field=value"),
            ({}, ""),
        ],
    )
    def test_format_event_payload(self, visualizer, payload, expected_content):
        """Test event payload formatting."""
        result = visualizer._format_event_payload(payload)

        if expected_content:
            assert expected_content in result
        else:
            # Empty payload should return short string
            assert len(result) < 10

    # Test _format_span basic
    def test_format_span_basic(self, visualizer, sample_span):
        """Test basic span formatting without verbose mode."""
        text = visualizer._format_span(sample_span, verbose=False, messages_by_span={}, seen_messages=set())

        text_str = text.plain
        assert "TestSpan" in text_str
        assert "1000.00ms" in text_str
        assert "(OK)" in text_str

    @pytest.mark.parametrize(
        "status_code,expected_icon",
        [
            ("OK", "✓"),
            ("ERROR", "❌"),
            ("UNSET", "◦"),
            (None, "◦"),
        ],
    )
    def test_format_span_status_icons(self, visualizer, status_code, expected_icon):
        """Test span status icon rendering."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code=status_code,
        )

        text = visualizer._format_span(span, verbose=False, messages_by_span={}, seen_messages=set())

        # Check icon is present (Rich text includes formatting)
        text_str = text.plain
        assert expected_icon in text_str

    # Test _format_span verbose mode
    def test_format_span_verbose_shows_details(self, visualizer):
        """Test that verbose mode shows span ID and service name."""
        span = Span(
            trace_id="trace-1",
            span_id="span-123",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
            service_name="test-service",
        )

        text = visualizer._format_span(span, verbose=True, messages_by_span={}, seen_messages=set())

        text_str = text.plain
        assert "span-123" in text_str
        assert "test-service" in text_str

    @pytest.mark.parametrize(
        "attributes,expected_in_output",
        [
            ({"gen_ai.request.model": "claude-3-sonnet"}, "claude-3-sonnet"),
            ({"gen_ai.usage.input_tokens": 100, "gen_ai.usage.output_tokens": 50}, "in: 100"),
            ({"rpc.service": "BedrockAgentRuntime", "aws.remote.operation": "Invoke"}, "Invoke"),
            ({"http.method": "POST", "http.status_code": 200}, "POST"),
        ],
    )
    def test_format_span_verbose_metadata(self, visualizer, attributes, expected_in_output):
        """Test that verbose mode displays various metadata attributes."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
            attributes=attributes,
        )

        text = visualizer._format_span(span, verbose=True, messages_by_span={}, seen_messages=set())

        text_str = text.plain
        assert expected_in_output in text_str

    # Test _format_span with messages
    def test_format_span_handles_messages_without_crash(self, visualizer):
        """Test that span formatting handles different message types without crashing."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
        )

        # Test with various message types
        test_messages = [
            {"type": "message", "role": "user", "content": "Hello!", "timestamp": "2025-10-28"},
            {
                "type": "exception",
                "exception_type": "ValueError",
                "message": "Invalid input",
                "timestamp": "2025-10-28",
            },
            {"type": "event", "event_name": "custom.event", "payload": {"key": "value"}, "timestamp": "2025-10-28"},
        ]

        for message_data in test_messages:
            messages_by_span = {"span-1": [message_data]}

            # Should not crash
            text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

            # Basic output check
            text_str = text.plain
            assert "TestSpan" in text_str
            assert "span-1" in text_str  # Verbose mode shows span ID

    def test_format_span_deduplicates_seen_messages(self, visualizer):
        """Test that messages already shown in parent spans are not duplicated."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
        )

        message = {"type": "message", "role": "user", "content": "Hello!", "timestamp": "2025-10-28T10:00:00Z"}

        messages_by_span = {"span-1": [message]}

        # First, get the item ID
        item_id = visualizer._get_item_id(message)

        # Mark as already seen
        seen_messages = {item_id}

        text = visualizer._format_span(
            span, verbose=True, messages_by_span=messages_by_span, seen_messages=seen_messages
        )

        text_str = text.plain
        # Should NOT contain the message content since it was seen
        assert "Hello!" not in text_str

    # Test visualize_trace
    def test_visualize_trace_basic(self, visualizer, sample_trace_data):
        """Test basic trace visualization."""
        visualizer.visualize_trace(sample_trace_data, "trace-1", verbose=False)

        # Check that output was produced (console captured)
        output = visualizer.console.file.getvalue()
        assert "RootSpan" in output
        assert "ChildSpan" in output

    def test_visualize_trace_verbose(self, visualizer, sample_trace_data):
        """Test trace visualization in verbose mode."""
        visualizer.visualize_trace(sample_trace_data, "trace-1", verbose=True)

        output = visualizer.console.file.getvalue()
        assert "RootSpan" in output
        assert "ChildSpan" in output
        # Verbose mode should show span IDs
        assert "span-1" in output
        assert "span-2" in output

    def test_visualize_trace_not_found(self, visualizer, sample_trace_data):
        """Test visualization of non-existent trace."""
        visualizer.visualize_trace(sample_trace_data, "nonexistent-trace", verbose=False)

        output = visualizer.console.file.getvalue()
        assert "not found" in output

    def test_visualize_trace_with_runtime_logs(self, visualizer):
        """Test trace visualization with runtime logs containing messages."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="RootSpan",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=2000000000,
                duration_ms=1000.0,
                status_code="OK",
            )
        ]

        # Create runtime log with GenAI message
        runtime_log = RuntimeLog(
            timestamp="2025-10-28T10:00:00Z",
            message=(
                '{"attributes": {"event.name": "gen_ai.user.message"}, "body": {"content": [{"text": "Test message"}]}}'
            ),
            span_id="span-1",
            trace_id="trace-1",
            raw_message={
                "attributes": {"event.name": "gen_ai.user.message"},
                "body": {"content": [{"text": "Test message"}]},
            },
        )

        trace_data = TraceData(spans=spans, runtime_logs=[runtime_log])
        trace_data.group_spans_by_trace()

        visualizer.visualize_trace(trace_data, "trace-1", verbose=True)

        output = visualizer.console.file.getvalue()
        # Check that trace and span are displayed
        assert "RootSpan" in output
        # Check that data section appears (indicates messages are being processed)
        # The actual message display depends on the internal formatting logic
        assert "span-1" in output  # Verbose mode shows span IDs

    # Test visualize_all_traces
    def test_visualize_all_traces(self, visualizer):
        """Test visualization of multiple traces."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Trace1Span",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=2000000000,
                duration_ms=1000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-2",
                span_id="span-2",
                span_name="Trace2Span",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=2000000000,
                duration_ms=1000.0,
                status_code="ERROR",
            ),
        ]

        trace_data = TraceData(spans=spans)
        trace_data.group_spans_by_trace()

        visualizer.visualize_all_traces(trace_data, verbose=False)

        output = visualizer.console.file.getvalue()
        assert "Trace1Span" in output
        assert "Trace2Span" in output
        assert "2 traces" in output

    def test_visualize_all_traces_empty(self, visualizer):
        """Test visualization with no traces."""
        trace_data = TraceData(spans=[])
        trace_data.group_spans_by_trace()

        visualizer.visualize_all_traces(trace_data, verbose=False)

        output = visualizer.console.file.getvalue()
        assert "No traces found" in output

    # Test print_trace_summary
    def test_print_trace_summary(self, visualizer):
        """Test trace summary table printing."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Test",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=2000000000,
                duration_ms=1000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-2",
                span_id="span-2",
                span_name="Test2",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=3000000000,
                duration_ms=2000.0,
                status_code="ERROR",
            ),
        ]

        trace_data = TraceData(spans=spans)
        trace_data.group_spans_by_trace()

        visualizer.print_trace_summary(trace_data)

        output = visualizer.console.file.getvalue()
        assert "trace-1" in output
        assert "trace-2" in output
        assert "Trace Summary" in output
        # Check for error indication
        assert "ERROR" in output

    def test_print_trace_summary_empty(self, visualizer):
        """Test trace summary with no traces."""
        trace_data = TraceData(spans=[])
        trace_data.group_spans_by_trace()

        visualizer.print_trace_summary(trace_data)

        output = visualizer.console.file.getvalue()
        assert "No traces found" in output

    # Test hierarchy rendering
    def test_visualize_trace_hierarchy(self, visualizer):
        """Test that parent-child span hierarchy is correctly rendered."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="root",
                span_name="RootSpan",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=4000000000,
                duration_ms=3000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-1",
                span_id="child1",
                span_name="ChildSpan1",
                parent_span_id="root",
                start_time_unix_nano=1500000000,
                end_time_unix_nano=2500000000,
                duration_ms=1000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-1",
                span_id="child2",
                span_name="ChildSpan2",
                parent_span_id="root",
                start_time_unix_nano=2500000000,
                end_time_unix_nano=3500000000,
                duration_ms=1000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-1",
                span_id="grandchild",
                span_name="GrandchildSpan",
                parent_span_id="child1",
                start_time_unix_nano=1800000000,
                end_time_unix_nano=2200000000,
                duration_ms=400.0,
                status_code="OK",
            ),
        ]

        trace_data = TraceData(spans=spans)
        trace_data.group_spans_by_trace()

        visualizer.visualize_trace(trace_data, "trace-1", verbose=False)

        output = visualizer.console.file.getvalue()

        # All spans should be present
        assert "RootSpan" in output
        assert "ChildSpan1" in output
        assert "ChildSpan2" in output
        assert "GrandchildSpan" in output

    # Test exception rendering
    def test_visualize_trace_with_exception(self, visualizer):
        """Test that exceptions are rendered prominently."""
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="FailedSpan",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=2000000000,
                duration_ms=1000.0,
                status_code="ERROR",
            )
        ]

        runtime_log = RuntimeLog(
            timestamp="2025-10-28T10:00:00Z",
            message=(
                '{"attributes": {"exception.type": "ValueError", "exception.message": "Invalid value", '
                '"exception.stacktrace": "Traceback..."}}'
            ),
            span_id="span-1",
            trace_id="trace-1",
            raw_message={
                "attributes": {
                    "exception.type": "ValueError",
                    "exception.message": "Invalid value",
                    "exception.stacktrace": "Traceback...",
                }
            },
        )

        trace_data = TraceData(spans=spans, runtime_logs=[runtime_log])
        trace_data.group_spans_by_trace()

        visualizer.visualize_trace(trace_data, "trace-1", verbose=True)

        output = visualizer.console.file.getvalue()

        # Check that error span is displayed
        assert "FailedSpan" in output
        assert "ERROR" in output
        # Check that trace shows error count
        assert "1 errors" in output


class TestVerboseFormatting:
    """Test verbose formatting of messages, events, and exceptions."""

    def test_format_span_with_verbose_exception_short_stacktrace(self):
        """Test formatting span with exception (short stacktrace < 10 lines)."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="ErrorSpan",
            duration_ms=100.0,
            status_code="ERROR",
            attributes={"gen_ai.request.model": "test-model"},
        )

        messages_by_span = {
            "span-1": [
                {
                    "type": "exception",
                    "exception_type": "ValueError",
                    "message": "Invalid input",
                    "stacktrace": "Line 1\nLine 2\nLine 3",
                    "timestamp": "2025-10-28T10:00:00Z",
                }
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        assert "ValueError" in text_str
        assert "Invalid input" in text_str
        assert "Line 1" in text_str

    def test_format_span_with_verbose_exception_long_stacktrace(self):
        """Test formatting span with exception (long stacktrace > 10 lines)."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="ErrorSpan",
            duration_ms=100.0,
            status_code="ERROR",
            attributes={"gen_ai.request.model": "test-model"},
        )

        # Create stacktrace with 15 lines
        stacktrace_lines = [f"Line {i}" for i in range(1, 16)]
        stacktrace = "\n".join(stacktrace_lines)

        messages_by_span = {
            "span-1": [
                {
                    "type": "exception",
                    "exception_type": "RuntimeError",
                    "message": "Something went wrong",
                    "stacktrace": stacktrace,
                    "timestamp": "2025-10-28T10:00:00Z",
                }
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        assert "RuntimeError" in text_str
        assert "..." in text_str  # Should have truncation marker
        assert "Line 1" in text_str  # First line
        assert "Line 15" in text_str  # Last line

    def test_format_span_with_verbose_messages_multiple_roles(self):
        """Test formatting span with messages from different roles."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="ChatSpan",
            duration_ms=100.0,
            attributes={"gen_ai.request.model": "test-model"},
        )

        messages_by_span = {
            "span-1": [
                {
                    "type": "message",
                    "role": "system",
                    "content": "You are a helpful assistant",
                    "timestamp": "2025-10-28T10:00:00Z",
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": "Hello, how are you?",
                    "timestamp": "2025-10-28T10:00:01Z",
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": "I'm doing well, thank you!",
                    "timestamp": "2025-10-28T10:00:02Z",
                },
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        assert "System" in text_str
        assert "User" in text_str
        assert "Assistant" in text_str
        assert "helpful assistant" in text_str
        assert "Hello, how are you?" in text_str

    def test_format_span_with_verbose_message_truncation(self):
        """Test formatting span with long message (should truncate)."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="ChatSpan",
            duration_ms=100.0,
            attributes={"gen_ai.request.model": "test-model"},
        )

        # Create message longer than 200 chars
        long_content = "A" * 250

        messages_by_span = {
            "span-1": [
                {
                    "type": "message",
                    "role": "user",
                    "content": long_content,
                    "timestamp": "2025-10-28T10:00:00Z",
                }
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        assert "..." in text_str  # Should have truncation
        assert len([c for c in text_str if c == "A"]) < 250  # Not all 250 A's should be there

    def test_format_span_with_verbose_events(self):
        """Test formatting span with events."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="EventSpan",
            duration_ms=100.0,
            attributes={"gen_ai.request.model": "test-model"},
        )

        messages_by_span = {
            "span-1": [
                {
                    "type": "event",
                    "event_name": "model.start",
                    "payload": {"model": "claude-3", "temperature": 0.7},
                    "timestamp": "2025-10-28T10:00:00Z",
                }
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        assert "Event: model.start" in text_str
        assert "model=claude-3" in text_str

    def test_format_span_with_mixed_data_types(self):
        """Test formatting span with exceptions, messages, and events mixed."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="MixedSpan",
            duration_ms=100.0,
            status_code="ERROR",
            attributes={"gen_ai.request.model": "test-model"},
        )

        messages_by_span = {
            "span-1": [
                {
                    "type": "exception",
                    "exception_type": "ValueError",
                    "message": "Error occurred",
                    "stacktrace": "Stack trace here",
                    "timestamp": "2025-10-28T10:00:00Z",
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": "Test message",
                    "timestamp": "2025-10-28T10:00:01Z",
                },
                {
                    "type": "event",
                    "event_name": "test.event",
                    "payload": {"key": "value"},
                    "timestamp": "2025-10-28T10:00:02Z",
                },
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        # Should show all three types
        assert "ValueError" in text_str  # Exception
        assert "Test message" in text_str  # Message
        assert "Event: test.event" in text_str  # Event
        # Should have label showing counts
        assert "1 exception" in text_str
        assert "1 msg" in text_str
        assert "1 event" in text_str

    def test_format_span_with_no_exception_message(self):
        """Test formatting exception with missing message field."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="ErrorSpan",
            duration_ms=100.0,
            status_code="ERROR",
            attributes={"gen_ai.request.model": "test-model"},
        )

        messages_by_span = {
            "span-1": [
                {
                    "type": "exception",
                    "exception_type": "Exception",
                    # No message field
                    "timestamp": "2025-10-28T10:00:00Z",
                }
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        assert "Exception" in text_str

    def test_format_span_with_event_empty_payload(self):
        """Test formatting event with empty payload."""
        visualizer = TraceVisualizer()
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="EventSpan",
            duration_ms=100.0,
            attributes={"gen_ai.request.model": "test-model"},
        )

        messages_by_span = {
            "span-1": [
                {
                    "type": "event",
                    "event_name": "empty.event",
                    "payload": {},
                    "timestamp": "2025-10-28T10:00:00Z",
                }
            ]
        }

        text = visualizer._format_span(span, verbose=True, messages_by_span=messages_by_span, seen_messages=set())

        text_str = text.plain
        assert "Event: empty.event" in text_str
        # Should show (empty) for empty payload or not show payload details
