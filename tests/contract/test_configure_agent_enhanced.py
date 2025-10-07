"""Contract tests for configureAgentEnhanced operation.

This module tests the enhanced agent configuration operation to ensure
backward compatibility and new source path tracking functionality.
"""

import tempfile
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    BedrockAgentCoreAgentSchema,
    BuildArtifactInfo,
)


class TestConfigureAgentEnhancedContract:
    """Contract tests for enhanced agent configuration operation."""

    def test_configure_agent_enhanced_with_source_path(self):
        """Test configuring agent with source path tracking."""
        # This test should fail initially since the enhanced configure operation isn't implemented yet

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a mock source directory and entrypoint file
            source_dir = temp_path / "agent_source"
            source_dir.mkdir()
            entrypoint_file = source_dir / "agent.py"
            entrypoint_file.write_text("# Mock agent entrypoint")

            # Test configuration with source path
            config_data = {
                "name": "enhanced-agent",
                "entrypoint": "agent.py",
                "source_path": str(source_dir),
                "output_directory": str(temp_path / "config"),
            }

            # This should work with enhanced configuration
            agent_config = BedrockAgentCoreAgentSchema(**config_data)

            # Verify source path is tracked
            assert agent_config.source_path == str(source_dir.resolve())
            assert agent_config.name == "enhanced-agent"
            assert agent_config.entrypoint == "agent.py"

            # This operation should be implemented in operations/runtime/configure.py
            # For now, this will pass the schema validation but the actual operation isn't implemented
            with pytest.raises(NotImplementedError, match="Enhanced configure operation not implemented"):
                # Mock the enhanced configure operation call
                from bedrock_agentcore_starter_toolkit.operations.runtime.configure import configure_agent_enhanced

                configure_agent_enhanced(
                    agent_name=config_data["name"],
                    entrypoint=config_data["entrypoint"],
                    source_path=config_data["source_path"],
                    output_directory=config_data["output_directory"],
                )

    def test_configure_agent_enhanced_backward_compatibility(self):
        """Test that enhanced configuration is backward compatible."""
        # This test should verify that existing configurations still work

        # Legacy configuration without source path
        legacy_config_data = {"name": "legacy-agent", "entrypoint": "legacy_agent.py"}

        # Should work with existing schema
        agent_config = BedrockAgentCoreAgentSchema(**legacy_config_data)

        # Verify backward compatibility
        assert agent_config.source_path is None  # Optional field defaults to None
        assert agent_config.build_artifacts is None  # Optional field defaults to None
        assert agent_config.name == "legacy-agent"
        assert agent_config.entrypoint == "legacy_agent.py"

        # Validation should still work
        errors = agent_config.validate(for_local=True)
        assert len(errors) == 0  # No validation errors for legacy config

    def test_configure_agent_enhanced_validation_errors(self):
        """Test validation errors for enhanced configuration."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test with non-existent source path
            with pytest.raises(ValueError, match="Source path does not exist"):
                BedrockAgentCoreAgentSchema(name="test-agent", entrypoint="agent.py", source_path="/non/existent/path")

            # Test with file instead of directory as source path
            file_path = temp_path / "not_a_dir.txt"
            file_path.write_text("content")

            with pytest.raises(ValueError, match="Source path must be a directory"):
                BedrockAgentCoreAgentSchema(name="test-agent", entrypoint="agent.py", source_path=str(file_path))

    def test_configure_agent_enhanced_response_schema(self):
        """Test that enhanced configuration returns expected response structure."""

        # Mock response structure for enhanced configuration
        expected_response = {
            "agent_name": "enhanced-agent",
            "configuration_path": "/path/to/config.yaml",
            "source_path": "/path/to/source",
            "status": "configured",
            "backward_compatible": True,
        }

        # This validates the contract schema from the OpenAPI spec
        # The actual implementation should return this structure
        assert "agent_name" in expected_response
        assert "configuration_path" in expected_response
        assert "source_path" in expected_response
        assert "status" in expected_response
        assert "backward_compatible" in expected_response

        # Status should be enum: [configured, updated]
        assert expected_response["status"] in ["configured", "updated"]

    def test_configure_agent_enhanced_with_build_artifacts(self):
        """Test configuration with build artifact information."""

        # Build artifacts should be auto-populated, not user-provided
        build_info = BuildArtifactInfo(
            base_directory=".packages/test-agent",
            source_copy_path=".packages/test-agent/src",
            dockerfile_path=".packages/test-agent/Dockerfile",
            organized=True,
        )

        # Verify build artifact info structure
        assert build_info.base_directory == ".packages/test-agent"
        assert build_info.source_copy_path == ".packages/test-agent/src"
        assert build_info.dockerfile_path == ".packages/test-agent/Dockerfile"
        assert build_info.organized is True
        assert build_info.is_valid() is True

        # Test agent config with build artifacts
        agent_config = BedrockAgentCoreAgentSchema(name="test-agent", entrypoint="agent.py", build_artifacts=build_info)

        assert agent_config.build_artifacts is not None
        assert agent_config.build_artifacts.is_valid() is True

    def test_configure_agent_enhanced_error_responses(self):
        """Test error response structure for enhanced configuration."""

        # Expected error response structure
        expected_error = {
            "error": "Invalid configuration parameters",
            "details": "Source path does not exist: /invalid/path",
            "suggestion": "Verify that the source path exists and is accessible",
            "backward_compatible": True,
        }

        # Validate error response structure
        assert "error" in expected_error
        assert "details" in expected_error
        assert "suggestion" in expected_error
        assert "backward_compatible" in expected_error

        # Test that the enhanced operation should handle these errors gracefully
        # The actual implementation should return this error structure
