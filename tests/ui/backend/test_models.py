"""Tests for UI backend models."""

from bedrock_agentcore_starter_toolkit.ui.backend.models import (
    AgentConfigResponse,
    ErrorResponse,
    InvokeRequest,
    InvokeResponse,
    MemoryResourceResponse,
    MemoryStrategyResponse,
    NewSessionResponse,
)


def test_agent_config_response():
    """Test AgentConfigResponse model."""
    config = AgentConfigResponse(
        mode="local",
        agent_name="test-agent",
        agent_arn="arn:aws:bedrock:us-east-1:123456789012:agent/test",
        region="us-east-1",
        session_id="session-123",
        auth_method="iam",
        memory_id="memory-123",
    )
    assert config.mode == "local"
    assert config.agent_name == "test-agent"
    assert config.agent_arn == "arn:aws:bedrock:us-east-1:123456789012:agent/test"
    assert config.region == "us-east-1"
    assert config.session_id == "session-123"
    assert config.auth_method == "iam"
    assert config.memory_id == "memory-123"


def test_agent_config_response_minimal():
    """Test AgentConfigResponse with minimal fields."""
    config = AgentConfigResponse(
        mode="remote",
        agent_name="test-agent",
        session_id="session-123",
        auth_method="oauth",
    )
    assert config.mode == "remote"
    assert config.agent_name == "test-agent"
    assert config.session_id == "session-123"
    assert config.auth_method == "oauth"
    assert config.agent_arn is None
    assert config.region is None
    assert config.memory_id is None


def test_invoke_request():
    """Test InvokeRequest model."""
    request = InvokeRequest(
        message="Hello",
        session_id="session-123",
        bearer_token="token-abc",
    )
    assert request.message == "Hello"
    assert request.session_id == "session-123"
    assert request.bearer_token == "token-abc"


def test_invoke_request_no_token():
    """Test InvokeRequest without bearer token."""
    request = InvokeRequest(
        message="Hello",
        session_id="session-123",
    )
    assert request.message == "Hello"
    assert request.session_id == "session-123"
    assert request.bearer_token is None


def test_invoke_response_string():
    """Test InvokeResponse with string response."""
    response = InvokeResponse(
        response="Hello, world!",
        session_id="session-123",
        timestamp="2024-01-01T00:00:00Z",
    )
    assert response.response == "Hello, world!"
    assert response.session_id == "session-123"
    assert response.timestamp == "2024-01-01T00:00:00Z"


def test_invoke_response_dict():
    """Test InvokeResponse with dict response."""
    response = InvokeResponse(
        response={"message": "Hello"},
        session_id="session-123",
        timestamp="2024-01-01T00:00:00Z",
    )
    assert response.response == {"message": "Hello"}
    assert response.session_id == "session-123"


def test_new_session_response():
    """Test NewSessionResponse model."""
    response = NewSessionResponse(session_id="new-session-456")
    assert response.session_id == "new-session-456"


def test_memory_strategy_response():
    """Test MemoryStrategyResponse model."""
    strategy = MemoryStrategyResponse(
        strategy_id="strategy-123",
        name="Test Strategy",
        type="semantic",
        status="ENABLED",
        description="A test strategy",
        namespaces=["namespace1", "namespace2"],
        configuration={"key": "value"},
    )
    assert strategy.strategy_id == "strategy-123"
    assert strategy.name == "Test Strategy"
    assert strategy.type == "semantic"
    assert strategy.status == "ENABLED"
    assert strategy.description == "A test strategy"
    assert strategy.namespaces == ["namespace1", "namespace2"]
    assert strategy.configuration == {"key": "value"}


def test_memory_strategy_response_minimal():
    """Test MemoryStrategyResponse with minimal fields."""
    strategy = MemoryStrategyResponse(
        strategy_id="strategy-123",
        name="Test Strategy",
        type="summary",
        status="ENABLED",
    )
    assert strategy.strategy_id == "strategy-123"
    assert strategy.name == "Test Strategy"
    assert strategy.type == "summary"
    assert strategy.status == "ENABLED"
    assert strategy.description is None
    assert strategy.namespaces is None
    assert strategy.configuration is None


def test_memory_resource_response():
    """Test MemoryResourceResponse model."""
    memory = MemoryResourceResponse(
        memory_id="memory-123",
        name="Test Memory",
        status="ENABLED",
        event_expiry_days=30,
        memory_type="short-term",
        strategies=[
            MemoryStrategyResponse(
                strategy_id="strategy-1",
                name="Strategy 1",
                type="semantic",
                status="ENABLED",
            )
        ],
    )
    assert memory.memory_id == "memory-123"
    assert memory.name == "Test Memory"
    assert memory.status == "ENABLED"
    assert memory.event_expiry_days == 30
    assert memory.memory_type == "short-term"
    assert len(memory.strategies) == 1
    assert memory.strategies[0].strategy_id == "strategy-1"


def test_memory_resource_response_long_term():
    """Test MemoryResourceResponse with long-term memory."""
    memory = MemoryResourceResponse(
        memory_id="memory-456",
        name="Long Term Memory",
        status="ENABLED",
        event_expiry_days=90,
        memory_type="short-term-and-long-term",
        strategies=[],
    )
    assert memory.memory_id == "memory-456"
    assert memory.memory_type == "short-term-and-long-term"
    assert memory.event_expiry_days == 90


def test_error_response():
    """Test ErrorResponse model."""
    error = ErrorResponse(
        error={
            "code": "TEST_ERROR",
            "message": "This is a test error",
        }
    )
    assert error.error["code"] == "TEST_ERROR"
    assert error.error["message"] == "This is a test error"
