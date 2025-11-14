"""Client for AgentCore Evaluation Control Plane API (evaluator CRUD)."""

import os
from typing import Any, Dict, Optional

import boto3

from ...utils.endpoints import get_control_plane_endpoint


class EvaluationControlPlaneClient:
    """Client for Control Plane evaluator management operations.

    Handles CRUD operations for custom evaluators:
    - list_evaluators: List all evaluators (builtin + custom)
    - get_evaluator: Get evaluator details
    - create_evaluator: Create custom evaluator
    - update_evaluator: Update custom evaluator
    - delete_evaluator: Delete custom evaluator
    """

    DEFAULT_REGION = "us-east-1"

    def __init__(self, region: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize Control Plane client.

        Args:
            region: AWS region (defaults to env var AGENTCORE_EVAL_REGION or us-east-1)
            endpoint_url: Optional custom endpoint URL (defaults to env var AGENTCORE_EVAL_CP_ENDPOINT for testing)
        """
        self.region = region or os.getenv("AGENTCORE_EVAL_REGION", self.DEFAULT_REGION)

        # Use AGENTCORE_EVAL_CP_ENDPOINT env var for gamma testing, otherwise use prod agentcore control endpoint
        self.endpoint_url = (
            endpoint_url or os.getenv("AGENTCORE_EVAL_CP_ENDPOINT") or get_control_plane_endpoint(self.region)
        )

        self.client = boto3.client(
            "agentcore-evaluation-controlplane",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
        )

    def list_evaluators(self, max_results: int = 50) -> Dict[str, Any]:
        """List all evaluators (builtin and custom).

        Args:
            max_results: Maximum number of evaluators to return

        Returns:
            API response with evaluators list
        """
        return self.client.list_evaluators(maxResults=max_results)

    def get_evaluator(self, evaluator_id: str) -> Dict[str, Any]:
        """Get evaluator details.

        Args:
            evaluator_id: Evaluator ID (e.g., Builtin.Helpfulness or custom-id)

        Returns:
            API response with evaluator details
        """
        return self.client.get_evaluator(evaluatorId=evaluator_id)

    def create_evaluator(
        self, name: str, config: Dict[str, Any], level: str = "TRACE", description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create custom evaluator.

        Args:
            name: Evaluator name
            config: Evaluator configuration (llmAsAJudge structure)
            level: Evaluation level (TRACE, SPAN, SESSION)
            description: Optional description

        Returns:
            API response with evaluatorId and evaluatorArn
        """
        params = {"evaluatorName": name, "level": level, "evaluatorConfig": config}
        if description:
            params["description"] = description
        return self.client.create_evaluator(**params)

    def update_evaluator(
        self, evaluator_id: str, description: Optional[str] = None, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update custom evaluator.

        Args:
            evaluator_id: Evaluator ID to update
            description: New description (optional)
            config: New evaluator config (optional)

        Returns:
            API response with updated details

        Note:
            AWS API requires evaluatorConfig to be present even for description-only updates.
            If only description is provided, the existing config will be fetched and reused.
        """
        params = {"evaluatorId": evaluator_id}
        if description:
            params["description"] = description

        # AWS API requires evaluatorConfig to be present
        # If only description is provided, fetch existing config
        if config:
            params["evaluatorConfig"] = config
        elif description:
            # Fetch current config to include in update
            current = self.get_evaluator(evaluator_id=evaluator_id)
            current_config = current.get("evaluatorConfig")
            if current_config:
                params["evaluatorConfig"] = current_config
            # If no config found, let API handle the error

        return self.client.update_evaluator(**params)

    def delete_evaluator(self, evaluator_id: str) -> None:
        """Delete custom evaluator.

        Args:
            evaluator_id: Evaluator ID to delete
        """
        self.client.delete_evaluator(evaluatorId=evaluator_id)
