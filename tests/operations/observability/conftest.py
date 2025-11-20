"""Shared fixtures for observability tests."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from bedrock_agentcore_starter_toolkit.operations.observability.client import ObservabilityClient


@pytest.fixture
def mock_logs_client():
    """Mock CloudWatch Logs client."""
    from botocore.exceptions import ClientError

    mock_client = Mock()
    mock_client.start_query.return_value = {"queryId": "test-query-123"}
    mock_client.get_query_results.return_value = {
        "status": "Complete",
        "results": [],
    }

    # Mock exceptions properly
    mock_client.exceptions = Mock()
    mock_client.exceptions.ResourceNotFoundException = ClientError

    return mock_client


@pytest.fixture
def observability_client(monkeypatch, mock_logs_client):
    """Create ObservabilityClient with mocked boto3 client."""

    # Mock boto3.client to return our mock_logs_client
    def mock_boto3_client(service_name, **kwargs):
        if service_name == "logs":
            return mock_logs_client
        return Mock()

    monkeypatch.setattr("boto3.client", mock_boto3_client)

    # Create the client (stateless - only needs region)
    client = ObservabilityClient(region_name="us-east-1")
    return client


@pytest.fixture
def session_id():
    """Sample session ID for tests."""
    return "test-session-123"


@pytest.fixture
def agent_id():
    """Sample agent ID for tests."""
    return "test-agent-456"


@pytest.fixture
def trace_id():
    """Sample trace ID for tests."""
    return "test-trace-789"


@pytest.fixture
def endpoint_name():
    """Sample endpoint name for tests."""
    return "DEFAULT"


@pytest.fixture
def time_range():
    """Sample time range for queries."""
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    return {
        "start_time_ms": int(start_time.timestamp() * 1000),
        "end_time_ms": int(end_time.timestamp() * 1000),
    }


@pytest.fixture
def mock_query_response_single_span():
    """Fixture that returns a function to mock a single span query response."""

    def _mock_response(mock_logs_client):
        mock_logs_client.start_query.return_value = {"queryId": "query-123"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "traceId", "value": "test-trace-789"},
                    {"field": "spanId", "value": "span-123"},
                    {"field": "spanName", "value": "TestSpan"},
                    {"field": "startTimeUnixNano", "value": "1000000000"},
                    {"field": "endTimeUnixNano", "value": "2000000000"},
                    {"field": "durationMs", "value": "1000"},
                    {"field": "statusCode", "value": "OK"},
                    {"field": "parentSpanId", "value": ""},
                    {"field": "@message", "value": '{"traceId": "test-trace-789"}'},
                ]
            ],
        }

    return _mock_response


@pytest.fixture
def mock_query_response_empty():
    """Fixture that returns a function to mock an empty query response."""

    def _mock_response(mock_logs_client):
        mock_logs_client.start_query.return_value = {"queryId": "query-empty"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [],
        }

    return _mock_response


@pytest.fixture
def mock_query_response_runtime_logs():
    """Fixture that returns a function to mock runtime logs query response."""

    def _mock_response(mock_logs_client):
        mock_logs_client.start_query.return_value = {"queryId": "query-logs"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2024-01-01 12:00:00.000"},
                    {"field": "traceId", "value": "test-trace-789"},
                    {"field": "spanId", "value": "span-123"},
                    {
                        "field": "@message",
                        "value": '{"eventType": "invokeAgentRuntime", "input": {"text": "test input"}}',
                    },
                ]
            ],
        }

    return _mock_response
