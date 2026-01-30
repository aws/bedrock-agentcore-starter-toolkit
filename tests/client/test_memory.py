"""Tests for Memory notebook interface."""

from unittest.mock import MagicMock, patch

import pytest

from bedrock_agentcore_starter_toolkit.notebook import Memory


class TestResolveMemoryConfig:
    """Test _resolve_memory_config function."""

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory.MemoryManager")
    @patch("boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_resolve_with_memory_id(self, mock_get_config, mock_session, mock_manager):
        """Test resolve with explicit memory_id."""
        from bedrock_agentcore_starter_toolkit.notebook.memory.memory import _resolve_memory_config

        memory_id, region, manager, console = _resolve_memory_config(memory_id="mem-123", region="us-east-1")

        assert memory_id == "mem-123"
        assert region == "us-east-1"
        mock_get_config.assert_not_called()

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory.MemoryManager")
    @patch("boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_resolve_from_config(self, mock_get_config, mock_session, mock_manager):
        """Test resolve from config file."""
        from bedrock_agentcore_starter_toolkit.notebook.memory.memory import _resolve_memory_config

        mock_get_config.return_value = {"memory_id": "config-mem", "region": "us-west-2"}

        memory_id, region, manager, console = _resolve_memory_config(agent_name="my-agent")

        assert memory_id == "config-mem"
        assert region == "us-west-2"

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory.MemoryManager")
    @patch("boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_resolve_region_from_session(self, mock_get_config, mock_session_class, mock_manager):
        """Test resolve region from boto session."""
        from bedrock_agentcore_starter_toolkit.notebook.memory.memory import _resolve_memory_config

        mock_session = MagicMock()
        mock_session.region_name = "eu-west-1"
        mock_session_class.return_value = mock_session
        mock_get_config.return_value = None

        memory_id, region, manager, console = _resolve_memory_config(memory_id="mem-123")

        assert region == "eu-west-1"

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory.MemoryManager")
    @patch("boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_resolve_no_memory_id_raises(self, mock_get_config, mock_session, mock_manager):
        """Test resolve raises when no memory_id found."""
        from bedrock_agentcore_starter_toolkit.notebook.memory.memory import _resolve_memory_config

        mock_get_config.return_value = None

        with pytest.raises(ValueError, match="No memory_id specified"):
            _resolve_memory_config()

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory.MemoryManager")
    @patch("boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_resolve_config_without_region(self, mock_get_config, mock_session_class, mock_manager):
        """Test resolve when config has memory_id but no region."""
        from bedrock_agentcore_starter_toolkit.notebook.memory.memory import _resolve_memory_config

        mock_get_config.return_value = {"memory_id": "config-mem"}
        mock_session = MagicMock()
        mock_session.region_name = "ap-south-1"
        mock_session_class.return_value = mock_session

        memory_id, region, manager, console = _resolve_memory_config(agent_name="my-agent")

        assert memory_id == "config-mem"
        assert region == "ap-south-1"

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory.MemoryManager")
    @patch("boto3.Session")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._get_memory_config_from_file")
    def test_resolve_config_with_region_already_set(self, mock_get_config, mock_session_class, mock_manager):
        """Test resolve when region is already set and config also has region."""
        from bedrock_agentcore_starter_toolkit.notebook.memory.memory import _resolve_memory_config

        mock_get_config.return_value = {"memory_id": "config-mem", "region": "us-west-2"}

        memory_id, region, manager, console = _resolve_memory_config(agent_name="my-agent", region="eu-west-1")

        assert memory_id == "config-mem"
        assert region == "eu-west-1"  # Explicit region takes precedence


class TestMemoryInit:
    """Test Memory client initialization."""

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_init_with_memory_id(self, mock_resolve):
        """Test initialization with memory_id."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mem = Memory(memory_id="mem-123", region="us-east-1")

        assert mem.memory_id == "mem-123"
        assert mem.region == "us-east-1"
        assert mem.manager == mock_manager
        mock_resolve.assert_called_once_with(None, "mem-123", "us-east-1")

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_init_with_agent_name(self, mock_resolve):
        """Test initialization with agent_name."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("config-mem", "us-west-2", mock_manager, mock_console)

        mem = Memory(agent_name="my-agent")

        assert mem.memory_id == "config-mem"
        mock_resolve.assert_called_once_with("my-agent", None, None)


class TestMemoryShow:
    """Test show() method."""

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_returns_memory_data(self, mock_resolve):
        """Test show returns memory data dict."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_memory = MagicMock()
        mock_memory.items.return_value = [("memoryId", "mem-123"), ("status", "ACTIVE")]
        mock_manager.get_memory.return_value = mock_memory

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show()

        assert result["memoryId"] == "mem-123"
        mock_manager.get_memory.assert_called_once_with("mem-123")

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_with_data_attribute(self, mock_resolve):
        """Test show with _data attribute fallback."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_memory = MagicMock(spec=[])
        mock_memory._data = {"memoryId": "mem-123"}
        del mock_memory.items
        mock_manager.get_memory.return_value = mock_memory

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show()

        assert result["memoryId"] == "mem-123"


class TestMemoryShowEvents:
    """Test show_events() method."""

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_default_returns_latest(self, mock_collect, mock_resolve):
        """Test show_events returns latest event by default."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = [
            {"eventTimestamp": "2024-01-02T00:00:00Z", "content": "newer"},
            {"eventTimestamp": "2024-01-01T00:00:00Z", "content": "older"},
        ]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_events()

        assert len(result) == 1
        assert result[0]["content"] == "newer"

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_no_events(self, mock_collect, mock_resolve):
        """Test show_events with no events."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = []

        mem = Memory(memory_id="mem-123")
        result = mem.show_events()

        assert result == []

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_last_exceeds_count(self, mock_collect, mock_resolve):
        """Test show_events when last exceeds event count."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = [{"eventTimestamp": "2024-01-01T00:00:00Z"}]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_events(last=10)

        assert len(result) == 1

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_events_list_actors(self, mock_resolve):
        """Test show_events with list_actors."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_manager.list_actors.return_value = [{"actorId": "user1"}, {"actorId": "user2"}]

        mem = Memory(memory_id="mem-123")
        result = mem.show_events(list_actors=True)

        assert len(result) == 2
        mock_manager.list_actors.assert_called_once_with("mem-123")

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_events_list_sessions(self, mock_resolve):
        """Test show_events with list_sessions."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_manager.list_sessions.return_value = [{"sessionId": "sess-1"}]

        mem = Memory(memory_id="mem-123")
        result = mem.show_events(list_sessions=True, actor_id="user1")

        assert len(result) == 1
        mock_manager.list_sessions.assert_called_once_with("mem-123", "user1")

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_events_list_sessions_requires_actor(self, mock_resolve):
        """Test show_events list_sessions requires actor_id."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mem = Memory(memory_id="mem-123")

        with pytest.raises(ValueError, match="list_sessions requires actor_id"):
            mem.show_events(list_sessions=True)

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_events")
    def test_show_events_all(self, mock_collect, mock_resolve):
        """Test show_events with all=True."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = [{"eventId": "e1"}, {"eventId": "e2"}]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_events(all=True)

        assert len(result) == 2
        mock_visualizer.display_events_tree.assert_called_once()


class TestMemoryShowRecords:
    """Test show_records() method."""

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_default_returns_latest(self, mock_collect, mock_resolve):
        """Test show_records returns latest record by default."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = [
            {"createdAt": "2024-01-02T00:00:00Z", "content": "newer"},
            {"createdAt": "2024-01-01T00:00:00Z", "content": "older"},
        ]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_records()

        assert len(result) == 1
        assert result[0]["content"] == "newer"

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_no_records(self, mock_collect, mock_resolve):
        """Test show_records with no records."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = []

        mem = Memory(memory_id="mem-123")
        result = mem.show_records()

        assert result == []

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_last_exceeds_count(self, mock_collect, mock_resolve):
        """Test show_records when last exceeds record count."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = [{"createdAt": "2024-01-01T00:00:00Z"}]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_records(last=10)

        assert len(result) == 1

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    @patch("bedrock_agentcore_starter_toolkit.cli.memory.commands._collect_all_records")
    def test_show_records_all(self, mock_collect, mock_resolve):
        """Test show_records with all=True."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_collect.return_value = [{"recordId": "r1"}]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_records(all=True)

        assert len(result) == 1
        mock_visualizer.display_records_tree.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_records_all_with_namespace_raises(self, mock_resolve):
        """Test show_records all=True with namespace raises error."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mem = Memory(memory_id="mem-123")

        with pytest.raises(ValueError, match="Use namespace without all"):
            mem.show_records(all=True, namespace="/some/path/")

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_records_namespace_only(self, mock_resolve):
        """Test show_records with namespace filter."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_manager.list_records.return_value = [{"recordId": "r1"}]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_records(namespace="/test/ns/")

        assert len(result) == 1
        # Namespace is passed through as-is
        mock_manager.list_records.assert_called_once_with("mem-123", "/test/ns/", 10)

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_records_query_requires_namespace(self, mock_resolve):
        """Test show_records query requires namespace."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mem = Memory(memory_id="mem-123")

        with pytest.raises(ValueError, match="namespace required for semantic search"):
            mem.show_records(query="test query")

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_records_with_query(self, mock_resolve):
        """Test show_records with semantic search."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_manager.search_records.return_value = [{"content": "match"}]

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_records(namespace="/test/", query="search term")

        assert len(result) == 1
        # Namespace is passed through as-is
        mock_manager.search_records.assert_called_once_with("mem-123", "/test/", "search term", 10)

    @patch("bedrock_agentcore_starter_toolkit.notebook.memory.memory._resolve_memory_config")
    def test_show_records_query_no_results(self, mock_resolve):
        """Test show_records query with no results."""
        mock_manager = MagicMock()
        mock_console = MagicMock()
        mock_visualizer = MagicMock()
        mock_resolve.return_value = ("mem-123", "us-east-1", mock_manager, mock_console)

        mock_manager.search_records.return_value = []

        mem = Memory(memory_id="mem-123")
        mem.visualizer = mock_visualizer
        result = mem.show_records(namespace="/test/", query="no match")

        assert result == []
        mock_visualizer.display_search_results.assert_not_called()
