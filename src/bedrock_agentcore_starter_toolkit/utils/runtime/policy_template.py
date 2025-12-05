"""Policy template utilities for runtime execution roles."""

import json
import re
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader


def _get_template_dir() -> Path:
    """Get the templates directory path."""
    return Path(__file__).parent / "templates"


def _render_template(template_name: str, variables: Dict[str, str]) -> str:
    """Render a Jinja2 template with the provided variables."""
    template_dir = _get_template_dir()
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    template = env.get_template(template_name)
    return template.render(**variables)


def render_trust_policy_template(region: str, account_id: str) -> str:
    """Render the trust policy template with provided values.

    Args:
        region: AWS region
        account_id: AWS account ID

    Returns:
        Rendered trust policy as JSON string
    """
    variables = {
        "region": region,
        "account_id": account_id,
    }
    return _render_template("execution_role_trust_policy.json.j2", variables)


def render_execution_policy_template(
    region: str,
    account_id: str,
    agent_name: str,
    deployment_type: str = "direct_code_deploy",
    protocol: Optional[str] = None,
    memory_enabled: bool = False,
    memory_id: Optional[str] = None,
    ecr_repository_name: Optional[str] = None,
) -> str:
    """Render the execution policy template with provided values.

    Args:
        region: AWS region
        account_id: AWS account ID
        agent_name: Agent name for resource scoping
        deployment_type: Deployment type ("container" or "direct_code_deploy")
        protocol: Server protocol (None, "HTTP", "MCP", or "A2A")
        memory_enabled: Whether memory is enabled
        memory_id: Specific memory ID for scoped access (if available)
        ecr_repository_name: Specific ECR repository name for scoped access

    Returns:
        Rendered execution policy as JSON string
    """
    variables = {
        "region": region,
        "account_id": account_id,
        "agent_name": agent_name,
        "deployment_type": deployment_type,
        "is_a2a_protocol": protocol == "A2A" if protocol else False,
        "memory_enabled": memory_enabled,
        "memory_id": memory_id,
        "has_memory_id": memory_id is not None,
        "ecr_repository_name": ecr_repository_name,
        "has_ecr_repository": ecr_repository_name is not None,
    }
    rendered = _render_template("execution_role_policy.json.j2", variables)

    # Clean up any trailing commas before closing braces/brackets
    cleaned = re.sub(r",(\s*[}\]])", r"\1", rendered)

    # Validate JSON is correct
    validate_rendered_policy(cleaned)

    return cleaned


def validate_rendered_policy(policy_json: str) -> Dict:
    """Validate that the rendered policy is valid JSON.

    Args:
        policy_json: JSON policy string

    Returns:
        Parsed policy dictionary

    Raises:
        ValueError: If policy JSON is invalid
    """
    try:
        return json.loads(policy_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid policy JSON: {e}") from e
