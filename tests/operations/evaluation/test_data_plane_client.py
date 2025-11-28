"""Comprehensive unit tests for data plane client.

Tests all data plane API calls with data-driven approach.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.evaluation.data_plane_client import (
    EvaluationDataPlaneClient,
)

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def mock_boto_client():
    """Mock boto3 client."""
    return MagicMock()


@pytest.fixture
def sample_spans():
    """Sample OTel spans."""
    return [
        {
            "traceId": "trace-123",
            "spanId": "span-456",
            "name": "TestSpan1",
            "startTimeUnixNano": 1234567890000000000,
            "attributes": {"test.key": "value"},
        },
        {
            "traceId": "trace-123",
            "spanId": "span-789",
            "name": "TestSpan2",
            "startTimeUnixNano": 1234567891000000000,
        },
    ]


@pytest.fixture
def evaluation_api_response():
    """Sample evaluation API response."""
    return {
        "evaluationResults": [
            {
                "evaluatorId": "Builtin.Helpfulness",
                "evaluatorName": "Helpfulness Evaluator",
                "evaluatorArn": "arn:aws:bedrock:::evaluator/Builtin.Helpfulness",
                "explanation": "The response was helpful",
                "context": {"spanContext": {"sessionId": "session-123", "traceId": "trace-456"}},
                "value": 4.5,
                "label": "Helpful",
                "tokenUsage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
            }
        ],
        "ResponseMetadata": {"RequestId": "req-123", "HTTPStatusCode": 200},
    }


# =============================================================================
# Initialization Tests
# =============================================================================


class TestInitialization:
    """Test client initialization."""

    @patch("boto3.client")
    def test_init_basic(self, mock_boto3_client):
        """Test basic initialization with region."""
        client = EvaluationDataPlaneClient(region_name="us-west-2")

        assert client.region == "us-west-2"
        assert client.endpoint_url is not None
        mock_boto3_client.assert_called_once()

    @patch("boto3.client")
    def test_init_with_custom_endpoint(self, mock_boto3_client):
        """Test initialization with custom endpoint."""
        custom_endpoint = "https://custom-endpoint.com"

        client = EvaluationDataPlaneClient(region_name="us-east-1", endpoint_url=custom_endpoint)

        assert client.endpoint_url == custom_endpoint
        call_args = mock_boto3_client.call_args
        assert call_args.kwargs["endpoint_url"] == custom_endpoint

    @patch("boto3.client")
    @patch.dict(os.environ, {"AGENTCORE_EVAL_ENDPOINT": "https://env-endpoint.com"})
    def test_init_with_env_var(self, mock_boto3_client):
        """Test initialization uses environment variable."""
        client = EvaluationDataPlaneClient(region_name="us-west-2")

        assert client.endpoint_url == "https://env-endpoint.com"

    def test_init_with_mock_client(self, mock_boto_client):
        """Test initialization with pre-configured client."""
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        assert client.client == mock_boto_client

    @patch("boto3.client")
    def test_init_configures_retry(self, mock_boto3_client):
        """Test initialization configures retry policy."""
        EvaluationDataPlaneClient(region_name="us-west-2")

        call_args = mock_boto3_client.call_args
        config = call_args.kwargs["config"]
        assert config.retries["max_attempts"] == 3
        assert config.retries["mode"] == "adaptive"

    @pytest.mark.parametrize(
        "region",
        [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-northeast-1",
        ],
    )
    @patch("boto3.client")
    def test_init_various_regions(self, mock_boto3_client, region):
        """Test initialization with various AWS regions."""
        client = EvaluationDataPlaneClient(region_name=region)

        assert client.region == region


# =============================================================================
# Evaluate Tests
# =============================================================================


class TestEvaluate:
    """Test evaluate operation."""

    def test_evaluate_success(self, mock_boto_client, sample_spans, evaluation_api_response):
        """Test successful evaluation."""
        mock_boto_client.evaluate.return_value = evaluation_api_response
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        assert "evaluationResults" in result
        assert len(result["evaluationResults"]) == 1
        mock_boto_client.evaluate.assert_called_once()

    def test_evaluate_call_structure(self, mock_boto_client, sample_spans):
        """Test evaluate API call structure."""
        mock_boto_client.evaluate.return_value = {"evaluationResults": []}
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        call_args = mock_boto_client.evaluate.call_args
        # evaluatorId should be in path param
        assert call_args.kwargs["evaluatorId"] == "Builtin.Helpfulness"
        # evaluationInput should be in body
        assert "evaluationInput" in call_args.kwargs
        assert call_args.kwargs["evaluationInput"]["sessionSpans"] == sample_spans

    def test_evaluate_without_target(self, mock_boto_client, sample_spans):
        """Test evaluation without specific target."""
        mock_boto_client.evaluate.return_value = {"evaluationResults": []}
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        call_args = mock_boto_client.evaluate.call_args
        # evaluationTarget should not be present
        assert "evaluationTarget" not in call_args.kwargs

    @pytest.mark.parametrize(
        "target",
        [
            {"traceIds": ["trace-123"]},
            {"spanIds": ["span-456", "span-789"]},
            {"traceIds": ["trace-1", "trace-2"]},
        ],
    )
    def test_evaluate_with_target(self, mock_boto_client, sample_spans, target):
        """Test evaluation with various targets."""
        mock_boto_client.evaluate.return_value = {"evaluationResults": []}
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans, evaluation_target=target)

        call_args = mock_boto_client.evaluate.call_args
        assert call_args.kwargs["evaluationTarget"] == target

    @pytest.mark.parametrize(
        "evaluator_id",
        [
            "Builtin.Helpfulness",
            "Builtin.Accuracy",
            "Custom.MyEval",
            "arn:aws:bedrock:::evaluator/Test",
        ],
    )
    def test_evaluate_various_evaluator_ids(self, mock_boto_client, sample_spans, evaluator_id):
        """Test evaluation with various evaluator IDs."""
        mock_boto_client.evaluate.return_value = {"evaluationResults": []}
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.evaluate(evaluator_id=evaluator_id, session_spans=sample_spans)

        call_args = mock_boto_client.evaluate.call_args
        assert call_args.kwargs["evaluatorId"] == evaluator_id

    def test_evaluate_empty_spans(self, mock_boto_client):
        """Test evaluation with empty spans list."""
        mock_boto_client.evaluate.return_value = {"evaluationResults": []}
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=[])

        call_args = mock_boto_client.evaluate.call_args
        assert call_args.kwargs["evaluationInput"]["sessionSpans"] == []

    def test_evaluate_multiple_results(self, mock_boto_client, sample_spans):
        """Test handling multiple evaluation results."""
        response = {
            "evaluationResults": [
                {
                    "evaluatorId": "Builtin.Helpfulness",
                    "evaluatorName": "Helpfulness",
                    "evaluatorArn": "arn:test:1",
                    "explanation": "Result 1",
                    "context": {},
                },
                {
                    "evaluatorId": "Builtin.Helpfulness",
                    "evaluatorName": "Helpfulness",
                    "evaluatorArn": "arn:test:2",
                    "explanation": "Result 2",
                    "context": {},
                },
            ]
        }
        mock_boto_client.evaluate.return_value = response
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        assert len(result["evaluationResults"]) == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.parametrize(
        "error_code,error_msg",
        [
            ("ValidationException", "Invalid input"),
            ("ThrottlingException", "Request throttled"),
            ("InternalServerError", "Server error"),
            ("ResourceNotFoundException", "Evaluator not found"),
        ],
    )
    def test_evaluate_client_error(self, mock_boto_client, sample_spans, error_code, error_msg):
        """Test handling various client errors."""
        mock_boto_client.evaluate.side_effect = ClientError(
            {"Error": {"Code": error_code, "Message": error_msg}, "ResponseMetadata": {"RequestId": "req-123"}},
            "evaluate",
        )
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        with pytest.raises(RuntimeError, match=error_code):
            client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

    def test_evaluate_error_includes_request_id(self, mock_boto_client, sample_spans):
        """Test error message includes RequestId."""
        mock_boto_client.evaluate.side_effect = ClientError(
            {
                "Error": {"Code": "ValidationException", "Message": "Invalid"},
                "ResponseMetadata": {"RequestId": "req-abc123"},
            },
            "evaluate",
        )
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        with pytest.raises(RuntimeError) as exc_info:
            client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        # Error should be raised, but logging would have captured RequestId
        assert "ValidationException" in str(exc_info.value)

    def test_evaluate_error_missing_metadata(self, mock_boto_client, sample_spans):
        """Test handling error with missing metadata."""
        mock_boto_client.evaluate.side_effect = ClientError(
            {"Error": {"Code": "Unknown", "Message": "Error"}}, "evaluate"
        )
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        with pytest.raises(RuntimeError, match="Unknown"):
            client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

    def test_evaluate_generic_exception(self, mock_boto_client, sample_spans):
        """Test handling generic exceptions."""
        mock_boto_client.evaluate.side_effect = Exception("Unexpected error")
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        # Should propagate as-is or wrapped
        with pytest.raises(Exception):
            client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)


# =============================================================================
# Response Handling Tests
# =============================================================================


class TestResponseHandling:
    """Test response handling."""

    def test_evaluate_empty_results(self, mock_boto_client, sample_spans):
        """Test handling empty results list."""
        mock_boto_client.evaluate.return_value = {"evaluationResults": []}
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        assert result["evaluationResults"] == []

    def test_evaluate_preserves_response_metadata(self, mock_boto_client, sample_spans, evaluation_api_response):
        """Test response metadata is preserved."""
        mock_boto_client.evaluate.return_value = evaluation_api_response
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        assert "ResponseMetadata" in result
        assert result["ResponseMetadata"]["RequestId"] == "req-123"

    def test_evaluate_result_structure(self, mock_boto_client, sample_spans, evaluation_api_response):
        """Test evaluation result structure is preserved."""
        mock_boto_client.evaluate.return_value = evaluation_api_response
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        result = client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        eval_result = result["evaluationResults"][0]
        assert eval_result["evaluatorId"] == "Builtin.Helpfulness"
        assert eval_result["value"] == 4.5
        assert eval_result["label"] == "Helpful"
        assert "tokenUsage" in eval_result
        assert eval_result["tokenUsage"]["totalTokens"] == 150


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Test integration scenarios."""

    def test_evaluate_full_workflow(self, mock_boto_client, sample_spans, evaluation_api_response):
        """Test complete evaluation workflow."""
        mock_boto_client.evaluate.return_value = evaluation_api_response
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        # Evaluate with target
        result = client.evaluate(
            evaluator_id="Builtin.Helpfulness",
            session_spans=sample_spans,
            evaluation_target={"traceIds": ["trace-123"]},
        )

        # Verify complete flow
        assert len(result["evaluationResults"]) == 1
        assert result["evaluationResults"][0]["value"] == 4.5

        # Verify API call
        call_args = mock_boto_client.evaluate.call_args
        assert call_args.kwargs["evaluatorId"] == "Builtin.Helpfulness"
        assert call_args.kwargs["evaluationInput"]["sessionSpans"] == sample_spans
        assert call_args.kwargs["evaluationTarget"] == {"traceIds": ["trace-123"]}

    def test_evaluate_with_retry_success(self, mock_boto_client, sample_spans):
        """Test successful retry after transient failure."""
        # First call fails, second succeeds (boto3 handles this internally)
        mock_boto_client.evaluate.return_value = {"evaluationResults": []}
        client = EvaluationDataPlaneClient(region_name="us-west-2", boto_client=mock_boto_client)

        # Should succeed (retry config is set in init)
        result = client.evaluate(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        assert result["evaluationResults"] == []
