"""Tests for UI backend mock mode."""

from bedrock_agentcore_starter_toolkit.ui.backend.mock_mode import MockAgentService


def test_mock_agent_service_init():
    """Test MockAgentService initialization."""
    service = MockAgentService()
    assert service.session_id is not None
    assert service.session_id.startswith("mock-session-")


def test_generate_session_id():
    """Test session ID generation."""
    service = MockAgentService()
    session_id = service._generate_session_id()
    assert session_id.startswith("mock-session-")
    assert len(session_id.split("-")) == 4


def test_get_config():
    """Test get_config returns mock configuration."""
    service = MockAgentService()
    config = service.get_config()

    assert config["mode"] == "local"
    assert config["agent_name"] == "Mock Agent (Test Mode)"
    assert config["agent_arn"] == "arn:aws:bedrock:us-east-1:123456789012:agent/mock-agent-id"
    assert config["region"] == "us-east-1"
    assert config["session_id"] == service.session_id
    assert config["auth_method"] == "none"
    assert config["memory_id"] == "mock-memory-123"


def test_invoke():
    """Test invoke returns mock response."""
    service = MockAgentService()
    result = service.invoke("Hello", service.session_id)

    assert "response" in result
    assert "session_id" in result
    assert "timestamp" in result
    assert result["session_id"] == service.session_id
    assert isinstance(result["response"], str)
    assert len(result["response"]) > 0


def test_invoke_with_new_session():
    """Test invoke with new session ID."""
    service = MockAgentService()
    _ = service.session_id  # Store old session for potential future use
    new_session = "custom-session-123"

    result = service.invoke("Test message", new_session)

    assert result["session_id"] == new_session
    assert service.session_id == new_session


def test_invoke_response_variety():
    """Test that invoke returns different responses."""
    service = MockAgentService()
    responses = set()

    # Call multiple times to get different responses
    for _ in range(10):
        result = service.invoke("Test", service.session_id)
        responses.add(result["response"])

    # Should have at least 2 different responses
    assert len(responses) >= 2


def test_create_new_session():
    """Test create_new_session generates new session ID."""
    service = MockAgentService()
    old_session = service.session_id

    result = service.create_new_session()

    assert "session_id" in result
    assert result["session_id"] != old_session
    assert service.session_id == result["session_id"]
    assert result["session_id"].startswith("mock-session-")


def test_get_memory():
    """Test get_memory returns mock memory information."""
    service = MockAgentService()
    memory = service.get_memory()

    assert memory is not None
    assert memory["memory_id"] == "mock-memory-123"
    assert memory["name"] == "Mock Memory Resource"
    assert memory["status"] == "ENABLED"
    assert memory["event_expiry_days"] == 30
    assert memory["memory_type"] == "short-term"
    assert len(memory["strategies"]) == 1
    assert memory["strategies"][0]["strategy_id"] == "mock-strategy-1"
    assert memory["strategies"][0]["name"] == "Session Summary"
    assert memory["strategies"][0]["type"] == "SESSION_SUMMARY"
    assert memory["strategies"][0]["status"] == "ENABLED"
