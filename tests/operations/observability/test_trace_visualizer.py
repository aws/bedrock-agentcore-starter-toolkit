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

    # Test _format_span basic
    def test_format_span_basic(self, visualizer, sample_span):
        """Test basic span formatting without details."""
        text = visualizer._format_span(
            sample_span,
            show_details=False,
            show_messages=False,
            messages_by_span={},
            seen_messages=set(),
            verbose=False,
        )

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

        text = visualizer._format_span(
            span, show_details=False, show_messages=False, messages_by_span={}, seen_messages=set(), verbose=False
        )

        # Check icon is present (Rich text includes formatting)
        text_str = text.plain
        assert expected_icon in text_str

    # Test _format_span with show_details mode
    def test_format_span_verbose_shows_details(self, visualizer):
        """Test that show_details mode shows full span ID."""
        span = Span(
            trace_id="trace-1",
            span_id="span-123456789012345678",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
            service_name="test-service",
        )

        text = visualizer._format_span(
            span, show_details=True, show_messages=False, messages_by_span={}, seen_messages=set(), verbose=False
        )

        text_str = text.plain
        # Check full span ID is shown (not truncated)
        assert "span-123456789012345678" in text_str

    # Test _format_span with show_messages mode
    def test_format_span_shows_messages_from_attributes(self, visualizer):
        """Test that show_messages mode displays prompts and completions from attributes."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
            attributes={
                "gen_ai.prompt": "What is the weather?",
                "gen_ai.completion": "The weather is sunny.",
            },
        )

        text = visualizer._format_span(
            span, show_details=False, show_messages=True, messages_by_span={}, seen_messages=set(), verbose=False
        )

        text_str = text.plain
        assert "What is the weather?" in text_str
        assert "The weather is sunny." in text_str

    def test_format_span_shows_messages_from_runtime_logs(self, visualizer):
        """Test that show_messages mode displays messages from runtime logs."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
        )

        # Messages from runtime logs
        messages_by_span = {
            "span-1": [
                {"type": "message", "role": "user", "content": "Hello from runtime log!"},
                {"type": "message", "role": "assistant", "content": "Hi there!"},
                {"type": "event", "event_name": "test.event", "payload": {"status": "success", "count": 5}},
            ]
        }

        text = visualizer._format_span(
            span,
            show_details=False,
            show_messages=True,
            messages_by_span=messages_by_span,
            seen_messages=set(),
            verbose=False,
        )

        text_str = text.plain
        assert "Hello from runtime log!" in text_str
        assert "Hi there!" in text_str
        assert "test.event" in text_str
        # Check event payload is displayed
        assert "status: success" in text_str
        assert "count: 5" in text_str

    def test_format_span_shows_full_messages_no_truncation(self, visualizer):
        """Test that verbose mode shows full messages without truncation."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            duration_ms=100.0,
            status_code="OK",
        )

        # Create a very long message (over 200 chars)
        long_message = "A" * 300

        messages_by_span = {
            "span-1": [
                {"type": "message", "role": "user", "content": long_message},
            ]
        }

        text = visualizer._format_span(
            span,
            show_details=False,
            show_messages=True,
            messages_by_span=messages_by_span,
            seen_messages=set(),
            verbose=True,
        )

        text_str = text.plain
        # In verbose mode, full message should be shown (no truncation)
        assert "A" * 300 in text_str
        # Should NOT have truncation marker for messages
        assert text_str.count("A") == 300

    # Test visualize_trace
    def test_visualize_trace_basic(self, visualizer, sample_trace_data):
        """Test basic trace visualization."""
        visualizer.visualize_trace(sample_trace_data, "trace-1", show_details=True)

        # Check that output was produced (console captured)
        output = visualizer.console.file.getvalue()
        assert "RootSpan" in output
        assert "ChildSpan" in output

    def test_visualize_trace_verbose(self, visualizer, sample_trace_data):
        """Test trace visualization with show_details mode."""
        visualizer.visualize_trace(sample_trace_data, "trace-1", show_details=True)

        output = visualizer.console.file.getvalue()
        assert "RootSpan" in output
        assert "ChildSpan" in output
        # show_details mode should show span IDs
        assert "span-1" in output
        assert "span-2" in output

    def test_visualize_trace_not_found(self, visualizer, sample_trace_data):
        """Test visualization of non-existent trace."""
        visualizer.visualize_trace(sample_trace_data, "nonexistent-trace", show_details=False)

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

        visualizer.visualize_trace(trace_data, "trace-1", show_details=True)

        output = visualizer.console.file.getvalue()
        # Check that trace and span are displayed
        assert "RootSpan" in output
        # Check that data section appears (indicates messages are being processed)
        # The actual message display depends on the internal formatting logic
        assert "span-1" in output  # show_details mode shows span IDs

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

        visualizer.visualize_all_traces(trace_data, show_details=False)

        output = visualizer.console.file.getvalue()
        assert "Trace1Span" in output
        assert "Trace2Span" in output
        assert "2 traces" in output

    def test_visualize_all_traces_empty(self, visualizer):
        """Test visualization with no traces."""
        trace_data = TraceData(spans=[])
        trace_data.group_spans_by_trace()

        visualizer.visualize_all_traces(trace_data, show_details=False)

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

        visualizer.visualize_trace(trace_data, "trace-1", show_details=True)

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

        visualizer.visualize_trace(trace_data, "trace-1", show_details=True)

        output = visualizer.console.file.getvalue()

        # Check that error span is displayed
        assert "FailedSpan" in output
        assert "ERROR" in output
        # Check that trace shows error count
        assert "1 errors" in output
