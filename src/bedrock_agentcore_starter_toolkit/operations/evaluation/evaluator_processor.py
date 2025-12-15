"""Evaluator management operations - business logic for CRUD operations.

This module contains all business logic for evaluator management,
separated from UI/display concerns.
"""

from typing import Any, Dict, List, Optional, Tuple

from .control_plane_client import EvaluationControlPlaneClient

# =============================================================================
# Filtering and Validation
# =============================================================================


def filter_custom_evaluators(evaluators: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter list to only custom evaluators.

    Args:
        evaluators: List of evaluator dicts

    Returns:
        List of custom evaluators only (non-Builtin)
    """
    return [e for e in evaluators if not e.get("evaluatorId", "").startswith("Builtin.")]


def is_builtin_evaluator(evaluator_id: str) -> bool:
    """Check if evaluator ID is a builtin.

    Args:
        evaluator_id: Evaluator ID to check

    Returns:
        True if builtin, False otherwise
    """
    return evaluator_id.startswith("Builtin.")


def validate_evaluator_config(config_data: Dict[str, Any]) -> None:
    """Validate evaluator configuration structure.

    Args:
        config_data: Config dict to validate

    Raises:
        ValueError: If config structure is invalid
    """
    if "llmAsAJudge" not in config_data:
        raise ValueError("Config must contain 'llmAsAJudge' key")


# =============================================================================
# Evaluator Retrieval and Preparation
# =============================================================================


def get_evaluator_for_duplication(
    client: EvaluationControlPlaneClient, evaluator_id: str
) -> Tuple[Dict[str, Any], str, str]:
    """Get evaluator details and prepare for duplication.

    Args:
        client: Control plane client
        evaluator_id: ID of evaluator to duplicate

    Returns:
        Tuple of (config_data, level, description)

    Raises:
        ValueError: If evaluator cannot be duplicated
    """
    # Check if builtin
    if is_builtin_evaluator(evaluator_id):
        raise ValueError("Built-in evaluators cannot be duplicated")

    # Fetch evaluator details
    details = client.get_evaluator(evaluator_id=evaluator_id)

    # Extract config
    config_data = details.get("evaluatorConfig", {})
    validate_evaluator_config(config_data)

    # Extract metadata
    level = details.get("level", "TRACE")
    description = details.get("description", "")

    return config_data, level, description


# =============================================================================
# Evaluator Creation
# =============================================================================


def create_evaluator(
    client: EvaluationControlPlaneClient,
    name: str,
    config: Dict[str, Any],
    level: str = "TRACE",
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new evaluator.

    Args:
        client: Control plane client
        name: Evaluator name
        config: Evaluator config
        level: Evaluation level (SESSION, TRACE, TOOL_CALL)
        description: Optional description

    Returns:
        API response dict with evaluatorId and evaluatorArn

    Raises:
        ValueError: If config is invalid
    """
    validate_evaluator_config(config)
    return client.create_evaluator(name=name, config=config, level=level, description=description)


def duplicate_evaluator(
    client: EvaluationControlPlaneClient, source_evaluator_id: str, new_name: str, new_description: Optional[str] = None
) -> Dict[str, Any]:
    """Duplicate an existing custom evaluator.

    Args:
        client: Control plane client
        source_evaluator_id: ID of evaluator to duplicate
        new_name: Name for new evaluator
        new_description: Optional new description (uses source if None)

    Returns:
        API response dict with evaluatorId and evaluatorArn

    Raises:
        ValueError: If source evaluator cannot be duplicated
    """
    # Get source evaluator config
    config_data, level, original_description = get_evaluator_for_duplication(client, source_evaluator_id)

    # Use source description if not provided
    description = new_description if new_description is not None else original_description

    # Create new evaluator
    return create_evaluator(client, new_name, config_data, level, description)


# =============================================================================
# Evaluator Update
# =============================================================================


def update_evaluator(
    client: EvaluationControlPlaneClient,
    evaluator_id: str,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update an existing evaluator.

    Args:
        client: Control plane client
        evaluator_id: Evaluator ID to update
        description: Optional new description
        config: Optional new config

    Returns:
        API response dict

    Raises:
        ValueError: If trying to update a builtin evaluator or no changes provided
    """
    if is_builtin_evaluator(evaluator_id):
        raise ValueError("Built-in evaluators cannot be updated")

    if not description and not config:
        raise ValueError("No updates provided")

    if config:
        validate_evaluator_config(config)

    return client.update_evaluator(evaluator_id=evaluator_id, description=description, config=config)


def update_evaluator_instructions(
    client: EvaluationControlPlaneClient, evaluator_id: str, new_instructions: str
) -> Dict[str, Any]:
    """Update only the instructions of an evaluator.

    Args:
        client: Control plane client
        evaluator_id: Evaluator ID to update
        new_instructions: New instructions text

    Returns:
        API response dict

    Raises:
        ValueError: If evaluator cannot be updated
    """
    # Get current config
    details = client.get_evaluator(evaluator_id=evaluator_id)
    config_data = details.get("evaluatorConfig", {})
    validate_evaluator_config(config_data)

    # Update instructions
    llm_config = config_data.get("llmAsAJudge", {})
    llm_config["instructions"] = new_instructions.strip()

    # Update evaluator
    return client.update_evaluator(evaluator_id=evaluator_id, config=config_data)


# =============================================================================
# Evaluator Deletion
# =============================================================================


def delete_evaluator(client: EvaluationControlPlaneClient, evaluator_id: str) -> None:
    """Delete an evaluator.

    Args:
        client: Control plane client
        evaluator_id: Evaluator ID to delete

    Raises:
        ValueError: If trying to delete a builtin evaluator
    """
    # Check if builtin
    if is_builtin_evaluator(evaluator_id):
        raise ValueError("Built-in evaluators cannot be deleted")

    client.delete_evaluator(evaluator_id=evaluator_id)


# =============================================================================
# List and Query Operations
# =============================================================================


def list_evaluators(client: EvaluationControlPlaneClient, max_results: int = 50) -> Dict[str, Any]:
    """List all evaluators.

    Args:
        client: Control plane client
        max_results: Maximum number of evaluators to return

    Returns:
        API response dict with evaluators list
    """
    return client.list_evaluators(max_results=max_results)


def get_evaluator(client: EvaluationControlPlaneClient, evaluator_id: str) -> Dict[str, Any]:
    """Get evaluator details.

    Args:
        client: Control plane client
        evaluator_id: Evaluator ID to fetch

    Returns:
        API response dict with evaluator details
    """
    return client.get_evaluator(evaluator_id=evaluator_id)
