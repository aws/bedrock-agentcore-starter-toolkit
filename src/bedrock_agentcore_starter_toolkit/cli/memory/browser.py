"""Interactive browser for exploring AgentCore Memory content."""

import json
import logging
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional

from botocore.exceptions import BotoCoreError, ClientError
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.table import Table
from rich.text import Text

from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.memory_visualizer import MemoryVisualizer

logger = logging.getLogger(__name__)

PAGE_SIZE = 25


@dataclass
class NavigationState:
    """State for navigation through memory hierarchy."""

    memory_id: Optional[str] = None
    actor_id: Optional[str] = None
    session_id: Optional[str] = None
    namespace: Optional[str] = None
    namespace_template: Optional[str] = None
    event_index: Optional[int] = None
    record_index: Optional[int] = None
    view: str = "memory"
    cursor: int = 0


@dataclass
class BrowserData:
    """Cached data for the browser."""

    memory: Optional[Dict[str, Any]] = None
    actors: List[Dict[str, Any]] = field(default_factory=list)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    namespaces: List[Dict[str, Any]] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)


class MemoryBrowser:
    """Interactive browser for AgentCore Memory content."""

    def __init__(
        self,
        manager: MemoryManager,
        memory_id: str,
        visualizer: Optional[MemoryVisualizer] = None,
        initial_memory: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the memory browser."""
        self.manager = manager
        self.console = Console()
        self.visualizer = visualizer or MemoryVisualizer(self.console)
        self.nav_stack: List[NavigationState] = []
        self.current = NavigationState(memory_id=memory_id, view="memory")
        self.data = BrowserData()
        if initial_memory:
            self.data.memory = initial_memory
        self.verbose = False
        self.cursor = 0
        self.items: List[Any] = []
        self.actors_next_token: Optional[str] = None
        self.sessions_next_token: Optional[str] = None
        self.events_next_token: Optional[str] = None
        self.records_next_token: Optional[str] = None

    def run(self) -> None:
        """Run the interactive browser."""
        from prompt_toolkit.layout import Layout
        from prompt_toolkit.layout.containers import Window
        from prompt_toolkit.layout.controls import FormattedTextControl

        bindings = KeyBindings()

        @bindings.add("up")
        def _(event):
            self._cursor_up()
            self._render()

        @bindings.add("down")
        def _(event):
            self._cursor_down()
            self._render()

        @bindings.add("enter")
        def _(event):
            self._select()
            self._render()

        @bindings.add("b")
        def _(event):
            self._go_back()
            self._render()

        @bindings.add("v")
        def _(event):
            self.verbose = not self.verbose
            self._render()

        @bindings.add("a")
        def _(event):
            if self.current.view == "memory":
                self._push_state()
                self.current.view = "actors"
                self._load_view()
                self._render()

        @bindings.add("n")
        def _(event):
            if self.current.view == "memory":
                self._push_state()
                self.current.view = "namespaces"
                self._load_view()
                self._render()

        @bindings.add("m")
        def _(event):
            if self.current.view == "actors" and self.actors_next_token:
                self._load_actors(load_more=True)
                self._render()
            elif self.current.view == "sessions" and self.sessions_next_token:
                self._load_sessions(load_more=True)
                self._render()
            elif self.current.view == "events" and self.events_next_token:
                self._load_events(load_more=True)
                self._render()
            elif self.current.view == "records" and self.records_next_token:
                self._load_records(load_more=True)
                self._render()

        @bindings.add("h")
        def _(event):
            self.nav_stack.clear()
            self.current = NavigationState(memory_id=self.current.memory_id, view="memory")
            self.cursor = 0
            self.data.actors = []
            self.data.sessions = []
            self.data.events = []
            self.data.records = []
            self.actors_next_token = None
            self.sessions_next_token = None
            self.events_next_token = None
            self.records_next_token = None
            self._load_view()
            self._render()

        @bindings.add("q")
        def _(event):
            event.app.exit()

        @bindings.add("c-c")
        def _(event):
            event.app.exit()

        # Minimal layout to satisfy prompt_toolkit
        layout = Layout(Window(FormattedTextControl("")))
        app = Application(key_bindings=bindings, layout=layout, full_screen=False, erase_when_done=True)

        self._load_view()
        self._render()

        try:
            app.run()
        except EOFError:
            pass

    def _clear(self) -> None:
        """Clear the terminal."""
        self.console.clear()

    def _render(self) -> None:
        """Render the current view."""
        self._clear()
        self._render_breadcrumb()
        self._render_content()
        self._render_controls()

    def _render_breadcrumb(self) -> None:
        """Render breadcrumb navigation."""
        parts = [self.current.memory_id or "Memory"]

        if self.current.view in ("actors", "sessions", "events", "event_detail"):
            parts.append("Actors")
        elif self.current.view in ("namespaces", "namespace_actors", "namespace_sessions", "records", "record_detail"):
            parts.append("Namespaces")

        actor_views = ("sessions", "events", "event_detail", "namespace_sessions", "records", "record_detail")
        if self.current.actor_id and self.current.view in actor_views:
            parts.append(self.current.actor_id)

        if self.current.session_id and self.current.view in ("events", "event_detail", "records", "record_detail"):
            parts.append(self.current.session_id)

        if self.current.namespace and self.current.view in ("records", "record_detail"):
            parts.append(self.current.namespace)

        if self.current.view == "event_detail" and self.current.event_index is not None:
            parts.append(f"Event #{self.current.event_index + 1}")
        elif self.current.view == "record_detail" and self.current.record_index is not None:
            parts.append(f"Record #{self.current.record_index + 1}")

        breadcrumb = Text()
        for i, part in enumerate(parts):
            if i > 0:
                breadcrumb.append(" > ", style="dim")
            breadcrumb.append(part, style="bold cyan" if i == len(parts) - 1 else "dim")

        self.console.print(breadcrumb)
        self.console.print()

    def _render_content(self) -> None:
        """Render the main content area."""
        renderers = {
            "memory": self._render_memory_view,
            "event_detail": self._render_event_detail,
            "record_detail": self._render_record_detail,
        }
        list_views = ("actors", "sessions", "events", "namespaces", "namespace_actors", "namespace_sessions", "records")

        if self.current.view in renderers:
            renderers[self.current.view]()
        elif self.current.view in list_views:
            self._render_list_view(self.current.view)

    def _render_memory_view(self) -> None:
        """Render memory detail with navigation options."""
        if self.data.memory:
            tree = self.visualizer.build_memory_tree(self.data.memory, self.verbose)
            self.console.print(tree)

        self.console.print()
        self.console.print("[bold]📋 Browse[/bold]\n")

        from rich.box import ROUNDED

        table = Table(box=ROUNDED, show_header=False, padding=(0, 1), border_style="dim")
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column()
        for i, item in enumerate(self.items):
            selected = i == self.cursor
            num = f"▸ {i + 1}" if selected else f"  {i + 1}"
            label = item["label"]
            if selected:
                table.add_row(f"[cyan]{num}[/cyan]", f"[cyan]{label}[/cyan]")
            else:
                table.add_row(num, label)
        self.console.print(table)

    def _render_list_view(self, view_type: str) -> None:
        """Render a list view with cursor highlighting."""
        if not self.items:
            self.console.print("[yellow]No items found[/yellow]")
            return

        # Title
        titles = {
            "actors": f"👤 Actors ({len(self.items)})",
            "namespace_actors": f"👤 Select Actor for {self.current.namespace_template}",
            "sessions": f"📁 Sessions ({len(self.items)})",
            "namespace_sessions": "📁 Select Session",
            "events": f"💬 Events ({len(self.items)})",
            "namespaces": f"📊 Namespaces ({len(self.items)})",
            "records": f"📝 Records ({len(self.items)})",
        }
        self.console.print(f"[bold]{titles.get(view_type, view_type)}[/bold]\n")

        from rich.box import ROUNDED

        table = Table(box=ROUNDED, show_header=True, padding=(0, 1), border_style="dim")
        table.add_column("#", style="dim", width=4, justify="right")

        if view_type in ("actors", "namespace_actors"):
            table.add_column("Actor ID")
            for i, item in enumerate(self.items):
                selected = i == self.cursor
                num = f"▸ {i + 1}" if selected else f"  {i + 1}"
                val = item.get("actorId", "N/A")
                if selected:
                    table.add_row(f"[cyan]{num}[/cyan]", f"[cyan]{val}[/cyan]")
                else:
                    table.add_row(num, val)

        elif view_type in ("sessions", "namespace_sessions"):
            table.add_column("Session ID")
            for i, item in enumerate(self.items):
                selected = i == self.cursor
                num = f"▸ {i + 1}" if selected else f"  {i + 1}"
                val = item.get("sessionId", "N/A")
                if selected:
                    table.add_row(f"[cyan]{num}[/cyan]", f"[cyan]{val}[/cyan]")
                else:
                    table.add_row(num, val)

        elif view_type == "events":
            table.add_column("Time", width=11)
            table.add_column("Content", no_wrap=False)
            for i, item in enumerate(self.items):
                selected = i == self.cursor
                num = f"▸ {i + 1}" if selected else f"  {i + 1}"
                ts = str(item.get("eventTimestamp", ""))[11:19]
                role = self._extract_role(item)
                text = self._extract_text(item)

                if role and text:
                    role_prefix = "👤 User: " if role == "USER" else "🤖 Assistant: "
                    preview = (text[:60] + "…") if len(text) > 60 else text
                    content = f"{role_prefix}{preview}"
                else:
                    # Show raw payload snippet
                    content = self._extract_payload_snippet(item)

                if selected:
                    table.add_row(f"[cyan]{num}[/cyan]", f"[cyan]{ts}[/cyan]", f"[cyan]{content}[/cyan]")
                else:
                    table.add_row(num, ts, content)

        elif view_type == "namespaces":
            table.add_column("Strategy")
            table.add_column("Type", width=16)
            table.add_column("Namespace")
            for i, item in enumerate(self.items):
                selected = i == self.cursor
                num = f"▸ {i + 1}" if selected else f"  {i + 1}"
                strat = item.get("strategy", "")
                stype = item.get("type", "")
                ns = item.get("namespace", "")
                if selected:
                    table.add_row(
                        f"[cyan]{num}[/cyan]", f"[cyan]{strat}[/cyan]", f"[cyan]{stype}[/cyan]", f"[cyan]{ns}[/cyan]"
                    )
                else:
                    table.add_row(num, strat, stype, ns)

        elif view_type == "records":
            table.add_column("Created", width=19)
            table.add_column("Content", no_wrap=False)
            for i, item in enumerate(self.items):
                selected = i == self.cursor
                num = f"▸ {i + 1}" if selected else f"  {i + 1}"
                created = str(item.get("createdAt", ""))[:19]
                text = self._extract_record_text(item)
                preview = (text[:70] + "…") if text and len(text) > 70 else (text or "")
                if selected:
                    table.add_row(f"[cyan]{num}[/cyan]", f"[cyan]{created}[/cyan]", f"[cyan]{preview}[/cyan]")
                else:
                    table.add_row(num, created, preview)

        self.console.print(table)

    def _render_event_detail(self) -> None:
        """Render event detail view."""
        if self.current.event_index is not None and self.current.event_index < len(self.data.events):
            event = self.data.events[self.current.event_index]
            panel = self.visualizer.build_event_detail(event, self.verbose)
            self.console.print(panel)

    def _render_record_detail(self) -> None:
        """Render record detail view."""
        if self.current.record_index is not None and self.current.record_index < len(self.data.records):
            record = self.data.records[self.current.record_index]
            panel = self.visualizer.build_record_detail(record, self.verbose, namespace=self.current.namespace)
            self.console.print(panel)

    def _render_controls(self) -> None:
        """Render control hints."""
        self.console.print()

        # Show "load more" notice if applicable
        has_more = (self.current.view == "events" and self.events_next_token) or (
            self.current.view == "records" and self.records_next_token
        )
        if has_more:
            self.console.print("[yellow]More items available. Press \\[m] to load more.[/yellow]")
            self.console.print()

        controls = Text()
        controls.append("[↑↓]", style="bold cyan")
        controls.append(" navigate  ")
        controls.append("[Enter]", style="bold cyan")
        controls.append(" select  ")
        if self.current.view != "memory":
            controls.append("[b]", style="bold cyan")
            controls.append(" back  ")
            controls.append("[h]", style="bold cyan")
            controls.append(" home  ")
        controls.append("[v]", style="bold cyan")
        controls.append(" verbose  ")
        if self.current.view == "memory":
            controls.append("[a]", style="bold cyan")
            controls.append(" actors  ")
            controls.append("[n]", style="bold cyan")
            controls.append(" namespaces  ")
        else:
            controls.append("[m]", style="bold cyan")
            controls.append(" more  ")
        controls.append("[q]", style="bold cyan")
        controls.append(" quit")
        self.console.print(controls)

    def _load_view(self) -> None:
        """Load data for current view."""
        self.cursor = 0
        self.items = []

        loaders = {
            "memory": self._load_memory,
            "actors": self._load_actors,
            "sessions": self._load_sessions,
            "events": self._load_events,
            "namespaces": self._load_namespaces,
            "namespace_actors": self._load_actors,
            "namespace_sessions": self._load_sessions,
            "records": self._load_records,
        }

        try:
            loader = loaders.get(self.current.view)
            if loader:
                loader()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            logger.exception("ClientError loading view %s", self.current.view)
            self.console.print(f"[red]API Error ({error_code}): {error_msg}[/red]")
        except BotoCoreError as e:
            logger.exception("BotoCoreError loading view %s", self.current.view)
            self.console.print(f"[red]AWS Error: {e}[/red]")
        except Exception as e:
            logger.exception("Unexpected error loading view %s", self.current.view)
            self.console.print(f"[red]Error: {e}[/red]")

    def _load_memory(self) -> None:
        if not self.data.memory:
            self.data.memory = self.manager.get_memory(self.current.memory_id)
        self.items = [
            {"label": "👤 Actors (STM)", "view": "actors"},
            {"label": "📊 Namespaces (LTM)", "view": "namespaces"},
        ]

    def _load_actors(self, load_more: bool = False) -> None:
        # Use cached data if available (e.g., when navigating back)
        if not load_more and self.data.actors:
            self.items = self.data.actors
            return

        token = self.actors_next_token if load_more else None
        actors, self.actors_next_token = self.manager._paginated_list_page(
            self.manager._data_plane_client.list_actors,
            "actorSummaries",
            {"memoryId": self.current.memory_id},
            max_results=PAGE_SIZE,
            next_token=token,
        )

        if load_more:
            self.data.actors.extend(actors)
        else:
            self.data.actors = actors

        self.items = self.data.actors

    def _load_sessions(self, load_more: bool = False) -> None:
        # Use cached data if available (e.g., when navigating back)
        if not load_more and self.data.sessions:
            self.items = self.data.sessions
            return

        token = self.sessions_next_token if load_more else None
        sessions, self.sessions_next_token = self.manager._paginated_list_page(
            self.manager._data_plane_client.list_sessions,
            "sessionSummaries",
            {"memoryId": self.current.memory_id, "actorId": self.current.actor_id},
            max_results=PAGE_SIZE,
            next_token=token,
        )

        if load_more:
            self.data.sessions.extend(sessions)
        else:
            self.data.sessions = sessions

        self.items = self.data.sessions

    def _load_events(self, load_more: bool = False) -> None:
        # Use cached data if available (e.g., when navigating back)
        if not load_more and self.data.events:
            self.items = self.data.events
            return

        token = self.events_next_token if load_more else None
        events, self.events_next_token = self.manager._paginated_list_page(
            self.manager._data_plane_client.list_events,
            "events",
            {
                "memoryId": self.current.memory_id,
                "actorId": self.current.actor_id,
                "sessionId": self.current.session_id,
            },
            max_results=PAGE_SIZE,
            next_token=token,
        )

        if load_more:
            self.data.events.extend(events)
        else:
            self.data.events = events

        self.data.events.sort(key=lambda e: e.get("eventTimestamp", ""), reverse=True)
        self.items = self.data.events

    def _load_namespaces(self) -> None:
        if not self.data.memory:
            self.data.memory = self.manager.get_memory(self.current.memory_id)
        strategies = self.data.memory.get("strategies") or self.data.memory.get("memoryStrategies") or []
        self.data.namespaces = []
        for s in strategies:
            stype = s.get("type") or s.get("memoryStrategyType", "")
            for ns in s.get("namespaces", []):
                self.data.namespaces.append({"strategy": s.get("name"), "type": stype, "namespace": ns})
        self.items = self.data.namespaces

    def _load_records(self, load_more: bool = False) -> None:
        # Use cached data if available (e.g., when navigating back)
        if not load_more and self.data.records:
            self.items = self.data.records
            return

        token = self.records_next_token if load_more else None
        records, self.records_next_token = self.manager._paginated_list_page(
            self.manager._data_plane_client.list_memory_records,
            "memoryRecordSummaries",
            {"memoryId": self.current.memory_id, "namespace": self.current.namespace},
            max_results=PAGE_SIZE,
            next_token=token,
        )

        if load_more:
            self.data.records.extend(records)
        else:
            self.data.records = records

        self.data.records.sort(key=lambda r: r.get("createdAt", ""), reverse=True)
        self.items = self.data.records

    def _cursor_up(self) -> None:
        """Move cursor up."""
        if self.cursor > 0:
            self.cursor -= 1

    def _cursor_down(self) -> None:
        """Move cursor down."""
        if self.cursor < len(self.items) - 1:
            self.cursor += 1

    def _push_state(self) -> None:
        """Push current state to navigation stack."""
        self.current.cursor = self.cursor
        self.nav_stack.append(replace(self.current))

    def _go_back(self) -> None:
        """Navigate back."""
        if self.nav_stack:
            self.current = self.nav_stack.pop()
            self._load_view()
            self.cursor = self.current.cursor

    def _select(self) -> None:
        """Select current item."""
        if not self.items:
            return

        handlers = {
            "memory": self._select_memory_item,
            "actors": self._select_actor,
            "sessions": self._select_session,
            "events": self._select_event,
            "namespaces": self._select_namespace,
            "namespace_actors": self._select_namespace_actor,
            "namespace_sessions": self._select_namespace_session,
            "records": self._select_record,
        }

        handler = handlers.get(self.current.view)
        if handler:
            handler()

    def _select_memory_item(self) -> None:
        self._push_state()
        self.current.view = self.items[self.cursor]["view"]
        self._load_view()

    def _select_actor(self) -> None:
        self._push_state()
        self.current.actor_id = self.items[self.cursor].get("actorId")
        self.current.view = "sessions"
        self.data.sessions = []  # Clear cache for new actor
        self.sessions_next_token = None
        self._load_view()

    def _select_session(self) -> None:
        self._push_state()
        self.current.session_id = self.items[self.cursor].get("sessionId")
        self.current.view = "events"
        self.data.events = []  # Clear cache for new session
        self.events_next_token = None
        self._load_view()

    def _select_event(self) -> None:
        self._push_state()
        self.current.event_index = self.cursor
        self.current.view = "event_detail"

    def _select_namespace(self) -> None:
        ns_info = self.items[self.cursor]
        ns_template = ns_info.get("namespace", "")
        self._push_state()
        self.current.namespace_template = ns_template

        if "{actorId}" in ns_template or "{sessionId}" in ns_template:
            self.current.view = "namespace_actors"
            self._load_view()
        else:
            self.current.namespace = ns_template
            self.current.view = "records"
            self.data.records = []  # Clear cache for new namespace
            self.records_next_token = None
            self._load_view()

    def _select_namespace_actor(self) -> None:
        self._push_state()
        actor_id = self.items[self.cursor].get("actorId")
        self.current.actor_id = actor_id
        ns = self.current.namespace_template.replace("{actorId}", actor_id)

        if "{sessionId}" in ns:
            self.current.view = "namespace_sessions"
            self._load_view()
        else:
            self.current.namespace = ns
            self.current.view = "records"
            self.data.records = []  # Clear cache for new namespace
            self.records_next_token = None
            self._load_view()

    def _select_namespace_session(self) -> None:
        self._push_state()
        session_id = self.items[self.cursor].get("sessionId")
        self.current.session_id = session_id
        ns = self.current.namespace_template.replace("{actorId}", self.current.actor_id)
        ns = ns.replace("{sessionId}", session_id)
        self.current.namespace = ns
        self.current.view = "records"
        self.data.records = []  # Clear cache for new namespace
        self.records_next_token = None
        self._load_view()

    def _select_record(self) -> None:
        self._push_state()
        self.current.record_index = self.cursor
        self.current.view = "record_detail"

    def _extract_role(self, event: Dict[str, Any]) -> str:
        """Extract role from event."""
        payload = event.get("payload", {})
        if isinstance(payload, dict):
            content = payload.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "role" in item:
                        return item["role"]
        return ""

    def _extract_text(self, event: Dict[str, Any]) -> str:
        """Extract text from event."""
        payload = event.get("payload", {})
        if isinstance(payload, dict):
            content = payload.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        return item["text"]
        return ""

    def _extract_payload_snippet(self, event: Dict[str, Any]) -> str:
        """Extract a snippet from raw payload for preview."""
        payload = event.get("payload")
        if not payload:
            return "(empty)"
        raw = json.dumps(payload, default=str)
        if len(raw) > 60:
            return f"{raw[:60]}…"
        return raw

    def _extract_record_text(self, record: Dict[str, Any]) -> str:
        """Extract text from record."""
        content = record.get("content", {})
        if isinstance(content, dict):
            return content.get("text", str(content))
        return str(content) if content else ""
