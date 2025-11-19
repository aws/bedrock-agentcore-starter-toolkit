"""CloudWatch Logs Insights query builder for observability queries."""


class CloudWatchQueryBuilder:
    """Builder for CloudWatch Logs Insights queries for spans, traces, and runtime logs."""

    @staticmethod
    def build_spans_by_session_query(session_id: str, agent_id: str) -> str:
        """Build query to get all spans for a session from aws/spans log group.

        Args:
            session_id: The session ID to filter by
            agent_id: Agent ID to filter by (required to prevent cross-agent session collisions)

        Returns:
            CloudWatch Logs Insights query string
        """
        return f"""fields @timestamp,
               @message,
               traceId,
               spanId,
               name as spanName,
               kind,
               status.code as statusCode,
               status.message as statusMessage,
               durationNano/1000000 as durationMs,
               attributes.session.id as sessionId,
               startTimeUnixNano,
               endTimeUnixNano,
               parentSpanId,
               events,
               resource.attributes.service.name as serviceName,
               resource.attributes.cloud.resource_id as resourceId,
               attributes.aws.remote.service as serviceType
        | filter attributes.session.id = '{session_id}'
        | parse resource.attributes.cloud.resource_id \"runtime/*/\" as parsedAgentId
        | filter parsedAgentId = '{agent_id}'
        | sort startTimeUnixNano asc"""

    @staticmethod
    def build_spans_by_trace_query(trace_id: str) -> str:
        """Build query to get all spans for a trace from aws/spans log group.

        Args:
            trace_id: The trace ID to filter by

        Returns:
            CloudWatch Logs Insights query string
        """
        return f"""fields @timestamp,
               @message,
               traceId,
               spanId,
               name as spanName,
               kind,
               status.code as statusCode,
               status.message as statusMessage,
               durationNano/1000000 as durationMs,
               attributes.session.id as sessionId,
               startTimeUnixNano,
               endTimeUnixNano,
               parentSpanId,
               events,
               resource.attributes.service.name as serviceName
        | filter traceId = '{trace_id}'
        | sort startTimeUnixNano asc"""

    @staticmethod
    def build_runtime_logs_by_trace_direct(trace_id: str) -> str:
        """Build query to get runtime logs for a trace (for direct log group query).

        Args:
            trace_id: The trace ID to filter by

        Returns:
            CloudWatch Logs Insights query string
        """
        return f"""fields @timestamp, @message, spanId, traceId, @logStream
        | filter traceId = '{trace_id}'
        | sort @timestamp asc"""

    @staticmethod
    def build_runtime_logs_by_traces_batch(trace_ids: list[str]) -> str:
        """Build optimized query to get runtime logs for multiple traces in one query.

        Args:
            trace_ids: List of trace IDs to filter by

        Returns:
            CloudWatch Logs Insights query string
        """
        if not trace_ids:
            return ""

        # Use IN clause for efficient batch filtering
        trace_ids_quoted = ", ".join([f"'{tid}'" for tid in trace_ids])

        return f"""fields @timestamp, @message, spanId, traceId, @logStream
        | filter traceId in [{trace_ids_quoted}]
        | sort @timestamp asc"""

    @staticmethod
    def build_latest_session_query(agent_id: str, limit: int = 1) -> str:
        """Build query to find the most recent session ID(s) for an agent.

        Args:
            agent_id: The agent ID to find sessions for
            limit: Number of recent sessions to return (default: 1)

        Returns:
            CloudWatch Logs Insights query string
        """
        # Filter for vended agent spans only
        base_filter = 'resource.attributes.aws.service.type = "gen_ai_agent"'

        # Parse and filter by agent ID (matches dashboard pattern)
        return f"""filter {base_filter}
| parse resource.attributes.cloud.resource_id "runtime/*/" as parsedAgentId
| filter parsedAgentId = '{agent_id}'
| stats max(endTimeUnixNano) as maxEnd by attributes.session.id
| sort maxEnd desc
| limit {limit}"""

    @staticmethod
    def build_session_summary_query(session_id: str, agent_id: str | None = None) -> str:
        """Build query to get session summary statistics.

        Note: This query is primarily used by evaluation functionality.

        Args:
            session_id: The session ID to get summary for
            agent_id: Optional agent ID to filter by (prevents cross-agent session collisions)

        Returns:
            CloudWatch Logs Insights query string
        """
        # Base filter by session ID
        base_filter = f"attributes.session.id = '{session_id}'"

        # Build parse and agent filter clauses if agent_id provided
        if agent_id:
            # Parse agent ID from resourceId ARN, then filter by it (matches dashboard pattern)
            parse_and_filter = f"""| parse resource.attributes.cloud.resource_id "runtime/*/" as parsedAgentId
        | filter parsedAgentId = '{agent_id}'"""
        else:
            parse_and_filter = ""

        return f"""fields traceId,
               resource.attributes.service.name as serviceName,
               attributes.session.id as sessionId,
               name as spanName,
               durationNano/1000000 as durationMs,
               status.code as statusCode,
               attributes.http.response.status_code as httpStatusCode
        | filter {base_filter}
        {parse_and_filter}
        | stats count(spanId) as spanCount,
                count_distinct(traceId) as traceCount,
                sum(durationMs) as totalDurationMs,
                sum(status.code = 'ERROR' or httpStatusCode >= 400) as errorCount,
                sum(httpStatusCode >= 500 or (status.code = 'ERROR' and not ispresent(httpStatusCode))) as systemErrors,
                sum(httpStatusCode >= 400 and httpStatusCode < 500) as clientErrors,
                sum(httpStatusCode = 429) as throttles,
                min(startTimeUnixNano) as sessionStart,
                max(endTimeUnixNano) as sessionEnd
          by sessionId"""
