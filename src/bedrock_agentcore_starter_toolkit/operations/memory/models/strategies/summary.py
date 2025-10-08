"""Summary memory strategy implementation."""

from typing import Any, Dict

from .base import BaseStrategy


class SummaryStrategy(BaseStrategy):
    """Summary memory strategy for creating conversation summaries.

    This strategy creates summaries of conversations, helping to maintain
    context over long interactions and reducing the need to process
    entire conversation histories.

    Example:
        strategy = SummaryStrategy(
            name="ConversationSummary",
            description="Summarize conversation content",
            namespaces=["summaries/{actorId}/{sessionId}"]
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

        return {"summaryMemoryStrategy": config}
