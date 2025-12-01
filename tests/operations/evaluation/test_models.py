"""Comprehensive unit tests for evaluation models.

Tests all data models with data-driven approach using pytest parametrize.
"""

import pytest

from bedrock_agentcore_starter_toolkit.operations.evaluation.models import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationResults,
)

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_spans():
    """Sample OTel spans for testing."""
    return [
        {
            "traceId": "trace-123",
            "spanId": "span-456",
            "name": "TestSpan1",
            "startTimeUnixNano": 1234567890000000000,
        },
        {
            "traceId": "trace-123",
            "spanId": "span-789",
            "name": "TestSpan2",
            "startTimeUnixNano": 1234567891000000000,
        },
    ]


@pytest.fixture
def sample_api_response():
    """Sample API response for evaluation result."""
    return {
        "evaluatorId": "Builtin.Helpfulness",
        "evaluatorName": "Helpfulness Evaluator",
        "evaluatorArn": "arn:aws:bedrock-agentcore:::evaluator/Builtin.Helpfulness",
        "explanation": "The response was helpful and addressed the question",
        "context": {"spanContext": {"sessionId": "session-123", "traceId": "trace-456", "spanId": "span-789"}},
        "value": 4.5,
        "label": "Helpful",
        "tokenUsage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
    }


# =============================================================================
# EvaluationRequest Tests
# =============================================================================


class TestEvaluationRequest:
    """Test EvaluationRequest model."""

    def test_init_basic(self, sample_spans):
        """Test basic initialization."""
        request = EvaluationRequest(evaluator_id="Builtin.Helpfulness", session_spans=sample_spans)

        assert request.evaluator_id == "Builtin.Helpfulness"
        assert request.session_spans == sample_spans
        assert request.evaluation_target is None

    def test_init_with_target(self, sample_spans):
        """Test initialization with evaluation target."""
        target = {"traceIds": ["trace-123"]}
        request = EvaluationRequest(
            evaluator_id="Builtin.Accuracy", session_spans=sample_spans, evaluation_target=target
        )

        assert request.evaluation_target == target

    @pytest.mark.parametrize(
        "evaluator_id,expected_id",
        [
            ("Builtin.Helpfulness", "Builtin.Helpfulness"),
            ("Custom.MyEvaluator", "Custom.MyEvaluator"),
            ("arn:aws:bedrock::evaluator/Test", "arn:aws:bedrock::evaluator/Test"),
        ],
    )
    def test_to_api_request_without_target(self, evaluator_id, expected_id, sample_spans):
        """Test converting to API request format without target."""
        request = EvaluationRequest(evaluator_id=evaluator_id, session_spans=sample_spans)

        api_evaluator_id, api_body = request.to_api_request()

        assert api_evaluator_id == expected_id
        assert "evaluationInput" in api_body
        assert api_body["evaluationInput"]["sessionSpans"] == sample_spans
        assert "evaluationTarget" not in api_body

    @pytest.mark.parametrize(
        "target",
        [
            {"traceIds": ["trace-123"]},
            {"spanIds": ["span-456", "span-789"]},
            {"traceIds": ["trace-1", "trace-2"], "spanIds": ["span-1"]},
        ],
    )
    def test_to_api_request_with_target(self, target, sample_spans):
        """Test converting to API request format with various targets."""
        request = EvaluationRequest(
            evaluator_id="Builtin.Helpfulness", session_spans=sample_spans, evaluation_target=target
        )

        _, api_body = request.to_api_request()

        assert "evaluationTarget" in api_body
        assert api_body["evaluationTarget"] == target

    def test_to_api_request_empty_spans(self):
        """Test API request with empty spans list."""
        request = EvaluationRequest(evaluator_id="Builtin.Helpfulness", session_spans=[])

        _, api_body = request.to_api_request()

        assert api_body["evaluationInput"]["sessionSpans"] == []


# =============================================================================
# EvaluationResult Tests
# =============================================================================


class TestEvaluationResult:
    """Test EvaluationResult model."""

    def test_init_basic(self):
        """Test basic initialization."""
        result = EvaluationResult(
            evaluator_id="Builtin.Helpfulness",
            evaluator_name="Helpfulness",
            evaluator_arn="arn:aws:bedrock:::evaluator/Builtin.Helpfulness",
            explanation="Good response",
            context={"spanContext": {"sessionId": "session-123"}},
        )

        assert result.evaluator_id == "Builtin.Helpfulness"
        assert result.evaluator_name == "Helpfulness"
        assert result.value is None
        assert result.label is None
        assert result.error is None

    def test_init_with_all_fields(self):
        """Test initialization with all optional fields."""
        result = EvaluationResult(
            evaluator_id="Builtin.Accuracy",
            evaluator_name="Accuracy",
            evaluator_arn="arn:aws:bedrock:::evaluator/Builtin.Accuracy",
            explanation="Highly accurate",
            context={"spanContext": {"sessionId": "session-456"}},
            value=4.8,
            label="Accurate",
            token_usage={"inputTokens": 200, "outputTokens": 100, "totalTokens": 300},
        )

        assert result.value == 4.8
        assert result.label == "Accurate"
        assert result.token_usage["totalTokens"] == 300

    @pytest.mark.parametrize(
        "api_response,expected_id,expected_value,expected_label",
        [
            (
                {
                    "evaluatorId": "Builtin.Helpfulness",
                    "evaluatorName": "Helpfulness",
                    "evaluatorArn": "arn:aws:bedrock:::evaluator/Builtin.Helpfulness",
                    "explanation": "Good",
                    "context": {},
                    "value": 4.5,
                    "label": "Helpful",
                },
                "Builtin.Helpfulness",
                4.5,
                "Helpful",
            ),
            (
                {
                    "evaluatorId": "Custom.MyEval",
                    "evaluatorName": "My Evaluator",
                    "evaluatorArn": "arn:aws:bedrock:::evaluator/Custom.MyEval",
                    "explanation": "Custom evaluation",
                    "context": {},
                    "value": 3.2,
                },
                "Custom.MyEval",
                3.2,
                None,
            ),
            (
                {
                    "evaluatorId": "Builtin.Accuracy",
                    "evaluatorName": "Accuracy",
                    "evaluatorArn": "arn:aws:bedrock:::evaluator/Builtin.Accuracy",
                    "explanation": "Accurate",
                    "context": {},
                    "label": "Yes",
                },
                "Builtin.Accuracy",
                None,
                "Yes",
            ),
        ],
    )
    def test_from_api_response(self, api_response, expected_id, expected_value, expected_label):
        """Test creating result from various API responses."""
        result = EvaluationResult.from_api_response(api_response)

        assert result.evaluator_id == expected_id
        assert result.value == expected_value
        assert result.label == expected_label

    def test_from_api_response_with_token_usage(self, sample_api_response):
        """Test parsing token usage from API response."""
        result = EvaluationResult.from_api_response(sample_api_response)

        assert result.token_usage is not None
        assert result.token_usage["inputTokens"] == 100
        assert result.token_usage["outputTokens"] == 50
        assert result.token_usage["totalTokens"] == 150

    def test_from_api_response_missing_fields(self):
        """Test handling API response with missing fields."""
        minimal_response = {
            "evaluatorId": "Test.Eval",
        }

        result = EvaluationResult.from_api_response(minimal_response)

        assert result.evaluator_id == "Test.Eval"
        assert result.evaluator_name == ""
        assert result.evaluator_arn == ""
        assert result.explanation == ""
        assert result.context == {}
        assert result.value is None
        assert result.label is None

    def test_from_api_response_with_error(self):
        """Test parsing API response with error."""
        error_response = {
            "evaluatorId": "Builtin.Helpfulness",
            "evaluatorName": "Helpfulness",
            "evaluatorArn": "arn:aws:bedrock:::evaluator/Builtin.Helpfulness",
            "explanation": "Evaluation failed",
            "context": {},
            "error": "Timeout exceeded",
        }

        result = EvaluationResult.from_api_response(error_response)

        assert result.error == "Timeout exceeded"
        assert result.has_error() is True

    @pytest.mark.parametrize(
        "error_value,expected",
        [
            (None, False),
            ("", True),  # Empty string is still an error
            ("Timeout", True),
            ("API error", True),
        ],
    )
    def test_has_error(self, error_value, expected):
        """Test error detection."""
        result = EvaluationResult(
            evaluator_id="Test",
            evaluator_name="Test",
            evaluator_arn="arn:test",
            explanation="Test",
            context={},
            error=error_value,
        )

        assert result.has_error() == expected


# =============================================================================
# EvaluationResults Tests
# =============================================================================


class TestEvaluationResults:
    """Test EvaluationResults container."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        results = EvaluationResults()

        assert results.session_id is None
        assert results.trace_id is None
        assert results.results == []
        assert results.input_data is None

    def test_init_with_ids(self):
        """Test initialization with session and trace IDs."""
        results = EvaluationResults(session_id="session-123", trace_id="trace-456")

        assert results.session_id == "session-123"
        assert results.trace_id == "trace-456"

    def test_add_result(self):
        """Test adding a single result."""
        results = EvaluationResults()
        result = EvaluationResult(
            evaluator_id="Builtin.Helpfulness",
            evaluator_name="Helpfulness",
            evaluator_arn="arn:test",
            explanation="Good",
            context={},
        )

        results.add_result(result)

        assert len(results.results) == 1
        assert results.results[0].evaluator_id == "Builtin.Helpfulness"

    def test_add_multiple_results(self):
        """Test adding multiple results."""
        results = EvaluationResults()

        for i in range(3):
            result = EvaluationResult(
                evaluator_id=f"Eval.{i}",
                evaluator_name=f"Evaluator {i}",
                evaluator_arn=f"arn:eval:{i}",
                explanation=f"Result {i}",
                context={},
            )
            results.add_result(result)

        assert len(results.results) == 3

    @pytest.mark.parametrize(
        "results_data,expected_has_errors",
        [
            ([], False),  # Empty results
            ([{"error": None}], False),  # Single success
            ([{"error": None}, {"error": None}], False),  # All success
            ([{"error": "Failed"}], True),  # Single error
            ([{"error": None}, {"error": "Failed"}], True),  # Mixed
            ([{"error": "E1"}, {"error": "E2"}], True),  # All errors
        ],
    )
    def test_has_errors(self, results_data, expected_has_errors):
        """Test error detection with various result combinations."""
        results = EvaluationResults()

        for i, data in enumerate(results_data):
            result = EvaluationResult(
                evaluator_id=f"Eval.{i}",
                evaluator_name=f"Name.{i}",
                evaluator_arn=f"arn:{i}",
                explanation="Test",
                context={},
                error=data.get("error"),
            )
            results.add_result(result)

        assert results.has_errors() == expected_has_errors

    def test_get_successful_results(self):
        """Test filtering successful results."""
        results = EvaluationResults()

        # Add successful results
        for i in range(2):
            results.add_result(
                EvaluationResult(
                    evaluator_id=f"Success.{i}",
                    evaluator_name=f"Success {i}",
                    evaluator_arn=f"arn:success:{i}",
                    explanation="Good",
                    context={},
                    value=4.0,
                )
            )

        # Add failed result
        results.add_result(
            EvaluationResult(
                evaluator_id="Failed.0",
                evaluator_name="Failed",
                evaluator_arn="arn:failed:0",
                explanation="Bad",
                context={},
                error="API error",
            )
        )

        successful = results.get_successful_results()

        assert len(successful) == 2
        assert all("Success" in r.evaluator_id for r in successful)

    def test_get_failed_results(self):
        """Test filtering failed results."""
        results = EvaluationResults()

        # Add successful result
        results.add_result(
            EvaluationResult(
                evaluator_id="Success.0",
                evaluator_name="Success",
                evaluator_arn="arn:success:0",
                explanation="Good",
                context={},
                value=4.0,
            )
        )

        # Add failed results
        for i in range(2):
            results.add_result(
                EvaluationResult(
                    evaluator_id=f"Failed.{i}",
                    evaluator_name=f"Failed {i}",
                    evaluator_arn=f"arn:failed:{i}",
                    explanation="Bad",
                    context={},
                    error=f"Error {i}",
                )
            )

        failed = results.get_failed_results()

        assert len(failed) == 2
        assert all("Failed" in r.evaluator_id for r in failed)

    def test_to_dict_basic(self):
        """Test converting to dictionary."""
        results = EvaluationResults(session_id="session-123")
        results.add_result(
            EvaluationResult(
                evaluator_id="Builtin.Helpfulness",
                evaluator_name="Helpfulness",
                evaluator_arn="arn:test",
                explanation="Good response",
                context={"spanContext": {"sessionId": "session-123"}},
                value=4.5,
                label="Helpful",
            )
        )

        result_dict = results.to_dict()

        assert result_dict["session_id"] == "session-123"
        assert result_dict["trace_id"] is None
        assert result_dict["summary"]["total_evaluations"] == 1
        assert result_dict["summary"]["successful"] == 1
        assert result_dict["summary"]["failed"] == 0
        assert len(result_dict["results"]) == 1

    def test_to_dict_with_summary(self):
        """Test dictionary summary statistics."""
        results = EvaluationResults()

        # Add 3 successful
        for i in range(3):
            results.add_result(
                EvaluationResult(
                    evaluator_id=f"Success.{i}",
                    evaluator_name=f"Success {i}",
                    evaluator_arn=f"arn:success:{i}",
                    explanation="Good",
                    context={},
                    value=4.0,
                )
            )

        # Add 2 failed
        for i in range(2):
            results.add_result(
                EvaluationResult(
                    evaluator_id=f"Failed.{i}",
                    evaluator_name=f"Failed {i}",
                    evaluator_arn=f"arn:failed:{i}",
                    explanation="Bad",
                    context={},
                    error=f"Error {i}",
                )
            )

        result_dict = results.to_dict()
        summary = result_dict["summary"]

        assert summary["total_evaluations"] == 5
        assert summary["successful"] == 3
        assert summary["failed"] == 2

    def test_to_dict_with_input_data(self):
        """Test dictionary includes input data when present."""
        results = EvaluationResults()
        input_spans = [{"traceId": "trace-123", "spanId": "span-456"}]
        results.input_data = {"spans": input_spans}

        result_dict = results.to_dict()

        assert "input_data" in result_dict
        assert result_dict["input_data"]["spans"] == input_spans

    def test_to_dict_without_input_data(self):
        """Test dictionary excludes input data when None."""
        results = EvaluationResults()

        result_dict = results.to_dict()

        assert "input_data" not in result_dict

    def test_to_dict_result_fields(self):
        """Test all result fields are included in dictionary."""
        results = EvaluationResults()
        results.add_result(
            EvaluationResult(
                evaluator_id="Builtin.Helpfulness",
                evaluator_name="Helpfulness Eval",
                evaluator_arn="arn:aws:bedrock:::evaluator/Builtin.Helpfulness",
                explanation="Very helpful response",
                context={"spanContext": {"sessionId": "session-123"}},
                value=4.7,
                label="Helpful",
                token_usage={"inputTokens": 150, "outputTokens": 75, "totalTokens": 225},
            )
        )

        result_dict = results.to_dict()
        result = result_dict["results"][0]

        assert result["evaluator_id"] == "Builtin.Helpfulness"
        assert result["evaluator_name"] == "Helpfulness Eval"
        assert result["evaluator_arn"] == "arn:aws:bedrock:::evaluator/Builtin.Helpfulness"
        assert result["value"] == 4.7
        assert result["label"] == "Helpful"
        assert result["explanation"] == "Very helpful response"
        assert result["context"] == {"spanContext": {"sessionId": "session-123"}}
        assert result["token_usage"]["totalTokens"] == 225
        assert result["error"] is None
