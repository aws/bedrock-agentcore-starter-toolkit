"""Client for querying observability data from CloudWatch Logs."""

import logging
import time
from typing import Dict, List, Optional

import boto3

from .builders import CloudWatchResultBuilder
from .query_builder import CloudWatchQueryBuilder
from .telemetry import RuntimeLog, Span


class ObservabilityClient:
    """Stateless client for querying spans, traces, and runtime logs from CloudWatch Logs.

    All operations require agent_id and runtime_suffix as parameters, making the client
    reusable across multiple agents without maintaining state.
    """

    SPANS_LOG_GROUP = "aws/spans"
    QUERY_TIMEOUT_SECONDS = 60
    POLL_INTERVAL_SECONDS = 2

    def __init__(self, region_name: str):
        """Initialize the stateless ObservabilityClient.

        Args:
            region_name: AWS region name
        """
        self.region = region_name
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
        agent_id: str,
    ) -> List[Span]:
        """Query all spans for a session from aws/spans log group.

        Args:
            session_id: The session ID to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch
            agent_id: Agent ID to filter results (required to prevent cross-agent collisions)

        Returns:
            List of Span objects
        """
        self.logger.debug("Querying spans for session: %s (agent: %s)", session_id, agent_id)

        # Pass agent_id to prevent cross-agent session ID collisions
        query_string = self.query_builder.build_spans_by_session_query(session_id, agent_id=agent_id)

        results = self._execute_cloudwatch_query(
            query_string=query_string,
            log_group_name=self.SPANS_LOG_GROUP,
            start_time=start_time_ms,
            end_time=end_time_ms,
        )

        spans = [CloudWatchResultBuilder.build_span(result) for result in results]
        self.logger.debug("Found %d spans for session %s", len(spans), session_id)

        return spans

    def query_spans_by_trace(
        self,
        trace_id: str,
        start_time_ms: int,
        end_time_ms: int,
        agent_id: str,
    ) -> List[Span]:
        """Query all spans for a trace from aws/spans log group.

        Args:
            trace_id: The trace ID to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch
            agent_id: Agent ID to filter results (required to prevent cross-agent access)

        Returns:
            List of Span objects
        """
        self.logger.debug("Querying spans for trace: %s (agent: %s)", trace_id, agent_id)

        # Note: Trace IDs are globally unique, so no agent_id filter needed in query
        query_string = self.query_builder.build_spans_by_trace_query(trace_id)

        results = self._execute_cloudwatch_query(
            query_string=query_string,
            log_group_name=self.SPANS_LOG_GROUP,
            start_time=start_time_ms,
            end_time=end_time_ms,
        )

        spans = [CloudWatchResultBuilder.build_span(result) for result in results]
        self.logger.debug("Found %d spans for trace %s", len(spans), trace_id)

        return spans

    def query_runtime_logs_by_traces(
        self,
        trace_ids: List[str],
        start_time_ms: int,
        end_time_ms: int,
        agent_id: str,
        endpoint_name: str = "DEFAULT",
    ) -> List[RuntimeLog]:
        """Query runtime logs for multiple traces from agent-specific log group.

        Optimized to use a single batch query instead of one query per trace.

        Args:
            trace_ids: List of trace IDs to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch
            agent_id: Agent ID for constructing the log group name
            endpoint_name: Runtime endpoint name for log group (default: DEFAULT)

        Returns:
            List of RuntimeLog objects
        """
        if not trace_ids:
            return []

        runtime_log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name}"

        self.logger.debug(
            "Querying runtime logs for %d traces from %s (single batch query)", len(trace_ids), runtime_log_group
        )

        # Use optimized batch query instead of looping
        query_string = self.query_builder.build_runtime_logs_by_traces_batch(trace_ids)

        try:
            results = self._execute_cloudwatch_query(
                query_string=query_string,
                log_group_name=runtime_log_group,
                start_time=start_time_ms,
                end_time=end_time_ms,
            )

            logs = [CloudWatchResultBuilder.build_runtime_log(result) for result in results]
            self.logger.debug("Found total %d runtime logs across %d traces", len(logs), len(trace_ids))
            return logs

        except Exception as e:
            self.logger.error("Failed to query runtime logs in batch: %s", str(e))
            # Fall back to individual queries if batch fails
            self.logger.info("Falling back to individual queries per trace")
            return self._query_runtime_logs_individually(trace_ids, start_time_ms, end_time_ms, agent_id, endpoint_name)

    def _query_runtime_logs_individually(
        self,
        trace_ids: List[str],
        start_time_ms: int,
        end_time_ms: int,
        agent_id: str,
        endpoint_name: str = "DEFAULT",
    ) -> List[RuntimeLog]:
        """Fallback method to query runtime logs one trace at a time.

        Args:
            trace_ids: List of trace IDs to query
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch
            agent_id: Agent ID for constructing the log group name
            endpoint_name: Runtime endpoint name for log group (default: DEFAULT)

        Returns:
            List of RuntimeLog objects
        """
        runtime_log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name}"
        all_logs = []

        for trace_id in trace_ids:
            query_string = self.query_builder.build_runtime_logs_by_trace_direct(trace_id)

            try:
                results = self._execute_cloudwatch_query(
                    query_string=query_string,
                    log_group_name=runtime_log_group,
                    start_time=start_time_ms,
                    end_time=end_time_ms,
                )

                logs = [CloudWatchResultBuilder.build_runtime_log(result) for result in results]
                all_logs.extend(logs)

            except Exception as e:
                self.logger.warning("Failed to query runtime logs for trace %s: %s", trace_id, str(e))
                continue

        self.logger.info(
            "Found total %d runtime logs across %d traces (individual queries)", len(all_logs), len(trace_ids)
        )
        return all_logs

    def get_latest_session_id(
        self,
        start_time_ms: int,
        end_time_ms: int,
        agent_id: str,
    ) -> Optional[str]:
        """Get the most recent session ID for an agent.

        Args:
            start_time_ms: Start time in milliseconds since epoch
            end_time_ms: End time in milliseconds since epoch
            agent_id: Agent ID to query for

        Returns:
            Latest session ID or None if no sessions found
        """
        self.logger.info("Fetching latest session ID for agent: %s", agent_id)

        query_string = self.query_builder.build_latest_session_query(agent_id, limit=1)

        results = self._execute_cloudwatch_query(
            query_string=query_string,
            log_group_name=self.SPANS_LOG_GROUP,
            start_time=start_time_ms,
            end_time=end_time_ms,
        )

        if not results or not results[0]:
            self.logger.info("No sessions found for agent %s", agent_id)
            return None

        # Extract session ID from first result
        session_id = None
        for field in results[0]:
            if field.get("field") == "attributes.session.id":
                session_id = field.get("value")
                break

        if session_id:
            self.logger.info("Found latest session: %s", session_id)
        else:
            self.logger.info("No session ID found in results")

        return session_id

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

            time.sleep(self.POLL_INTERVAL_SECONDS)
