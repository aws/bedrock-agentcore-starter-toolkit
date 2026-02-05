"""Tests for memory browser."""

from dataclasses import replace
from unittest.mock import MagicMock

from bedrock_agentcore_starter_toolkit.cli.memory.browser import (
    BrowserData,
    MemoryBrowser,
    NavigationState,
)


class TestNavigationState:
    """Test NavigationState dataclass."""

    def test_default_values(self):
        state = NavigationState()
        assert state.memory_id is None
        assert state.actor_id is None
        assert state.session_id is None
        assert state.namespace is None
        assert state.view == "memory"
        assert state.cursor == 0

    def test_with_values(self):
        state = NavigationState(
            memory_id="mem-123",
            actor_id="actor-1",
            view="actors",
            cursor=5,
        )
        assert state.memory_id == "mem-123"
        assert state.actor_id == "actor-1"
        assert state.view == "actors"
        assert state.cursor == 5

    def test_replace(self):
        state = NavigationState(memory_id="mem-123", view="memory", cursor=3)
        new_state = replace(state, view="actors")
        assert state.view == "memory"
        assert new_state.view == "actors"
        assert new_state.memory_id == "mem-123"
        assert new_state.cursor == 3


class TestBrowserData:
    """Test BrowserData dataclass."""

    def test_default_values(self):
        data = BrowserData()
        assert data.memory is None
        assert data.actors == []
        assert data.sessions == []
        assert data.events == []
        assert data.namespaces == []
        assert data.records == []

    def test_mutable_defaults_isolated(self):
        data1 = BrowserData()
        data2 = BrowserData()
        data1.actors.append({"actorId": "a1"})
        assert data2.actors == []


class TestMemoryBrowserInit:
    """Test MemoryBrowser initialization."""

    def test_init_with_manager(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        assert browser.manager == manager
        assert browser.current.memory_id == "mem-123"
        assert browser.current.view == "memory"
        assert browser.nav_stack == []
        assert browser.verbose is False

    def test_init_with_visualizer(self):
        manager = MagicMock()
        visualizer = MagicMock()
        browser = MemoryBrowser(manager, "mem-123", visualizer)
        assert browser.visualizer == visualizer


class TestMemoryBrowserNavigation:
    """Test MemoryBrowser navigation methods."""

    def test_push_state(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "actors"
        browser.cursor = 5
        browser._push_state()
        assert len(browser.nav_stack) == 1
        assert browser.nav_stack[0].view == "actors"
        assert browser.nav_stack[0].cursor == 5

    def test_go_back_empty_stack(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser._go_back()  # Should not raise
        assert browser.current.view == "memory"

    def test_go_back_with_stack(self):
        manager = MagicMock()
        manager.get_memory.return_value = {"id": "mem-123", "name": "test", "status": "ACTIVE"}
        browser = MemoryBrowser(manager, "mem-123")
        browser.nav_stack.append(NavigationState(memory_id="mem-123", view="memory", cursor=2))
        browser.current.view = "actors"
        browser.cursor = 0

        browser._go_back()

        assert browser.current.view == "memory"
        assert browser.cursor == 2
        assert len(browser.nav_stack) == 0

    def test_go_back_restores_cursor(self):
        manager = MagicMock()
        manager.list_actors.return_value = ([{"actorId": "a1"}, {"actorId": "a2"}, {"actorId": "a3"}], None)
        browser = MemoryBrowser(manager, "mem-123")

        # Simulate: at actors view, cursor on item 2, then navigated forward
        browser.nav_stack.append(NavigationState(memory_id="mem-123", view="actors", cursor=2))
        browser.current.view = "sessions"
        browser.cursor = 0

        browser._go_back()

        assert browser.current.view == "actors"
        assert browser.cursor == 2


class TestMemoryBrowserCursor:
    """Test MemoryBrowser cursor movement."""

    def test_cursor_up(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.cursor = 2
        browser._cursor_up()
        assert browser.cursor == 1

    def test_cursor_up_at_zero(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.cursor = 0
        browser._cursor_up()
        assert browser.cursor == 0

    def test_cursor_down(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.items = [1, 2, 3]
        browser.cursor = 0
        browser._cursor_down()
        assert browser.cursor == 1

    def test_cursor_down_at_end(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.items = [1, 2, 3]
        browser.cursor = 2
        browser._cursor_down()
        assert browser.cursor == 2


class TestMemoryBrowserSelection:
    """Test MemoryBrowser selection handlers."""

    def test_select_actor(self):
        manager = MagicMock()
        manager.list_sessions.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "actors"
        browser.items = [{"actorId": "actor-1"}, {"actorId": "actor-2"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.actor_id == "actor-1"
        assert browser.current.view == "sessions"
        assert len(browser.nav_stack) == 1

    def test_select_session(self):
        manager = MagicMock()
        manager.list_events.return_value = []
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "sessions"
        browser.current.actor_id = "actor-1"
        browser.items = [{"sessionId": "sess-1"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.session_id == "sess-1"
        assert browser.current.view == "events"

    def test_select_event(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "events"
        browser.items = [{"eventId": "evt-1"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.event_index == 0
        assert browser.current.view == "event_detail"

    def test_select_static_namespace(self):
        manager = MagicMock()
        manager.list_records.return_value = []
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespaces"
        browser.items = [{"namespace": "/facts"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.namespace == "/facts"
        assert browser.current.view == "records"

    def test_select_template_namespace(self):
        manager = MagicMock()
        manager.list_actors.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespaces"
        browser.items = [{"namespace": "/users/{actorId}/facts"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.view == "namespace_actors"
        assert browser.current.namespace_template == "/users/{actorId}/facts"

    def test_select_namespace_actor(self):
        manager = MagicMock()
        manager.list_records.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespace_actors"
        browser.current.namespace_template = "/users/{actorId}/facts"
        browser.items = [{"actorId": "user-1"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.namespace == "/users/user-1/facts"
        assert browser.current.view == "records"

    def test_select_namespace_actor_with_session(self):
        manager = MagicMock()
        manager.list_sessions.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespace_actors"
        browser.current.namespace_template = "/summaries/{actorId}/{sessionId}"
        browser.items = [{"actorId": "user-1"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.view == "namespace_sessions"
        assert browser.current.actor_id == "user-1"

    def test_select_namespace_session(self):
        manager = MagicMock()
        manager.list_records.return_value = []
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespace_sessions"
        browser.current.namespace_template = "/summaries/{actorId}/{sessionId}"
        browser.current.actor_id = "user-1"
        browser.items = [{"sessionId": "sess-1"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.namespace == "/summaries/user-1/sess-1"
        assert browser.current.view == "records"

    def test_select_record(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "records"
        browser.current.namespace = "/facts"
        browser.items = [{"memoryRecordId": "rec-1"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.record_index == 0
        assert browser.current.view == "record_detail"

    def test_select_empty_items(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.items = []
        browser._select()  # Should not raise


class TestMemoryBrowserExtractors:
    """Test text extraction methods."""

    def test_extract_role(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        event = {"payload": {"content": [{"role": "USER", "text": "Hello"}]}}
        assert browser._extract_role(event) == "USER"

    def test_extract_role_empty(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        assert browser._extract_role({}) == ""
        assert browser._extract_role({"payload": {}}) == ""
        assert browser._extract_role({"payload": {"content": []}}) == ""

    def test_extract_text(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        event = {"payload": {"content": [{"text": "Hello world"}]}}
        assert browser._extract_text(event) == "Hello world"

    def test_extract_text_empty(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        assert browser._extract_text({}) == ""
        assert browser._extract_text({"payload": {"content": [{"role": "USER"}]}}) == ""

    def test_extract_record_text(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        record = {"content": {"text": "Test content"}}
        assert browser._extract_record_text(record) == "Test content"

    def test_extract_record_text_string_content(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        record = {"content": "plain string"}
        assert browser._extract_record_text(record) == "plain string"

    def test_extract_record_text_empty(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        assert browser._extract_record_text({}) == "{}"  # Empty dict stringified
        assert browser._extract_record_text({"content": None}) == ""


class TestMemoryBrowserLoadView:
    """Test view loading methods."""

    def test_load_memory_view(self):
        manager = MagicMock()
        manager.get_memory.return_value = {"id": "mem-123", "strategies": []}
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "memory"
        browser._load_view()
        assert browser.data.memory == {"id": "mem-123", "strategies": []}

    def test_load_actors_view(self):
        manager = MagicMock()
        manager.list_actors.return_value = ([{"actorId": "a1"}, {"actorId": "a2"}], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "actors"
        browser._load_view()
        assert len(browser.items) == 2
        assert browser.cursor == 0

    def test_load_sessions_view(self):
        manager = MagicMock()
        manager.list_sessions.return_value = ([{"sessionId": "s1"}], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "sessions"
        browser.current.actor_id = "a1"
        browser._load_view()
        assert len(browser.items) == 1

    def test_load_events_view(self):
        manager = MagicMock()
        manager.list_events.return_value = (
            [
                {"eventId": "e1", "eventTimestamp": "2024-01-01T10:00:00"},
                {"eventId": "e2", "eventTimestamp": "2024-01-01T09:00:00"},
            ],
            None,
        )
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "events"
        browser.current.actor_id = "a1"
        browser.current.session_id = "s1"
        browser._load_view()
        assert len(browser.items) == 2
        # Should be sorted by timestamp
        assert browser.items[0]["eventTimestamp"] < browser.items[1]["eventTimestamp"]

    def test_load_namespaces_view(self):
        manager = MagicMock()
        manager.get_memory.return_value = {
            "strategies": [
                {"name": "Facts", "type": "SEMANTIC", "namespaces": ["/facts"]},
                {"name": "Prefs", "type": "USER_PREFERENCE", "namespaces": ["/prefs/{actorId}"]},
            ]
        }
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespaces"
        browser._load_view()
        assert len(browser.items) == 2
        assert browser.items[0]["namespace"] == "/facts"
        assert browser.items[1]["type"] == "USER_PREFERENCE"

    def test_load_records_view(self):
        manager = MagicMock()
        manager.list_records.return_value = ([{"memoryRecordId": "r1"}], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "records"
        browser.current.namespace = "/facts"
        browser._load_view()
        assert len(browser.items) == 1

    def test_load_view_error_handling(self):
        manager = MagicMock()
        manager.list_actors.side_effect = Exception("API error")
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "actors"
        browser._load_view()  # Should not raise
        assert browser.items == []
