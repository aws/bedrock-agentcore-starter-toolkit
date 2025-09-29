"""Semantic memory strategy implementation."""

from typing import Any, Dict

from .base import BaseStrategy


class SemanticStrategy(BaseStrategy):
    """Semantic memory strategy for extracting and storing semantic information.

    This strategy extracts semantic meaning from conversations and stores it
    for later retrieval. It's ideal for capturing facts, concepts, and
    contextual information from user interactions.

    Example:
        strategy = SemanticStrategy(
            name="ConversationSemantics",
            description="Extract semantic information from conversations",
            namespaces=["semantics/{actorId}/{sessionId}"]
        )
    """

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        config = {
            "name": self.name,
        }

        if self.description is not None:
            config["description"] = self.description

        if self.namespaces is not None:
            config["namespaces"] = self.namespaces

        return {"semanticMemoryStrategy": config}
