"""Memory summary model class for AgentCore Memory resources."""

from typing import Any, Dict

from .DictWrapper import DictWrapper


class MemorySummary(DictWrapper):
    """A class representing a memory summary."""

    def __init__(self, memory_summary: Dict[str, Any]):
        """Initialize MemorySummary with summary data.

        Args:
            memory_summary: Dictionary containing memory summary data.
        """
        super().__init__(memory_summary)
