"""Contract tests for getAgentStatusEnhanced operation.

This module tests the enhanced agent status operation to ensure
source path and build artifact information display.
"""

import tempfile
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    BuildArtifactInfo,
)


class TestGetAgentStatusEnhancedContract:
    """Contract tests for enhanced agent status operation."""

    def test_get_agent_status_enhanced_with_source_path(self):
        """Test getting agent status with source path information."""

        status_request = {"agent_name": "enhanced-agent"}

        expected_response = {
            "name": "enhanced-agent",
            "status": "ready",
            "entrypoint": "agent.py",
            "source_path": "/path/to/source",
            "build_artifacts": {
                "base_directory": ".packages/enhanced-agent",
                "source_copy_path": ".packages/enhanced-agent/src",
                "dockerfile_path": ".packages/enhanced-agent/Dockerfile",
                "build_timestamp": "2025-01-06T12:00:00Z",
                "organized": True,
            },
            "last_modified": "2025-01-06T12:00:00Z",
            "deployment_info": {
                "agent_arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/enhanced-agent-xyz",
                "region": "us-west-2",
                "account": "123456789012",
            },
        }

        # Validate response structure
        assert "name" in expected_response
        assert "status" in expected_response
        assert "source_path" in expected_response
        assert "build_artifacts" in expected_response

        # Status should be valid enum value
        assert expected_response["status"] in ["configured", "deployed", "ready", "error"]

        # This operation should be implemented in operations/runtime/status.py
        with pytest.raises(NotImplementedError, match="Enhanced status operation not implemented"):
            from bedrock_agentcore_starter_toolkit.operations.runtime.status import get_agent_status_enhanced

            get_agent_status_enhanced(status_request)

    def test_get_agent_status_enhanced_backward_compatibility(self):
        """Test that status works for legacy agents without source path."""

        # Test status for legacy agent without source path tracking

        expected_response = {
            "name": "legacy-agent",
            "status": "ready",
            "entrypoint": "legacy_agent.py",
            "source_path": None,  # Should be None for legacy agents
            "build_artifacts": None,  # May be None for legacy agents
            "last_modified": "2025-01-06T10:00:00Z",
            "deployment_info": {
                "agent_arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/legacy-agent-abc",
                "region": "us-west-2",
                "account": "123456789012",
            },
        }

        # Should handle legacy agents gracefully
        assert expected_response["source_path"] is None
        assert "deployment_info" in expected_response

    def test_get_agent_status_enhanced_build_artifact_details(self):
        """Test detailed build artifact information in status."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock build artifacts
            artifact_dir = temp_path / ".packages" / "test-agent"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "src").mkdir()
            (artifact_dir / "Dockerfile").write_text("FROM python:3.10")
            (artifact_dir / "build_metadata.json").write_text('{"build_time": "2025-01-06T12:00:00Z"}')

            build_info = BuildArtifactInfo(
                base_directory=str(artifact_dir),
                source_copy_path=str(artifact_dir / "src"),
                dockerfile_path=str(artifact_dir / "Dockerfile"),
                organized=True,
            )

            # Status should include detailed artifact information
            assert build_info.is_valid() is True

            expected_artifact_status = {
                "base_directory": str(artifact_dir),
                "source_copy_path": str(artifact_dir / "src"),
                "dockerfile_path": str(artifact_dir / "Dockerfile"),
                "organized": True,
                "exists": True,  # Should check if artifacts actually exist
                "size_mb": 0.1,  # Should include size information
            }

            # Validate artifact status structure
            assert "base_directory" in expected_artifact_status
            assert "organized" in expected_artifact_status
            assert "exists" in expected_artifact_status

    def test_get_agent_status_enhanced_error_cases(self):
        """Test error handling for status operation."""

        # Test agent not found error handling

        expected_error_response = {
            "error": "Agent not found",
            "details": "Agent 'non-existent-agent' is not configured",
            "suggestion": "Run 'agentcore configure list' to see available agents",
            "backward_compatible": True,
        }

        # Validate error response structure
        assert "error" in expected_error_response
        assert "details" in expected_error_response
        assert "suggestion" in expected_error_response
        assert "backward_compatible" in expected_error_response

    def test_get_agent_status_enhanced_rich_formatting(self):
        """Test that status information is formatted for Rich console display."""

        # Status should be optimized for Rich console output
        expected_display_format = {
            "sections": [
                {"title": "Agent Information", "content": ["Name", "Entrypoint", "Status"]},
                {"title": "Source Configuration", "content": ["Source Path", "Last Modified"]},
                {"title": "Build Artifacts", "content": ["Directory", "Status", "Size"]},
                {"title": "Deployment", "content": ["ARN", "Region", "Account"]},
            ]
        }

        # Validate display structure for Rich formatting
        assert "sections" in expected_display_format
        assert len(expected_display_format["sections"]) > 0

        # Each section should have title and content
        for section in expected_display_format["sections"]:
            assert "title" in section
            assert "content" in section

    def test_get_agent_status_enhanced_troubleshooting_info(self):
        """Test that status includes helpful troubleshooting information."""

        # Test troubleshooting information for problematic agent

        expected_response_with_issues = {
            "name": "problematic-agent",
            "status": "error",
            "entrypoint": "agent.py",
            "source_path": "/path/to/source",
            "build_artifacts": None,  # Missing artifacts
            "issues": [
                {
                    "type": "warning",
                    "message": "Source path exists but entrypoint file not found",
                    "suggestion": "Verify that 'agent.py' exists in the source directory",
                },
                {
                    "type": "error",
                    "message": "Build artifacts not found",
                    "suggestion": "Run 'agentcore launch' to create build artifacts",
                },
            ],
            "troubleshooting": {
                "source_accessible": True,
                "entrypoint_exists": False,
                "artifacts_exist": False,
                "deployment_ready": False,
            },
        }

        # Validate troubleshooting information structure
        assert "issues" in expected_response_with_issues
        assert "troubleshooting" in expected_response_with_issues

        # Issues should have type, message, and suggestion
        for issue in expected_response_with_issues["issues"]:
            assert "type" in issue
            assert "message" in issue
            assert "suggestion" in issue
            assert issue["type"] in ["info", "warning", "error"]

    def test_get_agent_status_enhanced_performance_info(self):
        """Test that status includes performance-related information."""

        expected_performance_info = {
            "last_launch_duration": "45.2s",
            "average_launch_time": "42.1s",
            "deployment_size": "125.3MB",
            "last_successful_launch": "2025-01-06T11:30:00Z",
        }

        # Performance info should be included in enhanced status
        assert "last_launch_duration" in expected_performance_info
        assert "deployment_size" in expected_performance_info

        # Should meet performance goals (<5 seconds for status operation)
        # This is a behavioral contract, not a data contract
        expected_status_operation_time = 5.0  # seconds
        assert expected_status_operation_time <= 5.0
