"""Thin client for AgentCore Evaluation Data Plane API.

This client only makes API calls - all business logic is in processor.py
"""

import logging
import os
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from ...utils.endpoints import get_data_plane_endpoint
from .models import EvaluationRequest

logger = logging.getLogger(__name__)


class EvaluationDataPlaneClient:
    """Thin client for AgentCore Evaluation Data Plane API.

    Handles only API calls to the evaluation data plane:
    - evaluate: Call evaluation API with spans

    NO business logic - that belongs in EvaluationProcessor.
    """

    def __init__(self, region_name: str, endpoint_url: Optional[str] = None, boto_client: Optional[Any] = None):
        """Initialize evaluation data plane client.

        Args:
            region_name: AWS region name (required)
            endpoint_url: Optional custom endpoint URL (defaults to env var for testing)
            boto_client: Optional pre-configured boto3 client for testing
        """
        self.region = region_name
        self.endpoint_url = endpoint_url or os.getenv("AGENTCORE_EVAL_ENDPOINT") or get_data_plane_endpoint(region_name)

        if boto_client:
            self.client = boto_client
        else:
            # Configure retries for transient failures
            retry_config = Config(
                retries={
                    "max_attempts": 3,
                    "mode": "adaptive",  # Adaptive retry mode for better reliability
                }
            )
            self.client = boto3.client(
                "bedrock-agentcore",
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                config=retry_config,
            )

    def evaluate(
        self, evaluator_id: str, session_spans: List[Dict[str, Any]], evaluation_target: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call evaluation API with transformed spans.

        Note: API accepts ONE evaluator per call via URI path.

        Args:
            evaluator_id: Single evaluator identifier (e.g., "Builtin.Helpfulness")
            session_spans: List of OpenTelemetry-formatted span documents
            evaluation_target: Optional dict with spanIds or traceIds to evaluate

        Returns:
            Raw API response with evaluationResults

        Raises:
            RuntimeError: If API call fails
        """
        request = EvaluationRequest(
            evaluator_id=evaluator_id, session_spans=session_spans, evaluation_target=evaluation_target
        )

        evaluator_id_param, request_body = request.to_api_request()

        # Removed verbose logging
        # print(f"🔍 Evaluation API Request:")
        # print(f"   Region: {self.region}")
        # print(f"   Endpoint: {self.endpoint_url}")
        # print(f"   Evaluator: {evaluator_id_param}")
        # print(f"   Spans count: {len(session_spans)}")

        try:
            response = self.client.evaluate(evaluatorId=evaluator_id_param, **request_body)

            # Removed verbose logging
            # response_metadata = response.get("ResponseMetadata", {})
            # request_id = response_metadata.get("RequestId", "N/A")
            # print(f"✅ Request ID: {request_id}")

            return response

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "N/A")

            # Log error with structured information
            logger.error("Evaluation API error: %s (RequestId: %s, Code: %s)", error_msg, request_id, error_code)

            raise RuntimeError(f"Evaluation API error ({error_code}): {error_msg}") from e
