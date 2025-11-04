"""Tests for Bedrock AgentCore launch operation."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

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


# Test Helper Functions
def create_test_config(
    tmp_path,
    agent_name="test-agent",
    entrypoint="test_agent.py",
    region="us-west-2",
    account="123456789012",
    execution_role=None,
    execution_role_auto_create=False,
    ecr_repository=None,
    ecr_auto_create=False,
    agent_id=None,
    agent_session_id=None,
    observability_enabled=False,
    deployment_type="container",
):
    """Create a test configuration with customizable parameters."""
    config_path = tmp_path / ".bedrock_agentcore.yaml"
    agent_config = BedrockAgentCoreAgentSchema(
        name=agent_name,
        entrypoint=entrypoint,
        container_runtime="docker",
        deployment_type=deployment_type,
        aws=AWSConfig(
            region=region,
            account=account,
            execution_role=execution_role,
            execution_role_auto_create=execution_role_auto_create,
            ecr_repository=ecr_repository,
            ecr_auto_create=ecr_auto_create,
            network_configuration=NetworkConfiguration(),
            observability=ObservabilityConfig(enabled=observability_enabled),
        ),
        bedrock_agentcore=BedrockAgentCoreDeploymentInfo(
            agent_id=agent_id,
            agent_session_id=agent_session_id,
        ),
    )
    project_config = BedrockAgentCoreConfigSchema(default_agent=agent_name, agents={agent_name: agent_config})
    save_config(project_config, config_path)
    return config_path


def create_test_agent_file(tmp_path, filename="test_agent.py", content="# test agent"):
    """Create a test agent file."""
    agent_file = tmp_path / filename
    agent_file.write_text(content)
    return agent_file


def create_test_dockerfile(tmp_path, agent_name="test-agent", source_path=None):
    """Create a Dockerfile in the expected location for tests.

    Args:
        tmp_path: Test temporary directory
        agent_name: Name of the agent
        source_path: Optional source path (if using multi-agent setup)

    Returns:
        Path to created Dockerfile
    """
    if source_path:
        # Multi-agent: Dockerfile in .bedrock_agentcore/{agent_name}/
        dockerfile_dir = tmp_path / ".bedrock_agentcore" / agent_name
        dockerfile_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Legacy: Dockerfile at project root
        dockerfile_dir = tmp_path

    dockerfile = dockerfile_dir / "Dockerfile"
    dockerfile.write_text("FROM python:3.10\nCOPY . /app\n")
    return dockerfile


class MockAWSClientFactory:
    """Factory for creating consistent AWS client mocks."""

    def __init__(self, account="123456789012", region="us-west-2"):
        self.account = account
        self.region = region
        self._setup_clients()

    def _setup_clients(self):
        """Setup all AWS service client mocks."""
        # IAM Client Mock
        self.iam_client = MagicMock()
        self.iam_client.get_role.return_value = {
            "Role": {
                "Arn": f"arn:aws:iam::{self.account}:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }

        # CodeBuild Client Mock
        self.codebuild_client = MagicMock()
        self.codebuild_client.batch_get_builds.return_value = {
            "builds": [{"buildStatus": "SUCCEEDED", "currentPhase": "COMPLETED"}]
        }
        self.codebuild_client.create_project.return_value = {}
        self.codebuild_client.start_build.return_value = {"build": {"id": "build-123"}}

        # S3 Client Mock
        self.s3_client = MagicMock()
        self.s3_client.head_bucket.return_value = {}
        self.s3_client.upload_file.return_value = {}

        # STS Client Mock
        self.sts_client = MagicMock()
        self.sts_client.get_caller_identity.return_value = {"Account": self.account}

    def get_client(self, service_name):
        """Get a mock client for the specified service."""
        clients = {
            "iam": self.iam_client,
            "codebuild": self.codebuild_client,
            "s3": self.s3_client,
            "sts": self.sts_client,
        }
        return clients.get(service_name, MagicMock())

    def setup_full_session_mock(self, mock_boto3_clients):
        """Setup the complete session mock with all AWS clients."""
        mock_session = mock_boto3_clients["session"]
        mock_session.client.side_effect = self.get_client
        mock_session.region_name = self.region

    def setup_session_mock(self, mock_boto3_clients):
        """Setup the session mock to use our client factory (legacy method)."""
        self.setup_full_session_mock(mock_boto3_clients)


def assert_codebuild_workflow_called(mock_factory):
    """Assert that CodeBuild workflow was properly executed."""
    mock_factory.codebuild_client.create_project.assert_called()
    mock_factory.codebuild_client.start_build.assert_called()
    mock_factory.codebuild_client.batch_get_builds.assert_called()


def assert_config_updated_with_role(config_path, expected_role_arn):
    """Assert that config was updated with the expected execution role."""
    from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

    updated_config = load_config(config_path)
    updated_agent = list(updated_config.agents.values())[0]
    assert updated_agent.aws.execution_role == expected_role_arn
    assert updated_agent.aws.execution_role_auto_create is False


def assert_no_agent_deployment_calls(mock_boto3_clients):
    """Assert that no agent deployment calls were made (for ECR-only tests)."""
    mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.assert_not_called()
    mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.assert_not_called()


class TestLaunchBedrockAgentCore:
    """Test launch_bedrock_agentcore functionality."""

    def test_launch_local_mode(self, mock_container_runtime, tmp_path):
        """Test local deployment."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

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
        mock_container_runtime.build.assert_called_once()

    def test_launch_cloud_with_ecr_auto_create(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test cloud deployment with ECR creation."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_auto_create=True,
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_create_role,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"
            mock_create_role.return_value = "arn:aws:iam::123456789012:role/TestRole"

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify codebuild mode result
            assert result.mode == "codebuild"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")
            assert hasattr(result, "ecr_uri")
            assert hasattr(result, "codebuild_id")

            # Verify CodeBuild workflow was executed
            assert_codebuild_workflow_called(mock_factory)

    def test_ensure_ecr_repository_no_auto_create_no_repo(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test error when ECR repository not configured and auto-create disabled."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository=None,  # No repository
            ecr_auto_create=False,  # No auto-create
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        # Mock the ContainerRuntime to avoid actual build
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime"
        ) as mock_runtime_class:
            mock_runtime = MagicMock()
            mock_runtime.has_local_runtime = True
            mock_runtime.build.return_value = (True, ["Successfully built"])
            mock_runtime_class.return_value = mock_runtime

            with pytest.raises(ValueError, match="ECR repository not configured"):
                launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

    def test_launch_cloud_existing_agent(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test updating existing agent."""
        config_path = create_test_config(
            tmp_path,
            account="023456789012",
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            agent_id="existing-agent-id",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory(account="023456789012")
        mock_factory.setup_session_mock(mock_boto3_clients)

        with patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository"):
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify update was called (not create)
            mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.assert_called_once()
            assert result.mode == "codebuild"

    def test_launch_build_failure(self, mock_container_runtime, tmp_path):
        """Test error handling for build failures."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

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
        config_path = create_test_config(tmp_path, entrypoint="")  # Invalid empty entrypoint
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        with pytest.raises(ValueError, match="Invalid configuration"):
            launch_bedrock_agentcore(config_path, local=False)

    def test_launch_local_build_cloud_deployment(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test local build with cloud deployment (use_codebuild=False)."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with (
            # Mock memory operations to prevent hanging
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            # Mock the BedrockAgentCoreClient to prevent hanging on wait operations
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.BedrockAgentCoreClient"
            ) as mock_client_class,
            # For direct fix, mock the _deploy_to_bedrock_agentcore function
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            # Setup BedrockAgentCoreClient mock
            mock_client = MagicMock()
            mock_client.create_or_update_agent.return_value = {
                "id": "agent-123",
                "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            }
            mock_client.wait_for_agent_endpoint_ready.return_value = "https://example.com"
            mock_client_class.return_value = mock_client

            # Direct fix for _deploy_to_bedrock_agentcore
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify local build with cloud deployment
            assert result.mode == "cloud"
            assert result.tag == "bedrock_agentcore-test-agent:latest"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")
            assert hasattr(result, "ecr_uri")
            assert hasattr(result, "build_output")

            # Verify local build was used (not CodeBuild)
            mock_container_runtime.build.assert_called_once()

    def test_launch_missing_ecr_repository(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test error when ECR repository not configured."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_auto_create=False,  # No auto-create and no ECR repository
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with (
            # Mock memory operations to prevent hanging
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            with pytest.raises(ValueError, match="ECR repository not configured"):
                launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

    def test_launch_cloud_with_execution_role_auto_create(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test cloud deployment with execution role auto-creation."""
        config_path = create_test_config(
            tmp_path,
            execution_role_auto_create=True,  # Enable auto-creation
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Role name will use random suffix, so we can't predict the exact name
        created_role_arn = "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKRuntime-us-west-2-abc123xyz9"

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

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

            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

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

    def test_launch_with_invalid_agent_name(self, tmp_path):
        """Test launch with invalid agent name."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import launch_bedrock_agentcore

        # Create a config file with invalid agent name (starts with a number)
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="1invalid-name",  # Invalid: starts with a number
            entrypoint="app.py",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                network_configuration=NetworkConfiguration(),
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(
            default_agent="1invalid-name", agents={"1invalid-name": agent_config}
        )
        save_config(project_config, config_path)

        # Should raise ValueError for invalid agent name
        with pytest.raises(ValueError, match="Invalid configuration"):
            launch_bedrock_agentcore(config_path)

    def test_launch_cloud_with_existing_execution_role(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test cloud deployment with existing execution role (no auto-creation)."""
        existing_role_arn = "arn:aws:iam::123456789012:role/existing-test-role"

        config_path = create_test_config(
            tmp_path,
            execution_role=existing_role_arn,
            execution_role_auto_create=True,  # Should be ignored since role exists
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": existing_role_arn,
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }
        mock_boto3_clients["session"].client.return_value = mock_iam_client

        with (
            # Mock memory operations to prevent hanging
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_create_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            # Mock the BedrockAgentCoreClient to prevent hanging on wait operations
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.BedrockAgentCoreClient"
            ) as mock_client_class,
            # For direct fix, mock the _deploy_to_bedrock_agentcore function
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            # Setup BedrockAgentCoreClient mock
            mock_client = MagicMock()
            mock_client.create_or_update_agent.return_value = {
                "id": "agent-123",
                "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            }
            mock_client.wait_for_agent_endpoint_ready.return_value = "https://example.com"
            mock_client_class.return_value = mock_client

            # Direct fix for _deploy_to_bedrock_agentcore
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

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

    def test_port_configuration(self, mock_container_runtime, tmp_path):
        """Test port configuration from environment variables."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock successful build
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])
        mock_container_runtime.has_local_runtime = True

        # Test various port configurations
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            # Default port
            result1 = launch_bedrock_agentcore(config_path, local=True)
            assert result1.port == 8080

            # String port
            result2 = launch_bedrock_agentcore(config_path, local=True, env_vars={"PORT": "9000"})
            assert result2.port == 8080  # Should still be 8080 as env vars are only passed to container

            # Invalid port
            result3 = launch_bedrock_agentcore(config_path, local=True, env_vars={"PORT": "invalid"})
            assert result3.port == 8080  # Should default to 8080

    def test_network_configuration_validation(self, tmp_path):
        """Test network configuration validation."""
        from pydantic import ValidationError

        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration

        # Should raise ValidationError when creating NetworkConfiguration with invalid network mode
        with pytest.raises(ValidationError, match="Invalid network_mode"):
            NetworkConfiguration(network_mode="INVALID_MODE")

    def test_container_build_failure_handling(self, mock_container_runtime, tmp_path):
        """Test handling of container build failures."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock build failure
        mock_container_runtime.build.return_value = (False, ["Error: failed to resolve", "No such file or directory"])
        mock_container_runtime.has_local_runtime = True

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            # Should raise RuntimeError with build failure message
            with pytest.raises(RuntimeError, match="Build failed"):
                launch_bedrock_agentcore(config_path, local=True)

    def test_container_runtime_availability_check(self, tmp_path):
        """Test container runtime availability check."""
        # Create config with execution role to avoid validation error
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock container runtime with no local runtime available
        mock_runtime = Mock()
        mock_runtime.has_local_runtime = False

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_runtime,
        ):
            # Test local mode with no runtime
            with pytest.raises(RuntimeError, match="Cannot run locally"):
                launch_bedrock_agentcore(config_path, local=True)

            # Test cloud mode with local build but no runtime
            with pytest.raises(RuntimeError, match="Cannot build locally"):
                launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

    def test_configuration_validation(self, tmp_path):
        """Test configuration validation for cloud deployment."""
        # Create config with missing execution role (invalid for cloud deployment)
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Should fail validation due to missing execution role
        with pytest.raises(ValueError, match="Missing 'aws.execution_role'"):
            launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

    def test_local_launch_result_structure(self, mock_container_runtime, tmp_path):
        """Test structure of LaunchResult for local mode."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock build success but don't mock run
        mock_container_runtime.has_local_runtime = True
        mock_container_runtime.build.return_value = (True, ["Successfully built"])

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime.run",
                return_value=True,
            ),
        ):  # Patch the class method directly
            result = launch_bedrock_agentcore(config_path, local=True)

            # Check result structure
            assert result.mode == "local"
            assert result.port == 8080
            assert result.tag == "bedrock_agentcore-test-agent:latest"
            assert isinstance(result.runtime, type(mock_container_runtime))

    def test_env_vars_handling(self, mock_container_runtime, tmp_path):
        """Test environment variable handling."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Add a memory configuration to the agent
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config, save_config

        config = load_config(config_path)
        agent = list(config.agents.values())[0]

        # Add memory info to the agent
        agent.memory = Mock()
        agent.memory.memory_id = "test-memory-id"
        agent.memory.memory_name = "test-memory-name"

        config.agents[agent.name] = agent
        save_config(config, config_path)

        # Test that launch operation adds the memory env vars
        env_vars = {}

        # Instead of running the full launch, just call the specific part we want to test
        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import launch_bedrock_agentcore

        # Mock ContainerRuntime
        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime.build") as mock_build,
        ):
            mock_build.return_value = (True, ["Successfully built"])

            # Launch with our env_vars dictionary
            launch_bedrock_agentcore(config_path, local=True, env_vars=env_vars)

            # Check that memory vars were added to env_vars
            assert "BEDROCK_AGENTCORE_MEMORY_ID" in env_vars
            assert env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] == "test-memory-id"
            assert "BEDROCK_AGENTCORE_MEMORY_NAME" in env_vars
            assert env_vars["BEDROCK_AGENTCORE_MEMORY_NAME"] == "test-memory-name"

    def test_memory_configuration_handling(self, mock_container_runtime, tmp_path):
        """Test memory configuration handling in environment variables."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

        # Create config with memory already configured
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="app.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                network_configuration=NetworkConfiguration(),
            ),
            memory=MemoryConfig(
                enabled=True,
                enable_ltm=True,
                memory_name="test_memory",
                memory_id="mem-12345",  # Already has memory ID
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)
        create_test_agent_file(tmp_path, filename="app.py")
        create_test_dockerfile(tmp_path)

        mock_container_runtime.has_local_runtime = True
        mock_container_runtime.build.return_value = (True, ["Successfully built"])

        # Change to temp directory where app.py is located
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ):
                # Run locally
                result = launch_bedrock_agentcore(config_path, local=True)

                # Check that memory env vars were passed
                assert "BEDROCK_AGENTCORE_MEMORY_ID" in result.env_vars
                assert result.env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] == "mem-12345"
                assert "BEDROCK_AGENTCORE_MEMORY_NAME" in result.env_vars
                assert result.env_vars["BEDROCK_AGENTCORE_MEMORY_NAME"] == "test_memory"
        finally:
            os.chdir(original_cwd)

    def test_container_runtime_error_handling(self, mock_container_runtime, tmp_path):
        """Test error handling for container runtime issues."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Simulate runtime error that mentions container runtime
        mock_container_runtime.has_local_runtime = True
        mock_container_runtime.build.return_value = (False, ["Error: No container runtime available"])

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            # Should throw specific error with recommendation
            with pytest.raises(RuntimeError) as excinfo:
                launch_bedrock_agentcore(config_path, local=True)

            # Verify error contains helpful recommendation
            error_text = str(excinfo.value)
            assert "No container runtime available" in error_text
            assert "Recommendation:" in error_text
            assert "CodeBuild" in error_text

    def test_launch_missing_execution_role_no_auto_create(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test error when execution role not configured and auto-create disabled."""
        config_path = create_test_config(
            tmp_path,
            execution_role_auto_create=False,  # No auto-create and no execution role
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

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
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.iam_client = mock_iam_client  # Use provided IAM client
        mock_factory.setup_full_session_mock(mock_boto3_clients)

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
            result = launch_bedrock_agentcore(
                config_path, local=False, auto_update_on_conflict=True, use_codebuild=False
            )

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
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.iam_client = mock_iam_client  # Use provided IAM client
        mock_factory.setup_full_session_mock(mock_boto3_clients)

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
        existing_session_id = "existing-session-123"
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            agent_session_id=existing_session_id,  # Pre-existing session ID
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.iam_client = mock_iam_client  # Use provided IAM client
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

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
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            agent_session_id=None,  # No existing session ID
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Mock IAM client response for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/TestRole",
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                },
            }
        }

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.iam_client = mock_iam_client  # Use provided IAM client
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify deployment succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

            # Verify NO warning log was emitted about session ID reset
            # Check that warning was not called with the specific session ID reset message
            for call in mock_log.warning.call_args_list:
                assert "Session ID will be reset" not in str(call)

    def test_launch_local_mode_no_docker_runtime(self, tmp_path):
        """Test local mode when Docker is not available."""
        config_path = create_test_config(tmp_path)

        # Create a mock runtime without Docker available
        mock_runtime_no_docker = MagicMock()
        mock_runtime_no_docker.runtime = "none"
        mock_runtime_no_docker.has_local_runtime = False  # No Docker available

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_runtime_no_docker,
        ):
            with pytest.raises(RuntimeError, match="Cannot run locally - no container runtime available"):
                launch_bedrock_agentcore(config_path, local=True)

    def test_launch_with_codebuild_from_main_function(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test that environment variables are passed from launch_bedrock_agentcore to _launch_with_codebuild."""
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

        # Test environment variables
        test_env_vars = {"TEST_VAR1": "value1", "TEST_VAR2": "value2"}

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch._launch_with_codebuild"
        ) as mock_launch_with_codebuild:
            mock_launch_with_codebuild.return_value = MagicMock()

            # Run launch_bedrock_agentcore with use_codebuild=True and env_vars
            launch_bedrock_agentcore(config_path=config_path, use_codebuild=True, env_vars=test_env_vars)

            # Verify _launch_with_codebuild was called with the environment variables
            mock_launch_with_codebuild.assert_called_once()
            # Check that env_vars parameter was passed to _launch_with_codebuild
            assert mock_launch_with_codebuild.call_args.kwargs["env_vars"] == test_env_vars

    def test_launch_with_memory_creation_codebuild(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch with memory creation in CodeBuild mode."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                mode="STM_AND_LTM",  # Changed from enable_ltm=True
                memory_name="test-agent_memory",
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_create_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
            ) as mock_memory_manager_class,
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.ContainerRuntime") as mock_runtime_class,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute_workflow,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"
            mock_create_role.return_value = "arn:aws:iam::123456789012:role/TestRole"

            # Add these return values
            mock_execute_workflow.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            # Fix the memory manager mock setup
            mock_memory_manager = Mock()

            # Create a SimpleNamespace object for memory results
            memory_data = {"id": "mem_123456", "arn": "arn:aws:bedrock-memory:us-west-2:123456789012:memory/mem_123456"}
            memory_result = SimpleNamespace(**memory_data)

            # Set the methods to return the SimpleNamespace object
            mock_memory_manager.create_memory_and_wait.return_value = memory_result

            # Add item access
            def getitem(self, key):
                return memory_data[key]

            memory_result.__getitem__ = getitem.__get__(memory_result)

            mock_memory_manager.list_memories.return_value = []  # No existing memories
            mock_memory_manager_class.return_value = mock_memory_manager

            # Mock container runtime for Dockerfile regeneration
            mock_runtime = Mock()
            mock_runtime.generate_dockerfile.return_value = tmp_path / "Dockerfile"
            mock_runtime_class.return_value = mock_runtime

            # Call the function
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify memory creation was called with the right parameters
            mock_memory_manager.create_memory_and_wait.assert_called_once()  # CHANGED: Check create_memory_and_wait

            # Check parameters for create_memory_and_wait
            call_args = mock_memory_manager.create_memory_and_wait.call_args
            assert "name" in call_args[1]
            assert "description" in call_args[1]
            assert "strategies" in call_args[1]

            # Verify strategies were added for LTM
            strategies = call_args[1]["strategies"]
            assert len(strategies) == 3  # Should have 3 strategies for LTM

            # Verify result
            assert result.mode == "codebuild"
            assert hasattr(result, "agent_arn")

    def test_launch_with_existing_memory_needs_strategies(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch with existing memory that needs LTM strategies added."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                mode="STM_AND_LTM",  # Want LTM strategies
                memory_name="test-agent_mem",
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute_workflow,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"
            mock_ensure_memory.return_value = "mem_existing"  # Memory was found/created

            mock_execute_workflow.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify memory helper was called
            mock_ensure_memory.assert_called_once()

            # Verify deployment succeeded
            assert result.mode == "codebuild"

    def test_launch_with_memory_stm_only(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch with STM-only memory (no LTM strategies)."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                mode="STM_ONLY",  # CHANGED: Use mode instead of enabled/enable_ltm
                memory_name="test-agent_memory",
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_create_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
            ) as mock_memory_manager_class,
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.container.ContainerRuntime") as mock_runtime_class,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute_workflow,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"
            mock_create_role.return_value = "arn:aws:iam::123456789012:role/TestRole"

            # Add these return values
            mock_execute_workflow.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            # Setup memory manager mock - FIXED VERSION
            mock_memory_manager = Mock()
            mock_memory_manager.list_memories.return_value = []

            # Create a proper SimpleNamespace object with string attributes
            from types import SimpleNamespace

            memory_result = SimpleNamespace(
                id="mem_stm_123456", arn="arn:aws:bedrock-memory:us-west-2:123456789012:memory/mem_stm_123456"
            )

            # Mock create_memory_and_wait to return the SimpleNamespace
            mock_memory_manager.create_memory_and_wait.return_value = memory_result
            mock_memory_manager_class.return_value = mock_memory_manager

            # Mock container runtime for Dockerfile regeneration
            mock_runtime = Mock()
            mock_runtime.generate_dockerfile.return_value = tmp_path / "Dockerfile"
            mock_runtime_class.return_value = mock_runtime

            # Call the function
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify memory creation was called - FIXED
            mock_memory_manager.create_memory_and_wait.assert_called_once()

            # Check parameters for create_memory_and_wait
            call_args = mock_memory_manager.create_memory_and_wait.call_args
            assert "name" in call_args[1]
            assert "description" in call_args[1]
            assert "strategies" in call_args[1]

            # Verify NO strategies for STM-only (strategies list should be empty)
            strategies = call_args[1]["strategies"]
            assert len(strategies) == 0  # Should have no strategies for STM-only

            # Verify result
            assert result.mode == "codebuild"

    def test_launch_with_existing_memory(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch with existing memory (reuse instead of create)."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                enabled=True,
                enable_ltm=True,
                memory_name="test-agent_memory",
                event_expiry_days=30,
                memory_id="existing_mem_123",  # Already has memory ID
                memory_arn="arn:aws:memory:us-west-2:123456789012:memory/existing_mem_123",
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.memory.manager.MemoryManager"
            ) as mock_memory_manager_class,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"

            result = launch_bedrock_agentcore(config_path, local=False)
            mock_memory_manager_class.assert_not_called()

            # Verify result
            assert result.mode == "codebuild"

    def test_launch_with_memory_creation_failure_codebuild(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch continues when memory creation fails in CodeBuild mode."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                mode="STM_AND_LTM",
                memory_name="test-agent_mem",
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute_workflow,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"

            # Mock memory creation failure - returns None (graceful failure)
            mock_ensure_memory.return_value = None

            mock_execute_workflow.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            # Launch with CodeBuild
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify memory helper was called and failed gracefully
            mock_ensure_memory.assert_called_once()

            # Verify deployment continued despite memory failure
            assert result.mode == "codebuild"

    def test_launch_with_existing_memory_add_strategies(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch adds LTM strategies to existing memory that doesn't have them."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                mode="STM_AND_LTM",
                memory_name="test-agent_mem",
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute_workflow,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"
            mock_ensure_memory.return_value = "mem_with_strategies"

            mock_execute_workflow.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = ("agent-123", "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent/agent-123")

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify memory helper was called
            mock_ensure_memory.assert_called_once()

            # Verify deployment succeeded
            assert result.mode == "codebuild"

    def test_launch_non_codebuild_with_memory_failure(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test non-CodeBuild launch path handles memory creation failure gracefully."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                mode="STM_AND_LTM",
                memory_name="test-agent_mem",
                event_expiry_days=30,
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime") as mock_runtime_class,
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            #            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            # Mock memory creation failure - returns None (graceful failure)
            mock_ensure_memory.return_value = None

            # Mock container runtime
            mock_runtime = MagicMock()
            mock_runtime.has_local_runtime = True
            mock_runtime.build.return_value = (True, ["Successfully built"])
            mock_runtime_class.return_value = mock_runtime

            # Mock IAM validation
            mock_iam = MagicMock()
            mock_iam.get_role.return_value = {
                "Role": {
                    "AssumeRolePolicyDocument": {
                        "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                    }
                }
            }
            mock_boto3_clients["session"].client.return_value = mock_iam

            # Launch without CodeBuild - memory creation fails but continues
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify memory helper was called and failed gracefully
            assert mock_ensure_memory.call_count >= 1, "Expected _ensure_memory_for_agent to be called at least once"

            # Verify it continued despite memory failure
            assert result.mode == "cloud"

    def test_launch_non_codebuild_memory_error_handling(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test that non-CodeBuild path handles memory API errors gracefully."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

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
            memory=MemoryConfig(
                enabled=True,
                enable_ltm=True,
                memory_name="test-agent_memory",
                event_expiry_days=30,
                # No memory_id, so it will try to create
            ),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        with (
            # Mock the entire _ensure_memory_for_agent function - this is likely the source of the hang
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime") as mock_runtime_class,
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
            # Mock the BedrockAgentCoreClient creation and methods
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.BedrockAgentCoreClient"
            ) as mock_client_class,
        ):
            # Mock container runtime
            mock_runtime = MagicMock()
            mock_runtime.has_local_runtime = True
            mock_runtime.build.return_value = (True, ["Successfully built"])
            mock_runtime_class.return_value = mock_runtime

            # Mock IAM validation
            mock_iam = MagicMock()
            mock_iam.get_role.return_value = {
                "Role": {
                    "AssumeRolePolicyDocument": {
                        "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                    }
                }
            }
            mock_boto3_clients["session"].client.return_value = mock_iam

            # Mock the bedrock client
            mock_client = MagicMock()
            mock_client.create_or_update_agent.return_value = {
                "id": "agent-123",
                "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            }
            mock_client.wait_for_agent_endpoint_ready.return_value = "https://example.com"
            mock_client_class.return_value = mock_client

            # Add mock return value for _deploy_to_bedrock_agentcore
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            # Run the function
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Should succeed despite memory error
            assert result.mode == "cloud"

    def test_launch_local_with_invalid_config(self, mock_container_runtime, tmp_path):
        """Test error handling when launching locally with invalid configuration."""
        # Create config with missing required fields
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="nonexistent.py",  # Invalid non-existent entrypoint
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        # Should raise RuntimeError for missing Dockerfile (checked before entrypoint)
        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            with pytest.raises(RuntimeError, match="Dockerfile not found"):
                launch_bedrock_agentcore(config_path, local=True)

    def test_launch_local_with_custom_port(self, mock_container_runtime, tmp_path):
        """Test local deployment with custom port configuration."""
        config_path = create_test_config(tmp_path)
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock successful build
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])
        mock_container_runtime.has_local_runtime = True

        env_vars = {"PORT": "9000"}  # Custom port

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            result = launch_bedrock_agentcore(config_path, local=True, env_vars=env_vars)

            # Verify result has the default port (8080) since PORT env var is only used at runtime
            assert result.mode == "local"
            assert result.port == 8080
            assert result.tag == "bedrock_agentcore-test-agent:latest"

            # Verify env_vars were passed through
            assert "PORT" in result.env_vars
            assert result.env_vars["PORT"] == "9000"

    def test_launch_auto_update_on_conflict(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test auto_update_on_conflict flag is properly passed to deployment."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute_workflow,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            # Configure return values
            mock_execute_workflow.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            # Call with auto_update_on_conflict=True
            result = launch_bedrock_agentcore(config_path, local=False, auto_update_on_conflict=True)

            # Verify flag was passed through to _deploy_to_bedrock_agentcore
            mock_deploy.assert_called_once()
            assert mock_deploy.call_args.kwargs["auto_update_on_conflict"] is True

            # Verify successful deployment
            assert result.mode == "codebuild"
            assert result.agent_id == "agent-123"

    def test_launch_with_vpc_validation_success(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch with valid VPC configuration."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

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
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Mock EC2 client for VPC validation
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"},
                {"SubnetId": "subnet-xyz789ghi012", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2b"},
            ]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "sg-abc123xyz789", "VpcId": "vpc-test123"}]
        }

        # Mock IAM client for service-linked role
        mock_iam = MagicMock()
        mock_iam.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/aws-service-role/...",
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {"Effect": "Allow", "Principal": {"Service": "network.bedrock-agentcore.amazonaws.com"}}
                    ]
                },
            }
        }

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service, **kwargs: mock_ec2 if service == "ec2" else mock_iam

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session", return_value=mock_session
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_execute.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify VPC validation was performed
            mock_ec2.describe_subnets.assert_called_once_with(SubnetIds=["subnet-abc123def456", "subnet-xyz789ghi012"])
            mock_ec2.describe_security_groups.assert_called_once_with(GroupIds=["sg-abc123xyz789"])

            assert result.mode == "codebuild"

    def test_launch_with_vpc_local_mode_warning(self, mock_container_runtime, tmp_path):
        """Test that VPC config is ignored with warning in local mode."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        mock_container_runtime.build.return_value = (True, ["Successfully built"])
        mock_container_runtime.has_local_runtime = True

        # Change to temp directory where test_agent.py is located
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                    return_value=mock_container_runtime,
                ),
                patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
            ):
                result = launch_bedrock_agentcore(config_path, local=True)

                # Verify warning was logged
                mock_log.warning.assert_called_with(
                    "⚠️  VPC configuration detected but running in local mode. VPC settings will be ignored."
                )
                assert result.mode == "local"
        finally:
            os.chdir(original_cwd)

    def test_launch_with_build_context_source_path(self, mock_container_runtime, tmp_path):
        """Test launch with custom source_path for build context."""
        # Create source directory
        source_dir = tmp_path / "src"
        source_dir.mkdir()

        config_path = create_test_config(tmp_path)
        create_test_agent_file(source_dir)  # Agent file in source dir

        # Create Dockerfile in agentcore directory
        agentcore_dir = tmp_path / ".bedrock_agentcore" / "test-agent"
        agentcore_dir.mkdir(parents=True)
        dockerfile = agentcore_dir / "Dockerfile"
        dockerfile.write_text("FROM python:3.10\nCOPY . /app\n")

        # Update config to have source_path
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config, save_config

        config = load_config(config_path)
        agent = list(config.agents.values())[0]
        agent.source_path = str(source_dir)
        config.agents[agent.name] = agent
        save_config(config, config_path)

        mock_container_runtime.build.return_value = (True, ["Successfully built"])
        mock_container_runtime.has_local_runtime = True

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            result = launch_bedrock_agentcore(config_path, local=True)

            # Verify build was called with source directory as build context
            mock_container_runtime.build.assert_called_once()
            call_args = mock_container_runtime.build.call_args
            assert call_args[0][0] == source_dir  # build_dir should be source_dir
            assert result.mode == "local"

    def test_launch_with_memory_no_memory_mode(self, mock_container_runtime, tmp_path):
        """Test launch with memory mode set to NO_MEMORY."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region="us-west-2",
                account="123456789012",
                network_configuration=NetworkConfiguration(),
                observability=ObservabilityConfig(),
            ),
            memory=MemoryConfig(mode="NO_MEMORY"),  # Explicitly no memory
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        mock_container_runtime.build.return_value = (True, ["Successfully built"])
        mock_container_runtime.has_local_runtime = True

        # Change to temp directory where test_agent.py is located
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ):
                result = launch_bedrock_agentcore(config_path, local=True)

                # Should not have memory env vars
                assert "BEDROCK_AGENTCORE_MEMORY_ID" not in result.env_vars
                assert "BEDROCK_AGENTCORE_MEMORY_NAME" not in result.env_vars
                assert result.mode == "local"
        finally:
            os.chdir(original_cwd)

    def test_launch_cloud_with_region_from_config(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test cloud deployment uses region from agent config."""
        custom_region = "eu-central-1"
        config_path = create_test_config(
            tmp_path,
            region=custom_region,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.eu-central-1.amazonaws.com/test-repo",
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        mock_container_runtime.build.return_value = (True, ["Successfully built"])

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory(region=custom_region)
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
        ):
            # Mock deployment return values
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:eu-central-1:123456789012:agent-runtime/agent-123",
            )

            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify deployment used custom region
            assert result.mode == "cloud"

    def test_launch_vpc_validation_subnet_not_found(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch fails when subnet IDs don't exist."""
        from botocore.exceptions import ClientError

        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

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
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-nonexistent"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Mock EC2 client to return subnet not found error
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.side_effect = ClientError(
            {"Error": {"Code": "InvalidSubnetID.NotFound", "Message": "Subnet not found"}}, "DescribeSubnets"
        )

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session", return_value=mock_session
        ):
            with pytest.raises(ValueError, match="One or more subnet IDs not found"):
                launch_bedrock_agentcore(config_path, local=False)

    def test_launch_with_missing_region_error(self, mock_container_runtime, tmp_path):
        """Test error when region is missing from config."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        agent_config = BedrockAgentCoreAgentSchema(
            name="test-agent",
            entrypoint="test_agent.py",
            container_runtime="docker",
            aws=AWSConfig(
                region=None,  # Missing region
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

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        mock_container_runtime.build.return_value = (True, ["Successfully built"])
        mock_container_runtime.has_local_runtime = True

        with patch(
            "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
            return_value=mock_container_runtime,
        ):
            with pytest.raises(ValueError, match="Missing 'aws.region' for cloud deployment"):
                launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

    def test_launch_vpc_validation_cross_vpc_error(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test launch fails when subnets are in different VPCs."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

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
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Mock EC2 client - subnets in different VPCs
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [
                {"SubnetId": "subnet-abc123def456", "VpcId": "vpc-111"},
                {"SubnetId": "subnet-xyz789ghi012", "VpcId": "vpc-222"},  # Different VPC!
            ]
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session", return_value=mock_session
            ),
        ):
            with pytest.raises(ValueError, match="All subnets must be in the same VPC"):
                launch_bedrock_agentcore(config_path, local=False)

    def test_launch_vpc_service_linked_role_creation(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test that service-linked role is created for VPC networking."""
        from botocore.exceptions import ClientError

        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

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
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Mock EC2 and IAM clients
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"}]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "sg-abc123xyz789", "VpcId": "vpc-test123"}]
        }

        mock_iam = MagicMock()
        # Simulate role doesn't exist yet
        mock_iam.get_role.side_effect = ClientError(
            {"Error": {"Code": "NoSuchEntity", "Message": "Role not found"}}, "GetRole"
        )
        mock_iam.create_service_linked_role.return_value = {"Role": {"Arn": "arn:aws:iam::..."}}

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service, **kwargs: mock_ec2 if service == "ec2" else mock_iam

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session", return_value=mock_session
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_execute.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify service-linked role creation was called
            mock_iam.create_service_linked_role.assert_called_once_with(
                AWSServiceName="network.bedrock-agentcore.amazonaws.com",
                Description="Service-linked role for Amazon Bedrock AgentCore VPC networking",
            )

            assert result.mode == "codebuild"

    def test_launch_vpc_service_linked_role_already_exists(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test that existing service-linked role is reused."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

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
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Mock EC2 and IAM clients
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-test123", "AvailabilityZone": "us-west-2a"}]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "sg-abc123xyz789", "VpcId": "vpc-test123"}]
        }

        mock_iam = MagicMock()
        # Role already exists
        mock_iam.get_role.return_value = {
            "Role": {
                "Arn": "arn:aws:iam::123456789012:role/aws-service-role/...",
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {"Effect": "Allow", "Principal": {"Service": "network.bedrock-agentcore.amazonaws.com"}}
                    ]
                },
            }
        }

        mock_session = MagicMock()
        mock_session.client.side_effect = lambda service, **kwargs: mock_ec2 if service == "ec2" else mock_iam

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session", return_value=mock_session
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
        ):
            mock_execute.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )
            mock_deploy.return_value = (
                "agent-123",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            )

            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify role creation was NOT called (role exists)
            mock_iam.create_service_linked_role.assert_not_called()

            assert result.mode == "codebuild"

    def test_launch_vpc_validation_security_group_different_vpc(
        self, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test launch fails when security groups are in different VPC than subnets."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration, NetworkModeConfig

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
                network_configuration=NetworkConfiguration(
                    network_mode="VPC",
                    network_mode_config=NetworkModeConfig(
                        subnets=["subnet-abc123def456"],
                        security_groups=["sg-abc123xyz789"],
                    ),
                ),
                observability=ObservabilityConfig(),
            ),
            bedrock_agentcore=BedrockAgentCoreDeploymentInfo(),
        )
        project_config = BedrockAgentCoreConfigSchema(default_agent="test-agent", agents={"test-agent": agent_config})
        save_config(project_config, config_path)

        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)

        # Mock EC2 client - SG in different VPC
        mock_ec2 = MagicMock()
        mock_ec2.describe_subnets.return_value = {
            "Subnets": [{"SubnetId": "subnet-abc123def456", "VpcId": "vpc-111", "AvailabilityZone": "us-west-2a"}]
        }
        mock_ec2.describe_security_groups.return_value = {
            "SecurityGroups": [{"GroupId": "sg-abc123xyz789", "VpcId": "vpc-222"}]  # Different VPC!
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session", return_value=mock_session
            ),
        ):
            with pytest.raises(ValueError, match="Security groups must be in the same VPC as subnets"):
                launch_bedrock_agentcore(config_path, local=False)

    def test_check_vpc_deployment_no_enis_found(self, mock_boto3_clients, tmp_path):
        """Test VPC deployment diagnostic when no ENIs are found yet."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _check_vpc_deployment

        mock_ec2 = MagicMock()
        mock_ec2.describe_network_interfaces.return_value = {
            "NetworkInterfaces": []  # No ENIs found
        }

        mock_session = MagicMock()
        mock_session.client.return_value = mock_ec2

        with patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log:
            # Should not raise - just log diagnostics
            _check_vpc_deployment(mock_session, "agent-123", ["subnet-abc123"], "us-west-2")

            # Verify diagnostic logging
            assert mock_log.info.called
            assert any(
                "VPC network interfaces will be created on first invocation" in str(call)
                for call in mock_log.info.call_args_list
            )

    def test_validate_vpc_resources_public_mode_early_return(self, tmp_path):
        """Test that VPC validation is skipped for PUBLIC network mode."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _validate_vpc_resources
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import NetworkConfiguration

        # Create agent config with PUBLIC mode (not VPC)
        agent_config = MagicMock()
        agent_config.aws = MagicMock()
        agent_config.aws.network_configuration = NetworkConfiguration(network_mode="PUBLIC")

        mock_session = MagicMock()
        mock_ec2 = mock_session.client.return_value

        # Should return early without calling EC2 describe methods
        _validate_vpc_resources(mock_session, agent_config, "us-west-2")

        # Verify EC2 was NOT called (early return for PUBLIC mode)
        mock_ec2.describe_subnets.assert_not_called()
        mock_ec2.describe_security_groups.assert_not_called()

    def test_validate_vpc_resources_missing_config(self, tmp_path):
        """Test validation fails when VPC mode has no network_mode_config."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _validate_vpc_resources

        # Create a mock agent_config with network_mode=VPC but no network_mode_config
        agent_config = MagicMock()
        agent_config.aws = MagicMock()
        network_config = MagicMock()
        network_config.network_mode = "VPC"
        network_config.network_mode_config = None
        agent_config.aws.network_configuration = network_config

        mock_session = MagicMock()

        with pytest.raises(ValueError, match="VPC mode requires network configuration"):
            _validate_vpc_resources(mock_session, agent_config, "us-west-2")


class TestEnsureExecutionRole:
    """Test _ensure_execution_role functionality."""

    def test_ensure_execution_role_auto_create_success(self, mock_boto3_clients, tmp_path):
        """Test successful execution role auto-creation."""
        config_path = create_test_config(tmp_path, execution_role_auto_create=True)

        # Load the config to get the agent and project configs
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        project_config = load_config(config_path)
        agent_config = project_config.agents["test-agent"]

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

        config_path = create_test_config(
            tmp_path,
            execution_role=existing_role_arn,
            execution_role_auto_create=True,  # Should be ignored
        )

        # Load the config to get the agent and project configs
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        project_config = load_config(config_path)
        agent_config = project_config.agents["test-agent"]

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
        config_path = create_test_config(tmp_path, execution_role_auto_create=False)

        # Load the config to get the agent and project configs
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        project_config = load_config(config_path)
        agent_config = project_config.agents["test-agent"]

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
        config_path = create_test_config(tmp_path, execution_role_auto_create=True)

        # Load the config to get the agent and project configs
        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        project_config = load_config(config_path)
        agent_config = project_config.agents["test-agent"]

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

    def test_launch_with_codebuild_passes_env_vars(self, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test that environment variables are passed with CodeBuild deployment."""
        from bedrock_agentcore_starter_toolkit.operations.runtime.launch import _launch_with_codebuild

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

        # Mock CodeBuild service
        mock_codebuild_service = MagicMock()
        mock_codebuild_service.create_codebuild_execution_role.return_value = (
            "arn:aws:iam::123456789012:role/CodeBuildRole"
        )
        mock_codebuild_service.upload_source.return_value = "s3://test-bucket/test-source.zip"
        mock_codebuild_service.create_or_update_project.return_value = "test-project"
        mock_codebuild_service.start_build.return_value = "test-build-id"
        mock_codebuild_service.wait_for_completion.return_value = None
        mock_codebuild_service.source_bucket = "test-bucket"

        # Test environment variables
        test_env_vars = {"TEST_VAR1": "value1", "TEST_VAR2": "value2"}

        # Mock IAM client for role validation
        mock_iam_client = MagicMock()
        mock_iam_client.get_role.return_value = {
            "Role": {
                "AssumeRolePolicyDocument": {
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"}}]
                }
            }
        }

        with (
            # Mock memory operations to prevent hanging
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent",
                return_value=None,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._execute_codebuild_workflow"
            ) as mock_execute_workflow,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.CodeBuildService",
                return_value=mock_codebuild_service,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._deploy_to_bedrock_agentcore"
            ) as mock_deploy,
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.boto3.Session") as mock_session,
            # Mock the BedrockAgentCoreClient to prevent hanging on wait operations
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.BedrockAgentCoreClient"
            ) as mock_client_class,
        ):
            # Set up the session's client method to return our mock IAM client
            mock_session.return_value.client.return_value = mock_iam_client

            # Setup BedrockAgentCoreClient mock
            mock_client = MagicMock()
            mock_client.create_or_update_agent.return_value = {
                "id": "agent-123",
                "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/agent-123",
            }
            mock_client.wait_for_agent_endpoint_ready.return_value = "https://example.com"
            mock_client_class.return_value = mock_client

            # Add mock return values for CodeBuild workflow
            mock_execute_workflow.return_value = (
                "build-123",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
                "us-west-2",
                "123456789012",
            )

            # Configure _deploy_to_bedrock_agentcore mock to return agent_id and agent_arn
            mock_deploy.return_value = (
                "test-agent-id",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent/test-agent-id",
            )

            # Run _launch_with_codebuild with environment variables
            _launch_with_codebuild(
                config_path=config_path,
                agent_name="test-agent",
                agent_config=agent_config,
                project_config=project_config,
                env_vars=test_env_vars,
            )

            # Verify _deploy_to_bedrock_agentcore was called with the environment variables
            mock_deploy.assert_called_once()
            # Check the env_vars parameter
            assert mock_deploy.call_args.kwargs["env_vars"] == test_env_vars


class TestTransactionSearchIntegration:
    """Test Transaction Search integration in launch operation."""

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.enable_transaction_search_if_needed")
    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_genai_observability_url")
    def test_transaction_search_called_when_observability_enabled(
        self, mock_get_url, mock_enable_transaction_search, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that transaction search is called when observability is enabled."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            observability_enabled=True,  # Enable observability
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock successful transaction search
        mock_enable_transaction_search.return_value = True
        mock_get_url.return_value = "https://console.aws.amazon.com/genai-observability"

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify deployment succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

            # Verify transaction search was called with correct parameters
            mock_enable_transaction_search.assert_called_once_with("us-west-2", "123456789012")

            # Verify GenAI observability dashboard URL was logged
            mock_get_url.assert_called_once_with("us-west-2")
            mock_log.info.assert_any_call("Observability is enabled, configuring Transaction Search...")
            mock_log.info.assert_any_call("🔍 GenAI Observability Dashboard:")
            mock_log.info.assert_any_call("   %s", "https://console.aws.amazon.com/genai-observability")

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.enable_transaction_search_if_needed")
    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_genai_observability_url")
    def test_transaction_search_not_called_when_observability_disabled(
        self, mock_get_url, mock_enable_transaction_search, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that transaction search is NOT called when observability is disabled."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            observability_enabled=False,  # Disable observability
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify deployment succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

            # Verify transaction search was NOT called
            mock_enable_transaction_search.assert_not_called()
            mock_get_url.assert_not_called()

            # Verify observability logs were NOT emitted
            log_calls = [call.args[0] for call in mock_log.info.call_args_list]
            assert "Observability is enabled, configuring Transaction Search..." not in log_calls
            assert "🔍 GenAI Observability Dashboard:" not in log_calls

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.enable_transaction_search_if_needed")
    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_genai_observability_url")
    def test_launch_continues_when_transaction_search_fails(
        self, mock_get_url, mock_enable_transaction_search, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test that launch continues even if transaction search fails."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_repository="123456789012.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            observability_enabled=True,  # Enable observability
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock failed transaction search
        mock_enable_transaction_search.return_value = False
        mock_get_url.return_value = "https://console.aws.amazon.com/genai-observability"

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            # Should not raise exception even if transaction search fails
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify deployment still succeeded
            assert result.mode == "cloud"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

            # Verify transaction search was attempted
            mock_enable_transaction_search.assert_called_once_with("us-west-2", "123456789012")

            # Verify GenAI dashboard URL was still shown (transaction search failure doesn't prevent this)
            mock_get_url.assert_called_once_with("us-west-2")
            mock_log.info.assert_any_call("🔍 GenAI Observability Dashboard:")
            mock_log.info.assert_any_call("   %s", "https://console.aws.amazon.com/genai-observability")

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.enable_transaction_search_if_needed")
    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_genai_observability_url")
    def test_transaction_search_with_codebuild_deployment(
        self, mock_get_url, mock_enable_transaction_search, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test transaction search integration with CodeBuild deployment."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            ecr_auto_create=True,
            observability_enabled=True,  # Enable observability
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock successful transaction search
        mock_enable_transaction_search.return_value = True
        mock_get_url.return_value = "https://console.aws.amazon.com/genai-observability"

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.get_or_create_ecr_repository") as mock_create_ecr,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.get_or_create_runtime_execution_role"
            ) as mock_create_role,
            patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.log") as mock_log,
        ):
            mock_create_ecr.return_value = "123456789012.dkr.ecr.us-west-2.amazonaws.com/bedrock_agentcore-test-agent"
            mock_create_role.return_value = "arn:aws:iam::123456789012:role/TestRole"

            # Test with CodeBuild (default use_codebuild=True)
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify CodeBuild deployment succeeded
            assert result.mode == "codebuild"
            assert hasattr(result, "agent_arn")
            assert hasattr(result, "agent_id")

            # Verify transaction search was called
            mock_enable_transaction_search.assert_called_once_with("us-west-2", "123456789012")

            # Verify observability logs were emitted
            mock_log.info.assert_any_call("Observability is enabled, configuring Transaction Search...")
            mock_log.info.assert_any_call("🔍 GenAI Observability Dashboard:")

    @patch("bedrock_agentcore_starter_toolkit.operations.runtime.launch.enable_transaction_search_if_needed")
    def test_transaction_search_with_different_regions(
        self, mock_enable_transaction_search, mock_boto3_clients, mock_container_runtime, tmp_path
    ):
        """Test transaction search is called with correct region parameter."""
        test_region = "eu-west-1"
        test_account = "987654321098"

        config_path = create_test_config(
            tmp_path,
            region=test_region,
            account=test_account,
            execution_role="arn:aws:iam::987654321098:role/TestRole",
            ecr_repository="987654321098.dkr.ecr.eu-west-1.amazonaws.com/test-repo",
            observability_enabled=True,
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock successful transaction search
        mock_enable_transaction_search.return_value = True

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        # Setup mock AWS clients for different region/account
        mock_factory = MockAWSClientFactory(account=test_account, region=test_region)
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch("bedrock_agentcore_starter_toolkit.services.ecr.deploy_to_ecr"),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
        ):
            result = launch_bedrock_agentcore(config_path, local=False, use_codebuild=False)

            # Verify deployment succeeded
            assert result.mode == "cloud"

            # Verify transaction search was called with correct region and account
            mock_enable_transaction_search.assert_called_once_with(test_region, test_account)

    def test_transaction_search_not_called_in_local_mode(self, mock_container_runtime, tmp_path):
        """Test that transaction search is NOT called in local mode, even with observability enabled."""
        config_path = create_test_config(
            tmp_path,
            observability_enabled=True,  # Enable observability
        )
        create_test_agent_file(tmp_path)
        create_test_dockerfile(tmp_path)  # Add Dockerfile for validation

        # Mock the build to return success
        mock_container_runtime.build.return_value = (True, ["Successfully built test-image"])

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.ContainerRuntime",
                return_value=mock_container_runtime,
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.enable_transaction_search_if_needed"
            ) as mock_enable_transaction_search,
        ):
            result = launch_bedrock_agentcore(config_path, local=True)

            # Verify local deployment succeeded
            assert result.mode == "local"

            # Verify transaction search was NOT called (local mode doesn't deploy to cloud)
            mock_enable_transaction_search.assert_not_called()


class TestCodeZipDeployment:
    """Tests for direct_code_deploy deployment workflow."""

    def test_launch_with_direct_code_deploy_success(self, mock_boto3_clients, tmp_path):
        """Test successful direct_code_deploy deployment with all steps."""
        # Create config with direct_code_deploy deployment
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
        )

        # Create agent file
        create_test_agent_file(tmp_path, "test_agent.py", "def handler(event, context): return {}")

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        # Override bedrock_agentcore mock for direct_code_deploy workflow
        mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.return_value = {
            "agentRuntimeId": "test-agent-123",
            "agentRuntimeArn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent-123",
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role"
            ) as mock_ensure_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.create_deployment_package"
            ) as mock_create_package,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.upload_to_s3"
            ) as mock_upload_s3,
            patch("shutil.which") as mock_which,
        ):
            # Setup mocks
            mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd in ["uv", "zip"] else None
            mock_ensure_role.return_value = "arn:aws:iam::123456789012:role/TestRole"
            mock_ensure_memory.return_value = None

            # Mock deployment package creation (in subdirectory to avoid cleanup conflicts)
            mock_deployment_dir = tmp_path / "mock_package"
            mock_deployment_dir.mkdir()
            mock_deployment_zip = mock_deployment_dir / "deployment.zip"
            mock_deployment_zip.write_bytes(b"fake zip content")
            mock_create_package.return_value = (mock_deployment_zip, False)  # (Path, has_otel_distro)

            # Mock S3 upload
            mock_upload_s3.return_value = "s3://test-bucket/test-agent/deployment.zip"

            # Execute launch
            result = launch_bedrock_agentcore(config_path, local=False)

            # Verify result
            assert result.mode == "direct_code_deploy"
            assert result.agent_arn == "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent-123"
            assert result.agent_id == "test-agent-123"
            # Note: s3_location is not part of LaunchResult model, so it won't be in the result

            # Verify workflow steps called
            mock_ensure_role.assert_called_once()
            mock_ensure_memory.assert_called_once()
            mock_create_package.assert_called_once()
            mock_upload_s3.assert_called_once()
            # Verify S3 upload was called with correct location
            assert mock_upload_s3.return_value == "s3://test-bucket/test-agent/deployment.zip"
            mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.assert_called_once()

    def test_launch_with_direct_code_deploy_package_creation_failure(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment handles create_deployment_package failure gracefully."""
        # Create config with direct_code_deploy deployment
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
        )

        # Create agent file
        create_test_agent_file(tmp_path, "test_agent.py", "def handler(event, context): return {}")

        # Setup mock AWS clients
        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role"
            ) as mock_ensure_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.create_deployment_package"
            ) as mock_create_package,
            patch("shutil.which") as mock_which,
        ):
            # Setup mocks
            mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd in ["uv", "zip"] else None
            mock_ensure_role.return_value = "arn:aws:iam::123456789012:role/TestRole"
            mock_ensure_memory.return_value = None

            # Simulate create_deployment_package failure
            mock_create_package.side_effect = RuntimeError("Failed to install dependencies")

            # Execute launch and verify it raises the correct error
            with pytest.raises(RuntimeError, match="Failed to install dependencies"):
                launch_bedrock_agentcore(config_path, local=False)

            # Verify that execution stopped at package creation
            mock_ensure_role.assert_called_once()
            mock_ensure_memory.assert_called_once()
            mock_create_package.assert_called_once()

            # Verify agent was not created (since package creation failed)
            mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.assert_not_called()

    def test_launch_with_direct_code_deploy_missing_uv(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment fails if uv not installed."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
        )
        create_test_agent_file(tmp_path)

        with (
            patch("shutil.which") as mock_which,
        ):
            # uv not found
            mock_which.return_value = None

            with pytest.raises(RuntimeError, match="uv is required for direct_code_deploy deployment"):
                launch_bedrock_agentcore(config_path, local=False)

    def test_launch_with_direct_code_deploy_missing_zip(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment fails if zip utility not installed."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
        )
        create_test_agent_file(tmp_path)

        with (
            patch("shutil.which") as mock_which,
        ):
            # uv found, zip not found
            mock_which.side_effect = lambda cmd: "/usr/bin/uv" if cmd == "uv" else None

            with pytest.raises(RuntimeError, match="zip utility is required"):
                launch_bedrock_agentcore(config_path, local=False)

    def test_launch_with_direct_code_deploy_with_memory(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment with memory enabled."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
        )
        create_test_agent_file(tmp_path)

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role"
            ) as mock_ensure_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.create_deployment_package"
            ) as mock_create_package,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.upload_to_s3"
            ) as mock_upload_s3,
            patch("shutil.which") as mock_which,
        ):
            mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd in ["uv", "zip"] else None
            mock_ensure_role.return_value = "arn:aws:iam::123456789012:role/TestRole"
            mock_ensure_memory.return_value = "memory-123"  # Memory created

            # Create deployment.zip in a subdirectory to avoid cleanup removing config
            mock_deployment_dir = tmp_path / "mock_package"
            mock_deployment_dir.mkdir()
            mock_deployment_zip = mock_deployment_dir / "deployment.zip"
            mock_deployment_zip.write_bytes(b"fake zip")
            mock_create_package.return_value = (mock_deployment_zip, False)
            mock_upload_s3.return_value = "s3://test-bucket/test-agent/deployment.zip"

            result = launch_bedrock_agentcore(config_path, local=False)

            assert result.mode == "direct_code_deploy"
            assert result.agent_id == "test-agent-id"  # From conftest mock

            # Verify memory was ensured
            mock_ensure_memory.assert_called_once()

    def test_launch_with_direct_code_deploy_force_rebuild(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment with force_rebuild_deps flag."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
        )
        create_test_agent_file(tmp_path)

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role"
            ) as mock_ensure_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.create_deployment_package"
            ) as mock_create_package,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.upload_to_s3"
            ) as mock_upload_s3,
            patch("bedrock_agentcore_starter_toolkit.services.runtime.BedrockAgentCoreClient") as mock_runtime_client,
            patch("shutil.which") as mock_which,
        ):
            mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd in ["uv", "zip"] else None
            mock_ensure_role.return_value = "arn:aws:iam::123456789012:role/TestRole"
            mock_ensure_memory.return_value = None

            # Create deployment.zip in a subdirectory to avoid cleanup removing config
            mock_deployment_dir = tmp_path / "mock_package"
            mock_deployment_dir.mkdir()
            mock_deployment_zip = mock_deployment_dir / "deployment.zip"
            mock_deployment_zip.write_bytes(b"fake zip")
            mock_create_package.return_value = (mock_deployment_zip, False)
            mock_upload_s3.return_value = "s3://test-bucket/test-agent/deployment.zip"

            mock_client = Mock()
            mock_client.create_or_update_agent.return_value = {
                "id": "test-agent-123",
                "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent-123",
            }
            mock_client.wait_for_agent_endpoint_ready.return_value = None
            mock_runtime_client.return_value = mock_client

            # Launch with force_rebuild_deps=True
            result = launch_bedrock_agentcore(config_path, local=False, force_rebuild_deps=True)

            assert result.mode == "direct_code_deploy"

            # Verify create_deployment_package was called with force_rebuild_deps=True
            mock_create_package.assert_called_once()
            call_kwargs = mock_create_package.call_args[1]
            assert call_kwargs["force_rebuild_deps"] is True

    def test_launch_with_direct_code_deploy_with_env_vars(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment passes environment variables correctly."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
        )
        create_test_agent_file(tmp_path)

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role"
            ) as mock_ensure_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.create_deployment_package"
            ) as mock_create_package,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.upload_to_s3"
            ) as mock_upload_s3,
            patch("shutil.which") as mock_which,
        ):
            mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd in ["uv", "zip"] else None
            mock_ensure_role.return_value = "arn:aws:iam::123456789012:role/TestRole"
            mock_ensure_memory.return_value = None

            # Create deployment.zip in a subdirectory to avoid cleanup removing config
            mock_deployment_dir = tmp_path / "mock_package"
            mock_deployment_dir.mkdir()
            mock_deployment_zip = mock_deployment_dir / "deployment.zip"
            mock_deployment_zip.write_bytes(b"fake zip")
            mock_create_package.return_value = (mock_deployment_zip, False)
            mock_upload_s3.return_value = "s3://test-bucket/test-agent/deployment.zip"

            # Launch with custom env vars
            custom_env = {"MY_VAR": "test_value", "DEBUG": "true"}
            result = launch_bedrock_agentcore(config_path, local=False, env_vars=custom_env)

            assert result.mode == "direct_code_deploy"
            assert result.agent_id == "test-agent-id"  # From conftest mock

            # Verify that create_agent_runtime was called with env vars
            call_kwargs = mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.call_args[1]
            assert "environmentVariables" in call_kwargs
            env_vars_dict = call_kwargs["environmentVariables"]
            # Service layer passes env_vars as dict, not AWS format list
            assert isinstance(env_vars_dict, dict)
            assert "MY_VAR" in env_vars_dict
            assert env_vars_dict["MY_VAR"] == "test_value"

    def test_launch_with_direct_code_deploy_with_observability(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment with observability enabled."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
            observability_enabled=True,
        )
        create_test_agent_file(tmp_path)

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role"
            ) as mock_ensure_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.create_deployment_package"
            ) as mock_create_package,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.upload_to_s3"
            ) as mock_upload_s3,
            patch("bedrock_agentcore_starter_toolkit.services.runtime.BedrockAgentCoreClient") as mock_runtime_client,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch.enable_transaction_search_if_needed"
            ) as mock_enable_xray,
            patch("shutil.which") as mock_which,
        ):
            mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd in ["uv", "zip"] else None
            mock_ensure_role.return_value = "arn:aws:iam::123456789012:role/TestRole"
            mock_ensure_memory.return_value = None

            # Create deployment.zip in a subdirectory to avoid cleanup removing config
            mock_deployment_dir = tmp_path / "mock_package"
            mock_deployment_dir.mkdir()
            mock_deployment_zip = mock_deployment_dir / "deployment.zip"
            mock_deployment_zip.write_bytes(b"fake zip")
            mock_create_package.return_value = (mock_deployment_zip, False)
            mock_upload_s3.return_value = "s3://test-bucket/test-agent/deployment.zip"

            mock_client = Mock()
            mock_client.create_or_update_agent.return_value = {
                "id": "test-agent-123",
                "arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/test-agent-123",
            }
            mock_client.wait_for_agent_endpoint_ready.return_value = None
            mock_runtime_client.return_value = mock_client

            result = launch_bedrock_agentcore(config_path, local=False)

            assert result.mode == "direct_code_deploy"

            # Verify observability was enabled
            mock_enable_xray.assert_called_once_with("us-west-2", "123456789012")

    def test_launch_with_direct_code_deploy_session_id_reset(self, mock_boto3_clients, tmp_path):
        """Test direct_code_deploy deployment resets existing session_id with warning."""
        config_path = create_test_config(
            tmp_path,
            execution_role="arn:aws:iam::123456789012:role/TestRole",
            deployment_type="direct_code_deploy",
            agent_session_id="old-session-123",  # Existing session ID
        )
        create_test_agent_file(tmp_path)

        mock_factory = MockAWSClientFactory()
        mock_factory.setup_full_session_mock(mock_boto3_clients)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_execution_role"
            ) as mock_ensure_role,
            patch(
                "bedrock_agentcore_starter_toolkit.operations.runtime.launch._ensure_memory_for_agent"
            ) as mock_ensure_memory,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.create_deployment_package"
            ) as mock_create_package,
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager.upload_to_s3"
            ) as mock_upload_s3,
            patch("shutil.which") as mock_which,
        ):
            mock_which.side_effect = lambda cmd: f"/usr/bin/{cmd}" if cmd in ["uv", "zip"] else None
            mock_ensure_role.return_value = "arn:aws:iam::123456789012:role/TestRole"
            mock_ensure_memory.return_value = None

            # Create deployment.zip in a subdirectory to avoid cleanup removing config
            mock_deployment_dir = tmp_path / "mock_package"
            mock_deployment_dir.mkdir()
            mock_deployment_zip = mock_deployment_dir / "deployment.zip"
            mock_deployment_zip.write_bytes(b"fake zip")
            mock_create_package.return_value = (mock_deployment_zip, False)
            mock_upload_s3.return_value = "s3://test-bucket/test-agent/deployment.zip"

            # Launch (should reset session_id)
            result = launch_bedrock_agentcore(config_path, local=False)

            assert result.mode == "direct_code_deploy"
            assert result.agent_id == "test-agent-id"  # From conftest mock

            # Verify config was updated with session_id reset
            from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

            updated_config = load_config(config_path)
            agent = updated_config.agents["test-agent"]
            assert agent.bedrock_agentcore.agent_session_id is None
