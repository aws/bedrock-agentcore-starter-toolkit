"""Evaluation operations for agent performance assessment.

Refactored structure:
- data_plane_client: Thin client for evaluation API calls
- control_plane_client: Thin client for evaluator management
- processor: Business logic for evaluation orchestration
- models: Data models (requests, results)
- formatters: Display formatting logic
"""

from . import formatters
from .control_plane_client import EvaluationControlPlaneClient
from .data_plane_client import EvaluationDataPlaneClient
from .models import EvaluationRequest, EvaluationResult, EvaluationResults
from .on_demand_processor import EvaluationProcessor

__all__ = [
    "EvaluationDataPlaneClient",
    "EvaluationControlPlaneClient",
    "EvaluationProcessor",
    "EvaluationRequest",
    "EvaluationResult",
    "EvaluationResults",
    "formatters",
]
