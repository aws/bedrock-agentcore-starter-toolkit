"""Strategy validation utilities for memory operations."""

import logging
import re
from typing import Any, Dict, List, Union

from .constants import StrategyType
from .models import convert_strategies_to_dicts
from .models.strategies import BaseStrategy

logger = logging.getLogger(__name__)


class UniversalComparator:
    """Universal comparison utility for deep strategy validation."""

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        # Handle sequences of uppercase letters (like XMLHttpRequest -> xml_http_request)
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    @staticmethod
    def normalize_field_names(data: Any) -> Any:
        """Recursively normalize field names from camelCase to snake_case."""
        if isinstance(data, dict):
            normalized = {}
            for key, value in data.items():
                normalized_key = UniversalComparator._camel_to_snake(key)
                normalized[normalized_key] = UniversalComparator.normalize_field_names(value)
            return normalized
        elif isinstance(data, list):
            return [UniversalComparator.normalize_field_names(item) for item in data]
        else:
            return data

    @staticmethod
    def deep_compare(dict1: Dict[str, Any], dict2: Dict[str, Any], path: str = "") -> tuple[bool, str]:
        """Deep compare two dictionaries with detailed error reporting."""
        # Normalize both dictionaries
        norm1 = UniversalComparator.normalize_field_names(dict1)
        norm2 = UniversalComparator.normalize_field_names(dict2)

        return UniversalComparator._deep_compare_normalized(norm1, norm2, path)

    @staticmethod
    def _deep_compare_normalized(obj1: Any, obj2: Any, path: str = "") -> tuple[bool, str]:
        """Compare normalized objects recursively."""
        # Special handling for namespaces - check this first before general type/None handling
        if path == "namespaces":
            # Skip validation if either is None/empty or both are None
            # This allows server-side namespace assignment when not provided by user
            if not obj1 or not obj2:
                return True, ""
            # Only validate if both are non-empty lists
            if isinstance(obj1, list) and isinstance(obj2, list):
                set1 = set(obj1) if obj1 else set()
                set2 = set(obj2) if obj2 else set()
                if set1 != set2:
                    return False, f"{path}: mismatch ({sorted(set1)} vs {sorted(set2)})"
                return True, ""
            # If not both lists, fall through to normal comparison

        # Handle None equivalence - treat None and empty values as equivalent
        if obj1 is None and obj2 is None:
            return True, ""
        if obj1 is None and (obj2 == "" or obj2 == [] or obj2 == {}):
            return True, ""
        if obj2 is None and (obj1 == "" or obj1 == [] or obj1 == {}):
            return True, ""

        # Type comparison
        if type(obj1) is not type(obj2):
            return False, f"{path}: type mismatch ({type(obj1).__name__} vs {type(obj2).__name__})"

        if isinstance(obj1, dict):
            # Get all keys from both dictionaries
            all_keys = set(obj1.keys()) | set(obj2.keys())

            for key in all_keys:
                key_path = f"{path}.{key}" if path else key

                val1 = obj1.get(key)
                val2 = obj2.get(key)

                # Special handling for namespaces - only validate when both are non-empty lists
                if key == "namespaces":
                    # Skip validation if either is None/empty or both are None
                    # This allows server-side namespace assignment when not provided by user
                    if not val1 or not val2:
                        continue
                    # Only validate if both are non-empty lists of strings
                    if isinstance(val1, list) and isinstance(val2, list):
                        set1 = set(val1) if val1 else set()
                        set2 = set(val2) if val2 else set()
                        if set1 != set2:
                            return False, f"{key_path}: mismatch ({sorted(set1)} vs {sorted(set2)})"
                    continue

                matches, error = UniversalComparator._deep_compare_normalized(val1, val2, key_path)
                if not matches:
                    return False, error

            return True, ""

        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False, f"{path}: list length mismatch ({len(obj1)} vs {len(obj2)})"

            for i, (item1, item2) in enumerate(zip(obj1, obj2, strict=False)):
                item_path = f"{path}[{i}]" if path else f"[{i}]"
                matches, error = UniversalComparator._deep_compare_normalized(item1, item2, item_path)
                if not matches:
                    return False, error

            return True, ""

        else:
            # Direct value comparison
            if obj1 != obj2:
                return False, f"{path}: value mismatch ('{obj1}' vs '{obj2}')"
            return True, ""


class StrategyComparator:
    """Utility class for comparing memory strategies in detail."""

    @staticmethod
    def normalize_strategy(strategy: Union[Dict[str, Any], Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Normalize a strategy to a standard format with universal field normalization.

        Args:
            strategy: Strategy dictionary (either from memory response or request format)

        Returns:
            Normalized strategy dictionary with snake_case field names
        """
        # Check if this is already a normalized strategy (from memory response)
        if "type" in strategy or "memoryStrategyType" in strategy:
            return StrategyComparator._normalize_memory_strategy(strategy)

        # Otherwise, it's a request format strategy
        return StrategyComparator._normalize_request_strategy(strategy)

    @staticmethod
    def _normalize_memory_strategy(strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a strategy from memory response, including only fields relevant for comparison."""
        # Handle different field name variations
        strategy_type = strategy.get("type", strategy.get("memoryStrategyType"))

        # Only include the core fields that should be compared
        normalized = {
            "type": strategy_type,
            "name": strategy.get("name"),
            "description": strategy.get("description"),
            "namespaces": strategy.get("namespaces", []),
        }

        # Add configuration if present and normalize it
        if "configuration" in strategy and strategy["configuration"]:
            config = strategy["configuration"]
            normalized_config = StrategyComparator._transform_memory_configuration(config, strategy_type)
            normalized["configuration"] = UniversalComparator.normalize_field_names(normalized_config)

        # Don't include any other fields from memory responses (like status, strategyId, etc.)
        # as they are not relevant for strategy comparison

        return normalized

    @staticmethod
    def _transform_memory_configuration(config: Dict[str, Any], strategy_type: str) -> Dict[str, Any]:
        """Transform memory configuration from stored format to match requested format.

        This handles the structural differences between how configurations are stored
        in memory vs how they're provided through typed strategy objects.

        Args:
            config: Configuration from memory response
            strategy_type: Strategy type (e.g., 'CUSTOM', 'SEMANTIC', etc.)

        Returns:
            Transformed configuration matching the requested format
        """
        if not config:
            return config

        # Handle CUSTOM strategy configurations that need transformation
        if strategy_type == "CUSTOM" and config.get("type") in [
            "SEMANTIC_OVERRIDE",
            "USER_PREFERENCE_OVERRIDE",
            "SUMMARY_OVERRIDE",
        ]:
            override_type = config.get("type")
            transformed_config = {}

            # Determine the override key name based on type
            if override_type == "SEMANTIC_OVERRIDE":
                override_key = "semanticOverride"
            elif override_type == "USER_PREFERENCE_OVERRIDE":
                override_key = "userPreferenceOverride"
            elif override_type == "SUMMARY_OVERRIDE":
                override_key = "summaryOverride"
            else:
                # Fallback - return original config
                return config

            transformed_config[override_key] = {}

            # Transform extraction configuration
            if "extraction" in config:
                extraction = config["extraction"]
                if "customExtractionConfiguration" in extraction:
                    custom_extraction = extraction["customExtractionConfiguration"]

                    # Find the override key and extract the actual config
                    for key, value in custom_extraction.items():
                        if key.endswith("Override"):
                            transformed_config[override_key]["extraction"] = value
                            break
                elif "custom_extraction_configuration" in extraction:
                    # Handle snake_case version
                    custom_extraction = extraction["custom_extraction_configuration"]

                    # Find the override key and extract the actual config
                    for key, value in custom_extraction.items():
                        if key.endswith("_override"):
                            transformed_config[override_key]["extraction"] = value
                            break
                else:
                    # Direct extraction config (no wrapper)
                    transformed_config[override_key]["extraction"] = extraction

            # Transform consolidation configuration
            if "consolidation" in config:
                consolidation = config["consolidation"]
                if "customConsolidationConfiguration" in consolidation:
                    custom_consolidation = consolidation["customConsolidationConfiguration"]

                    # Find the override key and extract the actual config
                    for key, value in custom_consolidation.items():
                        if key.endswith("Override"):
                            transformed_config[override_key]["consolidation"] = value
                            break
                elif "custom_consolidation_configuration" in consolidation:
                    # Handle snake_case version
                    custom_consolidation = consolidation["custom_consolidation_configuration"]

                    # Find the override key and extract the actual config
                    for key, value in custom_consolidation.items():
                        if key.endswith("_override"):
                            transformed_config[override_key]["consolidation"] = value
                            break
                else:
                    # Direct consolidation config (no wrapper)
                    transformed_config[override_key]["consolidation"] = consolidation

            # Copy any other fields that don't need transformation
            for key, value in config.items():
                if key not in ["type", "extraction", "consolidation"]:
                    transformed_config[key] = value

            return transformed_config

        # For non-CUSTOM strategies or configurations that don't need transformation, return as-is
        return config

    @staticmethod
    def _normalize_request_strategy(strategy_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a strategy from request format."""
        # Find the strategy type key in the dictionary
        strategy_type = None
        strategy_config = None

        for key, config in strategy_dict.items():
            if key.endswith("MemoryStrategy") or key in [
                StrategyType.SEMANTIC.value,
                StrategyType.SUMMARY.value,
                StrategyType.USER_PREFERENCE.value,
                StrategyType.CUSTOM.value,
            ]:
                strategy_config = config
                # Map strategy keys to standard types using the constants
                if key == "semanticMemoryStrategy" or key == StrategyType.SEMANTIC.value:
                    strategy_type = StrategyType.SEMANTIC.get_memory_strategy()
                elif key == "summaryMemoryStrategy" or key == StrategyType.SUMMARY.value:
                    strategy_type = StrategyType.SUMMARY.get_memory_strategy()
                elif key == "userPreferenceMemoryStrategy" or key == StrategyType.USER_PREFERENCE.value:
                    strategy_type = StrategyType.USER_PREFERENCE.get_memory_strategy()
                elif key == "customMemoryStrategy" or key == StrategyType.CUSTOM.value:
                    strategy_type = StrategyType.CUSTOM.get_memory_strategy()
                elif key.endswith("MemoryStrategy"):
                    # Handle future strategy types following naming convention
                    # e.g., "newTypeMemoryStrategy" -> "NEW_TYPE"
                    type_name = key.replace("MemoryStrategy", "")
                    strategy_type = UniversalComparator._camel_to_snake(type_name).upper()
                break

        if not strategy_config:
            raise ValueError(f"Invalid strategy format: {strategy_dict}")

        normalized = {
            "type": strategy_type,
            "name": strategy_config.get("name"),
            "description": strategy_config.get("description"),
            "namespaces": strategy_config.get("namespaces", []),
        }

        # Add configuration if present and normalize it
        if "configuration" in strategy_config and strategy_config["configuration"]:
            normalized["configuration"] = UniversalComparator.normalize_field_names(strategy_config["configuration"])

        # Normalize any additional fields in the strategy config (but exclude common metadata fields)
        excluded_fields = {"name", "description", "namespaces", "configuration", "status", "strategyId"}
        for key, value in strategy_config.items():
            if key not in excluded_fields:
                normalized_key = UniversalComparator._camel_to_snake(key)
                normalized[normalized_key] = UniversalComparator.normalize_field_names(value)

        return normalized

    @staticmethod
    def compare_strategies(
        existing_strategies: List[Dict[str, Any]], requested_strategies: List[Union[BaseStrategy, Dict[str, Any]]]
    ) -> tuple[bool, str]:
        """Compare existing memory strategies with requested strategies using universal comparison.

        Args:
            existing_strategies: List of strategy dictionaries from memory response
            requested_strategies: List of requested strategy objects or dictionaries

        Returns:
            Tuple of (matches, error_message). If matches is False, error_message contains details.
        """
        # Convert requested strategies to dictionaries for comparison
        requested_dict_strategies = convert_strategies_to_dicts(requested_strategies)

        # Normalize both sets of strategies
        normalized_existing = []
        for strategy in existing_strategies:
            try:
                normalized_existing.append(StrategyComparator.normalize_strategy(strategy))
            except Exception as e:
                logger.warning("Failed to normalize existing strategy: %s, error: %s", strategy, e)
                continue

        normalized_requested = []
        for strategy in requested_dict_strategies:
            try:
                normalized_requested.append(StrategyComparator.normalize_strategy(strategy))
            except Exception as e:
                logger.warning("Failed to normalize requested strategy: %s, error: %s", strategy, e)
                continue

        # Sort both lists by type and name for consistent comparison
        normalized_existing.sort(key=lambda x: (x.get("type", ""), x.get("name", "")))
        normalized_requested.sort(key=lambda x: (x.get("type", ""), x.get("name", "")))

        # Check if counts match
        if len(normalized_existing) != len(normalized_requested):
            existing_types = [s.get("type") for s in normalized_existing]
            requested_types = [s.get("type") for s in normalized_requested]
            return False, (
                f"Strategy count mismatch. "
                f"Existing memory has {len(normalized_existing)} strategies: {existing_types}, "
                f"but {len(normalized_requested)} strategies were requested: {requested_types}."
            )

        # Use universal comparison for each strategy pair
        for i, (existing, requested) in enumerate(zip(normalized_existing, normalized_requested, strict=False)):
            logger.info("Existing %s\nRequested %s", existing, requested)
            matches, error = UniversalComparator.deep_compare(existing, requested)
            if not matches:
                return False, f"Strategy {i + 1} mismatch: {error}"

        return True, ""


def validate_existing_memory_strategies(
    memory_strategies: List[Dict[str, Any]],
    requested_strategies: List[Union[BaseStrategy, Dict[str, Any]]],
    memory_name: str,
) -> None:
    """Validate that existing memory strategies match the requested strategies using universal comparison.

    Args:
        memory_strategies: List of strategy dictionaries from memory response
        requested_strategies: List of requested strategy objects or dictionaries
        memory_name: Memory name for error messages

    Raises:
        ValueError: If the strategies don't match with detailed explanation
    """
    matches, error_message = StrategyComparator.compare_strategies(memory_strategies, requested_strategies)

    if not matches:
        raise ValueError(
            f"Strategy mismatch for memory '{memory_name}'. {error_message} "
            f"Cannot use existing memory with different strategy configuration."
        )

    # Log successful validation
    strategy_types = [s.get("type", s.get("memoryStrategyType", "unknown")) for s in memory_strategies]
    logger.info(
        "Universal strategy validation passed for memory %s. Strategies match: [%s]",
        memory_name,
        ", ".join(strategy_types),
    )
