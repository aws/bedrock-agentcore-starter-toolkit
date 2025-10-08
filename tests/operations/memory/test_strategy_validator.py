"""Unit tests for strategy validation utilities."""

from unittest.mock import patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.memory.constants import StrategyType
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies.base import (
    ConsolidationConfig,
    ExtractionConfig,
)
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies.custom import (
    CustomSemanticStrategy,
    CustomSummaryStrategy,
    CustomUserPreferenceStrategy,
)
from bedrock_agentcore_starter_toolkit.operations.memory.strategy_validator import (
    StrategyComparator,
    UniversalComparator,
    validate_existing_memory_strategies,
)


class TestStrategyComparatorEdgeCases:
    """Test edge cases and missing coverage in StrategyComparator."""

    def test_normalize_memory_strategy_with_configuration(self):
        """Test _normalize_memory_strategy with various configuration types."""
        # Test with configuration present
        strategy = {
            "type": "CUSTOM",
            "name": "TestStrategy",
            "description": "Test description",
            "namespaces": ["test/{actorId}"],
            "configuration": {
                "type": "SEMANTIC_OVERRIDE",
                "extraction": {
                    "customExtractionConfiguration": {
                        "semanticOverride": {"appendToPrompt": "Extract test", "modelId": "test-model"}
                    }
                },
                "consolidation": {
                    "customConsolidationConfiguration": {
                        "semanticOverride": {
                            "appendToPrompt": "Consolidate test",
                            "modelId": "test-consolidation-model",
                        }
                    }
                },
            },
        }

        normalized = StrategyComparator._normalize_memory_strategy(strategy)

        assert normalized["type"] == "CUSTOM"
        assert normalized["name"] == "TestStrategy"
        assert normalized["description"] == "Test description"
        assert normalized["namespaces"] == ["test/{actorId}"]
        assert "configuration" in normalized

    def test_normalize_memory_strategy_without_configuration(self):
        """Test _normalize_memory_strategy without configuration."""
        strategy = {
            "type": "SEMANTIC",
            "name": "TestStrategy",
            "description": "Test description",
            "namespaces": ["test/{actorId}"],
        }

        normalized = StrategyComparator._normalize_memory_strategy(strategy)

        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "TestStrategy"
        assert normalized["description"] == "Test description"
        assert normalized["namespaces"] == ["test/{actorId}"]

    def test_transform_memory_configuration_semantic_override(self):
        """Test _transform_memory_configuration with SEMANTIC_OVERRIDE."""
        config = {
            "type": "SEMANTIC_OVERRIDE",
            "extraction": {
                "customExtractionConfiguration": {
                    "semanticOverride": {"appendToPrompt": "Extract semantic", "modelId": "semantic-model"}
                }
            },
            "consolidation": {
                "customConsolidationConfiguration": {
                    "semanticOverride": {"appendToPrompt": "Consolidate semantic", "modelId": "consolidation-model"}
                }
            },
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        expected = {
            "semanticOverride": {
                "extraction": {"appendToPrompt": "Extract semantic", "modelId": "semantic-model"},
                "consolidation": {"appendToPrompt": "Consolidate semantic", "modelId": "consolidation-model"},
            }
        }

        assert result == expected

    def test_transform_memory_configuration_user_preference_override(self):
        """Test _transform_memory_configuration with USER_PREFERENCE_OVERRIDE."""
        config = {
            "type": "USER_PREFERENCE_OVERRIDE",
            "extraction": {
                "customExtractionConfiguration": {
                    "userPreferenceOverride": {"appendToPrompt": "Extract preferences", "modelId": "preference-model"}
                }
            },
            "consolidation": {
                "customConsolidationConfiguration": {
                    "userPreferenceOverride": {
                        "appendToPrompt": "Consolidate preferences",
                        "modelId": "preference-consolidation-model",
                    }
                }
            },
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        expected = {
            "userPreferenceOverride": {
                "extraction": {"appendToPrompt": "Extract preferences", "modelId": "preference-model"},
                "consolidation": {
                    "appendToPrompt": "Consolidate preferences",
                    "modelId": "preference-consolidation-model",
                },
            }
        }

        assert result == expected

    def test_transform_memory_configuration_summary_override(self):
        """Test _transform_memory_configuration with SUMMARY_OVERRIDE."""
        config = {
            "type": "SUMMARY_OVERRIDE",
            "consolidation": {
                "customConsolidationConfiguration": {
                    "summaryOverride": {"appendToPrompt": "Consolidate summaries", "modelId": "summary-model"}
                }
            },
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        expected = {
            "summaryOverride": {
                "consolidation": {"appendToPrompt": "Consolidate summaries", "modelId": "summary-model"}
            }
        }

        assert result == expected

    def test_transform_memory_configuration_snake_case(self):
        """Test _transform_memory_configuration with snake_case fields."""
        config = {
            "type": "SEMANTIC_OVERRIDE",
            "extraction": {
                "custom_extraction_configuration": {
                    "semantic_override": {"append_to_prompt": "Extract semantic", "model_id": "semantic-model"}
                }
            },
            "consolidation": {
                "custom_consolidation_configuration": {
                    "semantic_override": {"append_to_prompt": "Consolidate semantic", "model_id": "consolidation-model"}
                }
            },
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        expected = {
            "semanticOverride": {
                "extraction": {"append_to_prompt": "Extract semantic", "model_id": "semantic-model"},
                "consolidation": {"append_to_prompt": "Consolidate semantic", "model_id": "consolidation-model"},
            }
        }

        assert result == expected

    def test_transform_memory_configuration_direct_config(self):
        """Test _transform_memory_configuration with direct config (no wrapper)."""
        config = {
            "type": "SEMANTIC_OVERRIDE",
            "extraction": {"appendToPrompt": "Direct extraction", "modelId": "direct-model"},
            "consolidation": {"appendToPrompt": "Direct consolidation", "modelId": "direct-consolidation-model"},
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        expected = {
            "semanticOverride": {
                "extraction": {"appendToPrompt": "Direct extraction", "modelId": "direct-model"},
                "consolidation": {"appendToPrompt": "Direct consolidation", "modelId": "direct-consolidation-model"},
            }
        }

        assert result == expected

    def test_transform_memory_configuration_unknown_type(self):
        """Test _transform_memory_configuration with unknown override type."""
        config = {"type": "UNKNOWN_OVERRIDE", "extraction": {"test": "value"}}

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        # Should return original config for unknown types
        assert result == config

    def test_transform_memory_configuration_non_custom_strategy(self):
        """Test _transform_memory_configuration with non-CUSTOM strategy."""
        config = {"type": "SEMANTIC_OVERRIDE", "extraction": {"test": "value"}}

        result = StrategyComparator._transform_memory_configuration(config, "SEMANTIC")

        # Should return original config for non-CUSTOM strategies
        assert result == config

    def test_transform_memory_configuration_empty_config(self):
        """Test _transform_memory_configuration with empty config."""
        result = StrategyComparator._transform_memory_configuration({}, "CUSTOM")
        assert result == {}

        result = StrategyComparator._transform_memory_configuration(None, "CUSTOM")
        assert result is None

    def test_transform_memory_configuration_with_other_fields(self):
        """Test _transform_memory_configuration preserves other fields."""
        config = {
            "type": "SEMANTIC_OVERRIDE",
            "extraction": {
                "customExtractionConfiguration": {"semanticOverride": {"appendToPrompt": "Extract", "modelId": "model"}}
            },
            "otherField": "otherValue",
            "anotherField": {"nested": "data"},
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        assert "semanticOverride" in result
        assert result["otherField"] == "otherValue"
        assert result["anotherField"] == {"nested": "data"}

    def test_normalize_request_strategy_future_strategy_type(self):
        """Test _normalize_request_strategy with future strategy type following naming convention."""
        strategy_dict = {
            "newTypeMemoryStrategy": {
                "name": "NewTypeStrategy",
                "description": "Test new type strategy",
                "namespaces": ["newtype/{actorId}"],
                "customField": "customValue",
            }
        }

        normalized = StrategyComparator._normalize_request_strategy(strategy_dict)

        assert normalized["type"] == "NEW_TYPE"
        assert normalized["name"] == "NewTypeStrategy"
        assert normalized["description"] == "Test new type strategy"
        assert normalized["namespaces"] == ["newtype/{actorId}"]
        assert normalized["custom_field"] == "customValue"

    def test_normalize_request_strategy_excluded_fields(self):
        """Test _normalize_request_strategy excludes metadata fields."""
        strategy_dict = {
            "semanticMemoryStrategy": {
                "name": "TestStrategy",
                "description": "Test description",
                "namespaces": ["test/{actorId}"],
                "status": "ACTIVE",  # Should be excluded
                "strategyId": "strategy-123",  # Should be excluded
                "customField": "customValue",  # Should be included
            }
        }

        normalized = StrategyComparator._normalize_request_strategy(strategy_dict)

        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "TestStrategy"
        assert normalized["description"] == "Test description"
        assert normalized["namespaces"] == ["test/{actorId}"]
        assert normalized["custom_field"] == "customValue"
        # Excluded fields should not be present
        assert "status" not in normalized
        assert "strategy_id" not in normalized

    def test_compare_strategies_with_typed_strategies(self):
        """Test compare_strategies with typed strategy objects."""
        existing = [
            {
                "type": "CUSTOM",
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Extract insights", "modelId": "claude-3-sonnet"},
                        "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                    }
                },
            }
        ]

        # Use typed strategy objects
        extraction_config = ExtractionConfig(append_to_prompt="Extract insights", model_id="claude-3-sonnet")
        consolidation_config = ConsolidationConfig(append_to_prompt="Consolidate insights", model_id="claude-3-haiku")

        requested = [
            CustomSemanticStrategy(
                name="CustomStrategy",
                description="Test custom strategy",
                extraction_config=extraction_config,
                consolidation_config=consolidation_config,
                namespaces=["custom/{actorId}"],
            )
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is True
        assert error == ""

    def test_compare_strategies_normalization_exception_handling(self):
        """Test compare_strategies handles normalization exceptions gracefully."""
        existing = [{"malformed": "strategy"}]
        requested = [{"semanticMemoryStrategy": {"name": "Test"}}]

        with patch.object(StrategyComparator, "normalize_strategy") as mock_normalize:
            # First call (existing) raises exception, second call (requested) succeeds
            mock_normalize.side_effect = [
                Exception("Normalization failed"),
                {"type": "SEMANTIC", "name": "Test", "description": None, "namespaces": []},
            ]

            with patch("bedrock_agentcore_starter_toolkit.operations.memory.strategy_validator.logger") as mock_logger:
                matches, error = StrategyComparator.compare_strategies(existing, requested)

                # Should log warning about normalization failure
                mock_logger.warning.assert_called()

                # Should detect count mismatch (0 vs 1 after filtering out failed normalization)
                assert matches is False
                assert "Strategy count mismatch" in error


class TestUniversalComparatorEdgeCases:
    """Test edge cases and missing coverage in UniversalComparator."""

    def test_camel_to_snake_complex_cases(self):
        """Test _camel_to_snake with complex cases."""
        test_cases = [
            ("XMLHttpRequest", "xml_http_request"),
            ("HTMLParser", "html_parser"),
            ("JSONData", "json_data"),
            ("APIKey", "api_key"),
            ("URLPath", "url_path"),
            ("HTTPSConnection", "https_connection"),
            ("simpleCase", "simple_case"),
            ("already_snake", "already_snake"),
            ("MixedCASEExample", "mixed_case_example"),
            ("A", "a"),
            ("AB", "ab"),
            ("ABC", "abc"),
            ("AbC", "ab_c"),
            ("AbCd", "ab_cd"),
        ]

        for input_str, expected in test_cases:
            result = UniversalComparator._camel_to_snake(input_str)
            assert result == expected, f"Failed for {input_str}: expected {expected}, got {result}"

    def test_deep_compare_normalized_none_equivalence_edge_cases(self):
        """Test _deep_compare_normalized with various None equivalence scenarios."""
        # Test None vs empty string
        matches, error = UniversalComparator._deep_compare_normalized(None, "")
        assert matches is True
        assert error == ""

        # Test empty string vs None
        matches, error = UniversalComparator._deep_compare_normalized("", None)
        assert matches is True
        assert error == ""

        # Test None vs empty list
        matches, error = UniversalComparator._deep_compare_normalized(None, [])
        assert matches is True
        assert error == ""

        # Test empty list vs None
        matches, error = UniversalComparator._deep_compare_normalized([], None)
        assert matches is True
        assert error == ""

        # Test None vs empty dict
        matches, error = UniversalComparator._deep_compare_normalized(None, {})
        assert matches is True
        assert error == ""

        # Test empty dict vs None
        matches, error = UniversalComparator._deep_compare_normalized({}, None)
        assert matches is True
        assert error == ""

    def test_deep_compare_normalized_namespaces_special_handling(self):
        """Test _deep_compare_normalized special handling for namespaces."""
        # Test namespaces at root level - should pass when both are non-empty and match (order independent)
        obj1 = ["namespace1", "namespace2"]
        obj2 = ["namespace2", "namespace1"]  # Different order

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "namespaces")
        assert matches is True
        assert error == ""

        # Test namespaces with duplicates - should pass (sets remove duplicates)
        obj1 = ["namespace1", "namespace2", "namespace1"]
        obj2 = ["namespace2", "namespace1"]

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "namespaces")
        assert matches is True
        assert error == ""

        # Test namespaces mismatch - should fail when both are non-empty but different
        obj1 = ["namespace1", "namespace2"]
        obj2 = ["namespace3", "namespace4"]

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "namespaces")
        assert matches is False
        assert "namespaces: mismatch" in error

        # Test empty vs non-empty namespaces - should pass (skip validation)
        obj1 = []
        obj2 = ["namespace1", "namespace2"]

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "namespaces")
        assert matches is True
        assert error == ""

        # Test None vs non-empty namespaces - should pass (skip validation)
        obj1 = None
        obj2 = ["namespace1", "namespace2"]

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "namespaces")
        assert matches is True
        assert error == ""

    def test_deep_compare_normalized_dict_namespaces_special_handling(self):
        """Test _deep_compare_normalized special handling for namespaces in dicts."""
        obj1 = {"name": "test", "namespaces": ["namespace1", "namespace2"]}
        obj2 = {
            "name": "test",
            "namespaces": ["namespace2", "namespace1"],  # Different order
        }

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2)
        assert matches is True
        assert error == ""

    def test_deep_compare_normalized_list_length_mismatch(self):
        """Test _deep_compare_normalized with list length mismatch (non-namespaces)."""
        obj1 = ["item1", "item2"]
        obj2 = ["item1", "item2", "item3"]

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "items")
        assert matches is False
        assert "items: list length mismatch (2 vs 3)" in error

    def test_deep_compare_normalized_list_item_mismatch(self):
        """Test _deep_compare_normalized with list item mismatch."""
        obj1 = ["item1", "item2"]
        obj2 = ["item1", "different_item"]

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "items")
        assert matches is False
        assert "items[1]: value mismatch" in error

    def test_deep_compare_normalized_type_mismatch(self):
        """Test _deep_compare_normalized with type mismatch."""
        obj1 = "string_value"
        obj2 = 123

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2, "field")
        assert matches is False
        assert "field: type mismatch (str vs int)" in error

    def test_deep_compare_normalized_nested_dict_missing_key(self):
        """Test _deep_compare_normalized with missing keys in nested dicts."""
        obj1 = {"config": {"field1": "value1", "field2": "value2"}}
        obj2 = {
            "config": {
                "field1": "value1"
                # field2 is missing
            }
        }

        matches, error = UniversalComparator._deep_compare_normalized(obj1, obj2)
        assert matches is False
        assert "config.field2: type mismatch" in error

    def test_normalize_field_names_primitive_types(self):
        """Test normalize_field_names with primitive types."""
        # Test with string
        result = UniversalComparator.normalize_field_names("test_string")
        assert result == "test_string"

        # Test with number
        result = UniversalComparator.normalize_field_names(123)
        assert result == 123

        # Test with boolean
        result = UniversalComparator.normalize_field_names(True)
        assert result is True

        # Test with None
        result = UniversalComparator.normalize_field_names(None)
        assert result is None

    def test_normalize_field_names_mixed_list(self):
        """Test normalize_field_names with mixed content list."""
        data = [{"camelCase": "value1"}, "string_item", 123, {"anotherCamelCase": {"nestedCamelCase": "nested_value"}}]

        result = UniversalComparator.normalize_field_names(data)

        expected = [
            {"camel_case": "value1"},
            "string_item",
            123,
            {"another_camel_case": {"nested_camel_case": "nested_value"}},
        ]

        assert result == expected


class TestValidateExistingMemoryStrategiesEdgeCases:
    """Test edge cases for validate_existing_memory_strategies function."""

    def test_validate_with_mixed_strategy_types(self):
        """Test validation with mixed typed and dict strategies."""
        memory_strategies = [
            {
                "type": "CUSTOM",
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Extract insights", "modelId": "claude-3-sonnet"},
                        "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                    }
                },
            }
        ]

        # Mix of typed strategy and dict
        extraction_config = ExtractionConfig(append_to_prompt="Extract insights", model_id="claude-3-sonnet")
        consolidation_config = ConsolidationConfig(append_to_prompt="Consolidate insights", model_id="claude-3-haiku")

        requested_strategies = [
            CustomSemanticStrategy(
                name="CustomStrategy",
                description="Test custom strategy",
                extraction_config=extraction_config,
                consolidation_config=consolidation_config,
                namespaces=["custom/{actorId}"],
            )
        ]

        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_with_custom_summary_strategy(self):
        """Test validation with CustomSummaryStrategy."""
        memory_strategies = [
            {
                "type": "CUSTOM",
                "name": "CustomSummaryStrategy",
                "description": "Test custom summary strategy",
                "namespaces": ["summary/{actorId}"],
                "configuration": {
                    "summaryOverride": {
                        "consolidation": {"appendToPrompt": "Consolidate summaries", "modelId": "claude-3-haiku"}
                    }
                },
            }
        ]

        consolidation_config = ConsolidationConfig(append_to_prompt="Consolidate summaries", model_id="claude-3-haiku")

        requested_strategies = [
            CustomSummaryStrategy(
                name="CustomSummaryStrategy",
                description="Test custom summary strategy",
                consolidation_config=consolidation_config,
                namespaces=["summary/{actorId}"],
            )
        ]

        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_with_custom_user_preference_strategy(self):
        """Test validation with CustomUserPreferenceStrategy."""
        memory_strategies = [
            {
                "type": "CUSTOM",
                "name": "CustomUserPrefStrategy",
                "description": "Test custom user preference strategy",
                "namespaces": ["preferences/{actorId}"],
                "configuration": {
                    "userPreferenceOverride": {
                        "extraction": {"appendToPrompt": "Extract preferences", "modelId": "claude-3-sonnet"},
                        "consolidation": {"appendToPrompt": "Consolidate preferences", "modelId": "claude-3-haiku"},
                    }
                },
            }
        ]

        extraction_config = ExtractionConfig(append_to_prompt="Extract preferences", model_id="claude-3-sonnet")
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Consolidate preferences", model_id="claude-3-haiku"
        )

        requested_strategies = [
            CustomUserPreferenceStrategy(
                name="CustomUserPrefStrategy",
                description="Test custom user preference strategy",
                extraction_config=extraction_config,
                consolidation_config=consolidation_config,
                namespaces=["preferences/{actorId}"],
            )
        ]

        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_complex_mismatch_error_message(self):
        """Test validation with complex mismatch produces detailed error message."""
        memory_strategies = [
            {
                "type": "CUSTOM",
                "name": "CustomStrategy",
                "description": "Existing description",
                "namespaces": ["existing/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Existing extraction prompt", "modelId": "existing-model"},
                        "consolidation": {
                            "appendToPrompt": "Existing consolidation prompt",
                            "modelId": "existing-consolidation-model",
                        },
                    }
                },
            }
        ]

        extraction_config = ExtractionConfig(
            append_to_prompt="Different extraction prompt",  # Different
            model_id="existing-model",
        )
        consolidation_config = ConsolidationConfig(
            append_to_prompt="Existing consolidation prompt", model_id="existing-consolidation-model"
        )

        requested_strategies = [
            CustomSemanticStrategy(
                name="CustomStrategy",
                description="Existing description",
                extraction_config=extraction_config,
                consolidation_config=consolidation_config,
                namespaces=["existing/{actorId}"],
            )
        ]

        with pytest.raises(ValueError) as exc_info:
            validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

        error_message = str(exc_info.value)
        assert "Strategy mismatch for memory 'TestMemory'" in error_message
        assert "Cannot use existing memory with different strategy configuration" in error_message

    def test_validate_logging_with_multiple_strategies(self):
        """Test that validation logs success message with multiple strategies."""
        memory_strategies = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test semantic strategy",
                "namespaces": ["semantic/{actorId}"],
            },
            {
                "type": "SUMMARIZATION",
                "name": "SummaryStrategy",
                "description": "Test summary strategy",
                "namespaces": ["summary/{actorId}"],
            },
        ]

        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test semantic strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            },
            {
                "summaryMemoryStrategy": {
                    "name": "SummaryStrategy",
                    "description": "Test summary strategy",
                    "namespaces": ["summary/{actorId}"],
                }
            },
        ]

        with patch("bedrock_agentcore_starter_toolkit.operations.memory.strategy_validator.logger") as mock_logger:
            validate_existing_memory_strategies(memory_strategies, requested_strategies, "MultiStrategyMemory")

            # Should log success message
            success_logged = False
            for call in mock_logger.info.call_args_list:
                if len(call[0]) >= 2 and "Universal strategy validation passed" in call[0][0]:
                    assert "MultiStrategyMemory" in call[0][1]
                    assert "SEMANTIC, SUMMARIZATION" in call[0][2] or "SUMMARIZATION, SEMANTIC" in call[0][2]
                    success_logged = True
                    break

            assert success_logged, "Success message with strategy types was not logged"


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases across the module."""

    def test_deep_compare_with_complex_nested_structure(self):
        """Test deep comparison with complex nested structures."""
        dict1 = {
            "level1": {
                "level2": {
                    "level3": {
                        "camelCaseField": "value1",
                        "anotherField": ["item1", "item2"],
                        "nestedObject": {"deepField": "deepValue"},
                    }
                }
            }
        }

        dict2 = {
            "level1": {
                "level2": {
                    "level3": {
                        "camel_case_field": "value1",  # snake_case equivalent
                        "another_field": ["item1", "item2"],
                        "nested_object": {"deep_field": "deepValue"},
                    }
                }
            }
        }

        matches, error = UniversalComparator.deep_compare(dict1, dict2)
        assert matches is True
        assert error == ""

    def test_deep_compare_with_complex_mismatch(self):
        """Test deep comparison with complex mismatch provides detailed path."""
        dict1 = {"level1": {"level2": {"level3": {"field": "value1"}}}}

        dict2 = {
            "level1": {
                "level2": {
                    "level3": {
                        "field": "value2"  # Different value
                    }
                }
            }
        }

        matches, error = UniversalComparator.deep_compare(dict1, dict2)
        assert matches is False
        assert "level1.level2.level3.field: value mismatch" in error
        assert "value1" in error
        assert "value2" in error

    def test_normalize_strategy_with_memoryStrategyType_field(self):
        """Test normalize_strategy with memoryStrategyType field instead of type."""
        strategy = {
            "memoryStrategyType": "SEMANTIC",
            "name": "TestStrategy",
            "description": "Test description",
            "namespaces": ["test/{actorId}"],
        }

        normalized = StrategyComparator.normalize_strategy(strategy)

        assert normalized["type"] == "SEMANTIC"
        assert normalized["name"] == "TestStrategy"
        assert normalized["description"] == "Test description"
        assert normalized["namespaces"] == ["test/{actorId}"]

    def test_normalize_strategy_with_empty_configuration(self):
        """Test normalize_strategy with empty configuration."""
        strategy = {
            "type": "CUSTOM",
            "name": "TestStrategy",
            "description": "Test description",
            "namespaces": ["test/{actorId}"],
            "configuration": {},
        }

        normalized = StrategyComparator.normalize_strategy(strategy)

        assert normalized["type"] == "CUSTOM"
        assert normalized["name"] == "TestStrategy"
        assert "configuration" not in normalized or not normalized["configuration"]

    def test_transform_memory_configuration_only_extraction(self):
        """Test _transform_memory_configuration with only extraction config."""
        config = {
            "type": "SEMANTIC_OVERRIDE",
            "extraction": {
                "customExtractionConfiguration": {
                    "semanticOverride": {"appendToPrompt": "Extract only", "modelId": "extraction-model"}
                }
            },
            # No consolidation
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        expected = {
            "semanticOverride": {"extraction": {"appendToPrompt": "Extract only", "modelId": "extraction-model"}}
        }

        assert result == expected

    def test_transform_memory_configuration_only_consolidation(self):
        """Test _transform_memory_configuration with only consolidation config."""
        config = {
            "type": "SUMMARY_OVERRIDE",
            "consolidation": {
                "customConsolidationConfiguration": {
                    "summaryOverride": {"appendToPrompt": "Consolidate only", "modelId": "consolidation-model"}
                }
            },
            # No extraction
        }

        result = StrategyComparator._transform_memory_configuration(config, "CUSTOM")

        expected = {
            "summaryOverride": {
                "consolidation": {"appendToPrompt": "Consolidate only", "modelId": "consolidation-model"}
            }
        }

        assert result == expected


class TestStrategyComparator:
    """Test cases for StrategyComparator class."""

    def test_normalize_strategy_memory_semantic(self):
        """Test normalizing semantic strategy from memory response."""
        strategy = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test semantic strategy",
            "namespaces": ["semantic/{actorId}"],
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
            "namespaces": ["semantic/{actorId}"],
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
                    "extraction": {"appendToPrompt": "Extract insights", "modelId": "claude-3-sonnet"},
                    "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                }
            },
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
                "namespaces": ["semantic/{actorId}"],
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
                        "extraction": {"appendToPrompt": "Extract insights", "modelId": "claude-3-sonnet"},
                        "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                    }
                },
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
        existing = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            }
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is True
        assert error == ""

    def test_compare_strategies_name_mismatch(self):
        """Test comparing strategies with name mismatch."""
        existing = [
            {
                "type": "SEMANTIC",
                "name": "ExistingStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "RequestedStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            }
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is False
        assert "name: value mismatch" in error
        assert "ExistingStrategy" in error
        assert "RequestedStrategy" in error

    def test_compare_strategies_description_mismatch(self):
        """Test comparing strategies with description mismatch."""
        existing = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Existing description",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Requested description",
                    "namespaces": ["semantic/{actorId}"],
                }
            }
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is False
        assert "description: value mismatch" in error

    def test_compare_strategies_namespaces_mismatch(self):
        """Test comparing strategies with namespaces mismatch - should fail when both are non-empty."""
        existing = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["different/{actorId}"],
                }
            }
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is False  # Should fail when both namespaces are non-empty but different
        assert "namespaces: mismatch" in error

    def test_compare_strategies_namespaces_skip_validation(self):
        """Test comparing strategies with namespaces - should skip validation when one is empty."""
        existing = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": [],  # Empty namespaces
            }
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["different/{actorId}"],  # Non-empty namespaces
                }
            }
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is True  # Should pass when one namespace is empty
        assert error == ""

    def test_compare_strategies_custom_extraction_mismatch(self):
        """Test comparing custom strategies with extraction config mismatch."""
        existing = [
            {
                "type": "CUSTOM",
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Existing prompt", "modelId": "claude-3-sonnet"},
                        "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                    }
                },
            }
        ]

        requested = [
            {
                "customMemoryStrategy": {
                    "name": "CustomStrategy",
                    "description": "Test custom strategy",
                    "namespaces": ["custom/{actorId}"],
                    "configuration": {
                        "semanticOverride": {
                            "extraction": {"appendToPrompt": "Requested prompt", "modelId": "claude-3-sonnet"},
                            "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                        }
                    },
                }
            }
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is False
        assert "append_to_prompt: value mismatch" in error

    def test_compare_strategies_count_mismatch(self):
        """Test comparing strategies with different counts."""
        existing = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            },
            {"summaryMemoryStrategy": {"name": "SummaryStrategy", "description": "Test summary strategy"}},
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
        existing = [
            {"type": "SEMANTIC", "name": "SemanticStrategy", "description": None, "namespaces": ["semantic/{actorId}"]}
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "namespaces": ["semantic/{actorId}"],
                    # No description field
                }
            }
        ]

        matches, error = StrategyComparator.compare_strategies(existing, requested)

        assert matches is True
        assert error == ""

    def test_compare_strategies_namespaces_order_independent(self):
        """Test that namespace order doesn't matter."""
        existing = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}", "semantic/{sessionId}"],
            }
        ]

        requested = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{sessionId}", "semantic/{actorId}"],  # Different order
                }
            }
        ]

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
            "config": {"field": None},
        }

        requested = {"type": "CUSTOM", "name": "CustomStrategy", "description": "Test", "namespaces": [], "config": {}}

        matches, error = UniversalComparator.deep_compare(existing, requested)

        assert matches is True
        assert error == ""


class TestValidateExistingMemoryStrategies:
    """Test cases for validate_existing_memory_strategies function."""

    def test_validate_matching_strategies(self):
        """Test validation with matching strategies."""
        memory_strategies = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            }
        ]

        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_mismatched_strategies(self):
        """Test validation with mismatched strategies."""
        memory_strategies = [
            {
                "type": "SEMANTIC",
                "name": "ExistingStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "RequestedStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            }
        ]

        with pytest.raises(ValueError, match="Strategy mismatch"):
            validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_custom_strategies_matching(self):
        """Test validation with matching custom strategies."""
        memory_strategies = [
            {
                "type": "CUSTOM",
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Extract insights", "modelId": "claude-3-sonnet"},
                        "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                    }
                },
            }
        ]

        requested_strategies = [
            {
                "customMemoryStrategy": {
                    "name": "CustomStrategy",
                    "description": "Test custom strategy",
                    "namespaces": ["custom/{actorId}"],
                    "configuration": {
                        "semanticOverride": {
                            "extraction": {"appendToPrompt": "Extract insights", "modelId": "claude-3-sonnet"},
                            "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                        }
                    },
                }
            }
        ]

        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_custom_strategies_extraction_mismatch(self):
        """Test validation with custom strategies having extraction config mismatch."""
        memory_strategies = [
            {
                "type": "CUSTOM",
                "name": "CustomStrategy",
                "description": "Test custom strategy",
                "namespaces": ["custom/{actorId}"],
                "configuration": {
                    "semanticOverride": {
                        "extraction": {"appendToPrompt": "Existing prompt", "modelId": "claude-3-sonnet"},
                        "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                    }
                },
            }
        ]

        requested_strategies = [
            {
                "customMemoryStrategy": {
                    "name": "CustomStrategy",
                    "description": "Test custom strategy",
                    "namespaces": ["custom/{actorId}"],
                    "configuration": {
                        "semanticOverride": {
                            "extraction": {"appendToPrompt": "Requested prompt", "modelId": "claude-3-sonnet"},
                            "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "claude-3-haiku"},
                        }
                    },
                }
            }
        ]

        with pytest.raises(ValueError, match="append_to_prompt: value mismatch"):
            validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_multiple_strategies_matching(self):
        """Test validation with multiple matching strategies."""
        memory_strategies = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test semantic strategy",
                "namespaces": ["semantic/{actorId}"],
            },
            {
                "type": "SUMMARIZATION",
                "name": "SummaryStrategy",
                "description": "Test summary strategy",
                "namespaces": ["summary/{actorId}"],
            },
        ]

        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test semantic strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            },
            {
                "summaryMemoryStrategy": {
                    "name": "SummaryStrategy",
                    "description": "Test summary strategy",
                    "namespaces": ["summary/{actorId}"],
                }
            },
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
                "namespaces": ["summary/{actorId}"],
            },
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test semantic strategy",
                "namespaces": ["semantic/{actorId}"],
            },
        ]

        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test semantic strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            },
            {
                "summaryMemoryStrategy": {
                    "name": "SummaryStrategy",
                    "description": "Test summary strategy",
                    "namespaces": ["summary/{actorId}"],
                }
            },
        ]

        # Should not raise any exception (order shouldn't matter)
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_with_logging(self):
        """Test that successful validation logs appropriate message."""
        memory_strategies = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested_strategies = [
            {
                "semanticMemoryStrategy": {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            }
        ]

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
        requested_strategies = [
            {"semanticMemoryStrategy": {"name": "SemanticStrategy", "description": "Test strategy"}}
        ]

        # Mock the normalize_strategy to raise an exception for the first call only
        side_effects = [
            Exception("Normalization error"),
            StrategyComparator.normalize_strategy(requested_strategies[0]),
        ]
        with patch.object(StrategyComparator, "normalize_strategy", side_effect=side_effects):
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
        memory_strategies = [
            {
                "type": "USER_PREFERENCE",
                "name": "UserPrefStrategy",
                "description": "Test user preference strategy",
                "namespaces": ["preferences/{actorId}"],
            }
        ]

        requested_strategies = [
            {
                "userPreferenceMemoryStrategy": {
                    "name": "UserPrefStrategy",
                    "description": "Test user preference strategy",
                    "namespaces": ["preferences/{actorId}"],
                }
            }
        ]

        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_validate_strategy_enum_values(self):
        """Test validation with StrategyType enum values."""
        memory_strategies = [
            {
                "type": "SEMANTIC",
                "name": "SemanticStrategy",
                "description": "Test strategy",
                "namespaces": ["semantic/{actorId}"],
            }
        ]

        requested_strategies = [
            {
                StrategyType.SEMANTIC.value: {
                    "name": "SemanticStrategy",
                    "description": "Test strategy",
                    "namespaces": ["semantic/{actorId}"],
                }
            }
        ]

        # Should not raise any exception
        validate_existing_memory_strategies(memory_strategies, requested_strategies, "TestMemory")

    def test_normalize_strategy_missing_namespaces(self):
        """Test normalizing strategy without namespaces field."""
        strategy = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
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
            "namespaces": ["custom/{actorId}"],
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
        data = {"appendToPrompt": "test prompt", "modelId": "test-model", "simpleField": "value"}

        normalized = UniversalComparator.normalize_field_names(data)

        assert normalized["append_to_prompt"] == "test prompt"
        assert normalized["model_id"] == "test-model"
        assert normalized["simple_field"] == "value"

    def test_normalize_field_names_nested_dict(self):
        """Test field name normalization for nested dictionary."""
        data = {"topLevel": {"nestedField": "nested_value", "anotherNested": {"deepField": "deep_value"}}}

        normalized = UniversalComparator.normalize_field_names(data)

        assert normalized["top_level"]["nested_field"] == "nested_value"
        assert normalized["top_level"]["another_nested"]["deep_field"] == "deep_value"

    def test_normalize_field_names_with_lists(self):
        """Test field name normalization with lists."""
        data = {"listField": [{"itemField": "value1"}, {"itemField": "value2"}]}

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
            "new_future_field": "existing_value",  # Simulated future field
        }

        requested = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
            "new_future_field": "existing_value",  # Same value
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
            "new_future_field": "existing_value",
        }

        requested = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
            "new_future_field": "different_value",  # Different value
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
            "new_future_field": "existing_value",
        }

        requested = {
            "type": "SEMANTIC",
            "name": "SemanticStrategy",
            "description": "Test strategy",
            "namespaces": ["semantic/{actorId}"],
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
            "config": {"nested": {"field1": "value1", "field2": "value2"}},
        }

        requested = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "config": {"nested": {"field1": "value1", "field2": "value2"}},
        }

        matches, error = UniversalComparator.deep_compare(existing, requested)

        assert matches is True
        assert error == ""

    def test_universal_nested_config_mismatch(self):
        """Test that universal comparison detects nested mismatches."""
        existing = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "config": {"nested": {"field1": "existing_value", "field2": "value2"}},
        }

        requested = {
            "type": "CUSTOM",
            "name": "CustomStrategy",
            "config": {"nested": {"field1": "different_value", "field2": "value2"}},
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
                "namespaces": ["newtype/{actorId}"],
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
                            "newExtractionField": "new_value",  # Future camelCase field
                        }
                    }
                },
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
                "namespaces": ["semantic/{actorId}"],
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
                "namespaces": ["custom/{actorId}"],
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
                "anotherNewField": {"nested": "data"},
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
