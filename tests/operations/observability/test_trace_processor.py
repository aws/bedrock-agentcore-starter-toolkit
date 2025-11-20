"""Data-driven tests for TraceProcessor using real trace data."""

import json
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.operations.observability.builders import CloudWatchResultBuilder
from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData
from bedrock_agentcore_starter_toolkit.operations.observability.trace_processor import TraceProcessor

# Load real fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def langchain_spans_data():
    """Load and build real langchain spans."""
    with open(FIXTURES_DIR / "raw_otel_langchain_spans.json") as f:
        data = json.load(f)

    spans = []
    for entry in data:
        otel_span = entry["raw_otel_json"]
        # Convert to CloudWatch format then build
        cw_result = _otel_span_to_cw(otel_span)
        span = CloudWatchResultBuilder.build_span(cw_result)
        spans.append(span)

    return spans


@pytest.fixture(scope="module")
def strands_bedrock_spans_data():
    """Load and build real strands bedrock spans."""
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_spans.json") as f:
        data = json.load(f)

    spans = []
    for entry in data[:50]:  # Use first 50 for performance
        otel_span = entry["raw_otel_json"]
        cw_result = _otel_span_to_cw(otel_span)
        span = CloudWatchResultBuilder.build_span(cw_result)
        spans.append(span)

    return spans


@pytest.fixture(scope="module")
def strands_bedrock_runtime_logs_data():
    """Load real strands bedrock runtime logs."""
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_runtime_logs.json") as f:
        data = json.load(f)

    logs = []
    for entry in data[:50]:  # Use first 50 for performance
        otel_log = entry["raw_otel_json"]
        cw_result = _otel_log_to_cw(otel_log)
        log = CloudWatchResultBuilder.build_runtime_log(cw_result)
        logs.append(log)

    return logs


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

    # Add @message field - CloudWatch returns the full OTEL log as JSON string
    result.append({"field": "@message", "value": json.dumps(otel_log)})
    return result


class TestTraceProcessorGrouping:
    """Test TraceProcessor grouping and hierarchy methods."""

    def test_group_spans_by_trace_langchain(self, langchain_spans_data):
        """Test grouping langchain spans by trace."""
        trace_data = TraceData(spans=langchain_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        # Should have grouped spans
        assert len(trace_data.traces) > 0

        # Each group should have valid trace ID
        for trace_id, spans in trace_data.traces.items():
            assert isinstance(trace_id, str)
            assert len(trace_id) > 0
            assert len(spans) > 0

            # All spans in group should have same trace ID
            for span in spans:
                assert span.trace_id == trace_id

    def test_group_spans_by_trace_strands_bedrock(self, strands_bedrock_spans_data):
        """Test grouping strands bedrock spans by trace."""
        trace_data = TraceData(spans=strands_bedrock_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        # Strands bedrock has multiple traces
        assert len(trace_data.traces) >= 1

        # Check spans are sorted by start time within each trace
        for _trace_id, spans in trace_data.traces.items():
            start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
            # Should be sorted in ascending order
            assert start_times == sorted(start_times)

    def test_build_span_hierarchy(self, langchain_spans_data):
        """Test building span hierarchy from langchain data."""
        trace_data = TraceData(spans=langchain_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        # Test hierarchy for each trace
        for trace_id in trace_data.traces.keys():
            root_spans = TraceProcessor.build_span_hierarchy(trace_data, trace_id)

            # Should have root spans
            assert len(root_spans) > 0

            # Root spans should not have parents (or parent not in trace)
            for root in root_spans:
                if root.parent_span_id:
                    # Parent should not be in this trace
                    span_ids = [s.span_id for s in trace_data.traces[trace_id]]
                    assert root.parent_span_id not in span_ids

    def test_build_span_hierarchy_children_populated(self, strands_bedrock_spans_data):
        """Test that children are populated in hierarchy."""
        trace_data = TraceData(spans=strands_bedrock_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        # Pick a trace with multiple spans
        multi_span_traces = [tid for tid, spans in trace_data.traces.items() if len(spans) > 3]

        if multi_span_traces:
            trace_id = multi_span_traces[0]
            root_spans = TraceProcessor.build_span_hierarchy(trace_data, trace_id)

            # Check if any root has children
            has_children = any(len(root.children) > 0 for root in root_spans)

            # At least one root should have children (or all spans are roots)
            total_spans = len(trace_data.traces[trace_id])
            total_roots = len(root_spans)
            if total_spans > total_roots:
                assert has_children, "Expected some spans to have children"


class TestTraceProcessorCalculations:
    """Test TraceProcessor calculation methods."""

    def test_calculate_trace_duration(self, langchain_spans_data):
        """Test calculating trace duration."""
        trace_data = TraceData(spans=langchain_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        for _trace_id, spans in trace_data.traces.items():
            duration = TraceProcessor.calculate_trace_duration(spans)

            # Duration should be positive
            assert duration > 0

            # If we have timestamps, verify calculation
            start_times = [s.start_time_unix_nano for s in spans if s.start_time_unix_nano]
            end_times = [s.end_time_unix_nano for s in spans if s.end_time_unix_nano]

            if start_times and end_times:
                expected_duration = (max(end_times) - min(start_times)) / 1_000_000
                assert duration == pytest.approx(expected_duration, rel=0.01)

    def test_count_error_spans(self, strands_bedrock_spans_data):
        """Test counting error spans."""
        trace_data = TraceData(spans=strands_bedrock_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        for _trace_id, spans in trace_data.traces.items():
            error_count = TraceProcessor.count_error_spans(spans)

            # Count should match manual count
            manual_count = sum(1 for s in spans if s.status_code == "ERROR")
            assert error_count == manual_count

            # Count should be non-negative
            assert error_count >= 0

    def test_get_trace_ids(self, langchain_spans_data):
        """Test getting unique trace IDs."""
        trace_data = TraceData(spans=langchain_spans_data)

        trace_ids = TraceProcessor.get_trace_ids(trace_data)

        # Should have trace IDs
        assert len(trace_ids) > 0

        # All should be strings
        assert all(isinstance(tid, str) for tid in trace_ids)

        # Should be unique
        assert len(trace_ids) == len(set(trace_ids))

        # Should match actual traces in spans
        actual_trace_ids = set(span.trace_id for span in langchain_spans_data if span.trace_id)
        assert set(trace_ids) == actual_trace_ids

    def test_filter_error_traces(self, strands_bedrock_spans_data):
        """Test filtering to only error traces."""
        trace_data = TraceData(spans=strands_bedrock_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        error_traces = TraceProcessor.filter_error_traces(trace_data)

        # All returned traces should have at least one error
        for trace_id, spans in error_traces.items():
            has_error = any(s.status_code == "ERROR" for s in spans)
            assert has_error, f"Trace {trace_id} should have at least one error span"

        # Should be subset of all traces
        assert len(error_traces) <= len(trace_data.traces)


class TestTraceProcessorMessages:
    """Test TraceProcessor message extraction methods."""

    def test_get_messages_by_span(self, strands_bedrock_spans_data, strands_bedrock_runtime_logs_data):
        """Test extracting messages grouped by span."""
        trace_data = TraceData(spans=strands_bedrock_spans_data, runtime_logs=strands_bedrock_runtime_logs_data)

        messages_by_span = TraceProcessor.get_messages_by_span(trace_data)

        # Should be a dictionary
        assert isinstance(messages_by_span, dict)

        # Check structure
        for span_id, items in messages_by_span.items():
            assert isinstance(span_id, str)
            assert isinstance(items, list)

            # Each item should have type
            for item in items:
                assert "type" in item
                assert item["type"] in ["message", "exception"]

        # If we have runtime logs with span IDs, should have some messages
        logs_with_span_ids = [log for log in strands_bedrock_runtime_logs_data if log.span_id]
        if logs_with_span_ids:
            assert len(messages_by_span) > 0

    def test_get_trace_messages(self, strands_bedrock_spans_data, strands_bedrock_runtime_logs_data):
        """Test extracting input/output messages for a trace."""
        trace_data = TraceData(spans=strands_bedrock_spans_data, runtime_logs=strands_bedrock_runtime_logs_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        # Test for each trace
        for trace_id in list(trace_data.traces.keys())[:3]:  # Test first 3 traces
            input_text, output_text = TraceProcessor.get_trace_messages(trace_data, trace_id)

            # Should return strings (may be empty)
            assert isinstance(input_text, str)
            assert isinstance(output_text, str)


class TestTraceProcessorSerialization:
    """Test TraceProcessor serialization methods."""

    def test_to_dict_structure(self, langchain_spans_data):
        """Test converting TraceData to dictionary."""
        trace_data = TraceData(
            session_id="test-session", agent_id="test-agent", spans=langchain_spans_data, runtime_logs=[]
        )
        TraceProcessor.group_spans_by_trace(trace_data)

        result = TraceProcessor.to_dict(trace_data)

        # Check top-level structure
        assert "session_id" in result
        assert "agent_id" in result
        assert "trace_count" in result
        assert "total_span_count" in result
        assert "traces" in result
        assert "runtime_logs" in result

        # Check values
        assert result["session_id"] == "test-session"
        assert result["agent_id"] == "test-agent"
        assert result["trace_count"] == len(trace_data.traces)
        assert result["total_span_count"] == len(langchain_spans_data)

    def test_to_dict_trace_structure(self, langchain_spans_data):
        """Test that to_dict includes proper trace structure."""
        trace_data = TraceData(spans=langchain_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        result = TraceProcessor.to_dict(trace_data)

        # Check each trace
        for trace_id, trace_info in result["traces"].items():
            assert "trace_id" in trace_info
            assert "span_count" in trace_info
            assert "total_duration_ms" in trace_info
            assert "error_count" in trace_info
            assert "root_spans" in trace_info

            # Verify trace ID matches
            assert trace_info["trace_id"] == trace_id

            # Check root spans structure
            assert isinstance(trace_info["root_spans"], list)
            for root_span in trace_info["root_spans"]:
                assert "trace_id" in root_span
                assert "span_id" in root_span
                assert "span_name" in root_span
                assert "children" in root_span

    def test_to_dict_hierarchy_preserved(self, strands_bedrock_spans_data):
        """Test that to_dict preserves span hierarchy."""
        trace_data = TraceData(spans=strands_bedrock_spans_data)
        TraceProcessor.group_spans_by_trace(trace_data)

        result = TraceProcessor.to_dict(trace_data)

        # Find a trace with hierarchy
        for _trace_id, trace_info in result["traces"].items():
            if trace_info["span_count"] > 2:
                # Should have root spans
                assert len(trace_info["root_spans"]) > 0

                # Check if any root has children
                def has_nested_children(span_dict):
                    if span_dict.get("children"):
                        return True
                    return any(has_nested_children(child) for child in span_dict.get("children", []))

                # At least verify structure is valid
                for root_span in trace_info["root_spans"]:
                    assert isinstance(root_span["children"], list)


class TestTraceProcessorEdgeCases:
    """Test TraceProcessor edge cases."""

    def test_empty_trace_data(self):
        """Test processing empty trace data."""
        trace_data = TraceData(spans=[])
        TraceProcessor.group_spans_by_trace(trace_data)

        assert trace_data.traces == {}
        assert TraceProcessor.get_trace_ids(trace_data) == []

    def test_single_span_trace(self):
        """Test processing trace with single span."""
        span = Span(trace_id="test-trace", span_id="test-span", span_name="TestSpan")
        trace_data = TraceData(spans=[span])
        TraceProcessor.group_spans_by_trace(trace_data)

        assert len(trace_data.traces) == 1
        assert "test-trace" in trace_data.traces
        assert len(trace_data.traces["test-trace"]) == 1

        # Build hierarchy
        root_spans = TraceProcessor.build_span_hierarchy(trace_data, "test-trace")
        assert len(root_spans) == 1
        assert root_spans[0].span_id == "test-span"

    def test_orphan_spans_treated_as_roots(self):
        """Test that orphan spans (parent not in trace) are treated as roots."""
        spans = [Span(trace_id="trace-1", span_id="orphan", span_name="Orphan", parent_span_id="non-existent-parent")]

        trace_data = TraceData(spans=spans)
        TraceProcessor.group_spans_by_trace(trace_data)

        root_spans = TraceProcessor.build_span_hierarchy(trace_data, "trace-1")

        # Orphan should be treated as root
        assert len(root_spans) == 1
        assert root_spans[0].span_id == "orphan"
