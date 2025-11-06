"""Client for AgentCore Evaluation DataPlane API."""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from ..constants import DEFAULT_RUNTIME_SUFFIX, AttributePrefixes, OTelFields
from ..observability.client import ObservabilityClient
from ..observability.models.telemetry import TraceData
from .constants import (
    DEFAULT_MAX_EVALUATION_ITEMS,
    MAX_SPAN_IDS_IN_CONTEXT,
    SESSION_SCOPED_EVALUATORS,
)
from .models.evaluation import EvaluationRequest, EvaluationResult, EvaluationResults
from .transformer import transform_trace_data_to_otel


class EvaluationClient:
    """Client for interacting with AgentCore Evaluation DataPlane API."""

    DEFAULT_ENDPOINT = "https://gamma.us-west-2.elcapdp.genesis-primitives.aws.dev"
    DEFAULT_REGION = "us-west-2"

    def __init__(
        self, region: Optional[str] = None, endpoint_url: Optional[str] = None, boto_client: Optional[Any] = None
    ):
        """Initialize evaluation client.

        Args:
            region: AWS region (defaults to env var or us-west-2)
            endpoint_url: API endpoint URL (defaults to env var or beta endpoint)
            boto_client: Optional pre-configured boto3 client for testing
        """
        self.region = region or os.getenv("AGENTCORE_EVAL_REGION", self.DEFAULT_REGION)
        self.endpoint_url = endpoint_url or os.getenv("AGENTCORE_EVAL_ENDPOINT", self.DEFAULT_ENDPOINT)

        if boto_client:
            self.client = boto_client
        else:
            self.client = boto3.client(
                "agentcore-evaluation-dataplane", region_name="us-west-2", endpoint_url=self.endpoint_url
            )

    def _is_session_scoped_evaluator(self, evaluator: str) -> bool:
        """Check if evaluator requires session-level data across all traces.

        Args:
            evaluator: Evaluator identifier

        Returns:
            True if evaluator needs data from all traces in session
        """
        return evaluator in SESSION_SCOPED_EVALUATORS

    def _filter_relevant_items(self, otel_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter to only high-signal items for evaluation.

        Keeps only:
        - Spans with gen_ai.* attributes (LLM calls, agent operations)
        - Log events with conversation data (input/output messages)

        Args:
            otel_items: List of OTel-formatted spans and log events

        Returns:
            Filtered list of relevant items
        """
        relevant_items = []
        for item in otel_items:
            # Check if it's a span with gen_ai attributes
            if OTelFields.SPAN_ID in item and OTelFields.START_TIME in item:
                has_genai = any(
                    k.startswith(AttributePrefixes.GEN_AI) for k in item.get(OTelFields.ATTRIBUTES, {}).keys()
                )
                if has_genai:
                    relevant_items.append(item)

            # Check if it's a log event with message body
            elif OTelFields.BODY in item and OTelFields.TIME_UNIX_NANO in item:
                body = item.get(OTelFields.BODY, {})
                # Only include if body has input or output (conversation data)
                if isinstance(body, dict) and ("input" in body or "output" in body):
                    relevant_items.append(item)

        return relevant_items

    def _get_most_recent_session_spans(
        self, trace_data: TraceData, max_items: int = DEFAULT_MAX_EVALUATION_ITEMS
    ) -> List[Dict[str, Any]]:
        """Get most recent relevant items across all traces in session.

        Collects spans with gen_ai attributes and log events with conversation data,
        sorted by timestamp to get the most recent items.

        Args:
            trace_data: TraceData containing all session data
            max_items: Maximum number of items to return (default: 100)

        Returns:
            List of OTel-formatted spans and log events, most recent first
        """
        # Transform all traces (no filtering)
        all_otel_items = transform_trace_data_to_otel(trace_data, latest_trace_only=False, trace_id=None)

        if not all_otel_items:
            return []

        # Filter to only relevant items using shared helper
        relevant_items = self._filter_relevant_items(all_otel_items)

        # Sort by timestamp (most recent first)
        def get_timestamp(item):
            # Spans have startTimeUnixNano, logs have timeUnixNano
            return item.get(OTelFields.START_TIME) or item.get(OTelFields.TIME_UNIX_NANO) or 0

        relevant_items.sort(key=get_timestamp, reverse=True)

        # Return most recent max_items
        return relevant_items[:max_items]

    def _extract_span_context(
        self, spans: List[Dict[str, Any]], session_id: Optional[str] = None, trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract span context information for evaluation results.

        Args:
            spans: List of OpenTelemetry spans/logs
            session_id: Optional session ID
            trace_id: Optional trace ID

        Returns:
            Dictionary with span context metadata
        """
        context = {}

        # Add session/trace IDs if provided
        if session_id:
            context["session.id"] = session_id
        if trace_id:
            context["trace.id"] = trace_id

        # Extract unique span and trace IDs from the spans
        span_ids = []
        trace_ids = set()

        for item in spans:
            if OTelFields.SPAN_ID in item:
                span_ids.append(item[OTelFields.SPAN_ID])
            if OTelFields.TRACE_ID in item:
                trace_ids.add(item[OTelFields.TRACE_ID])

        # Add span context
        if span_ids:
            context["spanContext"] = {
                "spanIds": span_ids[:MAX_SPAN_IDS_IN_CONTEXT],  # Limit to avoid huge contexts
                "totalSpans": len(span_ids),
            }

        if trace_ids:
            context["spanContext"] = context.get("spanContext", {})
            context["spanContext"]["traceIds"] = list(trace_ids)
            context["spanContext"]["totalTraces"] = len(trace_ids)

        return context

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

    def _count_otel_items(self, items: List[Dict[str, Any]]) -> tuple:
        """Count spans, logs, and gen_ai spans in OTel items.

        Args:
            items: List of OTel-formatted spans and log events

        Returns:
            Tuple of (spans_count, logs_count, genai_spans_count)
        """
        spans_count = sum(1 for item in items if OTelFields.SPAN_ID in item and OTelFields.START_TIME in item)
        logs_count = sum(1 for item in items if OTelFields.BODY in item and OTelFields.TIME_UNIX_NANO in item)
        genai_spans = sum(
            1
            for span in items
            if OTelFields.SPAN_ID in span
            and any(k.startswith(AttributePrefixes.GEN_AI) for k in span.get(OTelFields.ATTRIBUTES, {}).keys())
        )
        return spans_count, logs_count, genai_spans

    def _execute_evaluators(
        self, evaluators: List[str], otel_spans: List[Dict[str, Any]], session_id: str, trace_id: Optional[str] = None
    ) -> List[EvaluationResult]:
        """Execute evaluators and return results.

        Args:
            evaluators: List of evaluator identifiers
            otel_spans: OTel-formatted spans/logs to evaluate
            session_id: Session ID for context
            trace_id: Optional trace ID for context

        Returns:
            List of EvaluationResult objects (including errors)
        """
        results = []

        for evaluator in evaluators:
            try:
                response = self.evaluate(otel_spans, [evaluator])
                api_results = response.get("results", [])

                if not api_results:
                    print(f"Warning: Evaluator {evaluator} returned no results")

                for api_result in api_results:
                    span_context = self._extract_span_context(otel_spans, session_id=session_id, trace_id=trace_id)
                    result = EvaluationResult.from_api_response(api_result, span_context=span_context)
                    results.append(result)

            except Exception as e:
                error_result = EvaluationResult(
                    evaluator=evaluator,
                    explanation=f"Evaluation failed: {str(e)}",
                    context={"session.id": session_id},
                    error=str(e),
                )
                results.append(error_result)

        return results

    def evaluate(self, spans: List[Dict[str, Any]], evaluators: List[str]) -> Dict[str, Any]:
        """Call evaluation API with transformed spans.

        Args:
            spans: List of OpenTelemetry-formatted spans
            evaluators: List of evaluator identifiers

        Returns:
            Raw API response

        Raises:
            ClientError: If API call fails
        """
        request = EvaluationRequest(evaluators=evaluators, spans=spans)

        try:
            response = self.client.evaluate(**request.to_dict())
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
        all_traces: bool = False,
    ) -> EvaluationResults:
        """Evaluate a session using multiple evaluators.

        Session-scoped evaluators always get all traces.
        Trace-scoped evaluators behavior depends on parameters.

        Args:
            session_id: Session ID to evaluate
            evaluators: List of evaluator identifiers
            agent_id: Agent ID for fetching session data
            region: AWS region for ObservabilityClient
            trace_id: Optional specific trace ID to evaluate (trace-scoped only)
            all_traces: If True, evaluate all traces together (trace-scoped only)

        Returns:
            EvaluationResults containing all evaluation results

        Raises:
            RuntimeError: If session data cannot be fetched or evaluation fails
            ValueError: If both trace_id and all_traces are specified
        """
        # Validate parameters
        if trace_id and all_traces:
            raise ValueError("Cannot specify both trace_id and all_traces")

        # 1. Fetch session data
        trace_data = self._fetch_session_data(session_id, agent_id, region)

        # Log session stats
        num_traces = len(trace_data.get_trace_ids())
        num_spans = len(trace_data.spans)
        print(f"Found {num_spans} spans across {num_traces} traces in session")

        # Separate session-scoped and trace-scoped evaluators
        session_scoped = [e for e in evaluators if self._is_session_scoped_evaluator(e)]
        trace_scoped = [e for e in evaluators if not self._is_session_scoped_evaluator(e)]

        results = EvaluationResults(session_id=session_id)

        # Track all input data sent to API for export
        all_input_data = {"session_scoped": None, "trace_scoped": None}

        # Handle session-scoped evaluators (need data across all traces)
        if session_scoped:
            print(f"Session-scoped evaluators: {', '.join(session_scoped)}")
            print(
                f"Collecting most recent {DEFAULT_MAX_EVALUATION_ITEMS} relevant items across all {num_traces} traces"
            )

            # Get most recent items across all traces with relevant data
            session_otel_spans = self._get_most_recent_session_spans(trace_data, max_items=DEFAULT_MAX_EVALUATION_ITEMS)

            # Store for export
            all_input_data["session_scoped"] = session_otel_spans

            if session_otel_spans:
                spans_count, logs_count, genai_spans = self._count_otel_items(session_otel_spans)
                print(
                    f"Sending {len(session_otel_spans)} items ({spans_count} spans [{genai_spans} with gen_ai attrs], {logs_count} log events) for session-scoped evaluation"
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

            # Determine which traces to evaluate based on parameters
            if all_traces:
                # Evaluate all traces together
                print(
                    f"Collecting most recent {DEFAULT_MAX_EVALUATION_ITEMS} relevant items across all {num_traces} traces for trace-scoped evaluation"
                )
                otel_spans = self._get_most_recent_session_spans(trace_data, max_items=DEFAULT_MAX_EVALUATION_ITEMS)
            elif trace_id:
                # Evaluate specific trace
                print(f"Filtering to specific trace: {trace_id}")
                otel_spans_unfiltered = transform_trace_data_to_otel(
                    trace_data, latest_trace_only=False, trace_id=trace_id
                )
                if not otel_spans_unfiltered:
                    raise RuntimeError("Failed to transform trace data to OpenTelemetry format")
                otel_spans = self._filter_relevant_items(otel_spans_unfiltered)
            else:
                # Evaluate latest trace only (default)
                otel_spans_unfiltered = transform_trace_data_to_otel(trace_data, latest_trace_only=True)
                if num_traces > 1:
                    print(f"Evaluating latest trace only (out of {num_traces} traces)")
                if not otel_spans_unfiltered:
                    raise RuntimeError("Failed to transform trace data to OpenTelemetry format")
                otel_spans = self._filter_relevant_items(otel_spans_unfiltered)

            if not otel_spans:
                print("Warning: No relevant items found after filtering (no gen_ai spans or conversation logs)")

            # Store filtered data for export
            all_input_data["trace_scoped"] = otel_spans

            # Log what we're sending
            spans_count, logs_count, genai_spans = self._count_otel_items(otel_spans)
            print(
                f"Sending {len(otel_spans)} items ({spans_count} spans [{genai_spans} with gen_ai attrs], {logs_count} log events) to evaluation API"
            )

            # Evaluate with trace-scoped evaluators
            eval_results = self._execute_evaluators(trace_scoped, otel_spans, session_id, trace_id)
            for result in eval_results:
                results.add_result(result)

        # Store input data for export
        results.input_data = all_input_data

        return results
