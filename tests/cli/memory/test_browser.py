"""Tests for memory browser."""

from dataclasses import replace
from unittest.mock import MagicMock

from botocore.exceptions import BotoCoreError, ClientError
from rich.console import Console

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

    def test_init_with_initial_memory(self):
        manager = MagicMock()
        memory = {"id": "mem-123", "strategies": []}
        browser = MemoryBrowser(manager, "mem-123", initial_memory=memory)
        assert browser.data.memory == memory

    def test_load_memory_skips_api_when_preloaded(self):
        manager = MagicMock()
        memory = {"id": "mem-123", "strategies": []}
        browser = MemoryBrowser(manager, "mem-123", initial_memory=memory)
        browser._load_memory()
        manager.get_memory.assert_not_called()


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
        manager._paginated_list_page.return_value = ([{"actorId": "a1"}, {"actorId": "a2"}, {"actorId": "a3"}], None)
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
        manager._paginated_list_page.return_value = ([], None)
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
        manager._paginated_list_page.return_value = ([], None)
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
        manager._paginated_list_page.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespaces"
        browser.items = [{"namespace": "/facts"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.namespace == "/facts"
        assert browser.current.view == "records"

    def test_select_template_namespace(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespaces"
        browser.items = [{"namespace": "/users/{actorId}/facts"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.view == "namespace_actors"
        assert browser.current.namespace_template == "/users/{actorId}/facts"

    def test_select_namespace_actor(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([], None)
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
        manager._paginated_list_page.return_value = ([], None)
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
        manager._paginated_list_page.return_value = ([], None)
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

    def test_select_memory_item_actors(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "memory"
        browser.items = [{"label": "Actors", "view": "actors"}, {"label": "Namespaces", "view": "namespaces"}]
        browser.cursor = 0

        browser._select()

        assert browser.current.view == "actors"
        assert len(browser.nav_stack) == 1

    def test_select_memory_item_namespaces(self):
        manager = MagicMock()
        manager.get_memory.return_value = {"strategies": []}
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "memory"
        browser.items = [{"label": "Actors", "view": "actors"}, {"label": "Namespaces", "view": "namespaces"}]
        browser.cursor = 1

        browser._select()

        assert browser.current.view == "namespaces"


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

    def test_extract_payload_snippet_short(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        event = {"payload": {"key": "val"}}
        assert browser._extract_payload_snippet(event) == '{"key": "val"}'

    def test_extract_payload_snippet_long(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        event = {"payload": {"text": "a" * 100}}
        result = browser._extract_payload_snippet(event)
        assert len(result) == 61  # 60 chars + "…"
        assert result.endswith("…")

    def test_extract_payload_snippet_empty(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        assert browser._extract_payload_snippet({}) == "(empty)"
        assert browser._extract_payload_snippet({"payload": None}) == "(empty)"


class TestMemoryBrowserLoadView:
    """Test view loading methods."""

    def test_load_memory_view(self):
        manager = MagicMock()
        manager.get_memory.return_value = {"id": "mem-123", "strategies": []}
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "memory"
        browser._load_view()
        assert browser.data.memory == {"id": "mem-123", "strategies": []}
        assert len(browser.items) == 2
        assert browser.items[0]["view"] == "actors"
        assert browser.items[1]["view"] == "namespaces"

    def test_load_actors_view(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([{"actorId": "a1"}, {"actorId": "a2"}], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "actors"
        browser._load_view()
        assert len(browser.items) == 2
        assert browser.cursor == 0

    def test_load_sessions_view(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([{"sessionId": "s1"}], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "sessions"
        browser.current.actor_id = "a1"
        browser._load_view()
        assert len(browser.items) == 1

    def test_load_events_view(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = (
            [
                {"eventId": "e1", "eventTimestamp": "2024-01-01T10:00:00"},
                {"eventId": "e2", "eventTimestamp": "2024-01-01T09:00:00"},
                {"eventId": "e3", "eventTimestamp": "2024-01-01T11:00:00"},
                {"eventId": "e4", "eventTimestamp": "2024-01-01T08:00:00"},
            ],
            None,
        )
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "events"
        browser.current.actor_id = "a1"
        browser.current.session_id = "s1"
        browser._load_view()
        assert len(browser.items) == 4
        # Should be sorted by timestamp ascending
        assert [e["eventId"] for e in browser.items] == ["e3", "e1", "e2", "e4"]

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
        manager._paginated_list_page.return_value = ([{"memoryRecordId": "r1"}], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "records"
        browser.current.namespace = "/facts"
        browser._load_view()
        assert len(browser.items) == 1

    def test_load_view_error_handling(self):
        manager = MagicMock()
        manager._paginated_list_page.side_effect = Exception("API error")
        browser = MemoryBrowser(manager, "mem-123")
        browser.console = MagicMock()
        browser.current.view = "actors"
        browser._load_view()
        assert browser.items == []
        browser.console.print.assert_called()
        error_msg = browser.console.print.call_args[0][0]
        assert "Error" in error_msg and "API error" in error_msg

    def test_load_view_client_error_handling(self):
        """Test ClientError is caught and displays error code."""
        manager = MagicMock()
        error_response = {"Error": {"Code": "ExpiredTokenException", "Message": "Token expired"}}
        manager._paginated_list_page.side_effect = ClientError(error_response, "ListActors")
        browser = MemoryBrowser(manager, "mem-123")
        browser.console = MagicMock()
        browser.current.view = "actors"
        browser._load_view()
        assert browser.items == []
        browser.console.print.assert_called()
        error_msg = browser.console.print.call_args[0][0]
        assert "ExpiredTokenException" in error_msg

    def test_load_view_botocore_error_handling(self):
        """Test BotoCoreError is caught."""
        manager = MagicMock()
        manager._paginated_list_page.side_effect = BotoCoreError()
        browser = MemoryBrowser(manager, "mem-123")
        browser.console = MagicMock()
        browser.current.view = "actors"
        browser._load_view()
        assert browser.items == []
        browser.console.print.assert_called()
        error_msg = browser.console.print.call_args[0][0]
        assert "AWS Error" in error_msg


class TestMemoryBrowserLoadMore:
    """Test load_more pagination and cache behavior."""

    def test_load_actors_load_more(self):
        manager = MagicMock()
        manager._paginated_list_page.side_effect = [
            ([{"actorId": "a1"}], "token1"),
            ([{"actorId": "a2"}], None),
        ]
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "actors"
        browser._load_actors()
        assert len(browser.data.actors) == 1
        assert browser.actors_next_token == "token1"

        browser._load_actors(load_more=True)
        assert len(browser.data.actors) == 2
        assert browser.data.actors[1]["actorId"] == "a2"
        assert browser.actors_next_token is None

    def test_load_sessions_load_more(self):
        manager = MagicMock()
        manager._paginated_list_page.side_effect = [
            ([{"sessionId": "s1"}], "tok"),
            ([{"sessionId": "s2"}], None),
        ]
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.actor_id = "a1"
        browser._load_sessions()
        assert browser.sessions_next_token == "tok"

        browser._load_sessions(load_more=True)
        assert len(browser.data.sessions) == 2
        assert browser.sessions_next_token is None

    def test_load_events_load_more_sorts(self):
        manager = MagicMock()
        manager._paginated_list_page.side_effect = [
            ([{"eventId": "e1", "eventTimestamp": "2024-01-01T10:00:00"}], "tok"),
            ([{"eventId": "e2", "eventTimestamp": "2024-01-01T08:00:00"}], None),
        ]
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.actor_id = "a1"
        browser.current.session_id = "s1"
        browser._load_events()
        browser._load_events(load_more=True)
        assert len(browser.data.events) == 2
        # Sorted by timestamp descending — e1 (10:00) before e2 (08:00)
        assert browser.data.events[0]["eventId"] == "e1"
        assert browser.data.events[1]["eventId"] == "e2"

    def test_load_records_load_more(self):
        manager = MagicMock()
        manager._paginated_list_page.side_effect = [
            ([{"memoryRecordId": "r1"}], "tok"),
            ([{"memoryRecordId": "r2"}], None),
        ]
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.namespace = "/facts"
        browser._load_records()
        assert browser.records_next_token == "tok"

        browser._load_records(load_more=True)
        assert len(browser.data.records) == 2
        assert browser.records_next_token is None

    def test_load_actors_cache_hit(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.data.actors = [{"actorId": "cached"}]
        browser._load_actors()
        manager._paginated_list_page.assert_not_called()
        assert browser.items == [{"actorId": "cached"}]

    def test_load_namespaces_fallback_key(self):
        manager = MagicMock()
        manager.get_memory.return_value = {
            "memoryStrategies": [
                {"name": "Facts", "memoryStrategyType": "SEMANTIC", "namespaces": ["/facts"]},
            ]
        }
        browser = MemoryBrowser(manager, "mem-123")
        browser._load_namespaces()
        assert len(browser.items) == 1
        assert browser.items[0]["namespace"] == "/facts"
        assert browser.items[0]["type"] == "SEMANTIC"


class TestMemoryBrowserCacheInvalidation:
    """Test cache clearing on navigation."""

    def test_select_actor_clears_session_cache(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "actors"
        browser.data.sessions = [{"sessionId": "stale"}]
        browser.sessions_next_token = "old_token"
        browser.items = [{"actorId": "a1"}]
        browser.cursor = 0

        browser._select_actor()

        assert browser.data.sessions == []
        assert browser.sessions_next_token is None

    def test_select_session_clears_event_cache(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "sessions"
        browser.current.actor_id = "a1"
        browser.data.events = [{"eventId": "stale"}]
        browser.events_next_token = "old_token"
        browser.items = [{"sessionId": "s1"}]
        browser.cursor = 0

        browser._select_session()

        assert browser.data.events == []
        assert browser.events_next_token is None

    def test_select_namespace_clears_record_cache(self):
        manager = MagicMock()
        manager._paginated_list_page.return_value = ([], None)
        browser = MemoryBrowser(manager, "mem-123")
        browser.current.view = "namespaces"
        browser.data.records = [{"memoryRecordId": "stale"}]
        browser.records_next_token = "old_token"
        browser.items = [{"namespace": "/facts"}]
        browser.cursor = 0

        browser._select_namespace()

        assert browser.data.records == []
        assert browser.records_next_token is None


class TestMemoryBrowserRender:
    """Test rendering methods."""

    def _make_browser(self, **kwargs):
        manager = kwargs.pop("manager", MagicMock())
        from io import StringIO

        buf = StringIO()
        browser = MemoryBrowser(manager, "mem-123")
        browser.console = Console(file=buf, force_terminal=True, width=120)
        browser.visualizer = MagicMock()
        return browser, buf

    def test_render_breadcrumb_memory_root(self):
        browser, buf = self._make_browser()
        browser.current.view = "memory"
        browser._render_breadcrumb()
        output = buf.getvalue()
        assert "mem-123" in output

    def test_render_breadcrumb_deep_navigation(self):
        browser, buf = self._make_browser()
        browser.current.view = "event_detail"
        browser.current.actor_id = "actor-1"
        browser.current.session_id = "sess-1"
        browser.current.event_index = 2
        browser._render_breadcrumb()
        output = buf.getvalue()
        assert "Actors" in output
        assert "actor-1" in output
        assert "sess-1" in output
        assert "Event #3" in output

    def test_render_breadcrumb_record_detail(self):
        browser, buf = self._make_browser()
        browser.current.view = "record_detail"
        browser.current.namespace = "/facts"
        browser.current.record_index = 0
        browser._render_breadcrumb()
        output = buf.getvalue()
        assert "Namespaces" in output
        assert "/facts" in output
        assert "Record #1" in output

    def test_render_memory_view_calls_visualizer(self):
        browser, buf = self._make_browser()
        browser.data.memory = {"id": "mem-123"}
        browser.items = [
            {"label": "👤 Actors (STM)", "view": "actors"},
            {"label": "📊 Namespaces (LTM)", "view": "namespaces"},
        ]
        browser._render_memory_view()
        browser.visualizer.build_memory_tree.assert_called_once_with({"id": "mem-123"}, False)
        output = buf.getvalue()
        assert "Actors" in output
        assert "Namespaces" in output

    def test_render_memory_view_no_data_shows_nav(self):
        browser, buf = self._make_browser()
        browser.data.memory = None
        browser.items = [
            {"label": "👤 Actors (STM)", "view": "actors"},
            {"label": "📊 Namespaces (LTM)", "view": "namespaces"},
        ]
        browser._render_memory_view()
        browser.visualizer.build_memory_tree.assert_not_called()
        output = buf.getvalue()
        assert "Actors" in output
        assert "Namespaces" in output

    def test_render_event_detail_calls_visualizer(self):
        browser, _ = self._make_browser()
        browser.current.view = "event_detail"
        browser.current.event_index = 0
        browser.data.events = [{"eventId": "e1"}]
        browser._render_event_detail()
        browser.visualizer.build_event_detail.assert_called_once_with({"eventId": "e1"}, False)

    def test_render_record_detail_with_namespace(self):
        browser, _ = self._make_browser()
        browser.current.view = "record_detail"
        browser.current.record_index = 0
        browser.current.namespace = "/facts"
        browser.data.records = [{"memoryRecordId": "r1"}]
        browser._render_record_detail()
        browser.visualizer.build_record_detail.assert_called_once_with(
            {"memoryRecordId": "r1"}, False, namespace="/facts"
        )

    def test_render_event_detail_out_of_bounds(self):
        browser, _ = self._make_browser()
        browser.current.event_index = 5
        browser.data.events = [{"eventId": "e1"}]
        browser._render_event_detail()  # Should not raise
        browser.visualizer.build_event_detail.assert_not_called()

    def test_render_list_view_empty(self):
        browser, buf = self._make_browser()
        browser.items = []
        browser._render_list_view("actors")
        assert "No items found" in buf.getvalue()

    def test_render_list_view_events_with_role(self):
        browser, buf = self._make_browser()
        browser.items = [
            {"eventTimestamp": "2024-01-01T10:30:00", "payload": {"content": [{"role": "USER", "text": "Hello"}]}},
            {"eventTimestamp": "2024-01-01T11:00:00", "payload": {"content": [{"role": "ASSISTANT", "text": "Hi"}]}},
        ]
        browser.cursor = 0
        browser._render_list_view("events")
        output = buf.getvalue()
        assert "Hello" in output
        assert "Hi" in output

    def test_render_list_view_events_payload_fallback(self):
        browser, buf = self._make_browser()
        browser.items = [
            {"eventTimestamp": "2024-01-01T10:30:00", "payload": {"toolUse": "something"}},
        ]
        browser.cursor = 0
        browser._render_list_view("events")
        output = buf.getvalue()
        assert "toolUse" in output


class TestMemoryBrowserRenderControls:
    """Test _render_controls load-more notice behavior."""

    def _make_browser(self):
        from io import StringIO

        buf = StringIO()
        browser = MemoryBrowser(MagicMock(), "mem-123")
        browser.console = Console(file=buf, force_terminal=True, width=120)
        return browser, buf

    def test_render_controls_shows_more_for_events(self):
        browser, buf = self._make_browser()
        browser.current.view = "events"
        browser.events_next_token = "tok"
        browser._render_controls()
        assert "More items available" in buf.getvalue()

    def test_render_controls_no_notice_for_actors(self):
        browser, buf = self._make_browser()
        browser.current.view = "actors"
        browser.actors_next_token = "tok"
        browser._render_controls()
        assert "More items available" not in buf.getvalue()

    def test_render_controls_shows_shortcuts_on_memory_view(self):
        browser, buf = self._make_browser()
        browser.current.view = "memory"
        browser._render_controls()
        output = buf.getvalue()
        assert "actors" in output
        assert "namespaces" in output
        assert "back" not in output
        assert "home" not in output
        assert "more" not in output

    def test_render_controls_no_shortcuts_on_other_views(self):
        browser, buf = self._make_browser()
        browser.current.view = "actors"
        browser._render_controls()
        output = buf.getvalue()
        assert "namespaces" not in output
        assert "back" in output
        assert "home" in output
        assert "more" in output


class TestMemoryBrowserCoverage:
    """Tests to cover remaining uncovered lines and branches."""

    def _make_browser(self, **kwargs):
        manager = kwargs.pop("manager", MagicMock())
        from io import StringIO

        buf = StringIO()
        browser = MemoryBrowser(manager, "mem-123")
        browser.console = Console(file=buf, force_terminal=True, width=120)
        browser.visualizer = MagicMock()
        return browser, buf

    # _clear and _render (lines 179, 183-186)
    def test_render_calls_all_phases(self):
        browser, buf = self._make_browser()
        browser.current.view = "memory"
        browser.items = [
            {"label": "👤 Actors (STM)", "view": "actors"},
            {"label": "📊 Namespaces (LTM)", "view": "namespaces"},
        ]
        browser._render()
        output = buf.getvalue()
        # Breadcrumb, content, and controls all rendered
        assert "Browse" in output
        assert "quit" in output

    # _render_content dispatch (lines 223-233)
    def test_render_content_dispatches_to_list_view(self):
        browser, buf = self._make_browser()
        browser.current.view = "actors"
        browser.items = [{"actorId": "a1"}]
        browser.cursor = 0
        browser._render_content()
        assert "a1" in buf.getvalue()

    def test_render_content_unknown_view(self):
        browser, buf = self._make_browser()
        browser.current.view = "unknown_view"
        browser._render_content()
        assert buf.getvalue() == ""

    # _render_list_view actors (lines 283-291)
    def test_render_list_view_actors(self):
        browser, buf = self._make_browser()
        browser.items = [{"actorId": "actor-1"}, {"actorId": "actor-2"}]
        browser.cursor = 0
        browser._render_list_view("actors")
        output = buf.getvalue()
        assert "actor-1" in output
        assert "actor-2" in output

    def test_render_list_view_namespace_actors(self):
        browser, buf = self._make_browser()
        browser.items = [{"actorId": "ns-actor"}]
        browser.cursor = 0
        browser._render_list_view("namespace_actors")
        assert "ns-actor" in buf.getvalue()

    # _render_list_view sessions (lines 294-302)
    def test_render_list_view_sessions(self):
        browser, buf = self._make_browser()
        browser.items = [{"sessionId": "sess-1"}, {"sessionId": "sess-2"}]
        browser.cursor = 0
        browser._render_list_view("sessions")
        output = buf.getvalue()
        assert "sess-1" in output
        assert "sess-2" in output

    # _render_list_view namespaces (lines 325-340)
    def test_render_list_view_namespaces(self):
        browser, buf = self._make_browser()
        browser.items = [
            {"strategy": "Facts", "type": "SEMANTIC", "namespace": "/facts"},
            {"strategy": "Conv", "type": "CONVERSATION_SUMMARY", "namespace": "/conv"},
        ]
        browser.cursor = 0
        browser._render_list_view("namespaces")
        output = buf.getvalue()
        assert "Facts" in output
        assert "/conv" in output

    # _render_list_view records (lines 342-356)
    def test_render_list_view_records(self):
        browser, buf = self._make_browser()
        long_text = "x" * 80
        browser.items = [
            {"createdAt": "2024-01-01T10:00:00Z", "content": {"text": long_text}},
            {"createdAt": "2024-01-02T10:00:00Z", "content": {"text": "short"}},
        ]
        browser.cursor = 0
        browser._render_list_view("records")
        output = buf.getvalue()
        assert "2024-01-01" in output
        assert "…" in output  # truncation of long text

    # Cache hits: sessions (lines 475-476)
    def test_load_sessions_cache_hit(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.data.sessions = [{"sessionId": "cached"}]
        browser._load_sessions()
        manager._paginated_list_page.assert_not_called()
        assert browser.items == [{"sessionId": "cached"}]

    # Cache hits: events (lines 497-498)
    def test_load_events_cache_hit(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.data.events = [{"eventId": "cached"}]
        browser._load_events()
        manager._paginated_list_page.assert_not_called()
        assert browser.items == [{"eventId": "cached"}]

    # Cache hits: records (lines 535-536)
    def test_load_records_cache_hit(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.data.records = [{"recordId": "cached"}]
        browser._load_records()
        manager._paginated_list_page.assert_not_called()
        assert browser.items == [{"recordId": "cached"}]

    # _load_view unknown view (line 428->exit)
    def test_load_view_unknown_view(self):
        browser, buf = self._make_browser()
        browser.current.view = "nonexistent"
        browser._load_view()  # should not raise
        assert browser.items == []

    # _select with no items (line 593->exit)
    def test_select_empty_items(self):
        browser, _ = self._make_browser()
        browser.items = []
        browser._select()  # should not raise

    # _select unknown view (line 593->exit handler branch)
    def test_select_unknown_view(self):
        browser, _ = self._make_browser()
        browser.items = [{"something": "val"}]
        browser.current.view = "nonexistent"
        browser._select()  # should not raise

    # Branch: _extract_role with non-dict payload (674->680)
    def test_extract_role_non_dict_payload(self):
        browser, _ = self._make_browser()
        assert browser._extract_role({"payload": "string"}) == ""

    # Branch: _extract_role with non-list content (676->680)
    def test_extract_role_non_list_content(self):
        browser, _ = self._make_browser()
        assert browser._extract_role({"payload": {"content": "string"}}) == ""

    # Branch: _extract_role item not dict (678->677)
    def test_extract_role_non_dict_item(self):
        browser, _ = self._make_browser()
        assert browser._extract_role({"payload": {"content": ["not_a_dict"]}}) == ""

    # Branch: _extract_text with non-dict payload (685->691)
    def test_extract_text_non_dict_payload(self):
        browser, _ = self._make_browser()
        assert browser._extract_text({"payload": "string"}) == ""

    # Branch: _extract_text with non-list content (687->691)
    def test_extract_text_non_list_content(self):
        browser, _ = self._make_browser()
        assert browser._extract_text({"payload": {"content": "string"}}) == ""

    # _render_controls branch exit (369->exit): no token, no memory view
    def test_render_controls_minimal(self):
        browser, buf = self._make_browser()
        browser.current.view = "sessions"
        browser._render_controls()
        output = buf.getvalue()
        assert "navigate" in output
        assert "More items" not in output

    # _load_namespaces with memory already cached (522->524)
    def test_load_namespaces_memory_already_cached(self):
        manager = MagicMock()
        browser = MemoryBrowser(manager, "mem-123")
        browser.data.memory = {"strategies": [{"name": "S", "type": "SEMANTIC", "namespaces": ["/ns"]}]}
        browser._load_namespaces()
        manager.get_memory.assert_not_called()
        assert browser.items[0]["namespace"] == "/ns"
