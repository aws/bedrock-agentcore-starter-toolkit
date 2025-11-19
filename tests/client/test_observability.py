"""Tests for Observability notebook interface."""

from unittest.mock import MagicMock, patch

import pytest

from bedrock_agentcore_starter_toolkit.notebook import Observability
from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span, TraceData


class TestObservabilityInit:
    """Test Observability client initialization."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_init_with_agent_id(self, mock_create):
        """Test initialization with agent_id."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        obs = Observability(agent_id="test-agent", region="us-east-1")

        assert obs.agent_id == "test-agent"
        assert obs.region == "us-east-1"
        assert obs.endpoint_name == "DEFAULT"
        assert obs.client == mock_client
        mock_create.assert_called_once_with(
            agent=None, agent_id="test-agent", region="us-east-1", runtime_suffix="DEFAULT"
        )

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_init_with_agent_name(self, mock_create):
        """Test initialization with agent_name."""
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_create.return_value = (mock_client, "config-agent", "PROD")

        obs = Observability(agent_name="my-agent", runtime_suffix="PROD")

        assert obs.agent_id == "config-agent"
        assert obs.region == "us-west-2"
        assert obs.endpoint_name == "PROD"
        mock_create.assert_called_once_with(agent="my-agent", agent_id=None, region=None, runtime_suffix="PROD")

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_init_creates_visualizer(self, mock_create):
        """Test that visualizer is initialized."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        obs = Observability(agent_id="test-agent")

        assert obs.visualizer is not None
        assert obs.console is not None


class TestObservabilityList:
    """Test list() method."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._display_trace_list")
    def test_list_with_session_id(self, mock_display, mock_create):
        """Test list with explicit session_id."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        # Mock spans
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="TestSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        obs = Observability(agent_id="test-agent")
        result = obs.list(session_id="session-123")

        assert isinstance(result, TraceData)
        assert result.session_id == "session-123"
        assert len(result.spans) == 1
        mock_client.query_spans_by_session.assert_called_once()
        mock_display.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_list_auto_discovers_session(self, mock_create):
        """Test list auto-discovers session when not provided."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        mock_client.get_latest_session_id.return_value = "auto-session-456"
        mock_client.query_spans_by_session.return_value = []

        obs = Observability(agent_id="test-agent")
        result = obs.list()

        mock_client.get_latest_session_id.assert_called_once()
        assert result.session_id == "auto-session-456"

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_list_no_sessions_found(self, mock_create):
        """Test list when no sessions found."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        mock_client.get_latest_session_id.return_value = None

        obs = Observability(agent_id="test-agent")
        result = obs.list()

        assert isinstance(result, TraceData)
        assert len(result.spans) == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._display_trace_list")
    def test_list_filters_errors(self, mock_display, mock_create):
        """Test list with errors=True filters to error traces."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        error_span = Span(
            trace_id="error-trace",
            span_id="error-span",
            span_name="ErrorSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="ERROR",
        )
        mock_client.query_spans_by_session.return_value = [error_span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        obs = Observability(agent_id="test-agent")
        result = obs.list(session_id="session-123", errors=True)

        assert len(result.traces) == 1
        assert "error-trace" in result.traces


class TestObservabilityShow:
    """Test show() method."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._show_trace_view")
    def test_show_with_trace_id(self, mock_show_trace, mock_create):
        """Test show with explicit trace_id."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        span = Span(
            trace_id="trace-123",
            span_id="span-1",
            span_name="TestSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_trace.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        obs = Observability(agent_id="test-agent")
        result = obs.show(trace_id="trace-123")

        mock_show_trace.assert_called_once()
        assert isinstance(result, TraceData)
        mock_client.query_spans_by_trace.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._show_session_view")
    def test_show_with_session_all(self, mock_show_session, mock_create):
        """Test show with session_id and all=True."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        span = Span(
            trace_id="trace-456",
            span_id="span-2",
            span_name="SessionSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        obs = Observability(agent_id="test-agent")
        result = obs.show(session_id="session-456", all=True)

        mock_show_session.assert_called_once()
        assert isinstance(result, TraceData)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_show_validation_both_ids(self, mock_create):
        """Test show raises error when both trace_id and session_id provided."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        obs = Observability(agent_id="test-agent")

        with pytest.raises(ValueError, match="Cannot specify both"):
            obs.show(trace_id="trace-123", session_id="session-456")

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_show_validation_trace_with_all(self, mock_create):
        """Test show raises error when trace_id with all flag."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        obs = Observability(agent_id="test-agent")

        with pytest.raises(ValueError, match="--all only works with sessions"):
            obs.show(trace_id="trace-123", all=True)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    def test_show_validation_all_with_last(self, mock_create):
        """Test show raises error when both all and last provided."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        obs = Observability(agent_id="test-agent")

        with pytest.raises(ValueError, match="Cannot use --all and --last"):
            obs.show(session_id="session-123", all=True, last=2)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._show_session_view")
    def test_show_with_last_flag(self, mock_show_session, mock_create):
        """Test show with last=N flag."""
        mock_client = MagicMock()
        mock_client.region = "us-east-1"
        mock_create.return_value = (mock_client, "test-agent", "DEFAULT")

        span = Span(
            trace_id="trace-last",
            span_id="span-last",
            span_name="LastSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        obs = Observability(agent_id="test-agent")
        result = obs.show(session_id="session-789", last=2)

        mock_show_session.assert_called_once()
        assert isinstance(result, TraceData)
