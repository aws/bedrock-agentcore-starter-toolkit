"""Formatting utilities for memory visualization."""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from rich.panel import Panel


def get_memory_status_icon(status: str) -> str:
    """Get emoji icon for memory status."""
    icons = {
        "ACTIVE": "✓ ",
        "CREATING": "⏳ ",
        "DELETING": "🗑 ",
        "FAILED": "❌ ",
    }
    return icons.get(status, "? ")


def get_memory_status_style(status: str) -> str:
    """Get Rich console style for memory status."""
    styles = {
        "ACTIVE": "green",
        "CREATING": "yellow",
        "DELETING": "dim",
        "FAILED": "red",
    }
    return styles.get(status, "dim")


def get_strategy_type_icon(strategy_type: str) -> str:
    """Get icon for strategy type."""
    return ""


def get_strategy_status_style(status: str) -> str:
    """Get Rich console style for strategy status."""
    return get_memory_status_style(status)


def format_namespaces(namespaces: list) -> str:
    """Format namespace list for display."""
    if not namespaces:
        return "[dim]None[/dim]"
    return ", ".join(namespaces)


def format_memory_age(created_at: Any) -> str:
    """Format memory creation time as relative age."""
    if not created_at:
        return "N/A"
    try:
        from datetime import datetime, timezone

        if hasattr(created_at, "timestamp"):
            created_ts = created_at.timestamp()
        else:
            return str(created_at)

        now = datetime.now(timezone.utc).timestamp()
        age_seconds = now - created_ts

        if age_seconds < 60:
            return f"{int(age_seconds)}s ago"
        elif age_seconds < 3600:
            return f"{int(age_seconds / 60)}m ago"
        elif age_seconds < 86400:
            return f"{int(age_seconds / 3600)}h ago"
        else:
            return f"{int(age_seconds / 86400)}d ago"
    except Exception:
        return str(created_at)


# ==================== Display Configuration ====================


@dataclass
class DisplayConfig:
    """Configuration constants for visualization."""

    MAX_PREVIEW_LENGTH: int = 80
    MAX_CONTENT_LENGTH: int = 500
    MAX_RECORDS_PER_NAMESPACE: int = 10
    MAX_ACTORS: int = 5
    MAX_SESSIONS: int = 3
    MAX_EVENTS: int = 10


# ==================== Content Extraction ====================


def extract_record_text(record: Dict[str, Any]) -> str:
    """Extract text content from a record.

    Args:
        record: Record dict with content field.

    Returns:
        Text content as string.
    """
    content = record.get("content", {})
    if isinstance(content, dict):
        return content.get("text", str(content))
    return str(content)


def extract_event_text(event: Dict[str, Any]) -> Optional[str]:
    """Extract text content from event payload.

    Args:
        event: Event dict with payload field.

    Returns:
        Text content or None if not found.
    """
    payload = event.get("payload", [])
    if not isinstance(payload, list) or not payload:
        return None

    item = payload[0]
    if "conversational" not in item:
        return None

    conv = item["conversational"]
    content = conv.get("content", {})
    if not isinstance(content, dict) or "text" not in content:
        return None

    try:
        parsed = json.loads(content["text"])
        msg = parsed.get("message", {})
        msg_content = msg.get("content", [])
        if msg_content and isinstance(msg_content, list):
            return msg_content[0].get("text")
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    return None


def extract_event_role(event: Dict[str, Any]) -> Optional[str]:
    """Extract role from event payload.

    Args:
        event: Event dict with payload field.

    Returns:
        Role string (USER, ASSISTANT) or None.
    """
    payload = event.get("payload", [])
    if isinstance(payload, list) and payload:
        item = payload[0]
        if "conversational" in item:
            return item["conversational"].get("role")
    return None


def extract_event_type(event: Dict[str, Any]) -> Optional[str]:
    """Extract event type from payload.

    Args:
        event: Event dict with payload field.

    Returns:
        Event type (conversational, blob) or None.
    """
    payload = event.get("payload", [])
    if isinstance(payload, list) and payload:
        item = payload[0]
        if "conversational" in item:
            return "conversational"
        if "blob" in item:
            return "blob"
    return None


# ==================== Truncation & Display ====================


def truncate_text(text: str, max_len: int = 80, verbose: bool = False) -> str:
    """Truncate text with ellipsis.

    Args:
        text: Text to truncate.
        max_len: Maximum length before truncation.
        verbose: If True, don't truncate.

    Returns:
        Truncated text with '...' or original if verbose.
    """
    if verbose or len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def format_content_preview(text: str, verbose: bool = False) -> str:
    """Format content for inline preview (single line).

    Args:
        text: Text content to format.
        verbose: If True, show more content.

    Returns:
        Formatted preview string.
    """
    preview = text.replace("\n", " ").strip()
    max_len = DisplayConfig.MAX_CONTENT_LENGTH if verbose else DisplayConfig.MAX_PREVIEW_LENGTH
    return truncate_text(preview, max_len, verbose=False)


def render_content_panel(text: str, verbose: bool = False) -> Union[Panel, str]:
    """Render content as panel (verbose) or truncated string.

    Args:
        text: Text content to render.
        verbose: If True, render as full Panel.

    Returns:
        Panel for verbose mode, truncated string otherwise.
    """
    if verbose:
        return Panel(text.strip(), border_style="dim", padding=(0, 1))
    return format_content_preview(text)


def format_payload_snippet(event: Dict[str, Any], max_len: int = 60) -> str:
    """Format raw payload as truncated JSON snippet.

    Args:
        event: Event dict with payload field.
        max_len: Maximum length before truncation.

    Returns:
        Truncated JSON string with dim styling.
    """
    import json

    payload = event.get("payload")
    if not payload:
        return "[dim](empty)[/dim]"
    raw = json.dumps(payload, default=str)
    if len(raw) > max_len:
        return f"[dim]{raw[:max_len]}…[/dim]"
    return f"[dim]{raw}[/dim]"


def format_truncation_hint(shown: int, total: int) -> str:
    """Format '... N more items' hint.

    Args:
        shown: Number of items shown.
        total: Total number of items.

    Returns:
        Hint string or empty if all items shown.
    """
    remaining = total - shown
    if remaining <= 0:
        return ""
    return f"[dim]... {remaining} more[/dim]"


def format_role_icon(role: Optional[str]) -> str:
    """Format role as colored icon string.

    Args:
        role: Role string (USER, ASSISTANT, etc.)

    Returns:
        Formatted icon string with Rich markup.
    """
    if role == "USER":
        return "[cyan]👤 User[/cyan]"
    if role == "ASSISTANT":
        return "[green]🤖 Assistant[/green]"
    return f"[dim]{role or 'Unknown'}[/dim]"
