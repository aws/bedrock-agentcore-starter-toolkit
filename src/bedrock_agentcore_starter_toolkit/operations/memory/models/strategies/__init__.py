"""Memory strategy models and configurations.

This module provides strongly typed strategy classes for creating
memory strategies with full type safety and IDE support.

Example:
    from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
        SemanticStrategy,
        CustomSemanticStrategy,
        ExtractionConfig,
        ConsolidationConfig
    )

    # Create typed strategies manually
    semantic = SemanticStrategy(
        name="MySemanticStrategy",
        description="Extract key information"
    )

    custom = CustomSemanticStrategy(
        name="MyCustomStrategy",
        extraction_config=ExtractionConfig(
            append_to_prompt="Extract insights",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0"
        ),
        consolidation_config=ConsolidationConfig(
            append_to_prompt="Consolidate insights",
            model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )
    )
"""

from .base import BaseStrategy, ConsolidationConfig, ExtractionConfig, StrategyType
from .custom import CustomSemanticStrategy, CustomSummaryStrategy, CustomUserPreferenceStrategy
from .semantic import SemanticStrategy
from .summary import SummaryStrategy
from .user_preference import UserPreferenceStrategy

__all__ = [
    # Base classes and types
    "BaseStrategy",
    "StrategyType",
    "ExtractionConfig",
    "ConsolidationConfig",
    # Concrete strategy classes
    "SemanticStrategy",
    "SummaryStrategy",
    "UserPreferenceStrategy",
    "CustomSemanticStrategy",
    "CustomSummaryStrategy",
    "CustomUserPreferenceStrategy",
]
