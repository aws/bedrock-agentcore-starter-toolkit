"""Tests for UI backend main FastAPI application."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    # Import here to avoid startup event issues
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    return TestClient(app)


@pytest.fixture
def mock_config_service():
    """Create a mock ConfigService."""
    service = Mock()
    service.is_configured.return_value = True
    service.get_agent_name.return_value = "test-agent"
    service.get_agent_arn.return_value = "arn:aws:bedrock:us-east-1:123456789012:agent/test"
    service.get_region.return_value = "us-east-1"
    service.get_memory_id.return_value = "memory-123"
    service.has_oauth_config.return_value = False
    return service


@pytest.fixture
def mock_invoke_service():
    """Create a mock InvokeService."""
    service = Mock()
    service.invoke.return_value = {
        "response": "Test response",
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    service.generate_new_session_id.return_value = "new-session-456"
    return service


@pytest.fixture
def mock_memory_service():
    """Create a mock MemoryService."""
    service = Mock()
    service.get_memory_details.return_value = {
        "memory_id": "memory-123",
        "name": "Test Memory",
        "status": "ENABLED",
        "event_expiry_days": 30,
        "memory_type": "short-term",
        "strategies": [
            {
                "strategy_id": "strategy-1",
                "name": "Test Strategy",
                "type": "semantic",
                "status": "ENABLED",
                "description": None,
                "namespaces": None,
                "configuration": None,
            }
        ],
    }
    return service


def test_health_check(test_client):
    """Test health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_config_mock_mode(test_client):
    """Test get_config in mock mode."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    # Set mock mode
    main.mock_mode = True
    main.mock_service = Mock()
    main.mock_service.get_config.return_value = {
        "mode": "local",
        "agent_name": "Mock Agent",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/mock",
        "region": "us-east-1",
        "session_id": "mock-session-123",
        "auth_method": "none",
        "memory_id": "mock-memory-123",
    }

    response = test_client.get("/api/config")

    assert response.status_code == 200
    data = response.json()
    assert data["agent_name"] == "Mock Agent"
    assert data["mode"] == "local"

    # Reset
    main.mock_mode = False
    main.mock_service = None


def test_get_config_no_config(test_client, mock_config_service):
    """Test get_config with no configuration."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.config_service = Mock()
    main.config_service.is_configured.return_value = False
    main.mock_mode = False

    response = test_client.get("/api/config")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "CONFIG_NOT_FOUND"


def test_get_config_success(test_client, mock_config_service):
    """Test get_config with valid configuration."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.config_service = mock_config_service
    main.current_session_id = "session-123"
    main.local_mode = False
    main.mock_mode = False

    response = test_client.get("/api/config")

    assert response.status_code == 200
    data = response.json()
    assert data["agent_name"] == "test-agent"
    assert data["mode"] == "remote"
    assert data["auth_method"] == "iam"
    assert data["session_id"] == "session-123"


def test_get_config_local_mode(test_client, mock_config_service):
    """Test get_config in local mode."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.config_service = mock_config_service
    main.current_session_id = "session-123"
    main.local_mode = True
    main.mock_mode = False

    response = test_client.get("/api/config")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "local"
    assert data["auth_method"] == "none"


def test_get_config_oauth(test_client, mock_config_service):
    """Test get_config with OAuth."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    mock_config_service.has_oauth_config.return_value = True
    main.config_service = mock_config_service
    main.current_session_id = "session-123"
    main.local_mode = False
    main.mock_mode = False

    response = test_client.get("/api/config")

    assert response.status_code == 200
    data = response.json()
    assert data["auth_method"] == "oauth"


def test_invoke_agent_mock_mode(test_client):
    """Test invoke_agent in mock mode."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.mock_mode = True
    main.mock_service = Mock()
    main.mock_service.invoke.return_value = {
        "response": "Mock response",
        "session_id": "mock-session-123",
        "timestamp": "2024-01-01T00:00:00Z",
    }

    response = test_client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "mock-session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Mock response"
    assert data["session_id"] == "mock-session-123"

    # Reset
    main.mock_mode = False
    main.mock_service = None


def test_invoke_agent_no_service(test_client):
    """Test invoke_agent with no service initialized."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.invoke_service = None
    main.mock_mode = False

    response = test_client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "SERVICE_NOT_INITIALIZED"


def test_invoke_agent_success(test_client, mock_invoke_service):
    """Test invoke_agent with successful invocation."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["session_id"] == "session-123"


def test_invoke_agent_with_bearer_token(test_client, mock_invoke_service):
    """Test invoke_agent with bearer token."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post(
        "/api/invoke",
        json={
            "message": "Hello",
            "session_id": "session-123",
            "bearer_token": "token-abc",
        },
    )

    assert response.status_code == 200
    mock_invoke_service.invoke.assert_called_once()


def test_invoke_agent_with_user_id(test_client, mock_invoke_service):
    """Test invoke_agent with user ID."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post(
        "/api/invoke",
        json={
            "message": "Hello",
            "session_id": "session-123",
            "user_id": "user-456",
        },
    )

    assert response.status_code == 200
    mock_invoke_service.invoke.assert_called_once_with(
        message="Hello",
        session_id="session-123",
        bearer_token=None,
        user_id="user-456",
    )


def test_invoke_agent_exception(test_client, mock_invoke_service):
    """Test invoke_agent with exception."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    mock_invoke_service.invoke.side_effect = Exception("Invocation failed")
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "INVOCATION_FAILED"


def test_invoke_agent_json_response(test_client, mock_invoke_service):
    """Test invoke_agent with JSON response."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    mock_invoke_service.invoke.return_value = {
        "response": {"response": "Nested response"},
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200


def test_invoke_agent_list_response(test_client, mock_invoke_service):
    """Test invoke_agent with list response."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    mock_invoke_service.invoke.return_value = {
        "response": ["Response 1", "Response 2"],
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200


def test_create_new_session_mock_mode(test_client):
    """Test create_new_session in mock mode."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.mock_mode = True
    main.mock_service = Mock()
    main.mock_service.create_new_session.return_value = {
        "session_id": "new-mock-session",
    }

    response = test_client.post("/api/session/new")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "new-mock-session"

    # Reset
    main.mock_mode = False
    main.mock_service = None


def test_create_new_session_no_service(test_client):
    """Test create_new_session with no service."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.invoke_service = None
    main.mock_mode = False

    response = test_client.post("/api/session/new")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "SERVICE_NOT_INITIALIZED"


def test_create_new_session_success(test_client, mock_invoke_service):
    """Test create_new_session with success."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post("/api/session/new")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "new-session-456"


def test_create_new_session_exception(test_client, mock_invoke_service):
    """Test create_new_session with exception."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    mock_invoke_service.generate_new_session_id.side_effect = Exception("Failed")
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = test_client.post("/api/session/new")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "SESSION_CREATION_FAILED"


def test_get_memory_mock_mode(test_client):
    """Test get_memory in mock mode."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.mock_mode = True
    main.mock_service = Mock()
    main.mock_service.get_memory.return_value = {
        "memory_id": "mock-memory-123",
        "name": "Mock Memory",
        "status": "ENABLED",
        "event_expiry_days": 30,
        "memory_type": "short-term",
        "strategies": [],
    }

    response = test_client.get("/api/memory")

    assert response.status_code == 200
    data = response.json()
    assert data["memory_id"] == "mock-memory-123"

    # Reset
    main.mock_mode = False
    main.mock_service = None


def test_get_memory_mock_mode_no_memory(test_client):
    """Test get_memory in mock mode with no memory."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.mock_mode = True
    main.mock_service = Mock()
    main.mock_service.get_memory.return_value = None

    response = test_client.get("/api/memory")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "MEMORY_NOT_CONFIGURED"

    # Reset
    main.mock_mode = False
    main.mock_service = None


def test_get_memory_no_config(test_client):
    """Test get_memory with no config."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.config_service = Mock()
    main.config_service.is_configured.return_value = False
    main.mock_mode = False

    response = test_client.get("/api/memory")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "CONFIG_NOT_FOUND"


def test_get_memory_no_memory_id(test_client, mock_config_service):
    """Test get_memory with no memory ID."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    mock_config_service.get_memory_id.return_value = None
    main.config_service = mock_config_service
    main.mock_mode = False

    response = test_client.get("/api/memory")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == "MEMORY_NOT_CONFIGURED"


def test_get_memory_no_service(test_client, mock_config_service):
    """Test get_memory with no memory service."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.config_service = mock_config_service
    main.memory_service = None
    main.mock_mode = False

    response = test_client.get("/api/memory")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "SERVICE_NOT_INITIALIZED"


def test_get_memory_success(test_client, mock_config_service, mock_memory_service):
    """Test get_memory with success."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.config_service = mock_config_service
    main.memory_service = mock_memory_service
    main.mock_mode = False

    response = test_client.get("/api/memory")

    assert response.status_code == 200
    data = response.json()
    assert data["memory_id"] == "memory-123"
    assert data["name"] == "Test Memory"


def test_get_memory_exception(test_client, mock_config_service, mock_memory_service):
    """Test get_memory with exception."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    mock_memory_service.get_memory_details.side_effect = Exception("Failed")
    main.config_service = mock_config_service
    main.memory_service = mock_memory_service
    main.mock_mode = False

    response = test_client.get("/api/memory")

    assert response.status_code == 500
    data = response.json()
    assert data["detail"]["code"] == "MEMORY_RETRIEVAL_FAILED"
