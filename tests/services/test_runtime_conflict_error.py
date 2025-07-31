"""Test for improved ConflictException error handling."""

from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.services.runtime import BedrockAgentCoreClient


def test_conflict_exception_improved_error_message():
    """Test that ConflictException shows helpful error message about --auto-update-on-conflict flag."""

    # Create a mock client
    client = BedrockAgentCoreClient("us-east-1")

    # Mock the boto3 client to raise ConflictException
    mock_error = ClientError(
        {"Error": {"Code": "ConflictException", "Message": "AgentName already exists"}}, "CreateAgentRuntime"
    )

    client.client.create_agent_runtime = Mock(side_effect=mock_error)

    # Test that the improved error message is raised when auto_update_on_conflict=False
    with pytest.raises(ClientError) as exc_info:
        client.create_agent(
            agent_name="test_agent",
            image_uri="123456789.dkr.ecr.us-east-1.amazonaws.com/test:latest",
            execution_role_arn="arn:aws:iam::123456789:role/test-role",
            auto_update_on_conflict=False,
        )

    # Verify the error message mentions --auto-update-on-conflict flag
    error_message = exc_info.value.response["Error"]["Message"]
    assert "test_agent" in error_message
    assert "already exists" in error_message
    assert "--auto-update-on-conflict" in error_message
    assert "launch command" in error_message


def test_conflict_exception_with_auto_update_enabled():
    """Test that ConflictException triggers update flow when auto_update_on_conflict=True."""

    # Create a mock client
    client = BedrockAgentCoreClient("us-east-1")

    # Mock the boto3 client to raise ConflictException initially
    mock_error = ClientError(
        {"Error": {"Code": "ConflictException", "Message": "AgentName already exists"}}, "CreateAgentRuntime"
    )

    client.client.create_agent_runtime = Mock(side_effect=mock_error)

    # Mock find_agent_by_name to return existing agent
    existing_agent = {
        "agentRuntimeId": "existing-agent-id",
        "agentRuntimeArn": "arn:aws:bedrock-agentcore:us-east-1:123456789:agent-runtime/existing-agent-id",
    }
    client.find_agent_by_name = Mock(return_value=existing_agent)

    # Mock update_agent to succeed
    client.update_agent = Mock(
        return_value={
            "id": "existing-agent-id",
            "arn": "arn:aws:bedrock-agentcore:us-east-1:123456789:agent-runtime/existing-agent-id",
        }
    )

    # Test that auto_update_on_conflict=True triggers update flow
    result = client.create_agent(
        agent_name="test_agent",
        image_uri="123456789.dkr.ecr.us-east-1.amazonaws.com/test:latest",
        execution_role_arn="arn:aws:iam::123456789:role/test-role",
        auto_update_on_conflict=True,
    )

    # Verify that update_agent was called
    client.update_agent.assert_called_once()

    # Verify the result contains the existing agent info
    assert result["id"] == "existing-agent-id"
    assert "existing-agent-id" in result["arn"]
