"""Bedrock AgentCore Memory CLI - Command line interface for Memory operations."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.panel import Panel
from rich.tree import Tree

from ...operations.memory import MemoryManager
from ...operations.memory.memory_visualizer import MemoryVisualizer
from ..common import _handle_error, console

logger = logging.getLogger(__name__)

# Create a Typer app for memory commands
memory_app = typer.Typer(help="Manage Bedrock AgentCore Memory resources")

# Create subcommand group for data plane visualization
show_app = typer.Typer(help="Show memory data (actors, sessions, events, records)", invoke_without_command=True)
memory_app.add_typer(show_app, name="show")

BROWSE_MAX_ITEMS = 50


# ==================== Config Resolution Utilities ====================


@dataclass
class ResolvedMemoryConfig:
    """Resolved memory configuration from explicit params or config file."""

    memory_id: str
    region: Optional[str]


@dataclass
class _ConfigLookupResult:
    """Result of looking up memory config from file."""

    memory_id: Optional[str] = None
    region: Optional[str] = None
    config_exists: bool = False
    agent_name: Optional[str] = None  # The resolved agent name (could be default)


def _get_memory_config_from_file(agent_name: Optional[str] = None) -> _ConfigLookupResult:
    """Load memory config from .bedrock_agentcore.yaml if it exists.

    Returns _ConfigLookupResult with details about what was found.
    """
    from ...utils.runtime.config import load_config_if_exists

    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    config = load_config_if_exists(config_path)

    if not config:
        return _ConfigLookupResult(config_exists=False)

    try:
        agent_config = config.get_agent_config(agent_name)
        resolved_agent = agent_name or config.default_agent or "default"
        memory_id = agent_config.memory.memory_id if agent_config.memory else None
        region = agent_config.aws.region

        return _ConfigLookupResult(
            memory_id=memory_id,
            region=region,
            config_exists=True,
            agent_name=resolved_agent,
        )
    except Exception as e:
        logger.debug("Failed to load memory config: %s", e)
        return _ConfigLookupResult(config_exists=True, agent_name=agent_name)


def _resolve_memory_config(
    agent: Optional[str] = None,
    memory_id: Optional[str] = None,
    region: Optional[str] = None,
    show_hint: bool = True,
) -> ResolvedMemoryConfig:
    """Resolve memory configuration from explicit params or config file.

    Args:
        agent: Agent name from config file.
        memory_id: Explicit memory ID (takes precedence).
        region: Explicit region (takes precedence).
        show_hint: Whether to show console hint when using config.

    Returns:
        ResolvedMemoryConfig with memory_id and region.

    Raises:
        typer.Exit: If no memory_id can be resolved.
    """
    final_memory_id = memory_id
    final_region = region
    config_result: Optional[_ConfigLookupResult] = None

    if not final_memory_id:
        config_result = _get_memory_config_from_file(agent)
        if config_result.memory_id:
            final_memory_id = config_result.memory_id
            if not final_region:
                final_region = config_result.region
            if show_hint:
                console.print(f"[dim]Using memory from config: {final_memory_id}[/dim]\n")

    if not final_memory_id:
        # Build context-specific error message
        if config_result and config_result.config_exists:
            agent_desc = f"'{config_result.agent_name}'" if config_result.agent_name else "default agent"
            _handle_error(
                f"Found .bedrock_agentcore.yaml but {agent_desc} has no memory_id configured.\n\n"
                "This usually means you need to run 'agentcore launch' first to create the memory,\n"
                "or provide memory directly via --memory-id MEM_ID"
            )
        else:
            _handle_error(
                "No memory specified and no .bedrock_agentcore.yaml found.\n\n"
                "Provide memory via:\n"
                "  1. --memory-id MEM_ID\n"
                "  2. --agent AGENT_NAME (defaults to default_agent in config)\n"
                "  3. Run from directory with .bedrock_agentcore.yaml"
            )

    # Resolve region from boto3 if not set
    if not final_region:
        import boto3

        session = boto3.Session()
        final_region = session.region_name

    return ResolvedMemoryConfig(memory_id=final_memory_id, region=final_region)


# ==================== Validation Utilities ====================


def _validate_events_options(
    all_events: bool,
    last: int,
    session_id: Optional[str],
    actor_id: Optional[str],
    list_sessions: bool,
) -> None:
    """Validate mutually exclusive options for events command."""
    if all_events and last != 1:
        _handle_error("Cannot use --all and --last together")

    if session_id and not actor_id:
        _handle_error("--session-id requires --actor-id")

    if list_sessions and not actor_id:
        _handle_error("--list-sessions requires --actor-id")


def _validate_records_options(
    all_records: bool,
    last: int,
    namespace: Optional[str],
    query: Optional[str],
) -> None:
    """Validate mutually exclusive options for records command."""
    if all_records and last != 1:
        _handle_error("Cannot use --all and --last together")

    if all_records and namespace:
        _handle_error("Use --namespace without --all to drill into a namespace")

    if query and not namespace:
        _handle_error("--namespace required for semantic search")


# ==================== Data Collection Utilities ====================


def _collect_all_events(manager: MemoryManager, memory_id: str) -> List[Dict[str, Any]]:
    """Collect all events across all actors/sessions in a memory."""
    all_events = []
    actors = manager.list_actors(memory_id)
    for actor in actors:
        actor_id = actor.get("actorId")
        if not actor_id:
            continue
        sessions = manager.list_sessions(memory_id, actor_id)
        for session in sessions:
            session_id = session.get("sessionId")
            if not session_id:
                continue
            events = manager.list_events(memory_id, actor_id, session_id, max_results=100)
            for event in events:
                event["_actorId"] = actor_id
                event["_sessionId"] = session_id
            all_events.extend(events)
    return all_events


def _collect_all_records(
    manager: MemoryManager,
    memory_id: str,
    namespace: Optional[str],
    max_results: int,
) -> List[Dict[str, Any]]:
    """Collect records from specified namespace or all namespaces."""
    all_records: List[Dict[str, Any]] = []

    if namespace:
        # Single namespace
        records = manager.list_records(memory_id, namespace, max_results)
        for r in records:
            r["_namespace"] = namespace
        return records

    # All namespaces - get from memory strategies
    memory = manager.get_memory(memory_id)
    strategies = memory.get("strategies") or memory.get("memoryStrategies") or []

    for strategy in strategies:
        for ns_template in strategy.get("namespaces", []):
            _collect_records_from_namespace_template(manager, memory_id, ns_template, max_results, all_records)

    return all_records


def _collect_records_from_namespace_template(
    manager: MemoryManager,
    memory_id: str,
    ns_template: str,
    max_results: int,
    all_records: List[Dict[str, Any]],
) -> None:
    """Collect records from a namespace template, resolving placeholders."""
    if "{actorId}" not in ns_template and "{sessionId}" not in ns_template:
        # Static namespace
        _try_collect_records(manager, memory_id, ns_template, max_results, all_records)
        return

    # Need to enumerate actors/sessions
    try:
        actors = manager.list_actors(memory_id)
        for actor in actors[:5]:  # Limit actors
            actor_id = actor.get("actorId", "")
            ns = ns_template.replace("{actorId}", actor_id)

            if "{sessionId}" in ns:
                sessions = manager.list_sessions(memory_id, actor_id)
                for sess in sessions[:3]:  # Limit sessions
                    session_id = sess.get("sessionId", "")
                    final_ns = ns.replace("{sessionId}", session_id)
                    _try_collect_records(manager, memory_id, final_ns, max_results, all_records)
            else:
                _try_collect_records(manager, memory_id, ns, max_results, all_records)
    except Exception as e:
        logger.debug("Error collecting records: %s", e)


def _try_collect_records(
    manager: MemoryManager,
    memory_id: str,
    namespace: str,
    max_results: int,
    all_records: List[Dict[str, Any]],
) -> None:
    """Try to collect records from a namespace, ignoring errors."""
    try:
        records = manager.list_records(memory_id, namespace, max_results)
        for r in records:
            r["_namespace"] = namespace
        all_records.extend(records)
    except Exception as e:
        logger.debug("Error collecting records from namespace %s: %s", namespace, e)


# ==================== Main Memory Commands ====================


@memory_app.command()
def create(
    name: str = typer.Argument(..., help="Name for the memory resource"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region (default: session region)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Description for the memory"),
    event_expiry_days: int = typer.Option(90, "--event-expiry-days", "-e", help="Event retention in days"),
    strategies: Optional[str] = typer.Option(
        None,
        "--strategies",
        "-s",
        help='JSON string of memory strategies (e.g., \'[{"semanticMemoryStrategy": {"name": "Facts"}}]\')',
    ),
    memory_execution_role_arn: Optional[str] = typer.Option(
        None, "--role-arn", help="IAM role ARN for memory execution"
    ),
    encryption_key_arn: Optional[str] = typer.Option(None, "--encryption-key-arn", help="KMS key ARN for encryption"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for memory to become ACTIVE"),
    max_wait: int = typer.Option(300, "--max-wait", help="Maximum wait time in seconds"),
) -> None:
    """Create a new memory resource.

    Examples:
        # Create basic memory (STM only)
        agentcore memory create my_agent_memory

        # Create with LTM strategies
        agentcore memory create my_memory --strategies '[{"semanticMemoryStrategy": {"name": "Facts"}}]' --wait
    """
    try:
        manager = MemoryManager(region_name=region, console=console)

        parsed_strategies = None
        if strategies:
            try:
                parsed_strategies = json.loads(strategies)
            except json.JSONDecodeError as e:
                _handle_error(f"Error parsing strategies JSON: {e}")

        console.print(f"[cyan]Creating memory: {name}...[/cyan]")

        if wait:
            memory = manager.create_memory_and_wait(
                name=name,
                strategies=parsed_strategies,
                description=description,
                event_expiry_days=event_expiry_days,
                memory_execution_role_arn=memory_execution_role_arn,
                encryption_key_arn=encryption_key_arn,
                max_wait=max_wait,
            )
        else:
            memory = manager._create_memory(
                name=name,
                strategies=parsed_strategies,
                description=description,
                event_expiry_days=event_expiry_days,
                memory_execution_role_arn=memory_execution_role_arn,
                encryption_key_arn=encryption_key_arn,
            )

        console.print("[green]✓ Memory created successfully![/green]")
        console.print(f"[bold]Memory ID:[/bold] {memory.id}")
        console.print(f"[bold]Status:[/bold] {memory.status}")
        console.print(f"[bold]Region:[/bold] {manager.region_name or 'default'}")

    except typer.Exit:
        raise
    except Exception as e:
        _handle_error(f"Error creating memory: {e}", e)


@memory_app.command()
def show(
    agent: Optional[str] = typer.Option(
        None,
        "--agent",
        "-a",
        help="Agent name (use 'agentcore configure list' to see available agents)",
    ),
    memory_id: Optional[str] = typer.Option(None, "--memory-id", "-m", help="Memory ID (overrides config)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    all_events: bool = typer.Option(False, "--all", help="Show all events in memory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full configuration and event content"),
    max_events: int = typer.Option(10, "--max-events", "-n", help="Max events per session (with --all)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export to JSON file"),
) -> None:
    """Show memory details and events.

    CONFIG COMMANDS (uses .bedrock_agentcore.yaml):
        # Show memory details from config
        agentcore memory show

        # Show all events in memory
        agentcore memory show --all

        # Show with full event content
        agentcore memory show --all --verbose

    EXPLICIT MEMORY COMMANDS:
        # Show specific memory
        agentcore memory show -m mem_abc123

        # Show all events for specific memory
        agentcore memory show -m mem_abc123 --all

        # Export to JSON
        agentcore memory show -m mem_abc123 -o memory.json

    Notes:
        - Without --memory-id, uses memory from .bedrock_agentcore.yaml config
        - Use --all to show events tree (actors -> sessions -> events)
        - Use --verbose with --all to show event content
    """
    try:
        config = _resolve_memory_config(agent, memory_id, region)
        manager = MemoryManager(region_name=config.region, console=console)
        visualizer = MemoryVisualizer(console)

        if all_events:
            console.print(f"[dim]Fetching events tree for {config.memory_id}...[/dim]")
            visualizer.display_events_tree(
                config.memory_id,
                manager,
                max_events=max_events,
                output=output,
                verbose=verbose,
            )
        else:
            memory = manager.get_memory(config.memory_id)

            if output:
                path = Path(output)
                with path.open("w") as f:
                    data = dict(memory.items()) if hasattr(memory, "items") else memory._data
                    json.dump(data, f, indent=2, default=str)
                console.print(f"[green]✓[/green] Exported memory data to {path}")
                return

            visualizer.visualize_memory(memory, verbose=verbose)

    except typer.Exit:
        raise
    except Exception as e:
        _handle_error(f"Error showing memory: {e}", e)


@memory_app.command()
def get(
    memory_id: str = typer.Argument(..., help="Memory resource ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
) -> None:
    """Get details of a memory resource.

    Example:
        agentcore memory get my_memory_abc123
    """
    try:
        manager = MemoryManager(region_name=region, console=console)
        memory = manager.get_memory(memory_id)

        console.print("\n[bold cyan]Memory Details:[/bold cyan]")
        console.print(f"[bold]ID:[/bold] {memory.id}")
        console.print(f"[bold]Name:[/bold] {memory.name}")
        console.print(f"[bold]Status:[/bold] {memory.status}")
        console.print(f"[bold]Description:[/bold] {memory.description or 'N/A'}")
        console.print(f"[bold]Event Expiry:[/bold] {memory.event_expiry_duration} days")

        if memory.strategies:
            console.print(f"\n[bold]Strategies ({len(memory.strategies)}):[/bold]")
            for strategy in memory.strategies:
                console.print(f"  • {strategy.get('name', 'N/A')} ({strategy.get('type', 'N/A')})")

    except Exception as e:
        _handle_error(f"Error getting memory: {e}", e)


@memory_app.command(name="list")
def list_memories_cmd(
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    max_results: int = typer.Option(100, "--max-results", "-n", help="Maximum number of results"),
) -> None:
    """List all memory resources.

    Example:
        agentcore memory list
    """
    try:
        manager = MemoryManager(region_name=region, console=console)
        memories = manager.list_memories(max_results=max_results)

        visualizer = MemoryVisualizer(console)
        visualizer.display_memory_list(memories)

    except Exception as e:
        _handle_error(f"Error listing memories: {e}", e)


@memory_app.command()
def delete(
    memory_id: str = typer.Argument(..., help="Memory resource ID to delete"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    wait: bool = typer.Option(False, "--wait", help="Wait for deletion to complete"),
    max_wait: int = typer.Option(300, "--max-wait", help="Maximum wait time in seconds"),
) -> None:
    """Delete a memory resource.

    Example:
        agentcore memory delete my_memory_abc123 --wait
    """
    try:
        manager = MemoryManager(region_name=region, console=console)

        console.print(f"[yellow]Deleting memory: {memory_id}...[/yellow]")

        if wait:
            manager.delete_memory_and_wait(memory_id, max_wait=max_wait)
        else:
            manager.delete_memory(memory_id)

        console.print("[green]✓ Memory deleted successfully![/green]")

    except Exception as e:
        _handle_error(f"Error deleting memory: {e}", e)


@memory_app.command()
def status(
    memory_id: str = typer.Argument(..., help="Memory resource ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
) -> None:
    """Get memory provisioning status.

    Example:
        agentcore memory status mem_123
    """
    try:
        manager = MemoryManager(region_name=region, console=console)
        memory_status = manager.get_memory_status(memory_id)

        console.print(f"[bold]Memory Status:[/bold] {memory_status}")
        console.print(f"[bold]Memory ID:[/bold] {memory_id}")

    except Exception as e:
        _handle_error(f"Error getting status: {e}", e)


# ==================== SHOW SUBCOMMANDS (Data Plane Visualization) ====================


@show_app.callback()
def show_callback(
    ctx: typer.Context,
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name from config"),
    memory_id: Optional[str] = typer.Option(None, "--memory-id", "-m", help="Memory resource ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full details"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export to JSON file"),
) -> None:
    """Show memory details from config or explicit memory ID.

    CONFIG COMMANDS (uses .bedrock_agentcore.yaml):
        agentcore memory show              # Show memory details
        agentcore memory show --verbose    # Show with strategies

    EXPLICIT MEMORY:
        agentcore memory show -m mem_123   # Show specific memory
    """
    # If a subcommand is invoked, skip this
    if ctx.invoked_subcommand is not None:
        return

    try:
        config = _resolve_memory_config(agent, memory_id, region)
        manager = MemoryManager(region_name=config.region, console=console)
        memory = manager.get_memory(config.memory_id)

        if output:
            path = Path(output)
            data = dict(memory.items()) if hasattr(memory, "items") else memory
            with path.open("w") as f:
                json.dump(data, f, indent=2, default=str)
            console.print(f"[green]✓[/green] Exported memory to {path}")
            return

        actor_count = None
        if verbose:
            actors = manager.list_actors(config.memory_id)
            actor_count = len(actors)

        visualizer = MemoryVisualizer(console)
        visualizer.visualize_memory(memory, verbose=verbose, actor_count=actor_count)

    except typer.Exit:
        raise
    except Exception as e:
        _handle_error(f"Error: {e}", e)


@show_app.command(name="events")
def show_events(
    agent: Optional[str] = typer.Option(None, "--agent", help="Agent name from config"),
    memory_id: Optional[str] = typer.Option(None, "--memory-id", "-m", help="Memory resource ID"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    all_events: bool = typer.Option(False, "--all", help="Show events tree"),
    actor_id: Optional[str] = typer.Option(None, "--actor-id", "-a", help="Filter to specific actor"),
    session_id: Optional[str] = typer.Option(None, "--session-id", "-s", help="Filter to specific session"),
    last: int = typer.Option(1, "--last", "-l", help="Show Nth most recent event (default: 1=latest)"),
    list_actors: bool = typer.Option(False, "--list-actors", help="List all actor IDs"),
    list_sessions: bool = typer.Option(False, "--list-sessions", help="List all session IDs for actor"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full content"),
    max_events: int = typer.Option(10, "--max-events", help="Max events per session used with --all"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export to JSON file"),
) -> None:
    """Show memory events.

    Examples:
        # Show latest event
        agentcore memory show events

        # Show events tree (capped at 10 actors/sessions/events)
        agentcore memory show events --all

        # Filter to specific actor
        agentcore memory show events --all --actor-id quickstart-user

        # Filter to specific session
        agentcore memory show events --all -a quickstart-user -s abc123

        # List all actors
        agentcore memory show events --list-actors

        # List sessions for actor
        agentcore memory show events --list-sessions -a quickstart-user
    """
    try:
        config = _resolve_memory_config(agent, memory_id, region)
        _validate_events_options(all_events, last, session_id, actor_id, list_sessions)

        manager = MemoryManager(region_name=config.region, console=console)
        visualizer = MemoryVisualizer(console)

        # Handle list-actors mode
        if list_actors:
            _handle_list_actors(manager, config.memory_id)
            return

        # Handle list-sessions mode
        if list_sessions:
            _handle_list_sessions(manager, config.memory_id, actor_id)
            return

        # Handle all-events tree mode
        if all_events:
            console.print(f"[dim]Fetching events tree for {config.memory_id}...[/dim]")
            visualizer.display_events_tree(
                config.memory_id,
                manager,
                max_actors=10,
                max_sessions=10,
                max_events=max_events,
                actor_id=actor_id,
                session_id=session_id,
                output=output,
                verbose=verbose,
            )
            return

        # Handle single event (Nth most recent)
        _handle_show_nth_event(manager, visualizer, config.memory_id, last, verbose, output)

    except typer.Exit:
        raise
    except Exception as e:
        _handle_error(f"Error listing events: {e}", e)


def _handle_list_actors(manager: MemoryManager, memory_id: str) -> None:
    """Handle --list-actors mode."""
    actors = manager.list_actors(memory_id)
    tree = Tree(f"🧠 [bold cyan]{memory_id}[/bold cyan]")
    for a in actors:
        tree.add(f"👤 {a.get('actorId')}")
    console.print(tree)
    console.print(f"\n[dim]{len(actors)} actors[/dim]")


def _handle_list_sessions(manager: MemoryManager, memory_id: str, actor_id: Optional[str]) -> None:
    """Handle --list-sessions mode."""
    if not actor_id:
        _handle_error("--list-sessions requires --actor-id")
    sessions = manager.list_sessions(memory_id, actor_id)
    tree = Tree(f"🧠 [bold cyan]{memory_id}[/bold cyan]")
    actor_tree = tree.add(f"👤 [bold]{actor_id}[/bold]")
    for s in sessions:
        actor_tree.add(f"📁 [cyan]{s.get('sessionId')}[/cyan]")
    console.print(tree)
    console.print(f"\n[dim]{len(sessions)} sessions[/dim]")


def _handle_show_nth_event(
    manager: MemoryManager,
    visualizer: MemoryVisualizer,
    memory_id: str,
    last: int,
    verbose: bool,
    output: Optional[str],
) -> None:
    """Handle showing the Nth most recent event."""
    console.print(f"[dim]Fetching events for {memory_id}...[/dim]")
    all_events_list = _collect_all_events(manager, memory_id)

    if not all_events_list:
        console.print("[yellow]No events found in memory[/yellow]")
        raise typer.Exit(0)

    all_events_list.sort(key=lambda e: e.get("eventTimestamp", ""), reverse=True)

    if last > len(all_events_list):
        console.print(f"[yellow]Only {len(all_events_list)} events found, showing oldest[/yellow]")
        last = len(all_events_list)

    event = all_events_list[last - 1]
    visualizer.display_single_event(event, last, len(all_events_list), verbose)

    if output:
        path = Path(output)
        with path.open("w") as f:
            json.dump(event, f, indent=2, default=str)
        console.print(f"[green]✓[/green] Exported event to {path}")


@show_app.command(name="records")
def show_records(
    agent: Optional[str] = typer.Option(None, "--agent", help="Agent name from config"),
    memory_id: Optional[str] = typer.Option(None, "--memory-id", "-m", help="Memory resource ID"),
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="Namespace to list records from"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Semantic search query"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
    all_records: bool = typer.Option(False, "--all", help="Show all records across all namespaces"),
    last: int = typer.Option(1, "--last", "-l", help="Show Nth most recent record (default: 1=latest)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full record content"),
    max_results: int = typer.Option(10, "--max-results", help="Max records to return"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export to JSON file"),
) -> None:
    """Show memory records (long-term memory).

    Examples:
        # Show latest record (default, across all namespaces)
        agentcore memory show records

        # Show 2nd most recent record
        agentcore memory show records --last 2

        # Show all records tree
        agentcore memory show records --all

        # Search records semantically
        agentcore memory show records --query "user preferences" -n /users/quickstart-user/facts/

        # Show records from specific namespace
        agentcore memory show records -n /users/quickstart-user/facts/

        # Show with full content
        agentcore memory show records --verbose
    """
    try:
        config = _resolve_memory_config(agent, memory_id, region)
        _validate_records_options(all_records, last, namespace, query)

        manager = MemoryManager(region_name=config.region, console=console)
        visualizer = MemoryVisualizer(console)

        # Handle all-records tree mode
        if all_records:
            console.print(f"[dim]Fetching records tree for {config.memory_id}...[/dim]")
            visualizer.display_records_tree(manager, config.memory_id, verbose, max_results, output)
            return

        # Handle semantic search
        if query:
            _handle_semantic_search(manager, visualizer, config.memory_id, namespace, query, max_results, verbose)
            return

        # Handle namespace drill-down
        if namespace:
            console.print(f"[dim]Fetching records from {namespace}...[/dim]")
            visualizer.display_namespace_records(manager, config.memory_id, namespace, verbose, max_results, output)
            return

        # Handle single record (Nth most recent)
        _handle_show_nth_record(manager, visualizer, config.memory_id, namespace, last, verbose, max_results, output)

    except typer.Exit:
        raise
    except Exception as e:
        _handle_error(f"Error listing records: {e}", e)


def _handle_semantic_search(
    manager: MemoryManager,
    visualizer: MemoryVisualizer,
    memory_id: str,
    namespace: Optional[str],
    query: str,
    max_results: int,
    verbose: bool,
) -> None:
    """Handle semantic search on records."""
    if not namespace:
        _handle_error("--namespace required for semantic search")
    console.print(f"[dim]Searching records in {namespace}...[/dim]")
    records = manager.search_records(memory_id, namespace, query, max_results)
    if not records:
        console.print("[yellow]No matching records found[/yellow]")
        raise typer.Exit(0)
    visualizer.display_search_results(records, query, verbose)


def _handle_show_nth_record(
    manager: MemoryManager,
    visualizer: MemoryVisualizer,
    memory_id: str,
    namespace: Optional[str],
    last: int,
    verbose: bool,
    max_results: int,
    output: Optional[str],
) -> None:
    """Handle showing the Nth most recent record."""
    console.print(f"[dim]Fetching records for {memory_id}...[/dim]")
    all_records_list = _collect_all_records(manager, memory_id, namespace, max_results)

    if not all_records_list:
        console.print("[yellow]No records found in memory[/yellow]")
        raise typer.Exit(0)

    # Sort by createdAt descending (most recent first)
    all_records_list.sort(key=lambda r: r.get("createdAt", ""), reverse=True)

    if last > len(all_records_list):
        console.print(f"[yellow]Only {len(all_records_list)} records found, showing oldest[/yellow]")
        last = len(all_records_list)

    record = all_records_list[last - 1]
    visualizer.display_single_record(record, last, len(all_records_list), verbose)

    if output:
        path = Path(output)
        with path.open("w") as f:
            json.dump(record, f, indent=2, default=str)
        console.print(f"[green]✓[/green] Exported record to {path}")


# ==================== Browse Command ====================


@memory_app.command()
def browse(
    memory_id: Optional[str] = typer.Option(None, "--memory-id", "-m", help="Memory ID to browse"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent name from config"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="AWS region"),
) -> None:
    """Interactive TUI browser for exploring memory content.

    Navigate through actors, sessions, events (STM) and namespaces, records (LTM).

    Key bindings:
      ↑↓     Navigate list
      Enter  Select item
      b      Go back
      h      Home (return to memory view)
      v      Toggle verbose
      m      Load more (when paginated)
      q      Quit
    """
    from .browser import MemoryBrowser

    config = _resolve_memory_config(agent, memory_id, region)
    manager = MemoryManager(region_name=config.region)

    # Validate credentials before starting browser
    try:
        memory = manager.get_memory(config.memory_id)
    except Exception as e:
        console.print(
            Panel(
                f"[red]Cannot start browser:[/red] {e}",
                title="[red]Authentication Error[/red]",
                border_style="red",
            )
        )
        raise typer.Exit(1) from None

    app = MemoryBrowser(manager, config.memory_id, initial_memory=memory)
    app.run()


if __name__ == "__main__":
    memory_app()
