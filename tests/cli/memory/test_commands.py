"""Tests for memory CLI show commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.memory.commands import _ConfigLookupResult, memory_app, show_app

runner = CliRunner()


def _mock_config(memory_id=None, region=None, config_exists=True, agent_name=None):
    """Helper to create _ConfigLookupResult for tests."""
    return _ConfigLookupResult(
        memory_id=memory_id,
        region=region,
        config_exists=config_exists,
        agent_name=agent_name,
    )


class TestShowCommand:
    """Test the 'show' command (memory details)."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_uses_config_memory_id(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show uses memory_id from config."""
        mock_config.return_value = _mock_config(memory_id="config-mem-123", region="us-west-2")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_memory = MagicMock()
        mock_memory.items.return_value = [("id", "config-mem-123")]
        mock_manager.get_memory.return_value = mock_memory

        result = runner.invoke(show_app, [])

        assert result.exit_code == 0
        mock_manager.get_memory.assert_called_once_with("config-mem-123")

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_explicit_memory_id_overrides_config(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test explicit --memory-id overrides config."""
        mock_config.return_value = _mock_config(memory_id="config-mem", region="us-west-2")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_memory = MagicMock()
        mock_memory.items.return_value = [("id", "explicit-mem")]
        mock_manager.get_memory.return_value = mock_memory

        result = runner.invoke(show_app, ["--memory-id", "explicit-mem"])

        assert result.exit_code == 0
        mock_manager.get_memory.assert_called_once_with("explicit-mem")

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_no_memory_id_errors(self, mock_config):
        """Test show errors when no memory_id available."""
        mock_config.return_value = _mock_config(config_exists=False)

        result = runner.invoke(show_app, [])

        assert result.exit_code == 1
        assert "No memory specified" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_with_verbose(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show with verbose flag."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_memory = MagicMock()
        mock_memory.items.return_value = [("id", "mem-123")]
        mock_manager.get_memory.return_value = mock_memory
        mock_manager.list_actors.return_value = []
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer

        result = runner.invoke(show_app, ["--verbose"])

        assert result.exit_code == 0
        mock_visualizer.visualize_memory.assert_called_once()
        call_kwargs = mock_visualizer.visualize_memory.call_args[1]
        assert call_kwargs["verbose"] is True

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_with_region(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show with explicit region."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-west-2")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_memory = MagicMock()
        mock_memory.items.return_value = [("id", "mem-123")]
        mock_manager.get_memory.return_value = mock_memory

        result = runner.invoke(show_app, ["--region", "eu-west-1"])

        assert result.exit_code == 0
        mock_manager_class.assert_called_once()
        call_kwargs = mock_manager_class.call_args[1]
        assert call_kwargs["region_name"] == "eu-west-1"


class TestShowEventsCommand:
    """Test the 'show events' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_default_shows_latest(
        self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class
    ):
        """Test show events shows latest event by default."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer
        mock_collect.return_value = [
            {"eventTimestamp": "2024-01-02T00:00:00Z", "content": "newer"},
            {"eventTimestamp": "2024-01-01T00:00:00Z", "content": "older"},
        ]

        result = runner.invoke(show_app, ["events"])

        assert result.exit_code == 0
        mock_visualizer.display_single_event.assert_called_once()
        # First arg is the event, should be the newer one
        call_args = mock_visualizer.display_single_event.call_args[0]
        assert call_args[0]["content"] == "newer"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_last_n(self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show events --last N shows Nth most recent."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer
        mock_collect.return_value = [
            {"eventTimestamp": "2024-01-03T00:00:00Z", "content": "newest"},
            {"eventTimestamp": "2024-01-02T00:00:00Z", "content": "middle"},
            {"eventTimestamp": "2024-01-01T00:00:00Z", "content": "oldest"},
        ]

        result = runner.invoke(show_app, ["events", "--last", "2"])

        assert result.exit_code == 0
        call_args = mock_visualizer.display_single_event.call_args[0]
        assert call_args[0]["content"] == "middle"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_events_list_actors(self, mock_config, mock_manager_class):
        """Test show events --list-actors."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_actors.return_value = [{"actorId": "user1"}, {"actorId": "user2"}]

        result = runner.invoke(show_app, ["events", "--list-actors"])

        assert result.exit_code == 0
        assert "user1" in result.output
        assert "user2" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_events_list_sessions_requires_actor(self, mock_config, mock_manager_class):
        """Test show events --list-sessions requires --actor-id."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()

        result = runner.invoke(show_app, ["events", "--list-sessions"])

        assert result.exit_code == 1
        assert "--list-sessions requires --actor-id" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_events_session_requires_actor(self, mock_config, mock_manager_class):
        """Test show events --session-id requires --actor-id."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()

        result = runner.invoke(show_app, ["events", "--all", "--session-id", "sess-123"])

        assert result.exit_code == 1
        assert "--session-id requires --actor-id" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_events_all_and_last_conflict(self, mock_config, mock_manager_class):
        """Test show events --all and --last conflict."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()

        result = runner.invoke(show_app, ["events", "--all", "--last", "2"])

        assert result.exit_code == 1
        assert "Cannot use --all and --last together" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    def test_show_events_all_displays_tree(self, mock_visualizer_class, mock_config, mock_manager_class):
        """Test show events --all displays tree."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer

        result = runner.invoke(show_app, ["events", "--all"])

        assert result.exit_code == 0
        mock_visualizer.display_events_tree.assert_called_once()


class TestShowRecordsCommand:
    """Test the 'show records' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_default_shows_latest(
        self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class
    ):
        """Test show records shows latest record by default."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer
        mock_collect.return_value = [
            {"createdAt": "2024-01-02T00:00:00Z", "content": "newer"},
            {"createdAt": "2024-01-01T00:00:00Z", "content": "older"},
        ]

        result = runner.invoke(show_app, ["records"])

        assert result.exit_code == 0
        mock_visualizer.display_single_record.assert_called_once()
        call_args = mock_visualizer.display_single_record.call_args[0]
        assert call_args[0]["content"] == "newer"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_last_n(self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show records --last N shows Nth most recent."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer
        mock_collect.return_value = [
            {"createdAt": "2024-01-03T00:00:00Z", "content": "newest"},
            {"createdAt": "2024-01-02T00:00:00Z", "content": "middle"},
            {"createdAt": "2024-01-01T00:00:00Z", "content": "oldest"},
        ]

        result = runner.invoke(show_app, ["records", "--last", "2"])

        assert result.exit_code == 0
        call_args = mock_visualizer.display_single_record.call_args[0]
        assert call_args[0]["content"] == "middle"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_records_all_displays_tree(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show records --all displays tree."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer

        result = runner.invoke(show_app, ["records", "--all"])

        assert result.exit_code == 0
        mock_visualizer.display_records_tree.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_records_all_with_namespace_errors(self, mock_config, mock_manager_class):
        """Test show records --all with --namespace errors."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()

        result = runner.invoke(show_app, ["records", "--all", "--namespace", "/test/"])

        assert result.exit_code == 1
        assert "Use --namespace without --all" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_records_namespace_drills_down(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show records --namespace drills into namespace."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer

        result = runner.invoke(show_app, ["records", "--namespace", "/summaries/user/sess"])

        assert result.exit_code == 0
        mock_visualizer.display_namespace_records.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_records_query_requires_namespace(self, mock_config, mock_manager_class):
        """Test show records --query requires --namespace."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()

        result = runner.invoke(show_app, ["records", "--query", "test"])

        assert result.exit_code == 1
        assert "--namespace required for semantic search" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_records_query_with_namespace(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show records --query with --namespace performs search."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search_records.return_value = [{"content": "match"}]
        mock_visualizer = MagicMock()
        mock_visualizer_class.return_value = mock_visualizer

        result = runner.invoke(show_app, ["records", "--namespace", "/test/", "--query", "search term"])

        assert result.exit_code == 0
        mock_manager.search_records.assert_called_once()
        mock_visualizer.display_search_results.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_records_all_and_last_conflict(self, mock_config, mock_manager_class):
        """Test show records --all and --last conflict."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()

        result = runner.invoke(show_app, ["records", "--all", "--last", "2"])

        assert result.exit_code == 1
        assert "Cannot use --all and --last together" in result.output


class TestConfigResolution:
    """Test config resolution patterns."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_no_config_no_memory_id_errors(self, mock_config):
        """Test error when no config and no memory_id."""
        mock_config.return_value = _mock_config(config_exists=False)

        result = runner.invoke(show_app, ["events"])

        assert result.exit_code == 1
        assert "No memory specified" in result.output
        assert "no .bedrock_agentcore.yaml found" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_config_exists_but_no_memory_id_errors(self, mock_config):
        """Test error when config exists but no memory_id configured."""
        mock_config.return_value = _mock_config(config_exists=True, agent_name="my-agent")

        result = runner.invoke(show_app, ["events"])

        assert result.exit_code == 1
        assert "Found .bedrock_agentcore.yaml" in result.output
        assert "'my-agent' has no memory_id configured" in result.output
        assert "agentcore launch" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_region_from_config(self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class):
        """Test region is taken from config."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="eu-west-1")
        mock_collect.return_value = [{"eventTimestamp": "2024-01-01T00:00:00Z"}]
        mock_visualizer_class.return_value = MagicMock()

        runner.invoke(show_app, ["events"])

        mock_manager_class.assert_called_once()
        call_kwargs = mock_manager_class.call_args[1]
        assert call_kwargs["region_name"] == "eu-west-1"


class TestGetMemoryConfigFromFile:
    """Test _get_memory_config_from_file function."""

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists")
    def test_no_config_file(self, mock_load):
        """Test when no config file exists."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _get_memory_config_from_file

        mock_load.return_value = None
        result = _get_memory_config_from_file("test-agent")
        assert result.config_exists is False
        assert result.memory_id is None

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists")
    def test_config_without_memory(self, mock_load):
        """Test when config exists but has no memory."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _get_memory_config_from_file

        mock_config = MagicMock()
        mock_config.default_agent = "default"
        mock_agent_config = MagicMock()
        mock_agent_config.memory = None
        mock_agent_config.aws.region = "us-east-1"
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_load.return_value = mock_config

        result = _get_memory_config_from_file("test-agent")
        assert result.config_exists is True
        assert result.memory_id is None

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists")
    def test_config_with_memory(self, mock_load):
        """Test when config has memory."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _get_memory_config_from_file

        mock_config = MagicMock()
        mock_config.default_agent = "default"
        mock_agent_config = MagicMock()
        mock_agent_config.memory.memory_id = "mem-123"
        mock_agent_config.aws.region = "us-west-2"
        mock_config.get_agent_config.return_value = mock_agent_config
        mock_load.return_value = mock_config

        result = _get_memory_config_from_file("test-agent")
        assert result.config_exists is True
        assert result.memory_id == "mem-123"
        assert result.region == "us-west-2"

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists")
    def test_config_exception(self, mock_load):
        """Test when config loading raises exception."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _get_memory_config_from_file

        mock_config = MagicMock()
        mock_config.get_agent_config.side_effect = Exception("Config error")
        mock_load.return_value = mock_config

        result = _get_memory_config_from_file("test-agent")
        assert result.config_exists is True
        assert result.memory_id is None


class TestShowEventsEdgeCases:
    """Test edge cases for show events command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_events_list_sessions(self, mock_config, mock_manager_class):
        """Test show events --list-sessions with --actor-id."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.list_sessions.return_value = [{"sessionId": "sess1"}, {"sessionId": "sess2"}]

        result = runner.invoke(show_app, ["events", "--list-sessions", "--actor-id", "user1"])

        assert result.exit_code == 0
        assert "sess1" in result.output
        assert "sess2" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_no_events(self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show events when no events found."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_collect.return_value = []

        result = runner.invoke(show_app, ["events"])

        assert result.exit_code == 0
        assert "No events found" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_last_exceeds_count(self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show events --last N when N exceeds event count."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_collect.return_value = [{"eventTimestamp": "2024-01-01T00:00:00Z"}]

        result = runner.invoke(show_app, ["events", "--last", "5"])

        assert result.exit_code == 0
        assert "Only 1 events found" in result.output


class TestShowRecordsEdgeCases:
    """Test edge cases for show records command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_no_records(self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show records when no records found."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_collect.return_value = []

        result = runner.invoke(show_app, ["records"])

        assert result.exit_code == 0
        assert "No records found" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_last_exceeds_count(
        self, mock_collect, mock_config, mock_manager_class, mock_visualizer_class
    ):
        """Test show records --last N when N exceeds record count."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager_class.return_value = MagicMock()
        mock_collect.return_value = [{"createdAt": "2024-01-01T00:00:00Z"}]

        result = runner.invoke(show_app, ["records", "--last", "5"])

        assert result.exit_code == 0
        assert "Only 1 records found" in result.output

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryVisualizer")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_show_records_query_no_results(self, mock_config, mock_manager_class, mock_visualizer_class):
        """Test show records --query with no results."""
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-east-1")
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search_records.return_value = []

        result = runner.invoke(show_app, ["records", "--namespace", "/test/", "--query", "nonexistent"])

        assert result.exit_code == 0
        assert "No matching records" in result.output


class TestCollectAllEvents:
    """Test _collect_all_events function."""

    def test_collect_events_basic(self):
        """Test collecting events from actors and sessions."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_all_events

        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        manager.list_events.return_value = [{"eventId": "e1", "eventTimestamp": "2024-01-01T00:00:00Z"}]

        events = _collect_all_events(manager, "mem-123")

        assert len(events) == 1
        assert events[0]["_actorId"] == "user1"
        assert events[0]["_sessionId"] == "sess1"

    def test_collect_events_skips_missing_actor_id(self):
        """Test that actors without actorId are skipped."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_all_events

        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}, {}]  # Second actor has no actorId
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        manager.list_events.return_value = [{"eventId": "e1"}]

        events = _collect_all_events(manager, "mem-123")

        assert len(events) == 1

    def test_collect_events_skips_missing_session_id(self):
        """Test that sessions without sessionId are skipped."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_all_events

        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}, {}]  # Second session has no sessionId
        manager.list_events.return_value = [{"eventId": "e1"}]

        events = _collect_all_events(manager, "mem-123")

        assert len(events) == 1


class TestCollectAllRecords:
    """Test _collect_all_records function."""

    def test_collect_records_with_namespace(self):
        """Test collecting records from a specific namespace."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_all_records

        manager = MagicMock()
        manager.list_records.return_value = [{"memoryRecordId": "r1", "content": {"text": "test"}}]

        records = _collect_all_records(manager, "mem-123", "/test/", 10)

        assert len(records) == 1
        assert records[0]["_namespace"] == "/test/"

    def test_collect_records_all_namespaces(self):
        """Test collecting records from all namespaces."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_all_records

        manager = MagicMock()
        manager.get_memory.return_value = {"strategies": [{"name": "Facts", "namespaces": ["/facts/"]}]}
        manager.list_records.return_value = [{"memoryRecordId": "r1"}]
        manager.list_actors.return_value = []

        records = _collect_all_records(manager, "mem-123", None, 10)

        assert len(records) == 1


class TestCollectRecordsFromNamespaceTemplate:
    """Test _collect_records_from_namespace_template function."""

    def test_static_namespace(self):
        """Test collecting from static namespace."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_records_from_namespace_template

        manager = MagicMock()
        manager.list_records.return_value = [{"memoryRecordId": "r1"}]
        all_records = []

        _collect_records_from_namespace_template(manager, "mem-123", "/facts/", 10, all_records)

        assert len(all_records) == 1

    def test_actor_template(self):
        """Test collecting from actor template namespace."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_records_from_namespace_template

        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_records.return_value = [{"memoryRecordId": "r1"}]
        all_records = []

        _collect_records_from_namespace_template(manager, "mem-123", "/users/{actorId}/facts/", 10, all_records)

        assert len(all_records) == 1

    def test_session_template(self):
        """Test collecting from session template namespace."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_records_from_namespace_template

        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        manager.list_records.return_value = [{"memoryRecordId": "r1"}]
        all_records = []

        _collect_records_from_namespace_template(
            manager, "mem-123", "/users/{actorId}/sessions/{sessionId}/", 10, all_records
        )

        assert len(all_records) == 1

    def test_template_error_handling(self):
        """Test error handling in template resolution."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _collect_records_from_namespace_template

        manager = MagicMock()
        manager.list_actors.side_effect = Exception("API error")
        all_records = []

        _collect_records_from_namespace_template(manager, "mem-123", "/users/{actorId}/facts/", 10, all_records)

        assert len(all_records) == 0


class TestTryCollectRecords:
    """Test _try_collect_records function."""

    def test_successful_collection(self):
        """Test successful record collection."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _try_collect_records

        manager = MagicMock()
        manager.list_records.return_value = [{"memoryRecordId": "r1"}]
        all_records = []

        _try_collect_records(manager, "mem-123", "/test/", 10, all_records)

        assert len(all_records) == 1
        assert all_records[0]["_namespace"] == "/test/"

    def test_error_handling(self):
        """Test error handling in record collection."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _try_collect_records

        manager = MagicMock()
        manager.list_records.side_effect = Exception("API error")
        all_records = []

        _try_collect_records(manager, "mem-123", "/test/", 10, all_records)

        assert len(all_records) == 0


class TestResolveMemoryConfig:
    """Test _resolve_memory_config function."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("boto3.Session")
    def test_resolve_with_explicit_memory_id(self, mock_session, mock_config):
        """Test resolve with explicit memory_id."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _resolve_memory_config

        mock_session.return_value.region_name = "us-east-1"

        result = _resolve_memory_config(memory_id="mem-123", region="us-west-2")

        assert result.memory_id == "mem-123"
        assert result.region == "us-west-2"
        mock_config.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("boto3.Session")
    def test_resolve_from_config(self, mock_session, mock_config):
        """Test resolve from config."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _resolve_memory_config

        mock_config.return_value = _mock_config(memory_id="config-mem", region="eu-west-1")

        result = _resolve_memory_config(show_hint=False)

        assert result.memory_id == "config-mem"
        assert result.region == "eu-west-1"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("boto3.Session")
    def test_resolve_region_from_boto(self, mock_session_class, mock_config):
        """Test resolve region from boto session."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _resolve_memory_config

        mock_config.return_value = _mock_config(memory_id="config-mem")
        mock_session = MagicMock()
        mock_session.region_name = "ap-southeast-1"
        mock_session_class.return_value = mock_session

        result = _resolve_memory_config(show_hint=False)

        assert result.region == "ap-southeast-1"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("boto3.Session")
    def test_resolve_with_agent_name(self, mock_session, mock_config):
        """Test resolve with agent name."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _resolve_memory_config

        mock_config.return_value = _mock_config(memory_id="agent-mem", region="us-east-1")

        result = _resolve_memory_config(agent="my-agent", show_hint=False)

        assert result.memory_id == "agent-mem"
        mock_config.assert_called_once_with("my-agent")

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("boto3.Session")
    def test_resolve_config_region_not_overridden(self, mock_session, mock_config):
        """Test config region is used when no explicit region."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _resolve_memory_config

        mock_config.return_value = _mock_config(memory_id="config-mem", region="config-region")

        result = _resolve_memory_config(show_hint=False)

        assert result.region == "config-region"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("boto3.Session")
    def test_resolve_explicit_region_overrides_config(self, mock_session, mock_config):
        """Test explicit region overrides config region."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _resolve_memory_config

        mock_config.return_value = _mock_config(memory_id="config-mem", region="config-region")

        result = _resolve_memory_config(region="explicit-region", show_hint=False)

        assert result.region == "explicit-region"

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    @patch("boto3.Session")
    def test_resolve_explicit_memory_id_overrides_config(self, mock_session, mock_config):
        """Test explicit memory_id overrides config."""
        from bedrock_agentcore_starter_toolkit.cli.memory.commands import _resolve_memory_config

        mock_config.return_value = _mock_config(memory_id="config-mem", region="us-east-1")

        result = _resolve_memory_config(memory_id="explicit-mem", show_hint=False)

        assert result.memory_id == "explicit-mem"


class TestBrowseCommand:
    """Test the browse command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.browser.MemoryBrowser")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_browse_success(self, mock_config, mock_manager_class, mock_browser_class):
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-west-2")
        mock_manager = mock_manager_class.return_value
        mock_manager.get_memory.return_value = {"id": "mem-123"}

        result = runner.invoke(memory_app, ["browse", "--memory-id", "mem-123", "--region", "us-west-2"])

        assert result.exit_code == 0
        mock_browser_class.assert_called_once()
        mock_browser_class.return_value.run.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_browse_auth_error(self, mock_config, mock_manager_class):
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-west-2")
        mock_manager_class.return_value.get_memory.side_effect = Exception("Token expired")

        result = runner.invoke(memory_app, ["browse", "--memory-id", "mem-123", "--region", "us-west-2"])

        assert result.exit_code == 1

    @patch("bedrock_agentcore_starter_toolkit.cli.memory.browser.MemoryBrowser")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_browse_passes_initial_memory(self, mock_config, mock_manager_class, mock_browser_class):
        mock_config.return_value = _mock_config(memory_id="mem-123", region="us-west-2")
        memory_data = {"id": "mem-123", "strategies": []}
        mock_manager_class.return_value.get_memory.return_value = memory_data

        runner.invoke(memory_app, ["browse", "--memory-id", "mem-123", "--region", "us-west-2"])

        mock_browser_class.assert_called_once()
        call_kwargs = mock_browser_class.call_args
        assert call_kwargs.kwargs.get("initial_memory") == memory_data
