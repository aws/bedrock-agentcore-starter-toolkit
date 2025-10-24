"""Tests for the typed strategy system in bedrock_agentcore.memory.strategy_types."""

import pytest
from pydantic import ValidationError

from bedrock_agentcore_starter_toolkit.operations.memory.models import (
    BaseStrategy,
    SemanticStrategy,
    StrategyType,
    SummaryStrategy,
    UserPreferenceStrategy,
    convert_strategies_to_dicts,
)
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies.base import (
    ConsolidationConfig,
    ExtractionConfig,
)
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies.custom import (
    CustomSemanticStrategy,
    CustomSummaryStrategy,
    CustomUserPreferenceStrategy,
)
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies.self_managed import (
    InvocationConfig,
    MessageBasedTrigger,
    SelfManagedStrategy,
    TimeBasedTrigger,
    TokenBasedTrigger,
)


class TestExtractionConfig:
    """Test ExtractionConfig validation and functionality."""

    def test_extraction_config_creation(self):
        """Test basic ExtractionConfig creation."""
        config = ExtractionConfig(
            append_to_prompt="Extract key insights",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        )

        assert config.append_to_prompt == "Extract key insights"
        assert config.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"

    def test_extraction_config_optional_fields(self):
        """Test ExtractionConfig with optional fields."""
        config = ExtractionConfig()

        assert config.append_to_prompt is None
        assert config.model_id is None


class TestConsolidationConfig:
    """Test ConsolidationConfig validation and functionality."""

    def test_consolidation_config_creation(self):
        """Test basic ConsolidationConfig creation."""
        config = ConsolidationConfig(
            append_to_prompt="Consolidate insights",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )

        assert config.append_to_prompt == "Consolidate insights"
        assert config.model_id == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_consolidation_config_optional_fields(self):
        """Test ConsolidationConfig with optional fields."""
        config = ConsolidationConfig()

        assert config.append_to_prompt is None
        assert config.model_id is None


class TestSemanticStrategy:
    """Test SemanticStrategy functionality."""

    def test_semantic_strategy_creation(self):
        """Test basic SemanticStrategy creation."""
        strategy = SemanticStrategy(
            name="ConversationSemantics",
            description="Extract semantic information",
            namespaces=["semantics/{actorId}/{sessionId}"],
        )

        assert strategy.name == "ConversationSemantics"
        assert strategy.description == "Extract semantic information"
        assert strategy.namespaces == ["semantics/{actorId}/{sessionId}"]

    def test_semantic_strategy_minimal(self):
        """Test SemanticStrategy with only required fields."""
        strategy = SemanticStrategy(name="MinimalSemantic")

        assert strategy.name == "MinimalSemantic"
        assert strategy.description is None
        assert strategy.namespaces is None

    def test_semantic_strategy_to_dict(self):
        """Test SemanticStrategy to_dict conversion."""
        strategy = SemanticStrategy(name="TestSemantic", description="Test description", namespaces=["test/{actorId}"])

        result = strategy.to_dict()
        expected = {
            "semanticMemoryStrategy": {
                "name": "TestSemantic",
                "description": "Test description",
                "namespaces": ["test/{actorId}"],
            }
        }

        assert result == expected

    def test_semantic_strategy_validation(self):
        """Test SemanticStrategy validation."""
        # Name is required
        with pytest.raises(ValidationError):
            SemanticStrategy()


class TestSummaryStrategy:
    """Test SummaryStrategy functionality."""

    def test_summary_strategy_creation(self):
        """Test basic SummaryStrategy creation."""
        strategy = SummaryStrategy(
            name="ConversationSummary",
            description="Summarize conversations",
            namespaces=["summaries/{actorId}/{sessionId}"],
        )

        assert strategy.name == "ConversationSummary"
        assert strategy.description == "Summarize conversations"
        assert strategy.namespaces == ["summaries/{actorId}/{sessionId}"]

    def test_summary_strategy_to_dict(self):
        """Test SummaryStrategy to_dict conversion."""
        strategy = SummaryStrategy(name="TestSummary", description="Test description", namespaces=["test/{actorId}"])

        result = strategy.to_dict()
        expected = {
            "summaryMemoryStrategy": {
                "name": "TestSummary",
                "description": "Test description",
                "namespaces": ["test/{actorId}"],
            }
        }

        assert result == expected


class TestUserPreferenceStrategy:
    """Test UserPreferenceStrategy functionality."""

    def test_user_preference_strategy_creation(self):
        """Test basic UserPreferenceStrategy creation."""
        strategy = UserPreferenceStrategy(
            name="UserPreferences", description="Store user preferences", namespaces=["preferences/{actorId}"]
        )

        assert strategy.name == "UserPreferences"
        assert strategy.description == "Store user preferences"
        assert strategy.namespaces == ["preferences/{actorId}"]

    def test_user_preference_strategy_to_dict(self):
        """Test UserPreferenceStrategy to_dict conversion."""
        strategy = UserPreferenceStrategy(
            name="TestPreferences", description="Test description", namespaces=["test/{actorId}"]
        )

        result = strategy.to_dict()
        expected = {
            "userPreferenceMemoryStrategy": {
                "name": "TestPreferences",
                "description": "Test description",
                "namespaces": ["test/{actorId}"],
            }
        }

        assert result == expected


class TestCustomSemanticStrategy:
    """Test CustomSemanticStrategy functionality."""

    def test_custom_semantic_strategy_creation(self):
        """Test basic CustomSemanticStrategy creation."""
        extraction_config = ExtractionConfig(
            append_to_prompt="Extract insights", model_id="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Consolidate insights", model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )

        strategy = CustomSemanticStrategy(
            name="CustomExtraction",
            description="Custom semantic extraction",
            extraction_config=extraction_config,
            consolidation_config=consolidation_config,
            namespaces=["custom/{actorId}/{sessionId}"],
        )

        assert strategy.name == "CustomExtraction"
        assert strategy.description == "Custom semantic extraction"
        assert strategy.extraction_config == extraction_config
        assert strategy.consolidation_config == consolidation_config
        assert strategy.namespaces == ["custom/{actorId}/{sessionId}"]

    def test_custom_semantic_strategy_to_dict(self):
        """Test CustomSemanticStrategy to_dict conversion."""
        extraction_config = ExtractionConfig(
            append_to_prompt="Extract insights",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        )
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Consolidate insights",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )

        strategy = CustomSemanticStrategy(
            name="TestCustom",
            description="Test description",
            extraction_config=extraction_config,
            consolidation_config=consolidation_config,
            namespaces=["test/{actorId}"],
        )

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "TestCustom",
                "description": "Test description",
                "namespaces": ["test/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {
                            "appendToPrompt": "Extract insights",
                            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                        },
                        "consolidation": {
                            "appendToPrompt": "Consolidate insights",
                            "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                        },
                    }
                },
            }
        }

        assert result == expected

    def test_custom_semantic_strategy_to_dict_minimal_config(self):
        """Test CustomSemanticStrategy to_dict with minimal configuration."""
        extraction_config = ExtractionConfig()
        consolidation_config = ConsolidationConfig()

        strategy = CustomSemanticStrategy(
            name="MinimalCustom", extraction_config=extraction_config, consolidation_config=consolidation_config
        )

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "MinimalCustom",
                "configuration": {"semanticOverride": {"extraction": {}, "consolidation": {}}},
            }
        }

        assert result == expected

    def test_custom_semantic_strategy_validation(self):
        """Test CustomSemanticStrategy validation."""
        # extraction_config and consolidation_config are required
        with pytest.raises(ValidationError):
            CustomSemanticStrategy(name="Test")

        with pytest.raises(ValidationError):
            CustomSemanticStrategy(name="Test", extraction_config=ExtractionConfig())


class TestConvertStrategiesToDicts:
    """Test the convert_strategies_to_dicts function."""

    def test_convert_typed_strategies(self):
        """Test converting typed strategies to dictionaries."""
        strategies = [
            SemanticStrategy(name="Semantic1"),
            SummaryStrategy(name="Summary1"),
            UserPreferenceStrategy(name="Preferences1"),
        ]

        result = convert_strategies_to_dicts(strategies)

        assert len(result) == 3
        assert result[0] == {
            "semanticMemoryStrategy": {
                "name": "Semantic1",
            }
        }
        assert result[1] == {
            "summaryMemoryStrategy": {
                "name": "Summary1",
            }
        }
        assert result[2] == {
            "userPreferenceMemoryStrategy": {
                "name": "Preferences1",
            }
        }

    def test_convert_dict_strategies(self):
        """Test converting dictionary strategies (backward compatibility)."""
        strategies = [{"semanticMemoryStrategy": {"name": "Legacy1"}}, {"summaryMemoryStrategy": {"name": "Legacy2"}}]

        result = convert_strategies_to_dicts(strategies)

        assert len(result) == 2
        assert result[0] == {"semanticMemoryStrategy": {"name": "Legacy1"}}
        assert result[1] == {"summaryMemoryStrategy": {"name": "Legacy2"}}

    def test_convert_mixed_strategies(self):
        """Test converting mixed typed and dictionary strategies."""
        strategies = [
            SemanticStrategy(name="Typed1"),
            {"summaryMemoryStrategy": {"name": "Legacy1"}},
            UserPreferenceStrategy(name="Typed2"),
        ]

        result = convert_strategies_to_dicts(strategies)

        assert len(result) == 3
        assert result[0] == {
            "semanticMemoryStrategy": {
                "name": "Typed1",
            }
        }
        assert result[1] == {"summaryMemoryStrategy": {"name": "Legacy1"}}
        assert result[2] == {"userPreferenceMemoryStrategy": {"name": "Typed2"}}

    def test_convert_custom_semantic_strategy(self):
        """Test converting CustomSemanticStrategy."""
        extraction_config = ExtractionConfig(append_to_prompt="Extract")
        consolidation_config = ConsolidationConfig(append_to_prompt="Consolidate")

        strategies = [
            CustomSemanticStrategy(
                name="Custom1", extraction_config=extraction_config, consolidation_config=consolidation_config
            )
        ]

        result = convert_strategies_to_dicts(strategies)

        assert len(result) == 1
        expected = {
            "customMemoryStrategy": {
                "name": "Custom1",
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Extract"},
                        "consolidation": {"appendToPrompt": "Consolidate"},
                    }
                },
            }
        }
        assert result[0] == expected

    def test_convert_empty_list(self):
        """Test converting empty strategy list."""
        result = convert_strategies_to_dicts([])
        assert result == []

    def test_convert_invalid_strategy_type(self):
        """Test converting invalid strategy type raises error."""
        strategies = [
            SemanticStrategy(name="Valid"),
            "invalid_string",  # Invalid type
            {"valid": "dict"},
        ]

        with pytest.raises(ValueError, match="Invalid strategy type"):
            convert_strategies_to_dicts(strategies)

    def test_convert_invalid_object_type(self):
        """Test converting invalid object type raises error."""

        class InvalidStrategy:
            pass

        strategies = [InvalidStrategy()]

        with pytest.raises(ValueError, match="Invalid strategy type"):
            convert_strategies_to_dicts(strategies)


class TestStrategyTypeUnion:
    """Test the StrategyType union type."""

    def test_strategy_type_accepts_all_types(self):
        """Test that StrategyType union accepts all valid types."""
        # This test verifies the type union works correctly
        # In practice, this would be checked by mypy/type checkers

        semantic: StrategyType = SemanticStrategy(name="Test")
        summary: StrategyType = SummaryStrategy(name="Test")
        preference: StrategyType = UserPreferenceStrategy(name="Test")
        custom: StrategyType = CustomSemanticStrategy(
            name="Test", extraction_config=ExtractionConfig(), consolidation_config=ConsolidationConfig()
        )
        dict_strategy: StrategyType = {"semanticMemoryStrategy": {"name": "Test"}}

        # All should be valid StrategyType instances
        assert isinstance(semantic, BaseStrategy)
        assert isinstance(summary, BaseStrategy)
        assert isinstance(preference, BaseStrategy)
        assert isinstance(custom, BaseStrategy)
        assert isinstance(dict_strategy, dict)


class TestBaseStrategyAbstract:
    """Test BaseStrategy abstract class behavior."""

    def test_base_strategy_cannot_be_instantiated(self):
        """Test that BaseStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseStrategy(name="Test")

    def test_base_strategy_validation(self):
        """Test BaseStrategy field validation through concrete classes."""
        # Test through concrete implementation
        strategy = SemanticStrategy(name="Test")

        # Test name validation
        assert strategy.name == "Test"

        # Test that name is required
        with pytest.raises(ValidationError):
            SemanticStrategy()

    def test_base_strategy_optional_fields(self):
        """Test BaseStrategy optional fields through concrete classes."""
        strategy = SemanticStrategy(name="Test", description="Test description", namespaces=["test/namespace"])

        assert strategy.description == "Test description"
        assert strategy.namespaces == ["test/namespace"]

        # Test with None values
        strategy2 = SemanticStrategy(name="Test2")
        assert strategy2.description is None
        assert strategy2.namespaces is None


class TestPydanticIntegration:
    def test_model_serialization(self):
        """Test Pydantic model serialization."""
        strategy = SemanticStrategy(name="TestSemantic", description="Test description", namespaces=["test/{actorId}"])

        # Test model_dump() method (Pydantic v2)
        strategy_dict = strategy.model_dump()
        expected = {"name": "TestSemantic", "description": "Test description", "namespaces": ["test/{actorId}"]}
        assert strategy_dict == expected

        # Test model_dump_json() method (Pydantic v2)
        import json

        strategy_json = strategy.model_dump_json()
        assert json.loads(strategy_json) == expected

    def test_model_copy(self):
        """Test Pydantic model copying."""
        original = SemanticStrategy(name="Original", description="Original description")

        # Test model_copy with updates (Pydantic v2)
        copied = original.model_copy(update={"name": "Copied"})

        assert original.name == "Original"
        assert copied.name == "Copied"
        assert copied.description == "Original description"

    def test_field_descriptions(self):
        """Test that field descriptions are properly set."""
        # Check that fields have descriptions (used for API documentation)
        # Use model_fields for Pydantic v2
        extraction_fields = ExtractionConfig.model_fields

        assert "append_to_prompt" in extraction_fields
        assert extraction_fields["append_to_prompt"].description == "Additional prompt text for extraction"

        assert "model_id" in extraction_fields
        assert extraction_fields["model_id"].description == "Model identifier for extraction operations"


class TestCustomSummaryStrategy:
    """Comprehensive tests for CustomSummaryStrategy class."""

    def test_custom_summary_strategy_creation(self):
        """Test basic CustomSummaryStrategy creation."""
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Consolidate summaries", model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )

        strategy = CustomSummaryStrategy(
            name="CustomSummary",
            description="Custom summary extraction",
            consolidation_config=consolidation_config,
            namespaces=["summary/{actorId}/{sessionId}"],
        )

        assert strategy.name == "CustomSummary"
        assert strategy.description == "Custom summary extraction"
        assert strategy.consolidation_config == consolidation_config
        assert strategy.namespaces == ["summary/{actorId}/{sessionId}"]

    def test_custom_summary_strategy_minimal(self):
        """Test CustomSummaryStrategy with minimal configuration."""
        consolidation_config = ConsolidationConfig()

        strategy = CustomSummaryStrategy(name="MinimalSummary", consolidation_config=consolidation_config)

        assert strategy.name == "MinimalSummary"
        assert strategy.description is None
        assert strategy.namespaces is None
        assert strategy.consolidation_config == consolidation_config

    def test_custom_summary_strategy_to_dict_full(self):
        """Test CustomSummaryStrategy to_dict conversion with full configuration."""
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Consolidate insights", model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )

        strategy = CustomSummaryStrategy(
            name="TestSummary",
            description="Test summary description",
            consolidation_config=consolidation_config,
            namespaces=["test/{actorId}"],
        )

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "TestSummary",
                "description": "Test summary description",
                "namespaces": ["test/{actorId}"],
                "configuration": {
                    "summaryOverride": {
                        "consolidation": {
                            "appendToPrompt": "Consolidate insights",
                            "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                        }
                    }
                },
            }
        }

        assert result == expected

    def test_custom_summary_strategy_to_dict_minimal(self):
        """Test CustomSummaryStrategy to_dict with minimal configuration."""
        consolidation_config = ConsolidationConfig()

        strategy = CustomSummaryStrategy(name="MinimalSummary", consolidation_config=consolidation_config)

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "MinimalSummary",
                "configuration": {"summaryOverride": {"consolidation": {}}},
            }
        }

        assert result == expected

    def test_custom_summary_strategy_to_dict_partial_config(self):
        """Test CustomSummaryStrategy to_dict with partial configuration."""
        # Test with only append_to_prompt
        consolidation_config = ConsolidationConfig(append_to_prompt="Custom prompt")

        strategy = CustomSummaryStrategy(name="PartialSummary", consolidation_config=consolidation_config)

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "PartialSummary",
                "configuration": {"summaryOverride": {"consolidation": {"appendToPrompt": "Custom prompt"}}},
            }
        }

        assert result == expected

        # Test with only model_id
        consolidation_config = ConsolidationConfig(model_id="test-model")

        strategy = CustomSummaryStrategy(name="PartialSummary2", consolidation_config=consolidation_config)

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "PartialSummary2",
                "configuration": {"summaryOverride": {"consolidation": {"modelId": "test-model"}}},
            }
        }

        assert result == expected

    def test_custom_summary_strategy_validation(self):
        """Test CustomSummaryStrategy validation."""
        # consolidation_config is required
        with pytest.raises(ValidationError):
            CustomSummaryStrategy(name="Test")

        # name is required
        with pytest.raises(ValidationError):
            CustomSummaryStrategy(consolidation_config=ConsolidationConfig())

    def test_custom_summary_strategy_convert_consolidation_config(self):
        """Test _convert_consolidation_config method directly."""
        consolidation_config = ConsolidationConfig(append_to_prompt="Test prompt", model_id="test-model")

        strategy = CustomSummaryStrategy(name="Test", consolidation_config=consolidation_config)

        result = strategy._convert_consolidation_config()
        expected = {"appendToPrompt": "Test prompt", "modelId": "test-model"}

        assert result == expected

    def test_custom_summary_strategy_convert_consolidation_config_empty(self):
        """Test _convert_consolidation_config with empty config."""
        consolidation_config = ConsolidationConfig()

        strategy = CustomSummaryStrategy(name="Test", consolidation_config=consolidation_config)

        result = strategy._convert_consolidation_config()
        assert result == {}


class TestCustomUserPreferenceStrategy:
    """Comprehensive tests for CustomUserPreferenceStrategy class."""

    def test_custom_user_preference_strategy_creation(self):
        """Test basic CustomUserPreferenceStrategy creation."""
        extraction_config = ExtractionConfig(
            append_to_prompt="Extract preferences", model_id="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Consolidate preferences", model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )

        strategy = CustomUserPreferenceStrategy(
            name="CustomUserPref",
            description="Custom user preference extraction",
            extraction_config=extraction_config,
            consolidation_config=consolidation_config,
            namespaces=["preferences/{actorId}"],
        )

        assert strategy.name == "CustomUserPref"
        assert strategy.description == "Custom user preference extraction"
        assert strategy.extraction_config == extraction_config
        assert strategy.consolidation_config == consolidation_config
        assert strategy.namespaces == ["preferences/{actorId}"]

    def test_custom_user_preference_strategy_minimal(self):
        """Test CustomUserPreferenceStrategy with minimal configuration."""
        extraction_config = ExtractionConfig()
        consolidation_config = ConsolidationConfig()

        strategy = CustomUserPreferenceStrategy(
            name="MinimalUserPref", extraction_config=extraction_config, consolidation_config=consolidation_config
        )

        assert strategy.name == "MinimalUserPref"
        assert strategy.description is None
        assert strategy.namespaces is None

    def test_custom_user_preference_strategy_to_dict_full(self):
        """Test CustomUserPreferenceStrategy to_dict conversion with full configuration."""
        extraction_config = ExtractionConfig(
            append_to_prompt="Extract preferences", model_id="anthropic.claude-3-sonnet-20240229-v1:0"
        )
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Consolidate preferences", model_id="anthropic.claude-3-haiku-20240307-v1:0"
        )

        strategy = CustomUserPreferenceStrategy(
            name="TestUserPref",
            description="Test user preference description",
            extraction_config=extraction_config,
            consolidation_config=consolidation_config,
            namespaces=["test/{actorId}"],
        )

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "TestUserPref",
                "description": "Test user preference description",
                "namespaces": ["test/{actorId}"],
                "configuration": {
                    "userPreferenceOverride": {
                        "extraction": {
                            "appendToPrompt": "Extract preferences",
                            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
                        },
                        "consolidation": {
                            "appendToPrompt": "Consolidate preferences",
                            "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
                        },
                    }
                },
            }
        }

        assert result == expected

    def test_custom_user_preference_strategy_to_dict_minimal(self):
        """Test CustomUserPreferenceStrategy to_dict with minimal configuration."""
        extraction_config = ExtractionConfig()
        consolidation_config = ConsolidationConfig()

        strategy = CustomUserPreferenceStrategy(
            name="MinimalUserPref", extraction_config=extraction_config, consolidation_config=consolidation_config
        )

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "MinimalUserPref",
                "configuration": {"userPreferenceOverride": {"extraction": {}, "consolidation": {}}},
            }
        }

        assert result == expected

    def test_custom_user_preference_strategy_validation(self):
        """Test CustomUserPreferenceStrategy validation."""
        # Both extraction_config and consolidation_config are required
        with pytest.raises(ValidationError):
            CustomUserPreferenceStrategy(name="Test")

        with pytest.raises(ValidationError):
            CustomUserPreferenceStrategy(name="Test", extraction_config=ExtractionConfig())

        with pytest.raises(ValidationError):
            CustomUserPreferenceStrategy(name="Test", consolidation_config=ConsolidationConfig())

        # name is required
        with pytest.raises(ValidationError):
            CustomUserPreferenceStrategy(
                extraction_config=ExtractionConfig(), consolidation_config=ConsolidationConfig()
            )

    def test_custom_user_preference_strategy_convert_extraction_config(self):
        """Test _convert_extraction_config method directly."""
        extraction_config = ExtractionConfig(
            append_to_prompt="Test extraction prompt", model_id="test-extraction-model"
        )

        strategy = CustomUserPreferenceStrategy(
            name="Test", extraction_config=extraction_config, consolidation_config=ConsolidationConfig()
        )

        result = strategy._convert_extraction_config()
        expected = {"appendToPrompt": "Test extraction prompt", "modelId": "test-extraction-model"}

        assert result == expected

    def test_custom_user_preference_strategy_convert_extraction_config_empty(self):
        """Test _convert_extraction_config with empty config."""
        extraction_config = ExtractionConfig()

        strategy = CustomUserPreferenceStrategy(
            name="Test", extraction_config=extraction_config, consolidation_config=ConsolidationConfig()
        )

        result = strategy._convert_extraction_config()
        assert result == {}

    def test_custom_user_preference_strategy_convert_consolidation_config(self):
        """Test _convert_consolidation_config method directly."""
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Test consolidation prompt", model_id="test-consolidation-model"
        )

        strategy = CustomUserPreferenceStrategy(
            name="Test", extraction_config=ExtractionConfig(), consolidation_config=consolidation_config
        )

        result = strategy._convert_consolidation_config()
        expected = {"appendToPrompt": "Test consolidation prompt", "modelId": "test-consolidation-model"}

        assert result == expected

    def test_custom_user_preference_strategy_convert_consolidation_config_empty(self):
        """Test _convert_consolidation_config with empty config."""
        consolidation_config = ConsolidationConfig()

        strategy = CustomUserPreferenceStrategy(
            name="Test", extraction_config=ExtractionConfig(), consolidation_config=consolidation_config
        )

        result = strategy._convert_consolidation_config()
        assert result == {}


class TestCustomSemanticStrategyAdditionalCoverage:
    """Additional tests for CustomSemanticStrategy to improve coverage."""

    def test_custom_semantic_strategy_convert_extraction_config_partial(self):
        """Test _convert_extraction_config with partial configuration."""
        # Test with only append_to_prompt
        extraction_config = ExtractionConfig(append_to_prompt="Custom extraction prompt")

        strategy = CustomSemanticStrategy(
            name="Test", extraction_config=extraction_config, consolidation_config=ConsolidationConfig()
        )

        result = strategy._convert_extraction_config()
        expected = {"appendToPrompt": "Custom extraction prompt"}
        assert result == expected

        # Test with only model_id
        extraction_config = ExtractionConfig(model_id="custom-model")

        strategy = CustomSemanticStrategy(
            name="Test", extraction_config=extraction_config, consolidation_config=ConsolidationConfig()
        )

        result = strategy._convert_extraction_config()
        expected = {"modelId": "custom-model"}
        assert result == expected

    def test_custom_semantic_strategy_convert_consolidation_config_partial(self):
        """Test _convert_consolidation_config with partial configuration."""
        # Test with only append_to_prompt
        consolidation_config = ConsolidationConfig(append_to_prompt="Custom consolidation prompt")

        strategy = CustomSemanticStrategy(
            name="Test", extraction_config=ExtractionConfig(), consolidation_config=consolidation_config
        )

        result = strategy._convert_consolidation_config()
        expected = {"appendToPrompt": "Custom consolidation prompt"}
        assert result == expected

        # Test with only model_id
        consolidation_config = ConsolidationConfig(model_id="custom-consolidation-model")

        strategy = CustomSemanticStrategy(
            name="Test", extraction_config=ExtractionConfig(), consolidation_config=consolidation_config
        )

        result = strategy._convert_consolidation_config()
        expected = {"modelId": "custom-consolidation-model"}
        assert result == expected

    def test_custom_semantic_strategy_convert_configs_empty(self):
        """Test conversion methods with completely empty configs."""
        extraction_config = ExtractionConfig()
        consolidation_config = ConsolidationConfig()

        strategy = CustomSemanticStrategy(
            name="Test", extraction_config=extraction_config, consolidation_config=consolidation_config
        )

        assert strategy._convert_extraction_config() == {}
        assert strategy._convert_consolidation_config() == {}

    def test_custom_semantic_strategy_to_dict_no_optional_fields(self):
        """Test to_dict without optional description and namespaces."""
        extraction_config = ExtractionConfig(append_to_prompt="Extract")
        consolidation_config = ConsolidationConfig(append_to_prompt="Consolidate")

        strategy = CustomSemanticStrategy(
            name="TestNoOptional", extraction_config=extraction_config, consolidation_config=consolidation_config
        )

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "TestNoOptional",
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Extract"},
                        "consolidation": {"appendToPrompt": "Consolidate"},
                    }
                },
            }
        }

        assert result == expected
        # Ensure description and namespaces are not in the result
        assert "description" not in result["customMemoryStrategy"]
        assert "namespaces" not in result["customMemoryStrategy"]


class TestConfigurationEdgeCases:
    """Test edge cases for configuration handling."""

    def test_extraction_config_none_values(self):
        """Test ExtractionConfig with explicit None values."""
        config = ExtractionConfig(append_to_prompt=None, model_id=None)

        assert config.append_to_prompt is None
        assert config.model_id is None

    def test_consolidation_config_none_values(self):
        """Test ConsolidationConfig with explicit None values."""
        config = ConsolidationConfig(append_to_prompt=None, model_id=None)

        assert config.append_to_prompt is None
        assert config.model_id is None

    def test_custom_strategies_with_none_configs(self):
        """Test custom strategies with configs containing None values."""
        extraction_config = ExtractionConfig(append_to_prompt=None, model_id="test-model")
        consolidation_config = ConsolidationConfig(append_to_prompt="test-prompt", model_id=None)

        strategy = CustomSemanticStrategy(
            name="TestNoneValues", extraction_config=extraction_config, consolidation_config=consolidation_config
        )

        result = strategy.to_dict()

        # Only non-None values should be included
        extraction_result = result["customMemoryStrategy"]["configuration"]["semanticOverride"]["extraction"]
        consolidation_result = result["customMemoryStrategy"]["configuration"]["semanticOverride"]["consolidation"]

        assert extraction_result == {"modelId": "test-model"}
        assert consolidation_result == {"appendToPrompt": "test-prompt"}

    def test_all_custom_strategies_inheritance(self):
        """Test that all custom strategies properly inherit from BaseStrategy."""
        from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies.base import BaseStrategy

        # Test CustomSemanticStrategy
        extraction_config = ExtractionConfig()
        consolidation_config = ConsolidationConfig()

        semantic_strategy = CustomSemanticStrategy(
            name="TestSemantic", extraction_config=extraction_config, consolidation_config=consolidation_config
        )
        assert isinstance(semantic_strategy, BaseStrategy)

        # Test CustomSummaryStrategy
        summary_strategy = CustomSummaryStrategy(name="TestSummary", consolidation_config=consolidation_config)
        assert isinstance(summary_strategy, BaseStrategy)

        # Test CustomUserPreferenceStrategy
        user_pref_strategy = CustomUserPreferenceStrategy(
            name="TestUserPref", extraction_config=extraction_config, consolidation_config=consolidation_config
        )
        assert isinstance(user_pref_strategy, BaseStrategy)

    def test_custom_strategies_abstract_method_implementation(self):
        """Test that all custom strategies implement the abstract to_dict method."""
        extraction_config = ExtractionConfig()
        consolidation_config = ConsolidationConfig()

        strategies = [
            CustomSemanticStrategy(
                name="TestSemantic", extraction_config=extraction_config, consolidation_config=consolidation_config
            ),
            CustomSummaryStrategy(name="TestSummary", consolidation_config=consolidation_config),
            CustomUserPreferenceStrategy(
                name="TestUserPref", extraction_config=extraction_config, consolidation_config=consolidation_config
            ),
        ]

        for strategy in strategies:
            result = strategy.to_dict()
            assert isinstance(result, dict)
            assert "customMemoryStrategy" in result
            assert "name" in result["customMemoryStrategy"]


class TestSelfManagedStrategy:
    """Test SelfManagedStrategy functionality."""

    def test_self_managed_strategy_creation(self):
        """Test basic SelfManagedStrategy creation."""
        invocation_config = InvocationConfig(
            topic_arn="arn:aws:sns:us-east-1:123456789012:test-topic", payload_delivery_bucket_name="test-bucket"
        )

        strategy = SelfManagedStrategy(
            name="TestSelfManaged",
            description="Test self-managed strategy",
            trigger_conditions=[
                MessageBasedTrigger(message_count=10),
                TokenBasedTrigger(token_count=5000),
                TimeBasedTrigger(idle_session_timeout=40),
            ],
            invocation_config=invocation_config,
            historical_context_window_size=6,
        )

        assert strategy.name == "TestSelfManaged"
        assert strategy.description == "Test self-managed strategy"
        assert len(strategy.trigger_conditions) == 3
        assert strategy.historical_context_window_size == 6

    def test_self_managed_strategy_to_dict(self):
        """Test SelfManagedStrategy to_dict conversion."""
        invocation_config = InvocationConfig(
            topic_arn="arn:aws:sns:us-east-1:123456789012:test-topic", payload_delivery_bucket_name="test-bucket"
        )

        strategy = SelfManagedStrategy(
            name="TestSelfManaged",
            description="Test self-managed strategy",
            trigger_conditions=[
                MessageBasedTrigger(message_count=10),
                TokenBasedTrigger(token_count=5000),
                TimeBasedTrigger(idle_session_timeout=40),
            ],
            invocation_config=invocation_config,
            historical_context_window_size=6,
        )

        result = strategy.to_dict()
        expected = {
            "customMemoryStrategy": {
                "name": "TestSelfManaged",
                "description": "Test self-managed strategy",
                "configuration": {
                    "selfManagedConfiguration": {
                        "triggerConditions": [
                            {"messageBasedTrigger": {"messageCount": 10}},
                            {"tokenBasedTrigger": {"tokenCount": 5000}},
                            {"timeBasedTrigger": {"idleSessionTimeout": 40}},
                        ],
                        "invocationConfiguration": {
                            "topicArn": "arn:aws:sns:us-east-1:123456789012:test-topic",
                            "payloadDeliveryBucketName": "test-bucket",
                        },
                        "historicalContextWindowSize": 6,
                    }
                },
            }
        }

        assert result == expected
