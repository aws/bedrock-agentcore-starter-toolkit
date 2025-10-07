"""Base classes and types for memory strategies."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Union

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from .custom import CustomSemanticStrategy, CustomSummaryStrategy, CustomUserPreferenceStrategy
    from .semantic import SemanticStrategy
    from .summary import SummaryStrategy
    from .user_preference import UserPreferenceStrategy


class ExtractionConfig(BaseModel):
    """Configuration for memory extraction operations.

    Attributes:
        append_to_prompt: Additional prompt text for extraction
        model_id: Model identifier for extraction operations
    """

    append_to_prompt: str | None = Field(None, description="Additional prompt text for extraction")
    model_id: str | None = Field(None, description="Model identifier for extraction operations")

    model_config = ConfigDict(validate_by_name=True)


class ConsolidationConfig(BaseModel):
    """Configuration for memory consolidation operations.

    Attributes:
        append_to_prompt: Additional prompt text for consolidation
        model_id: Model identifier for consolidation operations
    """

    append_to_prompt: str | None = Field(None, description="Additional prompt text for consolidation")
    model_id: str | None = Field(None, description="Model identifier for consolidation operations")

    model_config = ConfigDict(validate_by_name=True)


class BaseStrategy(BaseModel, ABC):
    """Abstract base class for all memory strategies.

    Attributes:
        name: Strategy name (required)
        description: Optional strategy description
        namespaces: List of namespace patterns for the strategy
    """

    name: str = Field(..., description="Strategy name")
    description: str | None = Field(None, description="Strategy description")
    namespaces: list[str] | None = Field(None, description="Strategy namespaces")

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Convert strategy to dictionary format for API calls.

        Returns:
            Dictionary representation compatible with the AgentCore Memory API
        """
        pass

    model_config = ConfigDict(validate_assignment=True)


# Type union for all strategy types (including backward compatibility)
StrategyType = Union[
    "SemanticStrategy",
    "SummaryStrategy",
    "CustomSemanticStrategy",
    "CustomSummaryStrategy",
    "CustomUserPreferenceStrategy",
    "UserPreferenceStrategy",
    dict[str, Any],  # Backward compatibility with dict-based strategies
]
