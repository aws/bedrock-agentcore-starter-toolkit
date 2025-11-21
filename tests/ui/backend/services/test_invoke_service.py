"""Tests for InvokeService."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service import (
    InvokeService,
)


@pytest.fixture
def config_path():
    """Return a test config path."""
    return Path("/tmp/test_config.yaml")


def test_invoke_service_init(config_path):
    """Test InvokeService initialization."""
    service = InvokeService(config_path, local_mode=False)

    assert service.config_path == config_path
    assert service.local_mode is False
    assert service.current_session_id is None


def test_invoke_service_init_local_mode(config_path):
    """Test InvokeService initialization with local mode."""
    service = InvokeService(config_path, local_mode=True)

    assert service.local_mode is True


def test_invoke_with_session_id(config_path):
    """Test invoke with provided session ID."""
    service = InvokeService(config_path)

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "session-123"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.return_value = mock_result

        result = service.invoke("Hello", session_id="session-123")

        assert result["response"] == "Test response"
        assert result["session_id"] == "session-123"
        assert result["agent_arn"] == "arn:aws:bedrock:us-east-1:123456789012:agent/test"
        assert service.current_session_id == "session-123"


def test_invoke_without_session_id(config_path):
    """Test invoke without session ID generates new one."""
    service = InvokeService(config_path)

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "generated-session"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        with patch(
            "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.generate_session_id"
        ) as mock_gen:
            mock_gen.return_value = "generated-session"
            mock_invoke.return_value = mock_result

            result = service.invoke("Hello")

            assert result["session_id"] == "generated-session"
            assert service.current_session_id == "generated-session"


def test_invoke_with_bearer_token(config_path):
    """Test invoke with bearer token."""
    service = InvokeService(config_path)

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "session-123"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.return_value = mock_result

        _ = service.invoke(
            "Hello",
            session_id="session-123",
            bearer_token="token-abc",
        )

        mock_invoke.assert_called_once_with(
            config_path=config_path,
            payload="Hello",
            agent_name=None,
            session_id="session-123",
            bearer_token="token-abc",
            user_id=None,
            local_mode=False,
        )


def test_invoke_with_user_id(config_path):
    """Test invoke with user ID."""
    service = InvokeService(config_path)

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "session-123"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.return_value = mock_result

        _ = service.invoke(
            "Hello",
            session_id="session-123",
            user_id="user-456",
        )

        mock_invoke.assert_called_once_with(
            config_path=config_path,
            payload="Hello",
            agent_name=None,
            session_id="session-123",
            bearer_token=None,
            user_id="user-456",
            local_mode=False,
        )


def test_invoke_with_agent_name(config_path):
    """Test invoke with specific agent name."""
    service = InvokeService(config_path)

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "session-123"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.return_value = mock_result

        _ = service.invoke(
            "Hello",
            session_id="session-123",
            agent_name="custom-agent",
        )

        mock_invoke.assert_called_once_with(
            config_path=config_path,
            payload="Hello",
            agent_name="custom-agent",
            session_id="session-123",
            bearer_token=None,
            user_id=None,
            local_mode=False,
        )


def test_invoke_exception(config_path):
    """Test invoke with exception."""
    service = InvokeService(config_path)

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.side_effect = Exception("Invocation failed")

        with pytest.raises(Exception, match="Invocation failed"):
            service.invoke("Hello", session_id="session-123")


def test_generate_new_session_id(config_path):
    """Test generate_new_session_id."""
    service = InvokeService(config_path)

    with patch("bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.generate_session_id") as mock_gen:
        mock_gen.return_value = "new-session-789"

        session_id = service.generate_new_session_id()

        assert session_id == "new-session-789"
        assert service.current_session_id == "new-session-789"


def test_get_current_session_id(config_path):
    """Test get_current_session_id."""
    service = InvokeService(config_path)

    assert service.get_current_session_id() is None

    service.current_session_id = "session-123"
    assert service.get_current_session_id() == "session-123"


def test_invoke_local_mode(config_path):
    """Test invoke in local mode."""
    service = InvokeService(config_path, local_mode=True)

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "session-123"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.return_value = mock_result

        _ = service.invoke("Hello", session_id="session-123")

        mock_invoke.assert_called_once_with(
            config_path=config_path,
            payload="Hello",
            agent_name=None,
            session_id="session-123",
            bearer_token=None,
            user_id=None,
            local_mode=True,
        )


def test_invoke_service_init_with_agent_name(config_path):
    """Test InvokeService initialization with agent name."""
    service = InvokeService(config_path, agent_name="custom-agent", local_mode=False)

    assert service.config_path == config_path
    assert service.agent_name == "custom-agent"
    assert service.local_mode is False


def test_invoke_uses_instance_agent_name(config_path):
    """Test invoke uses instance agent_name when no parameter provided."""
    service = InvokeService(config_path, agent_name="instance-agent")

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "session-123"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.return_value = mock_result

        service.invoke("Hello", session_id="session-123")

        # Check that instance agent_name was used
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["agent_name"] == "instance-agent"


def test_invoke_parameter_overrides_instance_agent_name(config_path):
    """Test invoke parameter overrides instance agent_name."""
    service = InvokeService(config_path, agent_name="instance-agent")

    mock_result = Mock()
    mock_result.response = "Test response"
    mock_result.session_id = "session-123"
    mock_result.agent_arn = "arn:aws:bedrock:us-east-1:123456789012:agent/test"

    with patch(
        "bedrock_agentcore_starter_toolkit.ui.backend.services.invoke_service.invoke_bedrock_agentcore"
    ) as mock_invoke:
        mock_invoke.return_value = mock_result

        service.invoke("Hello", session_id="session-123", agent_name="override-agent")

        # Check that override agent_name was used
        call_kwargs = mock_invoke.call_args[1]
        assert call_kwargs["agent_name"] == "override-agent"
