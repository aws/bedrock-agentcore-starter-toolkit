"""Evaluation processor - contains all business logic for evaluation operations.

Separates business logic from API client calls for better testability and reusability.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from ..constants import DEFAULT_RUNTIME_SUFFIX, InstrumentationScopes
from ..observability.client import ObservabilityClient
from ..observability.telemetry import TraceData
from .models import EvaluationResult, EvaluationResults

logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_MAX_EVALUATION_ITEMS = 1000
DEFAULT_LOOKBACK_DAYS = 7
MAX_EVALUATORS_PER_REQUEST = 20


class EvaluationProcessor:
    """Processor for evaluation business logic.

    Handles:
    - Fetching session data from CloudWatch
    - Filtering spans based on instrumentation scopes
    - Determining which spans to send based on evaluator level
    - Orchestrating evaluation flow
    """

    def __init__(self, data_plane_client, control_plane_client=None):
        """Initialize processor with API clients.

        Args:
            data_plane_client: Client for evaluation data plane API
            control_plane_client: Optional client for control plane (evaluator management)
        """
        self.data_plane_client = data_plane_client
        self.control_plane_client = control_plane_client

    def get_latest_session(self, agent_id: str, region: str) -> Optional[str]:
        """Get the latest session ID for an agent.

        Args:
            agent_id: Agent ID to query
            region: AWS region

        Returns:
            Latest session ID or None if no sessions found

        Raises:
            ValueError: If agent_id or region is invalid
        """
        # Input validation
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id is required and cannot be empty")
        if not region or not region.strip():
            raise ValueError("region is required and cannot be empty")

        try:
            # ObservabilityClient is stateless - only takes region
            obs_client = ObservabilityClient(region_name=region)

            # Query recent sessions (last 7 days)
            end_time = datetime.now()
            start_time = end_time - timedelta(days=DEFAULT_LOOKBACK_DAYS)

            # Use ObservabilityClient's built-in method to get latest session
            latest_session = obs_client.get_latest_session_id(
                start_time_ms=int(start_time.timestamp() * 1000),
                end_time_ms=int(end_time.timestamp() * 1000),
                agent_id=agent_id,  # Pass as parameter, not in constructor
            )

            return latest_session

        except (ClientError, ValueError, KeyError) as e:
            logger.warning("Failed to fetch latest session for agent %s: %s", agent_id, str(e))
            logger.debug("Stack trace for get_latest_session error:", exc_info=True)
            return None

    def fetch_session_data(
        self, session_id: str, agent_id: str, region: str, days: int = DEFAULT_LOOKBACK_DAYS
    ) -> TraceData:
        """Fetch session data from CloudWatch.

        Args:
            session_id: Session ID to fetch
            agent_id: Agent ID for filtering
            region: AWS region
            days: Number of days to look back (default: 7)

        Returns:
            TraceData with session spans and logs

        Raises:
            ValueError: If required parameters are invalid
            RuntimeError: If session data cannot be fetched
        """
        # Input validation
        if not session_id or not session_id.strip():
            raise ValueError("session_id is required and cannot be empty")
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id is required and cannot be empty")
        if not region or not region.strip():
            raise ValueError("region is required and cannot be empty")

        # ObservabilityClient is stateless - only takes region
        obs_client = ObservabilityClient(region_name=region)

        # Configurable lookback
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        try:
            # Query spans for the session
            spans = obs_client.query_spans_by_session(
                session_id=session_id, start_time_ms=start_time_ms, end_time_ms=end_time_ms, agent_id=agent_id
            )

            if not spans:
                raise RuntimeError(f"No spans found for session {session_id}")

            # Get unique trace IDs from spans
            trace_ids = list(set(span.trace_id for span in spans if span.trace_id))

            # Query runtime logs for all traces
            runtime_logs = obs_client.query_runtime_logs_by_traces(
                trace_ids=trace_ids,
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                agent_id=agent_id,
                endpoint_name=DEFAULT_RUNTIME_SUFFIX,
            )

            # Build TraceData object
            trace_data = TraceData(session_id=session_id, agent_id=agent_id, spans=spans, runtime_logs=runtime_logs)

            return trace_data

        except (ClientError, ValueError, KeyError, TypeError) as e:
            raise RuntimeError(f"Failed to fetch session data: {e}") from e

    def extract_raw_spans(self, trace_data: TraceData) -> List[Dict[str, Any]]:
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

    def filter_relevant_spans(self, raw_spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter to only high-signal spans for evaluation.

        Keeps only:
        - Spans from known instrumentation scopes (LangChain, Strands)
        - Log events with conversation data (input/output messages)

        Args:
            raw_spans: List of raw span/log documents

        Returns:
            Filtered list of relevant spans
        """
        relevant_spans = []
        allowed_scopes = {
            InstrumentationScopes.OTEL_LANGCHAIN,
            InstrumentationScopes.OPENINFERENCE_LANGCHAIN,
            InstrumentationScopes.STRANDS,
        }

        for span_doc in raw_spans:
            # Check if span has a scope from allowed instrumentation sources
            scope = span_doc.get("scope", {})
            scope_name = scope.get("name", "") if isinstance(scope, dict) else ""

            if scope_name in allowed_scopes:
                relevant_spans.append(span_doc)
                continue

            # Check if it's a log with conversation data
            body = span_doc.get("body", {})
            if isinstance(body, dict) and ("input" in body or "output" in body):
                relevant_spans.append(span_doc)

        return relevant_spans

    def filter_traces_up_to(self, trace_data: TraceData, target_trace_id: str) -> TraceData:
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

    def get_most_recent_spans(
        self, trace_data: TraceData, max_items: int = DEFAULT_MAX_EVALUATION_ITEMS
    ) -> List[Dict[str, Any]]:
        """Get most recent relevant spans across all traces in session.

        Collects spans from known instrumentation scopes and log events with conversation data,
        sorted by timestamp to get the most recent items.

        Args:
            trace_data: TraceData containing all session data
            max_items: Maximum number of items to return

        Returns:
            List of raw span documents, most recent first
        """
        # Extract raw spans from all traces
        raw_spans = self.extract_raw_spans(trace_data)

        if not raw_spans:
            return []

        # Filter to only relevant spans
        relevant_spans = self.filter_relevant_spans(raw_spans)

        # Sort by timestamp (most recent first)
        def get_timestamp(span_doc):
            # Spans have startTimeUnixNano, logs have timeUnixNano
            return span_doc.get("startTimeUnixNano") or span_doc.get("timeUnixNano") or 0

        relevant_spans.sort(key=get_timestamp, reverse=True)

        # Return most recent max_items
        return relevant_spans[:max_items]

    def count_span_types(self, raw_spans: List[Dict[str, Any]]) -> tuple:
        """Count spans, logs, and scoped spans.

        Args:
            raw_spans: List of raw span documents

        Returns:
            Tuple of (spans_count, logs_count, scoped_spans_count)
        """
        allowed_scopes = {
            InstrumentationScopes.OTEL_LANGCHAIN,
            InstrumentationScopes.OPENINFERENCE_LANGCHAIN,
            InstrumentationScopes.STRANDS,
        }

        spans_count = sum(1 for item in raw_spans if "spanId" in item and "startTimeUnixNano" in item)
        logs_count = sum(1 for item in raw_spans if "body" in item and "timeUnixNano" in item)
        scoped_spans = sum(
            1 for span in raw_spans if "spanId" in span and span.get("scope", {}).get("name", "") in allowed_scopes
        )
        return spans_count, logs_count, scoped_spans

    def determine_spans_for_evaluator(
        self,
        evaluator_level: str,
        trace_data: TraceData,
        trace_id: Optional[str] = None,
        max_items: int = DEFAULT_MAX_EVALUATION_ITEMS,
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Determine which spans to send based on evaluator level.

        Args:
            evaluator_level: "SESSION" or "TRACE"
            trace_data: Full session data
            trace_id: Optional specific trace to evaluate
            max_items: Maximum items to return

        Returns:
            Tuple of (spans_to_send, evaluation_target)
            - spans_to_send: OTel spans for context
            - evaluation_target: Optional dict specifying what to evaluate
        """
        if evaluator_level == "SESSION":
            # Session-level: send most recent spans across all traces
            spans = self.get_most_recent_spans(trace_data, max_items=max_items)
            return spans, None

        elif evaluator_level == "TRACE":
            # Trace-level: send target trace + previous traces for context
            if trace_id:
                filtered_data = self.filter_traces_up_to(trace_data, trace_id)
                spans = self.get_most_recent_spans(filtered_data, max_items=max_items)
                evaluation_target = {"traceIds": [trace_id]}
                return spans, evaluation_target
            else:
                # No specific trace, evaluate all traces
                spans = self.get_most_recent_spans(trace_data, max_items=max_items)
                return spans, None
        else:
            raise ValueError(f"Unknown evaluator level: {evaluator_level}")

    def execute_evaluators(
        self,
        evaluators: List[str],
        otel_spans: List[Dict[str, Any]],
        session_id: str,
        evaluation_target: Optional[Dict[str, Any]] = None,
    ) -> List[EvaluationResult]:
        """Execute evaluators and return results.

        Calls data plane API once per evaluator.

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
                response = self.data_plane_client.evaluate(
                    evaluator_id=evaluator, session_spans=otel_spans, evaluation_target=evaluation_target
                )

                # API returns {evaluationResults: [...]}
                api_results = response.get("evaluationResults", [])

                if not api_results:
                    logger.warning("Evaluator %s returned no results", evaluator)

                for api_result in api_results:
                    result = EvaluationResult.from_api_response(api_result)
                    results.append(result)

            except (RuntimeError, ClientError, KeyError, ValueError, TypeError) as e:
                # Create error result for API failures and data processing errors
                logger.warning("Evaluator %s failed: %s", evaluator, str(e))
                error_result = EvaluationResult(
                    evaluator_id=evaluator,
                    evaluator_name=evaluator,
                    evaluator_arn="",
                    explanation=f"Evaluation failed: {str(e)}",
                    context={"spanContext": {"sessionId": session_id}},
                    error=str(e),
                )
                results.append(error_result)

        return results

    def evaluate_session(
        self,
        session_id: str,
        evaluators: List[str],
        agent_id: str,
        region: str,
        trace_id: Optional[str] = None,
        days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> EvaluationResults:
        """Evaluate a session using multiple evaluators.

        This is the main orchestration method that:
        1. Fetches session data
        2. Groups evaluators by level (if control plane client available)
        3. Determines spans needed for each level
        4. Executes evaluators
        5. Returns results

        Args:
            session_id: Session ID to evaluate
            evaluators: List of evaluator identifiers
            agent_id: Agent ID for fetching session data
            region: AWS region
            trace_id: Optional trace ID to evaluate
            days: Number of days to look back for session data (default: 7)

        Returns:
            EvaluationResults containing all evaluation results

        Raises:
            ValueError: If required parameters are invalid
            RuntimeError: If session data cannot be fetched or evaluation fails
        """
        # Input validation
        if not evaluators or not isinstance(evaluators, list):
            raise ValueError("evaluators must be a non-empty list")

        if len(evaluators) > MAX_EVALUATORS_PER_REQUEST:
            raise ValueError(
                f"Too many evaluators: {len(evaluators)}. Maximum allowed is {MAX_EVALUATORS_PER_REQUEST} per request."
            )

        # 1. Fetch session data (validates session_id, agent_id, region internally)
        trace_data = self.fetch_session_data(session_id, agent_id, region, days)

        # Removed verbose session stats logging

        results = EvaluationResults(session_id=session_id, trace_id=trace_id)
        input_spans = []

        # 2. Group evaluators by level (if control plane available)
        if self.control_plane_client:
            # TODO: Fetch evaluator details to get levels
            # For now, use default behavior
            evaluators_by_level = self._group_evaluators_by_level(evaluators)
        else:
            # Default: treat all as TRACE level
            evaluators_by_level = {"TRACE": evaluators}

        # 3. Process each level
        for level, eval_list in evaluators_by_level.items():
            if not eval_list:
                continue

            # Removed verbose logging: print(f"{level}-level evaluators: {', '.join(eval_list)}")

            # Determine spans for this level
            otel_spans, evaluation_target = self.determine_spans_for_evaluator(
                evaluator_level=level, trace_data=trace_data, trace_id=trace_id, max_items=DEFAULT_MAX_EVALUATION_ITEMS
            )

            if not otel_spans:
                # Removed verbose logging: print(f"Warning: No relevant items found for {level}-level evaluation")
                continue

            # Removed verbose logging about what we're sending
            # spans_count, logs_count, scoped_spans = self.count_span_types(otel_spans)

            # Store spans for export
            if not input_spans:
                input_spans = otel_spans

            # Execute evaluators
            eval_results = self.execute_evaluators(eval_list, otel_spans, session_id, evaluation_target)
            for result in eval_results:
                results.add_result(result)

        # Store input spans for export
        if input_spans:
            results.input_data = {"spans": input_spans}

        return results

    def _group_evaluators_by_level(self, evaluators: List[str]) -> Dict[str, List[str]]:
        """Group evaluators by their level (SESSION or TRACE).

        Note: TOOL_CALL and other levels are treated as TRACE for evaluation purposes.

        Args:
            evaluators: List of evaluator IDs

        Returns:
            Dict mapping level to list of evaluator IDs (SESSION or TRACE)
        """
        grouped = {"SESSION": [], "TRACE": []}

        for evaluator_id in evaluators:
            try:
                # Fetch evaluator details
                details = self.control_plane_client.get_evaluator(evaluator_id)
                level = details.get("level", "TRACE")

                # Map levels to SESSION or TRACE
                # TOOL_CALL and any other levels default to TRACE
                if level == "SESSION":
                    grouped["SESSION"].append(evaluator_id)
                else:
                    # TRACE, TOOL_CALL, or any other level -> TRACE
                    grouped["TRACE"].append(evaluator_id)
            except (ClientError, RuntimeError, KeyError, ValueError) as e:
                # Default to TRACE if we can't fetch evaluator details
                logger.debug("Could not fetch level for evaluator %s: %s - defaulting to TRACE", evaluator_id, e)
                grouped["TRACE"].append(evaluator_id)

        return grouped
