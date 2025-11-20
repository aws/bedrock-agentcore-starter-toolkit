"""Tests for CloudWatchQueryBuilder."""

from bedrock_agentcore_starter_toolkit.operations.observability.query_builder import CloudWatchQueryBuilder


class TestSpansQueries:
    """Test query builders for spans."""

    def test_build_spans_by_session_query_basic(self):
        """Test building spans query with session ID only."""
        session_id = "test-session-123"
        agent_id = "test-agent-123"
        query = CloudWatchQueryBuilder.build_spans_by_session_query(session_id, agent_id)

        # Should contain required fields
        assert "fields @timestamp" in query
        assert "traceId" in query
        assert "spanId" in query
        assert "name as spanName" in query

        # Should filter by session ID
        assert f"attributes.session.id = '{session_id}'" in query

        # Should sort by start time
        assert "sort startTimeUnixNano asc" in query

        # Should have agent ID filter
        assert "parsedAgentId" in query
        assert f"parsedAgentId = '{agent_id}'" in query

    def test_build_spans_by_session_query_with_agent_id(self):
        """Test building spans query with both session ID and agent ID."""
        session_id = "test-session-456"
        agent_id = "agent-abc123"
        query = CloudWatchQueryBuilder.build_spans_by_session_query(session_id, agent_id)

        # Should contain session filter
        assert f"attributes.session.id = '{session_id}'" in query

        # Should parse and filter by agent ID
        assert "parse resource.attributes.cloud.resource_id" in query
        assert f"parsedAgentId = '{agent_id}'" in query

        # Should contain required fields
        assert "traceId" in query
        assert "spanId" in query

    def test_build_spans_by_trace_query(self):
        """Test building spans query by trace ID."""
        trace_id = "trace-xyz789"
        query = CloudWatchQueryBuilder.build_spans_by_trace_query(trace_id)

        # Should contain required fields
        assert "fields @timestamp" in query
        assert "traceId" in query
        assert "spanId" in query
        assert "name as spanName" in query
        assert "durationNano/1000000 as durationMs" in query

        # Should filter by trace ID
        assert f"traceId = '{trace_id}'" in query

        # Should sort by start time
        assert "sort startTimeUnixNano asc" in query

    def test_spans_queries_include_essential_fields(self):
        """Test that span queries include all essential fields."""
        query = CloudWatchQueryBuilder.build_spans_by_session_query("test-session", "test-agent")

        # Essential fields for span processing
        essential_fields = [
            "@message",
            "traceId",
            "spanId",
            "spanName",
            "statusCode",
            "durationMs",
            "startTimeUnixNano",
            "endTimeUnixNano",
            "parentSpanId",
        ]

        for field in essential_fields:
            assert field in query, f"Missing essential field: {field}"


class TestRuntimeLogsQueries:
    """Test query builders for runtime logs."""

    def test_build_runtime_logs_by_trace_direct(self):
        """Test building runtime logs query for a single trace."""
        trace_id = "trace-abc123"
        query = CloudWatchQueryBuilder.build_runtime_logs_by_trace_direct(trace_id)

        # Should contain required fields
        assert "fields @timestamp" in query
        assert "@message" in query
        assert "spanId" in query
        assert "traceId" in query

        # Should filter by trace ID
        assert f"traceId = '{trace_id}'" in query

        # Should sort by timestamp
        assert "sort @timestamp asc" in query

    def test_build_runtime_logs_by_traces_batch_single_trace(self):
        """Test building batch runtime logs query with single trace."""
        trace_ids = ["trace-123"]
        query = CloudWatchQueryBuilder.build_runtime_logs_by_traces_batch(trace_ids)

        # Should contain required fields
        assert "fields @timestamp" in query
        assert "@message" in query
        assert "spanId" in query
        assert "traceId" in query

        # Should use IN clause
        assert "traceId in [" in query
        assert "'trace-123'" in query

        # Should sort by timestamp
        assert "sort @timestamp asc" in query

    def test_build_runtime_logs_by_traces_batch_multiple_traces(self):
        """Test building batch runtime logs query with multiple traces."""
        trace_ids = ["trace-1", "trace-2", "trace-3"]
        query = CloudWatchQueryBuilder.build_runtime_logs_by_traces_batch(trace_ids)

        # Should contain all trace IDs
        for trace_id in trace_ids:
            assert f"'{trace_id}'" in query

        # Should use IN clause with comma separation
        assert "traceId in [" in query
        assert ", " in query  # Should have comma separators

    def test_build_runtime_logs_by_traces_batch_empty_list(self):
        """Test building batch runtime logs query with empty list."""
        query = CloudWatchQueryBuilder.build_runtime_logs_by_traces_batch([])

        # Should return empty string for empty list
        assert query == ""


class TestSessionQueries:
    """Test query builders for session operations."""

    def test_build_latest_session_query_default_limit(self):
        """Test building latest session query with default limit."""
        agent_id = "agent-test123"
        query = CloudWatchQueryBuilder.build_latest_session_query(agent_id)

        # Should filter by agent type
        assert 'resource.attributes.aws.service.type = "gen_ai_agent"' in query

        # Should parse and filter by agent ID
        assert "parse resource.attributes.cloud.resource_id" in query
        assert f"parsedAgentId = '{agent_id}'" in query

        # Should aggregate by session ID
        assert "by attributes.session.id" in query

        # Should sort by max end time
        assert "sort maxEnd desc" in query

        # Should have default limit of 1
        assert "limit 1" in query

    def test_build_latest_session_query_custom_limit(self):
        """Test building latest session query with custom limit."""
        agent_id = "agent-test456"
        limit = 5
        query = CloudWatchQueryBuilder.build_latest_session_query(agent_id, limit)

        # Should have custom limit
        assert f"limit {limit}" in query

        # Should still contain agent filter
        assert f"parsedAgentId = '{agent_id}'" in query

    def test_build_session_summary_query_basic(self):
        """Test building session summary query without agent ID."""
        session_id = "session-abc123"
        query = CloudWatchQueryBuilder.build_session_summary_query(session_id)

        # Should filter by session ID
        assert f"attributes.session.id = '{session_id}'" in query

        # Should include aggregation fields
        assert "stats count(spanId) as spanCount" in query
        assert "count_distinct(traceId) as traceCount" in query
        assert "sum(durationMs) as totalDurationMs" in query

        # Should count errors
        assert "errorCount" in query
        assert "systemErrors" in query
        assert "clientErrors" in query
        assert "throttles" in query

        # Should aggregate by session ID
        assert "by sessionId" in query

        # Should NOT have agent ID filter
        assert "parsedAgentId" not in query

    def test_build_session_summary_query_with_agent_id(self):
        """Test building session summary query with agent ID."""
        session_id = "session-def456"
        agent_id = "agent-xyz789"
        query = CloudWatchQueryBuilder.build_session_summary_query(session_id, agent_id)

        # Should filter by session ID
        assert f"attributes.session.id = '{session_id}'" in query

        # Should parse and filter by agent ID
        assert "parse resource.attributes.cloud.resource_id" in query
        assert f"parsedAgentId = '{agent_id}'" in query

        # Should include aggregation fields
        assert "stats count(spanId) as spanCount" in query


class TestQuerySafety:
    """Test query builders handle special characters and edge cases safely."""

    def test_query_with_special_characters_in_ids(self):
        """Test that special characters in IDs are handled correctly."""
        # IDs with hyphens, underscores, numbers
        session_id = "session-123_test-456"
        trace_id = "trace_abc-def-789"
        agent_id = "agent-test_123-abc"

        # Should not raise exceptions
        query1 = CloudWatchQueryBuilder.build_spans_by_session_query(session_id, agent_id)
        query2 = CloudWatchQueryBuilder.build_spans_by_trace_query(trace_id)
        query3 = CloudWatchQueryBuilder.build_latest_session_query(agent_id)

        # Should contain the IDs
        assert session_id in query1
        assert trace_id in query2
        assert agent_id in query3

    def test_query_with_empty_trace_ids_list(self):
        """Test handling of empty trace IDs list."""
        query = CloudWatchQueryBuilder.build_runtime_logs_by_traces_batch([])
        assert query == ""

    def test_queries_use_proper_field_escaping(self):
        """Test that field names use proper dot notation."""
        query = CloudWatchQueryBuilder.build_spans_by_session_query("test-session", "test-agent")

        # Should use proper dot notation for nested fields
        assert "attributes.session.id" in query
        assert "resource.attributes" in query
        assert "status.code" in query


class TestQueryStructure:
    """Test the structure and syntax of generated queries."""

    def test_spans_query_has_valid_structure(self):
        """Test that spans queries have valid CloudWatch Logs Insights structure."""
        query = CloudWatchQueryBuilder.build_spans_by_session_query("test-session", "test-agent")

        # Should start with fields command
        assert query.strip().startswith("fields")

        # Should have filter clause
        assert "| filter" in query

        # Should have sort clause
        assert "| sort" in query

    def test_runtime_logs_query_has_valid_structure(self):
        """Test that runtime logs queries have valid structure."""
        query = CloudWatchQueryBuilder.build_runtime_logs_by_trace_direct("test-trace")

        # Should start with fields command
        assert query.strip().startswith("fields")

        # Should have filter clause
        assert "| filter" in query

        # Should have sort clause
        assert "| sort" in query

    def test_session_summary_query_has_stats_command(self):
        """Test that session summary query uses stats command."""
        query = CloudWatchQueryBuilder.build_session_summary_query("test-session")

        # Should have fields command
        assert "fields" in query

        # Should have stats command for aggregation
        assert "| stats" in query

        # Should aggregate by session ID
        assert "by sessionId" in query

    def test_latest_session_query_has_aggregation(self):
        """Test that latest session query uses proper aggregation."""
        query = CloudWatchQueryBuilder.build_latest_session_query("test-agent")

        # Should have stats for aggregation
        assert "| stats" in query

        # Should aggregate by session ID
        assert "by attributes.session.id" in query

        # Should have sort and limit
        assert "| sort" in query
        assert "| limit" in query


class TestQueryConsistency:
    """Test consistency across different query builders."""

    def test_all_span_queries_sort_by_start_time(self):
        """Test that all span queries sort by start time."""
        query1 = CloudWatchQueryBuilder.build_spans_by_session_query("session-1", "agent-1")
        query2 = CloudWatchQueryBuilder.build_spans_by_trace_query("trace-1")

        assert "sort startTimeUnixNano asc" in query1
        assert "sort startTimeUnixNano asc" in query2

    def test_all_runtime_log_queries_sort_by_timestamp(self):
        """Test that all runtime log queries sort by timestamp."""
        query1 = CloudWatchQueryBuilder.build_runtime_logs_by_trace_direct("trace-1")
        query2 = CloudWatchQueryBuilder.build_runtime_logs_by_traces_batch(["trace-1", "trace-2"])

        assert "sort @timestamp asc" in query1
        assert "sort @timestamp asc" in query2

    def test_queries_with_agent_id_use_consistent_parsing(self):
        """Test that agent ID parsing is consistent across queries."""
        agent_id = "test-agent"

        query1 = CloudWatchQueryBuilder.build_spans_by_session_query("session-1", agent_id)
        query2 = CloudWatchQueryBuilder.build_latest_session_query(agent_id)
        query3 = CloudWatchQueryBuilder.build_session_summary_query("session-1", agent_id)

        # All should use same parsing pattern
        parse_pattern = 'parse resource.attributes.cloud.resource_id "runtime/*/"'

        assert parse_pattern in query1
        assert parse_pattern in query2
        assert parse_pattern in query3

        # All should filter by parsed agent ID
        for query in [query1, query2, query3]:
            assert f"parsedAgentId = '{agent_id}'" in query
