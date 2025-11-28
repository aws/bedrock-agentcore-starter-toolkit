"""Additional tests for dev_command.py - Testing new functions."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import typer

from bedrock_agentcore_starter_toolkit.cli.runtime.dev_command import (
    _ensure_config,
    _get_env_vars,
)
from bedrock_agentcore_starter_toolkit.utils.runtime.config import save_config
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    AWSConfig,
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
)


class TestGetEnvVars:
    """Test _get_env_vars function."""

    def test_no_config_file_returns_empty(self, tmp_path):
        """Test returns empty dict when config file doesn't exist."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        # Don't create the file

        env_vars = _get_env_vars(config_path)

        assert env_vars == {}

    def test_config_with_memory_id_and_region(self, tmp_path):
        """Test that memory_id and region from config are set in env vars."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(region="us-east-1"),
            memory=MemoryConfig(memory_id="test-memory-123"),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        env_vars = _get_env_vars(config_path)

        assert env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] == "test-memory-123"
        assert env_vars["AWS_REGION"] == "us-east-1"

    def test_config_with_only_aws_region(self, tmp_path):
        """Test config with AWS region but no memory ID."""
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(region="eu-west-1"),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        env_vars = _get_env_vars(config_path)

        assert "BEDROCK_AGENTCORE_MEMORY_ID" not in env_vars
        assert env_vars["AWS_REGION"] == "eu-west-1"

    def test_config_with_only_memory_id(self, tmp_path):
        """Test config with memory ID but no AWS region."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
            memory=MemoryConfig(memory_id="test-memory-456"),
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        env_vars = _get_env_vars(config_path)

        assert env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] == "test-memory-456"
        assert "AWS_REGION" not in env_vars

    def test_config_without_memory_or_region(self, tmp_path):
        """Test config with neither memory ID nor AWS region."""
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

        env_vars = _get_env_vars(config_path)

        assert env_vars == {}

    def test_invalid_config_returns_empty_with_warning(self, tmp_path):
        """Test that invalid config returns empty dict and warns."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text("invalid: yaml: content: [")

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._handle_warn") as mock_warn:
            env_vars = _get_env_vars(config_path)

            assert env_vars == {}
            mock_warn.assert_called_once()
            # Check that warning message mentions failed to load
            assert "Failed to load configuration" in mock_warn.call_args[0][0]

    def test_config_load_exception_handling(self, tmp_path):
        """Test graceful handling when config loading raises exception."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text("agents: {}")  # Valid YAML but invalid schema

        with patch("bedrock_agentcore_starter_toolkit.cli.runtime.dev_command._handle_warn") as mock_warn:
            env_vars = _get_env_vars(config_path)

            # Should return empty dict, not crash
            assert isinstance(env_vars, dict)
            mock_warn.assert_called_once()


class TestEnsureConfig:
    """Test _ensure_config function."""

    def test_both_config_and_entrypoint_exist(self, tmp_path):
        """Test returns (True, True) when both exist."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text("agents: {}")

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            has_config, has_entrypoint = _ensure_config(config_path)
            assert has_config is True
            assert has_entrypoint is True
        finally:
            os.chdir(original_cwd)

    def test_only_config_exists(self, tmp_path):
        """Test returns (True, False) when only config exists."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        config_path.write_text("agents: {}")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            has_config, has_entrypoint = _ensure_config(config_path)
            assert has_config is True
            assert has_entrypoint is False
        finally:
            os.chdir(original_cwd)

    def test_only_entrypoint_exists(self, tmp_path):
        """Test returns (False, True) when only entrypoint exists."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        # Don't create config

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text("app = None")

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            has_config, has_entrypoint = _ensure_config(config_path)
            assert has_config is False
            assert has_entrypoint is True
        finally:
            os.chdir(original_cwd)

    def test_neither_exists_raises_error(self, tmp_path):
        """Test exits when neither config nor entrypoint exist."""
        config_path = tmp_path / ".bedrock_agentcore.yaml"

        original_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(typer.Exit):
                _ensure_config(config_path)
        finally:
            os.chdir(original_cwd)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_empty_memory_id(self, tmp_path):
        """Test config with empty string memory_id."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.schema import MemoryConfig

        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(),
            memory=MemoryConfig(memory_id=""),  # Empty string
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        env_vars = _get_env_vars(config_path)

        # Empty string is falsy, should not be included
        assert "BEDROCK_AGENTCORE_MEMORY_ID" not in env_vars

    def test_config_with_empty_region(self, tmp_path):
        """Test config with empty string region."""
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(region=""),  # Empty string
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        env_vars = _get_env_vars(config_path)

        # Empty string is falsy, should not be included
        assert "AWS_REGION" not in env_vars

    def test_config_without_memory_config(self, tmp_path):
        """Test config without memory config (not provided)."""
        agent_schema = BedrockAgentCoreAgentSchema(
            name="test_agent",
            entrypoint="src/main.py",
            deployment_type="container",
            source_path=".",
            aws=AWSConfig(region="us-west-2"),
            # memory not provided
        )
        config = BedrockAgentCoreConfigSchema(
            default_agent="test_agent",
            agents={"test_agent": agent_schema},
        )
        config_path = tmp_path / ".bedrock_agentcore.yaml"
        save_config(config, config_path)

        env_vars = _get_env_vars(config_path)

        assert "BEDROCK_AGENTCORE_MEMORY_ID" not in env_vars
        assert env_vars["AWS_REGION"] == "us-west-2"
