"""Utility functions for agent log information."""

from typing import Optional, Tuple


def get_agent_log_paths(agent_id: str, endpoint_name: Optional[str] = None) -> Tuple[str, str]:
    """Get CloudWatch log group paths for an agent.

    Args:
        agent_id: The agent ID
        endpoint_name: The endpoint name (defaults to "DEFAULT")

    Returns:
        Tuple of (runtime_log_group, otel_log_group)
    """
    endpoint_name = endpoint_name or "DEFAULT"
    runtime_log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name}"
    otel_log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name} --log-stream-names otel-rt-logs"
    return runtime_log_group, otel_log_group


def get_aws_tail_commands(log_group: str) -> tuple[str, str]:
    """Get AWS CLI tail commands for a log group.

    Args:
        log_group: The CloudWatch log group path

    Returns:
        Tuple of (follow_command, since_command)
    """
    follow_cmd = f"aws logs tail {log_group} --follow"
    since_cmd = f"aws logs tail {log_group} --since 1h"
    return follow_cmd, since_cmd
