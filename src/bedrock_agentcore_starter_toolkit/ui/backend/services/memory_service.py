"""Memory service for retrieving and formatting memory information."""

import logging
from typing import Dict, List, Optional

from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing AgentCore Memory operations."""

    def __init__(self, region: Optional[str] = None):
        """Initialize MemoryService.

        Args:
            region: AWS region for memory operations
        """
        self.region = region
        self._memory_manager: Optional[MemoryManager] = None

    def _get_memory_manager(self) -> MemoryManager:
        """Get or create MemoryManager instance.

        Returns:
            MemoryManager instance

        Raises:
            ValueError: If region is not configured
        """
        if not self.region:
            raise ValueError("Region not configured for memory operations")

        if not self._memory_manager:
            self._memory_manager = MemoryManager(region_name=self.region)

        return self._memory_manager

    def get_memory_details(self, memory_id: str) -> Dict:
        """Get memory resource details.

        Args:
            memory_id: Memory resource ID

        Returns:
            Dict with memory details including strategies

        Raises:
            Exception: If memory retrieval fails
        """
        try:
            memory_manager = self._get_memory_manager()
            memory = memory_manager.get_memory(memory_id)
            logger.info("Retrieved memory: %s", memory)
            # Extract memory details
            memory_data = dict(memory)

            # Format strategies
            strategies = self._format_strategies(memory_data.get("strategies", []))

            # Determine memory type
            memory_type = self._determine_memory_type(strategies)

            return {
                "memory_id": memory_data.get("id", memory_id),
                "name": memory_data.get("name", ""),
                "status": memory_data.get("status", "UNKNOWN"),
                "event_expiry_days": memory_data.get("eventExpiryDuration", 90),
                "memory_type": memory_type,
                "strategies": strategies,
            }

        except Exception as e:
            logger.error("Failed to get memory details: %s", e)
            raise

    def _format_strategies(self, strategies: List) -> List[Dict]:
        """Format memory strategies for frontend consumption.

        Args:
            strategies: List of strategy objects

        Returns:
            List of formatted strategy dicts
        """
        formatted = []

        for strategy in strategies:
            # Handle both dict and object formats
            if hasattr(strategy, "get_dict"):
                strategy_data = strategy.get_dict()
            elif isinstance(strategy, dict):
                strategy_data = strategy
            else:
                strategy_data = dict(strategy)

            formatted_strategy = {
                "strategy_id": strategy_data.get("id", ""),
                "name": strategy_data.get("name", ""),
                "type": self._get_strategy_type(strategy_data),
                "status": strategy_data.get("status", "UNKNOWN"),
                "description": strategy_data.get("description"),
                "namespaces": strategy_data.get("namespaces"),
                "configuration": self._extract_configuration(strategy_data),
            }

            formatted.append(formatted_strategy)

        return formatted

    def _get_strategy_type(self, strategy_data: Dict) -> str:
        """Extract strategy type from strategy data.

        Args:
            strategy_data: Strategy data dict

        Returns:
            Strategy type string (semantic, summary, user_preference, custom)
        """
        # Check for type field directly
        if "type" in strategy_data:
            strategy_type = strategy_data["type"]
            # Map API types to frontend types
            type_mapping = {
                "SEMANTIC": "semantic",
                "SUMMARIZATION": "summary",
                "USER_PREFERENCE": "user_preference",
                "CUSTOM": "custom",
            }
            return type_mapping.get(strategy_type, strategy_type.lower())

        # Fallback: infer from configuration structure
        config = strategy_data.get("configuration", {})
        if "semanticConfiguration" in config:
            return "semantic"
        elif "summarizationConfiguration" in config:
            return "summary"
        elif "userPreferenceConfiguration" in config:
            return "user_preference"
        elif "customConfiguration" in config:
            return "custom"

        return "unknown"

    def _extract_configuration(self, strategy_data: Dict) -> Optional[Dict]:
        """Extract configuration details from strategy.

        Args:
            strategy_data: Strategy data dict

        Returns:
            Configuration dict or None
        """
        config = strategy_data.get("configuration")
        if not config:
            return None

        # For custom strategies, extract extraction and consolidation configs
        if "customConfiguration" in config:
            custom_config = config["customConfiguration"]
            return {
                "extraction": custom_config.get("extraction"),
                "consolidation": custom_config.get("consolidation"),
            }

        return config

    def _determine_memory_type(self, strategies: List[Dict]) -> str:
        """Determine memory type based on configured strategies.

        Args:
            strategies: List of formatted strategy dicts

        Returns:
            "short-term" or "short-term-and-long-term"
        """
        # Check if any long-term strategies are present
        long_term_types = {"semantic", "user_preference"}

        for strategy in strategies:
            if strategy["type"] in long_term_types:
                return "short-term-and-long-term"

        return "short-term"
