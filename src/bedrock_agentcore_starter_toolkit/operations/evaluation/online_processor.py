"""Business logic for online evaluation configuration operations.

This module contains all business logic for online evaluation configs.
The control plane client only makes API calls - this module adds validation,
formatting, and helper utilities.
"""

import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from .control_plane_client import EvaluationControlPlaneClient

logger = logging.getLogger(__name__)


def create_online_evaluation_config(
    client: EvaluationControlPlaneClient,
    config_name: str,
    agent_id: str,
    agent_endpoint: str = "DEFAULT",
    config_description: Optional[str] = None,
    sampling_rate: float = 1.0,
    evaluator_list: Optional[List[str]] = None,
    execution_role: Optional[str] = None,
    auto_create_execution_role: bool = True,
    enable_on_create: bool = True,
) -> Dict[str, Any]:
    """Create online evaluation configuration with validation.

    Args:
        client: Control plane client instance
        config_name: Name for the evaluation configuration
        agent_id: Bedrock AgentCore agent ID to evaluate
        agent_endpoint: Agent endpoint type (DEFAULT, DRAFT, or alias ARN)
        config_description: Optional description
        sampling_rate: Percentage of interactions to evaluate (0-100, default: 1.0)
        evaluator_list: List of evaluator IDs (default: ["Builtin.GoalSuccessRate"])
        execution_role: IAM role ARN for evaluation execution
        auto_create_execution_role: Auto-create role if not provided (default: True)
        enable_on_create: Enable config immediately after creation (default: True)

    Returns:
        API response with config details

    Raises:
        ValueError: If validation fails
        RuntimeError: If creation fails
    """
    # Input validation
    if not config_name or not config_name.strip():
        raise ValueError("config_name is required and cannot be empty")

    if not agent_id or not agent_id.strip():
        raise ValueError("agent_id is required and cannot be empty")

    if not 0 <= sampling_rate <= 100:
        raise ValueError(f"sampling_rate must be between 0 and 100, got {sampling_rate}")

    logger.info("Creating online evaluation config: %s for agent: %s", config_name, agent_id)
    logger.info(
        "Configuration: sampling_rate=%.1f%%, evaluators=%s",
        sampling_rate,
        evaluator_list or ["Builtin.GoalSuccessRate"],
    )

    # Create config via control plane client
    response = client.create_online_evaluation_config(
        config_name=config_name,
        agent_id=agent_id,
        agent_endpoint=agent_endpoint,
        config_description=config_description,
        sampling_rate=sampling_rate,
        evaluator_list=evaluator_list,
        execution_role=execution_role,
        auto_create_execution_role=auto_create_execution_role,
        enable_on_create=enable_on_create,
    )

    config_id = response.get("onlineEvaluationConfigId")
    logger.info("✓ Online evaluation config created successfully")
    logger.info("Config ID: %s", config_id)
    logger.info("Status: %s", response.get("status", "ENABLED" if enable_on_create else "DISABLED"))

    return response


def get_online_evaluation_config(
    client: EvaluationControlPlaneClient,
    config_id: str,
) -> Dict[str, Any]:
    """Get online evaluation configuration.

    Args:
        client: Control plane client instance
        config_id: Online evaluation config ID

    Returns:
        API response with config details

    Raises:
        ValueError: If config_id is invalid
        RuntimeError: If retrieval fails
    """
    if not config_id or not config_id.strip():
        raise ValueError("config_id is required and cannot be empty")

    return client.get_online_evaluation_config(config_id=config_id)


def list_online_evaluation_configs(
    client: EvaluationControlPlaneClient,
    agent_id: Optional[str] = None,
    max_results: int = 50,
) -> Dict[str, Any]:
    """List online evaluation configurations.

    Args:
        client: Control plane client instance
        agent_id: Optional filter by agent ID
        max_results: Maximum number of configs to return

    Returns:
        API response with configs list
    """
    if agent_id:
        logger.info("Listing online evaluation configs for agent: %s", agent_id)
    else:
        logger.info("Listing all online evaluation configs")

    response = client.list_online_evaluation_configs(
        agent_id=agent_id,
        max_results=max_results,
    )

    config_count = len(response.get("onlineEvaluationConfigs", []))
    logger.info("Found %d online evaluation config(s)", config_count)

    return response


def update_online_evaluation_config(
    client: EvaluationControlPlaneClient,
    config_id: str,
    status: Optional[str] = None,
    sampling_rate: Optional[float] = None,
    evaluator_list: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update online evaluation configuration with validation.

    Args:
        client: Control plane client instance
        config_id: Online evaluation config ID to update
        status: New status (ENABLED/DISABLED)
        sampling_rate: New sampling rate (0-100)
        evaluator_list: New list of evaluator IDs
        description: New description

    Returns:
        API response with updated config details

    Raises:
        ValueError: If validation fails
        RuntimeError: If update fails
    """
    if not config_id or not config_id.strip():
        raise ValueError("config_id is required and cannot be empty")

    if sampling_rate is not None and not 0 <= sampling_rate <= 100:
        raise ValueError(f"sampling_rate must be between 0 and 100, got {sampling_rate}")

    if status and status not in ["ENABLED", "DISABLED"]:
        raise ValueError(f"status must be ENABLED or DISABLED, got {status}")

    logger.info("Updating online evaluation config: %s", config_id)

    if status:
        logger.info("Setting status to: %s", status)
    if sampling_rate is not None:
        logger.info("Setting sampling rate to: %.1f%%", sampling_rate)
    if evaluator_list:
        logger.info("Updating evaluator list: %s", evaluator_list)

    response = client.update_online_evaluation_config(
        config_id=config_id,
        status=status,
        sampling_rate=sampling_rate,
        evaluator_list=evaluator_list,
        description=description,
    )

    logger.info("✓ Online evaluation config updated successfully")

    return response


def delete_online_evaluation_config(
    client: EvaluationControlPlaneClient,
    config_id: str,
    delete_execution_role: bool = False,
) -> None:
    """Delete online evaluation configuration.

    Args:
        client: Control plane client instance
        config_id: Online evaluation config ID to delete
        delete_execution_role: If True, also delete the IAM execution role (default: False)

    Raises:
        ValueError: If config_id is invalid
        RuntimeError: If deletion fails
    """
    if not config_id or not config_id.strip():
        raise ValueError("config_id is required and cannot be empty")

    logger.info("Deleting online evaluation config: %s", config_id)

    # Get config details to extract execution role ARN if needed
    execution_role_arn = None
    if delete_execution_role:
        try:
            config_details = client.get_online_evaluation_config(config_id=config_id)
            execution_role_arn = config_details.get("evaluationExecutionRoleArn")
            if execution_role_arn:
                logger.info("Will delete execution role: %s", execution_role_arn)
        except (ClientError, RuntimeError, KeyError) as e:
            logger.warning("Could not retrieve config details to get execution role: %s", e)

    # Delete the config
    client.delete_online_evaluation_config(config_id=config_id)
    logger.info("✓ Online evaluation config deleted successfully")

    # Delete the execution role if requested
    if delete_execution_role and execution_role_arn:
        _delete_execution_role(execution_role_arn)


def _delete_execution_role(role_arn: str) -> None:
    """Delete IAM execution role and its inline policies.

    Args:
        role_arn: ARN of the IAM role to delete
    """
    # Extract role name from ARN
    # ARN format: arn:aws:iam::123456789012:role/RoleName
    role_name = role_arn.split("/")[-1]

    logger.info("Deleting IAM execution role: %s", role_name)

    iam = boto3.client("iam")

    try:
        # First, delete all inline policies attached to the role
        try:
            response = iam.list_role_policies(RoleName=role_name)
            inline_policies = response.get("PolicyNames", [])

            for policy_name in inline_policies:
                logger.info("Deleting inline policy: %s", policy_name)
                iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
                logger.info("✓ Inline policy deleted: %s", policy_name)

        except ClientError as e:
            logger.warning("Error listing/deleting inline policies: %s", e)

        # Delete the role itself
        iam.delete_role(RoleName=role_name)
        logger.info("✓ IAM role deleted successfully: %s", role_name)

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchEntity":
            logger.warning("Role %s does not exist or was already deleted", role_name)
        elif error_code == "DeleteConflict":
            logger.error(
                "Cannot delete role %s: Role is still attached to resources or has managed policies. "
                "Detach all managed policies and resources before deleting.",
                role_name,
            )
            raise RuntimeError(f"Cannot delete role {role_name}: {e}") from e
        else:
            logger.error("Error deleting role %s: %s", role_name, e)
            raise RuntimeError(f"Failed to delete role {role_name}: {e}") from e
