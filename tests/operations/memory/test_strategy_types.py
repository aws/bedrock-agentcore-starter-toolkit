"""Tests for the typed strategy system in bedrock_agentcore.memory.strategy_types."""

import pytest
from pydantic import ValidationError

from bedrock_agentcore_starter_toolkit.operations.memory.models import (
    BaseStrategy,
    ConsolidationConfig,
    CustomSemanticStrategy,
    ExtractionConfig,
    SemanticStrategy,
    StrategyType,
    SummaryStrategy,
    UserPreferenceStrategy,
    convert_strategies_to_dicts,
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
