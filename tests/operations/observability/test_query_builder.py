"""Unit tests for CloudWatchQueryBuilder."""

import pytest

from bedrock_agentcore_starter_toolkit.operations.observability.query_builder import CloudWatchQueryBuilder


class TestCloudWatchQueryBuilder:
    """Test cases for CloudWatchQueryBuilder."""

    @pytest.fixture
    def query_builder(self):
        """Create a CloudWatchQueryBuilder instance."""
        return CloudWatchQueryBuilder()

    # Test build_spans_by_session_query
    @pytest.mark.parametrize(
        "session_id,expected_fields,expected_filter",
        [
            (
                "session-123",
                ["traceId", "spanId", "name as spanName", "startTimeUnixNano"],
                "attributes.session.id = 'session-123'",
            ),
            (
                "eb358f6f-fc68-47ed-b09a-669abfaf4469",
                ["traceId", "spanId", "name as spanName", "startTimeUnixNano"],
                "attributes.session.id = 'eb358f6f-fc68-47ed-b09a-669abfaf4469'",
            ),
            (
                "test-session-with-dashes",
                ["traceId", "spanId", "name as spanName"],
                "attributes.session.id = 'test-session-with-dashes'",
            ),
        ],
    )
    def test_build_spans_by_session_query(self, query_builder, session_id, expected_fields, expected_filter):
        """Test building spans by session query with various session IDs."""
        query = query_builder.build_spans_by_session_query(session_id)

        # Check that all expected fields are present
        for field in expected_fields:
            assert field in query, f"Expected field '{field}' not found in query"

        # Check filter condition
        assert expected_filter in query, f"Expected filter '{expected_filter}' not found in query"

        # Check sort order
        assert "sort startTimeUnixNano asc" in query

    # Test build_spans_by_trace_query
    @pytest.mark.parametrize(
        "trace_id,expected_filter",
        [
            ("690156557a198c640accf1ab0fae04dd", "traceId = '690156557a198c640accf1ab0fae04dd'"),
            ("abc123", "traceId = 'abc123'"),
            ("trace-with-special-chars", "traceId = 'trace-with-special-chars'"),
        ],
    )
    def test_build_spans_by_trace_query(self, query_builder, trace_id, expected_filter):
        """Test building spans by trace query with various trace IDs."""
        query = query_builder.build_spans_by_trace_query(trace_id)

        # Check required fields
        assert "traceId" in query
        assert "spanId" in query
        assert "name as spanName" in query
        assert "startTimeUnixNano" in query

        # Check filter condition
        assert expected_filter in query

        # Check sort order
        assert "sort startTimeUnixNano asc" in query

    # Test build_runtime_logs_by_trace_direct
    @pytest.mark.parametrize(
        "trace_id,expected_filter",
        [
            ("690156557a198c640accf1ab0fae04dd", "traceId = '690156557a198c640accf1ab0fae04dd'"),
            ("trace-123", "traceId = 'trace-123'"),
        ],
    )
    def test_build_runtime_logs_by_trace_direct(self, query_builder, trace_id, expected_filter):
        """Test building runtime logs query for single trace."""
        query = query_builder.build_runtime_logs_by_trace_direct(trace_id)

        # Check required fields
        assert "@timestamp" in query
        assert "@message" in query
        assert "spanId" in query
        assert "traceId" in query
        assert "@logStream" in query

        # Check filter uses only traceId (not trace_id)
        assert expected_filter in query
        assert "trace_id" not in query  # Should not use snake_case

        # Check sort order
        assert "sort @timestamp asc" in query

    # Test build_runtime_logs_by_traces_batch
    @pytest.mark.parametrize(
        "trace_ids,expected_in_clause",
        [
            (["trace-1"], "'trace-1'"),
            (["trace-1", "trace-2"], "'trace-1', 'trace-2'"),
            (
                ["690156557a198c640accf1ab0fae04dd", "abc123", "xyz789"],
                "'690156557a198c640accf1ab0fae04dd', 'abc123', 'xyz789'",
            ),
        ],
    )
    def test_build_runtime_logs_by_traces_batch(self, query_builder, trace_ids, expected_in_clause):
        """Test building batch runtime logs query with various trace ID lists."""
        query = query_builder.build_runtime_logs_by_traces_batch(trace_ids)

        # Check required fields
        assert "@timestamp" in query
        assert "@message" in query
        assert "spanId" in query
        assert "traceId" in query

        # Check IN clause
        assert f"traceId in [{expected_in_clause}]" in query

        # Should not use snake_case or OR condition
        assert "trace_id" not in query
        assert " or " not in query.lower()

        # Check sort order
        assert "sort @timestamp asc" in query

    def test_build_runtime_logs_by_traces_batch_empty_list(self, query_builder):
        """Test building batch runtime logs query with empty list."""
        query = query_builder.build_runtime_logs_by_traces_batch([])

        # Should return empty string
        assert query == ""

    # Test build_session_summary_query
    @pytest.mark.parametrize(
        "session_id,expected_filter,expected_stats",
        [
            (
                "session-123",
                "attributes.session.id = 'session-123'",
                ["count(spanId) as spanCount", "count_distinct(traceId) as traceCount", "sum(durationMs)"],
            ),
            (
                "eb358f6f-fc68-47ed-b09a-669abfaf4469",
                "attributes.session.id = 'eb358f6f-fc68-47ed-b09a-669abfaf4469'",
                ["spanCount", "traceCount", "errorCount"],
            ),
        ],
    )
    def test_build_session_summary_query(self, query_builder, session_id, expected_filter, expected_stats):
        """Test building session summary query."""
        query = query_builder.build_session_summary_query(session_id)

        # Check filter condition
        assert expected_filter in query

        # Check stats aggregations
        for stat in expected_stats:
            assert stat in query, f"Expected stat '{stat}' not found in query"

        # Check group by
        assert "by sessionId" in query

    # Test query field consistency
    @pytest.mark.parametrize(
        "method_name,method_args",
        [
            ("build_spans_by_session_query", ["session-123"]),
            ("build_spans_by_trace_query", ["trace-123"]),
            ("build_runtime_logs_by_trace_direct", ["trace-123"]),
            ("build_runtime_logs_by_traces_batch", [["trace-1", "trace-2"]]),
        ],
    )
    def test_query_uses_camel_case_fields(self, query_builder, method_name, method_args):
        """Test that all queries use camelCase field names consistently."""
        method = getattr(query_builder, method_name)
        query = method(*method_args)

        # All queries should use camelCase
        assert "traceId" in query or "sessionId" in query
        assert "spanId" in query or method_name == "build_session_summary_query"

        # Should NOT use snake_case (except system fields like @timestamp)
        # Check for snake_case versions (excluding @timestamp, @message, etc.)
        if "trace" in query.lower():
            # If we're filtering by trace, make sure it's traceId not trace_id
            if "filter" in query:
                # Extract filter lines
                filter_lines = [line for line in query.split("\n") if "filter" in line.lower()]
                for line in filter_lines:
                    if "trace" in line.lower() and "trace_id" in line:
                        pytest.fail(f"Query uses snake_case 'trace_id' instead of 'traceId': {line}")

    # Test query structure
    @pytest.mark.parametrize(
        "method_name,method_args,expected_clauses",
        [
            (
                "build_spans_by_session_query",
                ["session-123"],
                ["fields", "filter", "sort"],
            ),
            (
                "build_spans_by_trace_query",
                ["trace-123"],
                ["fields", "filter", "sort"],
            ),
            (
                "build_runtime_logs_by_trace_direct",
                ["trace-123"],
                ["fields", "filter", "sort"],
            ),
            (
                "build_runtime_logs_by_traces_batch",
                [["trace-1"]],
                ["fields", "filter", "sort"],
            ),
            (
                "build_session_summary_query",
                ["session-123"],
                ["fields", "filter", "stats", "by"],
            ),
        ],
    )
    def test_query_structure(self, query_builder, method_name, method_args, expected_clauses):
        """Test that queries have proper structure with expected clauses."""
        method = getattr(query_builder, method_name)
        query = method(*method_args)

        # Check all expected clauses are present
        for clause in expected_clauses:
            assert clause in query.lower(), f"Expected clause '{clause}' not found in query"

    # Test special characters in IDs
    @pytest.mark.parametrize(
        "method_name,id_value",
        [
            ("build_spans_by_session_query", "session-with-dashes-123"),
            ("build_spans_by_trace_query", "trace-abc-123-xyz"),
            ("build_runtime_logs_by_trace_direct", "trace_with_underscores"),
        ],
    )
    def test_query_handles_special_characters(self, query_builder, method_name, id_value):
        """Test that queries properly handle IDs with special characters."""
        method = getattr(query_builder, method_name)
        query = method(id_value)

        # Query should contain the ID value
        assert id_value in query

        # Should not cause syntax errors (basic check)
        assert "'" in query  # Should be quoted

    # Test agent_id filtering (cross-agent session collision prevention)
    @pytest.mark.parametrize(
        "session_id,agent_id",
        [
            ("session-123", "AGENT123"),
            ("session-456", "agent-abc-def"),
        ],
    )
    def test_build_spans_by_session_query_with_agent_id(self, query_builder, session_id, agent_id):
        """Test that session queries filter by agent_id to prevent cross-agent collisions."""
        query = query_builder.build_spans_by_session_query(session_id, agent_id=agent_id)

        # Check that agent_id filter uses parse pattern (matches dashboard)
        assert f"attributes.session.id = '{session_id}'" in query
        assert 'parse resource.attributes.cloud.resource_id "runtime/*/"' in query
        assert f"parsedAgentId = '{agent_id}'" in query

    def test_build_spans_by_session_query_without_agent_id(self, query_builder):
        """Test that session queries work without agent_id for backward compatibility."""
        query = query_builder.build_spans_by_session_query("session-123")

        # Should only have session filter, no agent filter or parse
        assert "attributes.session.id = 'session-123'" in query
        # Check that there's no parse or agent filter
        assert "parsedAgentId" not in query
        assert 'parse resource.attributes.cloud.resource_id "runtime/*/"' not in query

    @pytest.mark.parametrize(
        "session_id,agent_id",
        [
            ("session-123", "AGENT123"),
            ("test-session", "agent-xyz"),
        ],
    )
    def test_build_session_summary_query_with_agent_id(self, query_builder, session_id, agent_id):
        """Test that session summary queries filter by agent_id."""
        query = query_builder.build_session_summary_query(session_id, agent_id=agent_id)

        # Check that agent_id filter uses parse pattern (matches dashboard)
        assert 'parse resource.attributes.cloud.resource_id "runtime/*/"' in query
        assert f"parsedAgentId = '{agent_id}'" in query

        # Check that session filter is still present
        assert f"attributes.session.id = '{session_id}'" in query

    def test_build_session_summary_query_without_agent_id(self, query_builder):
        """Test that session summary queries work without agent_id for backward compatibility."""
        query = query_builder.build_session_summary_query("session-123")

        # Should only have session filter, no agent filter or parse
        assert "attributes.session.id = 'session-123'" in query
        # Check that there's no parse or agent filter
        assert "parsedAgentId" not in query
        assert 'parse resource.attributes.cloud.resource_id "runtime/*/"' not in query

    def test_build_session_summary_query_enhanced_error_tracking(self, query_builder):
        """Test that session summary queries include enhanced error tracking (4xx, 5xx, throttles)."""
        query = query_builder.build_session_summary_query("session-123", agent_id="AGENT123")

        # Check for enhanced error tracking fields
        assert "systemErrors" in query
        assert "clientErrors" in query
        assert "throttles" in query

        # Check specific error conditions
        assert "httpStatusCode >= 500" in query
        assert "httpStatusCode >= 400 and httpStatusCode < 500" in query
        assert "httpStatusCode = 429" in query

    # Test latest session query
    @pytest.mark.parametrize(
        "agent_id,limit",
        [
            ("AGENT123", 1),
            ("agent-abc-def", 1),
            ("AGENT456", 5),
        ],
    )
    def test_build_latest_session_query(self, query_builder, agent_id, limit):
        """Test building query to find latest session for an agent."""
        query = query_builder.build_latest_session_query(agent_id, limit=limit)

        # Check vended spans filter is present
        assert 'resource.attributes.aws.service.type = "gen_ai_agent"' in query

        # Check agent filter uses parse pattern (matches dashboard)
        assert 'parse resource.attributes.cloud.resource_id "runtime/*/"' in query
        assert f"parsedAgentId = '{agent_id}'" in query

        # Check stats aggregation
        assert "stats max(endTimeUnixNano) as maxEnd by attributes.session.id" in query

        # Check sorting and limit
        assert "sort maxEnd desc" in query
        assert f"limit {limit}" in query

    def test_build_latest_session_query_default_limit(self, query_builder):
        """Test that latest session query uses default limit of 1."""
        query = query_builder.build_latest_session_query("AGENT123")

        # Should have limit 1 by default
        assert "limit 1" in query
