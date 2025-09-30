"""Custom memory strategy implementation."""

from typing import Any, Dict

from pydantic import Field

from .base import BaseStrategy, ConsolidationConfig, ExtractionConfig


class CustomSemanticStrategy(BaseStrategy):
    """Custom semantic strategy with configurable extraction and consolidation.

    This strategy allows customization of both extraction and consolidation
    processes using custom prompts and models.

    Attributes:
        extraction_config: Configuration for extraction operations
        consolidation_config: Configuration for consolidation operations

    Example:
        strategy = CustomSemanticStrategy(
            name="CustomExtraction",
            description="Custom semantic extraction with specific prompts",
            extraction_config=ExtractionConfig(
                append_to_prompt="Extract key business insights",
                model_id="anthropic.claude-3-sonnet-20240229-v1:0"
            ),
            consolidation_config=ConsolidationConfig(
                append_to_prompt="Consolidate business insights",
                model_id="anthropic.claude-3-haiku-20240307-v1:0"
            ),
            namespaces=["custom/{actorId}/{sessionId}"]
        )
    """

    extraction_config: ExtractionConfig = Field(..., description="Extraction configuration")
    consolidation_config: ConsolidationConfig = Field(..., description="Consolidation configuration")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        config = {
            "name": self.name,
            "configuration": {
                "semanticOverride": {
                    "extraction": self._convert_extraction_config(),
                    "consolidation": self._convert_consolidation_config(),
                }
            },
        }

        if self.description is not None:
            config["description"] = self.description

        if self.namespaces is not None:
            config["namespaces"] = self.namespaces

        return {"customMemoryStrategy": config}

    def _convert_extraction_config(self) -> Dict[str, Any]:
        """Convert extraction config to API format."""
        config = {}
        if self.extraction_config.append_to_prompt is not None:
            config["appendToPrompt"] = self.extraction_config.append_to_prompt
        if self.extraction_config.model_id is not None:
            config["modelId"] = self.extraction_config.model_id
        return config

    def _convert_consolidation_config(self) -> Dict[str, Any]:
        """Convert consolidation config to API format."""
        config = {}
        if self.consolidation_config.append_to_prompt is not None:
            config["appendToPrompt"] = self.consolidation_config.append_to_prompt
        if self.consolidation_config.model_id is not None:
            config["modelId"] = self.consolidation_config.model_id
        return config


class CustomSummaryStrategy(BaseStrategy):
    """Custom summary strategy with configurable consolidation.

    This strategy allows customization of consolidation using custom prompts and models.

    Attributes:
        consolidation_config: Configuration for consolidation operations

    Example:
        strategy = CustomSummaryStrategy(
            name="CustomSummary",
            description="Custom summary extraction with specific prompts",
            consolidation_config=ConsolidationConfig(
                append_to_prompt="Consolidate business insights",
                model_id="anthropic.claude-3-haiku-20240307-v1:0"
            ),
            namespaces=["custom/{actorId}/{sessionId}"]
        )
    """

    consolidation_config: ConsolidationConfig = Field(..., description="Consolidation configuration")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        config = {
            "name": self.name,
            "configuration": {
                "summaryOverride": {
                    "consolidation": self._convert_consolidation_config(),
                }
            },
        }

        if self.description is not None:
            config["description"] = self.description

        if self.namespaces is not None:
            config["namespaces"] = self.namespaces

        return {"customMemoryStrategy": config}

    def _convert_consolidation_config(self) -> Dict[str, Any]:
        """Convert consolidation config to API format."""
        config = {}
        if self.consolidation_config.append_to_prompt is not None:
            config["appendToPrompt"] = self.consolidation_config.append_to_prompt
        if self.consolidation_config.model_id is not None:
            config["modelId"] = self.consolidation_config.model_id
        return config


class CustomUserPreferenceStrategy(BaseStrategy):
    """Custom userPreference strategy with configurable extraction and consolidation.

    This strategy allows customization of both extraction and consolidation
    processes using custom prompts and models.

    Attributes:
        extraction_config: Configuration for extraction operations
        consolidation_config: Configuration for consolidation operations

    Example:
        strategy = CustomUserPreferenceStrategy(
            name="CustomUserPreference",
            description="Custom user preference extraction with specific prompts",
            extraction_config=ExtractionConfig(
                append_to_prompt="Extract key business insights",
                model_id="anthropic.claude-3-sonnet-20240229-v1:0"
            ),
            consolidation_config=ConsolidationConfig(
                append_to_prompt="Consolidate business insights",
                model_id="anthropic.claude-3-haiku-20240307-v1:0"
            ),
            namespaces=["custom/{actorId}/{sessionId}"]
        )
    """

    extraction_config: ExtractionConfig = Field(..., description="Extraction configuration")
    consolidation_config: ConsolidationConfig = Field(..., description="Consolidation configuration")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API calls."""
        config = {
            "name": self.name,
            "configuration": {
                "userPreferenceOverride": {
                    "extraction": self._convert_extraction_config(),
                    "consolidation": self._convert_consolidation_config(),
                }
            },
        }

        if self.description is not None:
            config["description"] = self.description

        if self.namespaces is not None:
            config["namespaces"] = self.namespaces

        return {"customMemoryStrategy": config}

    def _convert_extraction_config(self) -> Dict[str, Any]:
        """Convert extraction config to API format."""
        config = {}
        if self.extraction_config.append_to_prompt is not None:
            config["appendToPrompt"] = self.extraction_config.append_to_prompt
        if self.extraction_config.model_id is not None:
            config["modelId"] = self.extraction_config.model_id
        return config

    def _convert_consolidation_config(self) -> Dict[str, Any]:
        """Convert consolidation config to API format."""
        config = {}
        if self.consolidation_config.append_to_prompt is not None:
            config["appendToPrompt"] = self.consolidation_config.append_to_prompt
        if self.consolidation_config.model_id is not None:
            config["modelId"] = self.consolidation_config.model_id
        return config
