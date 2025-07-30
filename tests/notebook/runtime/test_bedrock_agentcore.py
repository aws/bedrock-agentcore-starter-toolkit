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
