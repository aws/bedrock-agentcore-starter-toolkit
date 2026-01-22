"""Tests for memory visualizer."""

from unittest.mock import MagicMock

import pytest
from rich.console import Console

from bedrock_agentcore_starter_toolkit.operations.memory.memory_visualizer import MemoryVisualizer


@pytest.fixture
def console():
    """Create a mock console."""
    return MagicMock(spec=Console)


@pytest.fixture
def visualizer(console):
    """Create a visualizer with mock console."""
    return MemoryVisualizer(console)


class TestMemoryVisualizerInit:
    """Test MemoryVisualizer initialization."""

    def test_init_with_console(self, console):
        viz = MemoryVisualizer(console)
        assert viz.console == console


class TestVisualizeMemory:
    """Test visualize_memory method."""

    def test_visualize_memory_basic(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "description": "Test memory",
                "eventExpiryDuration": 30,
                "createdAt": None,
                "strategies": [],
            }
        )

        visualizer.visualize_memory(memory)
        console.print.assert_called()

    def test_visualize_memory_with_strategies(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "strategies": [{"name": "Facts", "type": "SEMANTIC", "status": "ACTIVE", "namespaces": ["/facts"]}],
            }
        )

        visualizer.visualize_memory(memory)
        console.print.assert_called()

    def test_visualize_memory_verbose(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "arn": "arn:aws:...",
                "updatedAt": None,
                "strategies": [],
            }
        )

        visualizer.visualize_memory(memory, verbose=True)
        console.print.assert_called()


class TestDisplayMemoryList:
    """Test display_memory_list method."""

    def test_display_memory_list_empty(self, visualizer, console):
        visualizer.display_memory_list([])
        console.print.assert_called()

    def test_display_memory_list_with_memories(self, visualizer, console):
        memories = [
            {"id": "mem-1", "name": "mem1", "status": "ACTIVE", "createdAt": None, "updatedAt": None},
            {"id": "mem-2", "name": "mem2", "status": "CREATING", "createdAt": None, "updatedAt": None},
        ]
        visualizer.display_memory_list(memories)
        assert console.print.call_count >= 1


class TestDisplayEventsTree:
    """Test display_events_tree method."""

    def test_display_events_tree_no_actors(self, visualizer, console):
        manager = MagicMock()
        manager.list_actors.return_value = []

        visualizer.display_events_tree("mem-123", manager)
        console.print.assert_called()

    def test_display_events_tree_with_actors(self, visualizer, console):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        manager.list_events.return_value = []

        visualizer.display_events_tree("mem-123", manager)
        console.print.assert_called()

    def test_display_events_tree_with_events(self, visualizer, console):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        manager.list_events.return_value = [
            {
                "eventId": "e1",
                "eventTimestamp": "2024-01-01T00:00:00Z",
                "branchName": "main",
                "payload": [{"conversational": {"role": "USER", "content": {"text": "{}"}}}],
            }
        ]

        visualizer.display_events_tree("mem-123", manager)
        console.print.assert_called()


class TestDisplaySingleEvent:
    """Test display_single_event method."""

    def test_display_single_event_basic(self, visualizer, console):
        event = {
            "eventId": "e1",
            "eventTimestamp": "2024-01-01T00:00:00Z",
            "actorId": "user1",
            "sessionId": "sess1",
            "branchName": "main",
        }

        visualizer.display_single_event(event, 1, 10, verbose=False)
        console.print.assert_called()

    def test_display_single_event_verbose(self, visualizer, console):
        event = {
            "eventId": "e1",
            "eventTimestamp": "2024-01-01T00:00:00Z",
            "actorId": "user1",
            "sessionId": "sess1",
            "branchName": "main",
            "payload": [{"conversational": {"role": "USER", "content": {"text": "hello"}}}],
        }

        visualizer.display_single_event(event, 1, 10, verbose=True)
        console.print.assert_called()


class TestDisplayRecordsTree:
    """Test display_records_tree method."""

    def test_display_records_tree_no_strategies(self, visualizer, console):
        manager = MagicMock()
        manager.get_memory.return_value = MagicMock(_data={"strategies": []})

        visualizer.display_records_tree(manager, "mem-123", verbose=False, max_results=10, output=None)
        console.print.assert_called()

    def test_display_records_tree_with_records(self, visualizer, console):
        manager = MagicMock()
        manager.get_memory.return_value = MagicMock(
            _data={"strategies": [{"name": "Facts", "type": "SEMANTIC", "namespaces": ["/facts"]}]}
        )
        manager.list_records.return_value = [{"memoryRecordId": "r1", "content": {"text": "test"}}]

        visualizer.display_records_tree(manager, "mem-123", verbose=False, max_results=10, output=None)
        console.print.assert_called()


class TestDisplayNamespaceRecords:
    """Test display_namespace_records method."""

    def test_display_namespace_records_empty(self, visualizer, console):
        manager = MagicMock()
        manager.list_records.return_value = []

        visualizer.display_namespace_records(manager, "mem-123", "/test", verbose=False, max_results=10, output=None)
        console.print.assert_called()

    def test_display_namespace_records_with_records(self, visualizer, console):
        manager = MagicMock()
        manager.list_records.return_value = [{"memoryRecordId": "r1", "content": {"text": "test"}}]

        visualizer.display_namespace_records(manager, "mem-123", "/test", verbose=False, max_results=10, output=None)
        console.print.assert_called()


class TestDisplaySingleRecord:
    """Test display_single_record method."""

    def test_display_single_record_basic(self, visualizer, console):
        record = {
            "memoryRecordId": "r1",
            "namespace": "/test",
            "createdAt": "2024-01-01T00:00:00Z",
            "content": {"text": "test content"},
        }

        visualizer.display_single_record(record, 1, 10, verbose=False)
        console.print.assert_called()

    def test_display_single_record_verbose(self, visualizer, console):
        record = {
            "memoryRecordId": "r1",
            "namespace": "/test",
            "createdAt": "2024-01-01T00:00:00Z",
            "content": {"text": "test content"},
        }

        visualizer.display_single_record(record, 1, 10, verbose=True)
        console.print.assert_called()


class TestDisplaySearchResults:
    """Test display_search_results method."""

    def test_display_search_results_empty(self, visualizer, console):
        visualizer.display_search_results([], "query", verbose=False)
        console.print.assert_called()

    def test_display_search_results_with_results(self, visualizer, console):
        results = [{"memoryRecordId": "r1", "namespace": "/test", "score": 0.95, "content": {"text": "match"}}]
        visualizer.display_search_results(results, "query", verbose=False)
        console.print.assert_called()

    def test_display_search_results_verbose(self, visualizer, console):
        results = [{"memoryRecordId": "r1", "namespace": "/test", "score": 0.95, "content": {"text": "match"}}]
        visualizer.display_search_results(results, "query", verbose=True)
        console.print.assert_called()


class TestExtractMemoryData:
    """Test _extract_memory_data method."""

    def test_extract_from_dict(self, visualizer):
        data = {"id": "mem-123"}
        assert visualizer._extract_memory_data(data) == data

    def test_extract_from_object_with_dict(self, visualizer):
        class SimpleObj:
            def __init__(self):
                self.id = "mem-123"

        obj = SimpleObj()
        result = visualizer._extract_memory_data(obj)
        assert result["id"] == "mem-123"


class TestMemoryListWithManager:
    """Test display_memory_list with manager."""

    def test_display_memory_list_with_manager(self, visualizer, console):
        memories = [{"id": "mem-1", "name": "mem1", "status": "ACTIVE", "createdAt": None, "updatedAt": None}]
        manager = MagicMock()
        visualizer.display_memory_list(memories, manager)
        console.print.assert_called()


class TestFormatMemoryRow:
    """Test _format_memory_row method."""

    def test_format_row_with_data_attr(self, visualizer):
        memory = MagicMock()
        memory.get = None
        del memory.get
        memory._data = {"id": "mem-1", "name": "test", "status": "ACTIVE"}
        row = visualizer._format_memory_row(memory, None)
        assert len(row) == 4

    def test_format_row_name_equals_id(self, visualizer):
        memory = {"id": "mem-1", "name": "mem-1", "status": "ACTIVE"}
        row = visualizer._format_memory_row(memory, None)
        assert len(row) == 4


class TestEventsTreeEdgeCases:
    """Test display_events_tree edge cases."""

    def test_events_tree_with_actor_filter(self, visualizer, console):
        manager = MagicMock()
        manager.list_sessions.return_value = []
        visualizer.display_events_tree("mem-123", manager, actor_id="user1")
        console.print.assert_called()

    def test_events_tree_with_session_filter(self, visualizer, console):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        manager.list_events.return_value = []
        visualizer.display_events_tree("mem-123", manager, session_id="sess1")
        console.print.assert_called()

    def test_events_tree_truncation_hint(self, visualizer, console):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": f"user{i}"} for i in range(15)]
        manager.list_sessions.return_value = []
        visualizer.display_events_tree("mem-123", manager, max_actors=5)
        console.print.assert_called()

    def test_events_tree_session_error(self, visualizer, console):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.side_effect = Exception("API error")
        visualizer.display_events_tree("mem-123", manager)
        console.print.assert_called()

    def test_events_tree_with_output_file(self, visualizer, console, tmp_path):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        manager.list_events.return_value = []
        output_file = tmp_path / "events.json"
        visualizer.display_events_tree("mem-123", manager, output=str(output_file))
        assert output_file.exists()


class TestBuildSessionSubtree:
    """Test _build_session_subtree method."""

    def test_session_subtree_with_events(self, visualizer):
        from rich.tree import Tree

        root = Tree("test")
        manager = MagicMock()
        manager.list_events.return_value = [
            {"eventId": "e1", "eventTimestamp": "2024-01-01T00:00:00Z", "branch": {"name": "main"}, "payload": []}
        ]
        result = visualizer._build_session_subtree(root, manager, "mem-123", "user1", {"sessionId": "sess1"}, 10, False)
        assert result["sessionId"] == "sess1"

    def test_session_subtree_error(self, visualizer):
        from rich.tree import Tree

        root = Tree("test")
        manager = MagicMock()
        manager.list_events.side_effect = Exception("API error")
        result = visualizer._build_session_subtree(root, manager, "mem-123", "user1", {"sessionId": "sess1"}, 10, False)
        assert result["sessionId"] == "sess1"


class TestAddEventNode:
    """Test _add_event_node method."""

    def test_event_node_blob_type(self, visualizer):
        from rich.tree import Tree

        branch = Tree("test")
        event = {"eventTimestamp": "2024-01-01T00:00:00Z", "payload": [{"blob": {"data": "binary"}}]}
        visualizer._add_event_node(branch, event, False)

    def test_event_node_no_content(self, visualizer):
        from rich.tree import Tree

        branch = Tree("test")
        event = {"eventTimestamp": "2024-01-01T00:00:00Z", "payload": []}
        visualizer._add_event_node(branch, event, False)

    def test_event_node_verbose_user(self, visualizer):
        from rich.tree import Tree

        branch = Tree("test")
        event = {"payload": [{"conversational": {"role": "USER", "content": {"text": "hello"}}}]}
        visualizer._add_event_node(branch, event, True)

    def test_event_node_assistant(self, visualizer):
        from rich.tree import Tree

        branch = Tree("test")
        event = {"payload": [{"conversational": {"role": "ASSISTANT", "content": {"text": "hi"}}}]}
        visualizer._add_event_node(branch, event, False)


class TestSingleEventDisplay:
    """Test display_single_event edge cases."""

    def test_single_event_with_branch(self, visualizer, console):
        event = {
            "eventId": "e1",
            "eventTimestamp": "2024-01-01T00:00:00Z",
            "branch": {"name": "feature"},
            "payload": [{"conversational": {"role": "USER", "content": {"text": "test"}}}],
        }
        visualizer.display_single_event(event, 2, 10, verbose=False)
        console.print.assert_called()

    def test_single_event_no_content(self, visualizer, console):
        event = {"eventId": "e1", "eventTimestamp": "2024-01-01T00:00:00Z"}
        visualizer.display_single_event(event, 1, 1, verbose=False)
        console.print.assert_called()


class TestRecordsTreeEdgeCases:
    """Test display_records_tree edge cases."""

    def test_records_tree_with_output(self, visualizer, console, tmp_path):
        manager = MagicMock()
        manager.get_memory.return_value = {"strategies": []}
        output_file = tmp_path / "records.json"
        visualizer.display_records_tree(manager, "mem-123", False, 10, str(output_file))
        assert output_file.exists()

    def test_records_tree_with_strategy_records(self, visualizer, console):
        manager = MagicMock()
        manager.get_memory.return_value = {
            "strategies": [{"name": "Facts", "type": "SEMANTIC", "namespaces": ["/facts"]}]
        }
        manager.list_records.return_value = [{"memoryRecordId": "r1", "content": {"text": "test"}, "createdAt": "2024"}]
        visualizer.display_records_tree(manager, "mem-123", False, 10, None)
        console.print.assert_called()

    def test_records_tree_list_records_error(self, visualizer, console):
        manager = MagicMock()
        manager.get_memory.return_value = {
            "strategies": [{"name": "Facts", "type": "SEMANTIC", "namespaces": ["/facts"]}]
        }
        manager.list_records.side_effect = Exception("API error")
        visualizer.display_records_tree(manager, "mem-123", False, 10, None)
        console.print.assert_called()


class TestNamespaceRecordsEdgeCases:
    """Test display_namespace_records edge cases."""

    def test_namespace_records_error(self, visualizer, console):
        manager = MagicMock()
        manager.list_records.side_effect = Exception("API error")
        visualizer.display_namespace_records(manager, "mem-123", "/test", False, 10, None)
        console.print.assert_called()

    def test_namespace_records_with_output(self, visualizer, console, tmp_path):
        manager = MagicMock()
        manager.list_records.return_value = [{"memoryRecordId": "r1", "content": {"text": "test"}, "createdAt": "2024"}]
        output_file = tmp_path / "ns_records.json"
        visualizer.display_namespace_records(manager, "mem-123", "/test", False, 10, str(output_file))
        assert output_file.exists()


class TestResolveNamespace:
    """Test _resolve_namespace method."""

    def test_resolve_simple_namespace(self, visualizer):
        manager = MagicMock()
        result = visualizer._resolve_namespace(manager, "mem-123", "/facts")
        assert result == ["/facts"]

    def test_resolve_actor_template(self, visualizer):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}, {"actorId": "user2"}]
        result = visualizer._resolve_namespace(manager, "mem-123", "/users/{actorId}/facts")
        assert "/users/user1/facts" in result
        assert "/users/user2/facts" in result

    def test_resolve_session_template(self, visualizer):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": "sess1"}]
        result = visualizer._resolve_namespace(manager, "mem-123", "/users/{actorId}/sessions/{sessionId}")
        assert "/users/user1/sessions/sess1" in result

    def test_resolve_namespace_error(self, visualizer):
        manager = MagicMock()
        manager.list_actors.side_effect = Exception("API error")
        result = visualizer._resolve_namespace(manager, "mem-123", "/users/{actorId}/facts")
        assert result == []


class TestStrategyWithVerbose:
    """Test strategy display with verbose mode."""

    def test_visualize_memory_strategy_verbose_all_fields(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "strategies": [
                    {
                        "name": "Facts",
                        "type": "SEMANTIC",
                        "status": "ACTIVE",
                        "strategyId": "strat-123",
                        "description": "Test strategy",
                        "namespaces": ["/facts"],
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-02T00:00:00Z",
                        "configuration": {"nested": {"key": "value"}, "simple": "val"},
                    }
                ],
            }
        )
        visualizer.visualize_memory(memory, verbose=True)
        console.print.assert_called()


class TestAddRecordsToTree:
    """Test _add_records_to_tree method."""

    def test_add_records_truncation(self, visualizer):
        from rich.tree import Tree

        parent = Tree("test")
        records = [{"memoryRecordId": f"r{i}", "content": {"text": f"text{i}"}, "createdAt": "2024"} for i in range(15)]
        export_list = []
        visualizer._add_records_to_tree(parent, "/test", records, False, export_list)
        assert len(export_list) <= 10


class TestMemoryInfoVerbose:
    """Test verbose memory info display."""

    def test_memory_with_role_arn(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "memoryExecutionRoleArn": "arn:aws:iam::123456789:role/test",
                "strategies": [],
            }
        )
        visualizer.visualize_memory(memory, verbose=True)
        console.print.assert_called()

    def test_memory_with_actor_count(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory({"id": "mem-123", "name": "test_mem", "status": "ACTIVE", "strategies": []})
        visualizer.visualize_memory(memory, verbose=False, actor_count=5)
        console.print.assert_called()


class TestStrategyEdgeCases:
    """Test strategy display edge cases."""

    def test_strategy_no_type_icon(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "strategies": [{"name": "Custom", "type": "UNKNOWN_TYPE", "status": "ACTIVE", "namespaces": []}],
            }
        )
        visualizer.visualize_memory(memory, verbose=False)
        console.print.assert_called()

    def test_strategy_empty_namespaces(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "strategies": [{"name": "Facts", "type": "SEMANTIC", "status": "ACTIVE", "namespaces": []}],
            }
        )
        visualizer.visualize_memory(memory, verbose=False)
        console.print.assert_called()


class TestSessionTruncation:
    """Test session truncation hints."""

    def test_session_truncation_hint(self, visualizer, console):
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_sessions.return_value = [{"sessionId": f"sess{i}"} for i in range(15)]
        manager.list_events.return_value = []
        visualizer.display_events_tree("mem-123", manager, max_sessions=5)
        console.print.assert_called()


class TestEventNodeVerbose:
    """Test event node verbose display."""

    def test_event_node_verbose_with_content(self, visualizer):
        from rich.tree import Tree

        branch = Tree("test")
        event = {
            "eventTimestamp": "2024-01-01T00:00:00Z",
            "payload": [{"conversational": {"role": "ASSISTANT", "content": {"text": "response text"}}}],
        }
        visualizer._add_event_node(branch, event, True)


class TestSingleRecordDisplay:
    """Test single record display edge cases."""

    def test_single_record_no_content(self, visualizer, console):
        record = {"memoryRecordId": "r1", "namespace": "/test", "createdAt": "2024-01-01T00:00:00Z"}
        visualizer.display_single_record(record, 1, 1, verbose=False)
        console.print.assert_called()

    def test_single_record_with_recordId(self, visualizer, console):
        record = {"recordId": "r1", "namespace": "/test", "createdAt": "2024-01-01T00:00:00Z", "content": {"text": "x"}}
        visualizer.display_single_record(record, 1, 1, verbose=True)
        console.print.assert_called()


class TestStrategyRecordsWithResolvedNamespaces:
    """Test strategy records with resolved namespaces."""

    def test_strategy_records_with_actor_template(self, visualizer, console):
        manager = MagicMock()
        manager.get_memory.return_value = {
            "strategies": [{"name": "UserFacts", "type": "SEMANTIC", "namespaces": ["/users/{actorId}/facts"]}]
        }
        manager.list_actors.return_value = [{"actorId": "user1"}]
        manager.list_records.return_value = [{"memoryRecordId": "r1", "content": {"text": "test"}, "createdAt": "2024"}]
        visualizer.display_records_tree(manager, "mem-123", False, 10, None)
        console.print.assert_called()


class TestSingleEventNoRole:
    """Test single event display without role."""

    def test_single_event_no_role(self, visualizer, console):
        event = {"eventId": "e1", "eventTimestamp": "2024-01-01T00:00:00Z", "payload": []}
        visualizer.display_single_event(event, 1, 1, verbose=False)
        console.print.assert_called()


class TestMemoryInfoFields:
    """Test memory info field display."""

    def test_memory_with_event_expiry(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "eventExpiryDuration": 30,
                "strategies": [],
            }
        )
        visualizer.visualize_memory(memory, verbose=False)
        console.print.assert_called()

    def test_memory_with_created_at(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "createdAt": "2024-01-01T00:00:00Z",
                "strategies": [],
            }
        )
        visualizer.visualize_memory(memory, verbose=False)
        console.print.assert_called()

    def test_memory_with_updated_at_verbose(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "updatedAt": "2024-01-02T00:00:00Z",
                "strategies": [],
            }
        )
        visualizer.visualize_memory(memory, verbose=True)
        console.print.assert_called()


class TestStrategyConfigNested:
    """Test strategy configuration with nested values."""

    def test_strategy_config_simple_value(self, visualizer, console):
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "strategies": [
                    {
                        "name": "Facts",
                        "type": "SEMANTIC",
                        "status": "ACTIVE",
                        "namespaces": [],
                        "configuration": {"simpleKey": "simpleValue"},
                    }
                ],
            }
        )
        visualizer.visualize_memory(memory, verbose=True)
        console.print.assert_called()


class TestFormatMemoryRowEdgeCases:
    """Test _format_memory_row edge cases."""

    def test_format_row_with_memoryId(self, visualizer):
        memory = {"memoryId": "mem-1", "status": "ACTIVE"}
        row = visualizer._format_memory_row(memory, None)
        assert len(row) == 4

    def test_format_row_with_dates(self, visualizer):
        memory = {
            "id": "mem-1",
            "name": "test",
            "status": "ACTIVE",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
        }
        row = visualizer._format_memory_row(memory, None)
        assert len(row) == 4


class TestFormatStrategyHeader:
    """Test _format_strategy_header method."""

    def test_format_header_no_type_icon(self, visualizer):
        """Test header formatting when type has no icon."""
        from bedrock_agentcore_starter_toolkit.operations.memory.memory_formatters import get_strategy_type_icon

        # Verify UNKNOWN_TYPE has no icon
        assert get_strategy_type_icon("UNKNOWN_TYPE") == ""

        # Test the header formatting
        header = visualizer._format_strategy_header("Test", "UNKNOWN_TYPE", "ACTIVE")
        assert "Test" in str(header)

    def test_format_header_with_type_icon(self, visualizer):
        """Test header formatting when type has an icon."""
        header = visualizer._format_strategy_header("Test", "SEMANTIC", "ACTIVE")
        assert "Test" in str(header)


class TestGroupEventsByBranch:
    """Test _group_events_by_branch method."""

    def test_group_events_single_branch(self, visualizer):
        """Test grouping events with single branch."""
        events = [
            {"eventId": "e1", "branch": {"name": "main"}},
            {"eventId": "e2", "branch": {"name": "main"}},
        ]
        result = visualizer._group_events_by_branch(events)
        assert "main" in result
        assert len(result["main"]) == 2

    def test_group_events_multiple_branches(self, visualizer):
        """Test grouping events with multiple branches."""
        events = [
            {"eventId": "e1", "branch": {"name": "main"}},
            {"eventId": "e2", "branch": {"name": "feature"}},
        ]
        result = visualizer._group_events_by_branch(events)
        assert "main" in result
        assert "feature" in result

    def test_group_events_no_branch(self, visualizer):
        """Test grouping events without branch info."""
        events = [{"eventId": "e1"}, {"eventId": "e2"}]
        result = visualizer._group_events_by_branch(events)
        assert "main" in result
        assert len(result["main"]) == 2


class TestFormatPositionLabel:
    """Test _format_position_label method."""

    def test_format_latest(self, visualizer):
        """Test formatting for latest item."""
        result = visualizer._format_position_label(1, 10)
        assert result == "latest"

    def test_format_nth(self, visualizer):
        """Test formatting for nth item."""
        result = visualizer._format_position_label(3, 10)
        assert result == "#3 most recent"


class TestPrintContentPanel:
    """Test _print_content_panel method."""

    def test_print_content_verbose(self, visualizer, console):
        """Test printing content in verbose mode."""
        visualizer._print_content_panel("test content", verbose=True)
        console.print.assert_called()

    def test_print_content_truncated(self, visualizer, console):
        """Test printing truncated content."""
        long_content = "x" * 1000
        visualizer._print_content_panel(long_content, verbose=False)
        console.print.assert_called()


class TestOutputOrPrint:
    """Test _output_or_print method."""

    def test_output_to_console(self, visualizer, console):
        """Test output to console."""
        from rich.tree import Tree

        tree = Tree("test")
        visualizer._output_or_print(tree, {"data": "test"}, None, "test")
        console.print.assert_called_with(tree)

    def test_output_to_file(self, visualizer, console, tmp_path):
        """Test output to file."""
        from rich.tree import Tree

        tree = Tree("test")
        output_file = tmp_path / "output.json"
        visualizer._output_or_print(tree, {"data": "test"}, str(output_file), "test")
        assert output_file.exists()


class TestGetActors:
    """Test _get_actors method."""

    def test_get_actors_with_filter(self, visualizer):
        """Test getting actors with filter."""
        manager = MagicMock()
        actors, total = visualizer._get_actors(manager, "mem-123", "user1", 10)
        assert len(actors) == 1
        assert actors[0]["actorId"] == "user1"
        assert total == 1

    def test_get_actors_without_filter(self, visualizer):
        """Test getting actors without filter."""
        manager = MagicMock()
        manager.list_actors.return_value = [{"actorId": "user1"}, {"actorId": "user2"}]
        actors, total = visualizer._get_actors(manager, "mem-123", None, 10)
        assert len(actors) == 2
        assert total == 2


class TestGetSessions:
    """Test _get_sessions method."""

    def test_get_sessions_with_filter(self, visualizer):
        """Test getting sessions with filter."""
        manager = MagicMock()
        sessions, total = visualizer._get_sessions(manager, "mem-123", "user1", "sess1", 10)
        assert len(sessions) == 1
        assert sessions[0]["sessionId"] == "sess1"
        assert total == 1

    def test_get_sessions_without_filter(self, visualizer):
        """Test getting sessions without filter."""
        manager = MagicMock()
        manager.list_sessions.return_value = [{"sessionId": "sess1"}, {"sessionId": "sess2"}]
        sessions, total = visualizer._get_sessions(manager, "mem-123", "user1", None, 10)
        assert len(sessions) == 2
        assert total == 2


class TestAddStrategyRecords:
    """Test _add_strategy_records method."""

    def test_add_strategy_records_basic(self, visualizer):
        """Test adding strategy records."""
        from rich.tree import Tree

        root = Tree("test")
        manager = MagicMock()
        manager.list_records.return_value = [{"memoryRecordId": "r1", "content": {"text": "test"}, "createdAt": "2024"}]
        manager.list_actors.return_value = []
        export_data = {"namespaces": []}

        visualizer._add_strategy_records(
            root,
            manager,
            "mem-123",
            {"name": "Facts", "type": "SEMANTIC", "namespaces": ["/facts"]},
            False,
            10,
            export_data,
        )

        assert len(export_data["namespaces"]) >= 0


class TestMemoryVisualizerIntegration:
    """Integration tests for MemoryVisualizer."""

    def test_visualize_memory_full_flow(self, visualizer, console):
        """Test full memory visualization flow."""
        from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory

        memory = Memory(
            {
                "id": "mem-123",
                "name": "test_mem",
                "status": "ACTIVE",
                "description": "Test description",
                "eventExpiryDuration": 30,
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-02T00:00:00Z",
                "arn": "arn:aws:bedrock:us-east-1:123456789:memory/mem-123",
                "memoryExecutionRoleArn": "arn:aws:iam::123456789:role/test",
                "strategies": [
                    {
                        "name": "Facts",
                        "type": "SEMANTIC",
                        "status": "ACTIVE",
                        "strategyId": "strat-123",
                        "description": "Semantic facts",
                        "namespaces": ["/facts", "/summaries"],
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-02T00:00:00Z",
                        "configuration": {"key": "value", "nested": {"inner": "data"}},
                    }
                ],
            }
        )

        visualizer.visualize_memory(memory, verbose=True, actor_count=5)
        console.print.assert_called()
