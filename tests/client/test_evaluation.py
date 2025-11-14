"""Tests for Evaluation notebook interface."""

import pytest

from bedrock_agentcore_starter_toolkit.notebook import Evaluation


class TestEvaluation:
    """Test Evaluation client initialization and configuration."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        eval_client = Evaluation(agent_id="test-agent", region="us-east-1", session_id="test-session")

        assert eval_client.agent_id == "test-agent"
        assert eval_client.region == "us-east-1"
        assert eval_client.session_id == "test-session"

    def test_evaluate_requires_params(self):
        """Test that evaluate requires agent_id and region."""
        eval_client = Evaluation()

        with pytest.raises(ValueError, match="session_id"):
            eval_client.evaluate()

    def test_evaluate_requires_agent_info(self):
        """Test that evaluate requires agent_id and region."""
        eval_client = Evaluation(session_id="test-session")

        with pytest.raises(ValueError, match="Agent ID and region"):
            eval_client.evaluate()
