"""Unit tests for bootstrap utility functions."""

from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap import resolve_bootstrap_project_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    MemoryConfig,
    NetworkConfiguration,
    ObservabilityConfig,
    ProtocolConfiguration,
)


class TestResolveBootstrapProjectConfig:
    """Tests for resolve_bootstrap_project_config function."""

    def test_returns_none_for_non_bootstrap_project(self, tmp_path, monkeypatch):
        """Test that function returns None for non-bootstrap projects."""
        # Arrange
        # Create a config that is NOT a bootstrap project
        config = BedrockAgentCoreConfigSchema(
            default_agent="test-agent",
            agents={
                "test-agent": BedrockAgentCoreAgentSchema(
                    name="test-agent",
                    entrypoint="src/main.py",
                    source_path=".",
                    deployment_type="container",
                    aws=AWSConfig(
                        region="us-west-2",
                        account="123456789012",
                        execution_role="arn:aws:iam::123456789012:role/TestRole",
                        network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
                        observability=ObservabilityConfig(enabled=True),
                        protocol_configuration=ProtocolConfiguration(server_protocol="HTTP"),
                    ),
                    memory=MemoryConfig(mode="NO_MEMORY", event_expiry_days=30),
                    bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                        agent_id="test-id",
                        agent_arn="arn:aws:bedrock:us-west-2:123456789012:agent/test-id",
                    ),
                )
            },
            is_agentcore_bootstrap_project=False,  # Not a bootstrap project
        )

        monkeypatch.chdir(tmp_path)

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.load_config", return_value=config):
            # Act
            result = resolve_bootstrap_project_config()

            # Assert
            assert result is None

    def test_uses_existing_runtime_id_and_arn_when_present(self, tmp_path, monkeypatch):
        """Test that function uses existing runtime ID and ARN when they're already set."""
        # Arrange
        existing_id = "existing-runtime-id"
        existing_arn = "arn:aws:bedrock:us-west-2:123456789012:agent/existing-runtime-id"

        config = BedrockAgentCoreConfigSchema(
            default_agent="test-agent",
            agents={
                "test-agent": BedrockAgentCoreAgentSchema(
                    name="test-agent",
                    entrypoint="src/main.py",
                    source_path=".",
                    deployment_type="container",
                    aws=AWSConfig(
                        region="us-west-2",
                        account="123456789012",
                        execution_role="arn:aws:iam::123456789012:role/TestRole",
                        network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
                        observability=ObservabilityConfig(enabled=True),
                        protocol_configuration=ProtocolConfiguration(server_protocol="HTTP"),
                    ),
                    memory=MemoryConfig(mode="NO_MEMORY", event_expiry_days=30),
                    bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                        agent_id=existing_id,
                        agent_arn=existing_arn,
                    ),
                )
            },
            is_agentcore_bootstrap_project=True,
        )

        monkeypatch.chdir(tmp_path)

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.load_config", return_value=config):
            with patch("bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.save_config") as mock_save:
                with patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.get_region", return_value="us-west-2"
                ):
                    with patch(
                        "bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.generate_session_id",
                        return_value="session-123",
                    ):
                        resolve_bootstrap_project_config()

                        # Assert
                        mock_save.assert_called_once()
                        # Should have updated the config with session ID
                        saved_config = mock_save.call_args[0][0]
                        assert saved_config.agents["test-agent"].bedrock_agentcore.agent_id == existing_id
                        assert saved_config.agents["test-agent"].bedrock_agentcore.agent_arn == existing_arn
                        assert saved_config.agents["test-agent"].bedrock_agentcore.agent_session_id == "session-123"

    def test_finds_runtime_by_name_when_not_set(self, tmp_path, monkeypatch):
        """Test that function finds runtime by name when ID/ARN are not set."""

        config = BedrockAgentCoreConfigSchema(
            default_agent="test-agent",
            agents={
                "test-agent": BedrockAgentCoreAgentSchema(
                    name="test-agent",
                    entrypoint="src/main.py",
                    source_path=".",
                    deployment_type="container",
                    aws=AWSConfig(
                        region="us-west-2",
                        account="123456789012",
                        execution_role="arn:aws:iam::123456789012:role/TestRole",
                        network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
                        observability=ObservabilityConfig(enabled=True),
                        protocol_configuration=ProtocolConfiguration(server_protocol="HTTP"),
                    ),
                    memory=MemoryConfig(mode="NO_MEMORY", event_expiry_days=30),
                    bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                        agent_id=None,  # Not set
                        agent_arn=None,  # Not set
                    ),
                )
            },
            is_agentcore_bootstrap_project=True,
        )

        # Mock the client to return a matching agent
        mock_client = Mock()
        mock_client.list_agents.return_value = [
            {
                "agentRuntimeName": "test-agent",
                "agentRuntimeId": "found-runtime-id",
                "agentRuntimeArn": "arn:aws:bedrock:us-west-2:123456789012:agent/found-runtime-id",
            }
        ]

        monkeypatch.chdir(tmp_path)

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.load_config", return_value=config):
            with patch("bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.save_config") as mock_save:
                with patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.get_region", return_value="us-west-2"
                ):
                    with patch(
                        "bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.generate_session_id",
                        return_value="session-456",
                    ):
                        with patch(
                            "bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.BedrockAgentCoreClient",
                            return_value=mock_client,
                        ):
                            # Act
                            resolve_bootstrap_project_config()

                            # Assert
                            mock_save.assert_called_once()
                            saved_config = mock_save.call_args[0][0]
                            assert saved_config.agents["test-agent"].bedrock_agentcore.agent_id == "found-runtime-id"
                            assert (
                                saved_config.agents["test-agent"].bedrock_agentcore.agent_arn
                                == "arn:aws:bedrock:us-west-2:123456789012:agent/found-runtime-id"
                            )

    def test_raises_exception_when_agent_not_found(self, tmp_path, monkeypatch):
        """Test that function raises exception when agent is not found."""
        # Arrange
        config = BedrockAgentCoreConfigSchema(
            default_agent="test-agent",
            agents={
                "test-agent": BedrockAgentCoreAgentSchema(
                    name="test-agent",
                    entrypoint="src/main.py",
                    source_path=".",
                    deployment_type="container",
                    aws=AWSConfig(
                        region="us-west-2",
                        account="123456789012",
                        execution_role="arn:aws:iam::123456789012:role/TestRole",
                        network_configuration=NetworkConfiguration(network_mode="PUBLIC"),
                        observability=ObservabilityConfig(enabled=True),
                        protocol_configuration=ProtocolConfiguration(server_protocol="HTTP"),
                    ),
                    memory=MemoryConfig(mode="NO_MEMORY", event_expiry_days=30),
                    bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                        agent_id=None,
                        agent_arn=None,
                    ),
                )
            },
            is_agentcore_bootstrap_project=True,
        )

        # Mock the client to return no matching agents
        mock_client = Mock()
        mock_client.list_agents.return_value = []

        monkeypatch.chdir(tmp_path)

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.load_config", return_value=config):
            with patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.get_region", return_value="us-west-2"
            ):
                with patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.bootstrap.BedrockAgentCoreClient",
                    return_value=mock_client,
                ):
                    # Act & Assert
                    with pytest.raises(
                        Exception, match="Could not find an agentcore runtime resource with name test-agent"
                    ):
                        resolve_bootstrap_project_config()
