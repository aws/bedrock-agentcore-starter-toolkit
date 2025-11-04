"""Utility functions for agent log information."""

from datetime import datetime, timezone
from typing import Optional, Tuple


def get_genai_observability_url(region: str) -> str:
    """Get GenAI Observability Dashboard console URL.

    Args:
        region: The AWS region

    Returns:
        The GenAI Observability Dashboard console URL
    """
    return f"https://console.aws.amazon.com/cloudwatch/home?region={region}#gen-ai-observability/agent-core"


def get_agent_log_paths(
    agent_id: str,
    endpoint_name: Optional[str] = None,
    deployment_type: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Tuple[str, str]:
    """Get CloudWatch log group paths for an agent.

    Args:
        agent_id: The agent ID
        endpoint_name: The endpoint name (defaults to "DEFAULT")
        deployment_type: The deployment type ("direct_code_deploy" or "container")
        session_id: The session ID (for direct_code_deploy deployments)

    Returns:
        Tuple of (runtime_log_group, otel_log_group)
    """
    endpoint_name = endpoint_name or "DEFAULT"

    # For direct_code_deploy deployments, adjust log stream prefix
    if deployment_type == "direct_code_deploy":
        if session_id:
            # Specific session logs
            log_stream_prefix = "runtime-logs"
        else:
            # All session logs (incomplete prefix to match all)
            log_stream_prefix = "runtime-logs"
    else:
        # Container deployments use standard prefix
        log_stream_prefix = "runtime-logs]"

    runtime_log_group = (
        f"/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name} "
        f'--log-stream-name-prefix "{datetime.now(timezone.utc).strftime("%Y/%m/%d")}/\\[{log_stream_prefix}"'
    )
    otel_log_group = f'/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name} --log-stream-names "otel-rt-logs"'
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
