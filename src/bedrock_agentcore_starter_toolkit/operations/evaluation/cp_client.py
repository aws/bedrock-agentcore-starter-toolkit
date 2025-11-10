"""Client for AgentCore Evaluation Control Plane API (evaluator CRUD)."""

import os
from typing import Any, Dict, Optional

import boto3


class EvaluationControlPlaneClient:
    """Client for Control Plane evaluator management operations.

    Handles CRUD operations for custom evaluators:
    - list_evaluators: List all evaluators (builtin + custom)
    - get_evaluator: Get evaluator details
    - create_evaluator: Create custom evaluator
    - update_evaluator: Update custom evaluator
    - delete_evaluator: Delete custom evaluator
    """

    DEFAULT_ENDPOINT = "https://gamma.us-east-1.elcapcp.genesis-primitives.aws.dev"
    DEFAULT_REGION = "us-east-1"

    def __init__(self, region: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize Control Plane client.

        Args:
            region: AWS region (defaults to env var AGENTCORE_EVAL_REGION or us-east-1)
            endpoint_url: API endpoint URL (defaults to env var AGENTCORE_EVAL_CP_ENDPOINT)
        """
        self.region = region or os.getenv("AGENTCORE_EVAL_REGION", self.DEFAULT_REGION)
        self.endpoint_url = endpoint_url or os.getenv("AGENTCORE_EVAL_CP_ENDPOINT", self.DEFAULT_ENDPOINT)

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
        """
        params = {"evaluatorId": evaluator_id}
        if description:
            params["description"] = description
        if config:
            params["evaluatorConfig"] = config
        return self.client.update_evaluator(**params)

    def delete_evaluator(self, evaluator_id: str) -> None:
        """Delete custom evaluator.

        Args:
            evaluator_id: Evaluator ID to delete
        """
        self.client.delete_evaluator(evaluatorId=evaluator_id)
