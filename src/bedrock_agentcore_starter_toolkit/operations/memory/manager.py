"""Memory Manager for AgentCore Memory resources."""

import copy
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError
from rich.console import Console

from .constants import MemoryStatus, MemoryStrategyStatus, OverrideType, StrategyType
from .models import convert_strategies_to_dicts
from .models.Memory import Memory
from .models.MemoryStrategy import MemoryStrategy
from .models.MemorySummary import MemorySummary
from .models.strategies import BaseStrategy
from .strategy_validator import validate_existing_memory_strategies

logger = logging.getLogger(__name__)


class MemoryManager:
    """A high-level client for managing the lifecycle of AgentCore Memory resources.

    This class handles all CONTROL PLANE CRUD operations.
    """

    def __init__(
        self,
        region_name: Optional[str] = None,
        boto3_session: Optional[boto3.Session] = None,
        boto_client_config: Optional[BotocoreConfig] = None,
        console: Optional[Console] = None,
    ):
        """Initialize MemoryManager with AWS region.

        Args:
            region_name: AWS region for the bedrock-agentcore-control client. If not provided,
                   will use the region from boto3_session or default session.
            boto3_session: Optional boto3 Session to use. If provided and region_name
                          parameter is also specified, validation will ensure they match.
            boto_client_config: Optional boto3 client configuration. If provided, will be
                              merged with default configuration including user agent.
            console: Optional Rich console instance for output (creates new if not provided)

        Raises:
            ValueError: If region_name parameter conflicts with boto3_session region.
        """
        session = boto3_session or boto3.Session()
        session_region = session.region_name
        self.console = console or Console()

        # Validate region consistency if both are provided
        if region_name and boto3_session and session_region and region_name != session_region:
            raise ValueError(
                f"Region mismatch: provided region_name '{region_name}' does not match "
                f"boto3_session region '{session_region}'. Please ensure both "
                f"parameters specify the same region or omit the region_name parameter "
                f"to use the session's region."
            )

        # Configure boto3 client with merged configuration
        if boto_client_config:
            existing_user_agent = getattr(boto_client_config, "user_agent_extra", None)
            if existing_user_agent:
                new_user_agent = f"{existing_user_agent} bedrock-agentcore-starter-toolkit"
            else:
                new_user_agent = "bedrock-agentcore-starter-toolkit"
            client_config = boto_client_config.merge(BotocoreConfig(user_agent_extra=new_user_agent))
        else:
            client_config = BotocoreConfig(user_agent_extra="bedrock-agentcore-starter-toolkit")

        self.region_name = region_name
        self._control_plane_client = session.client(
            "bedrock-agentcore-control", region_name=self.region_name, config=client_config
        )

        # AgentCore Memory control plane methods
        self._ALLOWED_CONTROL_PLANE_METHODS = {
            "create_memory",
            "list_memories",
            "update_memory",
            "delete_memory",
        }
        logger.info("✅ MemoryManager initialized for region: %s", region_name)

    def __getattr__(self, name: str):
        """Dynamically forward method calls to the appropriate boto3 client.

        This method enables access to all control_plane boto3 client methods without explicitly
        defining them. Methods are looked up in the following order:
        _control_plane_client (bedrock-agentcore-control) - for control plane operations

        Args:
            name: The method name being accessed

        Returns:
            A callable method from the control_plane boto3 client

        Raises:
            AttributeError: If the method doesn't exist on control_plane_client

        Example:
            # Access any boto3 method directly
            manager = MemoryManager(region_name="us-east-1")

            # These calls are forwarded to the appropriate boto3 functions
            response = manager.list_memories()
            memory = manager.get_memory(memoryId="mem-123")
        """
        if name in self._ALLOWED_CONTROL_PLANE_METHODS and hasattr(self._control_plane_client, name):
            method = getattr(self._control_plane_client, name)
            logger.debug("Forwarding method '%s' to control_plane_client", name)
            return method

        # Method not found on client
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'. "
            f"Method not found on control_plane_client. "
            f"Available methods can be found in the boto3 documentation for "
            f"'bedrock-agentcore-control' services."
        )

    def _validate_namespace(self, namespace: str) -> bool:
        """Validate namespace format - basic check only."""
        # Only check for template variables in namespace definition
        if "{" in namespace and not (
            "{actorId}" in namespace or "{sessionId}" in namespace or "{strategyId}" in namespace
        ):
            logger.warning("Namespace with templates should contain valid variables: %s", namespace)

        return True

    def _validate_strategy_config(self, strategy: Dict[str, Any], strategy_type: str) -> None:
        """Validate strategy configuration parameters."""
        strategy_config = strategy[strategy_type]

        namespaces = strategy_config.get("namespaces", [])
        for namespace in namespaces:
            self._validate_namespace(namespace)

    def _wrap_configuration(
        self, config: Dict[str, Any], strategy_type: str, override_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Wrap configuration based on strategy type using new enum methods."""
        wrapped_config = {}

        if "extraction" in config:
            extraction = config["extraction"]

            if any(key in extraction for key in ["triggerEveryNMessages", "historicalContextWindowSize"]):
                if strategy_type == "SEMANTIC":
                    wrapper_key = StrategyType.SEMANTIC.extraction_wrapper_key()
                    if wrapper_key:
                        wrapped_config["extraction"] = {wrapper_key: extraction}
                elif strategy_type == "USER_PREFERENCE":
                    wrapper_key = StrategyType.USER_PREFERENCE.extraction_wrapper_key()
                    if wrapper_key:
                        wrapped_config["extraction"] = {wrapper_key: extraction}
                elif strategy_type == "CUSTOM" and override_type:
                    override_enum = OverrideType(override_type)
                    wrapper_key = override_enum.extraction_wrapper_key()
                    if wrapper_key and override_type in ["SEMANTIC_OVERRIDE", "USER_PREFERENCE_OVERRIDE"]:
                        wrapped_config["extraction"] = {"customExtractionConfiguration": {wrapper_key: extraction}}
            else:
                wrapped_config["extraction"] = extraction

        if "consolidation" in config:
            consolidation = config["consolidation"]

            raw_keys = ["triggerEveryNMessages", "appendToPrompt", "modelId"]
            if any(key in consolidation for key in raw_keys):
                if strategy_type == "SUMMARIZATION":
                    wrapper_key = StrategyType.SUMMARY.consolidation_wrapper_key()
                    if wrapper_key and "triggerEveryNMessages" in consolidation:
                        wrapped_config["consolidation"] = {
                            wrapper_key: {"triggerEveryNMessages": consolidation["triggerEveryNMessages"]}
                        }
                elif strategy_type == "CUSTOM" and override_type:
                    override_enum = OverrideType(override_type)
                    wrapper_key = override_enum.consolidation_wrapper_key()
                    if wrapper_key:
                        wrapped_config["consolidation"] = {
                            "customConsolidationConfiguration": {wrapper_key: consolidation}
                        }
            else:
                wrapped_config["consolidation"] = consolidation

        return wrapped_config

    def _create_memory(
        self,
        name: str,
        strategies: Optional[List[Dict[str, Any]]] = None,
        description: Optional[str] = None,
        event_expiry_days: int = 90,
        memory_execution_role_arn: Optional[str] = None,
        encryption_key_arn: Optional[str] = None,
    ) -> Memory:
        """Create a memory resource and return the raw response.

        Maps to: bedrock-agentcore-control.create_memory.
        """
        if strategies is None:
            strategies = []

        try:
            params = {
                "name": name,
                "eventExpiryDuration": event_expiry_days,
                "memoryStrategies": strategies,
                "clientToken": str(uuid.uuid4()),
            }

            if description is not None:
                params["description"] = description

            if memory_execution_role_arn is not None:
                params["memoryExecutionRoleArn"] = memory_execution_role_arn

            if encryption_key_arn is not None:
                params["encryptionKeyArn"] = encryption_key_arn

            response = self._control_plane_client.create_memory(**params)

            memory = response["memory"]

            # Handle field name normalization
            memory_id = memory.get("id", memory.get("memoryId", "unknown"))
            logger.info("Created memory: %s", memory_id)
            return Memory(memory)

        except ClientError as e:
            logger.error("Failed to create memory: %s", e)
            raise

    def _create_memory_and_wait(
        self,
        name: str,
        strategies: Optional[List[Dict[str, Any]]],
        description: Optional[str] = None,
        event_expiry_days: int = 90,
        memory_execution_role_arn: Optional[str] = None,
        max_wait: int = 300,
        poll_interval: int = 10,
        encryption_key_arn: Optional[str] = None,
    ) -> Memory:
        """Create a memory and wait for it to become ACTIVE.

        This method creates a memory and polls until it reaches ACTIVE status,
        providing a convenient way to ensure the memory is ready for use.

        Args:
            name: Name for the memory resource
            strategies: List of strategy configurations
            description: Optional description
            event_expiry_days: How long to retain events (default: 90 days)
            memory_execution_role_arn: IAM role ARN for memory execution
            max_wait: Maximum seconds to wait (default: 300)
            poll_interval: Seconds between status checks (default: 10)
            encryption_key_arn: kms key ARN for encryption

        Returns:
            Created memory object in ACTIVE status

        Raises:
            TimeoutError: If memory doesn't become ACTIVE within max_wait
            RuntimeError: If memory creation fails
        """
        # Create the memory
        memory = self._create_memory(
            name=name,
            strategies=strategies,
            description=description,
            event_expiry_days=event_expiry_days,
            memory_execution_role_arn=memory_execution_role_arn,
            encryption_key_arn=encryption_key_arn,
        )

        memory_id = memory.id
        if memory_id is None:
            memory_id = ""
        logger.info("Created memory %s, waiting for ACTIVE status...", memory_id)
        return self._wait_for_memory_active(memory_id, max_wait, poll_interval)

    def create_memory_and_wait(
        self,
        name: str,
        strategies: Optional[List[Union[BaseStrategy, Dict[str, Any]]]] = None,
        description: Optional[str] = None,
        event_expiry_days: int = 90,
        memory_execution_role_arn: Optional[str] = None,
        encryption_key_arn: Optional[str] = None,
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> Memory:
        """Create a memory and wait for it to become ACTIVE - public method.

        Args:
            name: Name for the memory resource
            strategies: List of typed strategy objects or dictionary configurations
            description: Optional description
            event_expiry_days: How long to retain events (default: 90 days)
            memory_execution_role_arn: IAM role ARN for memory execution
            max_wait: Maximum seconds to wait (default: 300)
            poll_interval: Seconds between status checks (default: 10)
            encryption_key_arn: kms key ARN for encryption

        Returns:
            Created memory object in ACTIVE status

        Example:
            from bedrock_agentcore_starter_toolkit.operations.memory.models import (
                SemanticStrategy, CustomSemanticStrategy, ExtractionConfig, ConsolidationConfig
            )

            # Create typed strategies
            semantic = SemanticStrategy(name="MySemanticStrategy")
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

            # Create memory with typed strategies
            memory = manager.create_memory_and_wait(
                name="TypedMemory",
                strategies=[semantic, custom]
            )
        """
        # Convert typed strategies to dicts for internal processing
        dict_strategies = convert_strategies_to_dicts(strategies) if strategies else None

        return self._create_memory_and_wait(
            name=name,
            strategies=dict_strategies,
            description=description,
            event_expiry_days=event_expiry_days,
            memory_execution_role_arn=memory_execution_role_arn,
            encryption_key_arn=encryption_key_arn,
            max_wait=max_wait,
            poll_interval=poll_interval,
        )

    def get_or_create_memory(
        self,
        name: str,
        strategies: Optional[List[Union[BaseStrategy, Dict[str, Any]]]] = None,
        description: Optional[str] = None,
        event_expiry_days: int = 90,
        memory_execution_role_arn: Optional[str] = None,
        encryption_key_arn: Optional[str] = None,
    ) -> Memory:
        """Fetch an existing memory resource or create the memory.

        Args:
            name: Memory name
            strategies: Optional List of typed strategy objects or dictionary configurations
            description: Optional description
            event_expiry_days: How long to retain events (default: 90 days)
            memory_execution_role_arn: IAM role ARN for memory execution
            encryption_key_arn: kms key ARN for encryption

        Returns:
            Memory object, either newly created or existing

        Raises:
            ValueError: If strategies are provided but existing memory has different strategies

        Example:
            from bedrock_agentcore_starter_toolkit.operations.memory.models import SemanticStrategy

            # Create with typed strategy
            semantic = SemanticStrategy(name="MyStrategy")
            memory = manager.get_or_create_memory(
                name="MyMemory",
                strategies=[semantic]
            )
        """
        memory: Memory = None
        try:
            memory_summaries = self.list_memories()
            memory_summary = next((m for m in memory_summaries if m.id.startswith(f"{name}-")), None)

            # Create Memory if it doesn't exist
            if memory_summary is None:
                # Convert typed strategies to dicts for internal processing
                dict_strategies = convert_strategies_to_dicts(strategies) if strategies else None

                memory = self._create_memory_and_wait(
                    name=name,
                    strategies=dict_strategies,
                    description=description,
                    event_expiry_days=event_expiry_days,
                    memory_execution_role_arn=memory_execution_role_arn,
                    encryption_key_arn=encryption_key_arn,
                )
            else:
                logger.info("Memory already exists. Using existing memory ID: %s", memory_summary.id)
                memory = self.get_memory(memory_summary.id)

                # Validate strategies if provided using deep comparison
                if strategies is not None:
                    existing_strategies = memory.get("strategies", memory.get("memoryStrategies", []))
                    memory_name = memory.get("name")
                    validate_existing_memory_strategies(existing_strategies, strategies, memory_name)

            return memory
        except ClientError as e:
            # Failed to create memory
            logger.error("ClientError: Failed to create or get memory: %s", e)
            raise
        except Exception:
            raise

    def get_memory(self, memory_id: str) -> Memory:
        """Retrieves an existing memory resource as a Memory object.

        Maps to: bedrock-agentcore-control.get_memory.
        """
        logger.info("🔎 Retrieving memory resource with ID: %s...", memory_id)
        try:
            response = self._control_plane_client.get_memory(memoryId=memory_id).get("memory", {})
            logger.info("  Found memory: %s", memory_id)
            return Memory(response)
        except ClientError as e:
            logger.error("  ❌ Error retrieving memory: %s", e)
            raise

    def get_memory_status(self, memory_id: str) -> str:
        """Get current memory status."""
        try:
            response = self._control_plane_client.get_memory(memoryId=memory_id)
            return response["memory"]["status"]
        except ClientError as e:
            logger.error("  ❌ Error retrieving memory status: %s", e)
            raise

    def get_memory_strategies(self, memory_id: str) -> List[MemoryStrategy]:
        """Get all strategies for a memory."""
        try:
            response = self._control_plane_client.get_memory(memoryId=memory_id)
            memory = response["memory"]

            # Handle both old and new field names in response
            strategies = memory.get("strategies", memory.get("memoryStrategies", []))
            return [MemoryStrategy(strategy) for strategy in strategies]
        except ClientError as e:
            logger.error("Failed to get memory strategies: %s", e)
            raise

    def list_memories(self, max_results: int = 100) -> list[MemorySummary]:
        """Lists all available memory resources.

        Maps to: bedrock-agentcore-control.list_memories.
        """
        try:
            # Ensure max_results doesn't exceed API limit per request
            results_per_request = min(max_results, 100)

            response = self._control_plane_client.list_memories(maxResults=results_per_request)
            memory_summaries = response.get("memories", [])

            next_token = response.get("nextToken")
            while next_token and len(memory_summaries) < max_results:
                remaining = max_results - len(memory_summaries)
                results_per_request = min(remaining, 100)

                response = self._control_plane_client.list_memories(
                    maxResults=results_per_request, nextToken=next_token
                )
                memory_summaries.extend(response.get("memories", []))
                next_token = response.get("nextToken")

            # Normalize field names for backward compatibility
            for memory_summary in memory_summaries:
                if "memoryId" in memory_summary and "id" not in memory_summary:
                    memory_summary["id"] = memory_summary["memoryId"]
                elif "id" in memory_summary and "memoryId" not in memory_summary:
                    memory_summary["memoryId"] = memory_summary["id"]

            response = [MemorySummary(memory_summary=memory_summary) for memory_summary in memory_summaries]
            return response

        except ClientError as e:
            logger.error("  ❌ Error listing memories: %s", e)
            raise

    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory resource.

        Maps to: bedrock-agentcore-control.delete_memory.
        """
        try:
            response = self._control_plane_client.delete_memory(memoryId=memory_id, clientToken=str(uuid.uuid4()))
            logger.info("Deleted memory: %s", memory_id)
            return response
        except ClientError as e:
            logger.error("  ❌ Error deleting memory: %s", e)
            raise

    def delete_memory_and_wait(self, memory_id: str, max_wait: int = 300, poll_interval: int = 10) -> Dict[str, Any]:
        """Delete a memory and wait for deletion to complete.

        This method deletes a memory and polls until it's fully deleted,
        ensuring clean resource cleanup.

        Args:
            memory_id: Memory resource ID to delete
            max_wait: Maximum seconds to wait (default: 300)
            poll_interval: Seconds between checks (default: 10)

        Returns:
            Final deletion response

        Raises:
            TimeoutError: If deletion doesn't complete within max_wait
        """
        # Initiate deletion
        response = self.delete_memory(memory_id)
        logger.info("Initiated deletion of memory %s", memory_id)

        start_time = time.time()
        while time.time() - start_time < max_wait:
            elapsed = int(time.time() - start_time)

            try:
                # Try to get the memory - if it doesn't exist, deletion is complete
                self._control_plane_client.get_memory(memoryId=memory_id)
                logger.debug("Memory still exists, waiting... (%d seconds elapsed)", elapsed)

            except ClientError as e:
                if e.response["Error"]["Code"] == "ResourceNotFoundException":
                    logger.info("Memory %s successfully deleted (took %d seconds)", memory_id, elapsed)
                    return response
                else:
                    logger.error("Error checking memory status: %s", e)
                    raise

            time.sleep(poll_interval)

        raise TimeoutError("Memory %s was not deleted within %d seconds" % (memory_id, max_wait))

    def add_semantic_strategy(
        self,
        memory_id: str,
        name: str,
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
    ) -> Memory:
        """Add a semantic memory strategy.

        Note: Configuration is no longer provided for built-in strategies as per API changes.
        """
        strategy: Dict = {
            StrategyType.SEMANTIC.value: {
                "name": name,
            }
        }

        if description:
            strategy[StrategyType.SEMANTIC.value]["description"] = description
        if namespaces:
            strategy[StrategyType.SEMANTIC.value]["namespaces"] = namespaces

        return self.add_strategy(memory_id, strategy)

    def add_semantic_strategy_and_wait(
        self,
        memory_id: str,
        name: str,
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> Memory:
        """Add a semantic strategy and wait for memory to return to ACTIVE state.

        This addresses the issue where adding a strategy puts the memory into
        CREATING state temporarily, preventing subsequent operations.
        """
        # Add the strategy
        self.add_semantic_strategy(memory_id, name, description, namespaces)

        # Wait for memory to return to ACTIVE
        return self._wait_for_memory_active(memory_id, max_wait, poll_interval)

    def add_summary_strategy(
        self,
        memory_id: str,
        name: str,
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
    ) -> Memory:
        """Add a summary memory strategy.

        Note: Configuration is no longer provided for built-in strategies as per API changes.
        """
        strategy: Dict = {
            StrategyType.SUMMARY.value: {
                "name": name,
            }
        }

        if description:
            strategy[StrategyType.SUMMARY.value]["description"] = description
        if namespaces:
            strategy[StrategyType.SUMMARY.value]["namespaces"] = namespaces

        return self.add_strategy(memory_id, strategy)

    def add_summary_strategy_and_wait(
        self,
        memory_id: str,
        name: str,
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> Memory:
        """Add a summary strategy and wait for memory to return to ACTIVE state."""
        self.add_summary_strategy(memory_id, name, description, namespaces)
        return self._wait_for_memory_active(memory_id, max_wait, poll_interval)

    def add_user_preference_strategy(
        self,
        memory_id: str,
        name: str,
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
    ) -> Memory:
        """Add a user preference memory strategy.

        Note: Configuration is no longer provided for built-in strategies as per API changes.
        """
        strategy: Dict = {
            StrategyType.USER_PREFERENCE.value: {
                "name": name,
            }
        }

        if description:
            strategy[StrategyType.USER_PREFERENCE.value]["description"] = description
        if namespaces:
            strategy[StrategyType.USER_PREFERENCE.value]["namespaces"] = namespaces

        return self.add_strategy(memory_id, strategy)

    def add_user_preference_strategy_and_wait(
        self,
        memory_id: str,
        name: str,
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> Memory:
        """Add a user preference strategy and wait for memory to return to ACTIVE state."""
        self.add_user_preference_strategy(memory_id, name, description, namespaces)
        return self._wait_for_memory_active(memory_id, max_wait, poll_interval)

    def add_custom_semantic_strategy(
        self,
        memory_id: str,
        name: str,
        extraction_config: Dict[str, Any],
        consolidation_config: Dict[str, Any],
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
    ) -> Memory:
        """Add a custom semantic strategy with prompts.

        Args:
            memory_id: Memory resource ID
            name: Strategy name
            extraction_config: Extraction configuration with prompt and model:
                {"prompt": "...", "modelId": "..."}
            consolidation_config: Consolidation configuration with prompt and model:
                {"prompt": "...", "modelId": "..."}
            description: Optional description
            namespaces: Optional namespaces list
        """
        strategy = {
            StrategyType.CUSTOM.value: {
                "name": name,
                "configuration": {
                    "semanticOverride": {
                        "extraction": {
                            "appendToPrompt": extraction_config["prompt"],
                            "modelId": extraction_config["modelId"],
                        },
                        "consolidation": {
                            "appendToPrompt": consolidation_config["prompt"],
                            "modelId": consolidation_config["modelId"],
                        },
                    }
                },
            }
        }

        if description:
            strategy[StrategyType.CUSTOM.value]["description"] = description
        if namespaces:
            strategy[StrategyType.CUSTOM.value]["namespaces"] = namespaces

        return self.add_strategy(memory_id, strategy)

    def add_custom_semantic_strategy_and_wait(
        self,
        memory_id: str,
        name: str,
        extraction_config: Dict[str, Any],
        consolidation_config: Dict[str, Any],
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> Memory:
        """Add a custom semantic strategy and wait for memory to return to ACTIVE state."""
        self.add_custom_semantic_strategy(
            memory_id, name, extraction_config, consolidation_config, description, namespaces
        )
        return self._wait_for_memory_active(memory_id, max_wait, poll_interval)

    def modify_strategy(
        self,
        memory_id: str,
        strategy_id: str,
        description: Optional[str] = None,
        namespaces: Optional[List[str]] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """Modify a strategy with full control over configuration."""
        modify_config: Dict = {"strategyId": strategy_id}

        if description is not None:
            modify_config["description"] = description
        if namespaces is not None:
            modify_config["namespaces"] = namespaces
        if configuration is not None:
            modify_config["configuration"] = configuration

        return self.update_memory_strategies(memory_id=memory_id, modify_strategies=[modify_config])

    def delete_strategy(self, memory_id: str, strategy_id: str) -> Memory:
        """Delete a strategy from a memory."""
        return self.update_memory_strategies(memory_id=memory_id, delete_strategy_ids=[strategy_id])

    def update_memory_strategies(
        self,
        memory_id: str,
        add_strategies: Optional[List[Union[BaseStrategy, Dict[str, Any]]]] = None,
        modify_strategies: Optional[List[Dict[str, Any]]] = None,
        delete_strategy_ids: Optional[List[str]] = None,
    ) -> Memory:
        """Update memory strategies - add, modify, or delete.

        Args:
            memory_id: Memory resource ID
            add_strategies: List of typed strategy objects or dictionaries to add
            modify_strategies: List of strategy modification dictionaries
            delete_strategy_ids: List of strategy IDs to delete

        Returns:
            Updated Memory object

        Example:
            from bedrock_agentcore_starter_toolkit.operations.memory.models import SemanticStrategy

            # Add typed strategy
            semantic = SemanticStrategy(name="NewStrategy")
            memory = manager.update_memory_strategies(
                memory_id="mem-123",
                add_strategies=[semantic]
            )
        """
        try:
            memory_strategies = {}

            if add_strategies:
                # Convert typed strategies to dicts for internal processing
                dict_strategies = convert_strategies_to_dicts(add_strategies)
                memory_strategies["addMemoryStrategies"] = dict_strategies

            if modify_strategies:
                current_strategies = self.get_memory_strategies(memory_id)
                strategy_map = {s["strategyId"]: s for s in current_strategies}

                modify_list = []
                for strategy in modify_strategies:
                    if "strategyId" not in strategy:
                        raise ValueError("Each modify strategy must include strategyId")

                    strategy_id = strategy["strategyId"]
                    strategy_info = strategy_map.get(strategy_id)

                    if not strategy_info:
                        raise ValueError("Strategy %s not found in memory %s" % (strategy_id, memory_id))

                    # Handle field name variations for strategy type
                    strategy_type = strategy_info.get("type", strategy_info.get("memoryStrategyType", "SEMANTIC"))
                    override_type = strategy_info.get("configuration", {}).get("type")

                    strategy_copy = copy.deepcopy(strategy)

                    if "configuration" in strategy_copy:
                        wrapped_config = self._wrap_configuration(
                            strategy_copy["configuration"], strategy_type, override_type
                        )
                        strategy_copy["configuration"] = wrapped_config

                    modify_list.append(strategy_copy)

                memory_strategies["modifyMemoryStrategies"] = modify_list

            if delete_strategy_ids:
                delete_list = [{"memoryStrategyId": sid} for sid in delete_strategy_ids]
                memory_strategies["deleteMemoryStrategies"] = delete_list

            if not memory_strategies:
                raise ValueError("No strategy operations provided")

            response = self._control_plane_client.update_memory(
                memoryId=memory_id,
                memoryStrategies=memory_strategies,
                clientToken=str(uuid.uuid4()),
            )

            logger.info("Updated memory strategies for: %s", memory_id)
            return Memory(response["memory"])

        except ClientError as e:
            logger.error("Failed to update memory strategies: %s", e)
            raise

    def update_memory_strategies_and_wait(
        self,
        memory_id: str,
        add_strategies: Optional[List[Union[BaseStrategy, Dict[str, Any]]]] = None,
        modify_strategies: Optional[List[Dict[str, Any]]] = None,
        delete_strategy_ids: Optional[List[str]] = None,
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> Memory:
        """Update memory strategies and wait for memory to return to ACTIVE state.

        This method handles the temporary CREATING state that occurs when
        updating strategies, preventing subsequent update errors.

        Args:
            memory_id: Memory resource ID
            add_strategies: List of typed strategy objects or dictionaries to add
            modify_strategies: List of strategy modification dictionaries
            delete_strategy_ids: List of strategy IDs to delete
            max_wait: Maximum seconds to wait (default: 300)
            poll_interval: Seconds between checks (default: 10)

        Returns:
            Updated Memory object in ACTIVE state

        Example:
            from bedrock_agentcore_starter_toolkit.operations.memory.models import SummaryStrategy

            # Add typed strategy and wait
            summary = SummaryStrategy(name="NewSummaryStrategy")
            memory = manager.update_memory_strategies_and_wait(
                memory_id="mem-123",
                add_strategies=[summary]
            )
        """
        # Update strategies
        self.update_memory_strategies(memory_id, add_strategies, modify_strategies, delete_strategy_ids)

        # Wait for memory to return to ACTIVE
        return self._wait_for_memory_active(memory_id, max_wait, poll_interval)

    def add_strategy(self, memory_id: str, strategy: Union[BaseStrategy, Dict[str, Any]]) -> Memory:
        """Add a strategy to a memory (without waiting).

        WARNING: After adding a strategy, the memory enters CREATING state temporarily.
        Use add_strategy_and_wait() method instead to avoid errors.

        Args:
            memory_id: Memory resource ID
            strategy: Typed strategy object or dictionary configuration

        Returns:
            Updated memory response

        Example:
            from bedrock_agentcore_starter_toolkit.operations.memory.models.semantic import SemanticStrategy

            # Using typed strategy (recommended)
            semantic = SemanticStrategy(name="MyStrategy", description="Test")
            memory = manager.add_strategy(memory_id="mem-123", strategy=semantic)

            # Using dictionary (legacy support)
            strategy_dict = {"semanticMemoryStrategy": {"name": "MyStrategy"}}
            memory = manager.add_strategy(memory_id="mem-123", strategy=strategy_dict)
        """
        return self.update_memory_strategies(memory_id=memory_id, add_strategies=[strategy])

    def add_strategy_and_wait(
        self,
        memory_id: str,
        strategy: Union[BaseStrategy, Dict[str, Any]],
        max_wait: int = 300,
        poll_interval: int = 10,
    ) -> Memory:
        """Add a strategy to a memory and wait for it to return to ACTIVE state.

        Args:
            memory_id: Memory resource ID
            strategy: Typed strategy object or dictionary configuration
            max_wait: Maximum seconds to wait (default: 300)
            poll_interval: Seconds between status checks (default: 10)

        Returns:
            Updated memory response in ACTIVE state

        Example:
            from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import (
                SemanticStrategy, CustomSemanticStrategy, ExtractionConfig, ConsolidationConfig
            )

            # Using typed strategy (recommended)
            semantic = SemanticStrategy(name="MyStrategy", description="Test")
            memory = manager.add_strategy_and_wait(memory_id="mem-123", strategy=semantic)

            # Using custom strategy with configurations
            custom = CustomSemanticStrategy(
                name="CustomStrategy",
                extraction_config=ExtractionConfig(
                    append_to_prompt="Extract insights",
                    model_id="anthropic.claude-3-sonnet-20240229-v1:0"
                ),
                consolidation_config=ConsolidationConfig(
                    append_to_prompt="Consolidate insights",
                    model_id="anthropic.claude-3-haiku-20240307-v1:0"
                )
            )
            memory = manager.add_strategy_and_wait(memory_id="mem-123", strategy=custom)
        """
        return self.update_memory_strategies_and_wait(
            memory_id=memory_id, add_strategies=[strategy], max_wait=max_wait, poll_interval=poll_interval
        )

    def _check_strategies_terminal_state(self, strategies: List[Dict[str, Any]]) -> tuple[bool, List[str], List[str]]:
        """Check if all strategies are in terminal states.

        Args:
            strategies: List of strategy dictionaries

        Returns:
            Tuple of (all_terminal, strategy_statuses, failed_strategy_names)
        """
        all_strategies_terminal = True
        strategy_statuses = []
        failed_strategy_names = []

        for strategy in strategies:
            strategy_status = strategy.get("status", "UNKNOWN")
            strategy_statuses.append(strategy_status)

            # Check if strategy is in a terminal state
            if strategy_status not in [MemoryStrategyStatus.ACTIVE.value, MemoryStrategyStatus.FAILED.value]:
                all_strategies_terminal = False
            elif strategy_status == MemoryStrategyStatus.FAILED.value:
                strategy_name = strategy.get("name", strategy.get("strategyId", "unknown"))
                failed_strategy_names.append(strategy_name)

        return all_strategies_terminal, strategy_statuses, failed_strategy_names

    def _wait_for_memory_active(self, memory_id: str, max_wait: int, poll_interval: int) -> Memory:
        """Wait for memory to return to ACTIVE state and all strategies to reach terminal states."""
        logger.info(
            "Waiting for memory %s to return to ACTIVE state and strategies to reach terminal states...", memory_id
        )

        start_time = time.time()
        last_status_print = 0
        status_print_interval = 10  # Print status every 10 seconds

        while time.time() - start_time < max_wait:
            elapsed = int(time.time() - start_time)

            try:
                # Get full memory details including strategies
                response = self._control_plane_client.get_memory(memoryId=memory_id)
                memory = response["memory"]
                memory_status = memory["status"]

                # Check if memory itself has failed
                if memory_status == MemoryStatus.FAILED.value:
                    failure_reason = memory.get("failureReason", "Unknown")
                    raise RuntimeError("Memory update failed: %s" % failure_reason)

                # Get strategies and check their statuses
                strategies = memory.get("strategies", memory.get("memoryStrategies", []))
                all_strategies_terminal, strategy_statuses, failed_strategy_names = (
                    self._check_strategies_terminal_state(strategies)
                )

                # Print status update every 10 seconds
                if elapsed - last_status_print >= status_print_interval:
                    if strategies:
                        active_count = len([s for s in strategy_statuses if s == "ACTIVE"])
                        self.console.log(
                            f"   ⏳ Memory: {memory_status}, "
                            f"Strategies: {active_count}/{len(strategies)} active "
                            f"({elapsed}s elapsed)"
                        )
                    else:
                        self.console.log(f"   ⏳ Memory: {memory_status} ({elapsed}s elapsed)")
                    last_status_print = elapsed

                # Check if memory is ACTIVE and all strategies are in terminal states
                if memory_status == MemoryStatus.ACTIVE.value and all_strategies_terminal:
                    # Check if any strategy failed
                    if failed_strategy_names:
                        raise RuntimeError("Memory strategy(ies) failed: %s" % ", ".join(failed_strategy_names))

                    logger.info(
                        "Memory %s is ACTIVE and all strategies are in terminal states (took %d seconds)",
                        memory_id,
                        elapsed,
                    )
                    self.console.log(f"   ✅ Memory is ACTIVE (took {elapsed}s)")
                    return Memory(memory)

                # Wait before next check
                time.sleep(poll_interval)

            except ClientError as e:
                logger.error("Error checking memory status: %s", e)
                raise

        raise TimeoutError(
            "Memory %s did not return to ACTIVE state with all strategies in terminal states within %d seconds"
            % (memory_id, max_wait)
        )

    def _validate_namespace(self, namespace: str) -> bool:
        """Validate namespace format - basic check only."""
        # Only check for template variables in namespace definition
        if "{" in namespace and not (
            "{actorId}" in namespace or "{sessionId}" in namespace or "{strategyId}" in namespace
        ):
            logger.warning("Namespace with templates should contain valid variables: %s", namespace)

        return True

    def _validate_strategy_config(self, strategy: Dict[str, Any], strategy_type: str) -> None:
        """Validate strategy configuration parameters."""
        strategy_config = strategy[strategy_type]

        namespaces = strategy_config.get("namespaces", [])
        for namespace in namespaces:
            self._validate_namespace(namespace)
