"""Tests for port configuration utilities."""

import os
import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.port_config import get_local_port


class TestPortConfig:
    """Test port configuration functionality."""

    def test_get_local_port_default(self, monkeypatch):
        """Test get_local_port returns default 8080 when env var not set."""
        # Ensure env var is not set
        monkeypatch.delenv("AGENTCORE_RUNTIME_LOCAL_PORT", raising=False)
        
        port = get_local_port()
        assert port == 8080

    def test_get_local_port_from_env(self, monkeypatch):
        """Test get_local_port returns value from environment variable."""
        monkeypatch.setenv("AGENTCORE_RUNTIME_LOCAL_PORT", "9000")
        
        port = get_local_port()
        assert port == 9000

    def test_get_local_port_invalid_value(self, monkeypatch):
        """Test get_local_port raises error for invalid port values."""
        monkeypatch.setenv("AGENTCORE_RUNTIME_LOCAL_PORT", "invalid")
        
        with pytest.raises(ValueError, match="Invalid port value"):
            get_local_port()

    def test_get_local_port_out_of_range_low(self, monkeypatch):
        """Test get_local_port raises error for port value too low."""
        monkeypatch.setenv("AGENTCORE_RUNTIME_LOCAL_PORT", "0")
        
        with pytest.raises(ValueError, match="Invalid port value in AGENTCORE_RUNTIME_LOCAL_PORT"):
            get_local_port()

    def test_get_local_port_out_of_range_high(self, monkeypatch):
        """Test get_local_port raises error for port value too high."""
        monkeypatch.setenv("AGENTCORE_RUNTIME_LOCAL_PORT", "65536")
        
        with pytest.raises(ValueError, match="Invalid port value in AGENTCORE_RUNTIME_LOCAL_PORT"):
            get_local_port()

    def test_get_local_port_edge_cases(self, monkeypatch):
        """Test get_local_port with edge case valid values."""
        # Test minimum valid port
        monkeypatch.setenv("AGENTCORE_RUNTIME_LOCAL_PORT", "1")
        assert get_local_port() == 1
        
        # Test maximum valid port
        monkeypatch.setenv("AGENTCORE_RUNTIME_LOCAL_PORT", "65535")
        assert get_local_port() == 65535