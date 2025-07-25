"""Tests for Bedrock AgentCore launch operation."""

from unittest.mock import MagicMock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.runtime.launch import (
    _ensure_execution_role,
    launch_bedrock_agentcore,
)
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

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

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

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

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

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

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

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            with pytest.raises(ValueError, match="ECR repository not configured"):
                launch_bedrock_agentcore(config_path, local=False)

    def test_launch_cloud_with_execution_role_auto_create(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test cloud deployment with execution role auto-creation."""
        # Create config file with execution role auto-create enabled
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role_auto_create=True,  # Enable auto-creation
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

        # Role name will use random suffix, so we can't predict the exact name
        created_role_arn = "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2-abc123xyz9"

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_get_or_create_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            mock_get_or_create_role.return_value = created_role_arn

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify execution role creation was called
            mock_get_or_create_role.assert_called_once()

            # Verify role creation parameters
            call_args = mock_get_or_create_role.call_args
            assert call_args.kwargs["region"] == "us-west-2"
            assert call_args.kwargs["account_id"] == "123456789012"
            assert call_args.kwargs["agent_name"] == "test-agent"

            # Verify cloud deployment succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

        # Verify the config was updated with the created role
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        updated_config = load_config(config_path)
        updated_agent = updated_config.agents["test-agent"]
        assert updated_agent.aws.execution_role == created_role_arn
        assert updated_agent.aws.execution_role_auto_create is False  # Should be disabled after creation

    def test_launch_cloud_with_existing_execution_role(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test cloud deployment with existing execution role (no auto-creation)."""
        existing_role_arn = "arn:aws:iam::123456789012:role/existing-test-role"

        # Create config file with existing execution role
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role=existing_role_arn,
                execution_role_auto_create=True,  # Should be ignored since role exists
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

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_create_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify execution role creation was NOT called (role already exists)
            mock_create_role.assert_not_called()

            # Verify cloud deployment succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

        # Verify the config was not modified (role already existed)
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        updated_config = load_config(config_path)
        updated_agent = updated_config.agents["test-agent"]
        assert updated_agent.aws.execution_role == existing_role_arn

    def test_launch_missing_execution_role_no_auto_create(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test error when execution role not configured and auto-create disabled."""
        # Create config file without execution role and auto-create disabled
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role_auto_create=False,  # No auto-create and no execution role
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
            with pytest.raises(ValueError, match="Missing 'aws.execution_role' for cloud deployment"):
                launch_bedrock_agentcore(config_path, local=False)

    def test_launch_cloud_conflict_exception_graceful_handling(
        self, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test graceful handling of ConflictException when agent already exists."""
        # Create config file without agent_id (simulating first deployment after agent already exists)
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
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),  # No agent_id set
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        # Mock ConflictException on create, then successful list and update
        from botocore.exceptions import ClientError

        conflict_error = ClientError(
            error_response={"Error": {"Code": "ConflictException", "Message": "Agent already exists"}},
            operation_name="CreateAgentRuntime",
        )

        # Mock the bedrock client to throw ConflictException on create_agent_runtime
        mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.side_effect = conflict_error

        # Mock successful list_agent_runtimes to find existing agent
        mock_boto3_clients["bedrock_agentcore"].list_agent_runtimes.return_value = {
            "agentRuntimes": [
                {
                    "agentRuntimeId": "existing-agent-123",
                    "agentRuntimeArn": (
                        "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/existing-agent-123"
                    ),
                    "agentRuntimeName": "test-agent",
                }
            ]
        }

        # Mock successful update_agent_runtime
        mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.return_value = {
            "agentRuntimeArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/existing-agent-123"
        }

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            result = launch_bedrock_agentcore(config_path, local=False, auto_update_on_conflict=True)

            # Verify that create was attempted first
            mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.assert_called_once()

            # Verify that list was called to find existing agent
            mock_boto3_clients["bedrock_agentcore"].list_agent_runtimes.assert_called()

            # Verify that update was called instead of failing
            mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.assert_called_once()

            # Verify successful deployment
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

        # Verify the config was updated with the discovered agent ID
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        updated_config = load_config(config_path)
        updated_agent = updated_config.agents["test-agent"]
        assert updated_agent.bedrock_agentcore.agent_id == "existing-agent-123"
        assert (
            updated_agent.bedrock_agentcore.agent_arn
            == "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/existing-agent-123"
        )

    def test_launch_cloud_conflict_exception_disabled_auto_update(
        self, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test ConflictException when auto_update_on_conflict is disabled."""
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

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        # Mock ConflictException on create
        from botocore.exceptions import ClientError

        conflict_error = ClientError(
            error_response={"Error": {"Code": "ConflictException", "Message": "Agent already exists"}},
            operation_name="CreateAgentRuntime",
        )
        mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.side_effect = conflict_error

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            # Should raise ConflictException when auto_update_on_conflict=False
            with pytest.raises(ClientError, match="ConflictException"):
                launch_bedrock_agentcore(config_path, local=False, auto_update_on_conflict=False)

            # Verify that create was attempted but list/update were not called
            mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.assert_called_once()
            mock_boto3_clients["bedrock_agentcore"].list_agent_runtimes.assert_not_called()
            mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.assert_not_called()

    def test_launch_cloud_with_existing_session_id_reset(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test that session ID gets reset when deploying to cloud."""
        # Create config file with existing session ID
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        existing_session_id = "existing-session-123"
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
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_session_id=existing_session_id  # Pre-existing session ID
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify deployment succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

            # Verify warning log was emitted about session ID reset
            mock_log.warning.assert_called_with(
                "⚠️ Session ID will be reset to connect to the updated agent. "
                "The previous agent remains accessible via the original session ID: %s",
                existing_session_id,
            )

        # Verify the session ID was reset to None in the config
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        updated_config = load_config(config_path)
        updated_agent = updated_config.agents["test-agent"]
        assert updated_agent.bedrock_agentcore.agent_session_id is None

    def test_launch_cloud_without_existing_session_id_no_reset(
        self, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that no session ID reset occurs when no session ID exists."""
        # Create config file without existing session ID
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
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
                agent_session_id=None  # No existing session ID
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Create a test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify deployment succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

            # Verify NO warning log was emitted about session ID reset
            mock_log.warning.assert_not_called()

        # Verify the session ID remains None in the config
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        updated_config = load_config(config_path)
        updated_agent = updated_config.agents["test-agent"]
        assert updated_agent.bedrock_agentcore.agent_session_id is None


class TestEnsureExecutionRole:
    """Test _ensure_execution_role functionality."""

    def test_ensure_execution_role_auto_create_success(self, mock_boto3_clients, tmp_path):
        """Test successful execution role auto-creation."""
        # Create agent config with auto-create enabled
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role_auto_create=True,
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

        # Create project config
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(project_config, config_path)

        # Role name will use random suffix, so we can't predict the exact name
        created_role_arn = "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreRuntimeSDKServiceRole-abc123xyz9"

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_get_or_create_role,
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.save_config") as mock_save_config,
        ):
            mock_get_or_create_role.return_value = created_role_arn

            result = _ensure_execution_role(
                agent_config=agent_config,
                project_config=project_config,
                config_path=config_path,
                agent_name="test-agent",
                region="us-west-2",
                account_id="123456789012",
            )

            # Verify role creation was called with correct parameters
            call_args = mock_get_or_create_role.call_args
            assert call_args.kwargs["region"] == "us-west-2"
            assert call_args.kwargs["account_id"] == "123456789012"
            assert call_args.kwargs["agent_name"] == "test-agent"
            assert "logger" in call_args.kwargs

            # Verify config was updated
            assert agent_config.aws.execution_role == created_role_arn
            assert agent_config.aws.execution_role_auto_create is False

            # Verify config was saved
            mock_save_config.assert_called_once_with(project_config, config_path)

            # Verify return value
            assert result == created_role_arn

    def test_ensure_execution_role_existing_role_no_create(self, tmp_path):
        """Test when execution role already exists (no auto-creation needed)."""
        existing_role_arn = "arn:aws:iam::123456789012:role/existing-role"

        # Create agent config with existing role
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role=existing_role_arn,
                execution_role_auto_create=True,  # Should be ignored
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})

        config_path = tmp_path / ".bedrock_agentcore.yaml"

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_create_role,
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session") as mock_session,
        ):
            mock_session.return_value.client.return_value = mock_iam_client

            result = _ensure_execution_role(
                agent_config=agent_config,
                project_config=project_config,
                config_path=config_path,
                agent_name="test-agent",
                region="us-west-2",
                account_id="123456789012",
            )

            # Verify role creation was NOT called
            mock_create_role.assert_not_called()

            # Verify return value is existing role
            assert result == existing_role_arn

    def test_ensure_execution_role_no_role_no_auto_create(self, tmp_path):
        """Test error when no execution role and auto-create disabled."""
        # Create agent config without role and auto-create disabled
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role_auto_create=False,
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})

        config_path = tmp_path / ".bedrock_agentcore.yaml"

        with pytest.raises(ValueError, match="Execution role not configured and auto-create not enabled"):
            _ensure_execution_role(
                agent_config=agent_config,
                project_config=project_config,
                config_path=config_path,
                agent_name="test-agent",
                region="us-west-2",
                account_id="123456789012",
            )

    def test_ensure_execution_role_creation_failure(self, tmp_path):
        """Test error handling when role creation fails."""
        # Create agent config with auto-create enabled
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role_auto_create=True,
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )

        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})

        config_path = tmp_path / ".bedrock_agentcore.yaml"

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
        ) as mock_get_or_create_role:
            # Mock role creation failure
            mock_get_or_create_role.side_effect = Exception("IAM permission denied")

            with pytest.raises(Exception, match="IAM permission denied"):
                _ensure_execution_role(
                    agent_config=agent_config,
                    project_config=project_config,
                    config_path=config_path,
                    agent_name="test-agent",
                    region="us-west-2",
                    account_id="123456789012",
                )

    def test_validate_execution_role_url_encoded_policy(self):
        """Test _validate_execution_role with URL-encoded trust policy."""
        import json
        import urllib.parse

        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _validate_execution_role

        # Create URL-encoded trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        url_encoded_policy = urllib.parse.quote(json.dumps(trust_policy))

        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": url_encoded_policy  # URL-encoded string
            }
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_iam_client

        result = _validate_execution_role("arn:aws:iam::123456789012:role/test-role", mock_session)

        assert result is True

    def test_validate_execution_role_invalid_trust_policy(self):
        """Test _validate_execution_role with invalid trust policy."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _validate_execution_role

        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},  # Wrong service
                            "Action": "sts:AssumeRole",
                        }
                    ]
                }
            }
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_iam_client

        result = _validate_execution_role("arn:aws:iam::123456789012:role/test-role", mock_session)

        assert result is False

    def test_validate_execution_role_role_not_found(self):
        """Test _validate_execution_role when role doesn't exist."""
        from botocore.exceptions import ClientError

        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _validate_execution_role

        mock_iam_client = MagicMock()
        mock_iam_client.get_role.side_effect = ClientError({"Error": {"Code": "NoSuchEntity"}}, "GetRole")

        mock_session = MagicMock()
        mock_session.client.return_value = mock_iam_client

        result = _validate_execution_role("arn:aws:iam::123456789012:role/nonexistent-role", mock_session)

        assert result is False
