"""Tests for run_mock_server.py."""

import os
from pathlib import Path

import pytest


def test_mock_server_file_exists():
    """Test that the mock server file exists."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"
    assert script_path.exists()
    assert script_path.is_file()


def test_mock_server_has_shebang():
    """Test that the script has proper shebang."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        first_line = f.readline()
        assert first_line.startswith("#!/usr/bin/env python3")


def test_mock_server_has_docstring():
    """Test that the script has a docstring."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert '"""' in content
        assert "mock mode" in content.lower()
        assert "testing" in content.lower()


def test_mock_server_sets_environment_variable():
    """Test that the script sets AGENTCORE_MOCK_MODE."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert 'os.environ["AGENTCORE_MOCK_MODE"] = "true"' in content


def test_mock_server_imports():
    """Test that the script has required imports."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "import os" in content
        assert "import sys" in content
        assert "import uvicorn" in content


def test_mock_server_uvicorn_configuration():
    """Test that uvicorn is configured correctly."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "uvicorn.run" in content
        assert '"backend.main:app"' in content
        assert 'host="127.0.0.1"' in content
        assert "port=8001" in content
        assert "reload=True" in content


def test_mock_server_error_handling():
    """Test that the script handles ImportError."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "except ImportError" in content
        assert "sys.exit(1)" in content


def test_mock_server_user_messages():
    """Test that the script prints helpful messages."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "MOCK MODE" in content
        assert "localhost:8001" in content
        assert "Ctrl+C" in content


def test_mock_server_main_guard():
    """Test that script has proper main guard."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert 'if __name__ == "__main__":' in content


def test_mock_server_readable():
    """Test that the script is readable."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"
    assert os.access(script_path, os.R_OK)


def test_mock_server_syntax_valid():
    """Test that the script has valid Python syntax."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        code = f.read()
        try:
            compile(code, str(script_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Script has syntax error: {e}")


def test_mock_server_help_text():
    """Test that script contains helpful usage information."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "Usage:" in content or "usage:" in content.lower()
        assert "python" in content.lower()


def test_mock_server_backend_reference():
    """Test that script references the backend module correctly."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "backend.main:app" in content


def test_mock_server_port_configuration():
    """Test that the server port is 8001."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "8001" in content


def test_mock_server_host_configuration():
    """Test that the server host is set to localhost."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "127.0.0.1" in content or "localhost" in content


def test_mock_server_reload_enabled():
    """Test that reload is enabled for development."""
    script_path = Path(__file__).parent.parent.parent / "src/bedrock_agentcore_starter_toolkit/ui/run_mock_server.py"

    with open(script_path, "r") as f:
        content = f.read()
        assert "reload=True" in content
