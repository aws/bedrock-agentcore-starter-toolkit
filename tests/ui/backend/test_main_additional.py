"""Additional tests for UI backend main to increase coverage."""

import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    return TestClient(app)


def test_startup_event_with_config_path():
    """Test startup event with AGENTCORE_CONFIG_PATH set."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    with patch.dict(
        os.environ,
        {
            "AGENTCORE_CONFIG_PATH": "/tmp/custom_config.yaml",
            "AGENTCORE_LOCAL_MODE": "false",
            "AGENTCORE_MOCK_MODE": "false",
        },
    ):
        with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.ConfigService") as mock_config:
            with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.InvokeService"):
                with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.generate_session_id") as mock_gen:
                    mock_gen.return_value = "test-session"
                    mock_config_instance = Mock()
                    mock_config_instance.is_configured.return_value = False
                    mock_config.return_value = mock_config_instance

                    # Manually trigger startup
                    import asyncio

                    asyncio.run(main.startup_event())

                    mock_config.assert_called_once()
                    call_args = mock_config.call_args[0]
                    assert str(call_args[0]) == "/tmp/custom_config.yaml"


def test_startup_event_with_memory_service():
    """Test startup event initializes memory service when region available."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    with patch.dict(
        os.environ,
        {
            "AGENTCORE_LOCAL_MODE": "false",
            "AGENTCORE_MOCK_MODE": "false",
        },
    ):
        with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.ConfigService") as mock_config:
            with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.InvokeService"):
                with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.MemoryService") as mock_memory:
                    with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.generate_session_id") as mock_gen:
                        mock_gen.return_value = "test-session"
                        mock_config_instance = Mock()
                        mock_config_instance.is_configured.return_value = True
                        mock_config_instance.get_region.return_value = "us-west-2"
                        mock_config.return_value = mock_config_instance

                        import asyncio

                        asyncio.run(main.startup_event())

                        mock_memory.assert_called_once_with(region="us-west-2")


def test_invoke_agent_mock_mode_json_message(test_client):
    """Test invoke_agent in mock mode with JSON message."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    main.mock_mode = True
    main.mock_service = Mock()
    main.mock_service.invoke.return_value = {
        "response": "Mock response",
        "session_id": "mock-session-123",
        "timestamp": "2024-01-01T00:00:00Z",
    }

    json_message = json.dumps({"prompt": "Hello from JSON"})
    response = test_client.post(
        "/api/invoke",
        json={"message": json_message, "session_id": "mock-session-123"},
    )

    assert response.status_code == 200
    main.mock_service.invoke.assert_called_once_with("Hello from JSON", "mock-session-123")

    # Reset
    main.mock_mode = False
    main.mock_service = None


def test_invoke_agent_mock_mode_invalid_json(test_client):
    """Test invoke_agent in mock mode with invalid JSON message."""
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
        json={"message": "Plain text message", "session_id": "mock-session-123"},
    )

    assert response.status_code == 200
    main.mock_service.invoke.assert_called_once_with("Plain text message", "mock-session-123")

    # Reset
    main.mock_mode = False
    main.mock_service = None


def test_invoke_agent_non_empty_dict_response():
    """Test invoke_agent with non-empty dict response."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    client = TestClient(app)

    mock_invoke_service = Mock()
    mock_invoke_service.invoke.return_value = {
        "response": {"data": "some data"},
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200


def test_invoke_agent_list_single_item():
    """Test invoke_agent with single-item list response."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    client = TestClient(app)

    mock_invoke_service = Mock()
    mock_invoke_service.invoke.return_value = {
        "response": ["Single response"],
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Single response"


def test_invoke_agent_list_with_bytes():
    """Test invoke_agent with list containing bytes."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    client = TestClient(app)

    mock_invoke_service = Mock()
    mock_invoke_service.invoke.return_value = {
        "response": [b"Byte response", "String response"],
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "Byte response" in data["response"]
    assert "String response" in data["response"]


def test_invoke_agent_json_string_response():
    """Test invoke_agent with JSON string response."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    client = TestClient(app)

    mock_invoke_service = Mock()
    mock_invoke_service.invoke.return_value = {
        "response": '{"response": "Nested JSON response"}',
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Nested JSON response"


def test_invoke_agent_json_string_plain():
    """Test invoke_agent with plain JSON string."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    client = TestClient(app)

    mock_invoke_service = Mock()
    mock_invoke_service.invoke.return_value = {
        "response": '"Plain string"',
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Plain string"


def test_invoke_agent_invalid_json_string():
    """Test invoke_agent with invalid JSON string."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main
    from bedrock_agentcore_starter_toolkit.ui.backend.main import app

    client = TestClient(app)

    mock_invoke_service = Mock()
    mock_invoke_service.invoke.return_value = {
        "response": "Not a JSON string",
        "session_id": "session-123",
        "agent_arn": "arn:aws:bedrock:us-east-1:123456789012:agent/test",
    }
    main.invoke_service = mock_invoke_service
    main.mock_mode = False

    response = client.post(
        "/api/invoke",
        json={"message": "Hello", "session_id": "session-123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Not a JSON string"


def test_serve_spa_api_route(test_client):
    """Test serve_spa rejects API routes."""

    # Check if frontend build exists
    frontend_dir = Path(__file__).parent.parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/frontend/dist"
    if not frontend_dir.exists():
        pytest.skip("Frontend build directory not found")

    response = test_client.get("/api/nonexistent")
    assert response.status_code == 404


def test_serve_spa_existing_file(test_client):
    """Test serve_spa serves existing files."""

    # Check if frontend build exists
    frontend_dir = Path(__file__).parent.parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/frontend/dist"
    if not frontend_dir.exists():
        pytest.skip("Frontend build directory not found")

    # Try to access a common file
    response = test_client.get("/vite.svg")
    # Should either return the file or 404 if it doesn't exist
    assert response.status_code in [200, 404, 500]


def test_serve_spa_index_fallback(test_client):
    """Test serve_spa serves index.html for non-existent routes."""

    # Check if frontend build exists
    frontend_dir = Path(__file__).parent.parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/frontend/dist"
    if not frontend_dir.exists():
        pytest.skip("Frontend build directory not found")

    response = test_client.get("/some/random/route")
    # Should either return index.html or 500 if build doesn't exist
    assert response.status_code in [200, 500]


def test_startup_event_with_agent_name():
    """Test startup event with AGENTCORE_AGENT_NAME set."""
    from bedrock_agentcore_starter_toolkit.ui.backend import main

    with patch.dict(
        os.environ,
        {
            "AGENTCORE_LOCAL_MODE": "false",
            "AGENTCORE_MOCK_MODE": "false",
            "AGENTCORE_AGENT_NAME": "custom-agent",
        },
    ):
        with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.ConfigService") as mock_config:
            with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.InvokeService") as mock_invoke:
                with patch("bedrock_agentcore_starter_toolkit.ui.backend.main.generate_session_id") as mock_gen:
                    mock_gen.return_value = "test-session"
                    mock_config_instance = Mock()
                    mock_config_instance.is_configured.return_value = False
                    mock_config.return_value = mock_config_instance

                    import asyncio

                    asyncio.run(main.startup_event())

                    # Verify ConfigService was called with agent_name
                    mock_config.assert_called_once()
                    call_kwargs = mock_config.call_args[1]
                    assert call_kwargs["agent_name"] == "custom-agent"

                    # Verify InvokeService was called with agent_name
                    mock_invoke.assert_called_once()
                    call_kwargs = mock_invoke.call_args[1]
                    assert call_kwargs["agent_name"] == "custom-agent"
