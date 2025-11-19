"""Tests for observability CLI commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.observability.commands import observability_app
from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import Span

runner = CliRunner()


class TestCreateObservabilityClient:
    """Test the _create_observability_client helper function."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_returns_tuple_with_client_agent_id_endpoint(self, mock_config, mock_client_class):
        """Test that helper returns (client, agent_id, endpoint_name) tuple."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _create_observability_client

        # Mock config
        mock_config.return_value = {
            "agent_id": "test-agent-123",
            "region": "us-west-2",
            "runtime_suffix": "PROD",
        }

        # Mock client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Call helper
        result = _create_observability_client(agent_id=None, agent="test-agent")

        # Should return tuple
        assert isinstance(result, tuple)
        assert len(result) == 3

        client, agent_id, endpoint_name = result
        assert client == mock_client
        assert agent_id == "test-agent-123"
        assert endpoint_name == "PROD"

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    def test_creates_stateless_client_with_only_region(self, mock_client_class):
        """Test that client is created with only region (stateless)."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _create_observability_client

        # Call with explicit agent_id and region
        _create_observability_client(
            agent_id="test-agent-123", agent=None, region="us-east-1", runtime_suffix="DEFAULT"
        )

        # Verify client was created with ONLY region_name
        mock_client_class.assert_called_once_with(region_name="us-east-1")


class TestObservabilityListCommand:
    """Test the 'list' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_list_passes_agent_id_to_client_methods(self, mock_config, mock_client_class):
        """Test that list command passes agent_id to client methods."""
        # Mock config
        mock_config.return_value = {
            "agent_id": "config-agent-123",
            "region": "us-west-2",
            "session_id": "session-abc",
        }

        # Mock client and its methods
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock query_spans_by_session to return empty list
        mock_client.query_spans_by_session.return_value = []

        # Run command
        runner.invoke(observability_app, ["list"])

        # Verify client methods were called with agent_id
        mock_client.query_spans_by_session.assert_called_once()
        call_kwargs = mock_client.query_spans_by_session.call_args.kwargs
        assert "agent_id" in call_kwargs
        assert call_kwargs["agent_id"] == "config-agent-123"


class TestStatelessClientPattern:
    """Test that commands follow stateless client pattern."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    def test_client_created_without_agent_id_parameter(self, mock_client_class):
        """Test that ObservabilityClient is created without agent_id parameter."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _create_observability_client

        # Create client
        _create_observability_client(agent_id="test-agent", region="us-west-2", runtime_suffix="DEFAULT")

        # Verify client constructor received ONLY region_name
        mock_client_class.assert_called_once()
        call_args = mock_client_class.call_args

        # Should only have region_name parameter
        assert "region_name" in call_args.kwargs
        assert "agent_id" not in call_args.kwargs
        assert "runtime_suffix" not in call_args.kwargs


class TestShowCommand:
    """Test the 'show' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_with_trace_id(self, mock_config, mock_client_class):
        """Test show command with explicit trace ID."""

        # Mock config
        mock_config.return_value = {
            "agent_id": "test-agent",
            "region": "us-west-2",
        }

        # Mock client and return value
        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        # Create a simple span
        test_span = Span(
            trace_id="test-trace-123",
            span_id="span-1",
            span_name="TestSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_trace.return_value = [test_span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        # Run show command with trace ID
        result = runner.invoke(observability_app, ["show", "--trace-id", "test-trace-123"])

        # Verify success
        assert result.exit_code == 0
        mock_client.query_spans_by_trace.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_with_session_id(self, mock_config, mock_client_class):
        """Test show command with session ID."""

        mock_config.return_value = {
            "agent_id": "test-agent",
            "region": "us-west-2",
        }

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        test_span = Span(
            trace_id="test-trace-456",
            span_id="span-2",
            span_name="SessionSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [test_span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        # Run show with session ID
        result = runner.invoke(observability_app, ["show", "--session-id", "test-session-789"])

        assert result.exit_code == 0
        mock_client.query_spans_by_session.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_with_conflicting_ids_fails(self, mock_config, mock_client_class):
        """Test that providing both trace_id and session_id fails."""
        mock_config.return_value = {
            "agent_id": "test-agent",
            "region": "us-west-2",
        }

        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client_class.return_value = mock_client

        # Run with both IDs (should fail)
        result = runner.invoke(observability_app, ["show", "--trace-id", "trace-123", "--session-id", "session-456"])

        # Should exit with error
        assert result.exit_code != 0
        assert "Cannot specify both" in result.output or result.exit_code == 1


class TestDefaultTimeRange:
    """Test the _get_default_time_range helper."""

    def test_returns_milliseconds_timestamp(self):
        """Test that time range returns milliseconds."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _get_default_time_range

        start_ms, end_ms = _get_default_time_range(days=7)

        # Should be milliseconds (13+ digits)
        assert start_ms > 1000000000000  # After year 2001 in ms
        assert end_ms > start_ms
        assert (end_ms - start_ms) > 0

    def test_respects_days_parameter(self):
        """Test that days parameter affects time range."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _get_default_time_range

        start_1, end_1 = _get_default_time_range(days=1)
        start_7, end_7 = _get_default_time_range(days=7)

        # 7 day range should have earlier start time
        assert start_7 < start_1
        # End times should be similar (both "now")
        assert abs(end_1 - end_7) < 10000  # Within 10 seconds


class TestAgentConfigHelper:
    """Test _get_agent_config_from_file helper."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    def test_returns_none_when_no_config_file(self, mock_load):
        """Test returns None when config doesn't exist."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _get_agent_config_from_file

        mock_load.return_value = None

        result = _get_agent_config_from_file()

        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    def test_extracts_agent_config_fields(self, mock_load):
        """Test extracts correct fields from config."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _get_agent_config_from_file

        # Mock config object
        mock_config = MagicMock()
        mock_agent_config = MagicMock()
        mock_agent_config.bedrock_agentcore.agent_id = "config-agent-999"
        mock_agent_config.bedrock_agentcore.agent_arn = "arn:aws:..."
        mock_agent_config.bedrock_agentcore.agent_session_id = "session-xyz"
        mock_agent_config.aws.region = "eu-west-1"
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_load.return_value = mock_config

        result = _get_agent_config_from_file("test-agent")

        assert result is not None
        assert result["agent_id"] == "config-agent-999"
        assert result["region"] == "eu-west-1"
        assert result["session_id"] == "session-xyz"


class TestShowCommandValidation:
    """Test validation logic in show command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_trace_id_with_all_flag_fails(self, mock_config, mock_client_class):
        """Test that --trace-id with --all flag fails."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--trace-id", "trace-123", "--all"])

        assert result.exit_code == 1
        assert "--all flag only works with sessions" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_trace_id_with_last_flag_fails(self, mock_config, mock_client_class):
        """Test that --trace-id with --last flag fails."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--trace-id", "trace-123", "--last", "2"])

        assert result.exit_code == 1
        assert "--last flag only works with sessions" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_all_and_last_together_fails(self, mock_config, mock_client_class):
        """Test that --all and --last together fails."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "session-123", "--all", "--last", "2"])

        assert result.exit_code == 1
        assert "Cannot use --all and --last together" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_with_all_flag(self, mock_config, mock_client_class):
        """Test show command with --all flag."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        # Create multiple spans
        span1 = Span(
            trace_id="trace-1",
            span_id="span-1",
            span_name="Span1",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        span2 = Span(
            trace_id="trace-2",
            span_id="span-2",
            span_name="Span2",
            parent_span_id="",
            start_time_unix_nano=3000000000,
            end_time_unix_nano=4000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span1, span2]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "session-789", "--all"])

        assert result.exit_code == 0
        mock_client.query_spans_by_session.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_with_last_flag(self, mock_config, mock_client_class):
        """Test show command with --last N flag."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="trace-last",
            span_id="span-x",
            span_name="LastSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "session-xyz", "--last", "2"])

        assert result.exit_code == 0
        mock_client.query_spans_by_session.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_with_errors_only_flag(self, mock_config, mock_client_class):
        """Test show command with --errors flag."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"

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

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "session-err", "--errors"])

        assert result.exit_code == 0


class TestShowCommandAutoDiscovery:
    """Test auto-discovery logic in show command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_without_ids_uses_config_session(self, mock_config, mock_client_class):
        """Test show without IDs uses session from config."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2", "session_id": "config-session-123"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="auto-trace",
            span_id="auto-span",
            span_name="AutoSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show"])

        assert result.exit_code == 0
        # Should use session from config
        call_args = mock_client.query_spans_by_session.call_args
        assert "config-session-123" in str(call_args)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_without_ids_fetches_latest_session(self, mock_config, mock_client_class):
        """Test show without IDs fetches latest session when no config."""

        # No session in config
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client.get_latest_session_id.return_value = "latest-session-456"

        span = Span(
            trace_id="latest-trace",
            span_id="latest-span",
            span_name="LatestSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show"])

        assert result.exit_code == 0
        # Should call get_latest_session_id
        mock_client.get_latest_session_id.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_without_ids_no_sessions_found(self, mock_config, mock_client_class):
        """Test show fails gracefully when no sessions found."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client.get_latest_session_id.return_value = None  # No sessions

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show"])

        assert result.exit_code == 1
        assert "No sessions found" in result.output


class TestListCommandValidation:
    """Test list command validation and options."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_list_with_errors_filter(self, mock_config, mock_client_class):
        """Test list command with --errors flag."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2", "session_id": "session-list"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        error_span = Span(
            trace_id="err-trace",
            span_id="err-span",
            span_name="ErrSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="ERROR",
        )
        mock_client.query_spans_by_session.return_value = [error_span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["list", "--errors"])

        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_list_auto_discovers_session(self, mock_config, mock_client_class):
        """Test list auto-discovers latest session."""

        # No session in config
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client.get_latest_session_id.return_value = "discovered-session"

        span = Span(
            trace_id="disc-trace",
            span_id="disc-span",
            span_name="DiscSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["list"])

        assert result.exit_code == 0
        mock_client.get_latest_session_id.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_list_no_sessions_found(self, mock_config, mock_client_class):
        """Test list fails when no sessions found."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}
        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client.get_latest_session_id.return_value = None

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["list"])

        assert result.exit_code == 1
        assert "No sessions found" in result.output


class TestAgentConfigHelperErrorPaths:
    """Test error handling in _get_agent_config_from_file."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    def test_returns_none_when_agent_id_missing(self, mock_load):
        """Test returns None when config has no agent_id."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _get_agent_config_from_file

        # Mock config with missing agent_id
        mock_config = MagicMock()
        mock_agent_config = MagicMock()
        mock_agent_config.bedrock_agentcore.agent_id = None  # Missing!
        mock_agent_config.aws.region = "us-west-2"
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_load.return_value = mock_config

        result = _get_agent_config_from_file("test-agent")

        # Should return None when agent_id missing
        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    def test_returns_none_when_region_missing(self, mock_load):
        """Test returns None when config has no region."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _get_agent_config_from_file

        # Mock config with missing region
        mock_config = MagicMock()
        mock_agent_config = MagicMock()
        mock_agent_config.bedrock_agentcore.agent_id = "test-agent"
        mock_agent_config.aws.region = None  # Missing!
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_load.return_value = mock_config

        result = _get_agent_config_from_file("test-agent")

        # Should return None when region missing
        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    def test_returns_none_on_exception(self, mock_load):
        """Test returns None when exception occurs during config loading."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _get_agent_config_from_file

        # Mock config that raises exception
        mock_config = MagicMock()
        mock_config.get_agent_config.side_effect = Exception("Config error")
        mock_load.return_value = mock_config

        result = _get_agent_config_from_file("test-agent")

        # Should return None on exception
        assert result is None


class TestShowCommandEmptyResults:
    """Test show command with empty/no results."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_trace_with_no_spans(self, mock_config, mock_client_class):
        """Test show trace when no spans found."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client.query_spans_by_trace.return_value = []  # No spans!

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--trace-id", "empty-trace"])

        # Should handle gracefully
        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_session_with_no_spans(self, mock_config, mock_client_class):
        """Test show session when no spans found."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client.query_spans_by_session.return_value = []  # No spans!

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "empty-session"])

        # Should handle gracefully
        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_list_with_no_spans(self, mock_config, mock_client_class):
        """Test list when no spans found."""
        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2", "session_id": "session-123"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"
        mock_client.query_spans_by_session.return_value = []  # No spans!

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["list"])

        # Should handle gracefully
        assert result.exit_code == 0


class TestShowCommandWithOutput:
    """Test show command with output file."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.Path")
    def test_show_with_output_json_export(self, mock_path, mock_config, mock_client_class):
        """Test show with --output exports to JSON."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="export-trace",
            span_id="export-span",
            span_name="ExportSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_trace.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        # Mock file operations
        mock_file = MagicMock()
        mock_path.return_value.open.return_value.__enter__.return_value = mock_file

        result = runner.invoke(observability_app, ["show", "--trace-id", "export-trace", "--output", "output.json"])

        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.Path")
    def test_show_output_handles_export_error(self, mock_path, mock_config, mock_client_class):
        """Test show handles export errors gracefully."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="error-export",
            span_id="error-span",
            span_name="ErrorSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_trace.return_value = [span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        # Mock file operation to raise error
        mock_path.return_value.open.side_effect = IOError("Cannot write file")

        result = runner.invoke(observability_app, ["show", "--trace-id", "error-export", "--output", "bad-path.json"])

        # Should handle error gracefully
        assert result.exit_code == 0
        assert "Error exporting" in result.output or result.exit_code == 0


class TestShowCommandRuntimeLogErrors:
    """Test runtime log error handling in show command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_trace_continues_when_runtime_logs_fail(self, mock_config, mock_client_class):
        """Test show continues when runtime logs query fails."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="test-trace",
            span_id="test-span",
            span_name="TestSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_trace.return_value = [span]
        # Runtime logs query raises exception
        mock_client.query_runtime_logs_by_traces.side_effect = Exception("Runtime logs error")

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--trace-id", "test-trace"])

        # Should still succeed (warning logged but not fatal)
        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_session_continues_when_runtime_logs_fail(self, mock_config, mock_client_class):
        """Test show session continues when runtime logs query fails."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="session-trace",
            span_id="session-span",
            span_name="SessionSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.side_effect = Exception("Runtime logs error")

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "test-session"])

        # Should still succeed
        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_all_traces_continues_when_runtime_logs_fail(self, mock_config, mock_client_class):
        """Test show --all continues when runtime logs fail."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="all-trace",
            span_id="all-span",
            span_name="AllSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.side_effect = Exception("Runtime logs error")

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "test-session", "--all"])

        # Should still succeed
        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_list_continues_when_runtime_logs_fail(self, mock_config, mock_client_class):
        """Test list continues when runtime logs query fails."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2", "session_id": "test-session"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        span = Span(
            trace_id="list-trace",
            span_id="list-span",
            span_name="ListSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [span]
        mock_client.query_runtime_logs_by_traces.side_effect = Exception("Runtime logs error")

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["list"])

        # Should still succeed (displays traces without I/O)
        assert result.exit_code == 0


class TestShowSessionErrorFiltering:
    """Test error filtering in session views."""

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_show_session_with_errors_only_no_errors_found(self, mock_config, mock_client_class):
        """Test --errors flag when no error traces exist."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        # Only OK spans (no errors)
        ok_span = Span(
            trace_id="ok-trace",
            span_id="ok-span",
            span_name="OKSpan",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [ok_span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["show", "--session-id", "no-errors-session", "--errors"])

        # Should complete (shows "no failed traces" message)
        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_list_with_errors_only_no_errors_found(self, mock_config, mock_client_class):
        """Test list --errors when no error traces exist."""

        mock_config.return_value = {"agent_id": "test-agent", "region": "us-west-2", "session_id": "no-err-session"}

        mock_client = MagicMock()
        mock_client.region = "us-west-2"

        ok_span = Span(
            trace_id="ok-trace-2",
            span_id="ok-span-2",
            span_name="OKSpan2",
            parent_span_id="",
            start_time_unix_nano=1000000000,
            end_time_unix_nano=2000000000,
            duration_ms=1000,
            status_code="OK",
        )
        mock_client.query_spans_by_session.return_value = [ok_span]
        mock_client.query_runtime_logs_by_traces.return_value = []

        mock_client_class.return_value = mock_client

        result = runner.invoke(observability_app, ["list", "--errors"])

        # Should complete
        assert result.exit_code == 0
