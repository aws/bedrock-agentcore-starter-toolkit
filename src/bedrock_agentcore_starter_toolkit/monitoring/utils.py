"""Utility functions for monitoring system."""

import re
from typing import Tuple


def validate_agent_id(agent_id: str) -> Tuple[bool, str]:
    """Validate agent ID format for security.
    
    Args:
        agent_id: Agent ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not agent_id:
        return False, "Agent ID cannot be empty"
    
    if len(agent_id) > 100:
        return False, "Agent ID too long (max 100 characters)"
    
    # Only allow alphanumeric, hyphens, underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', agent_id):
        return False, "Agent ID can only contain letters, numbers, hyphens, and underscores"
    
    return True, ""


def sanitize_log_group_name(agent_id: str) -> str:
    """Create sanitized log group name from agent ID.
    
    Args:
        agent_id: Validated agent ID
        
    Returns:
        Safe log group name
    """
    # Agent ID should already be validated, but double-check
    is_valid, error = validate_agent_id(agent_id)
    if not is_valid:
        raise ValueError(f"Invalid agent ID: {error}")
    
    return f"/aws/bedrock-agentcore/runtimes/{agent_id}"


def sanitize_dashboard_name(agent_id: str) -> str:
    """Create sanitized dashboard name from agent ID.
    
    Args:
        agent_id: Validated agent ID
        
    Returns:
        Safe dashboard name
    """
    # Agent ID should already be validated, but double-check
    is_valid, error = validate_agent_id(agent_id)
    if not is_valid:
        raise ValueError(f"Invalid agent ID: {error}")
    
    return f"BedrockAgentCore-{agent_id}"