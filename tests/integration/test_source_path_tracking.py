"""Integration tests for source path tracking functionality."""

import tempfile
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
)


class TestSourcePathTrackingIntegration:
    """Integration tests for source path tracking."""

    def test_source_path_validation_and_tracking(self):
        """Test end-to-end source path validation and tracking."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create source directory with entrypoint
            source_dir = temp_path / "agent_source"
            source_dir.mkdir()
            entrypoint_file = source_dir / "agent.py"
            entrypoint_file.write_text("# Agent entrypoint")

            # Test source path tracking
            agent_config = BedrockAgentCoreAgentSchema(
                name="tracked-agent", entrypoint="agent.py", source_path=str(source_dir)
            )

            # Source path should be resolved to absolute path
            assert agent_config.source_path == str(source_dir.resolve())

            # Validation should pass
            errors = agent_config.validate(for_local=True)
            assert len(errors) == 0

    def test_source_path_entrypoint_validation(self):
        """Test that entrypoint exists within source path."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create source directory without entrypoint
            source_dir = temp_path / "agent_source"
            source_dir.mkdir()

            agent_config = BedrockAgentCoreAgentSchema(
                name="invalid-agent", entrypoint="missing_agent.py", source_path=str(source_dir)
            )

            # Validation should fail - entrypoint not found in source path
            errors = agent_config.validate(for_local=True)
            assert len(errors) > 0
            assert any("Entrypoint file not found in source path" in error for error in errors)

    def test_source_path_usage_in_operations(self):
        """Test that operations use tracked source path consistently."""

        # This test should fail initially since operations don't use source path yet
        with pytest.raises(NotImplementedError):
            # Mock operation that should use source path
            from bedrock_agentcore_starter_toolkit.operations.runtime.configure import configure_with_source_path

            configure_with_source_path("agent-name", "/path/to/source")

    def test_source_path_persistence_in_config(self):
        """Test that source path is persisted in configuration."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "agent.py").write_text("# Agent")

            # Create config with source path
            config = BedrockAgentCoreConfigSchema(
                agents={
                    "test-agent": BedrockAgentCoreAgentSchema(
                        name="test-agent", entrypoint="agent.py", source_path=str(source_dir)
                    )
                }
            )

            # Serialize and deserialize
            config_dict = config.model_dump()
            reloaded_config = BedrockAgentCoreConfigSchema.model_validate(config_dict)

            # Source path should be preserved
            assert reloaded_config.agents["test-agent"].source_path == str(source_dir.resolve())
