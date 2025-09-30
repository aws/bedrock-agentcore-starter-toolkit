"""Unit tests for strategy validation utilities."""

import pytest
from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.operations.memory.constants import StrategyType
from bedrock_agentcore_starter_toolkit.operations.memory.strategy_validator import (
    StrategyComparator,
    UniversalComparator,
    validate_existing_memory_strategies,
)
from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory


class TestStrategyComparator:
    """Test cases for StrategyComparator class."""

    def test_normalize_strategy_memory_semantic(self):
        """Test normalizing semantic strategy from memory response."""
        strategy = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test semantic strategy",
            "namespaces": ["semantic/{actorId}"]
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy)
        
        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "SemanticStrategy"
        assert normalized["description"] == "Test semantic strategy"
        assert normalized["namespaces"] == ["semantic/{actorId}"]

    def test_normalize_strategy_legacy_fields(self):
        """Test normalizing strategy with legacy field names."""
        strategy = {
            "memoryStrategyType": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test semantic strategy",
            "namespaces": ["semantic/{actorId}"]
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy)
        
        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "SemanticStrategy"

    def test_normalize_strategy_custom(self):
        """Test normalizing custom strategy with universal normalization."""
        strategy = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "description": "Test custom strategy",
            "namespaces": ["custom/{actorId}"],
            "configuration": {
                "semanticOverride": {
                    "extraction": {
                        "appendToPrompt": "Extract insights",
                        "modelId": "claude-3-sonnet"
                    },
                    "consolidation": {
                        "appendToPrompt": "Consolidate insights",
                        "modelId": "claude-3-haiku"
                    }
                }
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy)
        
        assert normalized["type"] == "CUSTOM"
        assert normalized["name"] == "CustomStrategy"
        # With universal normalization, the entire structure is normalized
        assert "configuration" in normalized
        assert "semantic_override" in normalized["configuration"]

    def test_normalize_strategy_semantic(self):
        """Test normalizing semantic strategy from request."""
        strategy_dict = {
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test semantic strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy_dict)
        
        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "SemanticStrategy"
        assert normalized["description"] == "Test semantic strategy"
        assert normalized["namespaces"] == ["semantic/{actorId}"]

    def test_normalize_strategy_custom_request(self):
        """Test normalizing custom strategy from request."""
        strategy_dict = {
            "customMemoryStrategy": {
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {
                            "appendToPrompt": "Extract insights",
                            "modelId": "claude-3-sonnet"
                        },
                        "consolidation": {
                            "appendToPrompt": "Consolidate insights",
                            "modelId": "claude-3-haiku"
                        }
                    }
                }
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy_dict)
        
        assert normalized["type"] == "CUSTOM"
        assert normalized["name"] == "CustomStrategy"
        # With universal normalization, the entire structure is normalized
        assert "configuration" in normalized
        assert "semantic_override" in normalized["configuration"]

    def test_normalize_strategy_invalid_format(self):
        """Test normalizing strategy with invalid format."""
        strategy_dict = {"invalid": {"name": "Test"}}
        
        with pytest.raises(ValueError, match="Invalid strategy format"):
            StrategyComparator.normalize_strategy(strategy_dict)

    def test_compare_strategies_matching_semantic(self):
        """Test comparing matching semantic strategies."""
        existing = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is True
        assert error == ""

    def test_compare_strategies_name_mismatch(self):
        """Test comparing strategies with name mismatch."""
        existing = [{
            "type": "SEMANTIC",
            "name": "ExistingStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested = [{
            "semanticMemoryStrategy": {
                "name": "RequestedStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is False
        assert "name: value mismatch" in error
        assert "ExistingStrategy" in error
        assert "RequestedStrategy" in error

    def test_compare_strategies_description_mismatch(self):
        """Test comparing strategies with description mismatch."""
        existing = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Existing description",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Requested description",
                "namespaces": ["semantic/{actorId}"]
            }
        }]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is False
        assert "description: value mismatch" in error

    def test_compare_strategies_namespaces_mismatch(self):
        """Test comparing strategies with namespaces mismatch."""
        existing = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["different/{actorId}"]
            }
        }]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is False
        assert "namespaces: mismatch" in error

    def test_compare_strategies_custom_extraction_mismatch(self):
        """Test comparing custom strategies with extraction config mismatch."""
        existing = [{
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "description": "Test custom strategy",
            "namespaces": ["custom/{actorId}"],
            "configuration": {
                "semanticOverride": {
                    "extraction": {
                        "appendToPrompt": "Existing prompt",
                        "modelId": "claude-3-sonnet"
                    },
                    "consolidation": {
                        "appendToPrompt": "Consolidate insights",
                        "modelId": "claude-3-haiku"
                    }
                }
            }
        }]
        
        requested = [{
            "customMemoryStrategy": {
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {
                            "appendToPrompt": "Requested prompt",
                            "modelId": "claude-3-sonnet"
                        },
                        "consolidation": {
                            "appendToPrompt": "Consolidate insights",
                            "modelId": "claude-3-haiku"
                        }
                    }
                }
            }
        }]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is False
        assert "append_to_prompt: value mismatch" in error

    def test_compare_strategies_count_mismatch(self):
        """Test comparing strategies with different counts."""
        existing = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"]
                }
            },
            {
                "summaryMemoryStrategy": {
                    "name": "SummaryStrategy",
                    "description": "Test summary strategy"
                }
            }
        ]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is False
        assert "Strategy count mismatch" in error

    def test_compare_strategies_empty_both(self):
        """Test comparing when both existing and requested are empty."""
        existing = []
        requested = []
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is True
        assert error == ""

    def test_compare_strategies_description_none_equivalence(self):
        """Test that None and empty descriptions are treated as equivalent."""
        existing = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": None,
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "namespaces": ["semantic/{actorId}"]
                # No description field
            }
        }]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is True
        assert error == ""

    def test_compare_strategies_namespaces_order_independent(self):
        """Test that namespace order doesn't matter."""
        existing = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}", "semantic/{sessionId}"]
        }]
        
        requested = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{sessionId}", "semantic/{actorId}"]  # Different order
            }
        }]
        
        matches, error = StrategyComparator.compare_strategies(existing, requested)
        
        assert matches is True
        assert error == ""

    def test_universal_compare_type_mismatch(self):
        """Test universal comparison with type mismatch."""
        existing = {"type": "SEMANTIC", "name": "Test"}
        requested = {"type": "SUMMARIZATION", "name": "Test"}
        
        matches, error = UniversalComparator.deep_compare(existing, requested)
        
        assert matches is False
        assert "type: value mismatch" in error

    def test_universal_compare_none_equivalence(self):
        """Test that None and empty values are treated as equivalent."""
        existing = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "description": "Test",
            "namespaces": [],
            "config": {"field": None}
        }
        
        requested = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "description": "Test",
            "namespaces": [],
            "config": {}
        }
        
        matches, error = UniversalComparator.deep_compare(existing, requested)
        
        assert matches is True
        assert error == ""


class TestValidateExistingMemoryStrategies:
    """Test cases for validate_existing_memory_strategies function."""

    def test_validate_matching_strategies(self):
        """Test validation with matching strategies."""
        memory_strategies = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested_strategies = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }]
        
        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_mismatched_strategies(self):
        """Test validation with mismatched strategies."""
        memory_strategies = [{
            "type": "SEMANTIC",
            "name": "ExistingStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested_strategies = [{
            "semanticMemoryStrategy": {
                "name": "RequestedStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }]
        
        with pytest.raises(ValueError, match="Strategy mismatch"):
            validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_custom_strategies_matching(self):
        """Test validation with matching custom strategies."""
        memory_strategies = [{
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "description": "Test custom strategy",
            "namespaces": ["custom/{actorId}"],
            "configuration": {
                "semanticOverride": {
                    "extraction": {
                        "appendToPrompt": "Extract insights",
                        "modelId": "claude-3-sonnet"
                    },
                    "consolidation": {
                        "appendToPrompt": "Consolidate insights",
                        "modelId": "claude-3-haiku"
                    }
                }
            }
        }]
        
        requested_strategies = [{
            "customMemoryStrategy": {
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {
                            "appendToPrompt": "Extract insights",
                            "modelId": "claude-3-sonnet"
                        },
                        "consolidation": {
                            "appendToPrompt": "Consolidate insights",
                            "modelId": "claude-3-haiku"
                        }
                    }
                }
            }
        }]
        
        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_custom_strategies_extraction_mismatch(self):
        """Test validation with custom strategies having extraction config mismatch."""
        memory_strategies = [{
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "description": "Test custom strategy",
            "namespaces": ["custom/{actorId}"],
            "configuration": {
                "semanticOverride": {
                    "extraction": {
                        "appendToPrompt": "Existing prompt",
                        "modelId": "claude-3-sonnet"
                    },
                    "consolidation": {
                        "appendToPrompt": "Consolidate insights",
                        "modelId": "claude-3-haiku"
                    }
                }
            }
        }]
        
        requested_strategies = [{
            "customMemoryStrategy": {
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {
                            "appendToPrompt": "Requested prompt",
                            "modelId": "claude-3-sonnet"
                        },
                        "consolidation": {
                            "appendToPrompt": "Consolidate insights",
                            "modelId": "claude-3-haiku"
                        }
                    }
                }
            }
        }]
        
        with pytest.raises(ValueError, match="append_to_prompt: value mismatch"):
            validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_multiple_strategies_matching(self):
        """Test validation with multiple matching strategies."""
        memory_strategies = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test semantic strategy",
                "namespaces": ["semantic/{actorId}"]
            },
            {
                "type": "SUMMARIZATION",
                "name": "SummaryStrategy",
                "description": "Test summary strategy",
                "namespaces": ["summary/{actorId}"]
            }
        ]
        
        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test semantic strategy",
                    "namespaces": ["semantic/{actorId}"]
                }
            },
            {
                "summaryMemoryStrategy": {
                    "name": "SummaryStrategy",
                    "description": "Test summary strategy",
                    "namespaces": ["summary/{actorId}"]
                }
            }
        ]
        
        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_multiple_strategies_order_independent(self):
        """Test validation with multiple strategies in different order."""
        memory_strategies = [
            {
                "type": "SUMMARIZATION",
                "name": "SummaryStrategy",
                "description": "Test summary strategy",
                "namespaces": ["summary/{actorId}"]
            },
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test semantic strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        ]
        
        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test semantic strategy",
                    "namespaces": ["semantic/{actorId}"]
                }
            },
            {
                "summaryMemoryStrategy": {
                    "name": "SummaryStrategy",
                    "description": "Test summary strategy",
                    "namespaces": ["summary/{actorId}"]
                }
            }
        ]
        
        # Should not raise any exception (order shouldn't matter)
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_with_logging(self):
        """Test that successful validation logs appropriate message."""
        memory_strategies = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested_strategies = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }]
        
        with patch("bedrock_agentcore_starter_toolkit.operations.memory.strategy_validator.logger") as mock_logger:
            validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

            # Should log success message (may be called multiple times due to debug logging)
            assert mock_logger.info.call_count >= 1

            # Check that the success message was logged
            success_logged = False
            for call in mock_logger.info.call_args_list:
                if len(call[0]) >= 2 and "Universal strategy validation passed" in call[0][0]:
                    assert "TestMemory" in call[0][1]
                    success_logged = True
                    break

            assert success_logged, "Success message was not logged"

    def test_validate_normalization_error_handling(self):
        """Test validation handles normalization errors gracefully."""
        # Create strategy that will cause normalization to fail by raising an exception
        memory_strategies = [{"malformed": "strategy"}]
        requested_strategies = [{
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test strategy"
            }
        }]
        
        # Mock the normalize_strategy to raise an exception for the first call only
        side_effects = [Exception("Normalization error"), StrategyComparator.normalize_strategy(requested_strategies[0])]
        with patch.object(StrategyComparator, 'normalize_strategy', side_effect=side_effects):
            with patch("bedrock_agentcore_starter_toolkit.operations.memory.strategy_validator.logger") as mock_logger:
                # Should handle the error and continue with empty normalized list
                matches, error = StrategyComparator.compare_strategies(memory_strategies, requested_strategies)
                
                # Should log warning about normalization failure
                mock_logger.warning.assert_called()
                
                # Should detect count mismatch (0 vs 1)
                assert matches is False
                assert "Strategy count mismatch" in error

    def test_validate_user_preference_strategy(self):
        """Test validation with user preference strategies."""
        memory_strategies = [{
            "type": "USER_PREFERENCE",
            "name": "UserPrefStrategy",
            "description": "Test user preference strategy",
            "namespaces": ["preferences/{actorId}"]
        }]
        
        requested_strategies = [{
            "userPreferenceMemoryStrategy": {
                "name": "UserPrefStrategy",
                "description": "Test user preference strategy",
                "namespaces": ["preferences/{actorId}"]
            }
        }]
        
        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_strategy_enum_values(self):
        """Test validation with StrategyType enum values."""
        memory_strategies = [{
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
        }]
        
        requested_strategies = [{
            StrategyType.SEMANTIC.value: {
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }]
        
        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_normalize_strategy_missing_namespaces(self):
        """Test normalizing strategy without namespaces field."""
        strategy = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy"
            # No namespaces field
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy)
        
        assert normalized["namespaces"] == []  # Should default to empty list

    def test_normalize_strategy_custom_without_config(self):
        """Test normalizing custom strategy without configuration."""
        strategy = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "description": "Test custom strategy",
            "namespaces": ["custom/{actorId}"]
            # No configuration field
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy)
        
        assert normalized["type"] == "CUSTOM"
        assert normalized["name"] == "CustomStrategy"
        # Configuration field should not be present
        assert "configuration" not in normalized or not normalized["configuration"]


class TestUniversalComparator:
    """Test cases for UniversalComparator class."""

    def test_normalize_field_names_simple_dict(self):
        """Test field name normalization for simple dictionary."""
        data = {
            "appendToPrompt": "test prompt",
            "modelId": "test-model",
            "simpleField": "value"
        }
        
        normalized = UniversalComparator.normalize_field_names(data)
        
        assert normalized["append_to_prompt"] == "test prompt"
        assert normalized["model_id"] == "test-model"
        assert normalized["simple_field"] == "value"

    def test_normalize_field_names_nested_dict(self):
        """Test field name normalization for nested dictionary."""
        data = {
            "topLevel": {
                "nestedField": "nested_value",
                "anotherNested": {
                    "deepField": "deep_value"
                }
            }
        }
        
        normalized = UniversalComparator.normalize_field_names(data)
        
        assert normalized["top_level"]["nested_field"] == "nested_value"
        assert normalized["top_level"]["another_nested"]["deep_field"] == "deep_value"

    def test_normalize_field_names_with_lists(self):
        """Test field name normalization with lists."""
        data = {
            "listField": [
                {"itemField": "value1"},
                {"itemField": "value2"}
            ]
        }
        
        normalized = UniversalComparator.normalize_field_names(data)
        
        assert normalized["list_field"][0]["item_field"] == "value1"
        assert normalized["list_field"][1]["item_field"] == "value2"

    def test_deep_compare_matching_dicts(self):
        """Test deep comparison of matching dictionaries."""
        dict1 = {"name": "test", "config": {"field": "value"}}
        dict2 = {"name": "test", "config": {"field": "value"}}
        
        matches, error = UniversalComparator.deep_compare(dict1, dict2)
        
        assert matches is True
        assert error == ""

    def test_deep_compare_mismatched_dicts(self):
        """Test deep comparison of mismatched dictionaries."""
        dict1 = {"name": "test1", "config": {"field": "value"}}
        dict2 = {"name": "test2", "config": {"field": "value"}}
        
        matches, error = UniversalComparator.deep_compare(dict1, dict2)
        
        assert matches is False
        assert "name: value mismatch" in error

    def test_deep_compare_nested_mismatch(self):
        """Test deep comparison with nested mismatch."""
        dict1 = {"name": "test", "config": {"field": "value1"}}
        dict2 = {"name": "test", "config": {"field": "value2"}}
        
        matches, error = UniversalComparator.deep_compare(dict1, dict2)
        
        assert matches is False
        assert "config.field: value mismatch" in error

    def test_deep_compare_list_mismatch(self):
        """Test deep comparison with list length mismatch."""
        dict1 = {"items": ["a", "b"]}
        dict2 = {"items": ["a", "b", "c"]}
        
        matches, error = UniversalComparator.deep_compare(dict1, dict2)
        
        assert matches is False
        assert "list length mismatch" in error

class TestFutureProofValidation:
    """Test cases for future-proof dynamic validation using UniversalComparator."""

    def test_universal_field_comparison_basic_strategy(self):
        """Test that universal comparison works for basic strategies with new fields."""
        existing = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
            "new_future_field": "existing_value"  # Simulated future field
        }
        
        requested = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
            "new_future_field": "existing_value"  # Same value
        }
        
        matches, error = UniversalComparator.deep_compare(existing, requested)
        
        assert matches is True
        assert error == ""

    def test_universal_field_comparison_mismatch(self):
        """Test that universal comparison detects mismatches in new fields."""
        existing = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
            "new_future_field": "existing_value"
        }
        
        requested = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
            "new_future_field": "different_value"  # Different value
        }
        
        matches, error = UniversalComparator.deep_compare(existing, requested)
        
        assert matches is False
        assert "new_future_field: value mismatch" in error
        assert "existing_value" in error
        assert "different_value" in error

    def test_universal_field_comparison_missing_field(self):
        """Test that universal comparison handles missing fields."""
        existing = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
            "new_future_field": "existing_value"
        }
        
        requested = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"]
            # Missing new_future_field
        }
        
        matches, error = UniversalComparator.deep_compare(existing, requested)
        
        assert matches is False
        assert "new_future_field: type mismatch" in error
        assert "str" in error
        assert "NoneType" in error

    def test_universal_nested_config_comparison(self):
        """Test that universal comparison works for nested configurations."""
        existing = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "config": {
                "nested": {
                    "field1": "value1",
                    "field2": "value2"
                }
            }
        }
        
        requested = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "config": {
                "nested": {
                    "field1": "value1",
                    "field2": "value2"
                }
            }
        }
        
        matches, error = UniversalComparator.deep_compare(existing, requested)
        
        assert matches is True
        assert error == ""

    def test_universal_nested_config_mismatch(self):
        """Test that universal comparison detects nested mismatches."""
        existing = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "config": {
                "nested": {
                    "field1": "existing_value",
                    "field2": "value2"
                }
            }
        }
        
        requested = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "config": {
                "nested": {
                    "field1": "different_value",
                    "field2": "value2"
                }
            }
        }
        
        matches, error = UniversalComparator.deep_compare(existing, requested)
        
        assert matches is False
        assert "config.nested.field1: value mismatch" in error
        assert "existing_value" in error
        assert "different_value" in error

class TestFutureProofNormalization:
    """Test cases for future-proof normalization logic."""

    def test_camel_to_snake_conversion(self):
        """Test camelCase to snake_case conversion."""
        assert UniversalComparator._camel_to_snake("appendToPrompt") == "append_to_prompt"
        assert UniversalComparator._camel_to_snake("modelId") == "model_id"
        assert UniversalComparator._camel_to_snake("newFutureField") == "new_future_field"
        assert UniversalComparator._camel_to_snake("simpleField") == "simple_field"
        assert UniversalComparator._camel_to_snake("alreadySnake") == "already_snake"
        assert UniversalComparator._camel_to_snake("XMLHttpRequest") == "xml_http_request"

    def test_normalize_new_strategy_type(self):
        """Test normalization with a new strategy type following naming convention."""
        strategy_dict = {
            "newTypeMemoryStrategy": {
                "name": "NewTypeStrategy",
                "description": "Test new type strategy",
                "namespaces": ["newtype/{actorId}"]
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy_dict)
        
        assert normalized["type"] == "NEW_TYPE"
        assert normalized["name"] == "NewTypeStrategy"
        assert normalized["description"] == "Test new type strategy"
        assert normalized["namespaces"] == ["newtype/{actorId}"]

    def test_normalize_custom_with_new_fields(self):
        """Test normalization of custom strategy with new camelCase fields."""
        strategy_dict = {
            "customMemoryStrategy": {
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "newFutureField": "future_value",  # Future field at strategy level
                "configuration": {
                    "semanticOverride": {
                        "extraction": {
                            "appendToPrompt": "Extract insights",
                            "modelId": "claude-3-sonnet",
                            "newExtractionField": "new_value"  # Future camelCase field
                        }
                    }
                }
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy_dict)
        
        assert normalized["type"] == "CUSTOM"
        assert normalized["name"] == "CustomStrategy"
        assert normalized["new_future_field"] == "future_value"  # Converted to snake_case
        # Check that nested fields were also normalized
        assert "configuration" in normalized
        assert "semantic_override" in normalized["configuration"]

    def test_normalize_enum_values(self):
        """Test normalization with StrategyType enum values."""
        from bedrock_agentcore_starter_toolkit.operations.memory.constants import StrategyType
        
        strategy_dict = {
            StrategyType.SEMANTIC.value: {
                "name": "SemanticStrategy",
                "description": "Test semantic strategy",
                "namespaces": ["semantic/{actorId}"]
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy_dict)
        
        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "SemanticStrategy"
        assert normalized["description"] == "Test semantic strategy"
        assert normalized["namespaces"] == ["semantic/{actorId}"]

    def test_normalize_invalid_format_still_fails(self):
        """Test that invalid strategy formats still raise errors."""
        strategy_dict = {"invalid": {"name": "Test"}}
        
        with pytest.raises(ValueError, match="Invalid strategy format"):
            StrategyComparator.normalize_strategy(strategy_dict)

    def test_normalize_custom_without_configuration(self):
        """Test normalization of custom strategy without configuration section."""
        strategy_dict = {
            "customMemoryStrategy": {
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"]
                # No configuration section
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy_dict)
        
        assert normalized["type"] == "CUSTOM"
        assert normalized["name"] == "CustomStrategy"
        # Should not have configuration field when not provided
        assert "configuration" not in normalized

    def test_normalize_preserves_unknown_fields(self):
        """Test that normalization preserves unknown fields in strategy config."""
        strategy_dict = {
            "semanticMemoryStrategy": {
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
                "newFutureField": "future_value",  # Future field
                "anotherNewField": {"nested": "data"}
            }
        }
        
        normalized = StrategyComparator.normalize_strategy(strategy_dict)
        
        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "SemanticStrategy"
        assert normalized["description"] == "Test strategy"
        assert normalized["namespaces"] == ["semantic/{actorId}"]
        # Future fields should be preserved with normalized names
        assert normalized["new_future_field"] == "future_value"
        assert normalized["another_new_field"] == {"nested": "data"}
