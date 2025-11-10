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
