"""Unit tests for ObservabilityClient."""

from unittest.mock import MagicMock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.observability import ObservabilityClient
from bedrock_agentcore_starter_toolkit.operations.observability.models.telemetry import RuntimeLog, Span


@pytest.fixture
def mock_logs_client():
    """Create a mock CloudWatch Logs client."""
    with patch("boto3.client") as mock_client:
        logs_client = MagicMock()
        mock_client.return_value = logs_client
        yield logs_client


@pytest.fixture
def observability_client(mock_logs_client):  # noqa: ARG001
    """Create an ObservabilityClient with mocked dependencies."""
    return ObservabilityClient(
        region_name="us-east-1",
        agent_id="test-agent-123",
        runtime_suffix="DEFAULT",
    )


class TestObservabilityClient:
    """Test cases for ObservabilityClient."""

    def test_initialization(self, observability_client):
        """Test client initialization."""
        assert observability_client.region == "us-east-1"
        assert observability_client.agent_id == "test-agent-123"
        assert observability_client.runtime_suffix == "DEFAULT"
        assert observability_client.runtime_log_group == "/aws/bedrock-agentcore/runtimes/test-agent-123-DEFAULT"
        assert observability_client.SPANS_LOG_GROUP == "aws/spans"

    @pytest.mark.parametrize(
        "session_id,mock_results,expected_span_count",
        [
            (
                "session-123",
                [
                    [
                        {"field": "traceId", "value": "trace-1"},
                        {"field": "spanId", "value": "span-1"},
                        {"field": "spanName", "value": "Span1"},
                    ]
                ],
                1,
            ),
            (
                "session-456",
                [
                    [
                        {"field": "traceId", "value": "trace-1"},
                        {"field": "spanId", "value": "span-1"},
                        {"field": "spanName", "value": "Span1"},
                    ],
                    [
                        {"field": "traceId", "value": "trace-1"},
                        {"field": "spanId", "value": "span-2"},
                        {"field": "spanName", "value": "Span2"},
                    ],
                ],
                2,
            ),
        ],
    )
    def test_query_spans_by_session(
        self, observability_client, mock_logs_client, session_id, mock_results, expected_span_count
    ):
        """Test querying spans by session ID with various result counts."""
        # Mock CloudWatch query response
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": mock_results,
        }

        # Execute query
        spans = observability_client.query_spans_by_session(session_id, 1000, 2000)

        # Verify results
        assert len(spans) == expected_span_count
        assert all(isinstance(span, Span) for span in spans)

        # Verify CloudWatch API calls
        mock_logs_client.start_query.assert_called_once()
        call_args = mock_logs_client.start_query.call_args
        assert call_args.kwargs["logGroupName"] == "aws/spans"
        assert session_id in call_args.kwargs["queryString"]

    @pytest.mark.parametrize(
        "trace_id,expected_query_filter",
        [
            ("690156557a198c640accf1ab0fae04dd", "traceId = '690156557a198c640accf1ab0fae04dd'"),
            ("trace-123", "traceId = 'trace-123'"),
        ],
    )
    def test_query_spans_by_trace(self, observability_client, mock_logs_client, trace_id, expected_query_filter):
        """Test querying spans by trace ID."""
        # Mock CloudWatch query response
        mock_logs_client.start_query.return_value = {"queryId": "query-456"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "traceId", "value": trace_id},
                    {"field": "spanId", "value": "span-1"},
                    {"field": "spanName", "value": "TestSpan"},
                ]
            ],
        }

        # Execute query
        spans = observability_client.query_spans_by_trace(trace_id, 1000, 2000)

        # Verify results
        assert len(spans) == 1
        assert spans[0].trace_id == trace_id

        # Verify query contains correct filter
        call_args = mock_logs_client.start_query.call_args
        assert expected_query_filter in call_args.kwargs["queryString"]

    @pytest.mark.parametrize(
        "trace_ids,expected_in_clause",
        [
            (["trace-1"], "'trace-1'"),
            (["trace-1", "trace-2"], "'trace-1', 'trace-2'"),
            (["trace-1", "trace-2", "trace-3"], "'trace-1', 'trace-2', 'trace-3'"),
        ],
    )
    def test_query_runtime_logs_by_traces_batch(
        self, observability_client, mock_logs_client, trace_ids, expected_in_clause
    ):
        """Test batch querying runtime logs for multiple traces."""
        # Mock CloudWatch query response
        mock_logs_client.start_query.return_value = {"queryId": "query-789"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
                    {"field": "@message", "value": "Log message"},
                    {"field": "spanId", "value": "span-1"},
                    {"field": "traceId", "value": trace_ids[0]},
                ]
            ],
        }

        # Execute query
        logs = observability_client.query_runtime_logs_by_traces(trace_ids, 1000, 2000)

        # Verify results
        assert len(logs) > 0
        assert all(isinstance(log, RuntimeLog) for log in logs)

        # Verify batch query used IN clause
        call_args = mock_logs_client.start_query.call_args
        assert f"traceId in [{expected_in_clause}]" in call_args.kwargs["queryString"]

        # Verify it queries the runtime log group
        assert "/aws/bedrock-agentcore/runtimes/test-agent-123-DEFAULT" in call_args.kwargs["logGroupName"]

    def test_query_runtime_logs_empty_list(self, observability_client):
        """Test querying runtime logs with empty trace ID list."""
        logs = observability_client.query_runtime_logs_by_traces([], 1000, 2000)

        # Should return empty list without making API calls
        assert logs == []

    def test_query_runtime_logs_batch_failure_fallback(self, observability_client, mock_logs_client):
        """Test that batch query failure triggers fallback to individual queries."""
        trace_ids = ["trace-1", "trace-2"]

        # First call (batch) fails
        mock_logs_client.start_query.side_effect = [
            Exception("Batch query failed"),
            {"queryId": "query-1"},
            {"queryId": "query-2"},
        ]

        # Individual queries succeed
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2025-10-28T10:00:00Z"},
                    {"field": "@message", "value": "Log message"},
                    {"field": "spanId", "value": "span-1"},
                    {"field": "traceId", "value": "trace-1"},
                ]
            ],
        }

        # Execute query
        logs = observability_client.query_runtime_logs_by_traces(trace_ids, 1000, 2000)

        # Should fall back to individual queries and still return results
        assert len(logs) > 0

        # Should have called start_query 3 times (1 batch failed + 2 individual)
        assert mock_logs_client.start_query.call_count == 3

    @pytest.mark.parametrize(
        "query_status,should_timeout",
        [
            ("Complete", False),
            ("Running", True),
        ],
    )
    def test_execute_cloudwatch_query_timeout(
        self, observability_client, mock_logs_client, query_status, should_timeout
    ):
        """Test CloudWatch query timeout handling."""
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}

        if should_timeout:
            # Query never completes
            mock_logs_client.get_query_results.return_value = {"status": query_status}

            # Temporarily reduce timeout for faster test
            observability_client.QUERY_TIMEOUT_SECONDS = 0.1
            observability_client.POLL_INTERVAL_SECONDS = 0.05

            with pytest.raises(TimeoutError):
                observability_client.query_spans_by_session("session-123", 1000, 2000)
        else:
            mock_logs_client.get_query_results.return_value = {
                "status": query_status,
                "results": [],
            }

            # Should not raise
            observability_client.query_spans_by_session("session-123", 1000, 2000)

    @pytest.mark.parametrize(
        "query_status,expected_exception",
        [
            ("Failed", Exception),
            ("Cancelled", Exception),
        ],
    )
    def test_execute_cloudwatch_query_failure_states(
        self, observability_client, mock_logs_client, query_status, expected_exception
    ):
        """Test CloudWatch query failure state handling."""
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {"status": query_status}

        with pytest.raises(expected_exception):
            observability_client.query_spans_by_session("session-123", 1000, 2000)

    def test_get_session_data(self, observability_client, mock_logs_client):
        """Test getting complete session data."""
        session_id = "session-123"

        # Mock spans query
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "traceId", "value": "trace-1"},
                    {"field": "spanId", "value": "span-1"},
                    {"field": "spanName", "value": "TestSpan"},
                ]
            ],
        }

        # Execute
        session_data = observability_client.get_session_data(session_id, 1000, 2000)

        # Verify
        assert session_data.session_id == session_id
        assert session_data.agent_id == "test-agent-123"
        assert len(session_data.spans) == 1
        assert len(session_data.traces) == 1

    def test_get_session_summary(self, observability_client, mock_logs_client):
        """Test getting session summary statistics."""
        session_id = "session-123"

        # Mock summary query
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "sessionId", "value": session_id},
                    {"field": "spanCount", "value": "10"},
                    {"field": "traceCount", "value": "2"},
                    {"field": "errorCount", "value": "1"},
                ]
            ],
        }

        # Execute
        summary = observability_client.get_session_summary(session_id, 1000, 2000)

        # Verify
        assert summary["session_id"] == session_id
        assert summary["spanCount"] == "10"
        assert summary["traceCount"] == "2"
        assert summary["errorCount"] == "1"

    def test_get_session_summary_empty_results(self, observability_client, mock_logs_client):
        """Test getting session summary with no results."""
        session_id = "session-123"

        # Mock empty summary query
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [],
        }

        # Execute
        summary = observability_client.get_session_summary(session_id, 1000, 2000)

        # Should return default values
        assert summary["session_id"] == session_id
        assert summary["span_count"] == 0
        assert summary["trace_count"] == 0
        assert summary["error_count"] == 0

    def test_log_group_not_found(self, observability_client, mock_logs_client):
        """Test handling of missing log group."""
        from botocore.exceptions import ClientError

        # Mock ResourceNotFoundException
        error_response = {"Error": {"Code": "ResourceNotFoundException"}}
        mock_logs_client.start_query.side_effect = ClientError(error_response, "StartQuery")
        mock_logs_client.exceptions.ResourceNotFoundException = ClientError

        # Should raise Exception with helpful message
        with pytest.raises(Exception) as exc_info:
            observability_client.query_spans_by_session("session-123", 1000, 2000)

        assert "Log group not found" in str(exc_info.value)
