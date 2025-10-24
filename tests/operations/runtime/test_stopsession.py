"""Tests for Bedrock AgentCore stop session operation."""

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.runtime.stop_session import stop_runtime_session
from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config, save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
)


class TestStopSessionOperation:
    """Test stop_runtime_session functionality."""

    def test_stop_session_with_provided_session_id(self, mock_boto3_clients, tmp_path):
        """Test stopping session with explicitly provided session ID."""
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

        # Mock successful stop_runtime_session response
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.return_value = {"statusCode": 200}

        result = stop_runtime_session(
            config_path=config_path,
            session_id="test-session-123",
        )

        # Verify result
        assert result.session_id == "test-session-123"
        assert result.agent_name == "test-agent"
        assert result.status_code == 200
        assert result.message == "Session stopped successfully"

        # Verify Bedrock AgentCore client was called correctly
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.assert_called_once_with(
            agentRuntimeArn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            qualifier="DEFAULT",
            runtimeSessionId="test-session-123",
        )

    def test_stop_session_with_tracked_session_id(self, mock_boto3_clients, tmp_path):
        """Test stopping session using tracked session ID from config."""
        # Create config file with deployed agent and tracked session
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
                agent_session_id="tracked-session-456",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock successful stop_runtime_session response
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.return_value = {"statusCode": 200}

        result = stop_runtime_session(
            config_path=config_path,
            session_id=None,  # No session_id provided
        )

        # Verify result
        assert result.session_id == "tracked-session-456"
        assert result.agent_name == "test-agent"
        assert result.status_code == 200
        assert result.message == "Session stopped successfully"

        # Verify session ID was cleared from config
        updated_config = load_config(config_path)
        updated_agent = updated_config.get_agent_config(None)
        assert updated_agent.bedrock_agentcore.agent_session_id is None

        # Verify Bedrock AgentCore client was called correctly
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.assert_called_once_with(
            agentRuntimeArn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            qualifier="DEFAULT",
            runtimeSessionId="tracked-session-456",
        )

    def test_stop_session_clears_config_when_matching(self, mock_boto3_clients, tmp_path):
        """Test that session ID is cleared from config when it matches the stopped session."""
        # Create config file with tracked session
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
                agent_session_id="session-to-stop",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock successful stop_runtime_session response
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.return_value = {"statusCode": 200}

        # Stop the tracked session explicitly
        result = stop_runtime_session(
            config_path=config_path,
            session_id="session-to-stop",
        )

        # Verify session was stopped
        assert result.status_code == 200

        # Verify session ID was cleared from config
        updated_config = load_config(config_path)
        updated_agent = updated_config.get_agent_config(None)
        assert updated_agent.bedrock_agentcore.agent_session_id is None

    def test_stop_session_doesnt_clear_different_session(self, mock_boto3_clients, tmp_path):
        """Test that config session ID is NOT cleared when stopping a different session."""
        # Create config file with tracked session
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
                agent_session_id="tracked-session",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock successful stop_runtime_session response
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.return_value = {"statusCode": 200}

        # Stop a different session
        result = stop_runtime_session(
            config_path=config_path,
            session_id="different-session",
        )

        # Verify session was stopped
        assert result.status_code == 200
        assert result.session_id == "different-session"

        # Verify tracked session ID was NOT cleared from config
        updated_config = load_config(config_path)
        updated_agent = updated_config.get_agent_config(None)
        assert updated_agent.bedrock_agentcore.agent_session_id == "tracked-session"

    def test_stop_session_agent_not_deployed(self, tmp_path):
        """Test stopping session fails when agent is not deployed."""
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
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),  # No agent_arn
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Attempt to stop session
        with pytest.raises(ValueError) as exc_info:
            stop_runtime_session(
                config_path=config_path,
                session_id="some-session",
            )

        assert "is not deployed" in str(exc_info.value)
        assert "agentcore launch" in str(exc_info.value)

    def test_stop_session_no_session_id_provided_or_tracked(self, mock_boto3_clients, tmp_path):
        """Test stopping session fails when no session ID is provided or tracked."""
        # Create config file without tracked session
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
                agent_session_id=None,  # No tracked session
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Attempt to stop session without providing session_id
        with pytest.raises(ValueError) as exc_info:
            stop_runtime_session(
                config_path=config_path,
                session_id=None,
            )

        assert "No active session found" in str(exc_info.value)
        assert "--session-id" in str(exc_info.value)

    def test_stop_session_resource_not_found(self, mock_boto3_clients, tmp_path):
        """Test handling of ResourceNotFoundException (session already terminated)."""
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
                agent_session_id="session-not-found",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        error_response = {
            "Error": {"Code": "ResourceNotFoundException", "Message": "Session not found"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }

        # Mock ResourceNotFoundException
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.side_effect = ClientError(
            error_response, "stop_runtime_session"
        )
        result = stop_runtime_session(
            config_path=config_path,
            session_id="session-not-found",
        )

        # Verify graceful handling
        assert result.session_id == "session-not-found"
        assert result.agent_name == "test-agent"
        assert result.status_code == 404
        assert "not found" in result.message.lower()

        # Verify session ID was still cleared from config
        updated_config = load_config(config_path)
        updated_agent = updated_config.get_agent_config(None)
        assert updated_agent.bedrock_agentcore.agent_session_id is None

    def test_stop_session_not_found_error(self, mock_boto3_clients, tmp_path):
        """Test handling of NotFound error (alternative error format)."""
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

        # Mock NotFound error as ClientError
        error_response = {
            "Error": {
                "Code": "NotFound",  # or 'ResourceNotFoundException'
                "Message": "Session does not exist",
            },
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }

        # Mock NotFound error
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.side_effect = ClientError(
            error_response, "stop_runtime_session"
        )

        result = stop_runtime_session(
            config_path=config_path,
            session_id="nonexistent-session",
        )

        # Verify graceful handling
        assert result.session_id == "nonexistent-session"
        assert result.status_code == 404
        assert "not found" in result.message.lower()

    def test_stop_session_other_exception(self, mock_boto3_clients, tmp_path):
        """Test that other exceptions are re-raised."""
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

        # Mock a different exception
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.side_effect = Exception(
            "InternalServerError: Service unavailable"
        )

        # Verify exception is re-raised
        with pytest.raises(Exception) as exc_info:
            stop_runtime_session(
                config_path=config_path,
                session_id="some-session",
            )

        assert "InternalServerError" in str(exc_info.value)

    def test_stop_session_missing_config(self, tmp_path):
        """Test stopping session fails when config file doesn't exist."""
        nonexistent_config = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            stop_runtime_session(
                config_path=nonexistent_config,
                session_id="some-session",
            )

    def test_stop_session_with_agent_name(self, mock_boto3_clients, tmp_path):
        """Test stopping session with specific agent name in multi-agent config."""
        # Create config file with multiple agents
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent1_config = BedrockAgentCoreAgentSchema(
            name="agent-1",
            entrypoint="agent1.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="agent-1-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/agent-1-id",
                agent_session_id="session-1",
            ),
        )
        agent2_config = BedrockAgentCoreAgentSchema(
            name="agent-2",
            entrypoint="agent2.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_id="agent-2-id",
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/agent-2-id",
                agent_session_id="session-2",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="agent-1", agents={"agent-1": agent1_config, "agent-2": agent2_config}
        )
        save_config(project_config, config_path)

        # Mock successful stop_runtime_session response
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.return_value = {"statusCode": 200}

        # Stop session for agent-2
        result = stop_runtime_session(
            config_path=config_path,
            session_id=None,
            agent_name="agent-2",
        )

        # Verify correct agent was targeted
        assert result.agent_name == "agent-2"
        assert result.session_id == "session-2"

        # Verify correct agent ARN was used
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.assert_called_once_with(
            agentRuntimeArn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/agent-2-id",
            qualifier="DEFAULT",
            runtimeSessionId="session-2",
        )

        # Verify only agent-2's session was cleared
        updated_config = load_config(config_path)
        agent1_updated = updated_config.get_agent_config("agent-1")
        agent2_updated = updated_config.get_agent_config("agent-2")
        assert agent1_updated.bedrock_agentcore.agent_session_id == "session-1"  # Unchanged
        assert agent2_updated.bedrock_agentcore.agent_session_id is None  # Cleared

    def test_stop_session_with_custom_status_code(self, mock_boto3_clients, tmp_path):
        """Test handling of custom status code in response."""
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

        # Mock response with custom status code
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.return_value = {"statusCode": 204}

        result = stop_runtime_session(
            config_path=config_path,
            session_id="test-session",
        )

        # Verify custom status code is preserved
        assert result.status_code == 204

    def test_stop_session_response_without_status_code(self, mock_boto3_clients, tmp_path):
        """Test handling of response without statusCode field."""
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

        # Mock response without statusCode
        mock_boto3_clients["bedrock_agentcore"].stop_runtime_session.return_value = {}

        result = stop_runtime_session(
            config_path=config_path,
            session_id="test-session",
        )

        # Verify default status code is used
        assert result.status_code == 200
