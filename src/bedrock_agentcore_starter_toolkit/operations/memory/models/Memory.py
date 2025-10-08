"""Memory model class for AgentCore Memory resources."""

from typing import Any, Dict

from .DictWrapper import DictWrapper


class Memory(DictWrapper):
    """A class representing a memory resource."""

    def __init__(self, memory: Dict[str, Any]):
        """Initialize Memory with memory data.

        Args:
            memory: Dictionary containing memory resource data.
        """
        super().__init__(memory)
