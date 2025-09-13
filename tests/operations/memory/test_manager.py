"""Unit tests for Memory Client - no external connections."""

import time
import uuid
import warnings
from datetime import datetime
from unittest.mock import MagicMock, patch


import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager, Memory
from bedrock_agentcore_starter_toolkit.operations.memory.models.MemoryStrategy import MemoryStrategy
from bedrock_agentcore_starter_toolkit.operations.memory.models.MemorySummary import MemorySummary
from bedrock_agentcore_starter_toolkit.operations.memory.constants import (
    StrategyType,
)

def test_manager_initialization():
    """Test client initialization."""
    with patch("boto3.client") as mock_boto_client:
        # Setup the mock to return a consistent region_name
        mock_client_instance = MagicMock()
        mock_client_instance.meta.region_name = "us-west-2"
        mock_boto_client.return_value = mock_client_instance

        manager = MemoryManager(region_name="us-west-2")

        # Check that the region was set correctly and boto3.client was called once (only control plane)
        assert manager.region_name == "us-west-2"
        assert mock_boto_client.call_count == 1
        
        # Verify the correct service was called
        mock_boto_client.assert_called_with("bedrock-agentcore-control", region_name="us-west-2")


def test_manager_initialization_region_mismatch():
    """Test client initialization with region mismatch warning."""

    with patch("boto3.client") as mock_boto_client:
        # First test - environment variable takes precedence
        with patch("boto3.Session") as mock_session:
            # Mock the session instance to simulate AWS_REGION=us-east-1
            mock_session_instance = MagicMock()
            mock_session_instance.region_name = "us-east-1"
            mock_session.return_value = mock_session_instance

            # Mock the boto client
            mock_client_instance = MagicMock()
            mock_client_instance.meta.region_name = "us-east-1"
            mock_boto_client.return_value = mock_client_instance

            # When region_name is provided, environment variable should still take precedence
            client1 = MemoryManager(region_name="us-west-2")
            assert client1.region_name == "us-west-2"

        # Second test - no environment variable, explicit param is used
        with patch("boto3.Session") as mock_session:
            # Mock the session instance to simulate no AWS_REGION set
            mock_session_instance = MagicMock()
            mock_session_instance.region_name = None
            mock_session.return_value = mock_session_instance

            # Mock the boto client
            mock_client_instance = MagicMock()
            mock_client_instance.meta.region_name = "us-west-2"
            mock_boto_client.return_value = mock_client_instance

            # When AWS_REGION is not set, explicitly provided region should be used
            client2 = MemoryManager(region_name="us-west-2")
            assert client2.region_name == "us-west-2"


def test_namespace_defaults():
    """Test namespace defaults."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test strategy without namespace
        strategies = [{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}]
        processed = manager._add_default_namespaces(strategies)

        assert "namespaces" in processed[0][StrategyType.SEMANTIC.value]


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
            mock_control_plane_client.create_memory.return_value = {"memory": {"id": "test-memory-123", "status": "CREATING"}}

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
                "strategies": [
                    {"strategyId": "strat-123", "type": "SEMANTIC", "name": "Test Strategy"}
                ],
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
            manager.add_semantic_strategy(memory_id="mem-123", name="New Semantic Strategy", description="Test strategy")

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
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "test-mem-timeout", "status": "CREATING"}}

        # Mock get_memory to always return CREATING (never becomes ACTIVE)
        mock_control_plane_client.get_memory.return_value = {"memory": {"id": "test-mem-timeout", "status": "CREATING"}}

        # Mock time to simulate timeout - provide enough values for all time.time() calls
        with patch("time.time", side_effect=[0, 0, 0, 301, 301]):
            with patch("time.sleep"):
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
                        assert "did not become ACTIVE within 300 seconds" in str(e)


def test_create_memory_and_wait_failure():
    """Test failure scenario for create_memory_and_wait."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "test-mem-failed", "status": "CREATING"}}

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
                        assert "Memory creation failed: Configuration error" in str(e)

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
            {"memory": {"memoryId": "mem-123", "status": "CREATING", "memoryStrategies": []}},  # First call - still creating
            {"memory": {"memoryId": "mem-123", "status": "ACTIVE", "memoryStrategies": []}}     # Second call - now active
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
            assert kwargs["memoryStrategies"]["deleteMemoryStrategies"][0]["strategyId"] == "strat-456"


def test_add_strategy_warning():
    """Test add_strategy shows deprecation warning."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock get_memory for strategy retrieval
        mock_control_plane_client.get_memory.return_value = {"memory": {"memoryId": "mem-123", "memoryStrategies": []}}

        # Mock update_memory response
        mock_control_plane_client.update_memory.return_value = {"memory": {"memoryId": "mem-123", "status": "CREATING"}}

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                # Test add_strategy (should show warning)
                strategy = {StrategyType.SEMANTIC.value: {"name": "Test Strategy"}}
                manager.add_strategy(memory_id="mem-123", strategy=strategy)

                # Should have shown a warning
                assert len(w) >= 1
                assert any("may leave memory in CREATING state" in str(warning.message) for warning in w)

                # Verify update_memory was called
                assert mock_control_plane_client.update_memory.called

def test_create_memory_and_wait_client_error():
    """Test create_memory_and_wait with ClientError during status check."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock both clients
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock create_memory response
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "test-mem-error", "status": "CREATING"}}

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

def test_create_or_get_memory_creates_new():
    """Test create_or_get_memory creates new memory when it doesn't exist."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the _control_plane_client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock successful create_memory response
        mock_control_plane_client.create_memory.return_value = {"memory": {"id": "new-memory-123", "status": "CREATING"}}

        # Mock get_memory to return ACTIVE status (for the waiting part)
        mock_control_plane_client.get_memory.return_value = {"memory": {"id": "new-memory-123", "status": "ACTIVE"}}

        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    result = manager.create_or_get_memory(
                        name="TestMemory",
                        strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                    )

                    assert result["id"] == "new-memory-123"
                    assert mock_control_plane_client.create_memory.called


def test_create_or_get_memory_gets_existing():
    """Test create_or_get_memory returns existing memory when it already exists."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the _control_plane_client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock ValidationException for create_memory (memory already exists)
        error_response = {
            "Error": {
                "Code": "ValidationException",
                "Message": "Memory with name 'ExistingMemory' already exists",
            }
        }
        mock_control_plane_client.create_memory.side_effect = ClientError(error_response, "CreateMemory")

        # Mock list_memories response
        mock_control_plane_client.list_memories.return_value = {
            "memories": [{"id": "ExistingMemory-456", "name": "ExistingMemory", "status": "ACTIVE"}],
            "nextToken": None,
        }

        # Mock get_memory response (this is what was missing)
        mock_control_plane_client.get_memory.return_value = {
            "memory": {"id": "ExistingMemory-456", "name": "ExistingMemory", "status": "ACTIVE"}
        }

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            result = manager.create_or_get_memory(
                name="ExistingMemory",
                strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
            )

            assert result["id"] == "ExistingMemory-456"
            assert mock_control_plane_client.create_memory.called
            assert mock_control_plane_client.list_memories.called


def test_create_or_get_memory_other_client_error():
    """Test create_or_get_memory raises other ClientErrors."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the _control_plane_client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock different ClientError (not "already exists")
        error_response = {
            "Error": {
                "Code": "ValidationException",
                "Message": "Invalid parameters",
            }
        }
        mock_control_plane_client.create_memory.side_effect = ClientError(error_response, "CreateMemory")

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                manager.create_or_get_memory(
                    name="TestMemory",
                    strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                )
                raise AssertionError("ClientError was not raised")
            except ClientError as e:
                assert "ValidationException" in str(e)
                assert "Invalid parameters" in str(e)


def test_create_or_get_memory_general_exception():
    """Test create_or_get_memory raises general exceptions."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the _control_plane_client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client

        # Mock general exception
        mock_control_plane_client.create_memory.side_effect = Exception("Unexpected error")

        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            try:
                manager.create_or_get_memory(
                    name="TestMemory",
                    strategies=[{StrategyType.SEMANTIC.value: {"name": "TestStrategy"}}],
                )
                raise AssertionError("Exception was not raised")
            except Exception as e:
                assert "Unexpected error" in str(e)

# Memory class tests
def test_memory_initialization():
    """Test Memory class initialization."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        memory = Memory(memory_data, manager)
        
        assert memory.id == "mem-123"
        assert memory.name == "Test Memory"
        assert memory.status == "ACTIVE"


def test_memory_attribute_access():
    """Test Memory class attribute access patterns."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        memory = Memory(memory_data, manager)
        
        # Test __getattr__
        assert memory.id == "mem-123"
        assert memory.name == "Test Memory"
        
        # Test __getitem__
        assert memory["id"] == "mem-123"
        assert memory["name"] == "Test Memory"
        
        # Test _get method
        assert memory._get("id") == "mem-123"
        assert memory._get("nonexistent", "default") == "default"


def test_memory_validation():
    """Test Memory class validation."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        
        # Test with None memory
        memory = Memory(None, manager)
        try:
            memory.id
            raise AssertionError("ValueError was not raised")
        except ValueError as e:
            assert "Memory object is not properly initialized" in str(e)
        
        # Test with empty memory
        memory = Memory({}, manager)
        try:
            memory.id
            raise AssertionError("ValueError was not raised")
        except ValueError as e:
            assert "Memory object has been deleted or is empty" in str(e)


def test_memory_delete():
    """Test Memory class delete method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        # Mock the manager's delete_memory method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        mock_control_plane_client.delete_memory.return_value = {"status": "DELETING"}
        
        memory = Memory(memory_data, manager)
        
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            result = memory.delete()
            
            assert result["status"] == "DELETING"
            assert mock_control_plane_client.delete_memory.called
            
            # Memory should be emptied after deletion
            try:
                memory.id
                raise AssertionError("ValueError was not raised")
            except ValueError as e:
                assert "Memory object has been deleted or is empty" in str(e)


def test_memory_add_semantic_strategy():
    """Test Memory class add_semantic_strategy method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        # Mock the manager's add_semantic_strategy method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        mock_control_plane_client.update_memory.return_value = {"memory": {"id": "mem-123", "status": "CREATING"}}
        
        memory = Memory(memory_data, manager)
        
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            result = memory.add_semantic_strategy("Test Strategy", "Test description")
            
            assert result == memory  # Should return self
            assert mock_control_plane_client.update_memory.called


def test_memory_get_strategies():
    """Test Memory class get_strategies method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        # Mock the manager's get_memory_strategies method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        mock_control_plane_client.get_memory.return_value = {
            "memory": {
                "id": "mem-123",
                "strategies": [
                    {"strategyId": "strat-123", "type": "SEMANTIC", "name": "Test Strategy"}
                ],
            }
        }
        
        memory = Memory(memory_data, manager)
        strategies = memory.get_strategies()
        
        assert len(strategies) == 1
        assert isinstance(strategies[0], MemoryStrategy)


def test_memory_delete_strategy():
    """Test Memory class delete_strategy method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        # Mock the manager's delete_strategy method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        mock_control_plane_client.get_memory.return_value = {"memory": {"id": "mem-123", "strategies": []}}
        mock_control_plane_client.update_memory.return_value = {"memory": {"id": "mem-123", "status": "ACTIVE"}}
        
        memory = Memory(memory_data, manager)
        
        with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
            result = memory.delete_strategy("strat-456")
            
            assert result == memory  # Should return self
            assert mock_control_plane_client.update_memory.called


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


# Test missing MemoryManager methods that delegate to boto3
def test_memory_manager_getattr():
    """Test MemoryManager __getattr__ delegation."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Mock the control plane client
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        
        # Test that methods are delegated to control plane client
        mock_control_plane_client.some_method.return_value = "test_result"
        
        result = manager.some_method("arg1", kwarg1="value1")
        
        assert result == "test_result"
        mock_control_plane_client.some_method.assert_called_with("arg1", kwarg1="value1")


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
    strategy_data = {
        "strategyId": "strat-123",
        "type": "SEMANTIC",
        "name": "Test Strategy"
    }
    
    strategy = MemoryStrategy(strategy_data)
    
    assert strategy.strategyId == "strat-123"
    assert strategy.type == "SEMANTIC"
    assert strategy.name == "Test Strategy"
    assert strategy["strategyId"] == "strat-123"
    assert str(strategy) == str(strategy_data)


def test_memory_summary_model():
    """Test MemorySummary model."""
    summary_data = {
        "id": "mem-123",
        "name": "Test Memory",
        "status": "ACTIVE"
    }
    
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
        assert manager._validate_namespace("custom/{actorId}/{sessionId}") == True
        assert manager._validate_namespace("preferences/{actorId}") == True
        assert manager._validate_namespace("strategy/{strategyId}") == True
        assert manager._validate_namespace("simple/namespace") == True
        
        # Test namespace with invalid template variables (should log warning)
        with patch("bedrock_agentcore_starter_toolkit.operations.memory.manager.logger") as mock_logger:
            assert manager._validate_namespace("invalid/{unknownVar}") == True
            mock_logger.warning.assert_called_once()


def test_validate_strategy_config():
    """Test _validate_strategy_config functionality."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        
        # Mock _validate_namespace to track calls
        with patch.object(manager, '_validate_namespace', return_value=True) as mock_validate:
            strategy = {
                "semanticMemoryStrategy": {
                    "name": "Test Strategy",
                    "namespaces": ["custom/{actorId}", "preferences/{sessionId}"]
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
            {"strategyId": "strat-2", "status": "ACTIVE", "name": "Strategy 2"}
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal == True
        assert statuses == ["ACTIVE", "ACTIVE"]
        assert failed_names == []
        
        # Test some strategies still creating
        strategies = [
            {"strategyId": "strat-1", "status": "ACTIVE", "name": "Strategy 1"},
            {"strategyId": "strat-2", "status": "CREATING", "name": "Strategy 2"}
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal == False
        assert statuses == ["ACTIVE", "CREATING"]
        assert failed_names == []
        
        # Test some strategies failed
        strategies = [
            {"strategyId": "strat-1", "status": "ACTIVE", "name": "Strategy 1"},
            {"strategyId": "strat-2", "status": "FAILED", "name": "Strategy 2"}
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal == True
        assert statuses == ["ACTIVE", "FAILED"]
        assert failed_names == ["Strategy 2"]
        
        # Test strategy without name (uses strategyId)
        strategies = [
            {"strategyId": "strat-1", "status": "FAILED"}
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal == True
        assert statuses == ["FAILED"]
        assert failed_names == ["strat-1"]
        
        # Test strategy without name or strategyId (uses "unknown")
        strategies = [
            {"status": "FAILED"}
        ]
        all_terminal, statuses, failed_names = manager._check_strategies_terminal_state(strategies)
        assert all_terminal == True
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
                    {"strategyId": "strat-2", "status": "FAILED", "name": "Bad Strategy"}
                ]
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
                    "strategies": [
                        {"strategyId": "strat-1", "status": "CREATING", "name": "Strategy 1"}
                    ]
                }
            },
            {
                "memory": {
                    "memoryId": "mem-123", 
                    "status": "ACTIVE",
                    "strategies": [
                        {"strategyId": "strat-1", "status": "ACTIVE", "name": "Strategy 1"}
                    ]
                }
            }
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
                "strategies": [
                    {"strategyId": "strat-1", "status": "CREATING", "name": "Strategy 1"}
                ]
            }
        }

        # Mock time to simulate timeout - provide enough values for all time.time() calls
        # The method calls: start_time, while condition check, elapsed calc, while condition check (timeout), elapsed calc
        with patch("time.time", side_effect=[0, 0, 0, 61, 61]):
            with patch("time.sleep"):
                try:
                    manager._wait_for_memory_active("mem-123", max_wait=60, poll_interval=5)
                    raise AssertionError("TimeoutError was not raised")
                except TimeoutError as e:
                    assert "did not return to ACTIVE state with all strategies in terminal states within 60 seconds" in str(e)


def test_wrap_configuration_summary_strategy():
    """Test _wrap_configuration with SUMMARIZATION strategy type."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")

        # Test consolidation configuration for SUMMARIZATION strategy
        config = {
            "consolidation": {"triggerEveryNMessages": 10}
        }

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
                "preferenceType": "communication"
            },
            "consolidation": {
                "appendToPrompt": "Consolidate user preferences",
                "modelId": "user-pref-model"
            }
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
        config = {
            "consolidation": {
                "appendToPrompt": "Create custom summary",
                "modelId": "summary-model"
            }
        }

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
        config = {
            "extraction": {"modelId": "test-model"},
            "consolidation": {"modelId": "test-model"}
        }

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
                memory_execution_role_arn="arn:aws:iam::123456789012:role/MemoryRole"
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

            # Should handle memoryId field - access via dict since Memory class expects 'id'
            assert result._memory.get("memoryId") == "test-memory-normalized"


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
            mock_control_plane_client.create_memory.return_value = {
                "memory": {"status": "CREATING"}
            }

            result = manager._create_memory(name="NoIdMemory")

            # Should handle missing id gracefully - access via dict since Memory class expects 'id'
            assert result._memory.get("id", result._memory.get("memoryId", "unknown")) == "unknown"


# Additional Memory class tests for better coverage
def test_memory_repr():
    """Test Memory class __repr__ method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        memory = Memory(memory_data, manager)
        
        # __repr__ should return the string representation of the underlying dict
        assert repr(memory) == repr(memory_data)


def test_memory_get_method():
    """Test Memory class _get method access."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        memory = Memory(memory_data, manager)
        
        # Test accessing _get method through __getattr__
        get_method = memory.get
        assert get_method("id") == "mem-123"
        assert get_method("nonexistent", "default") == "default"


def test_memory_add_summary_strategy_and_wait():
    """Test Memory class add_summary_strategy_and_wait method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        # Mock the manager's method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        mock_control_plane_client.update_memory.return_value = {"memory": {"id": "mem-123", "status": "CREATING"}}
        mock_control_plane_client.get_memory.return_value = {"memory": {"id": "mem-123", "status": "ACTIVE"}}
        
        memory = Memory(memory_data, manager)
        
        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    result = memory.add_summary_strategy_and_wait("Test Summary Strategy", "Test description")
                    
                    assert result == memory  # Should return self
                    assert mock_control_plane_client.update_memory.called
                    assert mock_control_plane_client.get_memory.called


def test_memory_add_user_preference_strategy_and_wait():
    """Test Memory class add_user_preference_strategy_and_wait method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        # Mock the manager's method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        mock_control_plane_client.update_memory.return_value = {"memory": {"id": "mem-123", "status": "CREATING"}}
        mock_control_plane_client.get_memory.return_value = {"memory": {"id": "mem-123", "status": "ACTIVE"}}
        
        memory = Memory(memory_data, manager)
        
        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    result = memory.add_user_preference_strategy_and_wait("Test User Pref Strategy", "Test description")
                    
                    assert result == memory  # Should return self
                    assert mock_control_plane_client.update_memory.called
                    assert mock_control_plane_client.get_memory.called


def test_memory_add_custom_semantic_strategy_and_wait():
    """Test Memory class add_custom_semantic_strategy_and_wait method."""
    with patch("boto3.client"):
        manager = MemoryManager(region_name="us-east-1")
        memory_data = {"id": "mem-123", "name": "Test Memory", "status": "ACTIVE"}
        
        # Mock the manager's method
        mock_control_plane_client = MagicMock()
        manager._control_plane_client = mock_control_plane_client
        mock_control_plane_client.update_memory.return_value = {"memory": {"id": "mem-123", "status": "CREATING"}}
        mock_control_plane_client.get_memory.return_value = {"memory": {"id": "mem-123", "status": "ACTIVE"}}
        
        memory = Memory(memory_data, manager)
        
        with patch("time.time", return_value=0):
            with patch("time.sleep"):
                with patch("uuid.uuid4", return_value=uuid.UUID("12345678-1234-5678-1234-567812345678")):
                    extraction_config = {"prompt": "Extract key info", "modelId": "claude-3-sonnet"}
                    consolidation_config = {"prompt": "Consolidate info", "modelId": "claude-3-haiku"}
                    
                    result = memory.add_custom_semantic_strategy_and_wait(
                        "Test Custom Strategy",
                        extraction_config,
                        consolidation_config,
                        "Test description"
                    )
                    
                    assert result == memory  # Should return self
                    assert mock_control_plane_client.update_memory.called
                    assert mock_control_plane_client.get_memory.called


# Additional MemoryStrategy model tests
def test_memory_strategy_get_method():
    """Test MemoryStrategy get method."""
    strategy_data = {
        "strategyId": "strat-123",
        "type": "SEMANTIC",
        "name": "Test Strategy"
    }
    
    strategy = MemoryStrategy(strategy_data)
    
    assert strategy.get("strategyId") == "strat-123"
    assert strategy.get("nonexistent", "default") == "default"


def test_memory_strategy_contains():
    """Test MemoryStrategy __contains__ method."""
    strategy_data = {
        "strategyId": "strat-123",
        "type": "SEMANTIC",
        "name": "Test Strategy"
    }
    
    strategy = MemoryStrategy(strategy_data)
    
    assert "strategyId" in strategy
    assert "nonexistent" not in strategy


def test_memory_strategy_keys_values_items():
    """Test MemoryStrategy keys, values, and items methods."""
    strategy_data = {
        "strategyId": "strat-123",
        "type": "SEMANTIC",
        "name": "Test Strategy"
    }
    
    strategy = MemoryStrategy(strategy_data)
    
    assert list(strategy.keys()) == ["strategyId", "type", "name"]
    assert list(strategy.values()) == ["strat-123", "SEMANTIC", "Test Strategy"]
    assert list(strategy.items()) == [("strategyId", "strat-123"), ("type", "SEMANTIC"), ("name", "Test Strategy")]


# Additional MemorySummary model tests
def test_memory_summary_get_method():
    """Test MemorySummary get method."""
    summary_data = {
        "id": "mem-123",
        "name": "Test Memory",
        "status": "ACTIVE"
    }
    
    summary = MemorySummary(summary_data)
    
    assert summary.get("id") == "mem-123"
    assert summary.get("nonexistent", "default") == "default"


def test_memory_summary_contains():
    """Test MemorySummary __contains__ method."""
    summary_data = {
        "id": "mem-123",
        "name": "Test Memory",
        "status": "ACTIVE"
    }
    
    summary = MemorySummary(summary_data)
    
    assert "id" in summary
    assert "nonexistent" not in summary


def test_memory_summary_keys_values_items():
    """Test MemorySummary keys, values, and items methods."""
    summary_data = {
        "id": "mem-123",
        "name": "Test Memory",
        "status": "ACTIVE"
    }
    
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
            "memory": {
                "memoryId": "mem-123",
                "status": "ACTIVE",
                "memoryStrategies": []
            }
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


if __name__ == "__main__":
    pytest.main(["-v", __file__])
