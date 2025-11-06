"""Client for querying observability data from CloudWatch Logs."""

import logging
import time
from typing import Dict, List

import boto3

from .models.telemetry import RuntimeLog, Span, TraceData
from .query_builder import CloudWatchQueryBuilder


class ObservabilityClient:
    """Client for querying spans, traces, and runtime logs from CloudWatch Logs."""

    SPANS_LOG_GROUP = "aws/spans"
    QUERY_TIMEOUT_SECONDS = 60
    POLL_INTERVAL_SECONDS = 2

    def __init__(
        self,
        region_name: str,
        agent_id: str,
        runtime_suffix: str = "DEFAULT",
    ):
        """Initialize the ObservabilityClient.

        Args:
            region_name: AWS region name
            agent_id: Agent ID for querying agent-specific logs
            runtime_suffix: Runtime suffix for log group (default: DEFAULT)
        """
        self.region = region_name
        self.agent_id = agent_id
        self.runtime_suffix = runtime_suffix
        self.runtime_log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-{runtime_suffix}"

        self.logs_client = boto3.client("logs", region_name=region_name)
        self.query_builder = CloudWatchQueryBuilder()

        # Initialize the logger
        self.logger = logging.getLogger("bedrock_agentcore.observability")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def query_spans_by_session(
        self,
        session_id: str,
        start_time_ms: int,
        end_time_ms: int,
    ) -> List[Span]:
        """Query all spans for a session from aws/spans log group.

        Args:
            session_id: The session ID to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            List of Span objects
        """
        self.logger.info("Querying spans for session: %s (agent: %s)", session_id, self.agent_id)

        # Pass agent_id to prevent cross-agent session ID collisions
        query_string = self.query_builder.build_spans_by_session_query(session_id, agent_id=self.agent_id)

        results = self._execute_cloudwatch_query(
            query_string=query_string,
            log_group_name=self.SPANS_LOG_GROUP,
            start_time=start_time_ms,
            end_time=end_time_ms,
        )

        spans = [Span.from_cloudwatch_result(result) for result in results]
        self.logger.info("Found %d spans for session %s", len(spans), session_id)

        return spans

    def query_spans_by_trace(
        self,
        trace_id: str,
        start_time_ms: int,
        end_time_ms: int,
    ) -> List[Span]:
        """Query all spans for a trace from aws/spans log group.

        Args:
            trace_id: The trace ID to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            List of Span objects
        """
        self.logger.info("Querying spans for trace: %s", trace_id)

        query_string = self.query_builder.build_spans_by_trace_query(trace_id)

        results = self._execute_cloudwatch_query(
            query_string=query_string,
            log_group_name=self.SPANS_LOG_GROUP,
            start_time=start_time_ms,
            end_time=end_time_ms,
        )

        spans = [Span.from_cloudwatch_result(result) for result in results]
        self.logger.info("Found %d spans for trace %s", len(spans), trace_id)

        return spans

    def query_runtime_logs_by_traces(
        self,
        trace_ids: List[str],
        start_time_ms: int,
        end_time_ms: int,
    ) -> List[RuntimeLog]:
        """Query runtime logs for multiple traces from agent-specific log group.

        Optimized to use a single batch query instead of one query per trace.

        Args:
            trace_ids: List of trace IDs to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            List of RuntimeLog objects
        """
        if not trace_ids:
            return []

        self.logger.info("Querying runtime logs for %d traces (single batch query)", len(trace_ids))

        # Use optimized batch query instead of looping
        query_string = self.query_builder.build_runtime_logs_by_traces_batch(trace_ids)

        try:
            results = self._execute_cloudwatch_query(
                query_string=query_string,
                log_group_name=self.runtime_log_group,
                start_time=start_time_ms,
                end_time=end_time_ms,
            )

            logs = [RuntimeLog.from_cloudwatch_result(result) for result in results]
            self.logger.info("Found total %d runtime logs across %d traces", len(logs), len(trace_ids))
            return logs

        except Exception as e:
            self.logger.error("Failed to query runtime logs in batch: %s", str(e))
            # Fall back to individual queries if batch fails
            self.logger.info("Falling back to individual queries per trace")
            return self._query_runtime_logs_individually(trace_ids, start_time_ms, end_time_ms)

    def _query_runtime_logs_individually(
        self,
        trace_ids: List[str],
        start_time_ms: int,
        end_time_ms: int,
    ) -> List[RuntimeLog]:
        """Fallback method to query runtime logs one trace at a time.

        Args:
            trace_ids: List of trace IDs to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            List of RuntimeLog objects
        """
        all_logs = []
        for trace_id in trace_ids:
            query_string = self.query_builder.build_runtime_logs_by_trace_direct(trace_id)

            try:
                results = self._execute_cloudwatch_query(
                    query_string=query_string,
                    log_group_name=self.runtime_log_group,
                    start_time=start_time_ms,
                    end_time=end_time_ms,
                )

                logs = [RuntimeLog.from_cloudwatch_result(result) for result in results]
                all_logs.extend(logs)
                self.logger.debug("Found %d runtime logs for trace %s", len(logs), trace_id)
            except Exception as e:
                self.logger.warning("Failed to query runtime logs for trace %s: %s", trace_id, str(e))
                # Continue with other traces even if one fails

        self.logger.info("Found total %d runtime logs via fallback", len(all_logs))
        return all_logs

    def get_latest_session_id(
        self,
        start_time_ms: int,
        end_time_ms: int,
    ) -> str | None:
        """Find the most recent session ID for this agent.

        Args:
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            Session ID or None if no sessions found
        """
        self.logger.info("Finding latest session for agent: %s", self.agent_id)

        query_string = self.query_builder.build_latest_session_query(self.agent_id)

        try:
            results = self._execute_cloudwatch_query(
                query_string=query_string,
                log_group_name=self.SPANS_LOG_GROUP,
                start_time=start_time_ms,
                end_time=end_time_ms,
            )

            if not results:
                self.logger.info("No sessions found for agent %s", self.agent_id)
                return None

            # Extract session ID from first result
            # Results are list of field dicts: [{"field": "attributes.session.id", "value": "session-123"}, ...]
            first_result = results[0]
            for field in first_result:
                field_name = field.get("field")
                # CloudWatch returns the field name as used in the query
                if field_name == "attributes.session.id":
                    session_id = field.get("value")
                    self.logger.info("Found latest session: %s", session_id)
                    return session_id

            self.logger.warning("No session ID field found in query results")
            return None

        except Exception as e:
            self.logger.error("Failed to query latest session: %s", str(e))
            return None

    def get_session_data(
        self,
        session_id: str,
        start_time_ms: int,
        end_time_ms: int,
        include_runtime_logs: bool = True,
    ) -> TraceData:
        """Get complete session data including spans and optionally runtime logs.

        Note: This method is primarily used by evaluation functionality.

        Args:
            session_id: The session ID to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch
            include_runtime_logs: Whether to fetch runtime logs (default: True)

        Returns:
            TraceData object with spans and runtime logs
        """
        self.logger.info("Fetching session data for: %s", session_id)

        # Query spans first
        spans = self.query_spans_by_session(session_id, start_time_ms, end_time_ms)

        # Create session data
        session_data = TraceData(
            session_id=session_id,
            agent_id=self.agent_id,
            spans=spans,
            start_time=start_time_ms,
            end_time=end_time_ms,
        )

        # Group spans by trace
        session_data.group_spans_by_trace()

        # Query runtime logs if requested
        if include_runtime_logs:
            trace_ids = session_data.get_trace_ids()
            if trace_ids:
                runtime_logs = self.query_runtime_logs_by_traces(trace_ids, start_time_ms, end_time_ms)
                session_data.runtime_logs = runtime_logs

        self.logger.info(
            "Session data retrieved: %d spans, %d traces, %d runtime logs",
            len(session_data.spans),
            len(session_data.traces),
            len(session_data.runtime_logs),
        )

        return session_data

    def get_session_summary(
        self,
        session_id: str,
        start_time_ms: int,
        end_time_ms: int,
    ) -> Dict:
        """Get session summary statistics.

        Note: This method is primarily used by evaluation functionality.

        Args:
            session_id: The session ID to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch

        Returns:
            Dictionary with session statistics
        """
        self.logger.info("Fetching session summary for: %s (agent: %s)", session_id, self.agent_id)

        # Pass agent_id to prevent cross-agent session ID collisions
        query_string = self.query_builder.build_session_summary_query(session_id, agent_id=self.agent_id)

        results = self._execute_cloudwatch_query(
            query_string=query_string,
            log_group_name=self.SPANS_LOG_GROUP,
            start_time=start_time_ms,
            end_time=end_time_ms,
        )

        if not results:
            return {
                "session_id": session_id,
                "span_count": 0,
                "trace_count": 0,
                "total_duration_ms": 0,
                "error_count": 0,
            }

        # Parse the statistics result
        result = results[0]
        summary = {"session_id": session_id}

        # CloudWatch returns a list of field objects directly
        fields = result if isinstance(result, list) else result.get("fields", [])

        for field in fields:
            field_name = field.get("field", "")
            field_value = field.get("value")
            if field_name and field_value is not None:
                summary[field_name] = field_value

        return summary

    def _execute_cloudwatch_query(
        self,
        query_string: str,
        log_group_name: str,
        start_time: int,
        end_time: int,
    ) -> List[Dict]:
        """Execute a CloudWatch Logs Insights query and wait for results.

        Args:
            query_string: The CloudWatch Logs Insights query
            log_group_name: The log group to query
            start_time: Start time in milliseconds since epoch
            end_time: End time in milliseconds since epoch

        Returns:
            List of result dictionaries

        Raises:
            TimeoutError: If query doesn't complete within timeout
            Exception: If query fails
        """
        self.logger.debug("Starting CloudWatch query on log group: %s", log_group_name)
        self.logger.debug("Query: %s", query_string)

        # Start the query
        try:
            response = self.logs_client.start_query(
                logGroupName=log_group_name,
                startTime=start_time // 1000,  # Convert to seconds
                endTime=end_time // 1000,  # Convert to seconds
                queryString=query_string,
            )
        except self.logs_client.exceptions.ResourceNotFoundException as e:
            self.logger.error("Log group not found: %s", log_group_name)
            raise Exception(f"Log group not found: {log_group_name}") from e

        query_id = response["queryId"]
        self.logger.debug("Query started with ID: %s", query_id)

        # Poll for results
        start_poll_time = time.time()
        while True:
            elapsed = time.time() - start_poll_time
            if elapsed > self.QUERY_TIMEOUT_SECONDS:
                raise TimeoutError(f"Query {query_id} timed out after {self.QUERY_TIMEOUT_SECONDS} seconds")

            result = self.logs_client.get_query_results(queryId=query_id)
            status = result["status"]

            if status == "Complete":
                results = result.get("results", [])
                self.logger.debug("Query completed with %d results", len(results))
                return results
            elif status == "Failed" or status == "Cancelled":
                raise Exception(f"Query {query_id} failed with status: {status}")

            # Still running, wait before next poll
            time.sleep(self.POLL_INTERVAL_SECONDS)
