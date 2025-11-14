"""Tests for Observability notebook interface."""

import pytest

from bedrock_agentcore_starter_toolkit.notebook import Observability


class TestObservability:
    """Test Observability client initialization and configuration."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        obs = Observability(agent_id="test-agent", region="us-east-1", session_id="test-session")

        assert obs.agent_id == "test-agent"
        assert obs.region == "us-east-1"
        assert obs.session_id == "test-session"
        assert obs.runtime_suffix == "DEFAULT"

    def test_init_without_params_no_client(self):
        """Test that client is not initialized without required params."""
        obs = Observability()

        assert obs._client is None

    def test_methods_require_client(self):
        """Test that methods fail gracefully without client."""
        obs = Observability()

        with pytest.raises(ValueError, match="not initialized"):
            obs.get_session("test-session")

        with pytest.raises(ValueError, match="not initialized"):
            obs.get_latest_session()
