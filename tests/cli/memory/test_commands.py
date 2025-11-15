"""Unit tests for Memory CLI commands."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.memory.commands import memory_app
from bedrock_agentcore_starter_toolkit.operations.memory.models import Memory, MemorySummary

runner = CliRunner()


@pytest.fixture
def mock_memory_manager():
    """Fixture to create a mocked MemoryManager."""
    with patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager") as mock_manager_class:
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.region_name = "us-west-2"
        yield mock_manager


def test_create_command_basic(mock_memory_manager):
    """Test basic memory create command."""
    # Mock the create response
    mock_memory = Memory({"id": "mem-123", "status": "ACTIVE", "name": "test-memory"})
    mock_memory_manager.create_memory_and_wait.return_value = mock_memory

    result = runner.invoke(memory_app, ["create", "test-memory"])

    assert result.exit_code == 0
    assert "mem-123" in result.stdout
    assert "ACTIVE" in result.stdout
    mock_memory_manager.create_memory_and_wait.assert_called_once()


def test_create_command_with_strategies(mock_memory_manager):
    """Test create command with strategies."""
    mock_memory = Memory({"id": "mem-456", "status": "CREATING", "name": "test-memory"})
    mock_memory_manager.create_memory_and_wait.return_value = mock_memory

    strategies_json = '[{"semanticMemoryStrategy": {"name": "Facts"}}]'
    result = runner.invoke(memory_app, ["create", "test-memory", "--strategies", strategies_json])

    assert result.exit_code == 0
    assert "mem-456" in result.stdout

    # Verify strategies were parsed and passed
    call_args = mock_memory_manager.create_memory_and_wait.call_args
    assert call_args[1]["strategies"] is not None


def test_create_command_with_description(mock_memory_manager):
    """Test create command with description."""
    mock_memory = Memory({"id": "mem-789", "status": "ACTIVE", "name": "test-memory"})
    mock_memory_manager.create_memory_and_wait.return_value = mock_memory

    result = runner.invoke(memory_app, ["create", "test-memory", "--description", "Test description"])

    assert result.exit_code == 0
    call_args = mock_memory_manager.create_memory_and_wait.call_args
    assert call_args[1]["description"] == "Test description"


def test_create_command_no_wait(mock_memory_manager):
    """Test create command with --no-wait flag."""
    mock_memory = Memory({"id": "mem-999", "status": "CREATING", "name": "test-memory"})
    mock_memory_manager._create_memory.return_value = mock_memory

    result = runner.invoke(memory_app, ["create", "test-memory", "--no-wait"])

    assert result.exit_code == 0
    mock_memory_manager._create_memory.assert_called_once()
    mock_memory_manager.create_memory_and_wait.assert_not_called()


def test_create_command_invalid_json(mock_memory_manager):
    """Test create command with invalid JSON strategies."""
    result = runner.invoke(memory_app, ["create", "test-memory", "--strategies", "invalid-json"])

    assert result.exit_code == 1
    assert "Error parsing strategies JSON" in result.stdout


def test_get_command(mock_memory_manager):
    """Test get memory command."""
    mock_memory = Memory(
        {
            "id": "mem-123",
            "name": "test-memory",
            "status": "ACTIVE",
            "description": "Test description",
            "eventExpiryDuration": 90,
            "strategies": [{"name": "Facts", "type": "SEMANTIC"}],
        }
    )
    mock_memory_manager.get_memory.return_value = mock_memory

    result = runner.invoke(memory_app, ["get", "mem-123"])

    assert result.exit_code == 0
    assert "mem-123" in result.stdout
    assert "test-memory" in result.stdout
    assert "ACTIVE" in result.stdout
    mock_memory_manager.get_memory.assert_called_once_with("mem-123")


def test_get_command_with_region(mock_memory_manager):
    """Test get command with custom region."""
    mock_memory = Memory({"id": "mem-123", "name": "test-memory", "status": "ACTIVE"})
    mock_memory_manager.get_memory.return_value = mock_memory

    result = runner.invoke(memory_app, ["get", "mem-123", "--region", "us-east-1"])

    assert result.exit_code == 0
    # Verify MemoryManager was initialized with the correct region
    with patch("bedrock_agentcore_starter_toolkit.cli.memory.commands.MemoryManager") as mock_class:
        runner.invoke(memory_app, ["get", "mem-123", "--region", "us-east-1"])
        mock_class.assert_called_once()
        assert mock_class.call_args[1]["region_name"] == "us-east-1"


def test_list_command(mock_memory_manager):
    """Test list memories command."""
    mock_memories = [
        MemorySummary(
            {
                "id": "mem-1",
                "arn": "arn:aws:bedrock:us-west-2:123456789012:memory/mem-1",
                "status": "ACTIVE",
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-02T00:00:00Z",
            }
        ),
        MemorySummary(
            {
                "id": "mem-2",
                "arn": "arn:aws:bedrock:us-west-2:123456789012:memory/mem-2",
                "status": "ACTIVE",
                "createdAt": "2024-01-03T00:00:00Z",
                "updatedAt": "2024-01-04T00:00:00Z",
            }
        ),
    ]
    mock_memory_manager.list_memories.return_value = mock_memories

    result = runner.invoke(memory_app, ["list"])

    assert result.exit_code == 0
    assert "mem-1" in result.stdout
    assert "mem-2" in result.stdout
    assert "ACTIVE" in result.stdout
    mock_memory_manager.list_memories.assert_called_once()


def test_list_command_empty(mock_memory_manager):
    """Test list command with no memories."""
    mock_memory_manager.list_memories.return_value = []

    result = runner.invoke(memory_app, ["list"])

    assert result.exit_code == 0
    assert "No memories found" in result.stdout


def test_list_command_with_max_results(mock_memory_manager):
    """Test list command with max results."""
    mock_memory_manager.list_memories.return_value = []

    result = runner.invoke(memory_app, ["list", "--max-results", "50"])

    assert result.exit_code == 0
    call_args = mock_memory_manager.list_memories.call_args
    assert call_args[1]["max_results"] == 50


def test_delete_command(mock_memory_manager):
    """Test delete memory command."""
    result = runner.invoke(memory_app, ["delete", "mem-123"])

    assert result.exit_code == 0
    assert "deleted successfully" in result.stdout.lower()
    mock_memory_manager.delete_memory.assert_called_once_with("mem-123")


def test_delete_command_with_wait(mock_memory_manager):
    """Test delete command with --wait flag."""
    result = runner.invoke(memory_app, ["delete", "mem-123", "--wait"])

    assert result.exit_code == 0
    mock_memory_manager.delete_memory_and_wait.assert_called_once()
    mock_memory_manager.delete_memory.assert_not_called()


def test_status_command(mock_memory_manager):
    """Test status command."""
    mock_memory_manager.get_memory_status.return_value = "ACTIVE"

    result = runner.invoke(memory_app, ["status", "mem-123"])

    assert result.exit_code == 0
    assert "ACTIVE" in result.stdout
    assert "mem-123" in result.stdout
    mock_memory_manager.get_memory_status.assert_called_once_with("mem-123")


def test_command_error_handling(mock_memory_manager):
    """Test error handling in commands."""
    mock_memory_manager.get_memory.side_effect = Exception("Test error")

    result = runner.invoke(memory_app, ["get", "mem-123"])

    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_all_commands_accept_region_option(mock_memory_manager):
    """Test that all commands accept --region option."""
    commands_with_args = [
        (["create", "test-memory", "--region", "us-east-1"], mock_memory_manager.create_memory_and_wait),
        (["get", "mem-123", "--region", "us-east-1"], mock_memory_manager.get_memory),
        (["list", "--region", "us-east-1"], mock_memory_manager.list_memories),
        (["delete", "mem-123", "--region", "us-east-1"], mock_memory_manager.delete_memory),
        (["status", "mem-123", "--region", "us-east-1"], mock_memory_manager.get_memory_status),
    ]

    # Mock return values
    mock_memory_manager.create_memory_and_wait.return_value = Memory({"id": "mem-123", "status": "ACTIVE"})
    mock_memory_manager.get_memory.return_value = Memory({"id": "mem-123", "status": "ACTIVE"})
    mock_memory_manager.list_memories.return_value = []
    mock_memory_manager.get_memory_status.return_value = "ACTIVE"

    for command_args, mock_method in commands_with_args:
        result = runner.invoke(memory_app, command_args)
        # Should not fail due to region option
        assert result.exit_code == 0 or "Error" not in result.stdout
