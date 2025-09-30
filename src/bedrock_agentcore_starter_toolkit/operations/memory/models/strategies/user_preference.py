"""User preference memory strategy implementation."""

from typing import Any, Dict

from .base import BaseStrategy


class UserPreferenceStrategy(BaseStrategy):
    """User preference memory strategy for storing user preferences and settings.

    This strategy captures and stores user preferences, settings, and
    behavioral patterns that persist across sessions.

    Example:
        strategy = UserPreferenceStrategy(
            name="UserPreferences",
            description="Store user preferences and settings",
            namespaces=["preferences/{actorId}"]
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

        return {"userPreferenceMemoryStrategy": config}
