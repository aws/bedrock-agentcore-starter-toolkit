"""Notebook interface for memory - thin wrappers over CLI operations."""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.tree import Tree

from ...operations.memory import MemoryManager
from ...operations.memory.memory_visualizer import MemoryVisualizer


def _resolve_memory_config(
    agent_name: Optional[str] = None,
    memory_id: Optional[str] = None,
    region: Optional[str] = None,
) -> tuple:
    """Resolve memory_id and region from args or config."""
    import boto3

    from ...cli.memory.commands import _get_memory_config_from_file

    final_memory_id = memory_id
    final_region = region

    if not final_memory_id:
        config = _get_memory_config_from_file(agent_name)
        if config:
            final_memory_id = config.get("memory_id")
            if not final_region:
                final_region = config.get("region")

    if not final_region:
        session = boto3.Session()
        final_region = session.region_name

    if not final_memory_id:
        raise ValueError("No memory_id specified. Provide memory_id or run from directory with .bedrock_agentcore.yaml")

    console = Console()
    manager = MemoryManager(region_name=final_region, console=console)
    return final_memory_id, final_region, manager, console


class Memory:
    """Notebook interface for memory - mirrors CLI commands.

    Example:
        >>> from bedrock_agentcore_starter_toolkit.notebook import Memory
        >>>
        >>> mem = Memory(memory_id="mem-abc123", region="us-east-1")
        >>> mem.show()                          # Memory details
        >>> mem.show_events()                   # Latest event
        >>> mem.show_events(all=True)           # Events tree
        >>> mem.show_records()                  # Latest record
        >>> mem.show_records(all=True)          # Records tree
    """

    def __init__(
        self,
        memory_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize Memory interface."""
        self.memory_id, self.region, self.manager, self.console = _resolve_memory_config(agent_name, memory_id, region)
        self.visualizer = MemoryVisualizer(self.console)

    def show(self, verbose: bool = False) -> Dict[str, Any]:
        """Show memory details (equivalent to `agentcore memory show`)."""
        memory = self.manager.get_memory(self.memory_id)
        self.visualizer.visualize_memory(memory, verbose=verbose)
        return dict(memory.items()) if hasattr(memory, "items") else memory._data

    def show_events(
        self,
        all: bool = False,
        actor_id: Optional[str] = None,
        session_id: Optional[str] = None,
        last: int = 1,
        list_actors: bool = False,
        list_sessions: bool = False,
        verbose: bool = False,
        max_events: int = 10,
    ) -> List[Dict[str, Any]]:
        """Show memory events (equivalent to `agentcore memory show events`)."""
        from ...cli.memory.commands import _collect_all_events

        # List actors mode
        if list_actors:
            actors = self.manager.list_actors(self.memory_id)
            tree = Tree(f"🧠 [bold cyan]{self.memory_id}[/bold cyan]")
            for a in actors:
                tree.add(f"👤 {a.get('actorId')}")
            self.console.print(tree)
            return actors

        # List sessions mode
        if list_sessions:
            if not actor_id:
                raise ValueError("list_sessions requires actor_id")
            sessions = self.manager.list_sessions(self.memory_id, actor_id)
            tree = Tree(f"🧠 [bold cyan]{self.memory_id}[/bold cyan]")
            actor_tree = tree.add(f"👤 [bold]{actor_id}[/bold]")
            for s in sessions:
                actor_tree.add(f"📁 [cyan]{s.get('sessionId')}[/cyan]")
            self.console.print(tree)
            return sessions

        if all:
            # Show events tree
            self.visualizer.display_events_tree(
                self.memory_id,
                self.manager,
                max_actors=10,
                max_sessions=10,
                max_events=max_events,
                actor_id=actor_id,
                session_id=session_id,
                output=None,
                verbose=verbose,
            )
            return _collect_all_events(self.manager, self.memory_id)
        else:
            # Show Nth most recent event
            all_events = _collect_all_events(self.manager, self.memory_id)
            if not all_events:
                self.console.print("[yellow]No events found[/yellow]")
                return []

            all_events.sort(key=lambda e: e.get("eventTimestamp", ""), reverse=True)
            if last > len(all_events):
                last = len(all_events)

            event = all_events[last - 1]
            self.visualizer.display_single_event(event, last, len(all_events), verbose)
            return [event]

    def show_records(
        self,
        all: bool = False,
        namespace: Optional[str] = None,
        query: Optional[str] = None,
        last: int = 1,
        verbose: bool = False,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Show memory records (equivalent to `agentcore memory show records`)."""
        from ...cli.memory.commands import _collect_all_records

        if all:
            if namespace:
                raise ValueError("Use namespace without all to drill into a namespace")
            self.visualizer.display_records_tree(self.manager, self.memory_id, verbose, max_results, None)
            return _collect_all_records(self.manager, self.memory_id, None, max_results)
        elif namespace and not query:
            self.visualizer.display_namespace_records(
                self.manager, self.memory_id, namespace, verbose, max_results, None
            )
            return self.manager.list_records(self.memory_id, namespace, max_results)
        elif query:
            if not namespace:
                raise ValueError("namespace required for semantic search")
            records = self.manager.search_records(self.memory_id, namespace, query, max_results)
            if records:
                self.visualizer.display_search_results(records, query, verbose)
            return records
        else:
            # Show Nth most recent record
            all_records = _collect_all_records(self.manager, self.memory_id, namespace, max_results)
            if not all_records:
                self.console.print("[yellow]No records found[/yellow]")
                return []

            all_records.sort(key=lambda r: r.get("createdAt", ""), reverse=True)
            if last > len(all_records):
                last = len(all_records)

            record = all_records[last - 1]
            self.visualizer.display_single_record(record, last, len(all_records), verbose)
            return [record]
