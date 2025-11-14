"""Client for AgentCore Evaluation DataPlane API."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from ...utils.endpoints import get_data_plane_endpoint
from ..constants import DEFAULT_RUNTIME_SUFFIX
from ..observability.client import ObservabilityClient
from ..observability.models.telemetry import TraceData
from .constants import (
    DEFAULT_MAX_EVALUATION_ITEMS,
    SESSION_SCOPED_EVALUATORS,
)
from .models.evaluation import EvaluationRequest, EvaluationResult, EvaluationResults


class EvaluationClient:
    """Client for AgentCore Evaluation Data Plane API.

    Handles on-demand evaluation operations:
    - evaluate: Evaluate traces/spans with a single evaluator
    - evaluate_session: Evaluate a full session with multiple evaluators
    """

    DEFAULT_REGION = "us-east-1"

    def __init__(
        self, region: Optional[str] = None, endpoint_url: Optional[str] = None, boto_client: Optional[Any] = None
    ):
        """Initialize evaluation client.

        Args:
            region: AWS region (defaults to env var or us-east-1)
            endpoint_url: Optional custom endpoint URL (defaults to env var AGENTCORE_EVAL_ENDPOINT for testing)
            boto_client: Optional pre-configured boto3 client for testing
        """
        self.region = region or os.getenv("AGENTCORE_EVAL_REGION", self.DEFAULT_REGION)

        # Use AGENTCORE_EVAL_ENDPOINT env var for gamma testing, otherwise use prod agentcore endpoint
        self.endpoint_url = endpoint_url or os.getenv("AGENTCORE_EVAL_ENDPOINT") or get_data_plane_endpoint(self.region)

        if boto_client:
            self.client = boto_client
        else:
            self.client = boto3.client(
                "agentcore-evaluation-dataplane", region_name=self.region, endpoint_url=self.endpoint_url
            )

    def _is_session_scoped_evaluator(self, evaluator: str) -> bool:
        """Check if evaluator requires session-level data across all traces.

        Args:
            evaluator: Evaluator identifier

        Returns:
            True if evaluator needs data from all traces in session
        """
        return evaluator in SESSION_SCOPED_EVALUATORS

    def _extract_raw_spans(self, trace_data: TraceData) -> List[Dict[str, Any]]:
        """Extract raw span documents from TraceData.

        Args:
            trace_data: TraceData containing spans and runtime logs

        Returns:
            List of raw span documents
        """
        raw_spans = []

        # Extract raw_message from spans (contains full OTel span document)
        for span in trace_data.spans:
            if span.raw_message:
                raw_spans.append(span.raw_message)

        # Extract raw_message from runtime logs (contains OTel log events)
        for log in trace_data.runtime_logs:
            if log.raw_message:
                raw_spans.append(log.raw_message)

        return raw_spans

    def _filter_relevant_spans(self, raw_spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter to only high-signal spans for evaluation.

        Keeps only:
        - Spans with gen_ai.* attributes (LLM calls, agent operations)
        - Log events with conversation data (input/output messages)

        Args:
            raw_spans: List of raw span/log documents

        Returns:
            Filtered list of relevant spans
        """
        relevant_spans = []
        for span_doc in raw_spans:
            # Check attributes for gen_ai prefix
            attributes = span_doc.get("attributes", {})
            if any(k.startswith("gen_ai") for k in attributes.keys()):
                relevant_spans.append(span_doc)
                continue

            # Check if it's a log with conversation data
            body = span_doc.get("body", {})
            if isinstance(body, dict) and ("input" in body or "output" in body):
                relevant_spans.append(span_doc)

        return relevant_spans

    def _filter_traces_up_to(self, trace_data: TraceData, target_trace_id: str) -> TraceData:
        """Filter trace data to include target trace and all previous traces chronologically.

        Args:
            trace_data: TraceData containing all session data
            target_trace_id: Target trace ID to filter to

        Returns:
            Filtered TraceData with target trace and all earlier traces
        """
        # Get all trace IDs ordered by earliest start time
        trace_times = {}
        for span in trace_data.spans:
            if span.trace_id not in trace_times:
                trace_times[span.trace_id] = span.start_time_unix_nano or 0
            else:
                # Keep earliest time for this trace
                if span.start_time_unix_nano:
                    trace_times[span.trace_id] = min(trace_times[span.trace_id], span.start_time_unix_nano)

        # Sort trace IDs by time
        sorted_traces = sorted(trace_times.items(), key=lambda x: x[1])

        # Find position of target trace
        included_traces = set()
        for trace_id, _ in sorted_traces:
            included_traces.add(trace_id)
            if trace_id == target_trace_id:
                break

        # Filter trace_data to included traces
        return TraceData(
            session_id=trace_data.session_id,
            spans=[s for s in trace_data.spans if s.trace_id in included_traces],
            runtime_logs=[log for log in trace_data.runtime_logs if log.trace_id in included_traces],
        )

    def _get_most_recent_session_spans(
        self, trace_data: TraceData, max_items: int = DEFAULT_MAX_EVALUATION_ITEMS
    ) -> List[Dict[str, Any]]:
        """Get most recent relevant spans across all traces in session.

        Collects spans with gen_ai attributes and log events with conversation data,
        sorted by timestamp to get the most recent items.

        Args:
            trace_data: TraceData containing all session data
            max_items: Maximum number of items to return (default: 1000)

        Returns:
            List of raw span documents, most recent first
        """
        # Extract raw spans from all traces
        raw_spans = self._extract_raw_spans(trace_data)

        if not raw_spans:
            return []

        # Filter to only relevant spans
        relevant_spans = self._filter_relevant_spans(raw_spans)

        # Sort by timestamp (most recent first)
        def get_timestamp(span_doc):
            # Spans have startTimeUnixNano, logs have timeUnixNano
            return span_doc.get("startTimeUnixNano") or span_doc.get("timeUnixNano") or 0

        relevant_spans.sort(key=get_timestamp, reverse=True)

        # Return most recent max_items
        return relevant_spans[:max_items]

    def _fetch_session_data(self, session_id: str, agent_id: str, region: str) -> TraceData:
        """Fetch session data from CloudWatch.

        Args:
            session_id: Session ID to fetch
            agent_id: Agent ID for filtering
            region: AWS region

        Returns:
            TraceData with session spans and logs

        Raises:
            RuntimeError: If session data cannot be fetched
        """
        obs_client = ObservabilityClient(region_name=region, agent_id=agent_id, runtime_suffix=DEFAULT_RUNTIME_SUFFIX)

        # Default 7-day lookback
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        try:
            trace_data = obs_client.get_session_data(
                session_id=session_id, start_time_ms=start_time_ms, end_time_ms=end_time_ms, include_runtime_logs=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to fetch session data: {e}") from e

        if not trace_data or not trace_data.spans:
            raise RuntimeError(f"No trace data found for session {session_id}")

        return trace_data

    def _count_span_types(self, raw_spans: List[Dict[str, Any]]) -> tuple:
        """Count spans, logs, and gen_ai spans.

        Args:
            raw_spans: List of raw span documents

        Returns:
            Tuple of (spans_count, logs_count, genai_spans_count)
        """
        spans_count = sum(1 for item in raw_spans if "spanId" in item and "startTimeUnixNano" in item)
        logs_count = sum(1 for item in raw_spans if "body" in item and "timeUnixNano" in item)
        genai_spans = sum(
            1
            for span in raw_spans
            if "spanId" in span and any(k.startswith("gen_ai") for k in span.get("attributes", {}).keys())
        )
        return spans_count, logs_count, genai_spans

    def _execute_evaluators(
        self,
        evaluators: List[str],
        otel_spans: List[Dict[str, Any]],
        session_id: str,
        evaluation_target: Optional[Dict[str, Any]] = None,
    ) -> List[EvaluationResult]:
        """Execute evaluators and return results.

        Note: Calls API once per evaluator since API accepts single evaluator in URI path.

        Args:
            evaluators: List of evaluator identifiers
            otel_spans: OTel-formatted spans/logs to evaluate
            session_id: Session ID for context
            evaluation_target: Optional dict specifying which traces/spans to evaluate

        Returns:
            List of EvaluationResult objects (including errors)
        """
        results = []

        for evaluator in evaluators:
            try:
                # Call API with single evaluator
                response = self.evaluate(
                    evaluator_id=evaluator, session_spans=otel_spans, evaluation_target=evaluation_target
                )

                # API returns {evaluationResults: [...]}
                api_results = response.get("evaluationResults", [])

                if not api_results:
                    print(f"Warning: Evaluator {evaluator} returned no results")

                for api_result in api_results:
                    result = EvaluationResult.from_api_response(api_result)
                    results.append(result)

            except Exception as e:
                # Create error result with required fields
                error_result = EvaluationResult(
                    evaluator_id=evaluator,
                    evaluator_name=evaluator,
                    evaluator_arn="",  # Not available on error
                    explanation=f"Evaluation failed: {str(e)}",
                    context={"spanContext": {"sessionId": session_id}},
                    error=str(e),
                )
                results.append(error_result)

        return results

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
            ClientError: If API call fails
        """
        request = EvaluationRequest(
            evaluator_id=evaluator_id, session_spans=session_spans, evaluation_target=evaluation_target
        )

        evaluator_id_param, request_body = request.to_api_request()

        try:
            response = self.client.evaluate(evaluatorId=evaluator_id_param, **request_body)
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise RuntimeError(f"Evaluation API error ({error_code}): {error_msg}") from e

    def evaluate_session(
        self,
        session_id: str,
        evaluators: List[str],
        agent_id: str,
        region: str,
        trace_id: Optional[str] = None,
    ) -> EvaluationResults:
        """Evaluate a session using multiple evaluators.

        Default behavior: Evaluates all traces in session (most recent 1000 spans).
        With trace_id: Evaluates only that trace (includes spans from all previous traces for context).

        Args:
            session_id: Session ID to evaluate
            evaluators: List of evaluator identifiers
            agent_id: Agent ID for fetching session data
            region: AWS region for ObservabilityClient
            trace_id: Optional trace ID - evaluates only this trace, with previous traces for context

        Returns:
            EvaluationResults containing all evaluation results

        Raises:
            RuntimeError: If session data cannot be fetched or evaluation fails
        """
        # 1. Fetch session data
        trace_data = self._fetch_session_data(session_id, agent_id, region)

        # Log session stats
        num_traces = len(trace_data.get_trace_ids())
        num_spans = len(trace_data.spans)
        print(f"Found {num_spans} spans across {num_traces} traces in session")

        # Separate session-scoped and trace-scoped evaluators
        session_scoped = [e for e in evaluators if self._is_session_scoped_evaluator(e)]
        trace_scoped = [e for e in evaluators if not self._is_session_scoped_evaluator(e)]

        results = EvaluationResults(session_id=session_id, trace_id=trace_id)

        # Track input spans sent to API for export
        input_spans = []

        # Handle session-scoped evaluators (need data across all traces)
        if session_scoped:
            print(f"Session-scoped evaluators: {', '.join(session_scoped)}")
            print(
                f"Collecting most recent {DEFAULT_MAX_EVALUATION_ITEMS} relevant items across all {num_traces} traces"
            )

            # Get most recent items across all traces with relevant data
            session_otel_spans = self._get_most_recent_session_spans(trace_data, max_items=DEFAULT_MAX_EVALUATION_ITEMS)

            # Store for export (will be combined with trace_scoped spans if both present)
            if not input_spans:
                input_spans = session_otel_spans

            if session_otel_spans:
                spans_count, logs_count, genai_spans = self._count_span_types(session_otel_spans)
                print(
                    f"Sending {len(session_otel_spans)} items "
                    f"({spans_count} spans [{genai_spans} with gen_ai attrs], "
                    f"{logs_count} log events) for session-scoped evaluation"
                )

                # Evaluate with session-scoped evaluators
                eval_results = self._execute_evaluators(session_scoped, session_otel_spans, session_id)
                for result in eval_results:
                    results.add_result(result)
            else:
                print("Warning: No relevant data found for session-scoped evaluation")

        # Handle trace-scoped evaluators
        if trace_scoped:
            if session_scoped:
                print(f"\nTrace-scoped evaluators: {', '.join(trace_scoped)}")

            # Filter trace data if specific trace requested
            filtered_data = trace_data
            evaluation_target = None

            if trace_id:
                print(f"Evaluating trace {trace_id} (including previous traces for context)")
                filtered_data = self._filter_traces_up_to(trace_data, trace_id)
                filtered_trace_count = len(filtered_data.get_trace_ids())
                print(f"Including {filtered_trace_count} traces for context")

                # Set evaluation target to only evaluate the specific trace
                evaluation_target = {"traceIds": [trace_id]}

            # Get most recent spans from filtered data (default: all traces, or filtered to trace_id)
            print(f"Collecting most recent {DEFAULT_MAX_EVALUATION_ITEMS} relevant items")
            otel_spans = self._get_most_recent_session_spans(filtered_data, max_items=DEFAULT_MAX_EVALUATION_ITEMS)

            if not otel_spans:
                print("Warning: No relevant items found after filtering (no gen_ai spans or conversation logs)")

            # Store spans for export (use trace_scoped spans if available, otherwise keep session_scoped)
            input_spans = otel_spans

            # Log what we're sending
            spans_count, logs_count, genai_spans = self._count_span_types(otel_spans)
            if trace_id:
                print(
                    f"Sending {len(otel_spans)} items "
                    f"({spans_count} spans [{genai_spans} with gen_ai attrs], "
                    f"{logs_count} log events) for context, evaluating trace {trace_id}"
                )
            else:
                print(
                    f"Sending {len(otel_spans)} items "
                    f"({spans_count} spans [{genai_spans} with gen_ai attrs], "
                    f"{logs_count} log events) to evaluation API"
                )

            # Evaluate with trace-scoped evaluators
            eval_results = self._execute_evaluators(trace_scoped, otel_spans, session_id, evaluation_target)
            for result in eval_results:
                results.add_result(result)

        # Store input spans for export (if any evaluation was performed)
        if input_spans:
            results.input_data = {"spans": input_spans}

        return results
