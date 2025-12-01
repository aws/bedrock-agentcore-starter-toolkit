"""Thin client for AgentCore Evaluation Control Plane API (evaluator CRUD + online evaluation config).

This client only makes API calls - all business logic is in processor.py
"""

import logging
import os
from typing import Any, Dict, List, Optional

import boto3

from ...utils.endpoints import get_control_plane_endpoint
from ...utils.runtime.logs import get_agent_runtime_log_group
from .create_role import get_or_create_evaluation_execution_role

logger = logging.getLogger(__name__)


class EvaluationControlPlaneClient:
    """Thin client for Control Plane evaluator management and online evaluation config operations.

    Handles CRUD operations for custom evaluators:
    - list_evaluators: List all evaluators (builtin + custom) with level & description
    - get_evaluator: Get evaluator details
    - create_evaluator: Create custom evaluator
    - update_evaluator: Update custom evaluator
    - delete_evaluator: Delete custom evaluator

    Handles CRUD operations for online evaluation configs:
    - create_online_evaluation_config: Create online evaluation configuration
    - get_online_evaluation_config: Get online evaluation config details
    - list_online_evaluation_configs: List all online evaluation configs
    - update_online_evaluation_config: Update online evaluation config
    - delete_online_evaluation_config: Delete online evaluation config

    NO business logic - that belongs in EvaluationProcessor or formatters.
    """

    def __init__(self, region_name: str, endpoint_url: Optional[str] = None, boto_client: Optional[Any] = None):
        """Initialize Control Plane client.

        Args:
            region_name: AWS region name (required)
            endpoint_url: Optional custom endpoint URL (defaults to env var for testing)
            boto_client: Optional pre-configured boto3 client for testing
        """
        self.region = region_name
        self.endpoint_url = (
            endpoint_url or os.getenv("AGENTCORE_EVAL_CP_ENDPOINT") or get_control_plane_endpoint(region_name)
        )

        # Get account ID for role creation
        sts = boto3.client("sts")
        self.account_id = sts.get_caller_identity()["Account"]

        if boto_client:
            self.client = boto_client
        else:
            self.client = boto3.client(
                "bedrock-agentcore-control",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
            )

    def list_evaluators(self, max_results: int = 50) -> Dict[str, Any]:
        """List all evaluators (builtin and custom).

        Returns evaluators with level and description for display.

        Args:
            max_results: Maximum number of evaluators to return

        Returns:
            API response with evaluators list
            Example structure:
            {
                "evaluators": [
                    {
                        "evaluatorId": "Builtin.Helpfulness",
                        "evaluatorName": "Builtin.Helpfulness",
                        "evaluatorLevel": "TRACE",
                        "description": "Evaluates helpfulness...",
                        "evaluatorArn": "arn:...",
                        ...
                    }
                ]
            }
        """
        return self.client.list_evaluators(maxResults=max_results)

    def get_evaluator(self, evaluator_id: str) -> Dict[str, Any]:
        """Get evaluator details.

        Args:
            evaluator_id: Evaluator ID (e.g., Builtin.Helpfulness or custom-id)

        Returns:
            API response with evaluator details including level and config
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

    # =============================================================================
    # Online Evaluation Config Operations
    # =============================================================================

    def create_online_evaluation_config(
        self,
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
        """Create online evaluation configuration.

        Enables continuous automatic evaluation of agent interactions by monitoring
        CloudWatch logs and evaluating sampled interactions in real-time.

        Args:
            config_name: Name for the evaluation configuration
            agent_id: Bedrock AgentCore agent ID to evaluate
            agent_endpoint: Agent endpoint type (DEFAULT, DRAFT, or alias ARN)
            config_description: Optional description
            sampling_rate: Percentage of interactions to evaluate (0-100, default: 1.0)
            evaluator_list: List of evaluator IDs (default: ["Builtin.Helpfulness"])
            execution_role: IAM role ARN for evaluation execution
            auto_create_execution_role: Auto-create role if not provided (default: True)
            enable_on_create: Enable config immediately after creation (default: True)

        Returns:
            API response with config details including:
            - onlineEvaluationConfigId: Unique config identifier
            - onlineEvaluationConfigArn: ARN of the config
            - agentId, agentName, samplingRate, etc.

        Raises:
            ValueError: If agent_id is invalid or sampling_rate out of range
            RuntimeError: If role creation fails or API call fails
        """
        logger.info("Creating online evaluation config: %s for agent: %s", config_name, agent_id)

        # Auto-create execution role if needed
        if auto_create_execution_role and not execution_role:
            logger.info("Auto-creating execution role for config: %s", config_name)
            execution_role = get_or_create_evaluation_execution_role(
                session=boto3.Session(),
                region=self.region,
                account_id=self.account_id,
                config_name=config_name,
            )
            logger.info("✓ Execution role ready: %s", execution_role)

        # Default evaluators
        if not evaluator_list:
            evaluator_list = ["Builtin.GoalSuccessRate"]

        # Construct CloudWatch log group using shared runtime utility
        # This ensures consistency across observability and evaluation features
        runtime_log_group = get_agent_runtime_log_group(agent_id, agent_endpoint)

        # Online evaluation monitors the runtime log group where agent traces are written
        log_group_names = [runtime_log_group]

        logger.debug("Using log group: %s for agent: %s", runtime_log_group, agent_id)

        # Build API request with proper structure per API model
        params = {
            "onlineEvaluationConfigName": config_name,
            "rule": {"samplingConfig": {"samplingPercentage": sampling_rate}},
            "dataSourceConfig": {
                "cloudWatchLogs": {"logGroupNames": log_group_names, "serviceNames": ["bedrock-agentcore"]}
            },
            "evaluators": [{"evaluatorId": evaluator_id} for evaluator_id in evaluator_list],
            "evaluationExecutionRoleArn": execution_role,
            "enableOnCreate": enable_on_create,
        }

        if config_description:
            params["description"] = config_description

        logger.debug("Creating online evaluation config with params: %s", params)

        response = self.client.create_online_evaluation_config(**params)

        logger.info("✓ Online evaluation config created: %s", response.get("onlineEvaluationConfigId"))
        return response

    def get_online_evaluation_config(self, config_id: str) -> Dict[str, Any]:
        """Get online evaluation configuration details.

        Args:
            config_id: Online evaluation config ID

        Returns:
            API response with config details including:
            - onlineEvaluationConfigId, onlineEvaluationConfigArn
            - agentId, agentName, samplingRate
            - evaluatorList, executionRole
            - status (ENABLED/DISABLED)
            - createdAt, updatedAt
        """
        return self.client.get_online_evaluation_config(onlineEvaluationConfigId=config_id)

    def list_online_evaluation_configs(self, agent_id: Optional[str] = None, max_results: int = 50) -> Dict[str, Any]:
        """List online evaluation configurations.

        Args:
            agent_id: Optional filter by agent ID
            max_results: Maximum number of configs to return

        Returns:
            API response with configs list:
            {
                "onlineEvaluationConfigs": [
                    {
                        "onlineEvaluationConfigId": "...",
                        "onlineEvaluationConfigName": "...",
                        "agentId": "...",
                        "status": "ENABLED",
                        ...
                    }
                ]
            }
        """
        params = {"maxResults": max_results}
        if agent_id:
            params["agentId"] = agent_id

        return self.client.list_online_evaluation_configs(**params)

    def update_online_evaluation_config(
        self,
        config_id: str,
        status: Optional[str] = None,
        sampling_rate: Optional[float] = None,
        evaluator_list: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update online evaluation configuration.

        Args:
            config_id: Online evaluation config ID to update
            status: New status (ENABLED/DISABLED)
            sampling_rate: New sampling rate (0-100)
            evaluator_list: New list of evaluator IDs
            description: New description

        Returns:
            API response with updated config details
        """
        params = {"onlineEvaluationConfigId": config_id}

        if status:
            params["status"] = status
        if sampling_rate is not None:
            params["samplingRate"] = sampling_rate
        if evaluator_list:
            params["evaluatorList"] = evaluator_list
        if description:
            params["description"] = description

        return self.client.update_online_evaluation_config(**params)

    def delete_online_evaluation_config(self, config_id: str) -> None:
        """Delete online evaluation configuration.

        Args:
            config_id: Online evaluation config ID to delete
        """
        self.client.delete_online_evaluation_config(onlineEvaluationConfigId=config_id)
