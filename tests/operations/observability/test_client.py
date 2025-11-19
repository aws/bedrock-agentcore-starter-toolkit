"""Unit tests for stateless ObservabilityClient."""

import pytest
from botocore.exceptions import ClientError


class TestObservabilityClientInit:
    """Test stateless ObservabilityClient initialization."""

    def test_init_only_requires_region(self, observability_client):
        """Test that initialization only requires region (stateless)."""
        assert observability_client.region == "us-east-1"

    def test_init_does_not_store_agent_id(self, observability_client):
        """Test that client does not store agent_id (stateless)."""
        assert not hasattr(observability_client, "agent_id")

    def test_init_does_not_store_endpoint_name(self, observability_client):
        """Test that client does not store endpoint_name (stateless)."""
        assert not hasattr(observability_client, "runtime_suffix")
        assert not hasattr(observability_client, "endpoint_name")

    def test_init_creates_logs_client(self, observability_client, mock_logs_client):
        """Test that boto3 logs client is created."""
        assert observability_client.logs_client == mock_logs_client

    def test_init_creates_query_builder(self, observability_client):
        """Test that query builder is created."""
        assert observability_client.query_builder is not None


class TestQuerySpansBySession:
    """Test querying spans by session ID."""

    def test_query_spans_by_session_success(
        self, observability_client, mock_logs_client, mock_query_response_single_span, session_id, agent_id, time_range
    ):
        """Test successful span query by session."""
        mock_query_response_single_span(mock_logs_client)

        spans = observability_client.query_spans_by_session(
            session_id=session_id,
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
        )

        assert len(spans) == 1
        assert spans[0].span_name == "TestSpan"
        mock_logs_client.start_query.assert_called_once()

    def test_query_spans_requires_agent_id(self, observability_client, session_id, time_range):
        """Test that query_spans_by_session requires agent_id parameter."""
        # This should fail at call time if agent_id is not provided
        with pytest.raises(TypeError, match="agent_id"):
            observability_client.query_spans_by_session(
                session_id=session_id,
                start_time_ms=time_range["start_time_ms"],
                end_time_ms=time_range["end_time_ms"],
                # agent_id intentionally omitted
            )

    def test_query_spans_includes_agent_id_in_query(
        self, observability_client, mock_logs_client, mock_query_response_single_span, session_id, agent_id, time_range
    ):
        """Test that agent_id is included in CloudWatch query."""
        mock_query_response_single_span(mock_logs_client)

        observability_client.query_spans_by_session(
            session_id=session_id,
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
        )

        # Verify agent_id is in the query string
        call_args = mock_logs_client.start_query.call_args
        query_string = call_args.kwargs["queryString"]
        assert agent_id in query_string

    def test_query_spans_empty_results(
        self, observability_client, mock_logs_client, mock_query_response_empty, session_id, agent_id, time_range
    ):
        """Test query with no results."""
        mock_query_response_empty(mock_logs_client)

        spans = observability_client.query_spans_by_session(
            session_id=session_id,
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
        )

        assert spans == []


class TestQuerySpansByTrace:
    """Test querying spans by trace ID."""

    def test_query_spans_by_trace_success(
        self, observability_client, mock_logs_client, mock_query_response_single_span, trace_id, agent_id, time_range
    ):
        """Test successful span query by trace."""
        mock_query_response_single_span(mock_logs_client)

        spans = observability_client.query_spans_by_trace(
            trace_id=trace_id,
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
        )

        assert len(spans) == 1
        assert spans[0].trace_id == trace_id

    def test_query_spans_by_trace_requires_agent_id(self, observability_client, trace_id, time_range):
        """Test that query_spans_by_trace requires agent_id parameter."""
        with pytest.raises(TypeError, match="agent_id"):
            observability_client.query_spans_by_trace(
                trace_id=trace_id,
                start_time_ms=time_range["start_time_ms"],
                end_time_ms=time_range["end_time_ms"],
                # agent_id intentionally omitted
            )


class TestQueryRuntimeLogsByTraces:
    """Test querying runtime logs for traces."""

    def test_query_runtime_logs_success(
        self,
        observability_client,
        mock_logs_client,
        mock_query_response_runtime_logs,
        trace_id,
        agent_id,
        endpoint_name,
        time_range,
    ):
        """Test successful runtime logs query."""
        mock_query_response_runtime_logs(mock_logs_client)

        logs = observability_client.query_runtime_logs_by_traces(
            trace_ids=[trace_id],
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
            endpoint_name=endpoint_name,
        )

        assert len(logs) > 0
        assert all(isinstance(log, type(logs[0])) for log in logs)

    def test_query_runtime_logs_requires_agent_id(self, observability_client, trace_id, endpoint_name, time_range):
        """Test that query_runtime_logs requires agent_id parameter."""
        with pytest.raises(TypeError, match="agent_id"):
            observability_client.query_runtime_logs_by_traces(
                trace_ids=[trace_id],
                start_time_ms=time_range["start_time_ms"],
                end_time_ms=time_range["end_time_ms"],
                # agent_id intentionally omitted
                endpoint_name=endpoint_name,
            )

    def test_query_runtime_logs_constructs_correct_log_group(
        self,
        observability_client,
        mock_logs_client,
        mock_query_response_runtime_logs,
        trace_id,
        agent_id,
        endpoint_name,
        time_range,
    ):
        """Test that runtime log group name is constructed correctly."""
        mock_query_response_runtime_logs(mock_logs_client)

        observability_client.query_runtime_logs_by_traces(
            trace_ids=[trace_id],
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
            endpoint_name=endpoint_name,
        )

        # Verify log group name construction
        call_args = mock_logs_client.start_query.call_args
        log_group_name = call_args.kwargs["logGroupName"]
        assert log_group_name == f"/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name}"

    def test_query_runtime_logs_empty_list(self, observability_client, agent_id, endpoint_name, time_range):
        """Test querying with empty trace list."""
        logs = observability_client.query_runtime_logs_by_traces(
            trace_ids=[],
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
            endpoint_name=endpoint_name,
        )

        assert logs == []

    def test_query_runtime_logs_batch_query(
        self,
        observability_client,
        mock_logs_client,
        mock_query_response_runtime_logs,
        agent_id,
        endpoint_name,
        time_range,
    ):
        """Test that multiple traces use batch query."""
        mock_query_response_runtime_logs(mock_logs_client)
        trace_ids = ["trace-1", "trace-2", "trace-3"]

        observability_client.query_runtime_logs_by_traces(
            trace_ids=trace_ids,
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
            endpoint_name=endpoint_name,
        )

        # Should make single batch query (not 3 separate queries)
        assert mock_logs_client.start_query.call_count == 1

        # Verify IN clause in query
        call_args = mock_logs_client.start_query.call_args
        query_string = call_args.kwargs["queryString"]
        assert "traceId in [" in query_string


class TestGetLatestSessionId:
    """Test getting latest session ID."""

    def test_get_latest_session_id_success(self, observability_client, mock_logs_client, agent_id, time_range):
        """Test successfully getting latest session ID."""
        expected_session_id = "session-latest-123"

        # Mock the query response
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "attributes.session.id", "value": expected_session_id},
                    {"field": "maxEnd", "value": "1234567890"},
                ]
            ],
        }

        session_id = observability_client.get_latest_session_id(
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
        )

        assert session_id == expected_session_id

    def test_get_latest_session_id_requires_agent_id(self, observability_client, time_range):
        """Test that get_latest_session_id requires agent_id parameter."""
        with pytest.raises(TypeError, match="agent_id"):
            observability_client.get_latest_session_id(
                start_time_ms=time_range["start_time_ms"],
                end_time_ms=time_range["end_time_ms"],
                # agent_id intentionally omitted
            )

    def test_get_latest_session_id_no_sessions(
        self, observability_client, mock_logs_client, mock_query_response_empty, agent_id, time_range
    ):
        """Test when no sessions are found."""
        mock_query_response_empty(mock_logs_client)

        session_id = observability_client.get_latest_session_id(
            start_time_ms=time_range["start_time_ms"],
            end_time_ms=time_range["end_time_ms"],
            agent_id=agent_id,
        )

        assert session_id is None


class TestErrorHandling:
    """Test error handling."""

    def test_log_group_not_found(self, observability_client, mock_logs_client, session_id, agent_id, time_range):
        """Test handling of missing log group."""
        # Mock ResourceNotFoundException
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        mock_logs_client.start_query.side_effect = ClientError(error_response, "StartQuery")

        with pytest.raises(Exception, match="Log group not found"):
            observability_client.query_spans_by_session(
                session_id=session_id,
                start_time_ms=time_range["start_time_ms"],
                end_time_ms=time_range["end_time_ms"],
                agent_id=agent_id,
            )

    def test_query_timeout(self, observability_client, mock_logs_client, session_id, agent_id, time_range):
        """Test query timeout handling."""
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {"status": "Running"}

        # Reduce timeout for faster test
        observability_client.QUERY_TIMEOUT_SECONDS = 0.1
        observability_client.POLL_INTERVAL_SECONDS = 0.05

        with pytest.raises(TimeoutError):
            observability_client.query_spans_by_session(
                session_id=session_id,
                start_time_ms=time_range["start_time_ms"],
                end_time_ms=time_range["end_time_ms"],
                agent_id=agent_id,
            )
