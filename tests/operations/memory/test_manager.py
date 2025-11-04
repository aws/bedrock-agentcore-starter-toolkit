"""Unit tests for Memory Client - no external connections."""

import uuid
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.memory.constants import (
    StrategyType,
)
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory, MemoryStrategy, MemorySummary


def test_manager_initialization():
    """Test client initialization."""
    with patch("boto3.Session") as mock_session_class:
        # Setup the mock session
        mock_session = MagicMock()
        mock_session.region_name = "us-west-2"
        mock_session_class.return_value = mock_session

        # Setup the mock client
        mock_client_instance = MagicMock()
        mock_client_instance.meta.region_name = "us-west-2"
        mock_session.client.return_value = mock_client_instance

        manager = MemoryManager(region_name="us-west-2")

        # Check that the region was set correctly and session.client was called once
        assert manager.region_name == "us-west-2"
        assert mock_session.client.call_count == 1

        # Verify the correct service was called with config
        mock_session.client.assert_called_once()
        call_args = mock_session.client.call_args
        assert call_args[0][0] == "bedrock-agentcore-control"
        assert call_args[1]["region_name"] == "us-west-2"

        # Verify default config includes user agent
        config = call_args[1]["config"]
        assert config.user_agent_extra == "bedrock-agentcore-starter-toolkit"


def test_manager_initialization_with_boto_client_config():
    """Test client initialization with custom boto_client_config."""
    from botocore.config import Config as BotocoreConfig

    with patch("boto3.Session") as mock_session_class:
        # Setup the mock session
        mock_session = MagicMock()
        mock_session.region_name = "us-east-1"
        mock_session_class.return_value = mock_session

        # Setup the mock client
        mock_client_instance = MagicMock()
        mock_session.client.return_value = mock_client_instance

        # Create custom boto client config
        custom_config = BotocoreConfig(retries={"max_attempts": 5}, read_timeout=60)

        manager = MemoryManager(region_name="us-east-1", boto_client_config=custom_config)

        # Check that the region was set correctly
        assert manager.region_name == "us-east-1"
        assert mock_session.client.call_count == 1

        # Verify the correct service was called with merged config
        mock_session.client.assert_called_once()
        call_args = mock_session.client.call_args
        assert call_args[0][0] == "bedrock-agentcore-control"
        assert call_args[1]["region_name"] == "us-east-1"

        # Verify config was merged and includes user agent
        config = call_args[1]["config"]
        assert config.user_agent_extra == "bedrock-agentcore-starter-toolkit"
        # The merged config should contain the original settings
        assert hasattr(config, "retries")
        assert hasattr(config, "read_timeout")


def test_boto_client_config_user_agent_merging():
    """Test that boto_client_config properly merges user agent."""
    from botocore.config import Config as BotocoreConfig

    with patch("boto3.Session") as mock_session_class:
        # Setup the mock session
        mock_session = MagicMock()
        mock_session.region_name = "us-east-1"
        mock_session_class.return_value = mock_session

        # Setup the mock client
        mock_client_instance = MagicMock()
        mock_session.client.return_value = mock_client_instance

        # Test with existing user agent
        custom_config = BotocoreConfig(user_agent_extra="my-custom-agent", retries={"max_attempts": 3})

        MemoryManager(region_name="us-east-1", boto_client_config=custom_config)

        # Verify the user agent was merged correctly
        call_args = mock_session.client.call_args
        config = call_args[1]["config"]
        assert config.user_agent_extra == "my-custom-agent bedrock-agentcore-starter-toolkit"


def test_boto_client_config_without_existing_user_agent():
    """Test boto_client_config when no existing user agent is present."""
    from botocore.config import Config as BotocoreConfig

    with patch("boto3.Session") as mock_session_class:
        # Setup the mock session
        mock_session = MagicMock()
        mock_session.region_name = "us-east-1"
        mock_session_class.return_value = mock_session

        # Setup the mock client
        mock_client_instance = MagicMock()
        mock_session.client.return_value = mock_client_instance

        # Test with config that has no user agent
        custom_config = BotocoreConfig(retries={"max_attempts": 3}, read_timeout=30)

        MemoryManager(region_name="us-east-1", boto_client_config=custom_config)

        # Verify the user agent was added correctly
        call_args = mock_session.client.call_args
        config = call_args[1]["config"]
        assert config.user_agent_extra == "bedrock-agentcore-starter-toolkit"


def test_boto_client_config_with_session_and_region():
    """Test boto_client_config works with both boto3_session and region_name."""
    from botocore.config import Config as BotocoreConfig

    with patch("boto3.Session"):
        # Create a mock session
        mock_session = MagicMock()
        mock_session.region_name = "us-west-2"

        # Setup the mock client
        mock_client_instance = MagicMock()
        mock_session.client.return_value = mock_client_instance

        # Create custom boto client config
        custom_config = BotocoreConfig(connect_timeout=30, user_agent_extra="test-agent")

        MemoryManager(region_name="us-west-2", boto3_session=mock_session, boto_client_config=custom_config)

        # Verify the client was created with the session and merged config
        assert mock_session.client.call_count == 1
        call_args = mock_session.client.call_args
        assert call_args[0][0] == "bedrock-agentcore-control"
        assert call_args[1]["region_name"] == "us-west-2"

        # Verify config was merged properly
        config = call_args[1]["config"]
        assert config.user_agent_extra == "test-agent bedrock-agentcore-starter-toolkit"


def test_boto_client_config_none_handling():
    """Test that None boto_client_config is handled correctly."""
    with patch("boto3.Session") as mock_session_class:
        # Setup the mock session
        mock_session = MagicMock()
        mock_session.region_name = "us-east-1"
        mock_session_class.return_value = mock_session

        # Setup the mock client
        mock_client_instance = MagicMock()
        mock_session.client.return_value = mock_client_instance

        # Test with explicit None config
        MemoryManager(region_name="us-east-1", boto_client_config=None)

        # Verify default config is used
        call_args = mock_session.client.call_args
        config = call_args[1]["config"]
        assert config.user_agent_extra == "bedrock-agentcore-starter-toolkit"


def test_create_memory():
    """Test _create_memory."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock UUID generation to ensure deterministic test
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Mock the _control_plane_client
            mock_control_plane_client = MagicMock()
            manager._control_plane_client = mock_control_plane_client

            # Mock successful response
            mock_control_plane_client.create_memory.return_value = {
                "memory": {"id": "test-memory-123", "status": "CREATING"}
            }

            result = manager._create_memory(
                name="TestMemory", strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}]
            )

            assert result.id == "test-memory-123"
            assert mock_control_plane_client.create_memory.called

            # Verify the client token was passed
            args, kwargs = mock_control_plane_client.create_memory.call_args
            assert kwargs.get("clientToken") == "12345678-1234-5678-1234-567812345678"


def test_error_handling():
    """Test error handling."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client to raise an error
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        error_response = {"Error": {"Code": "ValidationException", "Message": "Invalid parameter"}}
        mock_control_plane_client.create_memory.side_effect = ClientError(error_response, "CreateMemory")

        try:
            manager._create_memory(name="TestMemory", strategies=[{StrategyType.SEMANTIC.value: {"name": "Test"}}])
            raise AssertionError("Error was not raised as expected")
        except ClientError as e:
            assert "ValidationException" in str(e)


def test_memory_strategy_management():
    """Test memory strategy management."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory response for strategy listing
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "id": "mem-123",
                "status": "ACTIVE",
                "strategies": [{"strategyId": "strat-123", "type": "SEMANTIC", "name": "Test Strategy"}],
            }
        }

        # Mock update_memory response for strategy modifications
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "ACTIVE"}}

        # Test get_memory_strategies
        strategies = manager.get_memory_strategies("mem-123")
        assert len(strategies) == 1
        assert strategies[0]["strategyId"] == "strat-123"

        # Test add_semantic_strategy
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            manager.add_semantic_strategy(
                memory_id="mem-123", name="New Semantic Strategy", description="Test strategy"
            )

            assert mock_control_plane_client.update_memory.called
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert "memoryStrategies" in kwargs
            assert "addMemoryStrategies" in kwargs["memoryStrategies"]


def test_create_memory_and_wait_success():
    """Test successful _create_memory_and_wait scenario."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "test-mem-456", "status": "CREATING"}}

        # Mock get_memory to return ACTIVE immediately (simulate quick activation)
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "test-mem-456", "status": "ACTIVE", "name": "TestMemory"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    result = manager._create_memory_and_wait(
                        name="TestMemory",
                        strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                        max_wait=300,
                        poll_interval=10,
                    )

                    assert result.id == "test-mem-456"
                    assert isinstance(result, Memory)


def test_create_memory_and_wait_timeout():
    """Test timeout scenario for create_memory_and_wait."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "test-mem-timeout", "status": "CREATING"}
        }

        # Mock _wait_for_memory_active to raise TimeoutError immediately (skip the loop entirely)
        with patch.object(
            manager,
            "_wait_for_memory_active",
            side_effect=TimeoutError(
                "Memory test-mem-timeout did not return to ACTIVE state "
                "with all strategies in terminal states within 300 seconds"
            ),
        ):
            with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                try:
                    manager.create_memory_and_wait(
                        name="TimeoutMemory",
                        strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                        max_wait=300,
                        poll_interval=10,
                    )
                    raise AssertionError("TimeoutError was not raised")
                except TimeoutError as e:
                    assert "did not return to ACTIVE state with all strategies in terminal states" in str(e)


def test_create_memory_and_wait_failure():
    """Test failure scenario for create_memory_and_wait."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "test-mem-failed", "status": "CREATING"}
        }

        # Mock get_memory to return FAILED status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"memoryId": "test-mem-failed", "status": "FAILED", "failureReason": "Configuration error"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    try:
                        manager.create_memory_and_wait(
                            name="FailedMemory",
                            strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                            max_wait=300,
                            poll_interval=10,
                        )
                        raise AssertionError("RuntimeError was not raised")
                    except RuntimeError as e:
                        # Changed: Error message is "Memory update failed" not "Memory creation failed"
                        assert "Memory update failed: Configuration error" in str(e)


def test_list_memories():
    """Test list_memories functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_memories = [
            {"memoryId": "mem-1", "name": "Memory 1", "status": "ACTIVE"},
            {"memoryId": "mem-2", "name": "Memory 2", "status": "ACTIVE"},
        ]
        mock_control_plane_client.list_memories.return_value = {"memories": mock_memories, "nextToken": None}

        # Test list_memories
        memories = manager.list_memories(max_results=50)

        assert len(memories) == 2
        assert memories[0]["memoryId"] == "mem-1"
        assert memories[1]["memoryId"] == "mem-2"

        # Verify API call
        args, kwargs = mock_control_plane_client.list_memories.call_args
        assert kwargs["maxResults"] == 50


def test_list_memories_with_pagination():
    """Test list_memories with pagination support."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock paginated responses
        first_batch = [{"memoryId": f"mem-{i}", "name": f"Memory {i}", "status": "ACTIVE"} for i in range(1, 101)]
        second_batch = [{"memoryId": f"mem-{i}", "name": f"Memory {i}", "status": "ACTIVE"} for i in range(101, 151)]

        # Setup side effects for multiple calls
        mock_control_plane_client.list_memories.side_effect = [
            {"memories": first_batch, "nextToken": "pagination-token-123"},
            {"memories": second_batch, "nextToken": None},
        ]

        # Test with max_results that requires pagination
        memories = manager.list_memories(max_results=150)

        assert len(memories) == 150
        assert memories[0]["memoryId"] == "mem-1"
        assert memories[0]["name"] == "Memory 1"
        assert memories[99]["memoryId"] == "mem-100"
        assert memories[149]["memoryId"] == "mem-150"

        # Verify two API calls were made
        assert mock_control_plane_client.list_memories.call_count == 2

        # Check first call parameters
        first_call = mock_control_plane_client.list_memories.call_args_list[0]
        assert first_call[1]["maxResults"] == 100
        assert "nextToken" not in first_call[1]

        # Check second call parameters
        second_call = mock_control_plane_client.list_memories.call_args_list[1]
        assert second_call[1]["nextToken"] == "pagination-token-123"
        assert second_call[1]["maxResults"] == 50  # Remaining results needed

        # Verify normalization was applied (both old and new field names should exist)
        for memory in memories:
            assert "memoryId" in memory
            assert "id" in memory
            assert memory["memoryId"] == memory["id"]


def test_delete_memory():
    """Test delete_memory functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_control_plane_client.delete_memory.return_value = {"status": "DELETING"}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test delete_memory
            result = manager.delete_memory("mem-123")

            assert result["status"] == "DELETING"

            # Verify API call
            args, kwargs = mock_control_plane_client.delete_memory.call_args
            assert kwargs["memoryId"] == "mem-123"
            assert kwargs["clientToken"] == "12345678-1234-5678-1234-567812345678"


def test_get_memory_status():
    """Test get_memory_status functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "ACTIVE"}}

        # Test get_memory_status
        status = manager.get_memory_status("mem-123")

        assert status == "ACTIVE"

        # Verify API call
        args, kwargs = mock_control_plane_client.get_memory.call_args
        assert kwargs["memoryId"] == "mem-123"


def test_add_summary_strategy():
    """Test add_summary_strategy functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test add_summary_strategy
            manager.add_summary_strategy(
                memory_id="mem-123", name="Test Summary Strategy", description="Test description"
            )

            assert mock_control_plane_client.update_memory.called

            # Verify strategy was added correctly
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert "memoryStrategies" in kwargs
            assert "addMemoryStrategies" in kwargs["memoryStrategies"]


def test_add_user_preference_strategy():
    """Test add_user_preference_strategy functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-456", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test add_user_preference_strategy
            manager.add_user_preference_strategy(
                memory_id="mem-456",
                name="Test User Preference Strategy",
                description="User preference test description",
                namespaces=["preferences/{actorId}"],
            )

            assert mock_control_plane_client.update_memory.called

            # Verify strategy was added correctly
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert "memoryStrategies" in kwargs
            assert "addMemoryStrategies" in kwargs["memoryStrategies"]

            # Verify the strategy configuration
            add_strategies = kwargs["memoryStrategies"]["addMemoryStrategies"]
            assert len(add_strategies) == 1

            strategy = add_strategies[0]
            assert "userPreferenceMemoryStrategy" in strategy

            user_pref_config = strategy["userPreferenceMemoryStrategy"]
            assert user_pref_config["name"] == "Test User Preference Strategy"
            assert user_pref_config["description"] == "User preference test description"
            assert user_pref_config["namespaces"] == ["preferences/{actorId}"]

            # Verify client token and memory ID
            assert kwargs["memoryId"] == "mem-456"
            assert kwargs["clientToken"] == "12345678-1234-5678-1234-567812345678"


def test_add_custom_semantic_strategy():
    """Test add_custom_semantic_strategy functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-789", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test add_custom_semantic_strategy
            extraction_config = {
                "prompt": "Extract key information from the conversation",
                "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
            }
            consolidation_config = {
                "prompt": "Consolidate extracted information into coherent summaries",
                "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
            }

            manager.add_custom_semantic_strategy(
                memory_id="mem-789",
                name="Test Custom Semantic Strategy",
                extraction_config=extraction_config,
                consolidation_config=consolidation_config,
                description="Custom semantic strategy test description",
                namespaces=["custom/{actorId}/{sessionId}"],
            )

            assert mock_control_plane_client.update_memory.called

            # Verify strategy was added correctly
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert "memoryStrategies" in kwargs
            assert "addMemoryStrategies" in kwargs["memoryStrategies"]

            # Verify the strategy configuration
            add_strategies = kwargs["memoryStrategies"]["addMemoryStrategies"]
            assert len(add_strategies) == 1

            strategy = add_strategies[0]
            assert "customMemoryStrategy" in strategy

            custom_config = strategy["customMemoryStrategy"]
            assert custom_config["name"] == "Test Custom Semantic Strategy"
            assert custom_config["description"] == "Custom semantic strategy test description"
            assert custom_config["namespaces"] == ["custom/{actorId}/{sessionId}"]

            # Verify the semantic override configuration
            assert "configuration" in custom_config
            assert "semanticOverride" in custom_config["configuration"]

            semantic_override = custom_config["configuration"]["semanticOverride"]

            # Verify extraction configuration
            assert "extraction" in semantic_override
            extraction = semantic_override["extraction"]
            assert extraction["appendToPrompt"] == "Extract key information from the conversation"
            assert extraction["modelId"] == "anthropic.claude-3-sonnet-20240229-v1:0"

            # Verify consolidation configuration
            assert "consolidation" in semantic_override
            consolidation = semantic_override["consolidation"]
            assert consolidation["appendToPrompt"] == "Consolidate extracted information into coherent summaries"
            assert consolidation["modelId"] == "anthropic.claude-3-haiku-20240307-v1:0"

            # Verify client token and memory ID
            assert kwargs["memoryId"] == "mem-789"
            assert kwargs["clientToken"] == "12345678-1234-5678-1234-567812345678"


def test_delete_memory_and_wait():
    """Test delete_memory_and_wait functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock delete response
        mock_control_plane_client.delete_memory.return_value = {"status": "DELETING"}

        # Mock get_memory to raise ResourceNotFoundException (memory deleted)
        error_response = {"Error": {"Code": "ResourceNotFoundException", "Message": "Memory not found"}}
        mock_control_plane_client.get_memory.side_effect = ClientError(error_response, "GetMemory")

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test delete_memory_and_wait
                    result = manager.delete_memory_and_wait("mem-123", max_wait=60, poll_interval=5)

                    assert result["status"] == "DELETING"

                    # Verify delete was called
                    assert mock_control_plane_client.delete_memory.called
                    args, kwargs = mock_control_plane_client.delete_memory.call_args
                    assert kwargs["memoryId"] == "mem-123"


def test_update_memory_strategies():
    """Test update_memory_strategies functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test adding strategies
            add_strategies = [{StrategyType.SEMANTIC.value: {"name": "New Strategy"}}]
            manager.update_memory_strategies(memory_id="mem-123", add_strategies=add_strategies)

            assert mock_control_plane_client.update_memory.called

            # Verify correct parameters
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert kwargs["memoryId"] == "mem-123"
            assert "memoryStrategies" in kwargs
            assert "addMemoryStrategies" in kwargs["memoryStrategies"]


def test_update_memory_strategies_modify():
    """Test update_memory_strategies with modify_strategies."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory_strategies to return existing strategies
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "memoryId": "mem-123",
                "status": "ACTIVE",
                "memoryStrategies": [
                    {"strategyId": "strat-456", "memoryStrategyType": "SEMANTIC", "name": "Existing Strategy"}
                ],
            }
        }

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test modifying strategies
            modify_strategies = [{"strategyId": "strat-456", "description": "Updated description"}]
            manager.update_memory_strategies(memory_id="mem-123", modify_strategies=modify_strategies)

            assert mock_control_plane_client.update_memory.called

            # Verify correct parameters
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert kwargs["memoryId"] == "mem-123"
            assert "memoryStrategies" in kwargs
            assert "modifyMemoryStrategies" in kwargs["memoryStrategies"]

            # Verify the modified strategy has the correct ID
            modified_strategy = kwargs["memoryStrategies"]["modifyMemoryStrategies"][0]
            assert modified_strategy["strategyId"] == "strat-456"
            assert modified_strategy["description"] == "Updated description"


def test_wait_for_memory_active():
    """Test _wait_for_memory_active functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory responses
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"memoryId": "mem-123", "status": "ACTIVE", "name": "Test Memory"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                # Test _wait_for_memory_active
                result = manager._wait_for_memory_active("mem-123", max_wait=60, poll_interval=5)

                assert result["memoryId"] == "mem-123"
                assert result["status"] == "ACTIVE"

                # Verify get_memory was called
                assert mock_control_plane_client.get_memory.called


def test_wait_for_memory_active_failed_status():
    """Test _wait_for_memory_active when memory status becomes FAILED."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory to return FAILED status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"memoryId": "mem-failed", "status": "FAILED", "failureReason": "Strategy configuration error"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                # Test _wait_for_memory_active with FAILED status
                try:
                    manager._wait_for_memory_active("mem-failed", max_wait=60, poll_interval=5)
                    raise AssertionError("RuntimeError was not raised")
                except RuntimeError as e:
                    assert "Memory update failed: Strategy configuration error" in str(e)

                # Verify get_memory was called
                assert mock_control_plane_client.get_memory.called


def test_wait_for_memory_active_client_error():
    """Test _wait_for_memory_active when ClientError is raised."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory to raise ClientError
        error_response = {"Error": {"Code": "ValidationException", "Message": "Invalid memory ID"}}
        mock_control_plane_client.get_memory.side_effect = ClientError(error_response, "GetMemory")

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                # Test _wait_for_memory_active with ClientError
                try:
                    manager._wait_for_memory_active("mem-invalid", max_wait=60, poll_interval=5)
                    raise AssertionError("ClientError was not raised")
                except ClientError as e:
                    assert "ValidationException" in str(e)

                # Verify get_memory was called
                assert mock_control_plane_client.get_memory.called


def test_wrap_configuration():
    """Test _wrap_configuration functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test basic configuration wrapping
        config = {
            "extraction": {"appendToPrompt": "Custom prompt", "modelId": "test-model"},
            "consolidation": {"appendToPrompt": "Consolidation prompt", "modelId": "test-model"},
        }

        # Test wrapping for CUSTOM strategy with semantic override
        wrapped = manager._wrap_configuration(config, "CUSTOM", "SEMANTIC_OVERRIDE")

        # Should wrap in custom configuration structure
        assert "extraction" in wrapped
        assert "consolidation" in wrapped


def test_wrap_configuration_basic():
    """Test _wrap_configuration with basic config."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test config that doesn't need wrapping
        simple_config = {"extraction": {"modelId": "test-model"}}

        # Test with SEMANTIC strategy
        wrapped = manager._wrap_configuration(simple_config, "SEMANTIC", None)

        # Should pass through unchanged
        assert wrapped["extraction"]["modelId"] == "test-model"


def test_wrap_configuration_semantic_strategy():
    """Test _wrap_configuration with SEMANTIC strategy type."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test extraction configuration that needs wrapping
        config = {
            "extraction": {"triggerEveryNMessages": 5, "historicalContextWindowSize": 10, "modelId": "semantic-model"}
        }

        wrapped = manager._wrap_configuration(config, "SEMANTIC", None)

        # Should wrap in semanticExtractionConfiguration
        assert "extraction" in wrapped
        assert "semanticExtractionConfiguration" in wrapped["extraction"]
        assert wrapped["extraction"]["semanticExtractionConfiguration"]["triggerEveryNMessages"] == 5
        assert wrapped["extraction"]["semanticExtractionConfiguration"]["historicalContextWindowSize"] == 10
        assert wrapped["extraction"]["semanticExtractionConfiguration"]["modelId"] == "semantic-model"


def test_wrap_configuration_user_preference_strategy():
    """Test _wrap_configuration with USER_PREFERENCE strategy type."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test extraction configuration that needs wrapping for user preferences
        config = {
            "extraction": {"triggerEveryNMessages": 3, "historicalContextWindowSize": 20, "preferenceType": "dietary"}
        }

        wrapped = manager._wrap_configuration(config, "USER_PREFERENCE", None)

        # Should wrap in userPreferenceExtractionConfiguration
        assert "extraction" in wrapped
        assert "userPreferenceExtractionConfiguration" in wrapped["extraction"]
        assert wrapped["extraction"]["userPreferenceExtractionConfiguration"]["triggerEveryNMessages"] == 3
        assert wrapped["extraction"]["userPreferenceExtractionConfiguration"]["historicalContextWindowSize"] == 20
        assert wrapped["extraction"]["userPreferenceExtractionConfiguration"]["preferenceType"] == "dietary"


def test_wrap_configuration_custom_semantic_override():
    """Test _wrap_configuration with CUSTOM strategy and SEMANTIC_OVERRIDE."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test custom semantic override configuration
        config = {
            "extraction": {
                "triggerEveryNMessages": 2,
                "historicalContextWindowSize": 15,
                "appendToPrompt": "Extract key insights",
                "modelId": "custom-semantic-model",
            },
            "consolidation": {"appendToPrompt": "Consolidate insights", "modelId": "consolidation-model"},
        }

        wrapped = manager._wrap_configuration(config, "CUSTOM", "SEMANTIC_OVERRIDE")

        # Should wrap extraction in customExtractionConfiguration with semanticExtractionOverride
        assert "extraction" in wrapped
        assert "customExtractionConfiguration" in wrapped["extraction"]
        assert "semanticExtractionOverride" in wrapped["extraction"]["customExtractionConfiguration"]

        semantic_config = wrapped["extraction"]["customExtractionConfiguration"]["semanticExtractionOverride"]
        assert semantic_config["triggerEveryNMessages"] == 2
        assert semantic_config["historicalContextWindowSize"] == 15
        assert semantic_config["appendToPrompt"] == "Extract key insights"
        assert semantic_config["modelId"] == "custom-semantic-model"

        # Should wrap consolidation in customConsolidationConfiguration with semanticConsolidationOverride
        assert "consolidation" in wrapped
        assert "customConsolidationConfiguration" in wrapped["consolidation"]
        assert "semanticConsolidationOverride" in wrapped["consolidation"]["customConsolidationConfiguration"]

        consolidation_config = wrapped["consolidation"]["customConsolidationConfiguration"][
            "semanticConsolidationOverride"
        ]
        assert consolidation_config["appendToPrompt"] == "Consolidate insights"
        assert consolidation_config["modelId"] == "consolidation-model"


def test_modify_strategy():
    """Test modify_strategy convenience method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory_strategies to return existing strategies (needed by update_memory_strategies)
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "memoryId": "mem-123",
                "status": "ACTIVE",
                "memoryStrategies": [
                    {"strategyId": "strat-789", "memoryStrategyType": "SEMANTIC", "name": "Test Strategy"}
                ],
            }
        }

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test modify_strategy
            manager.modify_strategy(
                memory_id="mem-123",
                strategy_id="strat-789",
                description="Modified description",
                namespaces=["custom/namespace"],
            )

            assert mock_control_plane_client.update_memory.called

            # Verify correct parameters were passed to update_memory_strategies
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert kwargs["memoryId"] == "mem-123"
            assert "memoryStrategies" in kwargs
            assert "modifyMemoryStrategies" in kwargs["memoryStrategies"]

            # Verify the modified strategy has correct details
            modified_strategy = kwargs["memoryStrategies"]["modifyMemoryStrategies"][0]
            assert modified_strategy["strategyId"] == "strat-789"
            assert modified_strategy["description"] == "Modified description"
            assert modified_strategy["namespaces"] == ["custom/namespace"]


def test_add_semantic_strategy_and_wait():
    """Test add_semantic_strategy_and_wait functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        # Mock get_memory response (simulating ACTIVE status)
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "ACTIVE"}}

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test add_semantic_strategy_and_wait
                    result = manager.add_semantic_strategy_and_wait(
                        memory_id="mem-123", name="Test Strategy", description="Test description"
                    )

                    assert result["memoryId"] == "mem-123"
                    assert result["status"] == "ACTIVE"

                    # Verify update_memory was called
                    assert mock_control_plane_client.update_memory.called

                    # Verify get_memory was called (for waiting)
                    assert mock_control_plane_client.get_memory.called


def test_add_summary_strategy_and_wait():
    """Test add_summary_strategy_and_wait functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-456", "status": "CREATING"}}

        # Mock get_memory response (simulating ACTIVE status)
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-456", "status": "ACTIVE"}}

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test add_summary_strategy_and_wait
                    result = manager.add_summary_strategy_and_wait(
                        memory_id="mem-456", name="Test Summary Strategy", description="Test description"
                    )

                    assert result["memoryId"] == "mem-456"
                    assert result["status"] == "ACTIVE"

                    # Verify update_memory was called
                    assert mock_control_plane_client.update_memory.called

                    # Verify get_memory was called (for waiting)
                    assert mock_control_plane_client.get_memory.called


def test_add_user_preference_strategy_and_wait():
    """Test add_user_preference_strategy_and_wait functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-789", "status": "CREATING"}}

        # Mock get_memory response (simulating ACTIVE status)
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-789", "status": "ACTIVE"}}

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test add_user_preference_strategy_and_wait
                    result = manager.add_user_preference_strategy_and_wait(
                        memory_id="mem-789", name="Test User Preference Strategy", description="Test description"
                    )

                    assert result["memoryId"] == "mem-789"
                    assert result["status"] == "ACTIVE"

                    # Verify update_memory was called
                    assert mock_control_plane_client.update_memory.called

                    # Verify get_memory was called (for waiting)
                    assert mock_control_plane_client.get_memory.called


def test_add_custom_semantic_strategy_and_wait():
    """Test add_custom_semantic_strategy_and_wait functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-999", "status": "CREATING"}}

        # Mock get_memory response (simulating ACTIVE status)
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-999", "status": "ACTIVE"}}

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test add_custom_semantic_strategy_and_wait
                    extraction_config = {"prompt": "Extract key info", "modelId": "claude-3-sonnet"}
                    consolidation_config = {"prompt": "Consolidate info", "modelId": "claude-3-haiku"}

                    result = manager.add_custom_semantic_strategy_and_wait(
                        memory_id="mem-999",
                        name="Test Custom Strategy",
                        extraction_config=extraction_config,
                        consolidation_config=consolidation_config,
                        description="Test description",
                    )

                    assert result["memoryId"] == "mem-999"
                    assert result["status"] == "ACTIVE"

                    # Verify update_memory was called
                    assert mock_control_plane_client.update_memory.called

                    # Verify get_memory was called (for waiting)
                    assert mock_control_plane_client.get_memory.called


def test_update_memory_strategies_and_wait():
    """Test update_memory_strategies_and_wait functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory to simulate transition from CREATING to ACTIVE
        get_memory_responses = [
            # First call - still creating
            {"memory": {"memoryId": "mem-123", "status": "CREATING", "memoryStrategies": []}},
            # Second call - now active
            {"memory": {"memoryId": "mem-123", "status": "ACTIVE", "memoryStrategies": []}},
        ]
        mock_control_plane_client.get_memory.side_effect = get_memory_responses

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test update_memory_strategies_and_wait
                    add_strategies = [{StrategyType.SEMANTIC.value: {"name": "New Strategy"}}]
                    result = manager.update_memory_strategies_and_wait(
                        memory_id="mem-123", add_strategies=add_strategies
                    )

                    assert result["memoryId"] == "mem-123"
                    assert result["status"] == "ACTIVE"

                    # Verify update_memory was called
                    assert mock_control_plane_client.update_memory.called

                    # Verify get_memory was called multiple times
                    assert mock_control_plane_client.get_memory.call_count >= 2


def test_delete_strategy():
    """Test delete_strategy functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory for strategy retrieval
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-123", "memoryStrategies": []}}

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "ACTIVE"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test delete_strategy
            result = manager.delete_strategy(memory_id="mem-123", strategy_id="strat-456")

            assert result["memoryId"] == "mem-123"

            # Verify update_memory was called with delete operation
            args, kwargs = mock_control_plane_client.update_memory.call_args
            assert "memoryStrategies" in kwargs
            assert "deleteMemoryStrategies" in kwargs["memoryStrategies"]
            assert kwargs["memoryStrategies"]["deleteMemoryStrategies"][0]["memoryStrategyId"] == "strat-456"


def test_create_memory_and_wait_client_error():
    """Test create_memory_and_wait with ClientError during status check."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "test-mem-error", "status": "CREATING"}
        }

        # Mock get_memory to raise ClientError
        error_response = {"Error": {"Code": "ValidationException", "Message": "Invalid memory ID"}}
        mock_control_plane_client.get_memory.side_effect = ClientError(error_response, "GetMemory")

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    try:
                        manager.create_memory_and_wait(
                            name="ErrorMemory",
                            strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                            max_wait=300,
                            poll_interval=10,
                        )
                        raise AssertionError("ClientError was not raised")
                    except ClientError as e:
                        assert "ValidationException" in str(e)


def test_get_memory_strategies_client_error():
    """Test get_memory_strategies with ClientError."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock ClientError
        error_response = {"Error": {"Code": "ResourceNotFoundException", "Message": "Memory not found"}}
        mock_control_plane_client.get_memory.side_effect = ClientError(error_response, "GetMemory")

        try:
            manager.get_memory_strategies("nonexistent-mem-123")
            raise AssertionError("ClientError was not raised")
        except ClientError as e:
            assert "ResourceNotFoundException" in str(e)


def test_list_memories_client_error():
    """Test list_memories with ClientError."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock ClientError
        error_response = {"Error": {"Code": "AccessDeniedException", "Message": "Insufficient permissions"}}
        mock_control_plane_client.list_memories.side_effect = ClientError(error_response, "ListMemories")

        try:
            manager.list_memories(max_results=50)
            raise AssertionError("ClientError was not raised")
        except ClientError as e:
            assert "AccessDeniedException" in str(e)


def test_delete_memory_client_error():
    """Test delete_memory with ClientError."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock ClientError
        error_response = {"Error": {"Code": "ConflictException", "Message": "Memory is in use"}}
        mock_control_plane_client.delete_memory.side_effect = ClientError(error_response, "DeleteMemory")

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                manager.delete_memory("mem-in-use")
                raise AssertionError("ClientError was not raised")
            except ClientError as e:
                assert "ConflictException" in str(e)


def test_update_memory_strategies_client_error():
    """Test update_memory_strategies with ClientError."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock ClientError
        error_response = {"Error": {"Code": "ValidationException", "Message": "Invalid strategy configuration"}}
        mock_control_plane_client.update_memory.side_effect = ClientError(error_response, "UpdateMemory")

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                add_strategies = [{StrategyType.SEMANTIC.value: {"name": "Invalid Strategy"}}]
                manager.update_memory_strategies(memory_id="mem-123", add_strategies=add_strategies)
                raise AssertionError("ClientError was not raised")
            except ClientError as e:
                assert "ValidationException" in str(e)


# Memory class tests
def test_memory_initialization():
    """Test Memory class initialization."""
    memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    memory = Memory(memory_data)

    assert memory.id == "mem-123"
    assert memory.name == "Test Memory"
    assert memory.status == "ACTIVE"


def test_memory_attribute_access():
    """Test Memory class attribute access patterns."""
    memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    memory = Memory(memory_data)

    # Test __getattr__
    assert memory.id == "mem-123"
    assert memory.name == "Test Memory"

    # Test __getitem__
    assert memory["id"] == "mem-123"
    assert memory["name"] == "Test Memory"

    # Test get method
    assert memory.get("id") == "mem-123"
    assert memory.get("nonexistent", "default") == "default"


def test_memory_with_none_data():
    """Test Memory class with None data."""
    memory = Memory(None)

    # Should handle None gracefully
    assert memory.id is None
    assert memory.get("id") is None


def test_memory_with_empty_data():
    """Test Memory class with empty data."""
    memory = Memory({})

    # Should handle empty dict gracefully
    assert memory.id is None
    assert memory.get("id") is None


def test_get_memory():
    """Test get_memory functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock response
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        }

        # Test get_memory
        result = manager.get_memory("mem-123")

        assert isinstance(result, Memory)
        assert result.id == "mem-123"
        assert result.name == "Test Memory"

        # Verify API call
        args, kwargs = mock_control_plane_client.get_memory.call_args
        assert kwargs["memoryId"] == "mem-123"


def test_memory_manager_getattr_not_found():
    """Test MemoryManager __getattr__ when method not found."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the control plane client without the method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        del mock_control_plane_client.nonexistent_method

        try:
            manager.nonexistent_method()
            raise AssertionError("AttributeError was not raised")
        except AttributeError as e:
            assert "object has no attribute 'nonexistent_method'" in str(e)


# Test MemoryStrategy and MemorySummary models
def test_memory_strategy_model():
    """Test MemoryStrategy model."""
    strategy_data = {"strategyId": "strat-123", "type": "SEMANTIC", "name": "Test Strategy"}

    strategy = MemoryStrategy(strategy_data)

    assert strategy.strategyId == "strat-123"
    assert strategy.type == "SEMANTIC"
    assert strategy.name == "Test Strategy"
    assert strategy["strategyId"] == "strat-123"
    assert str(strategy) == str(strategy_data)


def test_memory_summary_model():
    """Test MemorySummary model."""
    summary_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    summary = MemorySummary(summary_data)

    assert summary.id == "mem-123"
    assert summary.name == "Test Memory"
    assert summary.status == "ACTIVE"
    assert summary["id"] == "mem-123"
    assert str(summary) == str(summary_data)


# Additional tests for missing coverage


def test_validate_namespace():
    """Test _validate_namespace functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test valid namespaces
        assert manager._validate_namespace("custom/{actorId}/{sessionId}")
        assert manager._validate_namespace("preferences/{actorId}")
        assert manager._validate_namespace("strategy/{strategyId}")
        assert manager._validate_namespace("simple/namespace")

        # Test namespace with invalid template variables (should log warning)
        with patch("bedrock_agentcore_starter_toolkit.operations.memory.manager.logger") as mock_logger:
            assert manager._validate_namespace("invalid/{unknownVar}")
            mock_logger.warning.assert_called_once()


def test_validate_strategy_config():
    """Test _validate_strategy_config functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock _validate_namespace to track calls
        with patch.object(manager, "_validate_namespace", return_value=True) as mock_validate:
            strategy = {
                "semanticMemoryStrategy": {
                    "name": "Test Strategy",
                    "namespaces": ["custom/{actorId}", "preferences/{sessionId}"],
                }
            }

            manager._validate_strategy_config(strategy, "semanticMemoryStrategy")

            # Should validate each namespace
            assert mock_validate.call_count == 2
            mock_validate.assert_any_call("custom/{actorId}")
            mock_validate.assert_any_call("preferences/{sessionId}")


def test_check_strategies_terminal_state():
    """Test _check_strategies_terminal_state functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test all strategies active
        strategies = [
            {"strategyId": "strat-1", "status": "ACTIVE", "name": "Strategy 1"},
            {"strategyId": "strat-2", "status": "ACTIVE", "name": "Strategy 2"},
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal
        assert statuses == ["ACTIVE", "ACTIVE"]
        assert failed_names == []

        # Test some strategies still creating
        strategies = [
            {"strategyId": "strat-1", "status": "ACTIVE", "name": "Strategy 1"},
            {"strategyId": "strat-2", "status": "CREATING", "name": "Strategy 2"},
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert not all_terminal
        assert statuses == ["ACTIVE", "CREATING"]
        assert failed_names == []

        # Test some strategies failed
        strategies = [
            {"strategyId": "strat-1", "status": "ACTIVE", "name": "Strategy 1"},
            {"strategyId": "strat-2", "status": "FAILED", "name": "Strategy 2"},
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal
        assert statuses == ["ACTIVE", "FAILED"]
        assert failed_names == ["Strategy 2"]

        # Test strategy without name (uses strategyId)
        strategies = [{"strategyId": "strat-1", "status": "FAILED"}]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal
        assert statuses == ["FAILED"]
        assert failed_names == ["strat-1"]

        # Test strategy without name or strategyId (uses "unknown")
        strategies = [{"status": "FAILED"}]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal
        assert statuses == ["FAILED"]
        assert failed_names == ["unknown"]


def test_wait_for_memory_active_with_strategy_failures():
    """Test _wait_for_memory_active when strategies fail."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory to return ACTIVE memory with failed strategy
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "memoryId": "mem-123",
                "status": "ACTIVE",
                "strategies": [
                    {"strategyId": "strat-1", "status": "ACTIVE", "name": "Good Strategy"},
                    {"strategyId": "strat-2", "status": "FAILED", "name": "Bad Strategy"},
                ],
            }
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                try:
                    manager._wait_for_memory_active("mem-123", max_wait=60, poll_interval=5)
                    raise AssertionError("RuntimeError was not raised")
                except RuntimeError as e:
                    assert "Memory strategy(ies) failed: Bad Strategy" in str(e)


def test_wait_for_memory_active_with_strategies_still_creating():
    """Test _wait_for_memory_active when strategies are still creating then become active."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory responses - first call has creating strategy, second has active
        get_memory_responses = [
            {
                "memory": {
                    "memoryId": "mem-123",
                    "status": "ACTIVE",
                    "strategies": [{"strategyId": "strat-1", "status": "CREATING", "name": "Strategy 1"}],
                }
            },
            {
                "memory": {
                    "memoryId": "mem-123",
                    "status": "ACTIVE",
                    "strategies": [{"strategyId": "strat-1", "status": "ACTIVE", "name": "Strategy 1"}],
                }
            },
        ]
        mock_control_plane_client.get_memory.side_effect = get_memory_responses

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                result = manager._wait_for_memory_active("mem-123", max_wait=60, poll_interval=5)

                assert result["memoryId"] == "mem-123"
                assert result["status"] == "ACTIVE"
                assert mock_control_plane_client.get_memory.call_count == 2


def test_wait_for_memory_active_timeout_with_strategies():
    """Test _wait_for_memory_active timeout when strategies never reach terminal state."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory to always return ACTIVE memory with creating strategy
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "memoryId": "mem-123",
                "status": "ACTIVE",
                "strategies": [{"strategyId": "strat-1", "status": "CREATING", "name": "Strategy 1"}],
            }
        }

        # Mock time to simulate timeout
        # Use itertools.cycle to provide unlimited values for Python 3.12 compatibility
        from itertools import cycle

        with patch("time.time", side_effect=cycle([0, 0, 0, 61, 61, 61, 61, 61])):
            with patch("time.sleep"):
                try:
                    manager._wait_for_memory_active("mem-123", max_wait=60, poll_interval=5)
                    raise AssertionError("TimeoutError was not raised")
                except TimeoutError as e:
                    expected_msg = (
                        "did not return to ACTIVE state with all strategies in terminal states within 60 seconds"
                    )
                    assert expected_msg in str(e)


def test_wrap_configuration_summary_strategy():
    """Test _wrap_configuration with SUMMARIZATION strategy type."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test consolidation configuration for SUMMARIZATION strategy
        config = {"consolidation": {"triggerEveryNMessages": 10}}

        wrapped = manager._wrap_configuration(config, "SUMMARIZATION", None)

        # Should wrap in summaryConsolidationConfiguration
        assert "consolidation" in wrapped
        assert "summaryConsolidationConfiguration" in wrapped["consolidation"]
        assert wrapped["consolidation"]["summaryConsolidationConfiguration"]["triggerEveryNMessages"] == 10


def test_wrap_configuration_custom_user_preference_override():
    """Test _wrap_configuration with CUSTOM strategy and USER_PREFERENCE_OVERRIDE."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test custom user preference override configuration
        config = {
            "extraction": {
                "triggerEveryNMessages": 3,
                "historicalContextWindowSize": 25,
                "preferenceType": "communication",
            },
            "consolidation": {"appendToPrompt": "Consolidate user preferences", "modelId": "user-pref-model"},
        }

        wrapped = manager._wrap_configuration(config, "CUSTOM", "USER_PREFERENCE_OVERRIDE")

        # Should wrap extraction in customExtractionConfiguration with userPreferenceExtractionOverride
        assert "extraction" in wrapped
        assert "customExtractionConfiguration" in wrapped["extraction"]
        assert "userPreferenceExtractionOverride" in wrapped["extraction"]["customExtractionConfiguration"]

        user_pref_config = wrapped["extraction"]["customExtractionConfiguration"]["userPreferenceExtractionOverride"]
        assert user_pref_config["triggerEveryNMessages"] == 3
        assert user_pref_config["historicalContextWindowSize"] == 25
        assert user_pref_config["preferenceType"] == "communication"

        # Should wrap consolidation in customConsolidationConfiguration with userPreferenceConsolidationOverride
        assert "consolidation" in wrapped
        assert "customConsolidationConfiguration" in wrapped["consolidation"]
        assert "userPreferenceConsolidationOverride" in wrapped["consolidation"]["customConsolidationConfiguration"]

        consolidation_config = wrapped["consolidation"]["customConsolidationConfiguration"][
            "userPreferenceConsolidationOverride"
        ]
        assert consolidation_config["appendToPrompt"] == "Consolidate user preferences"
        assert consolidation_config["modelId"] == "user-pref-model"


def test_wrap_configuration_custom_summary_override():
    """Test _wrap_configuration with CUSTOM strategy and SUMMARY_OVERRIDE."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test custom summary override configuration
        config = {"consolidation": {"appendToPrompt": "Create custom summary", "modelId": "summary-model"}}

        wrapped = manager._wrap_configuration(config, "CUSTOM", "SUMMARY_OVERRIDE")

        # Should wrap consolidation in customConsolidationConfiguration with summaryConsolidationOverride
        assert "consolidation" in wrapped
        assert "customConsolidationConfiguration" in wrapped["consolidation"]
        assert "summaryConsolidationOverride" in wrapped["consolidation"]["customConsolidationConfiguration"]

        summary_config = wrapped["consolidation"]["customConsolidationConfiguration"]["summaryConsolidationOverride"]
        assert summary_config["appendToPrompt"] == "Create custom summary"
        assert summary_config["modelId"] == "summary-model"


def test_wrap_configuration_no_wrapping_needed():
    """Test _wrap_configuration when no wrapping is needed."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test config that doesn't need wrapping (no trigger/historical context keys)
        config = {"extraction": {"modelId": "test-model"}, "consolidation": {"modelId": "test-model"}}

        wrapped = manager._wrap_configuration(config, "SEMANTIC", None)

        # Should pass through unchanged
        assert wrapped["extraction"]["modelId"] == "test-model"
        # Consolidation might not be returned if it doesn't need wrapping
        if "consolidation" in wrapped:
            assert wrapped["consolidation"]["modelId"] == "test-model"


def test_create_memory_with_all_parameters():
    """Test _create_memory with all optional parameters."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock UUID generation
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Mock the _control_plane_client
            mock_control_plane_client = MagicMock()
            manager._control_plane_client = mock_control_plane_client

            # Mock successful response
            mock_control_plane_client.create_memory.return_value = {
                "memory": {"id": "test-memory-456", "status": "CREATING"}
            }

            result = manager._create_memory(
                name="TestMemory",
                strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                description="Test description",
                event_expiry_days=120,
                memory_execution_role_arn="arn:aws:iam::123456789012:role/MemoryRole",
            )

            assert result.id == "test-memory-456"
            assert mock_control_plane_client.create_memory.called

            # Verify all parameters were passed
            args, kwargs = mock_control_plane_client.create_memory.call_args
            assert kwargs["name"] == "TestMemory"
            assert kwargs["description"] == "Test description"
            assert kwargs["eventExpiryDuration"] == 120
            assert kwargs["memoryExecutionRoleArn"] == "arn:aws:iam::123456789012:role/MemoryRole"
            assert kwargs["clientToken"] == "12345678-1234-5678-1234-567812345678"


def test_create_memory_with_minimal_parameters():
    """Test _create_memory with minimal parameters."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock UUID generation
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Mock the _control_plane_client
            mock_control_plane_client = MagicMock()
            manager._control_plane_client = mock_control_plane_client

            # Mock successful response
            mock_control_plane_client.create_memory.return_value = {
                "memory": {"id": "test-memory-789", "status": "CREATING"}
            }

            result = manager._create_memory(name="MinimalMemory")

            assert result.id == "test-memory-789"
            assert mock_control_plane_client.create_memory.called

            # Verify minimal parameters were passed
            args, kwargs = mock_control_plane_client.create_memory.call_args
            assert kwargs["name"] == "MinimalMemory"
            assert kwargs["eventExpiryDuration"] == 90  # default
            assert kwargs["memoryStrategies"] == []  # empty list processed
            assert "description" not in kwargs
            assert "memoryExecutionRoleArn" not in kwargs


def test_create_memory_field_name_normalization():
    """Test _create_memory handles field name normalization."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock UUID generation
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Mock the _control_plane_client
            mock_control_plane_client = MagicMock()
            manager._control_plane_client = mock_control_plane_client

            # Mock response with memoryId instead of id
            mock_control_plane_client.create_memory.return_value = {
                "memory": {"memoryId": "test-memory-normalized", "status": "CREATING"}
            }

            result = manager._create_memory(name="NormalizedMemory")

            # Should handle memoryId field - access via get method
            assert result.get("memoryId") == "test-memory-normalized"


def test_create_memory_no_id_field():
    """Test _create_memory when response has no id field."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock UUID generation
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Mock the _control_plane_client
            mock_control_plane_client = MagicMock()
            manager._control_plane_client = mock_control_plane_client

            # Mock response with no id or memoryId field
            mock_control_plane_client.create_memory.return_value = {"memory": {"status": "CREATING"}}

            result = manager._create_memory(name="NoIdMemory")

            # Should handle missing id gracefully
            assert result.get("id") is None
            assert result.get("memoryId") is None


# Additional Memory class tests for better coverage
def test_memory_repr():
    """Test Memory class __repr__ method."""
    memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    memory = Memory(memory_data)

    # __repr__ should return the string representation of the underlying dict
    assert repr(memory) == repr(memory_data)


def test_memory_get_method():
    """Test Memory class get method access."""
    memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    memory = Memory(memory_data)

    # Test accessing get method
    assert memory.get("id") == "mem-123"
    assert memory.get("nonexistent", "default") == "default"


# Additional MemoryStrategy model tests
def test_memory_strategy_get_method():
    """Test MemoryStrategy get method."""
    strategy_data = {"strategyId": "strat-123", "type": "SEMANTIC", "name": "Test Strategy"}

    strategy = MemoryStrategy(strategy_data)

    assert strategy.get("strategyId") == "strat-123"
    assert strategy.get("nonexistent", "default") == "default"


def test_memory_strategy_contains():
    """Test MemoryStrategy __contains__ method."""
    strategy_data = {"strategyId": "strat-123", "type": "SEMANTIC", "name": "Test Strategy"}

    strategy = MemoryStrategy(strategy_data)

    assert "strategyId" in strategy
    assert "nonexistent" not in strategy


def test_memory_strategy_keys_values_items():
    """Test MemoryStrategy keys, values, and items methods."""
    strategy_data = {"strategyId": "strat-123", "type": "SEMANTIC", "name": "Test Strategy"}

    strategy = MemoryStrategy(strategy_data)

    assert list(strategy.keys()) == ["strategyId", "type", "name"]
    assert list(strategy.values()) == ["strat-123", "SEMANTIC", "Test Strategy"]
    assert list(strategy.items()) == [("strategyId", "strat-123"), ("type", "SEMANTIC"), ("name", "Test Strategy")]


# Additional MemorySummary model tests
def test_memory_summary_get_method():
    """Test MemorySummary get method."""
    summary_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    summary = MemorySummary(summary_data)

    assert summary.get("id") == "mem-123"
    assert summary.get("nonexistent", "default") == "default"


def test_memory_summary_contains():
    """Test MemorySummary __contains__ method."""
    summary_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    summary = MemorySummary(summary_data)

    assert "id" in summary
    assert "nonexistent" not in summary


def test_memory_summary_keys_values_items():
    """Test MemorySummary keys, values, and items methods."""
    summary_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}

    summary = MemorySummary(summary_data)

    assert list(summary.keys()) == ["id", "name", "status"]
    assert list(summary.values()) == ["mem-123", "Test Memory", "ACTIVE"]
    assert list(summary.items()) == [("id", "mem-123"), ("name", "Test Memory"), ("status", "ACTIVE")]


def test_delete_memory_and_wait_timeout():
    """Test delete_memory_and_wait timeout scenario."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock delete response
        mock_control_plane_client.delete_memory.return_value = {"status": "DELETING"}

        # Mock get_memory to always succeed (memory never gets deleted)
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "DELETING"}}

        # Mock time to simulate timeout - provide enough values for all time.time() calls
        # The while loop calls time.time() twice per iteration: once for the condition, once for elapsed calculation
        # We need: start_time, condition_check, elapsed_calc, condition_check (timeout), elapsed_calc
        with patch("time.time", side_effect=[0, 0, 0, 61, 61]):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    try:
                        manager.delete_memory_and_wait("mem-123", max_wait=60, poll_interval=5)
                        raise AssertionError("TimeoutError was not raised")
                    except TimeoutError as e:
                        assert "was not deleted within 60 seconds" in str(e)


def test_delete_memory_and_wait_other_client_error():
    """Test delete_memory_and_wait with non-ResourceNotFoundException ClientError."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock delete response
        mock_control_plane_client.delete_memory.return_value = {"status": "DELETING"}

        # Mock get_memory to raise different ClientError
        error_response = {"Error": {"Code": "ValidationException", "Message": "Invalid memory ID"}}
        mock_control_plane_client.get_memory.side_effect = ClientError(error_response, "GetMemory")

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    try:
                        manager.delete_memory_and_wait("mem-123", max_wait=60, poll_interval=5)
                        raise AssertionError("ClientError was not raised")
                    except ClientError as e:
                        assert "ValidationException" in str(e)


def test_update_memory_strategies_missing_strategy_id():
    """Test update_memory_strategies with missing strategyId in modify_strategies."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                # Missing strategyId in modify strategy
                modify_strategies = [{"description": "Updated description"}]
                manager.update_memory_strategies(memory_id="mem-123", modify_strategies=modify_strategies)
                raise AssertionError("ValueError was not raised")
            except ValueError as e:
                assert "Each modify strategy must include strategyId" in str(e)


def test_update_memory_strategies_strategy_not_found():
    """Test update_memory_strategies when strategy to modify is not found."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory_strategies to return empty list
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"memoryId": "mem-123", "status": "ACTIVE", "memoryStrategies": []}
        }

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                modify_strategies = [{"strategyId": "nonexistent-strat", "description": "Updated description"}]
                manager.update_memory_strategies(memory_id="mem-123", modify_strategies=modify_strategies)
                raise AssertionError("ValueError was not raised")
            except ValueError as e:
                assert "Strategy nonexistent-strat not found in memory mem-123" in str(e)


def test_update_memory_strategies_no_operations():
    """Test update_memory_strategies with no operations provided."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                # No operations provided
                manager.update_memory_strategies(memory_id="mem-123")
                raise AssertionError("ValueError was not raised")
            except ValueError as e:
                assert "No strategy operations provided" in str(e)


def test_getattr_method_forwarding():
    """Test __getattr__ method forwarding to control plane client."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the control plane client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock a method that exists in allowed methods
        mock_control_plane_client.create_memory = MagicMock(return_value={"memory": {"id": "test"}})

        # Test method forwarding
        result = manager.create_memory
        assert callable(result)

        # Verify the method is the same as the client method
        assert result == mock_control_plane_client.create_memory


def test_getattr_method_not_allowed():
    """Test __getattr__ with method not in allowed list."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the control plane client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock a method that exists but is not in allowed methods
        mock_control_plane_client.some_other_method = MagicMock()

        try:
            _ = manager.some_other_method
            raise AssertionError("AttributeError was not raised")
        except AttributeError as e:
            assert "object has no attribute 'some_other_method'" in str(e)


def test_validate_namespace_with_invalid_template():
    """Test _validate_namespace with invalid template variables."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test namespace with invalid template variables (should log warning)
        with patch("bedrock_agentcore_starter_toolkit.operations.memory.manager.logger") as mock_logger:
            result = manager._validate_namespace("invalid/{unknownVar}")
            assert result
            mock_logger.warning.assert_called_once_with(
                "Namespace with templates should contain valid variables: %s", "invalid/{unknownVar}"
            )


def test_validate_strategy_config_with_namespaces():
    """Test _validate_strategy_config with namespaces."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock _validate_namespace to track calls
        with patch.object(manager, "_validate_namespace", return_value=True) as mock_validate:
            strategy = {
                "semanticMemoryStrategy": {
                    "name": "Test Strategy",
                    "namespaces": ["custom/{actorId}", "preferences/{sessionId}"],
                }
            }

            manager._validate_strategy_config(strategy, "semanticMemoryStrategy")

            # Should validate each namespace
            assert mock_validate.call_count == 2
            mock_validate.assert_any_call("custom/{actorId}")
            mock_validate.assert_any_call("preferences/{sessionId}")


def test_wrap_configuration_consolidation_passthrough():
    """Test _wrap_configuration when consolidation doesn't need wrapping."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test config where consolidation doesn't have raw keys that need wrapping
        config = {"consolidation": {"modelId": "test-model", "customConfig": "value"}}

        manager._wrap_configuration(config, "SEMANTIC", None)

        # The method only returns wrapped configs, so consolidation may not be present
        # if it doesn't need wrapping. This is the expected behavior.
        # Let's test with a config that does get wrapped
        config_with_raw_keys = {"consolidation": {"triggerEveryNMessages": 10, "modelId": "test-model"}}

        wrapped_with_raw = manager._wrap_configuration(config_with_raw_keys, "SUMMARIZATION", None)

        # This should be wrapped since SUMMARIZATION strategy with triggerEveryNMessages
        assert "consolidation" in wrapped_with_raw


def test_create_memory_and_wait_memory_id_none():
    """Test _create_memory_and_wait when memory.id is None."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response with None id
        mock_memory = Memory({"status": "CREATING"})  # No id field

        with patch.object(manager, "_create_memory", return_value=mock_memory):
            # Mock get_memory to return ACTIVE immediately
            mock_control_plane_client.get_memory.return_value = {"memory": {"status": "ACTIVE"}}

            with patch("time.time", return_value=0):
                with patch("time.sleep"):
                    result = manager._create_memory_and_wait(
                        name="TestMemory",
                        strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                        max_wait=300,
                        poll_interval=10,
                    )

                    # The result should be the Memory object from get_memory response, not mock_memory
                    assert result["status"] == "ACTIVE"
                    assert isinstance(result, Memory)


def test_create_memory_and_wait_debug_logging():
    """Test _create_memory_and_wait debug logging during status checks."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "test-mem-debug", "status": "CREATING"}
        }

        # Mock _wait_for_memory_active to return immediately with ACTIVE memory
        mock_memory = Memory({"id": "test-mem-debug", "status": "ACTIVE"})
        with patch.object(manager, "_wait_for_memory_active", return_value=mock_memory):
            with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                result = manager._create_memory_and_wait(
                    name="TestMemory",
                    strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                    max_wait=300,
                    poll_interval=10,
                )

                # Verify it completed successfully
                assert result["id"] == "test-mem-debug"
                assert result["status"] == "ACTIVE"


def test_get_memory_client_error():
    """Test get_memory with ClientError."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock ClientError
        error_response = {"Error": {"Code": "ResourceNotFoundException", "Message": "Memory not found"}}
        mock_control_plane_client.get_memory.side_effect = ClientError(error_response, "GetMemory")

        try:
            manager.get_memory("nonexistent-mem-123")
            raise AssertionError("ClientError was not raised")
        except ClientError as e:
            assert "ResourceNotFoundException" in str(e)


def test_add_semantic_strategy_with_namespaces():
    """Test add_semantic_strategy with namespaces parameter."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory for strategy retrieval
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-123", "memoryStrategies": []}}

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test add_semantic_strategy with namespaces
            manager.add_semantic_strategy(
                memory_id="mem-123",
                name="Test Semantic Strategy",
                description="Test description",
                namespaces=["custom/{actorId}/{sessionId}"],
            )

            assert mock_control_plane_client.update_memory.called

            # Verify strategy was added with namespaces
            args, kwargs = mock_control_plane_client.update_memory.call_args
            add_strategies = kwargs["memoryStrategies"]["addMemoryStrategies"]
            strategy = add_strategies[0]["semanticMemoryStrategy"]
            assert strategy["namespaces"] == ["custom/{actorId}/{sessionId}"]


def test_add_summary_strategy_with_namespaces():
    """Test add_summary_strategy with namespaces parameter."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory for strategy retrieval
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-456", "memoryStrategies": []}}

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-456", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test add_summary_strategy with namespaces
            manager.add_summary_strategy(
                memory_id="mem-456",
                name="Test Summary Strategy",
                description="Test description",
                namespaces=["summaries/{actorId}"],
            )

            assert mock_control_plane_client.update_memory.called

            # Verify strategy was added with namespaces
            args, kwargs = mock_control_plane_client.update_memory.call_args
            add_strategies = kwargs["memoryStrategies"]["addMemoryStrategies"]
            strategy = add_strategies[0]["summaryMemoryStrategy"]
            assert strategy["namespaces"] == ["summaries/{actorId}"]


def test_delete_memory_and_wait_debug_logging():
    """Test delete_memory_and_wait debug logging during waiting."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock delete response
        mock_control_plane_client.delete_memory.return_value = {"status": "DELETING"}

        # Mock get_memory to succeed first, then raise ResourceNotFoundException
        get_memory_responses = [
            {"memory": {"memoryId": "mem-123", "status": "DELETING"}},  # First call - still exists
            ClientError({"Error": {"Code": "ResourceNotFoundException", "Message": "Memory not found"}}, "GetMemory"),
        ]
        mock_control_plane_client.get_memory.side_effect = get_memory_responses

        with patch("time.time", side_effect=[0, 0, 0, 5, 5]):  # Simulate time passing
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    with patch("bedrock_agentcore_starter_toolkit.operations.memory.manager.logger") as mock_logger:
                        result = manager.delete_memory_and_wait("mem-123", max_wait=60, poll_interval=5)

                        assert result["status"] == "DELETING"
                        # Should have logged debug message about memory still existing
                        mock_logger.debug.assert_called()


def test_modify_strategy_with_configuration():
    """Test modify_strategy with configuration parameter."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory_strategies to return existing strategies
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "memoryId": "mem-123",
                "status": "ACTIVE",
                "memoryStrategies": [
                    {"strategyId": "strat-789", "memoryStrategyType": "SEMANTIC", "name": "Test Strategy"}
                ],
            }
        }

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test modify_strategy with configuration
            configuration = {"extraction": {"modelId": "new-model"}}
            manager.modify_strategy(
                memory_id="mem-123",
                strategy_id="strat-789",
                description="Modified description",
                namespaces=["custom/namespace"],
                configuration=configuration,
            )

            assert mock_control_plane_client.update_memory.called

            # Verify configuration was included
            args, kwargs = mock_control_plane_client.update_memory.call_args
            modified_strategy = kwargs["memoryStrategies"]["modifyMemoryStrategies"][0]
            assert modified_strategy["configuration"] == configuration


def test_update_memory_strategies_with_configuration_wrapping():
    """Test update_memory_strategies with configuration that needs wrapping."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory_strategies to return existing strategies with configuration
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "memoryId": "mem-123",
                "status": "ACTIVE",
                "memoryStrategies": [
                    {
                        "strategyId": "strat-789",
                        "memoryStrategyType": "CUSTOM",
                        "name": "Custom Strategy",
                        "configuration": {"type": "SEMANTIC_OVERRIDE"},
                    }
                ],
            }
        }

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            # Test modifying strategy with configuration that needs wrapping
            modify_strategies = [
                {
                    "strategyId": "strat-789",
                    "configuration": {"extraction": {"triggerEveryNMessages": 5, "modelId": "test-model"}},
                }
            ]
            manager.update_memory_strategies(memory_id="mem-123", modify_strategies=modify_strategies)

            assert mock_control_plane_client.update_memory.called

            # Verify configuration was wrapped
            args, kwargs = mock_control_plane_client.update_memory.call_args
            modified_strategy = kwargs["memoryStrategies"]["modifyMemoryStrategies"][0]
            assert "configuration" in modified_strategy


# Tests for get_or_create_memory function
def test_get_or_create_memory_creates_new_memory():
    """Test get_or_create_memory when no existing memory is found."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return empty list (no existing memory)
        mock_control_plane_client.list_memories.return_value = {"memories": [], "nextToken": None}

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "mem-new-123", "status": "CREATING"}}

        # Mock get_memory to return ACTIVE status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "mem-new-123", "status": "ACTIVE", "name": "TestMemory"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test get_or_create_memory
                    result = manager.get_or_create_memory(
                        name="TestMemory",
                        strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                        description="Test description",
                    )

                    assert result.id == "mem-new-123"
                    assert isinstance(result, Memory)

                    # Verify list_memories was called to check for existing memory
                    assert mock_control_plane_client.list_memories.called

                    # Verify create_memory was called since no existing memory found
                    assert mock_control_plane_client.create_memory.called


def test_get_or_create_memory_returns_existing_memory():
    """Test get_or_create_memory when existing memory is found with matching strategies."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return existing memory with matching name pattern
        existing_memories = [
            {"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"},
            {"id": "OtherMemory-def456", "name": "OtherMemory", "status": "ACTIVE"},
        ]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to return the existing memory details with matching strategies
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "id": "TestMemory-abc123",
                "name": "TestMemory",
                "status": "ACTIVE",
                "strategies": [{"type": "SEMANTIC", "name": "TestStrategy", "description": "Test description"}],
            }
        }

        # Test get_or_create_memory with matching strategy (same name and description)
        result = manager.get_or_create_memory(
            name="TestMemory",
            strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy", "description": "Test description"}}],
            description="Test description",
        )

        assert result.id == "TestMemory-abc123"
        assert isinstance(result, Memory)

        # Verify list_memories was called to check for existing memory
        assert mock_control_plane_client.list_memories.called

        # Verify get_memory was called to fetch existing memory details
        assert mock_control_plane_client.get_memory.called
        args, kwargs = mock_control_plane_client.get_memory.call_args
        assert kwargs["memoryId"] == "TestMemory-abc123"

        # Verify create_memory was NOT called since existing memory was found
        assert not mock_control_plane_client.create_memory.called


def test_get_or_create_memory_with_minimal_parameters():
    """Test get_or_create_memory with minimal parameters."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return empty list
        mock_control_plane_client.list_memories.return_value = {"memories": [], "nextToken": None}

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "mem-minimal-456", "status": "CREATING"}
        }

        # Mock get_memory to return ACTIVE status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "mem-minimal-456", "status": "ACTIVE", "name": "MinimalMemory"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test get_or_create_memory with only name
                    result = manager.get_or_create_memory(name="MinimalMemory")

                    assert result.id == "mem-minimal-456"
                    assert isinstance(result, Memory)

                    # Verify create_memory was called with default parameters
                    assert mock_control_plane_client.create_memory.called
                    args, kwargs = mock_control_plane_client.create_memory.call_args
                    assert kwargs["name"] == "MinimalMemory"
                    assert kwargs["eventExpiryDuration"] == 90  # default
                    assert kwargs["memoryStrategies"] == []  # empty list processed


def test_get_or_create_memory_with_all_parameters():
    """Test get_or_create_memory with all optional parameters."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return empty list
        mock_control_plane_client.list_memories.return_value = {"memories": [], "nextToken": None}

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "mem-full-789", "status": "CREATING"}}

        # Mock get_memory to return ACTIVE status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "mem-full-789", "status": "ACTIVE", "name": "FullMemory"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test get_or_create_memory with all parameters
                    result = manager.get_or_create_memory(
                        name="FullMemory",
                        strategies=[{StrategyType.SEMANTIC.value: {"name": "FullStrategy"}}],
                        description="Full test description",
                        event_expiry_days=120,
                        memory_execution_role_arn="arn:aws:iam::123456789012:role/MemoryRole",
                    )

                    assert result.id == "mem-full-789"
                    assert isinstance(result, Memory)

                    # Verify create_memory was called with all parameters
                    assert mock_control_plane_client.create_memory.called
                    args, kwargs = mock_control_plane_client.create_memory.call_args
                    assert kwargs["name"] == "FullMemory"
                    assert kwargs["description"] == "Full test description"
                    assert kwargs["eventExpiryDuration"] == 120
                    assert kwargs["memoryExecutionRoleArn"] == "arn:aws:iam::123456789012:role/MemoryRole"


def test_get_or_create_memory_client_error_during_list():
    """Test get_or_create_memory when ClientError occurs during list_memories."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to raise ClientError
        error_response = {"Error": {"Code": "AccessDeniedException", "Message": "Insufficient permissions"}}
        mock_control_plane_client.list_memories.side_effect = ClientError(error_response, "ListMemories")

        try:
            manager.get_or_create_memory(name="ErrorMemory")
            raise AssertionError("ClientError was not raised")
        except ClientError as e:
            assert "AccessDeniedException" in str(e)


def test_get_or_create_memory_client_error_during_create():
    """Test get_or_create_memory when ClientError occurs during memory creation."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return empty list
        mock_control_plane_client.list_memories.return_value = {"memories": [], "nextToken": None}

        # Mock create_memory to raise ClientError
        error_response = {"Error": {"Code": "ValidationException", "Message": "Invalid parameter"}}
        mock_control_plane_client.create_memory.side_effect = ClientError(error_response, "CreateMemory")

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                manager.get_or_create_memory(name="ErrorMemory")
                raise AssertionError("ClientError was not raised")
            except ClientError as e:
                assert "ValidationException" in str(e)


def test_get_or_create_memory_client_error_during_get():
    """Test get_or_create_memory when ClientError occurs during get_memory for existing memory."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return existing memory
        existing_memories = [{"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"}]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to raise ClientError
        error_response = {"Error": {"Code": "ResourceNotFoundException", "Message": "Memory not found"}}
        mock_control_plane_client.get_memory.side_effect = ClientError(error_response, "GetMemory")

        try:
            manager.get_or_create_memory(name="TestMemory")
            raise AssertionError("ClientError was not raised")
        except ClientError as e:
            assert "ResourceNotFoundException" in str(e)


def test_get_or_create_memory_creation_timeout():
    """Test get_or_create_memory when memory creation times out."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return empty list
        mock_control_plane_client.list_memories.return_value = {"memories": [], "nextToken": None}

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "mem-timeout-999", "status": "CREATING"}
        }

        # Mock _wait_for_memory_active to raise TimeoutError immediately
        with patch.object(
            manager,
            "_wait_for_memory_active",
            side_effect=TimeoutError(
                "Memory test-mem-timeout did not return to ACTIVE state "
                "with all strategies in terminal states within 300 seconds"
            ),
        ):
            with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                try:
                    manager.get_or_create_memory(name="TimeoutMemory")
                    raise AssertionError("TimeoutError was not raised")
                except TimeoutError as e:
                    assert "did not return to ACTIVE state with all strategies in terminal states" in str(e)


def test_get_or_create_memory_creation_failure():
    """Test get_or_create_memory when memory creation fails."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return empty list
        mock_control_plane_client.list_memories.return_value = {"memories": [], "nextToken": None}

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "mem-failed-888", "status": "CREATING"}
        }

        # Mock get_memory to return FAILED status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "mem-failed-888", "status": "FAILED", "failureReason": "Configuration error"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    try:
                        manager.get_or_create_memory(name="FailedMemory")
                        raise AssertionError("RuntimeError was not raised")
                    except RuntimeError as e:
                        # Changed: Error message is "Memory update failed" not "Memory creation failed"
                        assert "Memory update failed: Configuration error" in str(e)


def test_get_or_create_memory_multiple_matching_memories():
    """Test get_or_create_memory when multiple memories match the name pattern."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return multiple memories with matching pattern
        existing_memories = [
            {"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"},
            {"id": "TestMemory-def456", "name": "TestMemory", "status": "ACTIVE"},
            {"id": "OtherMemory-ghi789", "name": "OtherMemory", "status": "ACTIVE"},
        ]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to return the first matching memory
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"}
        }

        # Test get_or_create_memory
        result = manager.get_or_create_memory(name="TestMemory")

        assert result.id == "TestMemory-abc123"
        assert isinstance(result, Memory)

        # Verify get_memory was called with the first matching memory ID
        assert mock_control_plane_client.get_memory.called
        args, kwargs = mock_control_plane_client.get_memory.call_args
        assert kwargs["memoryId"] == "TestMemory-abc123"


def test_get_or_create_memory_no_matching_pattern():
    """Test get_or_create_memory when memories exist but none match the name pattern."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return memories that don't match the pattern
        existing_memories = [
            {"id": "OtherMemory-abc123", "name": "OtherMemory", "status": "ACTIVE"},
            {"id": "DifferentMemory-def456", "name": "DifferentMemory", "status": "ACTIVE"},
        ]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "mem-new-777", "status": "CREATING"}}

        # Mock get_memory to return ACTIVE status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "mem-new-777", "status": "ACTIVE", "name": "TestMemory"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test get_or_create_memory
                    result = manager.get_or_create_memory(name="TestMemory")

                    assert result.id == "mem-new-777"
                    assert isinstance(result, Memory)

                    # Verify create_memory was called since no matching pattern found
                    assert mock_control_plane_client.create_memory.called


def test_get_or_create_memory_with_strategies():
    """Test get_or_create_memory with various strategy configurations."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return empty list
        mock_control_plane_client.list_memories.return_value = {"memories": [], "nextToken": None}

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {
            "memory": {"id": "mem-strategies-555", "status": "CREATING"}
        }

        # Mock get_memory to return ACTIVE status
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "mem-strategies-555", "status": "ACTIVE", "name": "StrategiesMemory"}
        }

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    # Test get_or_create_memory with multiple strategies
                    strategies = [
                        {StrategyType.SEMANTIC.value: {"name": "SemanticStrategy"}},
                        {StrategyType.SUMMARY.value: {"name": "SummaryStrategy"}},
                    ]
                    result = manager.get_or_create_memory(name="StrategiesMemory", strategies=strategies)

                    assert result.id == "mem-strategies-555"
                    assert isinstance(result, Memory)

                    # Verify create_memory was called with strategies
                    assert mock_control_plane_client.create_memory.called
                    args, kwargs = mock_control_plane_client.create_memory.call_args
                    assert len(kwargs["memoryStrategies"]) == 2


def test_get_or_create_memory_exception_handling():
    """Test get_or_create_memory handles unexpected exceptions."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to raise unexpected exception
        mock_control_plane_client.list_memories.side_effect = Exception("Unexpected error")

        try:
            manager.get_or_create_memory(name="ExceptionMemory")
            raise AssertionError("Exception was not raised")
        except Exception as e:
            assert "Unexpected error" in str(e)


def test_get_or_create_memory_strategy_validation_success():
    """Test get_or_create_memory strategy validation when strategies match."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return existing memory
        existing_memories = [{"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"}]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to return memory with matching strategies (same name)
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "id": "TestMemory-abc123",
                "name": "TestMemory",
                "status": "ACTIVE",
                "strategies": [{"type": "SEMANTIC", "name": "TestStrategy", "description": "Test description"}],
            }
        }

        # Test get_or_create_memory with matching strategy (same name and description)
        strategies = [{StrategyType.SEMANTIC.value: {"name": "TestStrategy", "description": "Test description"}}]
        result = manager.get_or_create_memory(name="TestMemory", strategies=strategies)

        assert result.id == "TestMemory-abc123"
        assert isinstance(result, Memory)

        # Verify get_memory was called
        assert mock_control_plane_client.get_memory.called


def test_get_or_create_memory_strategy_validation_mismatch():
    """Test get_or_create_memory strategy validation when strategies don't match."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return existing memory
        existing_memories = [{"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"}]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to return memory with different strategies
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "id": "TestMemory-abc123",
                "name": "TestMemory",
                "status": "ACTIVE",
                "strategies": [{"type": "SUMMARIZATION", "name": "SummaryStrategy"}],
            }
        }

        # Test get_or_create_memory with mismatched strategy
        strategies = [{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}]

        try:
            manager.get_or_create_memory(name="TestMemory", strategies=strategies)
            raise AssertionError("ValueError was not raised")
        except ValueError as e:
            assert "Strategy mismatch" in str(e)
            # The error should mention the type mismatch since we're comparing SUMMARIZATION vs SEMANTIC
            assert ("type: value mismatch" in str(e) and "SUMMARIZATION" in str(e) and "SEMANTIC" in str(e)) or (
                "name: value mismatch" in str(e) and "SummaryStrategy" in str(e) and "TestStrategy" in str(e)
            )


def test_get_or_create_memory_strategy_validation_multiple_strategies():
    """Test get_or_create_memory strategy validation with multiple strategies."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return existing memory
        existing_memories = [{"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"}]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to return memory with multiple strategies (matching names)
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "id": "TestMemory-abc123",
                "name": "TestMemory",
                "status": "ACTIVE",
                "strategies": [
                    {"type": "SEMANTIC", "name": "SemanticStrategy", "description": "Semantic description"},
                    {"type": "SUMMARIZATION", "name": "SummaryStrategy", "description": "Summary description"},
                ],
            }
        }

        # Test get_or_create_memory with matching multiple strategies (same names and descriptions)
        strategies = [
            {StrategyType.SEMANTIC.value: {"name": "SemanticStrategy", "description": "Semantic description"}},
            {StrategyType.SUMMARY.value: {"name": "SummaryStrategy", "description": "Summary description"}},
        ]
        result = manager.get_or_create_memory(name="TestMemory", strategies=strategies)

        assert result.id == "TestMemory-abc123"
        assert isinstance(result, Memory)


def test_get_or_create_memory_strategy_validation_no_existing_strategies():
    """Test get_or_create_memory strategy validation when existing memory has no strategies."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return existing memory
        existing_memories = [{"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"}]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to return memory with no strategies
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE", "strategies": []}
        }

        # Test get_or_create_memory with strategies when existing has none
        strategies = [{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}]

        try:
            manager.get_or_create_memory(name="TestMemory", strategies=strategies)
            raise AssertionError("ValueError was not raised")
        except ValueError as e:
            assert "Strategy mismatch" in str(e)
            assert "Strategy count mismatch" in str(e)
            assert "0 strategies" in str(e)
            assert "1 strategies were requested" in str(e)


def test_get_or_create_memory_no_strategy_validation_when_none_provided():
    """Test get_or_create_memory skips validation when no strategies provided."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock list_memories to return existing memory
        existing_memories = [{"id": "TestMemory-abc123", "name": "TestMemory", "status": "ACTIVE"}]
        mock_control_plane_client.list_memories.return_value = {"memories": existing_memories, "nextToken": None}

        # Mock get_memory to return memory with any strategies
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "id": "TestMemory-abc123",
                "name": "TestMemory",
                "status": "ACTIVE",
                "strategies": [{"type": "SUMMARIZATION", "name": "SummaryStrategy"}],
            }
        }

        # Test get_or_create_memory without providing strategies - should not validate
        result = manager.get_or_create_memory(name="TestMemory")

        assert result.id == "TestMemory-abc123"
        assert isinstance(result, Memory)

        # Should not raise any validation error
