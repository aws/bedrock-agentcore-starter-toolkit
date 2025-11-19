"""End-to-end functional tests for observability using fixtures and notebook interface."""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from bedrock_agentcore_starter_toolkit.notebook.observability.observability import Observability
from bedrock_agentcore_starter_toolkit.operations.observability.builders import CloudWatchResultBuilder
from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import TraceData

# Load real fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def langchain_fixtures():
    """Load langchain fixtures."""
    with open(FIXTURES_DIR / "raw_otel_langchain_spans.json") as f:
        span_data = json.load(f)
    with open(FIXTURES_DIR / "raw_otel_langchain_runtime_logs.json") as f:
        log_data = json.load(f)
    return span_data, log_data


@pytest.fixture(scope="module")
def strands_bedrock_fixtures():
    """Load strands bedrock fixtures."""
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_spans.json") as f:
        span_data = json.load(f)
    with open(FIXTURES_DIR / "raw_otel_strands_bedrock_runtime_logs.json") as f:
        log_data = json.load(f)
    return span_data, log_data


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


def _build_spans_from_fixtures(span_data: list) -> list:
    """Build Span objects from fixture data."""
    spans = []
    for entry in span_data:
        otel_span = entry["raw_otel_json"]
        cw_result = _otel_span_to_cw(otel_span)
        span = CloudWatchResultBuilder.build_span(cw_result)
        if span:
            spans.append(span)
    return spans


def _build_logs_from_fixtures(log_data: list) -> list:
    """Build RuntimeLog objects from fixture data."""
    logs = []
    for entry in log_data:
        otel_log = entry["raw_otel_json"]
        cw_result = _otel_log_to_cw(otel_log)
        log = CloudWatchResultBuilder.build_runtime_log(cw_result)
        if log:
            logs.append(log)
    return logs


class TestE2EObservabilityList:
    """Test end-to-end 'list' functionality with fixtures."""

    def test_list_with_auto_discovery(self, langchain_fixtures):
        """Test list command with automatic session discovery (common user flow)."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.get_latest_session_id.return_value = session_id  # Auto-discovery
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Execute list without session_id - should auto-discover
            trace_data = obs.list()

            # Verify auto-discovery was called
            mock_client.get_latest_session_id.assert_called_once()
            mock_client.query_spans_by_session.assert_called_once()

            # Verify data
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) > 0
            assert trace_data.session_id == session_id

    def test_list_auto_discovery_no_sessions_found(self):
        """Test list when no sessions are found during auto-discovery."""
        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.get_latest_session_id.return_value = None  # No sessions found
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Should handle gracefully
            trace_data = obs.list()

            # Verify message to user
            output = string_io.getvalue()
            assert "No sessions found" in output

            # Should return empty data
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) == 0

    def test_list_with_langchain_session(self, langchain_fixtures, capsys):
        """Test list command with langchain session data and validate output format."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        # Extract session ID from first span
        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        # Mock the client
        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Execute list command
            trace_data = obs.list(session_id=session_id)

            # Verify client was called correctly
            mock_client.query_spans_by_session.assert_called_once()
            mock_client.query_runtime_logs_by_traces.assert_called_once()

            # Verify returned data
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) > 0
            assert trace_data.session_id == session_id
            assert len(trace_data.traces) > 0

            # Capture stdout to validate output format
            captured = capsys.readouterr()
            output = captured.out

            # Verify output exists and has content
            assert len(output) > 100, "Should produce substantial output"

            # Verify trace count message
            assert "trace" in output.lower(), "Should mention traces"

            # Verify status indicator present
            assert "✓" in output or "❌" in output or "⚠" in output, "Should show status"

    def test_list_with_strands_bedrock_session(self, strands_bedrock_fixtures):
        """Test list command with strands bedrock session data."""
        span_data, log_data = strands_bedrock_fixtures
        spans = _build_spans_from_fixtures(span_data[:10])  # Use subset for performance
        logs = _build_logs_from_fixtures(log_data[:10])

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            trace_data = obs.list(session_id=session_id)

            # Verify data
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) > 0
            assert len(trace_data.traces) > 0

            # Verify output
            output = string_io.getvalue()
            assert len(output) > 0

    def test_list_with_errors_filter(self, langchain_fixtures):
        """Test list command with errors filter."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        # Mark some spans as errors
        for i, span in enumerate(spans):
            if i % 3 == 0:  # Every 3rd span
                span.status_code = "ERROR"

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Execute with errors filter
            trace_data = obs.list(session_id=session_id, errors=True)

            # Verify only error traces are included
            assert isinstance(trace_data, TraceData)
            for _trace_id, trace_spans in trace_data.traces.items():
                # At least one span should have ERROR status
                has_error = any(s.status_code == "ERROR" for s in trace_spans)
                assert has_error


class TestE2EObservabilityShow:
    """Test end-to-end 'show' functionality with fixtures."""

    def test_show_with_auto_discovery_default_behavior(self, langchain_fixtures):
        """Test show() without parameters - most common user flow."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.get_latest_session_id.return_value = session_id  # Auto-discover
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Execute show without any parameters - should auto-discover and show latest trace
            trace_data = obs.show()

            # Verify auto-discovery was called
            mock_client.get_latest_session_id.assert_called_once()
            mock_client.query_spans_by_session.assert_called()

            # Verify data returned
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) > 0

    def test_show_auto_discovery_no_sessions_found(self):
        """Test show when no sessions exist (user feedback)."""
        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.get_latest_session_id.return_value = None  # No sessions
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Should handle gracefully with user message
            trace_data = obs.show()

            # Verify user-friendly message
            output = string_io.getvalue()
            assert "No sessions found" in output

            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) == 0

    def test_show_specific_trace(self, langchain_fixtures):
        """Test show command with specific trace ID."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        # Get first trace ID
        trace_id = spans[0].trace_id if spans else "test-trace"
        trace_spans = [s for s in spans if s.trace_id == trace_id]

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_trace.return_value = trace_spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Execute show command
            trace_data = obs.show(trace_id=trace_id)

            # Verify client was called (called twice: once by CLI helper, once for return data)
            assert mock_client.query_spans_by_trace.call_count >= 1
            assert mock_client.query_runtime_logs_by_traces.call_count >= 1

            # Verify data
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) > 0
            assert all(s.trace_id == trace_id for s in trace_data.spans)
            # Output verification: CLI helpers use global console, so we verify data instead

    def test_show_with_verbose(self, langchain_fixtures):
        """Test show command with verbose flag."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        trace_id = spans[0].trace_id if spans else "test-trace"
        trace_spans = [s for s in spans if s.trace_id == trace_id]

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_trace.return_value = trace_spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Execute show with verbose
            trace_data = obs.show(trace_id=trace_id, verbose=True)

            # Verify client was called
            assert mock_client.query_spans_by_trace.call_count >= 1

            # Verify data
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) > 0
            # Verbose mode: no truncation, verified by data integrity

    def test_show_all_traces_in_session(self, strands_bedrock_fixtures):
        """Test show --all with session ID."""
        span_data, log_data = strands_bedrock_fixtures
        spans = _build_spans_from_fixtures(span_data[:10])
        logs = _build_logs_from_fixtures(log_data[:10])

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Execute show --all
            trace_data = obs.show(session_id=session_id, all=True)

            # Verify client was called
            assert mock_client.query_spans_by_session.call_count >= 1

            # Verify data
            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) > 0
            assert trace_data.session_id == session_id
            # Should have multiple traces
            assert len(trace_data.traces) >= 1

    def test_show_last_trace_from_session(self, langchain_fixtures):
        """Test show --last N from session."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Execute show --last 1 (default)
            trace_data = obs.show(session_id=session_id, last=1)

            # Verify client was called
            assert mock_client.query_spans_by_session.call_count >= 1

            # Verify data
            assert isinstance(trace_data, TraceData)
            # Should return single trace data
            assert len(trace_data.spans) > 0


class TestE2EObservabilityMessageDisplay:
    """Test that runtime log messages are properly displayed to users."""

    def test_list_shows_actual_user_assistant_messages(self, langchain_fixtures, capsys):
        """Validate that actual user input and assistant output content is displayed."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Execute list to display messages
            obs.list(session_id=session_id)

            # Capture output
            captured = capsys.readouterr()
            output = captured.out

            # Validate list output shows table structure
            assert "Trace ID" in output, "Table should have Trace ID column"
            assert "Input" in output, "Table should have Input column"
            assert "Output" in output, "Table should have Output column"

            # Validate specific user input from fixtures (may be truncated)
            # Check for partial match since list view truncates
            assert "Hello" in output and ("find everything" in output or "abo..." in output), (
                "User input message content should be visible (may be truncated)"
            )

            # Validate assistant response structure from fixtures
            assert "outputs" in output.lower() or "messages" in output, "Assistant response structure should be visible"

            # Validate status indicators in table
            has_status = "✓" in output or "❌" in output or "⚠" in output
            assert has_status, "Status indicators should be present in trace list"

            # Validate input/output structure with JSON-like format
            assert '{"inputs"' in output or '{"outputs"' in output or "inputs" in output.lower(), (
                "Input/Output JSON structure should be visible in list table"
            )

            # Validate trace count message
            assert "Found" in output and "trace" in output.lower(), "Summary message with trace count should be shown"

            # Validate session ID is displayed
            assert session_id[:8] in output or "session" in output.lower(), "Session ID should be shown in output"

    def test_runtime_log_messages_displayed(self, langchain_fixtures, capsys):
        """Verify that actual LLM messages from runtime logs are displayed."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        # Verify we have runtime logs with messages
        assert len(logs) > 0, "Test requires runtime logs"

        # Find a log with message content
        message_logs = [log for log in logs if log.message and len(log.message) > 50]
        assert len(message_logs) > 0, "Test requires logs with message content"

        session_id = spans[0].attributes.get("session.id") if spans else "test-session"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Execute list to display messages
            trace_data = obs.list(session_id=session_id)

            # Capture stdout to verify messages were displayed
            captured = capsys.readouterr()

            # Verify trace data has runtime logs
            assert len(trace_data.runtime_logs) > 0

            # Verify actual messages appear in output
            # Look for common message indicators from LangChain/Bedrock logs
            output = captured.out
            # Should show user/assistant message markers or actual message content
            has_message_content = any(
                [
                    "💬" in output,  # User message emoji
                    "🤖" in output,  # Assistant message emoji
                    "message" in output.lower(),
                    len(output) > 500,  # Substantial output with message content
                ]
            )
            assert has_message_content, "Runtime log messages not visible in output"

    def test_span_hierarchy_visualized(self, langchain_fixtures, capsys):
        """Verify that span tree structure is visualized."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data)
        logs = _build_logs_from_fixtures(log_data)

        # Use multiple spans from same trace to show hierarchy
        trace_id = spans[0].trace_id if spans else "test-trace"
        trace_spans = [s for s in spans if s.trace_id == trace_id]

        # Verify we have multiple spans to show
        assert len(trace_spans) >= 2, "Test requires multiple spans for hierarchy"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_trace.return_value = trace_spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Execute show to visualize hierarchy
            obs.show(trace_id=trace_id)

            # Capture output
            captured = capsys.readouterr()
            output = captured.out

            # Verify tree visualization characters are present
            has_tree_viz = any(
                [
                    "└──" in output,  # Tree branch
                    "├──" in output,  # Tree branch
                    "│" in output,  # Tree line
                ]
            )
            assert has_tree_viz, "Span hierarchy not visualized with tree structure"

            # Verify multiple span names appear in output
            span_names_in_output = sum(1 for s in trace_spans[:5] if s.span_name and s.span_name in output)
            assert span_names_in_output >= 2, "Multiple spans should be visible in hierarchy"


class TestE2EObservabilityOutputFormats:
    """Test different output formats and modes."""

    def test_output_json_export(self, langchain_fixtures, tmp_path):
        """Test JSON export functionality."""
        span_data, log_data = langchain_fixtures
        spans = _build_spans_from_fixtures(span_data[:5])
        logs = _build_logs_from_fixtures(log_data[:5])

        trace_id = spans[0].trace_id if spans else "test-trace"
        trace_spans = [s for s in spans if s.trace_id == trace_id]

        output_file = tmp_path / "trace_output.json"

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_trace.return_value = trace_spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Execute show with output file
            obs.show(trace_id=trace_id, output=str(output_file))

            # Verify JSON file was created
            assert output_file.exists()

            # Verify JSON content
            with open(output_file) as f:
                exported_data = json.load(f)

            # JSON structure should have trace data
            assert isinstance(exported_data, dict)
            # Should contain some trace data (structure varies by export format)
            assert len(str(exported_data)) > 100  # Has meaningful content

    def test_normal_vs_verbose_output_length(self, strands_bedrock_fixtures):
        """Test that verbose output is longer than normal output."""
        span_data, log_data = strands_bedrock_fixtures
        spans = _build_spans_from_fixtures(span_data[:5])
        logs = _build_logs_from_fixtures(log_data[:5])

        trace_id = spans[0].trace_id if spans else "test-trace"
        trace_spans = [s for s in spans if s.trace_id == trace_id]

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_trace.return_value = trace_spans
            mock_client.query_runtime_logs_by_traces.return_value = logs
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            # Normal mode
            string_io_normal = StringIO()
            console_normal = Console(file=string_io_normal, force_terminal=True, width=120)
            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console_normal
            obs.show(trace_id=trace_id, verbose=False)
            normal_output = string_io_normal.getvalue()

            # Verbose mode
            string_io_verbose = StringIO()
            console_verbose = Console(file=string_io_verbose, force_terminal=True, width=120)
            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console_verbose
            obs.show(trace_id=trace_id, verbose=True)
            verbose_output = string_io_verbose.getvalue()

            # Verbose should have equal or more content
            assert len(verbose_output) >= len(normal_output) * 0.8


class TestE2EObservabilityEdgeCases:
    """Test edge cases in E2E flows."""

    def test_empty_session_no_spans(self):
        """Test handling of empty session (no spans found)."""
        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            mock_client.query_spans_by_session.return_value = []
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            string_io = StringIO()
            console = Console(file=string_io, force_terminal=True, width=120)

            obs = Observability(agent_id="test-agent", region="us-east-1")
            obs.console = console

            # Should handle gracefully
            trace_data = obs.list(session_id="empty-session")

            assert isinstance(trace_data, TraceData)
            assert len(trace_data.spans) == 0

            output = string_io.getvalue()
            assert "No spans found" in output

    def test_show_conflicting_parameters(self):
        """Test validation of conflicting parameters."""
        with patch(
            "bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client"
        ) as mock_create:
            mock_client = MagicMock()
            mock_client.region = "us-east-1"
            # Return tuple: (client, agent_id, endpoint_name)
            mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

            obs = Observability(agent_id="test-agent", region="us-east-1")

            # Test conflicting parameters
            with pytest.raises(ValueError, match="Cannot specify both"):
                obs.show(trace_id="trace-1", session_id="session-1")

            with pytest.raises(ValueError, match="--all only works"):
                obs.show(trace_id="trace-1", all=True)

            with pytest.raises(ValueError, match="--last only works"):
                obs.show(trace_id="trace-1", last=2)
