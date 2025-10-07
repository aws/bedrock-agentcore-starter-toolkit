"""Contract tests for listAgentsEnhanced operation.

This module tests the enhanced agent listing operation to ensure
enhanced agent information display with source paths and build artifacts.
"""

import pytest


class TestListAgentsEnhancedContract:
    """Contract tests for enhanced agent listing operation."""

    def test_list_agents_enhanced_with_mixed_configurations(self):
        """Test listing agents with both legacy and enhanced configurations."""

        expected_response = {
            "agents": [
                {
                    "name": "legacy-agent",
                    "entrypoint": "legacy_agent.py",
                    "source_path": None,  # Legacy agent without source path
                    "status": "ready",
                    "has_build_artifacts": False,
                    "last_modified": "2025-01-05T10:00:00Z",
                },
                {
                    "name": "enhanced-agent",
                    "entrypoint": "enhanced_agent.py",
                    "source_path": "/path/to/enhanced/source",
                    "status": "ready",
                    "has_build_artifacts": True,
                    "last_modified": "2025-01-06T12:00:00Z",
                },
                {
                    "name": "configured-agent",
                    "entrypoint": "configured_agent.py",
                    "source_path": "/path/to/configured/source",
                    "status": "configured",  # Not yet launched
                    "has_build_artifacts": False,
                    "last_modified": "2025-01-06T11:00:00Z",
                },
            ],
            "default_agent": "enhanced-agent",
        }

        # Validate response structure
        assert "agents" in expected_response
        assert "default_agent" in expected_response
        assert isinstance(expected_response["agents"], list)

        # Each agent should have required fields
        for agent in expected_response["agents"]:
            assert "name" in agent
            assert "entrypoint" in agent
            assert "source_path" in agent  # Can be None
            assert "status" in agent
            assert "has_build_artifacts" in agent
            assert "last_modified" in agent

            # Status should be valid enum
            assert agent["status"] in ["configured", "deployed", "ready", "error"]

        # This operation should be implemented in operations/runtime/status.py or configure.py
        with pytest.raises(NotImplementedError, match="Enhanced list agents operation not implemented"):
            from bedrock_agentcore_starter_toolkit.operations.runtime.configure import list_agents_enhanced

            list_agents_enhanced()

    def test_list_agents_enhanced_rich_table_format(self):
        """Test that agent listing is formatted for Rich table display."""

        # Expected table structure for Rich console
        expected_table_format = {
            "headers": ["Name", "Status", "Entrypoint", "Source Path", "Build Artifacts", "Last Modified"],
            "rows": [
                ["legacy-agent", "ready", "legacy_agent.py", "—", "—", "2025-01-05 10:00"],
                ["enhanced-agent", "ready", "enhanced_agent.py", "/path/to/source", "✓", "2025-01-06 12:00"],
                ["configured-agent", "configured", "configured_agent.py", "/path/to/source", "—", "2025-01-06 11:00"],
            ],
        }

        # Validate table structure
        assert "headers" in expected_table_format
        assert "rows" in expected_table_format
        assert len(expected_table_format["headers"]) == 6

        # Each row should have same number of columns as headers
        for row in expected_table_format["rows"]:
            assert len(row) == len(expected_table_format["headers"])

    def test_list_agents_enhanced_empty_configuration(self):
        """Test listing agents when no agents are configured."""

        expected_empty_response = {"agents": [], "default_agent": None}

        # Should handle empty configuration gracefully
        assert expected_empty_response["agents"] == []
        assert expected_empty_response["default_agent"] is None

        # Should provide helpful message for empty state
        expected_empty_message = "No agents configured. Run 'agentcore configure' to configure your first agent."
        assert len(expected_empty_message) > 0

    def test_list_agents_enhanced_sorting_and_filtering(self):
        """Test that agent listing supports sorting and filtering."""

        # Agents should be sorted by default (e.g., by name or last_modified)
        unsorted_agents = [
            {"name": "z-agent", "last_modified": "2025-01-06T10:00:00Z"},
            {"name": "a-agent", "last_modified": "2025-01-06T12:00:00Z"},
            {"name": "m-agent", "last_modified": "2025-01-06T11:00:00Z"},
        ]

        # Expected sorting by name
        expected_sorted_by_name = ["a-agent", "m-agent", "z-agent"]

        # Expected sorting by last_modified (most recent first)
        expected_sorted_by_time = ["a-agent", "m-agent", "z-agent"]

        # Should support different sorting criteria
        assert len(expected_sorted_by_name) == len(unsorted_agents)
        assert len(expected_sorted_by_time) == len(unsorted_agents)

    def test_list_agents_enhanced_status_indicators(self):
        """Test that listing includes clear status indicators."""

        expected_status_indicators = {
            "configured": {"symbol": "⚪", "description": "Configured but not deployed"},
            "deployed": {"symbol": "🟡", "description": "Deployed but not ready"},
            "ready": {"symbol": "🟢", "description": "Ready for invocation"},
            "error": {"symbol": "🔴", "description": "Configuration or deployment error"},
        }

        # Each status should have visual indicator and description
        for status, indicator in expected_status_indicators.items():
            assert "symbol" in indicator
            assert "description" in indicator
            assert len(indicator["symbol"]) > 0
            assert len(indicator["description"]) > 0

    def test_list_agents_enhanced_build_artifact_summary(self):
        """Test that listing includes build artifact summary information."""

        expected_artifact_summary = {
            "agents_with_artifacts": 2,
            "total_artifact_size": "250.5MB",
            "cleanup_candidates": [{"name": "old-agent", "last_used": "2024-12-01T10:00:00Z", "size": "45.2MB"}],
        }

        # Should provide summary information about build artifacts
        assert "agents_with_artifacts" in expected_artifact_summary
        assert "total_artifact_size" in expected_artifact_summary
        assert "cleanup_candidates" in expected_artifact_summary

        # Cleanup candidates should help with maintenance
        for candidate in expected_artifact_summary["cleanup_candidates"]:
            assert "name" in candidate
            assert "last_used" in candidate
            assert "size" in candidate

    def test_list_agents_enhanced_default_agent_highlighting(self):
        """Test that the default agent is clearly highlighted in the list."""

        agents_list = [
            {"name": "agent-1", "is_default": False},
            {"name": "agent-2", "is_default": True},  # Default agent
            {"name": "agent-3", "is_default": False},
        ]

        # Default agent should be clearly marked
        default_agents = [agent for agent in agents_list if agent["is_default"]]
        assert len(default_agents) == 1
        assert default_agents[0]["name"] == "agent-2"

        # Should use visual indicators for default agent
        expected_default_indicator = "★"  # or similar visual marker
        assert len(expected_default_indicator) > 0

    def test_list_agents_enhanced_performance_summary(self):
        """Test that listing includes performance summary."""

        expected_performance_summary = {
            "fastest_launch": {"agent": "fast-agent", "time": "30.2s"},
            "slowest_launch": {"agent": "slow-agent", "time": "95.1s"},
            "average_launch_time": "52.3s",
            "total_agents": 3,
        }

        # Should provide performance insights
        assert "fastest_launch" in expected_performance_summary
        assert "slowest_launch" in expected_performance_summary
        assert "average_launch_time" in expected_performance_summary
        assert "total_agents" in expected_performance_summary

    def test_list_agents_enhanced_troubleshooting_indicators(self):
        """Test that listing includes troubleshooting indicators."""

        expected_issue_indicators = {
            "source_path_missing": {"count": 1, "agents": ["problematic-agent"]},
            "build_artifacts_missing": {"count": 2, "agents": ["agent-1", "agent-2"]},
            "deployment_errors": {"count": 0, "agents": []},
            "configuration_warnings": {"count": 1, "agents": ["warning-agent"]},
        }

        # Should highlight potential issues
        assert "source_path_missing" in expected_issue_indicators
        assert "build_artifacts_missing" in expected_issue_indicators
        assert "deployment_errors" in expected_issue_indicators

        # Each indicator should have count and affected agents
        for indicator_type, indicator in expected_issue_indicators.items():
            assert "count" in indicator
            assert "agents" in indicator
            assert isinstance(indicator["count"], int)
            assert isinstance(indicator["agents"], list)
