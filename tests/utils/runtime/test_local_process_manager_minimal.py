#!/usr/bin/env python3
"""Minimal tests for LocalProcessManager to identify crash cause."""

import os
import tempfile
from pathlib import Path

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.local_process_manager import (
    LocalAgentProcess,
    LocalProcessManager,
)


def test_agent_process_basic():
    """Test basic agent process creation."""
    agent = LocalAgentProcess(
        name="test-agent",
        pid=12345,
        port=8080,
        log_file="/tmp/test.log"
    )
    
    assert agent.name == "test-agent"
    assert agent.pid == 12345
    assert agent.port == 8080
    assert agent.log_file == "/tmp/test.log"


def test_agent_serialization():
    """Test agent serialization."""
    agent = LocalAgentProcess(
        name="test-agent",
        pid=12345,
        port=8080
    )
    
    data = agent.to_dict()
    agent2 = LocalAgentProcess.from_dict(data)
    
    assert agent2.name == agent.name
    assert agent2.pid == agent.pid
    assert agent2.port == agent.port


def test_manager_basic():
    """Test basic manager functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        assert manager.state_dir.exists()
        assert manager.logs_dir.exists()


def test_is_running_current_process():
    """Test is_running with current process."""
    agent = LocalAgentProcess("test", os.getpid(), 8080)
    assert agent.is_running() is True


def test_is_running_fake_process():
    """Test is_running with fake process."""
    agent = LocalAgentProcess("test", 999999, 8080)
    assert agent.is_running() is False