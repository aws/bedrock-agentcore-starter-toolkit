"""Memory strategy model class for AgentCore Memory resources."""

from typing import Any, Dict

from .DictWrapper import DictWrapper


class MemoryStrategy(DictWrapper):
    """A class representing a memory strategy."""

    def __init__(self, memory_strategy: Dict[str, Any]):
        """Initialize MemoryStrategy with strategy data.

        Args:
            memory_strategy: Dictionary containing memory strategy data.
        """
        super().__init__(memory_strategy)
