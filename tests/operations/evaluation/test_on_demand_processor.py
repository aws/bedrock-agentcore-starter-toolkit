"""Comprehensive unit tests for evaluation processor.

Tests all business logic in the evaluation processor with data-driven approach.
This is the most critical module as it contains all evaluation orchestration logic.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.constants import InstrumentationScopes
from bedrock_agentcore_starter_toolkit.operations.evaluation.models import (
    EvaluationResult,
    EvaluationResults,
)
from bedrock_agentcore_starter_toolkit.operations.evaluation.on_demand_processor import (
    EvaluationProcessor,
)
from bedrock_agentcore_starter_toolkit.operations.observability.telemetry import (
    RuntimeLog,
    Span,
    TraceData,
)

# Apply mock_boto3_clients fixture to prevent real AWS calls
pytestmark = pytest.mark.usefixtures("mock_boto3_clients")

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def mock_data_plane_client():
    """Mock data plane client."""
    return MagicMock()


@pytest.fixture
def mock_control_plane_client():
    """Mock control plane client."""
    return MagicMock()


@pytest.fixture
def processor(mock_data_plane_client, mock_control_plane_client):
    """Processor instance with mocked clients."""
    return EvaluationProcessor(mock_data_plane_client, mock_control_plane_client)


@pytest.fixture
def sample_trace_data():
    """Sample trace data with spans and logs."""
    spans = [
        Span(
            trace_id="trace-123",
            span_id="span-456",
            span_name="TestSpan1",
            start_time_unix_nano=1234567890000000000,
            raw_message={
                "traceId": "trace-123",
                "spanId": "span-456",
                "name": "TestSpan1",
                "startTimeUnixNano": 1234567890000000000,
                "scope": {"name": InstrumentationScopes.OTEL_LANGCHAIN},
            },
        ),
        Span(
            trace_id="trace-123",
            span_id="span-789",
            span_name="TestSpan2",
            start_time_unix_nano=1234567891000000000,
            raw_message={
                "traceId": "trace-123",
                "spanId": "span-789",
                "name": "TestSpan2",
                "startTimeUnixNano": 1234567891000000000,
                "scope": {"name": InstrumentationScopes.STRANDS},
            },
        ),
    ]

    logs = [
        RuntimeLog(
            trace_id="trace-123",
            timestamp=1234567892000,
            message="test log message",
            raw_message={
                "traceId": "trace-123",
                "timeUnixNano": 1234567892000000000,
                "body": {"input": "test input", "output": "test output"},
            },
        )
    ]

    return TraceData(session_id="session-123", agent_id="agent-456", spans=spans, runtime_logs=logs)


# =============================================================================
# Initialization Tests
# =============================================================================


class TestInitialization:
    """Test processor initialization."""

    def test_init_with_both_clients(self, mock_data_plane_client, mock_control_plane_client):
        """Test initialization with both clients."""
        processor = EvaluationProcessor(mock_data_plane_client, mock_control_plane_client)

        assert processor.data_plane_client == mock_data_plane_client
        assert processor.control_plane_client == mock_control_plane_client

    def test_init_without_control_plane_client(self, mock_data_plane_client):
        """Test initialization without control plane client (optional)."""
        processor = EvaluationProcessor(mock_data_plane_client)

        assert processor.data_plane_client == mock_data_plane_client
        assert processor.control_plane_client is None


# =============================================================================
# Get Latest Session Tests
# =============================================================================


class TestGetLatestSession:
    """Test get_latest_session operation."""

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.on_demand_processor.ObservabilityClient")
    def test_get_latest_session_success(self, mock_obs_client_class, processor):
        """Test successful latest session retrieval."""
        mock_obs_instance = MagicMock()
        mock_obs_client_class.return_value = mock_obs_instance
        mock_obs_instance.get_latest_session_id.return_value = "session-123"

        result = processor.get_latest_session("agent-456", "us-west-2")

        assert result == "session-123"
        mock_obs_client_class.assert_called_once_with(region_name="us-west-2")
        mock_obs_instance.get_latest_session_id.assert_called_once()

    @pytest.mark.parametrize(
        "agent_id,region,error_match",
        [
            ("", "us-west-2", "agent_id is required"),
            ("  ", "us-west-2", "agent_id is required"),
            ("agent-123", "", "region is required"),
            ("agent-123", "  ", "region is required"),
        ],
    )
    def test_get_latest_session_validation(self, processor, agent_id, region, error_match):
        """Test input validation."""
        with pytest.raises(ValueError, match=error_match):
            processor.get_latest_session(agent_id, region)

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.on_demand_processor.ObservabilityClient")
    def test_get_latest_session_no_sessions(self, mock_obs_client_class, processor):
        """Test when no sessions found."""
        mock_obs_instance = MagicMock()
        mock_obs_client_class.return_value = mock_obs_instance
        mock_obs_instance.get_latest_session_id.return_value = None

        result = processor.get_latest_session("agent-456", "us-west-2")

        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.on_demand_processor.ObservabilityClient")
    def test_get_latest_session_error_handling(self, mock_obs_client_class, processor):
        """Test error handling returns None."""
        from botocore.exceptions import ClientError

        mock_obs_instance = MagicMock()
        mock_obs_client_class.return_value = mock_obs_instance
        error_response = {"Error": {"Code": "ServiceError", "Message": "API error"}}
        mock_obs_instance.get_latest_session_id.side_effect = ClientError(error_response, "get_latest_session_id")

        result = processor.get_latest_session("agent-456", "us-west-2")

        assert result is None


# =============================================================================
# Fetch Session Data Tests
# =============================================================================


class TestFetchSessionData:
    """Test fetch_session_data operation."""

    @pytest.mark.parametrize(
        "session_id,agent_id,region,error_match",
        [
            ("", "agent-123", "us-west-2", "session_id is required"),
            ("session-123", "", "us-west-2", "agent_id is required"),
            ("session-123", "agent-123", "", "region is required"),
        ],
    )
    def test_fetch_session_data_validation(self, processor, session_id, agent_id, region, error_match):
        """Test input validation."""
        with pytest.raises(ValueError, match=error_match):
            processor.fetch_session_data(session_id, agent_id, region)

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.on_demand_processor.ObservabilityClient")
    def test_fetch_session_data_success(self, mock_obs_client_class, processor):
        """Test successful session data fetch."""
        mock_obs_instance = MagicMock()
        mock_obs_client_class.return_value = mock_obs_instance

        mock_spans = [Mock(spec=Span, trace_id="trace-123")]
        mock_logs = [Mock(spec=RuntimeLog, trace_id="trace-123")]

        mock_obs_instance.query_spans_by_session.return_value = mock_spans
        mock_obs_instance.query_runtime_logs_by_traces.return_value = mock_logs

        result = processor.fetch_session_data("session-123", "agent-456", "us-west-2")

        assert isinstance(result, TraceData)
        assert result.session_id == "session-123"
        assert result.agent_id == "agent-456"
        assert result.spans == mock_spans
        assert result.runtime_logs == mock_logs

    @patch("bedrock_agentcore_starter_toolkit.operations.evaluation.on_demand_processor.ObservabilityClient")
    def test_fetch_session_data_no_spans(self, mock_obs_client_class, processor):
        """Test error when no spans found."""
        mock_obs_instance = MagicMock()
        mock_obs_client_class.return_value = mock_obs_instance
        mock_obs_instance.query_spans_by_session.return_value = []

        with pytest.raises(RuntimeError, match="No spans found"):
            processor.fetch_session_data("session-123", "agent-456", "us-west-2")


# =============================================================================
# Span Processing Tests
# =============================================================================


class TestSpanProcessing:
    """Test span processing operations."""

    def test_extract_raw_spans(self, processor, sample_trace_data):
        """Test extracting raw spans from trace data."""
        raw_spans = processor.extract_raw_spans(sample_trace_data)

        # Should have 2 spans + 1 log
        assert len(raw_spans) == 3
        assert "spanId" in raw_spans[0]  # Span
        assert "body" in raw_spans[2]  # Log

    def test_filter_relevant_spans(self, processor):
        """Test filtering to relevant spans only."""
        raw_spans = [
            # Relevant: has allowed scope
            {
                "spanId": "span-1",
                "scope": {"name": InstrumentationScopes.OTEL_LANGCHAIN},
                "startTimeUnixNano": 1234567890000000000,
            },
            # Relevant: has allowed scope
            {
                "spanId": "span-2",
                "scope": {"name": InstrumentationScopes.STRANDS},
                "startTimeUnixNano": 1234567891000000000,
            },
            # Not relevant: wrong scope
            {"spanId": "span-3", "scope": {"name": "unknown.scope"}, "startTimeUnixNano": 1234567892000000000},
            # Relevant: has conversation data
            {"timeUnixNano": 1234567893000000000, "body": {"input": "test", "output": "response"}},
            # Not relevant: no scope, no conversation data
            {"spanId": "span-4", "startTimeUnixNano": 1234567894000000000},
        ]

        relevant = processor.filter_relevant_spans(raw_spans)

        assert len(relevant) == 3
        assert relevant[0]["spanId"] == "span-1"
        assert relevant[1]["spanId"] == "span-2"
        assert "body" in relevant[2]

    @pytest.mark.parametrize(
        "scope_name,should_include",
        [
            (InstrumentationScopes.OTEL_LANGCHAIN, True),
            (InstrumentationScopes.OPENINFERENCE_LANGCHAIN, True),
            (InstrumentationScopes.STRANDS, True),
            ("unknown.scope", False),
            ("", False),
        ],
    )
    def test_filter_relevant_spans_scopes(self, processor, scope_name, should_include):
        """Test filtering with various scope names."""
        raw_spans = [{"spanId": "span-1", "scope": {"name": scope_name}, "startTimeUnixNano": 1234567890000000000}]

        relevant = processor.filter_relevant_spans(raw_spans)

        if should_include:
            assert len(relevant) == 1
        else:
            assert len(relevant) == 0

    def test_count_span_types(self, processor):
        """Test counting different span types."""
        raw_spans = [
            # Span with allowed scope
            {"spanId": "span-1", "startTimeUnixNano": 123, "scope": {"name": InstrumentationScopes.OTEL_LANGCHAIN}},
            # Span without allowed scope
            {"spanId": "span-2", "startTimeUnixNano": 124, "scope": {"name": "other"}},
            # Log
            {"body": {"input": "test"}, "timeUnixNano": 125},
        ]

        spans_count, logs_count, scoped_spans = processor.count_span_types(raw_spans)

        assert spans_count == 2
        assert logs_count == 1
        assert scoped_spans == 1


# =============================================================================
# Trace Filtering Tests
# =============================================================================


class TestTraceFiltering:
    """Test trace filtering operations."""

    def test_filter_traces_up_to(self, processor):
        """Test filtering traces up to target trace."""
        spans = [
            Span(trace_id="trace-1", span_id="span-1", span_name="Span1", start_time_unix_nano=1000000000),
            Span(trace_id="trace-2", span_id="span-2", span_name="Span2", start_time_unix_nano=2000000000),
            Span(trace_id="trace-3", span_id="span-3", span_name="Span3", start_time_unix_nano=3000000000),
        ]

        logs = [
            RuntimeLog(trace_id="trace-1", timestamp=1000, message="Log 1"),
            RuntimeLog(trace_id="trace-2", timestamp=2000, message="Log 2"),
            RuntimeLog(trace_id="trace-3", timestamp=3000, message="Log 3"),
        ]

        trace_data = TraceData(session_id="session-123", agent_id="agent-456", spans=spans, runtime_logs=logs)

        # Filter up to trace-2
        filtered = processor.filter_traces_up_to(trace_data, "trace-2")

        # Should include trace-1 and trace-2, exclude trace-3
        filtered_trace_ids = {s.trace_id for s in filtered.spans}
        assert filtered_trace_ids == {"trace-1", "trace-2"}
        assert len(filtered.runtime_logs) == 2

    def test_get_most_recent_spans(self, processor, sample_trace_data):
        """Test getting most recent relevant spans."""
        spans = processor.get_most_recent_spans(sample_trace_data, max_items=10)

        # Should have 3 items (2 spans + 1 log), most recent first
        assert len(spans) == 3
        # Check they're sorted by time (most recent first)
        times = []
        for span in spans:
            time = span.get("startTimeUnixNano") or span.get("timeUnixNano") or 0
            times.append(time)
        assert times == sorted(times, reverse=True)

    def test_get_most_recent_spans_respects_max_items(self, processor):
        """Test max_items limit is respected."""
        # Create many spans
        spans = []
        for i in range(20):
            spans.append(
                Span(
                    trace_id="trace-123",
                    span_id=f"span-{i}",
                    span_name=f"Span{i}",
                    start_time_unix_nano=1000000000 + i,
                    raw_message={
                        "spanId": f"span-{i}",
                        "startTimeUnixNano": 1000000000 + i,
                        "scope": {"name": InstrumentationScopes.OTEL_LANGCHAIN},
                    },
                )
            )

        trace_data = TraceData(session_id="session-123", agent_id="agent-456", spans=spans, runtime_logs=[])

        result = processor.get_most_recent_spans(trace_data, max_items=5)

        assert len(result) == 5


# =============================================================================
# Evaluator Execution Tests
# =============================================================================


class TestEvaluatorExecution:
    """Test evaluator execution."""

    def test_determine_spans_for_evaluator_session_level(self, processor, sample_trace_data):
        """Test span determination for SESSION level evaluator."""
        spans, target = processor.determine_spans_for_evaluator(evaluator_level="SESSION", trace_data=sample_trace_data)

        # Should return spans without specific target
        assert len(spans) > 0
        assert target is None

    def test_determine_spans_for_evaluator_trace_level_with_trace(self, processor, sample_trace_data):
        """Test span determination for TRACE level with specific trace."""
        spans, target = processor.determine_spans_for_evaluator(
            evaluator_level="TRACE", trace_data=sample_trace_data, trace_id="trace-123"
        )

        # Should return spans with trace target
        assert len(spans) > 0
        assert target == {"traceIds": ["trace-123"]}

    def test_determine_spans_for_evaluator_trace_level_without_trace(self, processor, sample_trace_data):
        """Test span determination for TRACE level without specific trace."""
        spans, target = processor.determine_spans_for_evaluator(evaluator_level="TRACE", trace_data=sample_trace_data)

        # Should return all spans without target
        assert len(spans) > 0
        assert target is None

    def test_determine_spans_for_evaluator_invalid_level(self, processor, sample_trace_data):
        """Test error with invalid evaluator level."""
        with pytest.raises(ValueError, match="Unknown evaluator level"):
            processor.determine_spans_for_evaluator(evaluator_level="INVALID", trace_data=sample_trace_data)

    def test_execute_evaluators_success(self, processor, mock_data_plane_client):
        """Test successful evaluator execution."""
        mock_data_plane_client.evaluate.return_value = {
            "evaluationResults": [
                {
                    "evaluatorId": "Builtin.Helpfulness",
                    "evaluatorName": "Helpfulness",
                    "evaluatorArn": "arn:test",
                    "explanation": "Good",
                    "context": {"spanContext": {"sessionId": "session-123"}},
                    "value": 4.5,
                }
            ]
        }

        results = processor.execute_evaluators(
            evaluators=["Builtin.Helpfulness"], otel_spans=[{"spanId": "span-123"}], session_id="session-123"
        )

        assert len(results) == 1
        assert results[0].evaluator_id == "Builtin.Helpfulness"
        assert results[0].value == 4.5

    def test_execute_evaluators_multiple(self, processor, mock_data_plane_client):
        """Test executing multiple evaluators."""
        mock_data_plane_client.evaluate.return_value = {
            "evaluationResults": [
                {
                    "evaluatorId": "Test",
                    "evaluatorName": "Test",
                    "evaluatorArn": "arn",
                    "explanation": "Good",
                    "context": {},
                }
            ]
        }

        results = processor.execute_evaluators(
            evaluators=["Builtin.Helpfulness", "Builtin.Accuracy"],
            otel_spans=[{"spanId": "span-123"}],
            session_id="session-123",
        )

        # Should have 2 results
        assert len(results) == 2
        # Should call evaluate twice
        assert mock_data_plane_client.evaluate.call_count == 2

    def test_execute_evaluators_with_error(self, processor, mock_data_plane_client):
        """Test evaluator execution with error."""
        mock_data_plane_client.evaluate.side_effect = RuntimeError("API error")

        results = processor.execute_evaluators(
            evaluators=["Builtin.Helpfulness"], otel_spans=[{"spanId": "span-123"}], session_id="session-123"
        )

        # Should return error result
        assert len(results) == 1
        assert results[0].has_error()
        assert "API error" in results[0].error

    def test_execute_evaluators_empty_results(self, processor, mock_data_plane_client):
        """Test handling empty evaluation results."""
        mock_data_plane_client.evaluate.return_value = {"evaluationResults": []}

        results = processor.execute_evaluators(
            evaluators=["Builtin.Helpfulness"], otel_spans=[{"spanId": "span-123"}], session_id="session-123"
        )

        # Should return empty list (warning logged)
        assert len(results) == 0


# =============================================================================
# Evaluate Session Tests
# =============================================================================


class TestEvaluateSession:
    """Test complete evaluate_session workflow."""

    def test_evaluate_session_validation(self, processor):
        """Test input validation."""
        with pytest.raises(ValueError, match="evaluators must be a non-empty list"):
            processor.evaluate_session(
                session_id="session-123", evaluators=[], agent_id="agent-456", region="us-west-2"
            )

    def test_evaluate_session_too_many_evaluators(self, processor):
        """Test validation fails with too many evaluators."""
        # Create a list of 21 evaluators (exceeds max of 20)
        too_many_evaluators = [f"Evaluator{i}" for i in range(21)]

        with pytest.raises(ValueError, match="Too many evaluators: 21. Maximum allowed is 20"):
            processor.evaluate_session(
                session_id="session-123", evaluators=too_many_evaluators, agent_id="agent-456", region="us-west-2"
            )

    @patch.object(EvaluationProcessor, "fetch_session_data")
    @patch.object(EvaluationProcessor, "execute_evaluators")
    def test_evaluate_session_success(self, mock_execute, mock_fetch, processor):
        """Test successful session evaluation."""
        # Mock fetch
        mock_trace_data = Mock(spec=TraceData)
        mock_trace_data.spans = [
            Mock(
                trace_id="trace-123",
                span_id="span-456",
                start_time_unix_nano=1234567890000000000,
                raw_message={
                    "spanId": "span-456",
                    "startTimeUnixNano": 1234567890000000000,
                    "scope": {"name": InstrumentationScopes.OTEL_LANGCHAIN},
                },
            )
        ]
        mock_trace_data.runtime_logs = []
        mock_fetch.return_value = mock_trace_data

        # Mock execute
        mock_result = EvaluationResult(
            evaluator_id="Builtin.Helpfulness",
            evaluator_name="Helpfulness",
            evaluator_arn="arn:test",
            explanation="Good",
            context={},
            value=4.5,
        )
        mock_execute.return_value = [mock_result]

        results = processor.evaluate_session(
            session_id="session-123", evaluators=["Builtin.Helpfulness"], agent_id="agent-456", region="us-west-2"
        )

        assert isinstance(results, EvaluationResults)
        assert results.session_id == "session-123"
        assert len(results.results) == 1

    @patch.object(EvaluationProcessor, "fetch_session_data")
    def test_evaluate_session_no_spans(self, mock_fetch, processor):
        """Test handling when no relevant spans found."""
        # Mock fetch returns trace data with no relevant spans
        mock_trace_data = Mock(spec=TraceData)
        mock_trace_data.spans = []
        mock_trace_data.runtime_logs = []
        mock_fetch.return_value = mock_trace_data

        results = processor.evaluate_session(
            session_id="session-123", evaluators=["Builtin.Helpfulness"], agent_id="agent-456", region="us-west-2"
        )

        # Should return results with no evaluations
        assert len(results.results) == 0


# =============================================================================
# Evaluator Grouping Tests
# =============================================================================


class TestEvaluatorGrouping:
    """Test evaluator grouping by level."""

    def test_group_evaluators_by_level(self, processor, mock_control_plane_client):
        """Test grouping evaluators by level."""
        # Mock control plane responses
        mock_control_plane_client.get_evaluator.side_effect = [
            {"evaluatorId": "Eval1", "level": "SESSION"},
            {"evaluatorId": "Eval2", "level": "TRACE"},
            {"evaluatorId": "Eval3", "level": "TOOL_CALL"},
        ]

        grouped = processor._group_evaluators_by_level(["Eval1", "Eval2", "Eval3"])

        assert "SESSION" in grouped
        assert "TRACE" in grouped
        assert "Eval1" in grouped["SESSION"]
        assert "Eval2" in grouped["TRACE"]
        assert "Eval3" in grouped["TRACE"]  # TOOL_CALL maps to TRACE

    def test_group_evaluators_error_defaults_to_trace(self, processor, mock_control_plane_client):
        """Test evaluator defaults to TRACE on error."""
        mock_control_plane_client.get_evaluator.side_effect = RuntimeError("API error")

        grouped = processor._group_evaluators_by_level(["Eval1"])

        # Should default to TRACE
        assert "Eval1" in grouped["TRACE"]

    def test_evaluate_session_without_control_plane_client(self, mock_data_plane_client):
        """Test evaluation workflow when control_plane_client is None."""
        # Create processor without control_plane_client
        processor = EvaluationProcessor(mock_data_plane_client, control_plane_client=None)

        # Mock the fetch_session_data to return trace data
        with patch.object(processor, "fetch_session_data") as mock_fetch:
            mock_trace_data = Mock(spec=TraceData)
            mock_trace_data.spans = [
                Mock(
                    trace_id="trace-123",
                    span_id="span-456",
                    start_time_unix_nano=1234567890000000000,
                    raw_message={
                        "spanId": "span-456",
                        "startTimeUnixNano": 1234567890000000000,
                        "scope": {"name": InstrumentationScopes.OTEL_LANGCHAIN},
                    },
                )
            ]
            mock_trace_data.runtime_logs = []
            mock_fetch.return_value = mock_trace_data

            # Mock execute_evaluators
            with patch.object(processor, "execute_evaluators") as mock_execute:
                mock_result = EvaluationResult(
                    evaluator_id="Builtin.Helpfulness",
                    evaluator_name="Helpfulness",
                    evaluator_arn="arn:test",
                    explanation="Good",
                    context={},
                    value=4.5,
                )
                mock_execute.return_value = [mock_result]

                # Run evaluation - should work without control_plane_client
                results = processor.evaluate_session(
                    session_id="session-123",
                    evaluators=["Builtin.Helpfulness"],
                    agent_id="agent-456",
                    region="us-west-2",
                )

                # Should succeed and treat all evaluators as TRACE level
                assert isinstance(results, EvaluationResults)
                assert len(results.results) == 1
                assert results.results[0].evaluator_id == "Builtin.Helpfulness"
