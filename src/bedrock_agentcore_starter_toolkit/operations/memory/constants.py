"""Constants for Bedrock AgentCore Memory SDK."""

from enum import Enum
from typing import Optional


class StrategyType(Enum):
    """Memory strategy types with integrated wrapper key and type methods."""

    SEMANTIC = "semanticMemoryStrategy"
    SUMMARY = "summaryMemoryStrategy"
    USER_PREFERENCE = "userPreferenceMemoryStrategy"
    CUSTOM = "customMemoryStrategy"

    def extraction_wrapper_key(self) -> Optional[str]:
        """Get the extraction wrapper key for this strategy type."""
        extraction_keys = {
            StrategyType.SEMANTIC: "semanticExtractionConfiguration",
            StrategyType.USER_PREFERENCE: "userPreferenceExtractionConfiguration",
        }
        return extraction_keys.get(self)

    def consolidation_wrapper_key(self) -> Optional[str]:
        """Get the consolidation wrapper key for this strategy type."""
        # Only SUMMARY strategy has a consolidation wrapper key
        if self == StrategyType.SUMMARY:
            return "summaryConsolidationConfiguration"
        return None

    def get_memory_strategy(self) -> str:
        """Get the internal memory strategy type string."""
        strategy_mapping = {
            StrategyType.SEMANTIC: "SEMANTIC",
            StrategyType.SUMMARY: "SUMMARIZATION",
            StrategyType.USER_PREFERENCE: "USER_PREFERENCE",
            StrategyType.CUSTOM: "CUSTOM",
        }
        return strategy_mapping[self]

    def get_override_type(self) -> Optional[str]:
        """Get the override type for custom strategies."""
        # This method is primarily for CUSTOM strategy type
        # The actual override type would be determined by context
        if self == StrategyType.CUSTOM:
            return "CUSTOM_OVERRIDE"  # Base type, specific override determined by usage
        return None


class OverrideType(Enum):
    """Custom strategy override types."""

    SEMANTIC_OVERRIDE = "SEMANTIC_OVERRIDE"
    SUMMARY_OVERRIDE = "SUMMARY_OVERRIDE"
    USER_PREFERENCE_OVERRIDE = "USER_PREFERENCE_OVERRIDE"

    def extraction_wrapper_key(self) -> Optional[str]:
        """Get the extraction wrapper key for this override type."""
        extraction_keys = {
            OverrideType.SEMANTIC_OVERRIDE: "semanticExtractionOverride",
            OverrideType.USER_PREFERENCE_OVERRIDE: "userPreferenceExtractionOverride",
        }
        return extraction_keys.get(self)

    def consolidation_wrapper_key(self) -> Optional[str]:
        """Get the consolidation wrapper key for this override type."""
        consolidation_keys = {
            OverrideType.SEMANTIC_OVERRIDE: "semanticConsolidationOverride",
            OverrideType.SUMMARY_OVERRIDE: "summaryConsolidationOverride",
            OverrideType.USER_PREFERENCE_OVERRIDE: "userPreferenceConsolidationOverride",
        }
        return consolidation_keys.get(self)


class MemoryStatus(Enum):
    """Memory resource statuses."""

    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    UPDATING = "UPDATING"
    DELETING = "DELETING"


class MemoryStrategyStatus(Enum):
    """Memory strategy statuses (new from API update)."""

    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    DELETING = "DELETING"
    FAILED = "FAILED"
