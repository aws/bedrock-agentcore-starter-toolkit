"""Tests for Bedrock AgentCore Jupyter notebook interface."""

from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit import Runtime


class TestBedrockAgentCoreNotebook:
    """Test Bedrock AgentCore notebook interface functionality."""

    def test_bedrock_agentcore_initialization(self):
        """Test Bedrock AgentCore initialization."""
        bedrock_agentcore = Runtime()
        assert bedrock_agentcore._config_path is None

    def test_configure_success(self, mock_bedrock_agentcore_app, mock_boto3_clients, mock_container_runtime, tmp_path):
        """Test successful configuration."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
bedrock_agentcore = BedrockAgentCoreApp()

@bedrock_agentcore.entrypoint
def handler(payload):
    return {"result": "success"}
""")

        bedrock_agentcore = Runtime()

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
            ) as mock_configure,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                auto_create_ecr=True,
                container_runtime="docker",
            )

            # Verify configure was called with correct parameters
            mock_configure.assert_called_once()
            args, kwargs = mock_configure.call_args
            assert kwargs["execution_role"] == "arn:aws:iam::123456789012:role/TestRole"
            assert kwargs["auto_create_ecr"] is True

            # Verify config path was stored
            assert bedrock_agentcore._config_path == tmp_path / ".bedrock_agentcore.yaml"

    def test_configure_with_requirements_generation(self, tmp_path):
        """Test requirements.txt generation when requirements list is provided."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
            ) as mock_configure,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file), execution_role="test-role", requirements=["requests", "boto3", "pandas"]
            )

            # Check that requirements.txt was created
            req_file = agent_file.parent / "requirements.txt"
            assert req_file.exists()
            content = req_file.read_text()
            assert "requests" in content
            assert "boto3" in content
            assert "pandas" in content

    def test_launch_without_config(self):
        """Test launch fails when not configured."""
        bedrock_agentcore = Runtime()

        with pytest.raises(ValueError, match="Must configure before launching"):
            bedrock_agentcore.launch()

    def test_launch_local(self, tmp_path):
        """Test local launch."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create Dockerfile for the test
        dockerfile_path = tmp_path / "Dockerfile"
        dockerfile_path.write_text("FROM python:3.10\nCOPY . .\nRUN pip install -e .\nCMD ['python', 'test_agent.py']")

        # Create a config file with required AWS fields for cloud deployment
        config_text = """
name: test-agent
platform: linux/amd64
entrypoint: test_agent.py
container_runtime: docker
aws:
  execution_role: arn:aws:iam::123456789012:role/TestRole
  region: us-west-2
  account: '123456789012'
"""
        config_path.write_text(config_text)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.launch_bedrock_agentcore"
            ) as mock_launch,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.mode = "local"
            mock_result.tag = "test-image:latest"
            mock_launch.return_value = mock_result

            result = bedrock_agentcore.launch(local=True)

            mock_launch.assert_called_once_with(config_path, local=True, push_ecr_only=False, env_vars=None)
            assert result.mode == "local"

    def test_launch_cloud(self, tmp_path):
        """Test cloud launch."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a config file with required AWS fields for cloud deployment
        config_text = """
name: test-agent
platform: linux/amd64
entrypoint: test_agent.py
container_runtime: docker
aws:
  execution_role: arn:aws:iam::123456789012:role/TestRole
  region: us-west-2
  account: '123456789012'
"""
        config_path.write_text(config_text)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.launch_bedrock_agentcore"
            ) as mock_launch,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.mode = "cloud"
            mock_result.agent_arn = "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id"
            mock_launch.return_value = mock_result

            result = bedrock_agentcore.launch()

            mock_launch.assert_called_once_with(config_path, local=False, push_ecr_only=False, env_vars=None)
            assert result.mode == "cloud"

    def test_launch_push_ecr(self, tmp_path):
        """Test ECR push only."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a config file with required AWS fields for cloud deployment
        config_text = """
name: test-agent
platform: linux/amd64
entrypoint: test_agent.py
container_runtime: docker
aws:
  execution_role: arn:aws:iam::123456789012:role/TestRole
  region: us-west-2
  account: '123456789012'
"""
        config_path.write_text(config_text)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.launch_bedrock_agentcore"
            ) as mock_launch,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.mode = "push-ecr"
            mock_result.ecr_uri = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test"
            mock_launch.return_value = mock_result

            result = bedrock_agentcore.launch(push_ecr=True)

            mock_launch.assert_called_once_with(config_path, local=False, push_ecr_only=True, env_vars=None)
            assert result.mode == "push-ecr"

    def test_invoke_without_config(self):
        """Test invoke fails when not configured."""
        bedrock_agentcore = Runtime()

        with pytest.raises(ValueError, match="Must configure and launch first"):
            bedrock_agentcore.invoke({"test": "payload"})

    def test_invoke_success(self, tmp_path):
        """Test successful invocation."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a config file with AWS fields and deployment info for invoke
        config_text = """
name: test-agent
platform: linux/amd64
entrypoint: test_agent.py
container_runtime: docker
aws:
  execution_role: arn:aws:iam::123456789012:role/TestRole
  region: us-west-2
  account: '123456789012'
bedrock_agentcore:
  agent_arn: arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id
"""
        config_path.write_text(config_text)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.invoke_bedrock_agentcore"
            ) as mock_invoke,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_invoke.return_value = mock_result

            response = bedrock_agentcore.invoke({"message": "hello"}, session_id="test-session")

            mock_invoke.assert_called_once_with(
                config_path=config_path,
                payload={"message": "hello"},
                session_id="test-session",
                bearer_token=None,
                local_mode=False,
                user_id=None,
            )
            assert response == {"result": "success"}

    def test_invoke_with_bearer_token(self, tmp_path):
        """Test invocation with bearer token."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a config file with AWS fields and deployment info for invoke
        config_text = """
name: test-agent
platform: linux/amd64
entrypoint: test_agent.py
container_runtime: docker
aws:
  execution_role: arn:aws:iam::123456789012:role/TestRole
  region: us-west-2
  account: '123456789012'
bedrock_agentcore:
  agent_arn: arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id
"""
        config_path.write_text(config_text)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.invoke_bedrock_agentcore"
            ) as mock_invoke,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_invoke.return_value = mock_result

            bedrock_agentcore.invoke({"message": "hello"}, bearer_token="test-token")

            mock_invoke.assert_called_once_with(
                config_path=config_path,
                payload={"message": "hello"},
                session_id=None,
                bearer_token="test-token",
                local_mode=False,
                user_id=None,
            )

    def test_status_without_config(self):
        """Test status fails when not configured."""
        bedrock_agentcore = Runtime()

        with pytest.raises(ValueError, match="Must configure first"):
            bedrock_agentcore.status()

    def test_status_success(self, tmp_path):
        """Test successful status retrieval."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a minimal config file with required fields
        config_path.write_text(
            "name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\ncontainer_runtime: docker\n"
        )

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.get_status"
            ) as mock_status,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.config.name = "test-agent"
            mock_status.return_value = mock_result

            result = bedrock_agentcore.status()

            mock_status.assert_called_once_with(config_path)
            assert result.config.name == "test-agent"
