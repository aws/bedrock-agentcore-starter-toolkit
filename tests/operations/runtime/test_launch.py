"""Tests for Bedrock AgentCore launch operation."""

from unittest.mock import patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.runtime.launch import launch_bedrock_agentcore
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
    BedrockAgentCoreDeploymentInfo,
    NetworkConfiguration,
    ObservabilityConfig,
)


class TestLaunchBedrockAgentCore:
    """Test launch_bedrock_agentcore functionality."""

    def test_launch_local_mode(self, mock_container_runtime, tmp_path):
        """Test local deployment."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Patch ContainerRuntime in the launch module
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            result = launch_bedrock_agentcore(config_path, local=True)

        # Verify local mode result
        assert result.mode == "local"
        assert result.tag == "bedrock_agentcore-test-agent:latest"
        assert result.port == 8080
        assert hasattr(result, "runtime")

        # Verify build was called
        mock_container_runtime.build.assert_called_once()

    def test_launch_cloud_with_ecr_auto_create(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test cloud deployment with ECR creation."""
        # Create config file with auto-create ECR
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_auto_create=True,
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.create_ecr_repository") as mock_create_ecr,
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr") as mock_deploy_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"
            mock_deploy_ecr.return_value = (
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent:latest"
            )

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify cloud mode result
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")
            assert hasattr(result, "ecr_uri")

            # Verify ECR creation was called
            mock_create_ecr.assert_called_once()

    def test_launch_cloud_existing_agent(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test updating existing agent."""
        # Create config file with existing agent
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="023456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(agent_id="existing-agent-id"),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify update was called (not create)
            mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.assert_called_once()
            assert result.mode == "cloud"

    def test_launch_build_failure(self, mock_container_runtime, tmp_path):
        """Test error handling for build failures."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Mock build failure
        mock_container_runtime.build.return_value = (False, ["Error: build failed", "Missing dependency"])

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            with pytest.raises(RuntimeError, match="Build failed"):
                launch_bedrock_agentcore(config_path, local=True)

    def test_launch_missing_config(self, tmp_path):
        """Test error when config file not found."""
        nonexistent_config = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            launch_bedrock_agentcore(nonexistent_config)

    def test_launch_invalid_config(self, tmp_path):
        """Test validation errors."""
        # Create incomplete config (missing entrypoint)
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="",  # Invalid empty entrypoint
            aws=AWSConfig(network_configuration=NetworkConfiguration(), observability=ObservabilityConfig()),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        with pytest.raises(ValueError, match="Invalid configuration"):
            launch_bedrock_agentcore(config_path, local=False)

    def test_launch_push_ecr_only(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test push_ecr_only mode."""
        # Create config file
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            result = launch_bedrock_agentcore(config_path, local=False, push_ecr_only=True)

            # Verify push_ecr_only mode result
            assert result.mode == "push-ecr"
            assert result.tag == "bedrock_agentcore-test-agent:latest"
            assert hasattr(result, "ecr_uri")
            assert hasattr(result, "build_output")

    def test_launch_missing_ecr_repository(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test error when ECR repository not configured."""
        # Create config file without ECR repository
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                ecr_auto_create=False,  # No auto-create and no ECR repository
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            with pytest.raises(ValueError, match="ECR repository not configured"):
                launch_bedrock_agentcore(config_path, local=False)
