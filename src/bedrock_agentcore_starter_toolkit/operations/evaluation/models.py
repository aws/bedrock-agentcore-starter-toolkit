"""Data models for evaluation requests and results."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationRequest:
    """Request structure for evaluation API.

    API expects single evaluator per call with evaluator ID in URI path.
    """

    evaluator_id: str
    session_spans: List[Dict[str, Any]]
    evaluation_target: Optional[Dict[str, Any]] = None

    def to_api_request(self) -> tuple[str, Dict[str, Any]]:
        """Convert to API request format.

        Returns:
            Tuple of (evaluator_id, request_body)
        """
        request_body = {
            "evaluationInput": {"sessionSpans": self.session_spans},
        }
        if self.evaluation_target:
            request_body["evaluationTarget"] = self.evaluation_target
        return self.evaluator_id, request_body


@dataclass
class EvaluationResult:
    """Result from evaluation API."""

    evaluator_id: str
    evaluator_name: str
    evaluator_arn: str
    explanation: str
    context: Dict[str, Any]  # Contains spanContext union from API
    value: Optional[float] = None
    label: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None

    @classmethod
    def from_api_response(cls, result: Dict[str, Any]) -> "EvaluationResult":
        """Create from API response.

        Args:
            result: API response dictionary (EvaluationResultContent)

        Returns:
            EvaluationResult instance

        API response structure:
        {
            "evaluatorArn": "arn:...",
            "evaluatorId": "Builtin.Helpfulness",
            "evaluatorName": "Builtin.Helpfulness",
            "explanation": "...",
            "context": {"spanContext": {"sessionId": "...", "traceId": "...", "spanId": "..."}},
            "value": 0.8,  # optional
            "label": "helpful",  # optional
            "tokenUsage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},  # optional
            "error": "..."  # optional
        }
        """
        return cls(
            evaluator_id=result.get("evaluatorId", ""),
            evaluator_name=result.get("evaluatorName", ""),
            evaluator_arn=result.get("evaluatorArn", ""),
            explanation=result.get("explanation", ""),
            context=result.get("context", {}),
            value=result.get("value"),
            label=result.get("label"),
            token_usage=result.get("tokenUsage"),
            error=result.get("error"),
        )

    def has_error(self) -> bool:
        """Check if evaluation failed."""
        return self.error is not None


@dataclass
class EvaluationResults:
    """Container for multiple evaluation results."""

    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    results: List[EvaluationResult] = field(default_factory=list)
    input_data: Optional[Dict[str, Any]] = None  # Store OTel spans sent to API

    def add_result(self, result: EvaluationResult) -> None:
        """Add a result to the collection."""
        self.results.append(result)

    def has_errors(self) -> bool:
        """Check if any evaluation failed."""
        return any(r.has_error() for r in self.results)

    def get_successful_results(self) -> List[EvaluationResult]:
        """Get only successful evaluations."""
        return [r for r in self.results if not r.has_error()]

    def get_failed_results(self) -> List[EvaluationResult]:
        """Get only failed evaluations."""
        return [r for r in self.results if r.has_error()]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "summary": {
                "total_evaluations": len(self.results),
                "successful": len(self.get_successful_results()),
                "failed": len(self.get_failed_results()),
            },
            "results": [
                {
                    "evaluator_id": r.evaluator_id,
                    "evaluator_name": r.evaluator_name,
                    "evaluator_arn": r.evaluator_arn,
                    "value": r.value,
                    "label": r.label,
                    "explanation": r.explanation,
                    "context": r.context,
                    "token_usage": r.token_usage,
                    "error": r.error,
                }
                for r in self.results
            ],
        }
        if self.input_data is not None:
            result["input_data"] = self.input_data
        return result


@dataclass
class OnlineEvaluationConfig:
    """Model for online evaluation configuration.

    Represents a configuration for continuous automatic evaluation of agent
    interactions by monitoring CloudWatch logs.
    """

    config_id: str
    config_name: str
    agent_id: str
    agent_name: str
    log_group_name: str
    sampling_rate: float
    evaluator_list: List[str]
    execution_role: str
    status: str  # ENABLED or DISABLED
    config_arn: Optional[str] = None
    agent_endpoint: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    cloudwatch_logs_url: Optional[str] = None
    dashboard_url: Optional[str] = None

    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> "OnlineEvaluationConfig":
        """Create from API response.

        Args:
            response: API response dictionary

        Returns:
            OnlineEvaluationConfig instance

        API response structure:
        {
            "onlineEvaluationConfigId": "config-123",
            "onlineEvaluationConfigName": "my-config",
            "onlineEvaluationConfigArn": "arn:...",
            "agentId": "agent-456",
            "agentName": "MyAgent",
            "agentEndpoint": "DEFAULT",
            "logGroupName": "/aws/bedrock-agentcore/agents/agent-456",
            "samplingRate": 50.0,
            "evaluatorList": ["Builtin.Helpfulness"],
            "executionRole": "arn:...:role/...",
            "status": "ENABLED",
            "description": "...",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
            "cloudwatch_logs_url": "https://...",  # enriched field
            "dashboard_url": "https://..."  # enriched field
        }
        """
        return cls(
            config_id=response["onlineEvaluationConfigId"],
            config_name=response["onlineEvaluationConfigName"],
            agent_id=response["agentId"],
            agent_name=response["agentName"],
            log_group_name=response["logGroupName"],
            sampling_rate=response["samplingRate"],
            evaluator_list=response["evaluatorList"],
            execution_role=response["executionRole"],
            status=response["status"],
            config_arn=response.get("onlineEvaluationConfigArn"),
            agent_endpoint=response.get("agentEndpoint"),
            description=response.get("description"),
            created_at=response.get("createdAt"),
            updated_at=response.get("updatedAt"),
            cloudwatch_logs_url=response.get("cloudwatch_logs_url"),
            dashboard_url=response.get("dashboard_url"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "config_id": self.config_id,
            "config_name": self.config_name,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "log_group_name": self.log_group_name,
            "sampling_rate": self.sampling_rate,
            "evaluator_list": self.evaluator_list,
            "execution_role": self.execution_role,
            "status": self.status,
            "config_arn": self.config_arn,
            "agent_endpoint": self.agent_endpoint,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "cloudwatch_logs_url": self.cloudwatch_logs_url,
            "dashboard_url": self.dashboard_url,
        }

    def is_enabled(self) -> bool:
        """Check if config is enabled."""
        return self.status == "ENABLED"
