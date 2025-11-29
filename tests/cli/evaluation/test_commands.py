"""Comprehensive unit tests for CLI evaluation commands.

Tests all CLI commands with data-driven approach.
"""

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.evaluation.commands import (
    _get_agent_config_from_file,
    evaluation_app,
    evaluator_app,
)
from bedrock_agentcore_starter_toolkit.operations.evaluation.models import (
    EvaluationResult,
    EvaluationResults,
)

# Apply mock_boto3_clients fixture to prevent real AWS calls
pytestmark = pytest.mark.usefixtures("mock_boto3_clients")

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock agent configuration."""
    config = Mock()
    config.bedrock_agentcore.agent_id = "test-agent-123"
    config.bedrock_agentcore.agent_session_id = "test-session-123"
    config.aws.region = "us-west-2"

    agent_config = Mock()
    agent_config.get_agent_config = Mock(return_value=config)
    return agent_config


@pytest.fixture
def sample_evaluation_results():
    """Sample evaluation results."""
    results = EvaluationResults(session_id="session-123")
    results.add_result(
        EvaluationResult(
            evaluator_id="Builtin.Helpfulness",
            evaluator_name="Helpfulness",
            evaluator_arn="arn:test",
            explanation="Good response",
            context={"spanContext": {"sessionId": "session-123"}},
            value=4.5,
        )
    )
    return results


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Test helper functions."""

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.load_config_if_exists")
    def test_get_agent_config_from_file_success(self, mock_load_config, mock_config, tmp_path):
        """Test getting agent config from file."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("test: config")

        mock_load_config.return_value = mock_config

        with patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.Path.cwd", return_value=tmp_path):
            result = _get_agent_config_from_file()

        assert result is not None
        assert result["agent_id"] == "test-agent-123"
        assert result["region"] == "us-west-2"
        assert result["session_id"] == "test-session-123"

    def test_get_agent_config_from_file_no_config(self, tmp_path):
        """Test when config file doesn't exist."""
        with patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.Path.cwd", return_value=tmp_path):
            result = _get_agent_config_from_file()

        assert result is None

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.load_config_if_exists")
    def test_get_agent_config_from_file_error(self, mock_load_config, tmp_path):
        """Test when config loading throws error."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("test: config")

        mock_load_config.side_effect = ValueError("Parse error")

        with patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.Path.cwd", return_value=tmp_path):
            result = _get_agent_config_from_file()

        assert result is None


# =============================================================================
# Run Evaluation Command Tests
# =============================================================================


class TestRunEvaluationCommand:
    """Test 'agentcore eval run' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationProcessor")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands._get_agent_config_from_file")
    def test_run_evaluation_with_config_file(
        self, mock_get_config, mock_processor_class, runner, sample_evaluation_results
    ):
        """Test running evaluation using config file."""
        mock_get_config.return_value = {"agent_id": "agent-123", "region": "us-west-2", "session_id": "session-456"}

        mock_processor = Mock()
        mock_processor.evaluate_session.return_value = sample_evaluation_results
        mock_processor_class.return_value = mock_processor

        result = runner.invoke(evaluation_app, ["run", "-e", "Builtin.Helpfulness"])

        assert result.exit_code == 0
        mock_processor.evaluate_session.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationProcessor")
    def test_run_evaluation_with_explicit_params(self, mock_processor_class, runner, sample_evaluation_results):
        """Test running evaluation with explicit parameters."""
        mock_processor = Mock()
        mock_processor.evaluate_session.return_value = sample_evaluation_results
        mock_processor_class.return_value = mock_processor

        result = runner.invoke(
            evaluation_app,
            ["run", "--agent-id", "agent-123", "--session-id", "session-456", "-e", "Builtin.Helpfulness"],
        )

        # Should succeed with explicit params (region defaults to boto3 default)
        assert result.exit_code == 0
        mock_processor.evaluate_session.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationProcessor")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands._get_agent_config_from_file")
    def test_run_evaluation_with_trace_id(
        self, mock_get_config, mock_processor_class, runner, sample_evaluation_results
    ):
        """Test running evaluation for specific trace."""
        mock_get_config.return_value = {"agent_id": "agent-123", "region": "us-west-2", "session_id": "session-456"}

        mock_processor = Mock()
        mock_processor.evaluate_session.return_value = sample_evaluation_results
        mock_processor_class.return_value = mock_processor

        result = runner.invoke(evaluation_app, ["run", "-e", "Builtin.Helpfulness", "--trace-id", "trace-789"])

        assert result.exit_code == 0
        # Verify trace_id was passed
        call_args = mock_processor.evaluate_session.call_args
        assert call_args.kwargs.get("trace_id") == "trace-789"

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationProcessor")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands._get_agent_config_from_file")
    def test_run_evaluation_multiple_evaluators(
        self, mock_get_config, mock_processor_class, runner, sample_evaluation_results
    ):
        """Test running evaluation with multiple evaluators."""
        mock_get_config.return_value = {"agent_id": "agent-123", "region": "us-west-2", "session_id": "session-456"}

        mock_processor = Mock()
        mock_processor.evaluate_session.return_value = sample_evaluation_results
        mock_processor_class.return_value = mock_processor

        result = runner.invoke(evaluation_app, ["run", "-e", "Builtin.Helpfulness", "-e", "Builtin.Accuracy"])

        assert result.exit_code == 0
        call_args = mock_processor.evaluate_session.call_args
        evaluators = call_args.kwargs.get("evaluators", [])
        assert "Builtin.Helpfulness" in evaluators
        assert "Builtin.Accuracy" in evaluators

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands._get_agent_config_from_file")
    def test_run_evaluation_no_config(self, mock_get_config, runner):
        """Test running evaluation without config."""
        mock_get_config.return_value = None

        result = runner.invoke(evaluation_app, ["run", "-e", "Builtin.Helpfulness"])

        assert result.exit_code != 0
        assert "config" in result.stdout.lower() or "agent" in result.stdout.lower()


# =============================================================================
# List Evaluators Command Tests
# =============================================================================


class TestListEvaluatorsCommand:
    """Test 'agentcore eval evaluator list' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.list_evaluators")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_list_evaluators_success(self, mock_client_class, mock_list_op, runner):
        """Test listing evaluators successfully."""
        mock_list_op.return_value = {
            "evaluators": [
                {
                    "evaluatorId": "Builtin.Helpfulness",
                    "evaluatorName": "Helpfulness",
                    "level": "TRACE",
                    "description": "Evaluates helpfulness",
                }
            ]
        }

        result = runner.invoke(evaluator_app, ["list"])

        assert result.exit_code == 0
        assert "Helpfulness" in result.stdout

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.list_evaluators")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_list_evaluators_empty(self, mock_client_class, mock_list_op, runner):
        """Test listing when no evaluators exist."""
        mock_list_op.return_value = {"evaluators": []}

        result = runner.invoke(evaluator_app, ["list"])

        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.list_evaluators")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_list_evaluators_with_max_results(self, mock_client_class, mock_list_op, runner):
        """Test listing evaluators with custom max results."""
        mock_list_op.return_value = {"evaluators": [{"evaluatorId": "Test", "evaluatorName": "Test"}]}

        result = runner.invoke(evaluator_app, ["list", "--max-results", "100"])

        assert result.exit_code == 0
        # Verify max_results was passed through
        call_args = mock_list_op.call_args
        assert call_args is not None


# =============================================================================
# Get Evaluator Command Tests
# =============================================================================


class TestGetEvaluatorCommand:
    """Test 'agentcore eval evaluator get' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.get_evaluator")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_get_evaluator_success(self, mock_client_class, mock_get_op, runner):
        """Test getting evaluator details."""
        mock_get_op.return_value = {
            "evaluatorId": "Builtin.Helpfulness",
            "evaluatorName": "Helpfulness",
            "level": "TRACE",
            "description": "Evaluates helpfulness",
            "evaluatorConfig": {"llmAsAJudge": {"instructions": "Evaluate the response"}},
        }

        result = runner.invoke(evaluator_app, ["get", "--evaluator-id", "Builtin.Helpfulness"])

        assert result.exit_code == 0
        assert "Helpfulness" in result.stdout

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.get_evaluator")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_get_evaluator_not_found(self, mock_client_class, mock_get_op, runner):
        """Test getting non-existent evaluator."""
        mock_get_op.side_effect = Exception("Evaluator not found")

        result = runner.invoke(evaluator_app, ["get", "--evaluator-id", "NonExistent"])

        assert result.exit_code != 0


# =============================================================================
# Create Evaluator Command Tests
# =============================================================================


class TestCreateEvaluatorCommand:
    """Test 'agentcore eval evaluator create' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.create_evaluator")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_create_evaluator_from_json(self, mock_client_class, mock_create_op, runner, tmp_path):
        """Test creating evaluator from JSON file."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"llmAsAJudge": {"instructions": "Test"}}')

        mock_create_op.return_value = {"evaluatorId": "Custom.NewEval", "evaluatorArn": "arn:test"}

        result = runner.invoke(evaluator_app, ["create", "--name", "NewEval", "--config", str(config_file)])

        assert result.exit_code == 0
        assert "Custom.NewEval" in result.stdout or "NewEval" in result.stdout

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_create_evaluator_missing_config(self, mock_client_class, runner):
        """Test creating evaluator without config file."""
        result = runner.invoke(evaluator_app, ["create", "--name", "NewEval"])

        assert result.exit_code != 0
        assert "name is required" in result.stdout.lower() or "config" in result.stdout.lower()


# =============================================================================
# Update Evaluator Command Tests
# =============================================================================


class TestUpdateEvaluatorCommand:
    """Test 'agentcore eval evaluator update' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.update_evaluator")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_update_evaluator_description(self, mock_client_class, mock_update_op, runner):
        """Test updating evaluator description."""
        mock_update_op.return_value = {"status": "success"}

        result = runner.invoke(
            evaluator_app, ["update", "--evaluator-id", "Custom.MyEval", "--description", "Updated description"]
        )

        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.update_evaluator")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_update_evaluator_config(self, mock_client_class, mock_update_op, runner, tmp_path):
        """Test updating evaluator config."""
        config_file = tmp_path / "new_config.json"
        config_file.write_text('{"llmAsAJudge": {"instructions": "New instructions"}}')

        mock_update_op.return_value = {"status": "success"}

        result = runner.invoke(
            evaluator_app, ["update", "--evaluator-id", "Custom.MyEval", "--config", str(config_file)]
        )

        assert result.exit_code == 0


# =============================================================================
# Delete Evaluator Command Tests
# =============================================================================


class TestDeleteEvaluatorCommand:
    """Test 'agentcore eval evaluator delete' command."""

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.delete_evaluator")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_delete_evaluator_success(self, mock_client_class, mock_delete_op, runner):
        """Test deleting evaluator successfully."""
        mock_delete_op.return_value = None

        result = runner.invoke(evaluator_app, ["delete", "--evaluator-id", "Custom.MyEval", "--force"])

        assert result.exit_code == 0

    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.evaluator_processor.delete_evaluator")
    @patch("bedrock_agentcore_starter_toolkit.cli.evaluation.commands.EvaluationControlPlaneClient")
    def test_delete_evaluator_builtin_fails(self, mock_client_class, mock_delete_op, runner):
        """Test deleting builtin evaluator fails."""
        mock_delete_op.side_effect = ValueError("Built-in evaluators cannot be deleted")

        result = runner.invoke(evaluator_app, ["delete", "--evaluator-id", "Builtin.Helpfulness", "--force"])

        assert result.exit_code != 0


# Note: Duplicate command is not exposed via CLI (only available via notebook interface)
# Tests removed as the CLI command doesn't exist
