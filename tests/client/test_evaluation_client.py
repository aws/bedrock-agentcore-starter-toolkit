"""Tests for notebook Evaluation client (new API)."""

from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.notebook import Evaluation
from bedrock_agentcore_starter_toolkit.operations.evaluation.models import (
    EvaluationResults,
)

# Apply mock_boto3_clients fixture to prevent real AWS calls
pytestmark = pytest.mark.usefixtures("mock_boto3_clients")

# =============================================================================
# Initialization Tests
# =============================================================================


class TestInitialization:
    """Test Evaluation client initialization."""

    def test_init_with_region(self):
        """Test initialization with explicit region."""
        client = Evaluation(region="us-west-2")

        assert client.region == "us-west-2"
        assert client._data_plane_client is not None
        assert client._control_plane_client is not None
        assert client._processor is not None

    @patch("boto3.Session")
    def test_init_without_region(self, mock_session):
        """Test initialization without region uses boto3 default."""
        mock_session_instance = Mock()
        mock_session_instance.region_name = "us-east-1"
        mock_session.return_value = mock_session_instance

        client = Evaluation()

        assert client.region == "us-east-1"

    @patch("boto3.Session")
    def test_init_defaults_to_us_east_1(self, mock_session):
        """Test initialization defaults to us-east-1 if no boto3 region."""
        mock_session_instance = Mock()
        mock_session_instance.region_name = None
        mock_session.return_value = mock_session_instance

        client = Evaluation()

        assert client.region == "us-east-1"

    def test_init_with_endpoint_url(self):
        """Test initialization with custom endpoint."""
        client = Evaluation(region="us-west-2", endpoint_url="https://custom.endpoint.com")

        assert client.region == "us-west-2"
        assert client._data_plane_client is not None


# =============================================================================
# from_config Tests
# =============================================================================


class TestFromConfig:
    """Test creating client from config file."""

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists")
    def test_from_config_returns_tuple(self, mock_load_config, tmp_path):
        """Test from_config returns tuple of (client, agent_id, session_id)."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("test: config")

        mock_agent_config = Mock()
        mock_agent_config.aws.region = "us-west-2"
        mock_agent_config.bedrock_agentcore.agent_id = "agent-123"
        mock_agent_config.bedrock_agentcore.agent_session_id = "session-456"

        mock_config = Mock()
        mock_config.get_agent_config = Mock(return_value=mock_agent_config)
        mock_load_config.return_value = mock_config

        result = Evaluation.from_config(config_path=config_file)

        assert isinstance(result, tuple)
        assert len(result) == 3
        client, agent_id, session_id = result
        assert isinstance(client, Evaluation)
        assert agent_id == "agent-123"
        assert session_id == "session-456"

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.config.load_config_if_exists")
    def test_from_config_no_file(self, mock_load_config, tmp_path):
        """Test from_config raises error when file doesn't exist."""
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        mock_load_config.return_value = None

        with pytest.raises(ValueError, match="No config file found"):
            Evaluation.from_config(config_path=config_file)


# =============================================================================
# get_latest_session Tests
# =============================================================================


class TestGetLatestSession:
    """Test get_latest_session method."""

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_get_latest_session_requires_agent_id(self, mock_init):
        """Test get_latest_session requires agent_id."""
        client = Evaluation()
        client.region = "us-west-2"
        client.console = Mock()
        client._processor = None

        with pytest.raises(ValueError, match="Agent ID and region required"):
            client.get_latest_session("")

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_get_latest_session_success(self, mock_init):
        """Test successful latest session retrieval."""
        client = Evaluation()
        client.region = "us-west-2"
        client.console = Mock()

        mock_processor = Mock()
        mock_processor.get_latest_session.return_value = "session-123"
        client._processor = mock_processor

        result = client.get_latest_session("agent-456")

        assert result == "session-123"
        mock_processor.get_latest_session.assert_called_once_with("agent-456", "us-west-2")

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_get_latest_session_no_sessions(self, mock_init):
        """Test when no sessions found."""
        client = Evaluation()
        client.region = "us-west-2"
        client.console = Mock()

        mock_processor = Mock()
        mock_processor.get_latest_session.return_value = None
        client._processor = mock_processor

        result = client.get_latest_session("agent-456")

        assert result is None
        client.console.print.assert_called()

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_get_latest_session_error_handling(self, mock_init):
        """Test error handling returns None."""
        client = Evaluation()
        client.region = "us-west-2"
        client.console = Mock()

        mock_processor = Mock()
        mock_processor.get_latest_session.side_effect = RuntimeError("API error")
        client._processor = mock_processor

        result = client.get_latest_session("agent-456")

        assert result is None


# =============================================================================
# run Tests
# =============================================================================


class TestRun:
    """Test run evaluation method."""

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_run_requires_agent_id(self, mock_init):
        """Test run requires agent_id."""
        client = Evaluation()
        client.region = "us-west-2"
        client.console = Mock()

        with pytest.raises(ValueError, match="agent_id is required"):
            client.run(agent_id="", session_id="session-123")

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_run_with_session_id(self, mock_init):
        """Test run with explicit session_id."""
        client = Evaluation()
        client.region = "us-west-2"

        # Mock console with proper context manager support
        mock_console = Mock()
        mock_console.status.return_value.__enter__ = Mock(return_value=None)
        mock_console.status.return_value.__exit__ = Mock(return_value=None)
        client.console = mock_console

        mock_results = EvaluationResults(session_id="session-123")
        mock_processor = Mock()
        mock_processor.evaluate_session.return_value = mock_results
        client._processor = mock_processor

        result = client.run(agent_id="agent-456", session_id="session-123")

        assert isinstance(result, EvaluationResults)
        mock_processor.evaluate_session.assert_called_once()

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_run_auto_fetch_session(self, mock_init):
        """Test run auto-fetches session when not provided."""
        client = Evaluation()
        client.region = "us-west-2"

        # Mock console with proper context manager support
        mock_console = Mock()
        mock_console.status.return_value.__enter__ = Mock(return_value=None)
        mock_console.status.return_value.__exit__ = Mock(return_value=None)
        client.console = mock_console

        # Mock get_latest_session
        client.get_latest_session = Mock(return_value="session-789")

        mock_results = EvaluationResults(session_id="session-789")
        mock_processor = Mock()
        mock_processor.evaluate_session.return_value = mock_results
        client._processor = mock_processor

        result = client.run(agent_id="agent-456")

        client.get_latest_session.assert_called_once_with("agent-456")
        assert result.session_id == "session-789"

    @patch.object(Evaluation, "__init__", return_value=None)
    def test_run_fails_when_no_session_found(self, mock_init):
        """Test run fails when cannot auto-fetch session."""
        client = Evaluation()
        client.region = "us-west-2"
        client.console = Mock()
        client.get_latest_session = Mock(return_value=None)

        with pytest.raises(ValueError, match="No session_id provided"):
            client.run(agent_id="agent-456")


# =============================================================================
# Evaluator Management Tests
# =============================================================================


class TestEvaluatorManagement:
    """Test evaluator management methods."""

    def test_list_evaluators(self):
        """Test list_evaluators calls control plane client."""
        client = Evaluation(region="us-west-2")
        client._control_plane_client.list_evaluators = Mock(
            return_value={"evaluators": [{"evaluatorId": "Builtin.Helpfulness"}]}
        )

        result = client.list_evaluators(max_results=10)

        assert "evaluators" in result
        client._control_plane_client.list_evaluators.assert_called_once_with(max_results=10)

    def test_get_evaluator(self):
        """Test get_evaluator calls control plane client."""
        client = Evaluation(region="us-west-2")
        client._control_plane_client.get_evaluator = Mock(
            return_value={"evaluatorId": "Builtin.Helpfulness", "level": "TRACE"}
        )

        result = client.get_evaluator("Builtin.Helpfulness")

        assert result["evaluatorId"] == "Builtin.Helpfulness"
        client._control_plane_client.get_evaluator.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.evaluator_processor")
    def test_create_evaluator(self, mock_processor):
        """Test create_evaluator."""
        client = Evaluation(region="us-west-2")
        mock_processor.create_evaluator.return_value = {
            "evaluatorId": "Custom.MyEval",
            "evaluatorArn": "arn:test",
        }

        config = {"llmAsAJudge": {"instructions": "Test"}}
        result = client.create_evaluator("MyEval", config)

        assert result["evaluatorId"] == "Custom.MyEval"
        mock_processor.create_evaluator.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.evaluator_processor")
    def test_duplicate_evaluator(self, mock_processor):
        """Test duplicate_evaluator."""
        client = Evaluation(region="us-west-2")
        mock_processor.duplicate_evaluator.return_value = {
            "evaluatorId": "Custom.MyEvalV2",
            "evaluatorArn": "arn:test",
        }

        result = client.duplicate_evaluator("source-id", "MyEvalV2", "Description")

        assert result["evaluatorId"] == "Custom.MyEvalV2"
        mock_processor.duplicate_evaluator.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.evaluator_processor")
    def test_update_evaluator(self, mock_processor):
        """Test update_evaluator."""
        client = Evaluation(region="us-west-2")
        mock_processor.update_evaluator.return_value = {"status": "updated"}

        result = client.update_evaluator("eval-id", description="New description")

        assert result["status"] == "updated"
        mock_processor.update_evaluator.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.evaluator_processor")
    def test_delete_evaluator(self, mock_processor):
        """Test delete_evaluator."""
        client = Evaluation(region="us-west-2")
        mock_processor.delete_evaluator.return_value = None

        client.delete_evaluator("eval-id")

        mock_processor.delete_evaluator.assert_called_once()


# =============================================================================
# Online Evaluation Tests
# =============================================================================


class TestOnlineEvaluation:
    """Test online evaluation configuration methods."""

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.online_processor")
    def test_create_online_config(self, mock_processor):
        """Test create_online_config."""
        client = Evaluation(region="us-west-2")
        mock_processor.create_online_evaluation_config.return_value = {
            "onlineEvaluationConfigId": "config-123",
            "status": "ENABLED",
        }

        result = client.create_online_config("my-config", agent_id="agent-456")

        assert result["onlineEvaluationConfigId"] == "config-123"
        mock_processor.create_online_evaluation_config.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.online_processor")
    def test_create_online_config_requires_agent_id(self, mock_processor):
        """Test create_online_config requires agent_id."""
        client = Evaluation(region="us-west-2")

        with pytest.raises(ValueError, match="agent_id is required"):
            client.create_online_config("my-config", agent_id=None)

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.online_processor")
    def test_get_online_config(self, mock_processor):
        """Test get_online_config."""
        client = Evaluation(region="us-west-2")
        mock_processor.get_online_evaluation_config.return_value = {"onlineEvaluationConfigId": "config-123"}

        result = client.get_online_config("config-123")

        assert result["onlineEvaluationConfigId"] == "config-123"
        mock_processor.get_online_evaluation_config.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.online_processor")
    def test_list_online_configs(self, mock_processor):
        """Test list_online_configs."""
        client = Evaluation(region="us-west-2")
        mock_processor.list_online_evaluation_configs.return_value = {"onlineEvaluationConfigs": []}

        result = client.list_online_configs(agent_id="agent-456", max_results=10)

        assert "onlineEvaluationConfigs" in result
        mock_processor.list_online_evaluation_configs.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.online_processor")
    def test_update_online_config(self, mock_processor):
        """Test update_online_config."""
        client = Evaluation(region="us-west-2")
        mock_processor.update_online_evaluation_config.return_value = {"status": "DISABLED"}

        result = client.update_online_config("config-123", status="DISABLED")

        assert result["status"] == "DISABLED"
        mock_processor.update_online_evaluation_config.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.notebook.evaluation.client.online_processor")
    def test_delete_online_config(self, mock_processor):
        """Test delete_online_config."""
        client = Evaluation(region="us-west-2")
        mock_processor.delete_online_evaluation_config.return_value = None

        client.delete_online_config("config-123", delete_execution_role=True)

        mock_processor.delete_online_evaluation_config.assert_called_once()
