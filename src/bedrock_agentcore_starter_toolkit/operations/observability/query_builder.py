"""CloudWatch Logs Insights query builder for observability queries."""


class CloudWatchQueryBuilder:
    """Builder for CloudWatch Logs Insights queries for spans, traces, and runtime logs."""

    @staticmethod
    def build_spans_by_session_query(session_id: str) -> str:
        """Build query to get all spans for a session from aws/spans log group.

        Args:
            session_id: The session ID to filter by

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
    def build_session_summary_query(session_id: str) -> str:
        """Build query to get session summary statistics.

        Note: This query is primarily used by evaluation functionality.

        Args:
            session_id: The session ID to get summary for

        Returns:
            CloudWatch Logs Insights query string
        """
        return f"""fields traceId,
               resource.attributes.service.name as serviceName,
               attributes.session.id as sessionId,
               name as spanName,
               durationNano/1000000 as durationMs,
               status.code as statusCode
        | filter attributes.session.id = '{session_id}'
        | stats count(spanId) as spanCount,
                count_distinct(traceId) as traceCount,
                sum(durationMs) as totalDurationMs,
                sum(status.code = 'ERROR') as errorCount,
                min(startTimeUnixNano) as sessionStart,
                max(endTimeUnixNano) as sessionEnd
          by sessionId"""
