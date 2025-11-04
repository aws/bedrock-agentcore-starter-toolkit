"""Unit tests for Bedrock AgentCore notebook interface with direct_code_deploy deployment."""

from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore import Runtime


class TestBedrockAgentCoreCodeZip:
    """Test class for Bedrock AgentCore notebook interface with direct_code_deploy deployment."""

    def test_configure_direct_code_deploy_success(self, mock_bedrock_agentcore_app, mock_boto3_clients, tmp_path):
        """Test successful configuration with direct_code_deploy deployment."""
        # Create agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("""
from bedrock_agentcore import BedrockAgentCoreApp
bedrock_agentcore = BedrockAgentCoreApp()

@bedrock_agentcore.entrypoint
def handler(payload):
    return {"result": "success"}
""")

        bedrock_agentcore = Runtime()

        with patch(
            "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
        ) as mock_configure:
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="arn:aws:iam::123456789012:role/TestRole",
                deployment_type="direct_code_deploy",
                runtime_type="PYTHON_3_10",
            )

            # Verify configure was called with correct parameters
            mock_configure.assert_called_once()
            call_args = mock_configure.call_args[1]
            assert call_args["deployment_type"] == "direct_code_deploy"
            assert call_args["runtime_type"] == "PYTHON_3_10"

    def test_configure_direct_code_deploy_with_requirements(self, mock_bedrock_agentcore_app, mock_boto3_clients, tmp_path):
        """Test configuration with direct_code_deploy and requirements."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        bedrock_agentcore = Runtime()

        with patch(
            "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
        ) as mock_configure:
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                requirements=["requests", "boto3", "pandas"],
                deployment_type="direct_code_deploy",
                runtime_type="PYTHON_3_11",
            )

            # Verify configure was called with correct parameters
            mock_configure.assert_called_once()
            call_args = mock_configure.call_args[1]
            assert call_args["deployment_type"] == "direct_code_deploy"
            assert call_args["runtime_type"] == "PYTHON_3_11"
            # Check that requirements_file was set (the notebook converts requirements list to file)
            assert "requirements_file" in call_args

    def test_configure_direct_code_deploy_missing_runtime_type(self, mock_bedrock_agentcore_app, mock_boto3_clients, tmp_path):
        """Test that direct_code_deploy deployment requires runtime_type."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("# test agent")

        bedrock_agentcore = Runtime()

        with pytest.raises(ValueError, match="runtime_type is required when deployment_type is 'direct_code_deploy'"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                deployment_type="direct_code_deploy",
                # Missing runtime_type
            )

    def test_launch_direct_code_deploy_local_mode(self, mock_bedrock_agentcore_app, mock_boto3_clients, tmp_path):
        """Test local launch with direct_code_deploy deployment."""
        bedrock_agentcore = Runtime()
        bedrock_agentcore._config_path = tmp_path / ".bedrock_agentcore.yaml"

        with patch(
            "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.launch_bedrock_agentcore"
        ) as mock_launch:
            mock_result = Mock()
            mock_launch.return_value = mock_result

            bedrock_agentcore.launch(local=True)

            # Verify launch was called with local mode
            mock_launch.assert_called_once()
            call_args = mock_launch.call_args[1]
            assert call_args["local"] is True
