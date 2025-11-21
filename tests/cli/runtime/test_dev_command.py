"""Tests for dev_command.py - Development server command."""

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import typer

from bedrock_agentcore_starter_toolkit.cli.runtime.dev_command import (
    _cleanup_process,
    _find_available_port,
    _get_module_path_and_agent_name,
    _get_module_path_from_config,
    _setup_dev_environment,
    dev,
)
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
)


class TestGetModulePathAndAgentName:
    """Test _get_module_path_and_agent_name function."""

    def test_no_config_no_default_entrypoint_fails(self, tmp_path):
        """Test that it fails when no config and no default entrypoint exists."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        with pytest.raises(typer.Exit):
            _get_module_path_and_agent_name(config_path)

    def test_with_valid_config(self, tmp_path):
        """Test loading module path from valid config."""
        # Create config
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create entrypoint file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            module_path, agent_name = _get_module_path_and_agent_name(config_path)
            assert agent_name == "test_agent"
            assert "main:app" in module_path
        finally:
            os.chdir(original_cwd)

    def test_with_default_entrypoint_no_config(self, tmp_path):
        """Test fallback to default entrypoint when no config exists."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        # Create default entrypoint
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"):
                module_path, agent_name = _get_module_path_and_agent_name(config_path)
                assert module_path == "src.main:app"
                assert agent_name == "default"
        finally:
            os.chdir(original_cwd)

    def test_config_without_entrypoint(self, tmp_path):
        """Test config exists but has no entrypoint specified."""
        # Create config without entrypoint
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="",  # Empty entrypoint
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"):
                module_path, agent_name = _get_module_path_and_agent_name(config_path)
                assert module_path == "src.main:app"
                assert agent_name == "default"
        finally:
            os.chdir(original_cwd)

    def test_config_load_error_with_default_entrypoint(self, tmp_path):
        """Test fallback when config load fails but default entrypoint exists."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        # Create invalid YAML
        config_path.write_text("invalid: yaml: content: [")

        # Create default entrypoint
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"):
                module_path, agent_name = _get_module_path_and_agent_name(config_path)
                assert module_path == "src.main:app"
                assert agent_name == "default"
        finally:
            os.chdir(original_cwd)

    def test_config_load_error_without_default_entrypoint(self, tmp_path):
        """Test error when config load fails and no default entrypoint exists."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        # Create invalid YAML
        config_path.write_text("invalid: yaml: content: [")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                _get_module_path_and_agent_name(config_path)
        finally:
            os.chdir(original_cwd)


class TestGetModulePathFromConfig:
    """Test _get_module_path_from_config function."""

    def test_file_entrypoint(self, tmp_path):
        """Test converting file entrypoint to module path."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        # Create the actual file path relative to config
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        agent_config = Mock()
        # Use the full path relative to tmp_path
        agent_config.entrypoint = str(tmp_path / "src" / "main.py")

        module_path = _get_module_path_from_config(config_path, agent_config)
        assert module_path == "src.main:app"

    def test_directory_entrypoint(self, tmp_path):
        """Test converting directory entrypoint to module path."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        # Create the directory
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        agent_config = Mock()
        # Use the full path
        agent_config.entrypoint = str(tmp_path / "src")

        module_path = _get_module_path_from_config(config_path, agent_config)
        assert module_path == "src.main:app"

    def test_nested_entrypoint(self, tmp_path):
        """Test converting nested entrypoint path to module path."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        # Create the nested directory
        agents_dir = tmp_path / "agents" / "weather"
        agents_dir.mkdir(parents=True)
        (agents_dir / "main.py").write_text("app = None")

        agent_config = Mock()
        # Use the full path
        agent_config.entrypoint = str(tmp_path / "agents" / "weather" / "main.py")

        module_path = _get_module_path_from_config(config_path, agent_config)
        assert module_path == "agents.weather.main:app"

    def test_absolute_path_outside_project(self, tmp_path):
        """Test handling entrypoint outside project root."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        agent_config = Mock()
        agent_config.entrypoint = "/absolute/path/main.py"

        module_path = _get_module_path_from_config(config_path, agent_config)
        assert module_path == "main:app"


class TestSetupDevEnvironment:
    """Test _setup_dev_environment function."""

    def test_no_envs_default_port(self):
        """Test setup with no custom environment variables and default port."""
        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=8080):
            env = _setup_dev_environment(None, None)
            assert env["LOCAL_DEV"] == "1"
            assert env["PORT"] == "8080"

    def test_custom_port(self):
        """Test setup with custom port."""
        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=9000):
            env = _setup_dev_environment(None, 9000)
            assert env["PORT"] == "9000"

    def test_port_in_use_fallback(self):
        """Test warning when requested port is in use."""
        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=8081),
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print") as mock_print,
        ):
            env = _setup_dev_environment(None, 8080)
            assert env["PORT"] == "8081"
            # Check warning was printed
            mock_print.assert_called()

    def test_custom_env_vars(self):
        """Test setup with custom environment variables."""
        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=8080):
            env = _setup_dev_environment(["API_KEY=secret123", "DEBUG=true"], None)
            assert env["API_KEY"] == "secret123"
            assert env["DEBUG"] == "true"
            assert env["LOCAL_DEV"] == "1"

    def test_invalid_env_var_format(self):
        """Test error on invalid environment variable format."""
        with pytest.raises(typer.Exit):
            _setup_dev_environment(["INVALID_FORMAT"], None)

    def test_port_from_env_var_string(self):
        """Test port parsing from environment variable as string."""
        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=9000),
            patch.dict(os.environ, {"PORT": "9000"}),
        ):
            env = _setup_dev_environment(None, None)
            assert env["PORT"] == "9000"


class TestFindAvailablePort:
    """Test _find_available_port function."""

    def test_first_port_available(self):
        """Test when first port is available."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_socket.return_value.__enter__.return_value = mock_sock_instance

            port = _find_available_port(8080)
            assert port == 8080

    def test_first_port_in_use(self):
        """Test finding next available port when first is in use."""
        call_count = [0]

        def side_effect(address):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("Port in use")
            # Second call succeeds

        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_sock_instance.bind.side_effect = side_effect
            mock_socket.return_value.__enter__.return_value = mock_sock_instance

            port = _find_available_port(8080)
            assert port == 8081

    def test_no_available_port(self):
        """Test error when no ports available in range."""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_sock_instance.bind.side_effect = OSError("Port in use")
            mock_socket.return_value.__enter__.return_value = mock_sock_instance

            with pytest.raises(typer.Exit):
                _find_available_port(8080)


class TestCleanupProcess:
    """Test _cleanup_process function."""

    def test_cleanup_none_process(self):
        """Test cleanup with None process."""
        # Should not raise any exception
        _cleanup_process(None)

    def test_cleanup_terminates_process(self):
        """Test cleanup terminates process gracefully."""
        mock_process = Mock()
        mock_process.wait.return_value = None

        _cleanup_process(mock_process)

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_cleanup_kills_on_timeout(self):
        """Test cleanup kills process when terminate times out."""
        mock_process = Mock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

        _cleanup_process(mock_process)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()


class TestDevCommand:
    """Test the main dev command function."""

    def test_dev_starts_server(self, tmp_path):
        """Test dev command starts uvicorn server."""
        # Create config
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create entrypoint
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=8080
                ),
                patch("subprocess.Popen") as mock_popen,
            ):
                mock_process = Mock()
                mock_process.wait.return_value = 0
                mock_popen.return_value = mock_process

                dev(port=None, envs=None)

                # Verify Popen was called with uvicorn command
                mock_popen.assert_called_once()
                call_args = mock_popen.call_args
                cmd = call_args[0][0]
                assert "uv" in cmd
                assert "uvicorn" in cmd
                assert "--reload" in cmd
                assert "8080" in cmd

        finally:
            os.chdir(original_cwd)

    def test_dev_handles_keyboard_interrupt(self, tmp_path):
        """Test dev command handles Ctrl+C gracefully."""
        # Create config
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create entrypoint
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=8080
                ),
                patch("subprocess.Popen") as mock_popen,
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._cleanup_process") as mock_cleanup,
            ):
                mock_process = Mock()
                mock_process.wait.side_effect = KeyboardInterrupt()
                mock_popen.return_value = mock_process

                dev(port=None, envs=None)

                # Verify cleanup was called
                mock_cleanup.assert_called_once_with(mock_process)

        finally:
            os.chdir(original_cwd)

    def test_dev_handles_exception(self, tmp_path):
        """Test dev command handles exceptions properly."""
        # Create config
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create entrypoint
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=8080
                ),
                patch("subprocess.Popen") as mock_popen,
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._cleanup_process") as mock_cleanup,
            ):
                mock_process = Mock()
                mock_process.wait.side_effect = Exception("Server error")
                mock_popen.return_value = mock_process

                with pytest.raises(typer.Exit):
                    dev(port=None, envs=None)

                # Verify cleanup was called
                mock_cleanup.assert_called_once_with(mock_process)

        finally:
            os.chdir(original_cwd)

    def test_dev_with_custom_port(self, tmp_path):
        """Test dev command with custom port."""
        # Create config
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create entrypoint
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=9000
                ),
                patch("subprocess.Popen") as mock_popen,
            ):
                mock_process = Mock()
                mock_process.wait.return_value = 0
                mock_popen.return_value = mock_process

                dev(port=9000, envs=None)

                # Verify port is in command
                call_args = mock_popen.call_args
                cmd = call_args[0][0]
                assert "9000" in cmd

        finally:
            os.chdir(original_cwd)

    def test_dev_with_env_vars(self, tmp_path):
        """Test dev command passes environment variables."""
        # Create config
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        # Create entrypoint
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with (
                patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command.console.print"),
                patch(
                    "bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._find_available_port", return_value=8080
                ),
                patch("subprocess.Popen") as mock_popen,
            ):
                mock_process = Mock()
                mock_process.wait.return_value = 0
                mock_popen.return_value = mock_process

                dev(port=None, envs=["API_KEY=secret", "DEBUG=true"])

                # Verify env vars were passed
                call_args = mock_popen.call_args
                env = call_args[1]["env"]
                assert env["API_KEY"] == "secret"
                assert env["DEBUG"] == "true"
                assert env["LOCAL_DEV"] == "1"

        finally:
            os.chdir(original_cwd)
