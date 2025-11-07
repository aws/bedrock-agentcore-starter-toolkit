"""Integration tests for evaluation client."""

from unittest.mock import MagicMock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.evaluation.client import EvaluationClient
from bedrock_agentcore_starter_toolkit.operations.evaluation.models.evaluation import (
    EvaluationResult,
    EvaluationResults,
)
from bedrock_agentcore_starter_toolkit.operations.observability.models.telemetry import (
    Span,
    TraceData,
)


class TestEvaluationClient:
    """Test EvaluationClient class."""

    def test_client_init_defaults(self):
        """Test client initialization with defaults."""
        with patch("boto3.client"):
            client = EvaluationClient()

            assert client.region == "us-west-2"
            assert client.endpoint_url == EvaluationClient.DEFAULT_ENDPOINT

    def test_client_init_with_env_vars(self):
        """Test client initialization with environment variables."""
        with patch("boto3.client"), patch("os.getenv") as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: {
                "AGENTCORE_EVAL_REGION": "us-east-1",
                "AGENTCORE_EVAL_ENDPOINT": "https://custom-endpoint",
            }.get(key, default)

            client = EvaluationClient()

            assert client.region == "us-east-1"
            assert client.endpoint_url == "https://custom-endpoint"

    def test_client_init_with_args(self):
        """Test client initialization with explicit arguments."""
        with patch("boto3.client"):
            client = EvaluationClient(region="eu-west-1", endpoint_url="https://eu-endpoint")

            assert client.region == "eu-west-1"
            assert client.endpoint_url == "https://eu-endpoint"

    def test_evaluate_success(self):
        """Test successful evaluation call."""
        mock_boto_client = MagicMock()
        mock_boto_client.evaluate.return_value = {
            "evaluationResults": [
                {
                    "evaluatorId": "Builtin.Helpfulness",
                    "evaluatorName": "Builtin.Helpfulness",
                    "evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
                    "explanation": "The response was helpful",
                    "context": {"spanContext": {"sessionId": "session-123"}},
                    "value": 4.5,
                    "label": "Helpful",
                }
            ]
        }

        client = EvaluationClient(boto_client=mock_boto_client)

        session_spans = [
            {
                "traceId": "trace-123",
                "spanId": "span-456",
                "name": "TestSpan",
            }
        ]

        response = client.evaluate("Builtin.Helpfulness", session_spans)

        assert "evaluationResults" in response
        assert len(response["evaluationResults"]) == 1
        mock_boto_client.evaluate.assert_called_once()

    def test_evaluate_api_error(self):
        """Test evaluation with API error."""
        from botocore.exceptions import ClientError

        mock_boto_client = MagicMock()
        mock_boto_client.evaluate.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid input"}},
            "evaluate",
        )

        client = EvaluationClient(boto_client=mock_boto_client)

        session_spans = [{"traceId": "trace-123", "spanId": "span-456", "name": "TestSpan"}]

        with pytest.raises(RuntimeError, match="Evaluation API error"):
            client.evaluate("Builtin.Helpfulness", session_spans)

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.client.ObservabilityClient")
    def test_evaluate_session_success(self, mock_obs_client_class):
        """Test successful session evaluation."""
        # Mock ObservabilityClient instance
        mock_obs_instance = MagicMock()
        mock_obs_client_class.return_value = mock_obs_instance

        # Mock trace data
        mock_obs_instance.get_session_data.return_value = TraceData(
            session_id="session-123",
            spans=[
                Span(
                    trace_id="trace-1",
                    span_id="span-1",
                    span_name="TestSpan",
                )
            ],
        )

        # Mock evaluation API response
        mock_boto_client = MagicMock()
        mock_boto_client.evaluate.return_value = {
            "evaluationResults": [
                {
                    "evaluatorId": "Builtin.Helpfulness",
                    "evaluatorName": "Builtin.Helpfulness",
                    "evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
                    "explanation": "Success",
                    "context": {"spanContext": {"sessionId": "session-123"}},
                    "value": 4.0,
                }
            ]
        }

        client = EvaluationClient(boto_client=mock_boto_client)

        results = client.evaluate_session(
            session_id="session-123", evaluators=["Builtin.Helpfulness"], agent_id="agent-456", region="us-west-2"
        )

        assert results.session_id == "session-123"
        assert len(results.results) == 1
        assert results.results[0].evaluator_id == "Builtin.Helpfulness"

        # Verify ObservabilityClient was created with correct params
        mock_obs_client_class.assert_called_once_with(
            region_name="us-west-2", agent_id="agent-456", runtime_suffix="DEFAULT"
        )

        # Verify get_session_data was called with correct params
        assert mock_obs_instance.get_session_data.called
        call_args = mock_obs_instance.get_session_data.call_args
        assert call_args.kwargs["session_id"] == "session-123"
        assert "start_time_ms" in call_args.kwargs
        assert "end_time_ms" in call_args.kwargs
        assert call_args.kwargs["include_runtime_logs"] is True


class TestEvaluationResults:
    """Test EvaluationResults model."""

    def test_evaluation_results_init(self):
        """Test initializing evaluation results."""
        results = EvaluationResults(session_id="session-123")

        assert results.session_id == "session-123"
        assert results.results == []

    def test_add_result(self):
        """Test adding results."""
        results = EvaluationResults()
        result = EvaluationResult(
            evaluator_id="Builtin.Helpfulness",
            evaluator_name="Builtin.Helpfulness",
            evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
            explanation="Helpful",
            context={},
            value=4.5,
        )

        results.add_result(result)

        assert len(results.results) == 1
        assert results.results[0].evaluator_id == "Builtin.Helpfulness"

    def test_has_errors(self):
        """Test checking for errors."""
        results = EvaluationResults()

        # No errors initially
        assert results.has_errors() is False

        # Add successful result
        results.add_result(
            EvaluationResult(
                evaluator_id="Builtin.Helpfulness",
                evaluator_name="Builtin.Helpfulness",
                evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
                explanation="Good",
                context={},
                value=4.0,
            )
        )
        assert results.has_errors() is False

        # Add failed result
        results.add_result(
            EvaluationResult(
                evaluator_id="Builtin.Accuracy",
                evaluator_name="Builtin.Accuracy",
                evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Accuracy",
                explanation="Failed",
                context={},
                error="API error",
            )
        )
        assert results.has_errors() is True

    def test_get_successful_and_failed_results(self):
        """Test filtering successful and failed results."""
        results = EvaluationResults()

        # Add mixed results
        results.add_result(
            EvaluationResult(
                evaluator_id="Builtin.Helpfulness",
                evaluator_name="Builtin.Helpfulness",
                evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
                explanation="Good",
                context={},
                value=4.0,
            )
        )
        results.add_result(
            EvaluationResult(
                evaluator_id="Builtin.Accuracy",
                evaluator_name="Builtin.Accuracy",
                evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Accuracy",
                explanation="Failed",
                context={},
                error="API error",
            )
        )

        successful = results.get_successful_results()
        failed = results.get_failed_results()

        assert len(successful) == 1
        assert len(failed) == 1
        assert successful[0].evaluator_id == "Builtin.Helpfulness"
        assert failed[0].evaluator_id == "Builtin.Accuracy"

    def test_to_dict(self):
        """Test converting results to dictionary."""
        results = EvaluationResults(session_id="session-123")
        results.add_result(
            EvaluationResult(
                evaluator_id="Builtin.Helpfulness",
                evaluator_name="Builtin.Helpfulness",
                evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
                explanation="Helpful",
                context={"session.id": "session-123"},
                value=4.5,
                label="Helpful",
            )
        )

        result_dict = results.to_dict()

        assert result_dict["session_id"] == "session-123"
        assert len(result_dict["results"]) == 1
        assert result_dict["results"][0]["evaluator_id"] == "Builtin.Helpfulness"
        assert result_dict["results"][0]["value"] == 4.5


class TestEvaluationResult:
    """Test EvaluationResult model."""

    def test_from_api_response(self):
        """Test creating result from API response."""
        api_response = {
            "evaluatorId": "Builtin.Helpfulness",
            "evaluatorName": "Builtin.Helpfulness",
            "evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
            "explanation": "The response was very helpful",
            "context": {"spanContext": {"sessionId": "session-123"}},
            "value": 4.5,
            "label": "Helpful",
            "tokenUsage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
        }

        result = EvaluationResult.from_api_response(api_response)

        assert result.evaluator_id == "Builtin.Helpfulness"
        assert result.evaluator_name == "Builtin.Helpfulness"
        assert result.evaluator_arn == "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness"
        assert result.explanation == "The response was very helpful"
        assert result.value == 4.5
        assert result.label == "Helpful"
        assert result.token_usage["inputTokens"] == 100

    def test_has_error(self):
        """Test checking if result has error."""
        # Successful result
        result = EvaluationResult(
            evaluator_id="Builtin.Helpfulness",
            evaluator_name="Builtin.Helpfulness",
            evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
            explanation="Good",
            context={},
            value=4.0,
        )
        assert result.has_error() is False

        # Failed result
        result_with_error = EvaluationResult(
            evaluator_id="Builtin.Accuracy",
            evaluator_name="Builtin.Accuracy",
            evaluator_arn="arn:aws:bedrock-agentcore:::evaluator/Builtin.Accuracy",
            explanation="Failed",
            context={},
            error="API error",
        )
        assert result_with_error.has_error() is True
