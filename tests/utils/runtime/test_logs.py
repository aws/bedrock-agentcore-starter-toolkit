"""Tests for logs utility functions."""

import pytest
from bedrock_agentcore_starter_toolkit.utils.runtime.logs import (
    get_agent_log_paths,
    get_aws_tail_commands,
)


class TestGetAgentLogPaths:
    """Test get_agent_log_paths function."""

    def test_get_agent_log_paths_with_default_endpoint(self):
        """Test getting log paths with default endpoint name."""
        agent_id = "test-agent-123"
        runtime_log, otel_log = get_agent_log_paths(agent_id)
        
        expected_runtime = "/aws/bedrock-agentcore/runtimes/test-agent-123-DEFAULT"
        expected_otel = "/aws/bedrock-agentcore/runtimes/test-agent-123-DEFAULT/runtime-logs"
        
        assert runtime_log == expected_runtime
        assert otel_log == expected_otel

    def test_get_agent_log_paths_with_custom_endpoint(self):
        """Test getting log paths with custom endpoint name."""
        agent_id = "test-agent-456"
        endpoint_name = "CUSTOM"
        runtime_log, otel_log = get_agent_log_paths(agent_id, endpoint_name)
        
        expected_runtime = "/aws/bedrock-agentcore/runtimes/test-agent-456-CUSTOM"
        expected_otel = "/aws/bedrock-agentcore/runtimes/test-agent-456-CUSTOM/runtime-logs"
        
        assert runtime_log == expected_runtime
        assert otel_log == expected_otel

    def test_get_agent_log_paths_with_none_endpoint(self):
        """Test getting log paths with None endpoint (should use DEFAULT)."""
        agent_id = "test-agent-789"
        runtime_log, otel_log = get_agent_log_paths(agent_id, None)
        
        expected_runtime = "/aws/bedrock-agentcore/runtimes/test-agent-789-DEFAULT"
        expected_otel = "/aws/bedrock-agentcore/runtimes/test-agent-789-DEFAULT/runtime-logs"
        
        assert runtime_log == expected_runtime
        assert otel_log == expected_otel

    def test_get_agent_log_paths_with_empty_string_endpoint(self):
        """Test getting log paths with empty string endpoint (should use DEFAULT)."""
        agent_id = "test-agent-empty"
        runtime_log, otel_log = get_agent_log_paths(agent_id, "")
        
        expected_runtime = "/aws/bedrock-agentcore/runtimes/test-agent-empty-DEFAULT"
        expected_otel = "/aws/bedrock-agentcore/runtimes/test-agent-empty-DEFAULT/runtime-logs"
        
        assert runtime_log == expected_runtime
        assert otel_log == expected_otel


class TestGetAwsTailCommands:
    """Test get_aws_tail_commands function."""

    def test_get_aws_tail_commands_basic(self):
        """Test getting AWS tail commands for a log group."""
        log_group = "/aws/bedrock-agentcore/runtimes/test-agent-123-DEFAULT"
        follow_cmd, since_cmd = get_aws_tail_commands(log_group)
        
        expected_follow = "aws logs tail /aws/bedrock-agentcore/runtimes/test-agent-123-DEFAULT --follow"
        expected_since = "aws logs tail /aws/bedrock-agentcore/runtimes/test-agent-123-DEFAULT --since 1h"
        
        assert follow_cmd == expected_follow
        assert since_cmd == expected_since

    def test_get_aws_tail_commands_with_special_characters(self):
        """Test getting AWS tail commands with special characters in log group."""
        log_group = "/aws/logs/test-group_with-special.chars"
        follow_cmd, since_cmd = get_aws_tail_commands(log_group)
        
        expected_follow = "aws logs tail /aws/logs/test-group_with-special.chars --follow"
        expected_since = "aws logs tail /aws/logs/test-group_with-special.chars --since 1h"
        
        assert follow_cmd == expected_follow
        assert since_cmd == expected_since

    def test_get_aws_tail_commands_empty_log_group(self):
        """Test getting AWS tail commands with empty log group."""
        log_group = ""
        follow_cmd, since_cmd = get_aws_tail_commands(log_group)
        
        expected_follow = "aws logs tail  --follow"
        expected_since = "aws logs tail  --since 1h"
        
        assert follow_cmd == expected_follow
        assert since_cmd == expected_since