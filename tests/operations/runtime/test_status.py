"""Tests for Bedrock AgentCore status operation."""

from unittest.mock import patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.runtime.status import get_status
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
)


class TestStatusOperation:
    """Test get_status functionality."""

    def test_status_with_deployed_agent(self, mock_boto3_clients, tmp_path):
        """Test status for deployed agent with runtime details."""
        # Create config file with deployed agent
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock successful runtime responses
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
            "agentRuntimeId": "test-agent-id",
            "agentRuntimeArn": "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            "status": "READY",
            "createdAt": "2024-01-01T00:00:00Z",
        }

        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {
            "agentRuntimeEndpointArn": (
                "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
            ),
            "status": "READY",
            "endpointUrl": "https://example.com/endpoint",
        }

        result = get_status(config_path)

        # Verify result structure
        assert hasattr(result, "config")
        assert hasattr(result, "agent")
        assert hasattr(result, "endpoint")

        # Verify config info
        assert result.config.name == "test-agent"
        assert result.config.entrypoint == "test.py"
        assert result.config.region == "us-west-2"
        assert result.config.account == "123456789012"
        assert result.config.execution_role == "arn:aws:iam::123456789012:role/TestRole"
        assert result.config.agent_id == "test-agent-id"
        assert result.config.agent_arn == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"

        # Verify agent details
        assert result.agent is not None
        assert result.agent["status"] == "READY"
        assert result.agent["agentRuntimeId"] == "test-agent-id"

        # Verify endpoint details
        assert result.endpoint is not None
        assert result.endpoint["status"] == "READY"
        assert "endpointUrl" in result.endpoint

        # Verify Bedrock AgentCore client was called
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.assert_called_once_with(
            agentRuntimeId="test-agent-id"
        )
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.assert_called_once_with(
            agentRuntimeId="test-agent-id", endpointName="DEFAULT"
        )

    def test_status_not_deployed(self, tmp_path):
        """Test status for non-deployed agent."""
        # Create config file without deployment info
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),  # No agent_id/agent_arn
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        result = get_status(config_path)

        # Verify config info is populated
        assert result.config.name == "test-agent"
        assert result.config.agent_id is None
        assert result.config.agent_arn is None

        # Verify agent/endpoint details are None (not deployed)
        assert result.agent is None
        assert result.endpoint is None

    def test_status_runtime_error(self, mock_boto3_clients, tmp_path):
        """Test status with runtime API errors."""
        # Create config file with deployed agent
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock runtime API errors
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.side_effect = Exception("Agent not found")
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.side_effect = Exception(
            "Endpoint not accessible"
        )

        result = get_status(config_path)

        # Verify config info is still populated
        assert result.config.name == "test-agent"
        assert result.config.agent_id == "test-agent-id"

        # Verify error details are captured
        assert result.agent is not None
        assert result.agent["error"] == "Agent not found"
        assert result.endpoint is not None
        assert result.endpoint["error"] == "Endpoint not accessible"

    def test_status_missing_config(self, tmp_path):
        """Test status fails when config file not found."""
        nonexistent_config = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            get_status(nonexistent_config)

    def test_status_client_initialization_error(self, tmp_path):
        """Test status with Bedrock AgentCore client initialization failure."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock client initialization failure
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.status.BedrockAgentCoreClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Failed to initialize client")

            result = get_status(config_path)

            # Verify error is captured
            assert result.agent is not None
            assert "Failed to initialize Bedrock AgentCore client" in result.agent["error"]
            assert result.endpoint is not None
            assert "Failed to initialize Bedrock AgentCore client" in result.endpoint["error"]

    def test_status_partial_failure(self, mock_boto3_clients, tmp_path):
        """Test status when agent call succeeds but endpoint call fails."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="test-agent-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock partial success
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
            "agentRuntimeId": "test-agent-id",
            "status": "READY",
        }
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.side_effect = Exception("Endpoint error")

        result = get_status(config_path)

        # Verify agent succeeded
        assert result.agent is not None
        assert result.agent["status"] == "READY"
        assert result.agent["agentRuntimeId"] == "test-agent-id"

        # Verify endpoint failed
        assert result.endpoint is not None
        assert result.endpoint["error"] == "Endpoint error"

    def test_status_config_info_creation(self, mock_boto3_clients, tmp_path):
        """Test StatusConfigInfo creation with all fields."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="my-test-agent",
            entrypoint="src/handler.py",
            aws=AWSConfig(
                region="eu-west-1",
                account="987654321098",
                execution_role="arn:aws:iam::987654321098:role/MyCustomRole",
                ecr_repository="987654321098.dkr.ecr.eu-west-1.amazonaws.com/my-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="my-agent-id-123",
                agent_arn="arn:aws:bedrock_agentcore:eu-west-1:987654321098:agent-runtime/my-agent-id-123",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="my-test-agent", agents={"my-test-agent": agent_config}
        )
        save_config(project_config, config_path)

        # Mock runtime responses so the test doesn't make real API calls
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
            "agentRuntimeId": "my-agent-id-123",
            "status": "READY",
        }
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {"status": "READY"}

        result = get_status(config_path)

        # Verify all config fields are properly mapped
        assert result.config.name == "my-test-agent"
        assert result.config.entrypoint == "src/handler.py"
        assert result.config.region == "eu-west-1"
        assert result.config.account == "987654321098"
        assert result.config.execution_role == "arn:aws:iam::987654321098:role/MyCustomRole"
        assert result.config.ecr_repository == "987654321098.dkr.ecr.eu-west-1.amazonaws.com/my-repo"
        assert result.config.agent_id == "my-agent-id-123"
        assert (
            result.config.agent_arn == "arn:aws:bedrock_agentcore:eu-west-1:987654321098:agent-runtime/my-agent-id-123"
        )
