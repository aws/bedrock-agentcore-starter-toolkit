"""Integration tests for mixed configuration compatibility."""

import tempfile
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
)


class TestMixedConfigurationIntegration:
    """Integration tests for mixed legacy and enhanced configurations."""

    def test_mixed_legacy_and_enhanced_agents_coexistence(self):
        """Test that legacy and enhanced agents can coexist in same config."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create source directory for enhanced agent
            source_dir = temp_path / "enhanced_source"
            source_dir.mkdir()
            (source_dir / "enhanced.py").write_text("# Enhanced agent")

            # Create mixed configuration
            mixed_config = BedrockAgentCoreConfigSchema(
                default_agent="enhanced-agent",
                agents={
                    "legacy-agent": BedrockAgentCoreAgentSchema(
                        name="legacy-agent",
                        entrypoint="legacy.py",
                        # No source_path - legacy agent
                    ),
                    "enhanced-agent": BedrockAgentCoreAgentSchema(
                        name="enhanced-agent",
                        entrypoint="enhanced.py",
                        source_path=str(source_dir),
                        # Has source_path - enhanced agent
                    ),
                },
            )

            # Both agents should be valid
            legacy_agent = mixed_config.agents["legacy-agent"]
            enhanced_agent = mixed_config.agents["enhanced-agent"]

            # Legacy agent should have new fields as None
            assert legacy_agent.source_path is None
            assert legacy_agent.build_artifacts is None

            # Enhanced agent should have source path
            assert enhanced_agent.source_path == str(source_dir.resolve())
            assert enhanced_agent.build_artifacts is None  # Not yet set

            # Both should validate for local deployment
            assert len(legacy_agent.validate(for_local=True)) == 0
            assert len(enhanced_agent.validate(for_local=True)) == 0

    def test_operations_handle_mixed_configurations(self):
        """Test that CLI operations handle both legacy and enhanced agents."""

        # This should fail initially since operations don't distinguish yet
        with pytest.raises(NotImplementedError):
            from bedrock_agentcore_starter_toolkit.operations.runtime.configure import handle_mixed_agents

            handle_mixed_agents(["legacy-agent", "enhanced-agent"])

    def test_listing_mixed_agents_shows_appropriate_info(self):
        """Test that listing shows appropriate info for each agent type."""

        # Should display different information based on agent capabilities
        expected_display_difference = {
            "legacy": {"source_path": "—", "build_artifacts": "—"},
            "enhanced": {"source_path": "/path/to/source", "build_artifacts": "✓"},
        }

        assert expected_display_difference["legacy"]["source_path"] == "—"
        assert expected_display_difference["enhanced"]["source_path"] != "—"
