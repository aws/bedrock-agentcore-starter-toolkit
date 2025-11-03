"""Tests for Bedrock AgentCore Jupyter notebook interface."""

import logging
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
                deployment_type="container",
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
                entrypoint=str(agent_file),
                execution_role="test-role",
                requirements=["requests", "boto3", "pandas"],
                deployment_type="container",
            )

            # Check that requirements.txt was created
            req_file = agent_file.parent / "requirements.txt"
            assert req_file.exists()
            content = req_file.read_text()
            assert "requests" in content
            assert "boto3" in content
            assert "pandas" in content

    def test_configure_with_code_build_execution_role(self, tmp_path):
        """Test configuration with CodeBuild execution role."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
            ) as mock_configure,
        ):
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="ExecutionRole",
                code_build_execution_role="CodeBuildRole",
                deployment_type="container",
            )

            # Verify configure was called with CodeBuild execution role
            mock_configure.assert_called_once()
            args, kwargs = mock_configure.call_args
            assert kwargs["code_build_execution_role"] == "CodeBuildRole"

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

            mock_launch.assert_called_once_with(
                config_path,
                local=True,
                use_codebuild=False,  # Local mode doesn't use CodeBuild
                auto_update_on_conflict=False,
                env_vars=None,
            )
            assert result.mode == "local"

    def test_launch_local_build(self, tmp_path):
        """Test local build mode (build locally, deploy to cloud)."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a config file with required AWS fields for cloud deployment
        config_text = """
name: test-agent
platform: linux/amd64
entrypoint: test_agent.py
deployment_type: container
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

            result = bedrock_agentcore.launch(local_build=True)

            mock_launch.assert_called_once_with(
                config_path,
                local=False,
                use_codebuild=False,  # Local build mode doesn't use CodeBuild
                auto_update_on_conflict=False,
                env_vars=None,
            )
            assert result.mode == "cloud"

    def test_launch_mutually_exclusive_flags(self, tmp_path):
        """Test that local and local_build flags are mutually exclusive."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a config file
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

        with pytest.raises(ValueError, match="Cannot use both 'local' and 'local_build' flags together"):
            bedrock_agentcore.launch(local=True, local_build=True)

    def test_launch_cloud(self, tmp_path):
        """Test cloud launch (default CodeBuild mode)."""
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
            mock_result.mode = "codebuild"  # Default mode is CodeBuild
            mock_result.agent_arn = "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id"
            mock_launch.return_value = mock_result

            result = bedrock_agentcore.launch()

            mock_launch.assert_called_once_with(
                config_path,
                local=False,
                use_codebuild=True,  # Default mode uses CodeBuild
                auto_update_on_conflict=False,
                env_vars=None,
            )
            assert result.mode == "codebuild"

    def test_launch_with_auto_update_on_conflict(self, tmp_path):
        """Test launch with auto_update_on_conflict parameter."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path

        # Create a config file with required AWS fields
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
            ) as mock_launch,
        ):
            mock_result = Mock()
            mock_result.mode = "codebuild"  # Default mode is CodeBuild
            mock_result.agent_arn = "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id"
            mock_launch.return_value = mock_result

            result = bedrock_agentcore.launch(auto_update_on_conflict=True)

            # Verify launch was called with auto_update_on_conflict=True
            mock_launch.assert_called_once_with(
                config_path,
                local=False,
                use_codebuild=True,  # Default mode uses CodeBuild
                auto_update_on_conflict=True,
                env_vars=None,
            )
            assert result.mode == "codebuild"

    def test_configure_with_disable_otel(self, tmp_path):
        """Test configure with disable_otel parameter."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
            ) as mock_configure,
        ):
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                disable_otel=True,
                deployment_type="container",
            )

            # Verify configure was called with enable_observability=False
            mock_configure.assert_called_once()
            args, kwargs = mock_configure.call_args
            assert kwargs["enable_observability"] is False

    def test_configure_default_otel(self, tmp_path):
        """Test configure with default OTEL setting (enabled)."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
            ) as mock_configure,
        ):
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                deployment_type="container",
                # disable_otel not specified, should default to False
            )

            # Verify configure was called with enable_observability=True (default)
            mock_configure.assert_called_once()
            args, kwargs = mock_configure.call_args
            assert kwargs["enable_observability"] is True

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

    def test_invoke_unicode_payload(self, tmp_path):
        """Test invoke with Unicode characters in payload."""
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

        unicode_payload = {
            "message": "Hello, 你好, नमस्ते, مرحبا, Здравствуйте",
            "emoji": "Hello! 👋 How are you? 😊 Having a great day! 🌟",
            "technical": "File: test_文件.py → Status: ✅ Success",
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.invoke_bedrock_agentcore"
            ) as mock_invoke,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.response = {"result": "success", "processed_unicode": True}
            mock_invoke.return_value = mock_result

            response = bedrock_agentcore.invoke(unicode_payload)

            # Verify the payload was passed correctly with Unicode characters
            mock_invoke.assert_called_once_with(
                config_path=config_path,
                payload=unicode_payload,
                session_id=None,
                bearer_token=None,
                local_mode=False,
                user_id=None,
            )
            assert response == {"result": "success", "processed_unicode": True}

    def test_invoke_unicode_response(self, tmp_path):
        """Test invoke with Unicode characters in response."""
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

        unicode_response = {
            "message": "नमस्ते! मैं आपसे हिंदी में बात कर सकता हूं",
            "greeting": "こんにちは！元気ですか？",
            "emoji_response": "処理完了！ ✅ 成功しました 🎉",
            "mixed": "English + 中文 + العربية = 🌍",
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.invoke_bedrock_agentcore"
            ) as mock_invoke,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.response = unicode_response
            mock_invoke.return_value = mock_result

            response = bedrock_agentcore.invoke({"message": "hello"})

            # Verify Unicode response is properly returned
            assert response == unicode_response
            assert response["message"] == "नमस्ते! मैं आपसे हिंदी में बात कर सकता हूं"
            assert response["greeting"] == "こんにちは！元気ですか？"
            assert response["emoji_response"] == "処理完了！ ✅ 成功しました 🎉"
            assert response["mixed"] == "English + 中文 + العربية = 🌍"

    def test_invoke_unicode_mixed_content(self, tmp_path):
        """Test invoke with mixed Unicode and ASCII content."""
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

        mixed_payload = {
            "english": "Hello World",
            "chinese": "你好世界",
            "numbers": "123456789",
            "symbols": "!@#$%^&*()",
            "emoji": "😊🌟✨",
            "mixed_sentence": "Processing file_名前.txt with status: ✅ Success!",
        }

        mixed_response = {
            "status": "processed",
            "input_language_detected": "mixed: EN+ZH+emoji",
            "output": "Successfully processed: 文件_名前.txt ✅",
            "emoji_count": 3,
            "languages": ["English", "中文", "日本語"],
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.invoke_bedrock_agentcore"
            ) as mock_invoke,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.response = mixed_response
            mock_invoke.return_value = mock_result

            response = bedrock_agentcore.invoke(mixed_payload)

            # Verify mixed content is properly handled
            mock_invoke.assert_called_once_with(
                config_path=config_path,
                payload=mixed_payload,
                session_id=None,
                bearer_token=None,
                local_mode=False,
                user_id=None,
            )
            assert response == mixed_response
            assert response["output"] == "Successfully processed: 文件_名前.txt ✅"
            assert response["languages"] == ["English", "中文", "日本語"]

    def test_invoke_unicode_edge_cases(self, tmp_path):
        """Test invoke with Unicode edge cases."""
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

        edge_case_payload = {
            "empty_unicode": "",
            "whitespace_unicode": "   ",
            "special_chars": "™€£¥©®",
            "combining_chars": "é̂ñ̃",  # Characters with combining diacritics
            "rtl_text": "مرحبا بكم في العالم",  # Right-to-left text
            "zero_width": "hello\u200bzero\u200bwidth",  # Zero-width space
            "high_unicode": "𝐇𝐞𝐥𝐥𝐨",  # High Unicode points
            "mixed_emoji": "🏳️‍🌈🏴‍☠️👨‍👩‍👧‍👦",  # Composite emoji
        }

        edge_case_response = {
            "processed_successfully": True,
            "detected_issues": [],
            "normalized_text": "hello zero width",
            "rtl_detected": True,
            "emoji_sequences": 3,
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.invoke_bedrock_agentcore"
            ) as mock_invoke,  # Patch in bedrock_agentcore.py module
        ):
            mock_result = Mock()
            mock_result.response = edge_case_response
            mock_invoke.return_value = mock_result

            response = bedrock_agentcore.invoke(edge_case_payload)

            # Verify edge cases are properly handled
            mock_invoke.assert_called_once_with(
                config_path=config_path,
                payload=edge_case_payload,
                session_id=None,
                bearer_token=None,
                local_mode=False,
                user_id=None,
            )
            assert response == edge_case_response
            assert response["processed_successfully"] is True
            assert response["rtl_detected"] is True
            assert response["emoji_sequences"] == 3

    def test_help_deployment_modes(self, capsys):
        """Test help_deployment_modes displays deployment information."""
        bedrock_agentcore = Runtime()

        # Call the help method
        bedrock_agentcore.help_deployment_modes()

        # Capture the printed output
        captured = capsys.readouterr()

        # Minimal checks for coverage - verify key deployment modes are mentioned
        assert "CodeBuild Mode" in captured.out
        assert "Local Development Mode" in captured.out
        assert "Local Build Mode" in captured.out
        assert "runtime.launch()" in captured.out

    def test_launch_docker_error_local_mode(self, tmp_path):
        """Test launch handles Docker-related RuntimeError in local mode."""
        bedrock_agentcore = Runtime()
        bedrock_agentcore._config_path = tmp_path / ".bedrock_agentcore.yaml"

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.launch_bedrock_agentcore"
            ) as mock_launch,
        ):
            mock_launch.side_effect = RuntimeError("docker command not found")

            with pytest.raises(RuntimeError) as exc_info:
                bedrock_agentcore.launch(local=True)

            # Verify the enhanced error message
            error_msg = str(exc_info.value)
            assert "Docker/Finch/Podman is required for local mode" in error_msg
            assert "Use CodeBuild mode instead: runtime.launch()" in error_msg

    def test_destroy_without_config(self):
        """Test destroy fails when not configured."""
        bedrock_agentcore = Runtime()

        with pytest.raises(ValueError, match="Must configure first"):
            bedrock_agentcore.destroy()

    @pytest.mark.parametrize(
        "dry_run,delete_ecr_repo,resources_removed,should_clear_state,test_id",
        [
            (False, False, ["agent-runtime", "lambda-function", "iam-role"], True, "success"),
            (True, False, ["agent-runtime", "lambda-function", "iam-role"], False, "dry_run"),
            (False, True, ["agent-runtime", "lambda-function", "ecr-repository"], True, "with_ecr_deletion"),
            (True, True, ["agent-runtime", "ecr-repository"], False, "dry_run_with_ecr"),
        ],
        ids=lambda x: x if isinstance(x, str) else "",
    )
    def test_destroy_with_parameters(
        self, tmp_path, dry_run, delete_ecr_repo, resources_removed, should_clear_state, test_id
    ):
        """Test destroy with various parameter combinations."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with patch(
            "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
        ) as mock_destroy:
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = resources_removed
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = dry_run
            mock_destroy.return_value = mock_result

            result = bedrock_agentcore.destroy(dry_run=dry_run, delete_ecr_repo=delete_ecr_repo)

            # Verify the call was made with correct parameters
            mock_destroy.assert_called_once_with(
                config_path=config_path,
                agent_name="test-agent",
                dry_run=dry_run,
                force=True,  # Always True in notebook interface
                delete_ecr_repo=delete_ecr_repo,
            )

            # Verify results
            assert result.agent_name == "test-agent"
            assert result.resources_removed == resources_removed
            assert result.dry_run == dry_run

            # Verify state handling
            if should_clear_state:
                # State should be cleared after successful destroy (not dry run, no errors)
                assert bedrock_agentcore._config_path is None
                assert bedrock_agentcore.name is None
            else:
                # State should be preserved during dry run
                assert bedrock_agentcore._config_path == config_path
                assert bedrock_agentcore.name == "test-agent"

    def test_destroy_success(self, tmp_path):
        """Test successful destroy operation."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime", "lambda-function", "iam-role"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = False
            mock_destroy.return_value = mock_result

            result = bedrock_agentcore.destroy()

            mock_destroy.assert_called_once_with(
                config_path=config_path,
                agent_name="test-agent",
                dry_run=False,
                force=True,  # Always True in notebook interface
                delete_ecr_repo=False,
            )
            assert result.agent_name == "test-agent"
            assert len(result.resources_removed) == 3
            assert result.dry_run is False

            # Verify internal state was cleared after successful destroy
            assert bedrock_agentcore._config_path is None
            assert bedrock_agentcore.name is None

    def test_destroy_dry_run(self, tmp_path):
        """Test destroy dry run mode."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime", "lambda-function", "iam-role"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = True
            mock_destroy.return_value = mock_result

            result = bedrock_agentcore.destroy(dry_run=True)

            mock_destroy.assert_called_once_with(
                config_path=config_path,
                agent_name="test-agent",
                dry_run=True,
                force=True,
                delete_ecr_repo=False,
            )
            assert result.dry_run is True

            # Verify internal state was NOT cleared during dry run
            assert bedrock_agentcore._config_path == config_path
            assert bedrock_agentcore.name == "test-agent"

    def test_destroy_always_forces_in_notebook(self, tmp_path):
        """Test destroy always uses force=True internally in notebook interface."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = False
            mock_destroy.return_value = mock_result

            # Call destroy - should internally use force=True
            bedrock_agentcore.destroy()

            mock_destroy.assert_called_once_with(
                config_path=config_path,
                agent_name="test-agent",
                dry_run=False,
                force=True,  # Always True in notebook interface
                delete_ecr_repo=False,
            )

    def test_destroy_with_delete_ecr_repo(self, tmp_path):
        """Test destroy with delete_ecr_repo flag."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime", "lambda-function", "ecr-repository"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = False
            mock_destroy.return_value = mock_result

            result = bedrock_agentcore.destroy(delete_ecr_repo=True)

            mock_destroy.assert_called_once_with(
                config_path=config_path,
                agent_name="test-agent",
                dry_run=False,
                force=True,
                delete_ecr_repo=True,
            )
            assert "ecr-repository" in result.resources_removed

    def test_destroy_combined_parameters(self, tmp_path):
        """Test destroy with multiple parameters combined."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime", "ecr-repository"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = True
            mock_destroy.return_value = mock_result

            bedrock_agentcore.destroy(dry_run=True, delete_ecr_repo=True)

            mock_destroy.assert_called_once_with(
                config_path=config_path,
                agent_name="test-agent",
                dry_run=True,
                force=True,  # Always True in notebook interface
                delete_ecr_repo=True,
            )

    @pytest.mark.parametrize(
        "warnings,errors,should_clear_state,test_id",
        [
            (["ECR repository not found", "Some resources already deleted"], [], True, "with_warnings"),
            ([], ["Failed to delete IAM role", "Access denied for ECR repository"], False, "with_errors"),
            (["Minor warning"], ["Critical error"], False, "with_both_warnings_and_errors"),
        ],
        ids=lambda x: x if isinstance(x, str) else "",
    )
    def test_destroy_with_warnings_and_errors(self, tmp_path, warnings, errors, should_clear_state, test_id):
        """Test destroy operation with different warning/error combinations."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with patch(
            "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
        ) as mock_destroy:
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime"]
            mock_result.warnings = warnings
            mock_result.errors = errors
            mock_result.dry_run = False
            mock_destroy.return_value = mock_result

            result = bedrock_agentcore.destroy()

            # Verify warnings
            assert len(result.warnings) == len(warnings)
            for warning in warnings:
                assert warning in result.warnings

            # Verify errors
            assert len(result.errors) == len(errors)
            for error in errors:
                assert error in result.errors

            # Verify state handling
            if should_clear_state:
                # State should be cleared when no errors (warnings are OK)
                assert bedrock_agentcore._config_path is None
                assert bedrock_agentcore.name is None
            else:
                # State should be preserved when errors occurred
                assert bedrock_agentcore._config_path == config_path
                assert bedrock_agentcore.name == "test-agent"

    def test_destroy_operation_exception(self, tmp_path):
        """Test destroy handles exceptions from operations layer."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_destroy.side_effect = Exception("AWS API error")

            with pytest.raises(Exception, match="AWS API error"):
                bedrock_agentcore.destroy()

            # Verify state is preserved when exception occurs
            assert bedrock_agentcore._config_path == config_path
            assert bedrock_agentcore.name == "test-agent"

    def test_destroy_logging_output(self, tmp_path, caplog):
        """Test destroy produces appropriate logging output."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime", "lambda-function"]
            mock_result.warnings = ["Minor warning"]
            mock_result.errors = []
            mock_result.dry_run = False
            mock_destroy.return_value = mock_result

            with caplog.at_level(logging.INFO):
                bedrock_agentcore.destroy()

            # Check for expected log messages
            log_messages = [record.message for record in caplog.records]
            assert any("Destroying Bedrock AgentCore resources" in msg for msg in log_messages)
            assert any("Destroy completed. Removed 2 resources" in msg for msg in log_messages)
            assert any("Minor warning" in record.message for record in caplog.records if record.levelname == "WARNING")

    def test_destroy_dry_run_logging(self, tmp_path, caplog):
        """Test destroy dry run produces appropriate logging output."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime", "lambda-function"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = True
            mock_destroy.return_value = mock_result

            with caplog.at_level(logging.INFO):
                bedrock_agentcore.destroy(dry_run=True)

            # Check for expected log messages
            log_messages = [record.message for record in caplog.records]
            assert any("Dry run mode: showing what would be destroyed" in msg for msg in log_messages)
            assert any("Dry run completed. Would destroy 2 resources" in msg for msg in log_messages)

    def test_destroy_with_delete_ecr_repo_logging(self, tmp_path, caplog):
        """Test destroy with delete_ecr_repo produces appropriate logging output."""
        bedrock_agentcore = Runtime()
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        bedrock_agentcore._config_path = config_path
        bedrock_agentcore.name = "test-agent"

        # Create a minimal config file
        config_path.write_text("name: test-agent\nplatform: linux/amd64\nentrypoint: test_agent.py\n")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.destroy_bedrock_agentcore"
            ) as mock_destroy,
        ):
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.resources_removed = ["agent-runtime", "ecr-repository"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_result.dry_run = False
            mock_destroy.return_value = mock_result

            with caplog.at_level(logging.INFO):
                bedrock_agentcore.destroy(delete_ecr_repo=True)

            # Check for expected log messages
            log_messages = [record.message for record in caplog.records]
            assert any("Including ECR repository deletion" in msg for msg in log_messages)

    def test_configure_with_vpc_parameters(self, tmp_path):
        """Test configure with VPC networking parameters."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.notebook.runtime.bedrock_agentcore.configure_bedrock_agentcore"
            ) as mock_configure,
        ):
            mock_result = Mock()
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_result.network_mode = "VPC"
            mock_result.network_subnets = ["subnet-abc123def456", "subnet-xyz789ghi012"]
            mock_result.network_security_groups = ["sg-abc123xyz789"]
            mock_configure.return_value = mock_result

            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=True,
                vpc_subnets=["subnet-abc123def456", "subnet-xyz789ghi012"],
                vpc_security_groups=["sg-abc123xyz789"],
                deployment_type="container",
            )

            # Verify configure was called with VPC parameters
            mock_configure.assert_called_once()
            args, kwargs = mock_configure.call_args
            assert kwargs["vpc_enabled"] is True
            assert kwargs["vpc_subnets"] == ["subnet-abc123def456", "subnet-xyz789ghi012"]
            assert kwargs["vpc_security_groups"] == ["sg-abc123xyz789"]

            assert bedrock_agentcore._config_path == tmp_path / ".bedrock_agentcore.yaml"

    def test_configure_vpc_validation_errors(self, tmp_path):
        """Test configure with invalid VPC configuration."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        # Test VPC enabled without subnets
        with pytest.raises(ValueError, match="VPC mode requires both vpc_subnets and vpc_security_groups"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=True,
                vpc_subnets=None,
                vpc_security_groups=["sg-abc123xyz789"],
            )

        # Test VPC enabled without security groups
        with pytest.raises(ValueError, match="VPC mode requires both vpc_subnets and vpc_security_groups"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=True,
                vpc_subnets=["subnet-abc123def456"],
                vpc_security_groups=None,
            )

    def test_configure_vpc_subnet_format_validation_notebook(self, tmp_path):
        """Test subnet ID format validation in notebook interface."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        # Invalid subnet prefix
        with pytest.raises(ValueError, match="Invalid subnet ID format"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=True,
                vpc_subnets=["invalid-abc123"],
                vpc_security_groups=["sg-abc123xyz789"],
            )

        # Subnet too short
        with pytest.raises(ValueError, match="Subnet ID is too short"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=True,
                vpc_subnets=["subnet-abc"],
                vpc_security_groups=["sg-abc123xyz789"],
            )

    def test_configure_vpc_security_group_format_validation_notebook(self, tmp_path):
        """Test security group ID format validation in notebook interface."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        # Invalid SG prefix
        with pytest.raises(ValueError, match="Invalid security group ID format"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=True,
                vpc_subnets=["subnet-abc123def456"],
                vpc_security_groups=["invalid-xyz789"],
            )

        # SG too short
        with pytest.raises(ValueError, match="Security group ID is too short"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=True,
                vpc_subnets=["subnet-abc123def456"],
                vpc_security_groups=["sg-xyz"],
            )

    def test_configure_vpc_resources_without_flag_error(self, tmp_path):
        """Test error when VPC resources provided without vpc_enabled=True."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        bedrock_agentcore = Runtime()

        with pytest.raises(ValueError, match="require vpc_enabled=True"):
            bedrock_agentcore.configure(
                entrypoint=str(agent_file),
                execution_role="test-role",
                vpc_enabled=False,
                vpc_subnets=["subnet-abc123def456"],  # Provided without vpc_enabled
                vpc_security_groups=["sg-abc123xyz789"],
            )

    def test_help_vpc_networking(self, capsys):
        """Test help_vpc_networking displays VPC guidance."""
        bedrock_agentcore = Runtime()

        bedrock_agentcore.help_vpc_networking()

        captured = capsys.readouterr()

        # Verify key VPC concepts are mentioned
        assert "VPC Networking for Bedrock AgentCore" in captured.out
        assert "Prerequisites" in captured.out
        assert "vpc_enabled=True" in captured.out
        assert "vpc_subnets" in captured.out
        assert "vpc_security_groups" in captured.out
        assert "IMMUTABLE" in captured.out
        assert "Security Group Requirements" in captured.out
