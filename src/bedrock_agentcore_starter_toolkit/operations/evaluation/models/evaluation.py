"""Data models for evaluation requests and results."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EvaluationRequest:
    """Request structure for evaluation API."""

    evaluators: List[str]
    spans: List[Dict[str, Any]]
    evaluation_target: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request format."""
        request = {"evaluators": self.evaluators, "evaluatorInput": {"spans": self.spans}}
        if self.evaluation_target:
            request["evaluationTarget"] = self.evaluation_target
        return request


@dataclass
class EvaluationResult:
    """Result from evaluation API."""

    evaluator: str
    explanation: str
    context: Dict[str, Any]
    value: Optional[float] = None
    label: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
    span_context: Optional[Dict[str, Any]] = None  # Separate span context (not evaluation-specific)

    @classmethod
    def from_api_response(
        cls, result: Dict[str, Any], span_context: Optional[Dict[str, Any]] = None
    ) -> "EvaluationResult":
        """Create from API response with optional span context.

        Args:
            result: API response dictionary
            span_context: Optional context with span/trace IDs and metadata (kept separate)

        Returns:
            EvaluationResult with evaluation-specific context and separate span context
        """
        return cls(
            evaluator=result.get("evaluator", ""),
            explanation=result.get("explanation", ""),
            context=result.get("context", {}),  # Evaluation-specific context from API
            value=result.get("value"),
            label=result.get("label"),
            token_usage=result.get("tokenUsage"),
            error=result.get("error"),
            span_context=span_context,  # Keep span context separate
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
            "results": [
                {
                    "evaluator": r.evaluator,
                    "explanation": r.explanation,
                    "context": r.context,
                    "span_context": r.span_context,
                    "value": r.value,
                    "label": r.label,
                    "token_usage": r.token_usage,
                    "error": r.error,
                }
                for r in self.results
            ],
        }
        if self.input_data is not None:
            result["input_data"] = self.input_data
        return result
