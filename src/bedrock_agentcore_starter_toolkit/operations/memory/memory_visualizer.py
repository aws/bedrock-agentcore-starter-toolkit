"""Memory visualization with tree and table views."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .memory_formatters import (
    DisplayConfig,
    extract_event_role,
    extract_event_text,
    extract_event_type,
    extract_record_text,
    format_content_preview,
    format_memory_age,
    format_namespaces,
    format_role_icon,
    format_truncation_hint,
    get_memory_status_icon,
    get_memory_status_style,
    get_strategy_status_style,
    get_strategy_type_icon,
    render_content_panel,
    truncate_text,
)

logger = logging.getLogger(__name__)


class MemoryVisualizer:
    """Visualizer for displaying memory resources in human-readable format."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the memory visualizer."""
        self.console = console or Console()

    # ==================== Memory Details ====================

    def visualize_memory(
        self, memory: Dict[str, Any], verbose: bool = False, actor_count: Optional[int] = None
    ) -> None:
        """Visualize a memory resource as a hierarchical tree."""
        data = self._extract_memory_data(memory)

        memory_id = data.get("id") or data.get("memoryId", "Unknown")
        name = data.get("name", "Unknown")
        status = data.get("status", "UNKNOWN")

        tree = Tree(self._format_memory_header(memory_id, name, status), guide_style="cyan")

        self._add_memory_info(tree, data, verbose, actor_count)
        self._add_memory_strategies(tree, data, verbose)

        self.console.print(tree)

    def _extract_memory_data(self, memory: Any) -> Dict[str, Any]:
        """Extract data dict from memory object."""
        if hasattr(memory, "get"):
            return memory
        return memory.__dict__ if hasattr(memory, "__dict__") else {}

    def _format_memory_header(self, memory_id: str, name: str, status: str) -> Text:
        """Format the memory tree header."""
        icon = get_memory_status_icon(status)
        style = get_memory_status_style(status)

        header = Text()
        header.append("🧠 Memory: ", style="bold cyan")
        header.append(name, style="bold white")
        header.append(f" ({icon}{status})", style=style)
        return header

    def _add_memory_info(self, tree: Tree, data: Dict[str, Any], verbose: bool, actor_count: Optional[int]) -> None:
        """Add info section to memory tree."""
        info_branch = tree.add("📋 [bold]Info[/bold]")

        info_branch.add(f"[dim]ID:[/dim] {data.get('id') or data.get('memoryId', 'Unknown')}")
        info_branch.add(f"[dim]Name:[/dim] {data.get('name', 'Unknown')}")

        if data.get("description"):
            info_branch.add(f"[dim]Description:[/dim] {data['description']}")
        if data.get("eventExpiryDuration"):
            info_branch.add(f"[dim]Event Expiry:[/dim] {data['eventExpiryDuration']} days")
        if data.get("createdAt"):
            info_branch.add(f"[dim]Created:[/dim] {format_memory_age(data['createdAt'])}")

        if verbose:
            if data.get("updatedAt"):
                info_branch.add(f"[dim]Updated:[/dim] {format_memory_age(data['updatedAt'])}")
            if data.get("arn"):
                info_branch.add(f"[dim]ARN:[/dim] {data['arn']}")
            if data.get("memoryExecutionRoleArn"):
                info_branch.add(f"[dim]Role ARN:[/dim] {data['memoryExecutionRoleArn']}")

        if actor_count is not None:
            info_branch.add(f"[dim]Actors:[/dim] {actor_count}")

    def _add_memory_strategies(self, tree: Tree, data: Dict[str, Any], verbose: bool) -> None:
        """Add strategies section to memory tree."""
        strategies = data.get("strategies") or data.get("memoryStrategies") or []

        if not strategies:
            tree.add("[dim]No strategies configured[/dim]")
            return

        strategies_branch = tree.add(f"📊 [bold]Strategies[/bold] ({len(strategies)})")
        for strategy in strategies:
            self._add_strategy_node(strategies_branch, strategy, verbose)

    def _add_strategy_node(self, parent: Tree, strategy: Dict[str, Any], verbose: bool) -> None:
        """Add a strategy node to the tree."""
        strategy_name = strategy.get("name", "Unnamed")
        strategy_type = strategy.get("type") or strategy.get("memoryStrategyType", "UNKNOWN")
        strategy_status = strategy.get("status", "UNKNOWN")

        header = self._format_strategy_header(strategy_name, strategy_type, strategy_status)
        strategy_branch = parent.add(header)

        if strategy.get("strategyId"):
            strategy_branch.add(f"[dim]ID:[/dim] {strategy['strategyId']}")
        if strategy.get("description"):
            strategy_branch.add(f"[dim]Description:[/dim] {strategy['description']}")

        namespaces = strategy.get("namespaces", [])
        if namespaces:
            strategy_branch.add(f"[dim]Namespaces:[/dim] {format_namespaces(namespaces)}")

        if verbose:
            if strategy.get("createdAt"):
                strategy_branch.add(f"[dim]Created:[/dim] {format_memory_age(strategy['createdAt'])}")
            if strategy.get("updatedAt"):
                strategy_branch.add(f"[dim]Updated:[/dim] {format_memory_age(strategy['updatedAt'])}")
            if strategy.get("configuration"):
                self._add_config_tree(strategy_branch, strategy["configuration"])

    def _format_strategy_header(self, name: str, strategy_type: str, status: str) -> Text:
        """Format strategy header text."""
        type_icon = get_strategy_type_icon(strategy_type)
        status_icon = get_memory_status_icon(status)
        status_style = get_strategy_status_style(status)

        header = Text()
        if type_icon:
            header.append(f"{type_icon} ", style="bold")
        header.append(name, style="bold white")
        header.append(f" [{strategy_type}]", style="dim")
        header.append(f" ({status_icon}{status})", style=status_style)
        return header

    def _add_config_tree(self, parent: Tree, config: Dict[str, Any]) -> None:
        """Add configuration subtree."""
        config_branch = parent.add("[dim]Configuration:[/dim]")
        for key, value in config.items():
            if isinstance(value, dict):
                sub_branch = config_branch.add(f"[cyan]{key}:[/cyan]")
                self._add_config_tree(sub_branch, value)
            else:
                config_branch.add(f"[cyan]{key}:[/cyan] {value}")

    # ==================== Memory List ====================

    def display_memory_list(self, memories: List[Dict[str, Any]], manager: Any = None) -> None:
        """Display memories in a table format."""
        if not memories:
            self.console.print("[yellow]No memories found.[/yellow]")
            return

        table = Table(title=f"Memory Resources ({len(memories)})")
        table.add_column("#", style="dim", width=3)
        table.add_column("Memory ID", style="cyan", no_wrap=False)
        table.add_column("Status", justify="center", width=12)
        table.add_column("Created", style="dim", width=10)
        table.add_column("Updated", style="dim", width=10)

        for idx, memory in enumerate(memories, 1):
            row = self._format_memory_row(memory, manager)
            table.add_row(str(idx), *row)

        self.console.print(table)
        self.console.print(f"\n[green]✓[/green] Found {len(memories)} memories")

    def _format_memory_row(self, memory: Any, manager: Any) -> tuple:
        """Format a single memory row for the table."""
        data = self._extract_memory_data(memory)
        if not data and hasattr(memory, "_data"):
            data = memory._data

        memory_id = data.get("id") or data.get("memoryId", "N/A")
        name = data.get("name", "")
        status = data.get("status", "UNKNOWN")
        created = data.get("createdAt")
        updated = data.get("updatedAt")

        # Format ID column
        id_display = Text()
        if name and name != memory_id:
            id_display.append(name, style="bold")
            id_display.append(f"\n{memory_id}", style="dim")
        else:
            id_display.append(memory_id)

        # Format status
        status_icon = get_memory_status_icon(status)
        status_style = get_memory_status_style(status)
        status_display = Text(f"{status_icon}{status}", style=status_style)

        # Format ages
        created_age = format_memory_age(created) if created else "N/A"
        updated_age = format_memory_age(updated) if updated else "N/A"

        return (id_display, status_display, created_age, updated_age)

    # ==================== Events Tree ====================

    def display_events_tree(
        self,
        memory_id: str,
        manager: Any,
        max_actors: int = 10,
        max_sessions: int = 10,
        max_events: int = 10,
        actor_id: Optional[str] = None,
        session_id: Optional[str] = None,
        output: Optional[str] = None,
        verbose: bool = False,
    ) -> None:
        """Display events as a tree: memory -> actors -> sessions -> events."""
        actors, total_actors = self._get_actors(manager, memory_id, actor_id, max_actors)

        if not actors:
            self.console.print(f"[yellow]No actors found in memory {memory_id}[/yellow]")
            return

        root = Tree(f"🧠 [bold cyan]{memory_id}[/bold cyan]")
        export_data = {"memoryId": memory_id, "actors": []}

        for actor in actors:
            actor_data = self._build_actor_subtree(
                root, manager, memory_id, actor, max_sessions, max_events, session_id, verbose
            )
            export_data["actors"].append(actor_data)

        # Add truncation hint
        if total_actors > max_actors and not actor_id:
            root.add(f"[dim]Showing {max_actors} of {total_actors} actors. Use --list-actors to see all.[/dim]")

        self._output_or_print(root, export_data, output, "events")

    def _get_actors(self, manager: Any, memory_id: str, actor_id: Optional[str], max_actors: int) -> tuple:
        """Get actors list (filtered or all)."""
        if actor_id:
            return [{"actorId": actor_id}], 1
        all_actors = manager.list_actors(memory_id)
        return all_actors[:max_actors], len(all_actors)

    def _build_actor_subtree(
        self,
        root: Tree,
        manager: Any,
        memory_id: str,
        actor: Dict[str, Any],
        max_sessions: int,
        max_events: int,
        session_id: Optional[str],
        verbose: bool,
    ) -> Dict[str, Any]:
        """Build actor subtree with sessions and events."""
        aid = actor.get("actorId", "N/A")
        actor_data = {"actorId": aid, "sessions": []}

        try:
            sessions, total_sessions = self._get_sessions(manager, memory_id, aid, session_id, max_sessions)
            actor_tree = root.add(f"👤 [bold]{aid}[/bold] ({total_sessions} sessions)")

            for session in sessions:
                session_data = self._build_session_subtree(
                    actor_tree, manager, memory_id, aid, session, max_events, verbose
                )
                actor_data["sessions"].append(session_data)

            if total_sessions > max_sessions and not session_id:
                actor_tree.add(format_truncation_hint(max_sessions, total_sessions))

        except Exception:
            root.add(f"👤 [bold]{aid}[/bold] [dim red](error)[/dim red]")

        return actor_data

    def _get_sessions(
        self, manager: Any, memory_id: str, actor_id: str, session_id: Optional[str], max_sessions: int
    ) -> tuple:
        """Get sessions list (filtered or all)."""
        if session_id:
            return [{"sessionId": session_id}], 1
        all_sessions = manager.list_sessions(memory_id, actor_id)
        return all_sessions[:max_sessions], len(all_sessions)

    def _build_session_subtree(
        self,
        actor_tree: Tree,
        manager: Any,
        memory_id: str,
        actor_id: str,
        session: Dict[str, Any],
        max_events: int,
        verbose: bool,
    ) -> Dict[str, Any]:
        """Build session subtree with events."""
        sid = session.get("sessionId", "N/A")
        session_data = {"sessionId": sid, "events": []}

        try:
            events = manager.list_events(memory_id, actor_id, sid, max_results=max_events)
            events.sort(key=lambda e: e.get("eventTimestamp", ""))

            session_tree = actor_tree.add(f"📁 [cyan]{sid}[/cyan] ({len(events)} events)")

            # Group by branch
            branches = self._group_events_by_branch(events)

            for branch_name, branch_events in branches.items():
                branch_tree = session_tree.add(f"🌿 [dim]{branch_name}[/dim]")
                for event in branch_events:
                    self._add_event_node(branch_tree, event, verbose)
                    session_data["events"].append(event)

        except Exception:
            actor_tree.add(f"📁 [cyan]{sid}[/cyan] [dim red](error)[/dim red]")

        return session_data

    def _group_events_by_branch(self, events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group events by branch name."""
        branches: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            branch_name = event.get("branch", {}).get("name", "main")
            if branch_name not in branches:
                branches[branch_name] = []
            branches[branch_name].append(event)
        return branches

    def _add_event_node(self, branch_tree: Tree, event: Dict[str, Any], verbose: bool) -> None:
        """Add a single event node to the tree."""
        timestamp = str(event.get("eventTimestamp", ""))[:19]
        text_content = extract_event_text(event)
        role = extract_event_role(event)
        event_type = extract_event_type(event)

        if text_content:
            if verbose:
                role_label = format_role_icon(role)
                branch_tree.add(Panel(text_content.strip(), title=role_label, border_style="dim", padding=(0, 1)))
            else:
                preview = format_content_preview(text_content)
                role_prefix = "[cyan]👤 User:[/cyan]" if role == "USER" else "[green]🤖 Assistant:[/green]"
                branch_tree.add(f"{role_prefix} {preview}")
        elif event_type == "blob":
            branch_tree.add(f"[dim]{timestamp} (blob)[/dim]")
        else:
            branch_tree.add(f"[dim]{timestamp}[/dim]")

    # ==================== Single Event/Record Display ====================

    def display_single_event(self, event: Dict[str, Any], nth: int, total: int, verbose: bool) -> None:
        """Display a single event with details."""
        self.console.print(f"[bold]Event[/bold] ({self._format_position_label(nth, total)})\n")

        self.console.print(f"[dim]Event ID:[/dim]   {event.get('eventId', 'N/A')}")
        self.console.print(f"[dim]Timestamp:[/dim]  {event.get('eventTimestamp', 'N/A')}")
        self.console.print(f"[dim]Actor:[/dim]      {event.get('_actorId', event.get('actorId', 'N/A'))}")
        self.console.print(f"[dim]Session:[/dim]    {event.get('_sessionId', event.get('sessionId', 'N/A'))}")

        branch = event.get("branch", {}).get("name")
        if branch:
            self.console.print(f"[dim]Branch:[/dim]     {branch}")

        role = extract_event_role(event)
        if role:
            self.console.print(f"[dim]Role:[/dim]       {format_role_icon(role)}")

        text_content = extract_event_text(event)
        if text_content:
            self.console.print()
            self._print_content_panel(text_content, verbose)

    def display_single_record(self, record: Dict[str, Any], nth: int, total: int, verbose: bool) -> None:
        """Display a single record with details."""
        self.console.print(f"[bold]Record[/bold] ({self._format_position_label(nth, total)})\n")

        self.console.print(f"[dim]Record ID:[/dim]  {record.get('memoryRecordId', record.get('recordId', 'N/A'))}")
        self.console.print(f"[dim]Namespace:[/dim]  {record.get('_namespace', 'N/A')}")
        self.console.print(f"[dim]Created:[/dim]    {record.get('createdAt', 'N/A')}")

        text_content = extract_record_text(record)
        if text_content:
            self.console.print()
            self._print_content_panel(text_content, verbose)

    def _format_position_label(self, nth: int, total: int) -> str:
        """Format position label (latest, #2 most recent, etc.)."""
        return "latest" if nth == 1 else f"#{nth} most recent"

    def _print_content_panel(self, text: str, verbose: bool) -> None:
        """Print content with appropriate formatting."""
        if verbose:
            self.console.print(Panel(text, title="Content", border_style="dim"))
        else:
            display = truncate_text(text, DisplayConfig.MAX_CONTENT_LENGTH)
            self.console.print(Panel(display, title="Content", border_style="dim"))

    # ==================== Records Display ====================

    def display_namespace_records(
        self,
        manager: Any,
        memory_id: str,
        namespace: str,
        verbose: bool,
        max_results: int,
        output: Optional[str] = None,
    ) -> None:
        """Display records for a specific namespace."""
        root = Tree(f"🧠 [bold cyan]{memory_id}[/bold cyan]")
        export_data = {"memoryId": memory_id, "namespace": namespace, "records": []}

        try:
            records = manager.list_records(memory_id, namespace, max_results)
            if records:
                self._add_records_to_tree(root, namespace, records, verbose, export_data["records"])
            else:
                root.add(f"[yellow]No records in {namespace}[/yellow]")
        except Exception as e:
            root.add(f"[red]Error: {e}[/red]")

        self._output_or_print(root, export_data, output, "records")

    def display_records_tree(
        self,
        manager: Any,
        memory_id: str,
        verbose: bool,
        max_results: int,
        output: Optional[str] = None,
    ) -> None:
        """Display records as a tree by namespace."""
        memory = manager.get_memory(memory_id)
        strategies = memory.get("strategies") or memory.get("memoryStrategies") or []

        root = Tree(f"🧠 [bold cyan]{memory_id}[/bold cyan]")
        export_data = {"memoryId": memory_id, "namespaces": []}

        for strategy in strategies:
            self._add_strategy_records(root, manager, memory_id, strategy, verbose, max_results, export_data)

        self._output_or_print(root, export_data, output, "records")

    def _add_strategy_records(
        self,
        root: Tree,
        manager: Any,
        memory_id: str,
        strategy: Dict[str, Any],
        verbose: bool,
        max_results: int,
        export_data: Dict[str, Any],
    ) -> None:
        """Add strategy records subtree."""
        strategy_name = strategy.get("name", "Unknown")
        strategy_type = strategy.get("type") or strategy.get("memoryStrategyType", "")
        strategy_branch = root.add(f"📊 [bold]{strategy_name}[/bold] [{strategy_type}]")

        for ns_template in strategy.get("namespaces", []):
            ns_data = {"template": ns_template, "records": []}
            resolved = self._resolve_namespace(manager, memory_id, ns_template)

            for ns in resolved[: DisplayConfig.MAX_ACTORS]:
                try:
                    records = manager.list_records(memory_id, ns, max_results)
                    if records:
                        self._add_records_to_tree(strategy_branch, ns, records, verbose, ns_data["records"])
                except Exception as e:
                    logger.debug("Error listing records for namespace %s: %s", ns, e)

            if ns_data["records"]:
                export_data["namespaces"].append(ns_data)

    def _add_records_to_tree(
        self,
        parent: Tree,
        namespace: str,
        records: List[Dict[str, Any]],
        verbose: bool,
        export_list: List[Dict[str, Any]],
    ) -> None:
        """Add records to a tree branch."""
        records.sort(key=lambda r: r.get("createdAt", ""))
        total = len(records)
        display_count = min(total, DisplayConfig.MAX_RECORDS_PER_NAMESPACE)

        ns_branch = parent.add(f"📁 [cyan]{namespace}[/cyan] ({total} records)")

        for record in records[:display_count]:
            text = extract_record_text(record)
            content = render_content_panel(text, verbose)
            ns_branch.add(content)
            export_list.append(record)

        hint = format_truncation_hint(display_count, total)
        if hint:
            ns_branch.add(hint)

    def _resolve_namespace(self, manager: Any, memory_id: str, ns_template: str) -> List[str]:
        """Resolve namespace template to actual namespaces."""
        if "{actorId}" not in ns_template and "{sessionId}" not in ns_template:
            return [ns_template]

        resolved = []
        try:
            actors = manager.list_actors(memory_id)
            for actor in actors[: DisplayConfig.MAX_ACTORS]:
                actor_id = actor.get("actorId", "")
                ns = ns_template.replace("{actorId}", actor_id)

                if "{sessionId}" in ns:
                    sessions = manager.list_sessions(memory_id, actor_id)
                    for sess in sessions[: DisplayConfig.MAX_SESSIONS]:
                        session_id = sess.get("sessionId", "")
                        resolved.append(ns.replace("{sessionId}", session_id))
                else:
                    resolved.append(ns)
        except Exception as e:
            logger.debug("Error resolving namespace template %s: %s", ns_template, e)

        return resolved

    def display_search_results(self, records: List[Dict[str, Any]], query: str, verbose: bool) -> None:
        """Display semantic search results."""
        self.console.print(f'[bold]Search Results[/bold] for "{query}" ({len(records)} found)\n')

        table = Table(box=ROUNDED)
        table.add_column("#", width=3, style="dim")
        table.add_column("Score", width=6)
        table.add_column("Content", no_wrap=False)

        for i, record in enumerate(records, 1):
            score = record.get("score", 0)
            text = extract_record_text(record)
            preview = format_content_preview(text, verbose)
            table.add_row(str(i), f"{score:.2f}", preview)

        self.console.print(table)

    # ==================== Utility Methods ====================

    def _output_or_print(self, tree: Tree, data: Dict[str, Any], output: Optional[str], label: str) -> None:
        """Output to file or print to console."""
        if output:
            path = Path(output)
            with path.open("w") as f:
                json.dump(data, f, indent=2, default=str)
            self.console.print(f"[green]✓[/green] Exported {label} to {path}")
        else:
            self.console.print(tree)
