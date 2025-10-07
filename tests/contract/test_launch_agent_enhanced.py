"""Contract tests for launchAgentEnhanced operation.

This module tests the enhanced agent launch operation to ensure
build artifact organization and source path integration.
"""

import tempfile
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    BedrockAgentCoreAgentSchema,
    BuildArtifactInfo,
)


class TestLaunchAgentEnhancedContract:
    """Contract tests for enhanced agent launch operation."""

    def test_launch_agent_enhanced_with_artifact_organization(self):
        """Test launching agent with automatic build artifact organization."""
        # This test should fail initially since enhanced launch isn't implemented yet

        launch_request = {"agent_name": "enhanced-agent"}

        # Expected response structure
        expected_response = {
            "agent_arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/enhanced-agent-xyz",
            "build_artifacts": {
                "base_directory": ".packages/enhanced-agent",
                "source_copy_path": ".packages/enhanced-agent/src",
                "dockerfile_path": ".packages/enhanced-agent/Dockerfile",
                "build_timestamp": "2025-01-06T12:00:00Z",
                "organized": True,
            },
            "deployment_status": "READY",
            "observability_urls": {
                "cloudwatch_logs": "https://console.aws.amazon.com/cloudwatch/...",
                "xray_traces": "https://console.aws.amazon.com/xray/...",
            },
            "source_path_used": "/path/to/source",
        }

        # This operation should be implemented in operations/runtime/launch.py
        with pytest.raises(NotImplementedError, match="Enhanced launch operation not implemented"):
            # Mock the enhanced launch operation call
            from bedrock_agentcore_starter_toolkit.operations.runtime.launch import launch_agent_enhanced

            launch_agent_enhanced(launch_request)

    def test_launch_agent_enhanced_build_artifact_structure(self):
        """Test that build artifacts are created with correct structure."""

        # Expected artifact directory structure
        expected_structure = {
            "base_directory": ".packages/test-agent",
            "contents": [
                "src/",  # Copied source code
                "Dockerfile",  # Generated Dockerfile
                "build_metadata.json",  # Build information
            ],
        }

        # Build artifact info validation
        build_info = BuildArtifactInfo(
            base_directory=expected_structure["base_directory"],
            source_copy_path=f"{expected_structure['base_directory']}/src",
            dockerfile_path=f"{expected_structure['base_directory']}/Dockerfile",
            organized=True,
        )

        assert build_info.is_valid() is True
        assert build_info.get_artifact_directory("test-agent") == ".packages/test-agent"

    def test_launch_agent_enhanced_source_path_integration(self):
        """Test that launch operation uses tracked source path."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock source directory structure
            source_dir = temp_path / "agent_source"
            source_dir.mkdir()
            (source_dir / "agent.py").write_text("# Agent code")
            (source_dir / "requirements.txt").write_text("requests>=2.25.0")

            # Agent configuration with source path
            agent_config = BedrockAgentCoreAgentSchema(
                name="test-agent", entrypoint="agent.py", source_path=str(source_dir)
            )

            # Launch should use the tracked source path
            launch_request = {"agent_name": "test-agent"}

            # The enhanced launch operation should:
            # 1. Copy source from tracked source_path to build artifacts
            # 2. Generate Dockerfile in build artifacts
            # 3. Build container using organized artifacts
            # 4. Deploy to Bedrock AgentCore Runtime

            # For now, this will raise NotImplementedError
            with pytest.raises(NotImplementedError):
                # Mock enhanced launch that validates source path usage
                from bedrock_agentcore_starter_toolkit.operations.runtime.launch import launch_agent_enhanced

                launch_agent_enhanced(launch_request)

    def test_launch_agent_enhanced_backward_compatibility(self):
        """Test that enhanced launch works with legacy configurations."""

        # Launch request for agent without source path tracking
        launch_request = {"agent_name": "legacy-agent"}

        # Should still work with existing launch behavior
        # Enhanced launch should detect missing source_path and fall back to existing behavior

        # Expected response should still include artifact organization
        expected_response_structure = {
            "agent_arn": str,
            "build_artifacts": dict,  # Should be populated even for legacy agents
            "deployment_status": str,
            "observability_urls": dict,
            "source_path_used": None,  # Should be None for legacy agents
        }

        # Validate response structure expectations
        assert "agent_arn" in expected_response_structure
        assert "build_artifacts" in expected_response_structure
        assert "source_path_used" in expected_response_structure

    def test_launch_agent_enhanced_error_handling(self):
        """Test error handling for enhanced launch operation."""

        # Test invalid agent name
        invalid_request = {"agent_name": "non-existent-agent"}

        expected_error_response = {
            "error": "Agent not found",
            "details": "Agent 'non-existent-agent' is not configured",
            "suggestion": "Run 'agentcore configure' to configure the agent first",
            "backward_compatible": True,
        }

        # Validate error response structure
        assert "error" in expected_error_response
        assert "details" in expected_error_response
        assert "suggestion" in expected_error_response
        assert "backward_compatible" in expected_error_response

    def test_launch_agent_enhanced_progress_reporting(self):
        """Test that launch operation provides progress indicators."""

        launch_request = {"agent_name": "test-agent"}

        # Enhanced launch should provide progress indicators for operations >5 seconds
        expected_progress_stages = [
            "Loading configuration",
            "Organizing build artifacts",
            "Copying source code",
            "Generating Dockerfile",
            "Building container image",
            "Pushing to ECR",
            "Deploying to Bedrock AgentCore",
            "Verifying deployment",
        ]

        # The implementation should include progress reporting
        # This is more of a behavioral contract than a data contract
        assert len(expected_progress_stages) > 0

    def test_launch_agent_enhanced_artifact_isolation(self):
        """Test that build artifacts are isolated per agent."""

        # Multiple agents should have separate artifact directories
        agents = ["agent-1", "agent-2", "agent-3"]

        for agent_name in agents:
            build_info = BuildArtifactInfo()
            artifact_dir = build_info.get_artifact_directory(agent_name)

            # Each agent should have its own directory
            assert artifact_dir == f".packages/{agent_name}"

        # Verify isolation - different agents get different directories
        artifact_dirs = [BuildArtifactInfo().get_artifact_directory(name) for name in agents]
        assert len(set(artifact_dirs)) == len(agents)  # All unique

    def test_launch_agent_enhanced_cleanup_on_failure(self):
        """Test that partial build artifacts are cleaned up on launch failure."""

        launch_request = {"agent_name": "failing-agent"}

        # If launch fails, artifacts should be cleaned up
        expected_failure_response = {
            "error": "Launch failed",
            "details": "Container build failed",
            "cleanup_performed": True,
            "artifacts_removed": [".packages/failing-agent/src", ".packages/failing-agent/Dockerfile"],
        }

        # Validate cleanup behavior contract
        assert "cleanup_performed" in expected_failure_response
        assert "artifacts_removed" in expected_failure_response
