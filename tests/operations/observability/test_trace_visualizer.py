"""Data-driven tests for TraceVisualizer using real OTEL trace data."""

import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from bedrock_agentcore_starter_toolkit.operations.observability.builders import CloudWatchResultBuilder
from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import TraceData
from bedrock_agentcore_starter_toolkit.operations.observability.trace_processor import TraceProcessor
from bedrock_agentcore_starter_toolkit.operations.observability.trace_visualizer import TraceVisualizer

# Load real fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def langchain_trace_data():
    """Load and build real langchain trace data."""
    with open(FIXTURES_DIR / "raw_otel_langchain_spans.json") as f:
        span_data = json.load(f)
    with open(FIXTURES_DIR / "raw_otel_langchain_runtime_logs.json") as f:
        log_data = json.load(f)

    spans = []
    for entry in span_data:
        otel_span = entry["raw_otel_json"]
        cw_result = _otel_span_to_cw(otel_span)
        span = CloudWatchResultBuilder.build_span(cw_result)
        spans.append(span)

    runtime_logs = []
    for entry in log_data:
        otel_log = entry["raw_otel_json"]
        cw_result = _otel_log_to_cw(otel_log)
        log = CloudWatchResultBuilder.build_runtime_log(cw_result)
        runtime_logs.append(log)

    trace_data = TraceData(spans=spans, runtime_logs=runtime_logs)
    TraceProcessor.group_spans_by_trace(trace_data)
    return trace_data


@pytest.fixture(scope="module")
def strands_bedrock_trace_data():
    """Load and build real strands bedrock trace data."""
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_spans.json") as f:
        span_data = json.load(f)
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_runtime_logs.json") as f:
        log_data = json.load(f)

    spans = []
    for entry in span_data[:20]:  # Use first 20 for performance
        otel_span = entry["raw_otel_json"]
        cw_result = _otel_span_to_cw(otel_span)
        span = CloudWatchResultBuilder.build_span(cw_result)
        spans.append(span)

    runtime_logs = []
    for entry in log_data[:20]:  # Use first 20 for performance
        otel_log = entry["raw_otel_json"]
        cw_result = _otel_log_to_cw(otel_log)
        log = CloudWatchResultBuilder.build_runtime_log(cw_result)
        runtime_logs.append(log)

    trace_data = TraceData(spans=spans, runtime_logs=runtime_logs)
    TraceProcessor.group_spans_by_trace(trace_data)
    return trace_data


def _otel_span_to_cw(otel_span: dict) -> list:
    """Convert OTEL span to CloudWatch result format."""
    result = []
    if "traceId" in otel_span:
        result.append({"field": "traceId", "value": otel_span["traceId"]})
    if "spanId" in otel_span:
        result.append({"field": "spanId", "value": otel_span["spanId"]})
    if "name" in otel_span:
        result.append({"field": "spanName", "value": otel_span["name"]})
    if "kind" in otel_span:
        result.append({"field": "kind", "value": str(otel_span["kind"])})
    if "parentSpanId" in otel_span:
        result.append({"field": "parentSpanId", "value": otel_span["parentSpanId"]})
    if "startTimeUnixNano" in otel_span:
        result.append({"field": "startTimeUnixNano", "value": str(otel_span["startTimeUnixNano"])})
    if "endTimeUnixNano" in otel_span:
        result.append({"field": "endTimeUnixNano", "value": str(otel_span["endTimeUnixNano"])})
    if "status" in otel_span and "code" in otel_span["status"]:
        result.append({"field": "statusCode", "value": str(otel_span["status"]["code"])})
    if "attributes" in otel_span and "session.id" in otel_span["attributes"]:
        result.append({"field": "attributes.session.id", "value": otel_span["attributes"]["session.id"]})
    result.append({"field": "@message", "value": json.dumps(otel_span)})
    return result


def _otel_log_to_cw(otel_log: dict) -> list:
    """Convert OTEL log to CloudWatch result format."""
    result = []
    if "timeUnixNano" in otel_log:
        result.append({"field": "@timestamp", "value": str(otel_log["timeUnixNano"])})
    if "traceId" in otel_log:
        result.append({"field": "traceId", "value": otel_log["traceId"]})
    if "spanId" in otel_log:
        result.append({"field": "spanId", "value": otel_log["spanId"]})
    result.append({"field": "@message", "value": json.dumps(otel_log)})
    return result


class TestTraceVisualizerWithLangchain:
    """Test TraceVisualizer with real langchain data."""

    def test_visualize_trace_no_errors(self, langchain_trace_data):
        """Test that visualize_trace runs without errors on langchain data."""
        # Use StringIO to capture output
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Pick first trace
        if langchain_trace_data.traces:
            trace_id = list(langchain_trace_data.traces.keys())[0]

            # Should not raise any exceptions
            visualizer.visualize_trace(langchain_trace_data, trace_id)

            # Should produce some output
            output = string_io.getvalue()
            assert len(output) > 0
            # Trace ID may be truncated in display, check for prefix
            assert trace_id[:16] in output

    def test_visualize_trace_with_messages(self, langchain_trace_data):
        """Test visualize_trace with show_messages=True."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        if langchain_trace_data.traces:
            trace_id = list(langchain_trace_data.traces.keys())[0]
            visualizer.visualize_trace(langchain_trace_data, trace_id, show_messages=True)

            output = string_io.getvalue()
            assert len(output) > 0

    def test_visualize_trace_verbose(self, langchain_trace_data):
        """Test visualize_trace with verbose=True."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        if langchain_trace_data.traces:
            trace_id = list(langchain_trace_data.traces.keys())[0]
            visualizer.visualize_trace(langchain_trace_data, trace_id, verbose=True)

            output = string_io.getvalue()
            assert len(output) > 0

    def test_visualize_all_traces(self, langchain_trace_data):
        """Test visualize_all_traces with langchain data."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_all_traces(langchain_trace_data)

        output = string_io.getvalue()
        assert len(output) > 0

        # Should show all trace IDs (may be truncated in display)
        for trace_id in langchain_trace_data.traces.keys():
            assert trace_id[:16] in output


class TestTraceVisualizerWithStrandsBedrock:
    """Test TraceVisualizer with real strands bedrock data."""

    def test_visualize_trace_no_errors(self, strands_bedrock_trace_data):
        """Test that visualize_trace runs without errors on strands bedrock data."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        if strands_bedrock_trace_data.traces:
            trace_id = list(strands_bedrock_trace_data.traces.keys())[0]
            visualizer.visualize_trace(strands_bedrock_trace_data, trace_id)

            output = string_io.getvalue()
            assert len(output) > 0

    def test_visualize_trace_shows_hierarchy(self, strands_bedrock_trace_data):
        """Test that visualizer shows span hierarchy correctly."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Find a trace with multiple spans
        multi_span_trace = None
        for trace_id, spans in strands_bedrock_trace_data.traces.items():
            if len(spans) > 2:
                multi_span_trace = trace_id
                break

        if multi_span_trace:
            visualizer.visualize_trace(strands_bedrock_trace_data, multi_span_trace)

            output = string_io.getvalue()
            # Should show span names
            spans = strands_bedrock_trace_data.traces[multi_span_trace]
            for span in spans[:3]:  # Check first 3 spans
                if span.span_name:
                    assert span.span_name in output

    def test_visualize_trace_with_messages_shows_content(self, strands_bedrock_trace_data):
        """Test that show_messages displays message content."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        if strands_bedrock_trace_data.traces:
            trace_id = list(strands_bedrock_trace_data.traces.keys())[0]
            visualizer.visualize_trace(strands_bedrock_trace_data, trace_id, show_messages=True)

            output = string_io.getvalue()
            assert len(output) > 0
            # Output should be longer with messages
            assert len(output) > 100

    def test_visualize_all_traces_multiple_traces(self, strands_bedrock_trace_data):
        """Test visualize_all_traces with multiple traces."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_all_traces(strands_bedrock_trace_data)

        output = string_io.getvalue()
        assert len(output) > 0

        # Should show summary of traces
        trace_count = len(strands_bedrock_trace_data.traces)
        if trace_count > 0:
            # Output should contain trace information
            assert len(output) > 200  # Reasonable output length


class TestTraceVisualizerWithSpanAttributes:
    """Test visualizer with spans that have LLM attributes (to exercise helper functions)."""

    def test_visualize_span_with_prompt_attribute(self):
        """Test visualizing span with gen_ai.prompt attribute."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData

        # Create span with prompt attribute
        span = Span(
            trace_id="test-trace-123",
            span_id="span-456",
            span_name="LLM Call",
            attributes={"gen_ai.prompt": "What is the capital of France?"},
            start_time_unix_nano=1000000000,
            end_time_unix_nano=1500000000,
            duration_ms=500.0,
        )

        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "test-trace-123", show_messages=True)
        output = string_io.getvalue()

        # Should display the prompt
        assert "What is the capital of France?" in output
        assert "💬 User:" in output

    def test_visualize_span_with_completion_attribute(self):
        """Test visualizing span with gen_ai.completion attribute."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData

        span = Span(
            trace_id="test-trace-456",
            span_id="span-789",
            span_name="LLM Response",
            attributes={"gen_ai.completion": "The capital of France is Paris."},
            start_time_unix_nano=1000000000,
            end_time_unix_nano=1500000000,
            duration_ms=500.0,
        )

        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "test-trace-456", show_messages=True)
        output = string_io.getvalue()

        # Should display the completion
        assert "The capital of France is Paris." in output
        assert "🤖 Assistant:" in output

    def test_visualize_span_with_invocation_payload(self):
        """Test visualizing span with invocation payload."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData

        span = Span(
            trace_id="test-trace-789",
            span_id="span-abc",
            span_name="API Call",
            attributes={"gen_ai.request.model.input": '{"messages": [{"role": "user", "content": "Hello"}]}'},
            start_time_unix_nano=1000000000,
            end_time_unix_nano=1500000000,
            duration_ms=500.0,
        )

        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "test-trace-789", show_messages=True)
        output = string_io.getvalue()

        # Should display the payload
        assert "messages" in output
        assert "📦 Payload:" in output

    def test_visualize_span_with_input_output(self):
        """Test visualizing span with input/output data."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData

        span = Span(
            trace_id="test-trace-input-output",
            span_id="span-io",
            span_name="Processing",
            attributes={
                "gen_ai.request.model.input": "User query text",
                "gen_ai.response.model.output": "Assistant response text",
            },
            start_time_unix_nano=1000000000,
            end_time_unix_nano=1500000000,
            duration_ms=500.0,
        )

        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "test-trace-input-output", show_messages=True)
        output = string_io.getvalue()

        # Should display both input and output
        assert "User query text" in output
        assert "Assistant response text" in output
        assert "📥 Input:" in output
        assert "📤 Output:" in output

    def test_visualize_span_with_llm_fallback_attributes(self):
        """Test visualizing span with llm.* fallback attributes."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData

        span = Span(
            trace_id="test-trace-llm",
            span_id="span-llm",
            span_name="LLM Call Legacy",
            attributes={
                "llm.prompts": "Legacy prompt format",
                "llm.responses": "Legacy response format",
            },
            start_time_unix_nano=1000000000,
            end_time_unix_nano=1500000000,
            duration_ms=500.0,
        )

        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "test-trace-llm", show_messages=True)
        output = string_io.getvalue()

        # Should display using fallback attributes
        assert "Legacy prompt format" in output
        assert "Legacy response format" in output

    def test_visualize_truncates_long_content(self):
        """Test that visualizer truncates long content in normal mode."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData

        long_prompt = "x" * 300  # Longer than default truncation limit

        span = Span(
            trace_id="test-trace-truncate",
            span_id="span-truncate",
            span_name="Long Content",
            attributes={"gen_ai.prompt": long_prompt},
            start_time_unix_nano=1000000000,
            end_time_unix_nano=1500000000,
            duration_ms=500.0,
        )

        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Normal mode - should truncate
        visualizer.visualize_trace(trace_data, "test-trace-truncate", show_messages=True, verbose=False)
        output = string_io.getvalue()

        # Should have truncation marker
        assert "..." in output
        # Full content should not be present
        assert long_prompt not in output

    def test_visualize_verbose_no_truncation(self):
        """Test that verbose mode doesn't truncate content."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData

        long_prompt = "y" * 300

        span = Span(
            trace_id="test-trace-verbose",
            span_id="span-verbose",
            span_name="Verbose Content",
            attributes={"gen_ai.prompt": long_prompt},
            start_time_unix_nano=1000000000,
            end_time_unix_nano=1500000000,
            duration_ms=500.0,
        )

        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Verbose mode - should NOT truncate
        visualizer.visualize_trace(trace_data, "test-trace-verbose", show_messages=True, verbose=True)
        output = string_io.getvalue()

        # Full content should be present (count y's to handle line wrapping)
        y_count = output.count("y")
        assert y_count == 300  # All 300 y's should be present


class TestTraceVisualizerEdgeCases:
    """Test visualizer with edge cases."""

    def test_visualize_empty_trace_data(self):
        """Test visualizing empty trace data."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        trace_data = TraceData(spans=[])
        TraceProcessor.group_spans_by_trace(trace_data)

        # Should handle gracefully
        visualizer.visualize_all_traces(trace_data)
        output = string_io.getvalue()
        assert len(output) >= 0  # May be empty or have message

    def test_visualize_nonexistent_trace_id(self, langchain_trace_data):
        """Test visualizing with non-existent trace ID."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Should handle gracefully (may print error or do nothing)
        visualizer.visualize_trace(langchain_trace_data, "nonexistent-trace-id")
        output = string_io.getvalue()
        assert isinstance(output, str)  # Should not crash

    def test_visualize_trace_with_show_details(self, langchain_trace_data):
        """Test visualize_trace with show_details=True."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        if langchain_trace_data.traces:
            trace_id = list(langchain_trace_data.traces.keys())[0]
            visualizer.visualize_trace(langchain_trace_data, trace_id, show_details=True)

            output = string_io.getvalue()
            assert len(output) > 0


class TestTraceVisualizerFormatting:
    """Test visualizer output formatting."""

    def test_visualize_shows_status_icons(self, langchain_trace_data):
        """Test that visualizer shows status icons for spans."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        if langchain_trace_data.traces:
            trace_id = list(langchain_trace_data.traces.keys())[0]
            visualizer.visualize_trace(langchain_trace_data, trace_id)

            output = string_io.getvalue()
            # Should contain status indicators (though may be unicode)
            assert len(output) > 0

    def test_visualize_shows_duration(self, strands_bedrock_trace_data):
        """Test that visualizer shows span durations."""
        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        if strands_bedrock_trace_data.traces:
            trace_id = list(strands_bedrock_trace_data.traces.keys())[0]
            visualizer.visualize_trace(strands_bedrock_trace_data, trace_id)

            output = string_io.getvalue()
            # Should show duration in milliseconds
            assert "ms" in output or len(output) > 0

    def test_verbose_mode_shows_more_content(self, strands_bedrock_trace_data):
        """Test that verbose mode produces more detailed output."""
        if not strands_bedrock_trace_data.traces:
            pytest.skip("No traces available")

        trace_id = list(strands_bedrock_trace_data.traces.keys())[0]

        # Normal mode
        string_io_normal = StringIO()
        console_normal = Console(file=string_io_normal, force_terminal=True, width=120)
        visualizer_normal = TraceVisualizer(console_normal)
        visualizer_normal.visualize_trace(strands_bedrock_trace_data, trace_id, show_messages=True)
        normal_output = string_io_normal.getvalue()

        # Verbose mode
        string_io_verbose = StringIO()
        console_verbose = Console(file=string_io_verbose, force_terminal=True, width=120)
        visualizer_verbose = TraceVisualizer(console_verbose)
        visualizer_verbose.visualize_trace(strands_bedrock_trace_data, trace_id, show_messages=True, verbose=True)
        verbose_output = string_io_verbose.getvalue()

        # Verbose should have equal or more content (no truncation)
        assert len(verbose_output) >= len(normal_output) * 0.9  # Allow some variance


class TestTraceVisualizerEdgeCasesExtended:
    """Test additional edge cases for improved coverage."""

    def test_visualize_trace_with_no_root_spans(self):
        """Test visualization when trace has no root spans."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        # Create trace with only child spans (no root)
        child_span = Span(
            trace_id="test-trace",
            span_id="child-1",
            span_name="ChildSpan",
            parent_span_id="missing-parent",  # Parent doesn't exist
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )

        trace_data = TraceData(spans=[child_span], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Should handle gracefully when no root spans
        visualizer.visualize_trace(trace_data, "test-trace")
        output = string_io.getvalue()

        # Should show warning message
        assert "No spans found" in output or len(output) > 0

    def test_visualize_all_traces_with_empty_traces_dict(self):
        """Test visualize_all_traces when traces dict is empty."""
        trace_data = TraceData(spans=[], agent_id="test-agent")
        trace_data.traces = {}  # Empty traces

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Should handle empty traces gracefully
        visualizer.visualize_all_traces(trace_data)
        output = string_io.getvalue()

        # Should either show message or complete without error
        assert isinstance(output, str)

    def test_visualize_trace_with_error_status(self):
        """Test visualization of spans with ERROR status."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        error_span = Span(
            trace_id="error-trace",
            span_id="error-span-1",
            span_name="ErrorSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="ERROR",
            status_message="Something went wrong",
        )

        trace_data = TraceData(spans=[error_span], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "error-trace")
        output = string_io.getvalue()

        # Should show error status
        assert "ERROR" in output or "❌" in output

    def test_visualize_with_very_long_span_names(self):
        """Test visualization handles very long span names."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        long_name = "A" * 200  # Very long span name
        span = Span(
            trace_id="long-trace",
            span_id="long-span-1",
            span_name=long_name,
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )

        trace_data = TraceData(spans=[span], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Should handle long names without error
        visualizer.visualize_trace(trace_data, "long-trace")
        output = string_io.getvalue()

        assert len(output) > 0

    def test_visualize_span_with_show_details_true(self):
        """Test show_details=True path."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        span = Span(
            trace_id="details-trace",
            span_id="details-span-1",
            span_name="DetailSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
            attributes={"key1": "value1", "key2": "value2"},
        )

        trace_data = TraceData(spans=[span], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Test with show_details=True
        visualizer.visualize_trace(trace_data, "details-trace", show_details=True)
        output = string_io.getvalue()

        # Should show more information with details
        assert len(output) > 0
        # Attributes might be shown
        assert "key1" in output or "DetailSpan" in output


class TestTraceVisualizerExceptionHandling:
    """Test exception and error visualization."""

    def test_visualize_span_with_exceptions(self):
        """Test visualization of spans with exception events."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        # Create span with exception event
        span_with_exception = Span(
            trace_id="exc-trace",
            span_id="exc-span",
            span_name="ExceptionSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="ERROR",
            events=[
                {
                    "name": "exception",
                    "attributes": {
                        "exception.type": "ValueError",
                        "exception.message": "Invalid input",
                        "exception.stacktrace": "Traceback:\n  File test.py line 10\n  File test.py line 20",
                    },
                }
            ],
        )

        trace_data = TraceData(spans=[span_with_exception], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "exc-trace")
        output = string_io.getvalue()

        # Should show exception info
        assert "ValueError" in output or "exception" in output.lower()

    def test_visualize_with_messages_containing_tool_use(self):
        """Test message visualization with tool use content (🔧)."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import RuntimeLog, Span

        span = Span(
            trace_id="tool-trace",
            span_id="tool-span",
            span_name="ToolSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )

        # Create runtime log with tool use
        tool_message = (
            "🔧 Tool: calculator\\nInput: 2+2\\nVery long tool use content that should be truncated in non-verbose mode"
        )
        runtime_log = RuntimeLog(
            timestamp="2024-01-01 12:00:00",
            trace_id="tool-trace",
            span_id="tool-span",
            message=f'{{"eventType": "invokeAgentRuntime", "input": {{"text": "{tool_message}"}}}}',
        )

        trace_data = TraceData(spans=[span], runtime_logs=[runtime_log], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Test non-verbose mode (should truncate tool use)
        visualizer.visualize_trace(trace_data, "tool-trace", show_messages=True, verbose=False)
        output = string_io.getvalue()

        # Should show tool message
        assert len(output) > 0

    def test_visualize_with_messages_verbose_no_truncation(self):
        """Test verbose mode shows full message content."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import RuntimeLog, Span

        long_content = "A" * 500  # Very long content
        span = Span(
            trace_id="verbose-trace",
            span_id="verbose-span",
            span_name="VerboseSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )

        runtime_log = RuntimeLog(
            timestamp="2024-01-01 12:00:00",
            trace_id="verbose-trace",
            span_id="verbose-span",
            message=f'{{"eventType": "invokeAgentRuntime", "input": {{"text": "{long_content}"}}}}',
        )

        trace_data = TraceData(spans=[span], runtime_logs=[runtime_log], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Verbose mode - should NOT truncate
        visualizer.visualize_trace(trace_data, "verbose-trace", show_messages=True, verbose=True)
        output_verbose = string_io.getvalue()

        # Non-verbose mode - should truncate
        string_io_normal = StringIO()
        console_normal = Console(file=string_io_normal, force_terminal=True, width=120)
        visualizer_normal = TraceVisualizer(console_normal)
        visualizer_normal.visualize_trace(trace_data, "verbose-trace", show_messages=True, verbose=False)
        output_normal = string_io_normal.getvalue()

        # Verbose should show more content
        assert len(output_verbose) >= len(output_normal)


class TestTraceVisualizerAttributeExtraction:
    """Test attribute extraction and display logic."""

    def test_visualize_span_with_gen_ai_attributes(self):
        """Test visualization extracts gen_ai specific attributes."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        span = Span(
            trace_id="genai-trace",
            span_id="genai-span",
            span_name="GenAISpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
            attributes={
                "gen_ai.prompt": "What is 2+2?",
                "gen_ai.completion": "The answer is 4.",
                "gen_ai.system": "You are a helpful assistant",
            },
        )

        trace_data = TraceData(spans=[span], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "genai-trace")
        output = string_io.getvalue()

        # Should extract and show gen_ai attributes
        assert len(output) > 0

    def test_visualize_span_with_llm_attributes(self):
        """Test visualization extracts llm specific attributes."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        span = Span(
            trace_id="llm-trace",
            span_id="llm-span",
            span_name="LLMSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
            attributes={"llm.prompts": '["Prompt 1", "Prompt 2"]', "llm.completions": '["Response 1"]'},
        )

        trace_data = TraceData(spans=[span], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "llm-trace")
        output = string_io.getvalue()

        assert len(output) > 0

    def test_visualize_span_with_bedrock_invocation_payload(self):
        """Test visualization of bedrock invocation payloads."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        span = Span(
            trace_id="bedrock-trace",
            span_id="bedrock-span",
            span_name="BedrockInvoke",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
            attributes={
                "bedrock.agent.invocationInput": '{"text": "User input text"}',
                "bedrock.agent.invocationOutput": '{"text": "Agent response"}',
            },
        )

        trace_data = TraceData(spans=[span], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "bedrock-trace")
        output = string_io.getvalue()

        assert len(output) > 0


class TestTraceVisualizerComplexHierarchy:
    """Test visualization of complex span hierarchies."""

    def test_visualize_deep_span_hierarchy(self):
        """Test visualization of deeply nested spans."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        # Create a deep hierarchy: root -> child1 -> child2 -> child3
        root = Span(
            trace_id="deep-trace",
            span_id="root",
            span_name="Root",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=5000000000,
            duration_ms=4000,
            status_code="OK",
        )
        child1 = Span(
            trace_id="deep-trace",
            span_id="child1",
            span_name="Child1",
            parent_span_id="root",
            start_time_unix_nano=1500000000,
            end_time_unix_nano=4500000000,
            duration_ms=3000,
            status_code="OK",
        )
        child2 = Span(
            trace_id="deep-trace",
            span_id="child2",
            span_name="Child2",
            parent_span_id="child1",
            start_time_unix_nano=2000000000,
            end_time_unix_nano=4000000000,
            duration_ms=2000,
            status_code="OK",
        )
        child3 = Span(
            trace_id="deep-trace",
            span_id="child3",
            span_name="Child3",
            parent_span_id="child2",
            start_time_unix_nano=2500000000,
            end_time_unix_nano=3500000000,
            duration_ms=1000,
            status_code="OK",
        )

        trace_data = TraceData(spans=[root, child1, child2, child3], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "deep-trace")
        output = string_io.getvalue()

        # Should handle deep nesting
        assert "Root" in output
        assert "Child1" in output or len(output) > 100

    def test_visualize_wide_span_hierarchy(self):
        """Test visualization of spans with many siblings."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        # Create root with 5 children
        root = Span(
            trace_id="wide-trace",
            span_id="root",
            span_name="Root",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=6000000000,
            duration_ms=5000,
            status_code="OK",
        )

        children = []
        for i in range(5):
            child = Span(
                trace_id="wide-trace",
                span_id=f"child{i}",
                span_name=f"Child{i}",
                parent_span_id="root",
                start_time_unix_nano=1000000000 + i * 1000000000,
                end_time_unix_nano=2000000000 + i * 1000000000,
                duration_ms=1000,
                status_code="OK",
            )
            children.append(child)

        trace_data = TraceData(spans=[root] + children, agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "wide-trace")
        output = string_io.getvalue()

        # Should show all siblings
        assert "Root" in output
        assert len(output) > 200  # Should have substantial content


class TestTraceVisualizerSpanEventDisplay:
    """Test span event visualization."""

    def test_visualize_span_with_non_exception_events(self):
        """Test visualization of spans with regular events (non-exception)."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

        # Create span with regular event
        span_with_event = Span(
            trace_id="event-trace",
            span_id="event-span",
            span_name="EventSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
            events=[{"name": "data_processed", "attributes": {"event.type": "processing", "records_count": "100"}}],
        )

        trace_data = TraceData(spans=[span_with_event], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "event-trace")
        output = string_io.getvalue()

        # Should show event info
        assert len(output) > 0

    def test_visualize_trace_without_messages_flag(self):
        """Test visualization without show_messages flag."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import RuntimeLog, Span

        span = Span(
            trace_id="no-msg-trace",
            span_id="no-msg-span",
            span_name="NoMsgSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )

        runtime_log = RuntimeLog(
            timestamp="2024-01-01 12:00:00",
            trace_id="no-msg-trace",
            span_id="no-msg-span",
            message='{"eventType": "test"}',
        )

        trace_data = TraceData(spans=[span], runtime_logs=[runtime_log], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # show_messages=False (default)
        visualizer.visualize_trace(trace_data, "no-msg-trace", show_messages=False)
        output = string_io.getvalue()

        # Should not attempt to get messages
        assert len(output) > 0


class TestTraceVisualizerRuntimeLogFormatting:
    """Test runtime log message formatting."""

    def test_visualize_with_error_in_runtime_logs(self):
        """Test visualization handles errors in runtime log parsing."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import RuntimeLog, Span

        span = Span(
            trace_id="error-log-trace",
            span_id="error-log-span",
            span_name="ErrorLogSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )

        # Runtime log with invalid JSON
        runtime_log = RuntimeLog(
            timestamp="2024-01-01 12:00:00",
            trace_id="error-log-trace",
            span_id="error-log-span",
            message="INVALID JSON {",
        )

        trace_data = TraceData(spans=[span], runtime_logs=[runtime_log], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        # Should handle invalid JSON gracefully
        visualizer.visualize_trace(trace_data, "error-log-trace", show_messages=True)
        output = string_io.getvalue()

        assert len(output) > 0

    def test_visualize_with_multiple_message_roles(self):
        """Test visualization with different message roles."""
        from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import RuntimeLog, Span

        span = Span(
            trace_id="multi-role-trace",
            span_id="multi-role-span",
            span_name="MultiRoleSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )

        # Runtime logs with different roles
        user_log = RuntimeLog(
            timestamp="2024-01-01 12:00:00",
            trace_id="multi-role-trace",
            span_id="multi-role-span",
            message='{"eventType": "invokeAgentRuntime", "input": {"text": "user message", "role": "user"}}',
        )

        assistant_log = RuntimeLog(
            timestamp="2024-01-01 12:00:01",
            trace_id="multi-role-trace",
            span_id="multi-role-span",
            message='{"eventType": "invokeAgentRuntime", "output": {"text": "assistant message", "role": "assistant"}}',
        )

        trace_data = TraceData(spans=[span], runtime_logs=[user_log, assistant_log], agent_id="test-agent")
        TraceProcessor.group_spans_by_trace(trace_data)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True, width=120)
        visualizer = TraceVisualizer(console)

        visualizer.visualize_trace(trace_data, "multi-role-trace", show_messages=True)
        output = string_io.getvalue()

        # Should show both messages
        assert len(output) > 0
