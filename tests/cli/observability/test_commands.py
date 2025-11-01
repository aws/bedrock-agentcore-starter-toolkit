"""Unit tests for CLI observability commands."""

import json
from unittest.mock import MagicMock, patch

import pytest
import typer

from bedrock_agentcore_starter_toolkit.cli.observability.commands import (
    _create_observability_client,
    _export_trace_data_to_json,
    _get_agent_config_from_file,
    _get_default_time_range,
    list_traces,
    show,
)
from bedrock_agentcore_starter_toolkit.operations.observability.models.telemetry import Span, TraceData


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_default_time_range_7_days(self):
        """Test default time range calculation (7 days)."""
        start_ms, end_ms = _get_default_time_range(days=7)

        # Verify the range is approximately 7 days (allow some seconds for test execution)
        expected_diff_ms = 7 * 24 * 60 * 60 * 1000
        actual_diff_ms = end_ms - start_ms
        assert abs(actual_diff_ms - expected_diff_ms) < 10000  # Within 10 seconds

    @pytest.mark.parametrize("days", [1, 3, 7, 14, 30])
    def test_get_default_time_range_various_days(self, days):
        """Test time range calculation with various day values."""
        start_ms, end_ms = _get_default_time_range(days=days)

        expected_diff_ms = days * 24 * 60 * 60 * 1000
        actual_diff_ms = end_ms - start_ms
        assert abs(actual_diff_ms - expected_diff_ms) < 10000

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.Path")
    def test_get_agent_config_from_file_success(self, mock_path, mock_load_config):
        """Test loading agent config from file successfully."""
        # Mock config
        mock_config = MagicMock()
        mock_agent_config = MagicMock()
        mock_agent_config.bedrock_agentcore.agent_id = "agent-123"
        mock_agent_config.bedrock_agentcore.agent_arn = "arn:aws:bedrock:us-east-1:123:agent/agent-123"
        mock_agent_config.bedrock_agentcore.agent_session_id = "session-456"
        mock_agent_config.aws.region = "us-east-1"
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_load_config.return_value = mock_config

        result = _get_agent_config_from_file()

        assert result == {
            "agent_id": "agent-123",
            "agent_arn": "arn:aws:bedrock:us-east-1:123:agent/agent-123",
            "session_id": "session-456",
            "region": "us-east-1",
            "runtime_suffix": "DEFAULT",
        }

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    def test_get_agent_config_from_file_no_config(self, mock_load_config):
        """Test when config file doesn't exist."""
        mock_load_config.return_value = None

        result = _get_agent_config_from_file()

        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.Path")
    def test_get_agent_config_from_file_missing_agent_id(self, mock_path, mock_load_config):
        """Test when config exists but missing required fields."""
        mock_config = MagicMock()
        mock_agent_config = MagicMock()
        mock_agent_config.bedrock_agentcore.agent_id = None  # Missing
        mock_agent_config.aws.region = "us-east-1"
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_load_config.return_value = mock_config

        result = _get_agent_config_from_file()

        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.load_config_if_exists")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.Path")
    def test_get_agent_config_from_file_exception(self, mock_path, mock_load_config):
        """Test when config loading raises exception."""
        mock_config = MagicMock()
        mock_config.get_agent_config.side_effect = Exception("Config error")
        mock_load_config.return_value = mock_config

        result = _get_agent_config_from_file()

        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    def test_create_observability_client_with_cli_args(self, mock_client_class):
        """Test creating client with CLI arguments."""
        _create_observability_client(agent_id="agent-123", region="us-east-1")

        mock_client_class.assert_called_once_with(
            region_name="us-east-1", agent_id="agent-123", runtime_suffix="DEFAULT"
        )

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.ObservabilityClient")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    def test_create_observability_client_from_config(self, mock_get_config, mock_client_class):
        """Test creating client from config file."""
        mock_get_config.return_value = {
            "agent_id": "agent-456",
            "region": "us-west-2",
            "runtime_suffix": "DEFAULT",
        }

        _create_observability_client(agent_id=None, region=None)

        mock_client_class.assert_called_once_with(
            region_name="us-west-2", agent_id="agent-456", runtime_suffix="DEFAULT"
        )

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_create_observability_client_missing_params(self, mock_console, mock_get_config):
        """Test error when both CLI args and config are missing."""
        mock_get_config.return_value = None

        with pytest.raises(typer.Exit) as exc_info:
            _create_observability_client(agent_id=None, region=None)

        assert exc_info.value.exit_code == 1
        assert mock_console.print.call_count >= 1

    def test_export_trace_data_to_json_success(self, tmp_path):
        """Test exporting trace data to JSON successfully."""
        output_file = tmp_path / "trace.json"

        # Create sample trace data
        span = Span(trace_id="trace-1", span_id="span-1", span_name="TestSpan", duration_ms=100.0)
        trace_data = TraceData(spans=[span])
        trace_data.group_spans_by_trace()

        _export_trace_data_to_json(trace_data, str(output_file), data_type="trace")

        # Verify file was created
        assert output_file.exists()

        # Verify content
        with output_file.open() as f:
            data = json.load(f)

        assert "traces" in data
        assert "trace-1" in data["traces"]

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_export_trace_data_to_json_failure(self, mock_console):
        """Test export failure handling."""
        span = Span(trace_id="trace-1", span_id="span-1", span_name="TestSpan")
        trace_data = TraceData(spans=[span])

        # Try to export to invalid path
        _export_trace_data_to_json(trace_data, "/invalid/path/trace.json", data_type="trace")

        # Should print error
        assert any("Error exporting" in str(call) for call in mock_console.print.call_args_list)


class TestShowCommand:
    """Test the show command and its helper functions."""

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
        ]

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._show_trace_view")
    def test_show_with_trace_id(self, mock_show_trace, mock_create_client, mock_get_time_range):
        """Test show command with trace ID."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        show(
            trace_id="trace-123",
            session_id=None,
            agent_id="agent-1",
            region="us-east-1",
            agent_name=None,
            days=7,
            all_traces=False,
            errors_only=False,
            simple=False,
            output=None,
            last=1,
        )

        mock_show_trace.assert_called_once_with(mock_client, "trace-123", 1000, 2000, True, None)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._show_session_view")
    def test_show_with_session_id(self, mock_show_session, mock_create_client, mock_get_time_range):
        """Test show command with session ID."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        show(
            trace_id=None,
            session_id="session-456",
            agent_id="agent-1",
            region="us-east-1",
            agent_name=None,
            days=7,
            all_traces=False,
            errors_only=False,
            simple=False,
            output=None,
            last=1,
        )

        mock_show_session.assert_called_once_with(
            mock_client, "session-456", 1000, 2000, True, True, False, False, None
        )

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_with_both_trace_and_session_id(self, mock_console, mock_create_client, mock_get_time_range):
        """Test error when both trace_id and session_id are provided."""
        mock_get_time_range.return_value = (1000, 2000)

        with pytest.raises(typer.Exit) as exc_info:
            show(
                trace_id="trace-123",
                session_id="session-456",
                agent_id="agent-1",
                region="us-east-1",
                agent_name=None,
                days=7,
                all_traces=False,
                errors_only=False,
                simple=False,
                output=None,
                last=1,
            )

        assert exc_info.value.exit_code == 1
        assert any("Cannot specify both" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_trace_with_all_flag_error(self, mock_console, mock_create_client, mock_get_time_range):
        """Test error when using --all flag with trace_id."""
        mock_get_time_range.return_value = (1000, 2000)

        with pytest.raises(typer.Exit) as exc_info:
            show(
                trace_id="trace-123",
                session_id=None,
                agent_id="agent-1",
                region="us-east-1",
                agent_name=None,
                days=7,
                all_traces=True,
                errors_only=False,
                simple=False,
                output=None,
                last=1,
            )

        assert exc_info.value.exit_code == 1
        assert any("--all flag only works with sessions" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_trace_with_last_flag_error(self, mock_console, mock_create_client, mock_get_time_range):
        """Test error when using --last flag with trace_id."""
        mock_get_time_range.return_value = (1000, 2000)

        with pytest.raises(typer.Exit) as exc_info:
            show(
                trace_id="trace-123",
                session_id=None,
                agent_id="agent-1",
                region="us-east-1",
                agent_name=None,
                days=7,
                all_traces=False,
                errors_only=False,
                simple=False,
                output=None,
                last=2,
            )

        assert exc_info.value.exit_code == 1
        assert any("--last flag only works with sessions" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_with_all_and_last_flags_error(self, mock_console, mock_create_client, mock_get_time_range):
        """Test error when using both --all and --last flags."""
        mock_get_time_range.return_value = (1000, 2000)

        with pytest.raises(typer.Exit) as exc_info:
            show(
                trace_id=None,
                session_id="session-456",
                agent_id="agent-1",
                region="us-east-1",
                agent_name=None,
                days=7,
                all_traces=True,
                errors_only=False,
                simple=False,
                output=None,
                last=2,
            )

        assert exc_info.value.exit_code == 1
        assert any("Cannot use --all and --last together" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._show_last_trace_from_session")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_from_config_session(
        self, mock_console, mock_show_last, mock_get_config, mock_create_client, mock_get_time_range
    ):
        """Test show command using session from config file."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        mock_get_config.return_value = {"session_id": "session-from-config"}

        show(
            trace_id=None,
            session_id=None,
            agent_id="agent-1",
            region="us-east-1",
            agent_name=None,
            days=7,
            all_traces=False,
            errors_only=False,
            simple=False,
            output=None,
            last=1,
        )

        mock_show_last.assert_called_once_with(mock_client, "session-from-config", 1000, 2000, True, 1, False, None)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_command_exception_handling(self, mock_console, mock_create_client, mock_get_time_range):
        """Test exception handling in show command."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_create_client.side_effect = Exception("Client creation failed")

        with pytest.raises(typer.Exit) as exc_info:
            show(
                trace_id="trace-123",
                session_id=None,
                agent_id="agent-1",
                region="us-east-1",
                agent_name=None,
                days=7,
                all_traces=False,
                errors_only=False,
                simple=False,
                output=None,
                last=1,
            )

        assert exc_info.value.exit_code == 1
        assert any("Error:" in str(call) for call in mock_console.print.call_args_list)


class TestListCommand:
    """Test the list_traces command."""

    @pytest.fixture
    def sample_spans(self):
        """Create sample spans for testing."""
        return [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Trace1",
                start_time_unix_nano=1000000000,
                end_time_unix_nano=2000000000,
                duration_ms=1000.0,
                status_code="OK",
            ),
            Span(
                trace_id="trace-2",
                span_id="span-2",
                span_name="Trace2",
                start_time_unix_nano=3000000000,
                end_time_unix_nano=4000000000,
                duration_ms=1000.0,
                status_code="ERROR",
            ),
        ]

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_list_traces_with_session_id(self, mock_console, mock_create_client, mock_get_time_range, sample_spans):
        """Test list_traces command with session ID."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = sample_spans
        mock_create_client.return_value = mock_client

        list_traces(
            session_id="session-123",
            agent_id="agent-1",
            region="us-east-1",
            agent_name=None,
            days=7,
            errors_only=False,
        )

        mock_client.query_spans_by_session.assert_called_once_with("session-123", 1000, 2000)
        # Verify console.print was called (table rendering)
        assert mock_console.print.called

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_list_traces_from_config(
        self, mock_console, mock_get_config, mock_create_client, mock_get_time_range, sample_spans
    ):
        """Test list_traces using session from config."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = sample_spans
        mock_create_client.return_value = mock_client
        mock_get_config.return_value = {"session_id": "session-from-config"}

        list_traces(session_id=None, agent_id="agent-1", region="us-east-1", agent_name=None, days=7, errors_only=False)

        mock_client.query_spans_by_session.assert_called_once_with("session-from-config", 1000, 2000)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_list_traces_no_spans_found(self, mock_console, mock_create_client, mock_get_time_range):
        """Test list_traces when no spans are found."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = []
        mock_create_client.return_value = mock_client

        list_traces(
            session_id="session-123",
            agent_id="agent-1",
            region="us-east-1",
            agent_name=None,
            days=7,
            errors_only=False,
        )

        assert any("No spans found" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_list_traces_errors_only(self, mock_console, mock_create_client, mock_get_time_range, sample_spans):
        """Test list_traces with --errors flag."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = sample_spans
        mock_create_client.return_value = mock_client

        list_traces(
            session_id="session-123",
            agent_id="agent-1",
            region="us-east-1",
            agent_name=None,
            days=7,
            errors_only=True,
        )

        # Should only show error trace
        mock_client.query_spans_by_session.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_agent_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_list_traces_no_config_session(
        self, mock_console, mock_get_config, mock_create_client, mock_get_time_range
    ):
        """Test list_traces error when no session ID and no config."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_get_config.return_value = None

        with pytest.raises(typer.Exit) as exc_info:
            list_traces(
                session_id=None, agent_id="agent-1", region="us-east-1", agent_name=None, days=7, errors_only=False
            )

        assert exc_info.value.exit_code == 1
        assert any("No session ID provided" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._get_default_time_range")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._create_observability_client")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_list_traces_exception_handling(self, mock_console, mock_create_client, mock_get_time_range):
        """Test exception handling in list_traces."""
        mock_get_time_range.return_value = (1000, 2000)
        mock_create_client.side_effect = Exception("Client error")

        with pytest.raises(typer.Exit) as exc_info:
            list_traces(
                session_id="session-123",
                agent_id="agent-1",
                region="us-east-1",
                agent_name=None,
                days=7,
                errors_only=False,
            )

        assert exc_info.value.exit_code == 1
        assert any("Error:" in str(call) for call in mock_console.print.call_args_list)


class TestInternalViewFunctions:
    """Test internal view functions that are called by show and list commands."""

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
                status_code="ERROR",
            ),
        ]

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_trace_view_basic(self, mock_console, mock_visualizer_class, sample_spans):
        """Test _show_trace_view with basic trace."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_trace_view

        mock_client = MagicMock()
        mock_client.query_spans_by_trace.return_value = sample_spans

        _show_trace_view(mock_client, "trace-1", 1000, 2000, verbose=False, output=None)

        mock_client.query_spans_by_trace.assert_called_once_with("trace-1", 1000, 2000)
        mock_visualizer_class.assert_called_once()
        assert mock_console.print.called

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_trace_view_no_spans(self, mock_console, mock_visualizer_class):
        """Test _show_trace_view when no spans found."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_trace_view

        mock_client = MagicMock()
        mock_client.query_spans_by_trace.return_value = []

        _show_trace_view(mock_client, "trace-1", 1000, 2000, verbose=False, output=None)

        # Should print "No spans found" and not call visualizer
        assert any("No spans found" in str(call) for call in mock_console.print.call_args_list)
        mock_visualizer_class.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands._export_trace_data_to_json")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_trace_view_with_output(self, mock_console, mock_visualizer_class, mock_export, sample_spans):
        """Test _show_trace_view with JSON export."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_trace_view

        mock_client = MagicMock()
        mock_client.query_spans_by_trace.return_value = sample_spans
        mock_client.query_runtime_logs_by_traces.return_value = []

        _show_trace_view(mock_client, "trace-1", 1000, 2000, verbose=False, output="trace.json")

        mock_client.query_runtime_logs_by_traces.assert_called_once()
        mock_export.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.logger")
    def test_show_trace_view_runtime_logs_error(self, mock_logger, mock_console, mock_visualizer_class, sample_spans):
        """Test _show_trace_view when runtime log query fails."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_trace_view

        mock_client = MagicMock()
        mock_client.query_spans_by_trace.return_value = sample_spans
        mock_client.query_runtime_logs_by_traces.side_effect = Exception("Log query failed")

        _show_trace_view(mock_client, "trace-1", 1000, 2000, verbose=True, output=None)

        # Should log warning but continue
        mock_logger.warning.assert_called_once()
        mock_visualizer_class.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_session_view_summary(self, mock_console, mock_visualizer_class, sample_spans):
        """Test _show_session_view with summary mode."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_session_view

        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = sample_spans

        _show_session_view(
            mock_client,
            "session-1",
            1000,
            2000,
            verbose=False,
            summary_only=True,
            all_traces=False,
            errors_only=False,
            output=None,
        )

        mock_client.query_spans_by_session.assert_called_once_with("session-1", 1000, 2000)
        # Should call print_trace_summary
        mock_visualizer_class.return_value.print_trace_summary.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_session_view_all_traces(self, mock_console, mock_visualizer_class, sample_spans):
        """Test _show_session_view with all traces mode."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_session_view

        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = sample_spans
        mock_client.query_runtime_logs_by_traces.return_value = []

        _show_session_view(
            mock_client,
            "session-1",
            1000,
            2000,
            verbose=True,
            summary_only=False,
            all_traces=True,
            errors_only=False,
            output=None,
        )

        # Should query runtime logs and visualize all traces
        mock_client.query_runtime_logs_by_traces.assert_called_once()
        mock_visualizer_class.return_value.visualize_all_traces.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_session_view_errors_only(self, mock_console, mock_visualizer_class, sample_spans):
        """Test _show_session_view with errors_only filter."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_session_view

        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = sample_spans

        _show_session_view(
            mock_client,
            "session-1",
            1000,
            2000,
            verbose=False,
            summary_only=True,
            all_traces=False,
            errors_only=True,
            output=None,
        )

        # Should still call visualizer (filtering happens in TraceData)
        mock_visualizer_class.return_value.print_trace_summary.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_session_view_no_error_traces(self, mock_console, mock_visualizer_class):
        """Test _show_session_view when no error traces found."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_session_view

        # Create only successful spans
        ok_spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="OKSpan",
                duration_ms=100.0,
                status_code="OK",
            )
        ]

        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = ok_spans

        _show_session_view(
            mock_client,
            "session-1",
            1000,
            2000,
            verbose=False,
            summary_only=True,
            all_traces=False,
            errors_only=True,
            output=None,
        )

        # Should print "No failed traces found"
        assert any("No failed traces found" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_last_trace_from_session(self, mock_console, mock_visualizer_class, sample_spans):
        """Test _show_last_trace_from_session."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_last_trace_from_session

        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = sample_spans

        _show_last_trace_from_session(
            mock_client, "session-1", 1000, 2000, verbose=False, nth_last=1, errors_only=False, output=None
        )

        mock_client.query_spans_by_session.assert_called_once()
        mock_visualizer_class.return_value.visualize_trace.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.TraceVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_last_trace_nth(self, mock_console, mock_visualizer_class):
        """Test _show_last_trace_from_session with nth trace."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_last_trace_from_session

        # Create spans for multiple traces
        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Trace1",
                end_time_unix_nano=1000000000,
                duration_ms=100.0,
            ),
            Span(
                trace_id="trace-2",
                span_id="span-2",
                span_name="Trace2",
                end_time_unix_nano=2000000000,
                duration_ms=100.0,
            ),
        ]

        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = spans

        _show_last_trace_from_session(
            mock_client, "session-1", 1000, 2000, verbose=False, nth_last=2, errors_only=False, output=None
        )

        # Should show "2nd most recent trace" or "2th most recent trace"
        assert any("2th most recent" in str(call) or "2nd" in str(call) for call in mock_console.print.call_args_list)

    @patch("bedrock_agentcore_starter_toolkit.cli.observability.commands.console")
    def test_show_last_trace_exceeds_count(self, mock_console):
        """Test _show_last_trace_from_session when requested nth exceeds trace count."""
        from bedrock_agentcore_starter_toolkit.cli.observability.commands import _show_last_trace_from_session

        spans = [
            Span(
                trace_id="trace-1",
                span_id="span-1",
                span_name="Trace1",
                end_time_unix_nano=1000000000,
                duration_ms=100.0,
            )
        ]

        mock_client = MagicMock()
        mock_client.query_spans_by_session.return_value = spans

        _show_last_trace_from_session(
            mock_client, "session-1", 1000, 2000, verbose=False, nth_last=5, errors_only=False, output=None
        )

        # Should print warning about only 1 trace found
        assert any("Only 1 trace" in str(call) for call in mock_console.print.call_args_list)
