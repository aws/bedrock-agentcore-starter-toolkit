"""Bedrock AgentCore Memory Models.

This module provides strongly typed models for memory operations,
including memory resources, strategies, and configurations.

Example:
    # Import strategy classes
    from bedrock_agentcore_starter_toolkit.operations.memory.models import (
        SemanticStrategy,
        SummaryStrategy,
        CustomSemanticStrategy,
        ExtractionConfig,
        ConsolidationConfig
    )

    # Create typed strategies
    semantic_strategy = SemanticStrategy(
        name="ConversationSemantics",
        description="Extract semantic information",
        namespaces=["semantics/{actorId}/{sessionId}"]
    )

    custom_strategy = CustomSemanticStrategy(
        name="CustomExtraction",
        extraction_config=ExtractionConfig(
            append_to_prompt="Extract key insights",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0"
        ),
        consolidation_config=ConsolidationConfig(
            append_to_prompt="Consolidate insights",
            model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )
    )
"""

# Memory resource models
from typing import Any, Dict, List

from .Memory import Memory
from .MemoryStrategy import MemoryStrategy
from .MemorySummary import MemorySummary

# Strategy models
from .strategies import (
    BaseStrategy,
    ConsolidationConfig,
    CustomSemanticStrategy,
    ExtractionConfig,
    SemanticStrategy,
    StrategyType,
    SummaryStrategy,
    UserPreferenceStrategy,
)


def convert_strategies_to_dicts(strategies: List[StrategyType]) -> List[Dict[str, Any]]:
    """Convert mixed strategy types to dictionary format for API calls.

    This function handles both new typed strategies and legacy dictionary
    strategies, ensuring backward compatibility.

    Args:
        strategies: List of strategy objects (typed or dict)

    Returns:
        List of strategy dictionaries compatible with the API

    Raises:
        ValueError: If an invalid strategy type is provided

    Example:
        strategies = [
            SemanticStrategy(name="Test"),
            {"semanticMemoryStrategy": {"name": "Legacy"}}
        ]
        dicts = convert_strategies_to_dicts(strategies)
    """
    result = []
    for strategy in strategies:
        if isinstance(strategy, BaseStrategy):
            result.append(strategy.to_dict())
        elif isinstance(strategy, dict):
            result.append(strategy)  # Backward compatibility
        else:
            raise ValueError(f"Invalid strategy type: {type(strategy)}. Expected BaseStrategy or dict.")
    return result


__all__ = [
    # Memory models
    "Memory",
    "MemorySummary",
    "MemoryStrategy",
    # Strategy base classes and types
    "BaseStrategy",
    "StrategyType",
    "ExtractionConfig",
    "ConsolidationConfig",
    # Strategy models
    "SemanticStrategy",
    "SummaryStrategy",
    "UserPreferenceStrategy",
    "CustomSemanticStrategy",
    # Utility functions
    "convert_strategies_to_dicts",
]
