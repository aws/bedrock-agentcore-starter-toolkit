"""Data-driven tests for CloudWatchResultBuilder using real OTEL data from CloudWatch."""

import json
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.operations.observability.builders import CloudWatchResultBuilder
from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import RuntimeLog, Span

# Load real fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def langchain_spans():
    """Load real langchain OTEL spans from CloudWatch."""
    with open(FIXTURES_DIR / "raw_otel_langchain_spans.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture(scope="module")
def strands_openai_spans():
    """Load real strands openai OTEL spans from CloudWatch."""
    with open(FIXTURES_DIR / "raw_otel_strands_openai_spans.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture(scope="module")
def strands_bedrock_spans():
    """Load real strands bedrock OTEL spans from CloudWatch."""
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_spans.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture(scope="module")
def langchain_runtime_logs():
    """Load real langchain OTEL runtime logs from CloudWatch."""
    with open(FIXTURES_DIR / "raw_otel_langchain_runtime_logs.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture(scope="module")
def strands_openai_runtime_logs():
    """Load real strands openai OTEL runtime logs from CloudWatch."""
    with open(FIXTURES_DIR / "raw_otel_strands_openai_runtime_logs.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


@pytest.fixture(scope="module")
def strands_bedrock_runtime_logs():
    """Load real strands bedrock OTEL runtime logs from CloudWatch."""
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_runtime_logs.json") as f:
        data = json.load(f)
    return [entry["raw_otel_json"] for entry in data]


class TestCloudWatchSpanBuilder:
    """Test CloudWatchResultBuilder.build_span() with real OTEL span data."""

    def test_build_langchain_spans(self, langchain_spans):
        """Test building Span objects from real langchain OTEL spans."""
        # Convert OTEL format to CloudWatch query result format
        for otel_span in langchain_spans:
            # Simulate CloudWatch Logs Insights result format
            cw_result = self._otel_span_to_cloudwatch_result(otel_span)

            # Build span using our builder
            span = CloudWatchResultBuilder.build_span(cw_result)

            # Assertions
            assert isinstance(span, Span)
            assert span.trace_id == otel_span["traceId"]
            assert span.span_id == otel_span["spanId"]
            assert span.span_name == otel_span["name"]
            assert span.kind == otel_span.get("kind")
            assert span.status_code == otel_span.get("status", {}).get("code")

            # Check timing
            if "startTimeUnixNano" in otel_span:
                assert span.start_time_unix_nano == int(otel_span["startTimeUnixNano"])
            if "endTimeUnixNano" in otel_span:
                assert span.end_time_unix_nano == int(otel_span["endTimeUnixNano"])

    def test_build_strands_openai_spans(self, strands_openai_spans):
        """Test building Span objects from real strands openai OTEL spans."""
        for otel_span in strands_openai_spans:
            cw_result = self._otel_span_to_cloudwatch_result(otel_span)
            span = CloudWatchResultBuilder.build_span(cw_result)

            assert isinstance(span, Span)
            assert span.trace_id == otel_span["traceId"]
            assert span.span_id == otel_span["spanId"]
            assert span.span_name == otel_span["name"]

            # Check attributes are preserved
            if "attributes" in otel_span:
                assert isinstance(span.attributes, dict)

    def test_build_strands_bedrock_spans(self, strands_bedrock_spans):
        """Test building Span objects from real strands bedrock OTEL spans."""
        for otel_span in strands_bedrock_spans[:10]:  # Test first 10
            cw_result = self._otel_span_to_cloudwatch_result(otel_span)
            span = CloudWatchResultBuilder.build_span(cw_result)

            assert isinstance(span, Span)
            assert span.trace_id == otel_span["traceId"]
            assert span.span_id == otel_span["spanId"]

            # Check parent relationships
            if "parentSpanId" in otel_span:
                assert span.parent_span_id == otel_span["parentSpanId"]

    def test_span_duration_calculation(self, langchain_spans):
        """Test that duration is calculated correctly from timestamps."""
        for otel_span in langchain_spans:
            cw_result = self._otel_span_to_cloudwatch_result(otel_span)
            span = CloudWatchResultBuilder.build_span(cw_result)

            if span.start_time_unix_nano and span.end_time_unix_nano:
                expected_duration_ms = (span.end_time_unix_nano - span.start_time_unix_nano) / 1_000_000
                assert span.duration_ms == pytest.approx(expected_duration_ms, rel=0.01)

    @staticmethod
    def _otel_span_to_cloudwatch_result(otel_span: dict) -> list:
        """Convert OTEL span format to CloudWatch Logs Insights result format.

        CloudWatch returns results as list of field dictionaries.
        """
        result = []

        # Add top-level fields
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

        # Add timing fields
        if "startTimeUnixNano" in otel_span:
            result.append({"field": "startTimeUnixNano", "value": str(otel_span["startTimeUnixNano"])})
        if "endTimeUnixNano" in otel_span:
            result.append({"field": "endTimeUnixNano", "value": str(otel_span["endTimeUnixNano"])})
        if "durationNano" in otel_span:
            # Convert nano to ms
            duration_ms = int(otel_span["durationNano"]) / 1_000_000
            result.append({"field": "durationMs", "value": str(duration_ms)})

        # Add status
        if "status" in otel_span and "code" in otel_span["status"]:
            result.append({"field": "statusCode", "value": str(otel_span["status"]["code"])})
        if "status" in otel_span and "message" in otel_span["status"]:
            result.append({"field": "statusMessage", "value": otel_span["status"]["message"]})

        # Add session ID from attributes
        if "attributes" in otel_span and "session.id" in otel_span["attributes"]:
            result.append({"field": "attributes.session.id", "value": otel_span["attributes"]["session.id"]})

        # Add full message as JSON string (CloudWatch format)
        result.append({"field": "@message", "value": json.dumps(otel_span)})

        return result


class TestCloudWatchRuntimeLogBuilder:
    """Test CloudWatchResultBuilder.build_runtime_log() with real OTEL runtime logs."""

    def test_build_langchain_runtime_logs(self, langchain_runtime_logs):
        """Test building RuntimeLog objects from real langchain OTEL logs."""
        for otel_log in langchain_runtime_logs:
            cw_result = self._otel_log_to_cloudwatch_result(otel_log)
            runtime_log = CloudWatchResultBuilder.build_runtime_log(cw_result)

            assert isinstance(runtime_log, RuntimeLog)
            assert runtime_log.timestamp is not None
            assert runtime_log.message is not None

            # Check trace/span IDs if present
            if "traceId" in otel_log:
                assert runtime_log.trace_id == otel_log["traceId"]
            if "spanId" in otel_log:
                assert runtime_log.span_id == otel_log["spanId"]

            # Check raw message is preserved
            assert runtime_log.raw_message is not None
            assert isinstance(runtime_log.raw_message, dict)

    def test_build_strands_openai_runtime_logs(self, strands_openai_runtime_logs):
        """Test building RuntimeLog objects from real strands openai OTEL logs."""
        for otel_log in strands_openai_runtime_logs:
            cw_result = self._otel_log_to_cloudwatch_result(otel_log)
            runtime_log = CloudWatchResultBuilder.build_runtime_log(cw_result)

            assert isinstance(runtime_log, RuntimeLog)
            assert runtime_log.raw_message is not None

    def test_build_strands_bedrock_runtime_logs(self, strands_bedrock_runtime_logs):
        """Test building RuntimeLog objects from real strands bedrock OTEL logs."""
        for otel_log in strands_bedrock_runtime_logs[:10]:  # Test first 10
            cw_result = self._otel_log_to_cloudwatch_result(otel_log)
            runtime_log = CloudWatchResultBuilder.build_runtime_log(cw_result)

            assert isinstance(runtime_log, RuntimeLog)
            assert runtime_log.raw_message is not None

    @staticmethod
    def _otel_log_to_cloudwatch_result(otel_log: dict) -> list:
        """Convert OTEL log format to CloudWatch Logs Insights result format."""
        result = []

        # Add timestamp
        if "timeUnixNano" in otel_log:
            # Convert nano to ISO format
            timestamp_ms = int(otel_log["timeUnixNano"]) / 1_000_000
            result.append({"field": "@timestamp", "value": str(timestamp_ms)})

        # Add trace/span IDs
        if "traceId" in otel_log:
            result.append({"field": "traceId", "value": otel_log["traceId"]})
        if "spanId" in otel_log:
            result.append({"field": "spanId", "value": otel_log["spanId"]})

        # Add @message field - CloudWatch returns the full OTEL log as JSON string
        # The builder will parse this to get the structured data
        result.append({"field": "@message", "value": json.dumps(otel_log)})

        return result
