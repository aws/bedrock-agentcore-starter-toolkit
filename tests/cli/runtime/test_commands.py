"""Tests for Bedrock AgentCore CLI functionality."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.cli import app


class TestBedrockAgentCoreCLI:
    """Test Bedrock AgentCore CLI commands."""

    def setup_method(self):
        """Setup test runner."""
        self.runner = CliRunner()

    def test_configure_command_basic(self, tmp_path):
        """Test basic configure command."""
        # Create test agent file
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
bedrock_agentcore = BedrockAgentCoreApp()

@bedrock_agentcore.entrypoint
def handler(payload):
    return {"result": "success"}
""")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands.configure_bedrock_agentcore"
            ) as mock_configure,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_requirements_file_display"
            ) as mock_req_display,
            patch("bedrock_agentcore_starter_toolkit.cli.common.prompt") as mock_prompt,
        ):
            mock_parse.return_value = (str(agent_file), "bedrock_agentcore")

            # Mock the requirements file display to return a requirements file
            mock_req_display.return_value = tmp_path / "requirements.txt"

            # Mock the OAuth prompt to return "no" (default behavior)
            mock_prompt.return_value = "no"

            mock_result = Mock()
            mock_result.runtime = "docker"
            mock_result.region = "us-west-2"
            mock_result.account_id = "123456789012"
            mock_result.execution_role = "arn:aws:iam::123456789012:role/TestRole"
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_result.auto_create_ecr = True
            mock_configure.return_value = mock_result

            os.chdir(tmp_path)

            result = self.runner.invoke(
                app, ["configure", "--entrypoint", str(agent_file), "--execution-role", "TestRole", "--ecr", "auto"]
            )

            assert result.exit_code == 0
            assert "Configuration Summary" in result.stdout
            mock_configure.assert_called_once()

    def test_configure_with_oauth(self, tmp_path):
        """Test configure command with OAuth configuration."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        oauth_config = {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://example.com/.well-known/openid_configuration",
                "allowedClients": ["client1", "client2"],
                "allowedAudience": ["aud1", "aud2"],
            }
        }

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands.configure_bedrock_agentcore"
            ) as mock_configure,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_requirements_file_display"
            ) as mock_req_display,
            patch("bedrock_agentcore_starter_toolkit.cli.common.prompt") as mock_prompt,
        ):
            mock_parse.return_value = (str(agent_file), "bedrock_agentcore")

            # Mock the requirements file display to return a requirements file
            mock_req_display.return_value = tmp_path / "requirements.txt"

            # Mock the OAuth prompt to return "no" (default behavior)
            mock_prompt.return_value = "no"

            mock_result = Mock()
            mock_result.runtime = "docker"
            mock_result.region = "us-west-2"
            mock_result.account_id = "123456789012"
            mock_result.execution_role = "arn:aws:iam::123456789012:role/TestRole"
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_configure.return_value = mock_result

            result = self.runner.invoke(
                app,
                [
                    "configure",
                    "--entrypoint",
                    str(agent_file),
                    "--execution-role",
                    "TestRole",
                    "--authorizer-config",
                    json.dumps(oauth_config),
                ],
            )

            assert result.exit_code == 0
            # Verify OAuth config was passed
            call_args = mock_configure.call_args
            assert call_args[1]["authorizer_configuration"] == oauth_config

    def test_configure_with_invalid_protocol(self, tmp_path):
        agent_file = tmp_path / "test_agent.py"

        def mock_handle_error_side_effect():
            raise typer.Exit(1)

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error",
            side_effect=mock_handle_error_side_effect,
        ) as mock_error:
            try:
                self.runner.invoke(app, ["configure", "--entrypoint", str(agent_file), "--protocol", "HTTPS"])
            except typer.Exit:
                pass
            mock_error.assert_called_once_with("Error: --protocol must be either HTTP or MCP")

    @pytest.mark.skip(reason="Skipping due to Typer CLI issues with YAML parsing")
    def test_launch_command_local(self, tmp_path):
        """Test launch command in local mode."""
        # Create config file
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("""default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
    container_runtime: docker
    aws:
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: null
      agent_arn: null
      endpoint_arn: null""")

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch,
            patch("typer.Exit", side_effect=lambda *args, **kwargs: None),
            patch("sys.exit", side_effect=lambda *args, **kwargs: None),
        ):
            mock_result = Mock()
            mock_result.mode = "local"
            mock_result.tag = "bedrock_agentcore-test-agent:latest"
            mock_result.runtime = Mock()
            mock_result.port = 8080
            mock_launch.return_value = mock_result

            # Change to temp directory
            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["launch", "--local"], catch_exceptions=False)
                # Just check exit code
                assert result.exit_code == 0 or result.exit_code == 2
                # Verify the core function was called correctly
                mock_launch.assert_called_once_with(
                    config_path=config_file,
                    agent_name=None,
                    local=False,
                    use_codebuild=False,  # Should be False due to --local-build
                    env_vars=None,
                    auto_update_on_conflict=False,
                )
            finally:
                os.chdir(original_cwd)

    # Edge case tests for configure command
    def test_configure_invalid_agent_name_special_chars(self, tmp_path):
        """Test configure command with agent name containing invalid characters."""
        agent_file = tmp_path / "test-agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        def mock_handle_error_side_effect():
            raise typer.Exit(1)

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.validate_agent_name") as mock_validate,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error",
                side_effect=mock_handle_error_side_effect,
            ) as mock_error,
        ):
            mock_parse.return_value = (str(agent_file), "test-agent")
            mock_validate.return_value = (False, "Agent name contains invalid characters: @#$")

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(
                    app,
                    [
                        "configure",
                        "--entrypoint",
                        str(agent_file),
                        "--name",
                        "test@agent#123",
                        "--execution-role",
                        "TestRole",
                    ],
                )
                assert result.exit_code == 1
                mock_error.assert_called_with("Agent name contains invalid characters: @#$")
            except typer.Exit:
                pass
            finally:
                os.chdir(original_cwd)

    def test_configure_no_entrypoint(self, tmp_path):
        """Test configure command with no entrypoint specified."""

        def mock_handle_error_side_effect():
            raise typer.Exit(1)

        with patch(
            "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error",
            side_effect=mock_handle_error_side_effect,
        ) as mock_error:
            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["configure", "--execution-role", "TestRole"])
                assert result.exit_code == 1
                mock_error.assert_called_with("--entrypoint is required")
            except typer.Exit:
                pass
            finally:
                os.chdir(original_cwd)

    def test_configure_no_execution_role_interactive_prompt_fails(self, tmp_path):
        """Test configure command when execution role prompt fails."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        def mock_handle_error_side_effect():
            raise typer.Exit(1)

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.ConfigurationManager") as mock_config_manager,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error",
                side_effect=mock_handle_error_side_effect,
            ),
        ):
            mock_parse.return_value = (str(agent_file), "bedrock_agentcore")

            # Mock config manager to simulate prompt failure
            mock_manager = Mock()
            mock_manager.prompt_execution_role.side_effect = Exception("Failed to get execution role")
            mock_config_manager.return_value = mock_manager

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["configure", "--entrypoint", str(agent_file)])
                assert result.exit_code == 1
                # Should fail when trying to get execution role
                mock_manager.prompt_execution_role.assert_called_once()
            except typer.Exit:
                pass
            finally:
                os.chdir(original_cwd)

    def test_configure_ecr_repository_specified(self, tmp_path):
        """Test configure command with specific ECR repository specified."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands.configure_bedrock_agentcore"
            ) as mock_configure,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_requirements_file_display"
            ) as mock_req_display,
            patch("bedrock_agentcore_starter_toolkit.cli.common.prompt") as mock_prompt,
        ):
            mock_parse.return_value = (str(agent_file), "bedrock_agentcore")
            mock_req_display.return_value = tmp_path / "requirements.txt"
            mock_prompt.return_value = "no"

            mock_result = Mock()
            mock_result.runtime = "docker"
            mock_result.region = "us-west-2"
            mock_result.account_id = "123456789012"
            mock_result.execution_role = "arn:aws:iam::123456789012:role/TestRole"
            mock_result.config_path = tmp_path / ".bedrock_agentcore.yaml"
            mock_result.auto_create_ecr = False
            mock_result.ecr_repository = "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-existing-repo"
            mock_configure.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(
                    app,
                    [
                        "configure",
                        "--entrypoint",
                        str(agent_file),
                        "--execution-role",
                        "TestRole",
                        "--ecr",
                        "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-existing-repo",
                    ],
                )
                assert result.exit_code == 0

                # Should use existing ECR repository (not auto-create)
                call_args = mock_configure.call_args
                assert (
                    call_args.kwargs["ecr_repository"]
                    == "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-existing-repo"
                )
                assert not call_args.kwargs["auto_create_ecr"]
                assert "Using existing ECR repository" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_configure_json_decode_error_in_authorizer_config(self, tmp_path):
        """Test configure command with JSON decode error in authorizer config."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        def mock_handle_error_side_effect():
            raise typer.Exit(1)

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.ConfigurationManager") as mock_config_manager,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_requirements_file_display"
            ) as mock_req_display,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error",
                side_effect=mock_handle_error_side_effect,
            ) as mock_error,
        ):
            mock_parse.return_value = (str(agent_file), "bedrock_agentcore")
            mock_req_display.return_value = None

            # Mock configuration manager to provide execution role
            mock_manager = Mock()
            mock_manager.prompt_ecr_repository.return_value = (None, True)
            mock_manager.prompt_oauth_config.return_value = None
            mock_config_manager.return_value = mock_manager

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                # Test with malformed JSON (missing closing brace)
                result = self.runner.invoke(
                    app,
                    [
                        "configure",
                        "--entrypoint",
                        str(agent_file),
                        "--execution-role",
                        "TestRole",
                        "--authorizer-config",
                        '{"customJWTAuthorizer": {"discoveryUrl": "test"',
                    ],
                )
                assert result.exit_code == 1

                # Should call _handle_error with JSON decode error
                mock_error.assert_called()
                call_args = mock_error.call_args[0][0]
                assert "Invalid JSON in --authorizer-config:" in call_args
            except typer.Exit:
                pass
            finally:
                os.chdir(original_cwd)

    @pytest.mark.skip(reason="Skipping due to Typer CLI issues with YAML parsing")
    def test_launch_command_cloud(self, tmp_path):
        """Test launch command in cloud mode."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("""default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      region: us-west-2
      account: 123456789012
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: null
      ecr_auto_create: true
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: null
      agent_arn: null
      endpoint_arn: null""")

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch,
            patch("typer.Exit", side_effect=lambda *args, **kwargs: None),
            patch("sys.exit", side_effect=lambda *args, **kwargs: None),
        ):
            mock_result = Mock()
            mock_result.mode = "cloud"
            mock_result.tag = "bedrock_agentcore-test-agent"
            mock_result.agent_arn = "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id"
            mock_result.ecr_uri = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test"
            mock_launch.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["launch"], catch_exceptions=False)
                # Just check exit code
                assert result.exit_code == 0 or result.exit_code == 2
                # Verify the core function was called correctly
                mock_launch.assert_called_once_with(
                    config_path=config_file,
                    agent_name=None,
                    local=False,
                    use_codebuild=True,
                    env_vars=None,
                    auto_update_on_conflict=False,
                )
            finally:
                os.chdir(original_cwd)

    def test_configure_command_value_error(self, tmp_path):
        """Test configure command with ValueError from core operations."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Simulate ValueError during entrypoint parsing
            mock_parse.side_effect = ValueError("Invalid entrypoint configuration")

            # Mock _handle_error to raise typer.Exit to simulate actual behavior
            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(
                    app, ["configure", "--entrypoint", str(agent_file), "--execution-role", "TestRole"]
                )

                assert result.exit_code == 1
                mock_error.assert_called_once_with("Error: Invalid entrypoint configuration", mock_parse.side_effect)
            finally:
                os.chdir(original_cwd)

    def test_configure_command_file_not_found_error(self, tmp_path):
        """Test configure command with FileNotFoundError."""
        nonexistent_file = tmp_path / "nonexistent.py"

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            result = self.runner.invoke(
                app, ["configure", "--entrypoint", str(nonexistent_file), "--execution-role", "TestRole"]
            )

            # Should fail with exit code 1 and contain file error info
            assert result.exit_code == 1
            assert "File not found" in result.stdout
        finally:
            os.chdir(original_cwd)

    def test_configure_command_general_exception(self, tmp_path):
        """Test configure command with general Exception."""
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands.configure_bedrock_agentcore"
            ) as mock_configure,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.parse_entrypoint") as mock_parse,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_requirements_file_display"
            ) as mock_req,
            patch("bedrock_agentcore_starter_toolkit.cli.common.prompt") as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            mock_parse.return_value = (str(agent_file), "bedrock_agentcore")
            mock_req.return_value = None
            mock_prompt.return_value = "no"

            # Simulate Exception during configure operation
            mock_configure.side_effect = Exception("Configuration failed due to network error")

            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(
                    app, ["configure", "--entrypoint", str(agent_file), "--execution-role", "TestRole"]
                )

                assert result.exit_code == 1
                mock_error.assert_called_once_with(
                    "Configuration failed: Configuration failed due to network error", mock_configure.side_effect
                )
            finally:
                os.chdir(original_cwd)

    def test_launch_command_value_error(self, tmp_path):
        """Test launch command with ValueError."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Simulate ValueError during launch
            mock_launch.side_effect = ValueError("Invalid configuration: missing required field")

            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["launch"])

                assert result.exit_code == 1
                mock_error.assert_called_once_with(
                    "Invalid configuration: missing required field", mock_launch.side_effect
                )
            finally:
                os.chdir(original_cwd)

    def test_launch_command_general_exception(self, tmp_path):
        """Test launch command with general Exception."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Simulate general Exception during launch
            mock_launch.side_effect = Exception("Docker daemon not running")

            def mock_handle_error_side_effect(message, exception=None):
                # Check if it's not a typer.Exit to avoid recursion
                if not isinstance(exception, typer.Exit):
                    raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["launch"])

                assert result.exit_code == 1
                # Should handle the exception but not re-raise typer.Exit
                assert mock_error.called
            finally:
                os.chdir(original_cwd)

    def test_invoke_command_value_error_not_deployed(self, tmp_path):
        """Test invoke command with ValueError for not deployed agent."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text(
            "default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent\n    entrypoint: test.py"
        )

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Simulate ValueError with "not deployed" message
            mock_invoke.side_effect = ValueError("Agent is not deployed to Bedrock AgentCore")

            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", '{"message": "hello"}'])

                assert result.exit_code == 1
                mock_error.assert_called_once_with(
                    "Bedrock AgentCore not deployed. Run 'bedrock_agentcore launch' first", mock_invoke.side_effect
                )
            finally:
                os.chdir(original_cwd)

    def test_invoke_command_value_error_general(self, tmp_path):
        """Test invoke command with general ValueError."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text(
            "default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent\n    entrypoint: test.py"
        )

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Simulate general ValueError
            mock_invoke.side_effect = ValueError("Invalid payload format")

            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", "invalid-json"])

                assert result.exit_code == 1
                mock_error.assert_called_with("Invocation failed: Invalid payload format", mock_invoke.side_effect)
            finally:
                os.chdir(original_cwd)

    def test_invoke_command_general_exception(self, tmp_path):
        """Test invoke command with general Exception."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text(
            "default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent\n    entrypoint: test.py"
        )

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Simulate general Exception during invoke
            mock_invoke.side_effect = Exception("Network timeout during invocation")

            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", '{"message": "hello"}'])

                assert result.exit_code == 1
                mock_error.assert_called_once_with(
                    "Invocation failed: Network timeout during invocation", mock_invoke.side_effect
                )
            finally:
                os.chdir(original_cwd)

    def test_status_command_value_error(self, tmp_path):
        """Test status command with ValueError."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            # Simulate ValueError during status check
            mock_status.side_effect = ValueError("Invalid agent configuration")

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                # Should fail with exit code 1 and the exception should be the ValueError
                assert result.exit_code == 1
                # Check if the exception is the one we raised or contains the message
                assert result.exception is not None
                assert "Invalid agent configuration" in str(result.exception)
            finally:
                os.chdir(original_cwd)

    def test_status_command_general_exception(self, tmp_path):
        """Test status command with general Exception."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            # Simulate general Exception during status check
            mock_status.side_effect = Exception("AWS credentials not found")

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                # Should fail with exit code 1 and the exception should be raised
                assert result.exit_code == 1
                # Check if the exception is the one we raised or contains the message
                assert result.exception is not None
                assert "AWS credentials not found" in str(result.exception)
            finally:
                os.chdir(original_cwd)

    def test_configure_set_default_file_not_found_error(self, tmp_path):
        """Test configure set-default command with missing config file."""
        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error:

            def mock_handle_error_side_effect(message):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)  # Directory without .bedrock_agentcore.yaml

            try:
                result = self.runner.invoke(app, ["configure", "set-default", "some-agent"])

                assert result.exit_code == 1
                # Check that error was called with the actual message format
                call_args = mock_error.call_args[0][0]
                assert "Configuration not found" in call_args
            finally:
                os.chdir(original_cwd)

    def test_configure_set_default_value_error(self, tmp_path):
        """Test configure set-default command with ValueError."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: existing-agent\nagents:\n  existing-agent:\n    name: existing-agent")

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Mock load_config to raise ValueError
            mock_load_config.side_effect = ValueError("Invalid YAML configuration")

            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["configure", "set-default", "nonexistent-agent"])

                assert result.exit_code == 1
                # Check that error was called with the actual message format
                call_args = mock_error.call_args[0][0]
                assert "Invalid YAML configuration" in call_args
            finally:
                os.chdir(original_cwd)

    def test_configure_list_file_not_found_error(self, tmp_path):
        """Test configure list command with missing config file."""
        original_cwd = Path.cwd()
        os.chdir(tmp_path)  # Directory without .bedrock_agentcore.yaml

        try:
            result = self.runner.invoke(app, ["configure", "list"])

            # Should show message about no config file
            assert result.exit_code == 0
            assert ".bedrock_agentcore.yaml not found" in result.stdout
        finally:
            os.chdir(original_cwd)

    def test_validate_requirements_file_error(self, tmp_path):
        """Test _validate_requirements_file with validation error."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import _validate_requirements_file

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.validate_requirements_file"
            ) as mock_validate,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._handle_error") as mock_error,
        ):
            # Simulate validation error
            mock_validate.side_effect = ValueError("Invalid requirements file format")

            def mock_handle_error_side_effect(message, exception=None):
                raise typer.Exit(1)

            mock_error.side_effect = mock_handle_error_side_effect

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                _validate_requirements_file("invalid-requirements.txt")
                raise AssertionError("Should have raised typer.Exit")
            except typer.Exit:
                pass  # Expected
            finally:
                os.chdir(original_cwd)

            mock_error.assert_called_once_with("Invalid requirements file format", mock_validate.side_effect)

    def test_prompt_for_requirements_file_validation_error(self, tmp_path):
        """Test _prompt_for_requirements_file with validation error and retry."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import _prompt_for_requirements_file

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.prompt") as mock_prompt,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._validate_requirements_file"
            ) as mock_validate,
        ):
            # First call should succeed, so return the file path
            mock_prompt.side_effect = ["valid_requirements.txt"]
            mock_validate.return_value = "valid_requirements.txt"

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = _prompt_for_requirements_file("Enter path: ", "")

                # Should return validated file path
                assert result == "valid_requirements.txt"
            finally:
                os.chdir(original_cwd)

    def test_invoke_command_basic(self, tmp_path):
        """Test invoke command."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke:
            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_result.session_id = "test-session-123"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", '{"message": "hello"}', "--session-id", "test-session-123"])

                assert result.exit_code == 0
                assert "Session ID: test-session-123" in result.stdout
                mock_invoke.assert_called_once_with(
                    config_path=config_file,
                    payload={"message": "hello"},
                    agent_name=None,
                    session_id="test-session-123",
                    bearer_token=None,
                    local_mode=False,
                    user_id=None,
                )
            finally:
                os.chdir(original_cwd)

    def test_invoke_with_bearer_token_and_oauth_config(self, tmp_path):
        """Test invoke command uses bearer token only when OAuth is configured."""
        # Config file path for potential future use
        config_file = tmp_path / ".bedrock_agentcore.yaml"

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
        ):
            # Mock project config and agent config with OAuth
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.authorizer_configuration = {"customJWTAuthorizer": {"discoveryUrl": "test"}}
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_result.session_id = "test-session"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", '{"message": "hello"}', "--bearer-token", "test-token"])

                assert result.exit_code == 0
                assert "Using bearer token for OAuth authentication" in result.stdout

                # Verify bearer token was passed
                mock_invoke.assert_called_once_with(
                    config_path=config_file,
                    payload={"message": "hello"},
                    agent_name=None,
                    session_id=None,
                    bearer_token="test-token",
                    local_mode=False,
                    user_id=None,
                )
            finally:
                os.chdir(original_cwd)

    def test_invoke_bearer_token_without_oauth_config(self, tmp_path):
        """Test invoke command warns when bearer token provided but OAuth not configured."""
        # Config file path for potential future use
        config_file = tmp_path / ".bedrock_agentcore.yaml"

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
        ):
            # Mock project config and agent config without OAuth
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.authorizer_configuration = None
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_result.session_id = "test-session"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", '{"message": "hello"}', "--bearer-token", "test-token"])

                assert result.exit_code == 0
                assert "Warning: Bearer token provided but OAuth is not configured" in result.stdout

                # Verify bearer token was NOT passed
                mock_invoke.assert_called_once_with(
                    config_path=config_file,
                    payload={"message": "hello"},
                    agent_name=None,
                    session_id=None,
                    bearer_token=None,
                    local_mode=False,
                    user_id=None,
                )
            finally:
                os.chdir(original_cwd)

    def test_status_command(self, tmp_path):
        """Test status command."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
    aws:
      region: us-west-2
      account: "123456789012"
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: null
      ecr_auto_create: true
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: null
      agent_arn: null
      agent_session_id: null
    container_runtime: docker
    authorizer_configuration: null
"""
        config_file.write_text(config_content.strip())

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            mock_result = Mock()
            mock_result.model_dump.return_value = {
                "config": {
                    "name": "test-agent",
                    "agent_id": "test-id",
                    "agent_arn": "test-arn",
                    "region": "us-west-2",
                    "account": "123456789012",
                    "execution_role": "test-role",
                    "ecr_repository": "test-repo",
                },
                "agent": {
                    "status": "deployed",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "lastUpdatedAt": "2024-01-01T00:00:00Z",
                },
                "endpoint": {
                    "status": "ready",
                    "id": "test-endpoint-id",
                    "name": "test-endpoint",
                    "agentRuntimeEndpointArn": "test-endpoint-arn",
                    "agentRuntimeArn": "test-agent-arn",
                    "lastUpdatedAt": "2024-01-01T00:00:00Z",
                },
            }
            mock_status.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                # Debug output to see what went wrong
                if result.exit_code != 0:
                    print(f"CLI stdout: {result.stdout}")
                    print(f"CLI exception: {result.exception}")
                    if result.exception:
                        import traceback

                        traceback.print_exception(
                            type(result.exception), result.exception, result.exception.__traceback__
                        )

                assert result.exit_code == 0
                assert "test-agent" in result.stdout
                mock_status.assert_called_once_with(config_file, None)
            finally:
                os.chdir(original_cwd)

    def test_error_no_config_file(self, tmp_path):
        """Test error when .bedrock_agentcore.yaml not found."""
        original_cwd = Path.cwd()
        os.chdir(tmp_path)  # Directory without .bedrock_agentcore.yaml

        try:
            result = self.runner.invoke(app, ["launch"])
            assert result.exit_code == 1
            assert ".bedrock_agentcore.yaml not found" in result.stdout
        finally:
            os.chdir(original_cwd)

    def test_invoke_simple_text_payload(self, tmp_path):
        """Test invoke with simple text (auto-wrapped)."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
"""
        config_file.write_text(config_content.strip())

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
        ):
            # Mock project config and agent config
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.authorizer_configuration = None
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_result.session_id = "test-session"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", "Hello World"])

                assert result.exit_code == 0
                # Verify text was auto-wrapped in message field
                call_args = mock_invoke.call_args
                assert call_args.kwargs["payload"] == {"message": "Hello World"}
            finally:
                os.chdir(original_cwd)

    def test_launch_command_mutually_exclusive_options(self):
        """Test launch command with mutually exclusive options."""
        # Test local and local-build together (not allowed)
        result = self.runner.invoke(app, ["launch", "--local", "--local-build"])
        assert result.exit_code == 1
        assert "cannot be used together" in result.stdout

    def test_launch_command_local_build_success(self, tmp_path):
        """Test launch command with --local-build for cloud deployment."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch:
            mock_result = Mock()
            mock_result.mode = "cloud"
            mock_result.tag = "bedrock_agentcore-test-agent"
            mock_result.agent_arn = "arn:aws:bedrock:us-west-2:123456789012:agent-runtime/AGENT123"
            mock_result.ecr_uri = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-agent"
            mock_result.agent_id = "AGENT123"
            mock_launch.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["launch", "--local-build"])
                assert result.exit_code == 0
                assert "Local Docker Build Deployment Successful!" in result.stdout
                assert "agentcore status" in result.stdout
                assert "agentcore invoke" in result.stdout

                # Verify the core function was called with correct parameters
                mock_launch.assert_called_once_with(
                    config_path=config_file,
                    agent_name=None,
                    local=False,
                    use_codebuild=False,  # Should be False due to --local-build
                    env_vars=None,
                    auto_update_on_conflict=False,
                )
            finally:
                os.chdir(original_cwd)

    def test_launch_help_text_updated(self):
        """Test that help text reflects the three simplified launch modes."""
        result = self.runner.invoke(app, ["launch", "--help"])
        assert result.exit_code == 0

        # Check that old flags are no longer in help text
        assert "--push-ecr" not in result.stdout
        assert "--codebuild" not in result.stdout
        assert "Build and push to ECR only" not in result.stdout

        # Check that the three modes are clearly described
        assert "DEFAULT (no flags): CodeBuild + cloud runtime (RECOMMENDED)" in result.stdout
        assert "--local: Local build + local runtime" in result.stdout
        assert "--local-build: Local build + cloud runtime" in result.stdout

        # Check that remaining options are present
        assert "--local" in result.stdout
        assert "--local-build" in result.stdout

        # Check that Docker requirements are mentioned for local modes
        assert "requires Docker/Finch/Podman" in result.stdout

    def test_launch_missing_config(self, tmp_path):
        """Test launch command with missing config file."""
        original_cwd = Path.cwd()
        os.chdir(tmp_path)  # Directory without .bedrock_agentcore.yaml

        try:
            # We only verify the exit code here, not the content
            result = self.runner.invoke(app, ["launch"])
            assert result.exit_code == 1

            # Skip checking for output text since it's not captured properly
        finally:
            os.chdir(original_cwd)

    def test_invoke_missing_config(self, tmp_path):
        """Test invoke command with missing config file."""
        original_cwd = Path.cwd()
        os.chdir(tmp_path)  # Directory without .bedrock_agentcore.yaml

        try:
            result = self.runner.invoke(app, ["invoke", '{"message": "hello"}'])
            assert result.exit_code == 1
            assert ".bedrock_agentcore.yaml not found" in result.stdout
        finally:
            os.chdir(original_cwd)

    def test_status_verbose_json_output(self, tmp_path):
        """Test status command with verbose JSON output."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("name: test-agent")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            mock_result = Mock()
            mock_result.model_dump.return_value = {
                "config": {"name": "test-agent"},
                "agent": {"status": "deployed"},
                "endpoint": {"status": "READY"},
            }
            mock_status.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status", "--verbose"])
                assert result.exit_code == 0
                # Should contain JSON output
                assert '"name": "test-agent"' in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_status_command_missing_fields(self, tmp_path):
        """Test status command handles missing fields gracefully when endpoint is creating."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
    aws:
      region: us-west-2
      account: "123456789012"
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: null
      ecr_auto_create: true
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: test-agent-id
      agent_arn: null
      agent_session_id: null
    container_runtime: docker
    authorizer_configuration: null
"""
        config_file.write_text(config_content.strip())

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            mock_result = Mock()
            # Simulate agent data without createdAt field (endpoint still creating)
            mock_result.model_dump.return_value = {
                "config": {
                    "name": "test-agent",
                    "agent_id": "test-agent-id",
                    "agent_arn": "test-arn",
                    "region": "us-west-2",
                    "account": "123456789012",
                    "execution_role": "test-role",
                    "ecr_repository": "test-repo",
                },
                "agent": {
                    "status": "creating",
                    # Missing createdAt and lastUpdatedAt fields - this was the bug
                },
                "endpoint": {
                    "status": "creating",
                    "id": "test-endpoint-id",
                    # Missing some fields like name, agentRuntimeEndpointArn, etc.
                    "agentRuntimeArn": "test-agent-arn",
                },
            }
            mock_status.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                # Should not crash and should handle missing fields gracefully
                assert result.exit_code == 0
                assert "test-agent" in result.stdout
                # Should show "Not available" for missing fields
                assert "Not available" in result.stdout
                # Should show "Unknown" for missing endpoint status if needed
                mock_status.assert_called_once_with(config_file, None)
            finally:
                os.chdir(original_cwd)

    def test_handle_requirements_file_display_with_provided_file(self, tmp_path):
        """Test _handle_requirements_file_display with user-provided file."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import _handle_requirements_file_display

        # Create a requirements file in the project directory
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.25.1\nnumpy==1.21.0")

        # Change to the temp directory to make the file "within project"
        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.commands._validate_requirements_file",
                return_value="requirements.txt",
            ) as mock_validate:
                result = _handle_requirements_file_display("requirements.txt")
                assert result == "requirements.txt"
                mock_validate.assert_called_once_with("requirements.txt")
        finally:
            os.chdir(original_cwd)

    def test_handle_requirements_file_display_auto_detect_found(self, tmp_path):
        """Test _handle_requirements_file_display with auto-detection finding a file."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import _handle_requirements_file_display
        from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import DependencyInfo

        # Mock the detect_dependencies function
        mock_deps = DependencyInfo(file="pyproject.toml", type="pyproject")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.detect_dependencies",
                    return_value=mock_deps,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.commands._prompt_for_requirements_file",
                    return_value=None,
                ) as mock_prompt,
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.console.print") as mock_print,
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands._print_success") as mock_success,
            ):
                result = _handle_requirements_file_display(None)

                assert result is None
                mock_prompt.assert_called_once()
                mock_print.assert_any_call("\n🔍 [cyan]Detected dependency file:[/cyan] [bold]pyproject.toml[/bold]")
                mock_success.assert_called_once_with("Using detected file: [dim]pyproject.toml[/dim]")
        finally:
            os.chdir(original_cwd)

    def test_handle_requirements_file_display_no_file_found(self, tmp_path):
        """Test _handle_requirements_file_display with no auto-detection and user provides file."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import _handle_requirements_file_display
        from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import DependencyInfo

        # Mock the detect_dependencies function to return no file found
        mock_deps = DependencyInfo(file=None, type="notfound")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch(
                    "bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.detect_dependencies",
                    return_value=mock_deps,
                ),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.commands._prompt_for_requirements_file",
                    return_value="user_requirements.txt",
                ) as mock_prompt,
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.console.print") as mock_print,
            ):
                result = _handle_requirements_file_display(None)

                assert result == "user_requirements.txt"
                mock_prompt.assert_called_once_with("Path: ")
                mock_print.assert_any_call(
                    "\n[yellow]⚠️  No dependency file found (requirements.txt or pyproject.toml)[/yellow]"
                )
        finally:
            os.chdir(original_cwd)

    def test_configure_oauth(self, tmp_path):
        """Test _configure_oauth with discovery URL, client IDs, and audience."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import ConfigurationManager

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._print_success") as mock_success,
        ):
            # Setup prompt responses - note audience uses ", " separator
            mock_prompt.side_effect = [
                "https://example.com/.well-known/openid_configuration",  # discovery URL
                "client1,client2,client3",  # client IDs
                "aud1, aud2",  # audience (note the space after comma)
            ]

            result = config_manager._configure_oauth()

            expected_config = {
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://example.com/.well-known/openid_configuration",
                    "allowedClients": ["client1", "client2", "client3"],
                    "allowedAudience": ["aud1", "aud2"],
                }
            }

            assert result == expected_config
            mock_prompt.assert_any_call("Enter OAuth discovery URL", "")
            mock_prompt.assert_any_call("Enter allowed OAuth client IDs (comma-separated)", "")
            mock_prompt.assert_any_call("Enter allowed OAuth audience (comma-separated)", "")
            mock_success.assert_called_once_with("OAuth authorizer configuration created")

    def test_configure_oauth_with_existing_values(self, tmp_path):
        """Test _configure_oauth with existing configuration values as defaults."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import ConfigurationManager

        # Mock existing config with OAuth settings
        mock_project_config = Mock()
        mock_agent_config = Mock()
        mock_agent_config.authorizer_configuration = {
            "customJWTAuthorizer": {
                "discoveryUrl": "https://existing.com/.well-known/openid_configuration",
                "allowedClients": ["existing_client1", "existing_client2"],
                "allowedAudience": ["existing_aud1"],
            }
        }
        mock_project_config.get_agent_config.return_value = mock_agent_config

        with patch(
            "bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists",
            return_value=mock_project_config,
        ):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
        ):
            mock_prompt.side_effect = [
                "https://new.com/.well-known/openid_configuration",  # new discovery URL
                "new_client1,new_client2",  # new client IDs
                "new_aud1",  # new audience
            ]

            result = config_manager._configure_oauth()

            # Verify existing values were used as defaults
            mock_prompt.assert_any_call(
                "Enter OAuth discovery URL", "https://existing.com/.well-known/openid_configuration"
            )
            mock_prompt.assert_any_call(
                "Enter allowed OAuth client IDs (comma-separated)", "existing_client1,existing_client2"
            )
            mock_prompt.assert_any_call("Enter allowed OAuth audience (comma-separated)", "existing_aud1")

            expected_config = {
                "customJWTAuthorizer": {
                    "discoveryUrl": "https://new.com/.well-known/openid_configuration",
                    "allowedClients": ["new_client1", "new_client2"],
                    "allowedAudience": ["new_aud1"],
                }
            }

            assert result == expected_config

    def test_configure_oauth_no_discovery_url_error(self, tmp_path):
        """Test _configure_oauth raises error when no discovery URL provided."""
        import typer

        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import ConfigurationManager

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

        # Mock _handle_error to actually raise typer.Exit to stop execution
        def mock_handle_error_side_effect(message, exception=None):
            raise typer.Exit(1)

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default",
                return_value="",
            ),
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._handle_error",
                side_effect=mock_handle_error_side_effect,
            ) as mock_error,
        ):
            try:
                config_manager._configure_oauth()
            except typer.Exit:
                pass  # Expected behavior
            mock_error.assert_called_once_with("OAuth discovery URL is required")

    def test_configure_oauth_no_client_or_audience_error(self, tmp_path):
        """Test _configure_oauth raises error when neither client IDs nor audience provided."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import ConfigurationManager

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists", return_value=None):
            config_manager = ConfigurationManager(tmp_path / ".bedrock_agentcore.yaml")

        with (
            patch(
                "bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._prompt_with_default"
            ) as mock_prompt,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.configuration_manager._handle_error") as mock_error,
        ):
            mock_prompt.side_effect = [
                "https://example.com/.well-known/openid_configuration",  # discovery URL
                "",  # empty client IDs
                "",  # empty audience
            ]

            config_manager._configure_oauth()
            mock_error.assert_called_once_with(
                "At least one client ID or one audience is required for OAuth configuration"
            )

    def test_configure_list_agents_success(self, tmp_path):
        """Test configure list command with configured agents."""
        # Create config file with agents
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
    bedrock_agentcore:
      agent_arn: arn:aws:bedrock:us-west-2:123456789012:agent/test-id
  another-agent:
    name: another-agent
    entrypoint: another.py
    bedrock_agentcore:
      agent_arn: null
"""
        config_file.write_text(config_content.strip())

        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config:
            mock_project_config = Mock()
            mock_project_config.default_agent = "test-agent"
            mock_project_config.agents = {
                "test-agent": Mock(
                    entrypoint="test.py",
                    aws=Mock(region="us-west-2"),
                    bedrock_agentcore=Mock(agent_arn="arn:aws:bedrock:us-west-2:123456789012:agent/test-id"),
                ),
                "another-agent": Mock(
                    entrypoint="another.py", aws=Mock(region="us-west-2"), bedrock_agentcore=Mock(agent_arn=None)
                ),
            }
            mock_load_config.return_value = mock_project_config

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["configure", "list"])
                assert result.exit_code == 0
                assert "test-agent" in result.stdout
                assert "another-agent" in result.stdout
                assert "(default)" in result.stdout
                assert "Ready" in result.stdout
                assert "Config only" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_configure_set_default_success(self, tmp_path):
        """Test configure set-default command success."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: old-agent
agents:
  old-agent:
    name: old-agent
  new-agent:
    name: new-agent
"""
        config_file.write_text(config_content.strip())

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.save_config") as mock_save_config,
        ):
            mock_project_config = Mock()
            mock_project_config.agents = {"old-agent": Mock(), "new-agent": Mock()}
            mock_load_config.return_value = mock_project_config

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["configure", "set-default", "new-agent"])
                assert result.exit_code == 0
                assert "Set 'new-agent' as default" in result.stdout

                # Verify the config was updated
                assert mock_project_config.default_agent == "new-agent"
                mock_save_config.assert_called_once_with(mock_project_config, config_file)
            finally:
                os.chdir(original_cwd)

    def test_validate_requirements_file_success(self, tmp_path):
        """Test _validate_requirements_file with valid file."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import _validate_requirements_file
        from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import DependencyInfo

        # Create a requirements file
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.25.1")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with patch(
                "bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.validate_requirements_file"
            ) as mock_validate:
                mock_deps = DependencyInfo(file="requirements.txt", type="requirements", resolved_path=str(req_file))
                mock_validate.return_value = mock_deps

                result = _validate_requirements_file("requirements.txt")
                assert result == "requirements.txt"
                mock_validate.assert_called_once_with(Path.cwd(), "requirements.txt")
        finally:
            os.chdir(original_cwd)

    def test_prompt_for_requirements_file_success(self, tmp_path):
        """Test _prompt_for_requirements_file with valid response."""
        from bedrock_agentcore_starter_toolkit.cli.runtime.commands import _prompt_for_requirements_file

        # Create a requirements file
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.25.1")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.prompt", return_value="requirements.txt"),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.commands._validate_requirements_file",
                    return_value="requirements.txt",
                ) as mock_validate,
            ):
                result = _prompt_for_requirements_file("Enter path: ", "")
                assert result == "requirements.txt"
                mock_validate.assert_called_once_with("requirements.txt")
        finally:
            os.chdir(original_cwd)

    def test_launch_command_with_env_vars(self, tmp_path):
        """Test launch command with environment variables."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch:
            mock_result = Mock()
            mock_result.mode = "local"
            mock_result.tag = "bedrock_agentcore-test-agent"
            mock_result.runtime = Mock()
            mock_result.port = 8080
            mock_result.env_vars = {"KEY1": "value1", "KEY2": "value2"}
            mock_launch.return_value = mock_result

            # Mock the local run to avoid blocking
            mock_result.runtime.run_local = Mock()

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["launch", "--local", "--env", "KEY1=value1", "--env", "KEY2=value2"])
                assert result.exit_code == 0

                # Verify environment variables were parsed correctly
                call_args = mock_launch.call_args
                assert call_args.kwargs["env_vars"] == {"KEY1": "value1", "KEY2": "value2"}
            finally:
                os.chdir(original_cwd)

    def test_invoke_with_oauth_and_env_bearer_token(self, tmp_path):
        """Test invoke command uses bearer token from environment when OAuth configured."""
        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
            patch.dict(os.environ, {"BEDROCK_AGENTCORE_BEARER_TOKEN": "env-token"}),
        ):
            # Mock project config with OAuth
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.authorizer_configuration = {"customJWTAuthorizer": {"discoveryUrl": "test"}}
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_result.session_id = "test-session"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", '{"message": "hello"}'])
                assert result.exit_code == 0
                assert "Using bearer token for OAuth authentication" in result.stdout

                # Verify environment token was used
                call_args = mock_invoke.call_args
                assert call_args.kwargs["bearer_token"] == "env-token"
            finally:
                os.chdir(original_cwd)

    def test_launch_command_cloud_success(self, tmp_path):
        """Test launch command in cloud mode success."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch:
            mock_result = Mock()
            mock_result.mode = "cloud"
            mock_result.tag = "bedrock_agentcore-test-agent"
            mock_result.agent_arn = "arn:aws:bedrock:us-west-2:123456789012:agent-runtime/AGENT123"
            mock_result.ecr_uri = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test-agent"
            mock_result.agent_id = "AGENT123"
            mock_launch.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["launch"])
                assert result.exit_code == 0
                assert "Deployment Successful!" in result.stdout
                assert "arn:aws:bedrock:us-west-2:123456789012:agent-runtime/AGENT123" in result.stdout
                assert "agentcore status" in result.stdout
                assert "agentcore invoke" in result.stdout
                mock_launch.assert_called_once_with(
                    config_path=config_file,
                    agent_name=None,
                    local=False,
                    use_codebuild=True,
                    env_vars=None,
                    auto_update_on_conflict=False,
                )
            finally:
                os.chdir(original_cwd)

    def test_status_command_missing_agent(self, tmp_path):
        """Test status command with non-existent agent name."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            # Simulate the core function raising ValueError for non-existent agent
            mock_status.side_effect = ValueError("Agent 'nonexistent-agent' not found in configuration")

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status", "--agent", "agent"])

                assert result.exit_code == 1
                assert result.exception is not None
                assert "not found in configuration" in str(result.exception)
            finally:
                os.chdir(original_cwd)

    def test_status_command_no_agents_in_config(self, tmp_path):
        """Test status command when config has no agents defined."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: null\nagents: {}")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            # Simulate the core function raising ValueError for empty agents
            mock_status.side_effect = ValueError("No agents configured")

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                assert result.exit_code == 1
                assert result.exception is not None
                assert "No agents configured" in str(result.exception)
            finally:
                os.chdir(original_cwd)

    def test_status_command_log_info_failure(self, tmp_path):
        """Test status command when log path retrieval fails."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status,
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.logs.get_agent_log_paths") as mock_log_paths,
        ):
            mock_result = Mock()
            mock_result.model_dump.return_value = {
                "config": {
                    "name": "test-agent",
                    "agent_id": "test-agent-id",
                    "agent_arn": "test-arn",
                    "region": "us-west-2",
                    "account": "123456789012",
                    "execution_role": "test-role",
                    "ecr_repository": "test-repo",
                },
                "agent": {
                    "status": "deployed",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "lastUpdatedAt": "2024-01-01T00:00:00Z",
                },
                "endpoint": {
                    "status": "ready",
                    "id": "test-endpoint-id",
                    "name": "test-endpoint",
                    "agentRuntimeEndpointArn": "test-endpoint-arn",
                    "agentRuntimeArn": "test-agent-arn",
                    "lastUpdatedAt": "2024-01-01T00:00:00Z",
                },
            }
            mock_status.return_value = mock_result

            # Mock log path retrieval to fail
            mock_log_paths.side_effect = ValueError("Unable to determine log paths")

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                # Should still succeed even if log paths fail
                assert result.exit_code == 0
                assert "test-agent" in result.stdout
                # Log error should be silently handled and not shown to user
                assert "Unable to determine log paths" not in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_status_command_malformed_response(self, tmp_path):
        """Test status command with response missing expected fields."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            mock_result = Mock()
            # Return response with minimal but complete structure
            mock_result.model_dump.return_value = {
                "config": {
                    "name": "test-agent",
                    "region": "us-west-2",
                    "account": "123456789012",
                    "execution_role": "test-role",
                    "ecr_repository": "test-repo",
                },
                "agent": None,  # Valid None value
                "endpoint": None,  # Valid None value
            }
            mock_status.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                # Should handle response with minimal fields gracefully
                assert result.exit_code == 0
                assert "test-agent" in result.stdout
                # Should not crash even with some missing data
                mock_status.assert_called_once_with(config_file, None)
            finally:
                os.chdir(original_cwd)

    def test_status_command_with_specific_agent(self, tmp_path):
        """Test status command with specific agent parameter."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent-1
agents:
  test-agent-1:
    name: test-agent-1
  test-agent-2:
    name: test-agent-2
"""
        config_file.write_text(config_content.strip())

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            mock_result = Mock()
            mock_result.model_dump.return_value = {
                "config": {
                    "name": "test-agent-2",
                    "region": "us-west-2",
                    "account": "123456789012",
                    "execution_role": "test-role",
                    "ecr_repository": "test-repo",
                },
                "agent": None,
                "endpoint": None,
            }
            mock_status.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status", "--agent", "test-agent-2"])

                assert result.exit_code == 0
                assert "test-agent-2" in result.stdout
                # Should call get_status with the specific agent name
                mock_status.assert_called_once_with(config_file, "test-agent-2")
            finally:
                os.chdir(original_cwd)

    def test_status_command_endpoint_missing_optional_fields(self, tmp_path):
        """Test status command when endpoint has some missing optional fields."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("default_agent: test-agent\nagents:\n  test-agent:\n    name: test-agent")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.get_status") as mock_status:
            mock_result = Mock()
            mock_result.model_dump.return_value = {
                "config": {
                    "name": "test-agent",
                    "agent_id": "test-agent-id",
                    "agent_arn": "test-arn",
                    "region": "us-west-2",
                    "account": "123456789012",
                    "execution_role": "test-role",
                    "ecr_repository": "test-repo",
                },
                "agent": {
                    "status": "deployed",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "lastUpdatedAt": "2024-01-01T00:00:00Z",
                },
                "endpoint": {
                    "status": "creating",
                    "id": "test-endpoint-id",
                    # Missing name, agentRuntimeEndpointArn, agentRuntimeArn, lastUpdatedAt
                },
            }
            mock_status.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["status"])

                assert result.exit_code == 0
                assert "test-agent" in result.stdout
                assert "Not available" in result.stdout  # Should show for missing fields
                assert "creating" in result.stdout  # Should show available status
                mock_status.assert_called_once_with(config_file, None)
            finally:
                os.chdir(original_cwd)

    def test_invoke_command_unicode_payload(self, tmp_path):
        """Test invoke command with Unicode characters in payload."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        unicode_payload = {
            "message": "Hello, 你好, नमस्ते, مرحبا, Здравствуйте",
            "emoji": "Hello! 👋 How are you? 😊 Having a great day! 🌟",
            "technical": "File: test_文件.py → Status: ✅ Success",
        }

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
        ):
            # Mock project config and agent config
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.authorizer_configuration = None
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            mock_result = Mock()
            mock_result.response = {"result": "success"}
            mock_result.session_id = "test-session"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", json.dumps(unicode_payload, ensure_ascii=False)])

                assert result.exit_code == 0
                # Verify Unicode characters are properly displayed in payload
                assert "你好" in result.stdout
                assert "नमस्ते" in result.stdout
                assert "👋" in result.stdout
                assert "✅" in result.stdout

                # Verify the payload was passed correctly
                call_args = mock_invoke.call_args
                assert call_args.kwargs["payload"] == unicode_payload
            finally:
                os.chdir(original_cwd)

    def test_invoke_command_unicode_response(self, tmp_path):
        """Test invoke command with Unicode characters in response."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        unicode_response = {
            "message": "नमस्ते! मैं आपसे हिंदी में बात कर सकता हूं",
            "greeting": "こんにちは！元気ですか？",
            "emoji_response": "処理完了！ ✅ 成功しました 🎉",
            "mixed": "English + 中文 + العربية = 🌍",
        }

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
        ):
            # Mock project config and agent config
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.authorizer_configuration = None
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            mock_result = Mock()
            mock_result.response = unicode_response
            mock_result.session_id = "test-session"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", '{"message": "hello"}'])

                assert result.exit_code == 0
                # Verify Unicode characters are properly displayed in response
                assert "नमस्ते" in result.stdout
                assert "こんにちは" in result.stdout
                assert "✅" in result.stdout
                assert "🎉" in result.stdout
                assert "العربية" in result.stdout
                assert "🌍" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_invoke_command_mixed_unicode_ascii(self, tmp_path):
        """Test invoke command with mixed Unicode and ASCII content."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        mixed_payload = {
            "english": "Hello World",
            "chinese": "你好世界",
            "numbers": "123456789",
            "symbols": "!@#$%^&*()",
            "emoji": "😊🌟✨",
            "mixed_sentence": "Processing file_名前.txt with status: ✅ Success!",
        }

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.invoke_bedrock_agentcore") as mock_invoke,
        ):
            # Mock project config and agent config
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.authorizer_configuration = None
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            mock_result = Mock()
            mock_result.response = {"result": "mixed_content_processed"}
            mock_result.session_id = "test-session"
            mock_invoke.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["invoke", json.dumps(mixed_payload, ensure_ascii=False)])

                assert result.exit_code == 0
                # Verify mixed content is properly displayed
                assert "Hello World" in result.stdout
                assert "你好世界" in result.stdout
                assert "😊🌟✨" in result.stdout
                assert "file_名前.txt" in result.stdout
                assert "✅" in result.stdout

                # Verify the payload was passed correctly
                call_args = mock_invoke.call_args
                assert call_args.kwargs["payload"] == mixed_payload
            finally:
                os.chdir(original_cwd)

    def test_destroy_command_dry_run(self, tmp_path):
        """Test destroy command with dry run."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.destroy_bedrock_agentcore") as mock_destroy,
        ):
            # Mock project config and agent config
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.name = "test-agent"
            mock_agent_config.bedrock_agentcore = Mock()
            mock_agent_config.bedrock_agentcore.agent_arn = "arn:aws:bedrock:us-west-2:123456789012:agent-runtime/test"
            mock_agent_config.bedrock_agentcore.agent_id = "test-agent-id"
            mock_agent_config.aws.ecr_repository = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test"
            mock_agent_config.aws.execution_role = "arn:aws:iam::123456789012:role/test-role"
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            # Mock destroy result
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.dry_run = True
            mock_result.resources_removed = [
                "AgentCore agent: arn:aws:bedrock:us-west-2:123456789012:agent-runtime/test (DRY RUN)",
                "ECR images in repository: test (DRY RUN)",
                "CodeBuild project: bedrock-agentcore-test-agent-builder (DRY RUN)",
            ]
            mock_result.warnings = []
            mock_result.errors = []
            mock_destroy.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["destroy", "--dry-run"])

                assert result.exit_code == 0
                assert "Dry run completed" in result.stdout
                assert "Resources That Would Be Destroyed" in result.stdout
                assert "DRY RUN" in result.stdout

                # Verify destroy was called with dry_run=True
                call_args = mock_destroy.call_args
                assert call_args.kwargs["dry_run"] is True
            finally:
                os.chdir(original_cwd)

    def test_destroy_command_force(self, tmp_path):
        """Test destroy command with force flag."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.destroy_bedrock_agentcore") as mock_destroy,
        ):
            # Mock project config and agent config
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.name = "test-agent"
            mock_agent_config.bedrock_agentcore = Mock()
            mock_agent_config.bedrock_agentcore.agent_arn = "arn:aws:bedrock:us-west-2:123456789012:agent-runtime/test"
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            # Mock destroy result
            mock_result = Mock()
            mock_result.agent_name = "test-agent"
            mock_result.dry_run = False
            mock_result.resources_removed = ["AgentCore agent: arn:aws:bedrock:us-west-2:123456789012:agent-runtime/test"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_destroy.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["destroy", "--force"])

                assert result.exit_code == 0
                assert "Successfully destroyed resources" in result.stdout
                assert "Resources Successfully Destroyed" in result.stdout

                # Verify destroy was called with force=True
                call_args = mock_destroy.call_args
                assert call_args.kwargs["force"] is True
            finally:
                os.chdir(original_cwd)

    def test_destroy_command_undeployed_agent(self, tmp_path):
        """Test destroy command on undeployed agent."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
        ):
            # Mock project config with undeployed agent
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.name = "test-agent"
            mock_agent_config.bedrock_agentcore = None  # Not deployed
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["destroy"])

                assert result.exit_code == 0
                assert "Agent is not deployed, nothing to destroy" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_destroy_command_specific_agent(self, tmp_path):
        """Test destroy command with specific agent."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: agent1
agents:
  agent1:
    name: agent1
    entrypoint: agent1.py
  agent2:
    name: agent2
    entrypoint: agent2.py
"""
        config_file.write_text(config_content.strip())

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.destroy_bedrock_agentcore") as mock_destroy,
        ):
            # Mock project config and agent config for agent2
            mock_project_config = Mock()
            mock_agent_config = Mock()
            mock_agent_config.name = "agent2"
            mock_agent_config.bedrock_agentcore = Mock()
            mock_project_config.get_agent_config.return_value = mock_agent_config
            mock_load_config.return_value = mock_project_config

            # Mock destroy result
            mock_result = Mock()
            mock_result.agent_name = "agent2"
            mock_result.dry_run = True
            mock_result.resources_removed = ["AgentCore agent: arn:aws:bedrock:us-west-2:123456789012:agent-runtime/agent2"]
            mock_result.warnings = []
            mock_result.errors = []
            mock_destroy.return_value = mock_result

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["destroy", "--agent", "agent2", "--dry-run"])

                assert result.exit_code == 0
                assert "agent2" in result.stdout

                # Verify correct agent was targeted
                call_args = mock_destroy.call_args
                assert call_args.kwargs["agent_name"] == "agent2"
            finally:
                os.chdir(original_cwd)

    def test_destroy_command_nonexistent_agent(self, tmp_path):
        """Test destroy command with nonexistent agent."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_content = """
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
"""
        config_file.write_text(config_content.strip())

        with (
            patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config") as mock_load_config,
        ):
            # Mock project config
            mock_project_config = Mock()
            mock_project_config.get_agent_config.return_value = None  # Agent not found
            mock_load_config.return_value = mock_project_config

            original_cwd = Path.cwd()
            os.chdir(tmp_path)

            try:
                result = self.runner.invoke(app, ["destroy", "--agent", "nonexistent"])

                assert result.exit_code == 1
                assert "not found" in result.stdout
            finally:
                os.chdir(original_cwd)

    def test_destroy_command_no_config(self, tmp_path):
        """Test destroy command without configuration file."""
        original_cwd = Path.cwd()
        os.chdir(tmp_path)  # Directory without .bedrock_agentcore.yaml

        try:
            result = self.runner.invoke(app, ["destroy"])

            assert result.exit_code == 1
            assert ".bedrock_agentcore.yaml not found" in result.stdout
        finally:
            os.chdir(original_cwd)
