#!/usr/bin/env python3
"""Simplified tests for LocalProcessManager."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.local_process_manager import (
    LocalAgentProcess,
    LocalProcessManager,
)


class TestLocalAgentProcess:
    """Test LocalAgentProcess functionality."""

    def test_agent_process_creation(self):
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
        assert agent.started_at is not None

    def test_agent_process_serialization(self):
        """Test agent process serialization/deserialization."""
        agent = LocalAgentProcess(
            name="test-agent",
            pid=12345,
            port=8080,
            log_file="/tmp/test.log",
            started_at="2025-01-01T00:00:00Z",
            config_path="/tmp/config.yaml"
        )
        
        # Test to_dict
        data = agent.to_dict()
        expected_keys = {"name", "pid", "port", "log_file", "started_at", "config_path"}
        assert set(data.keys()) == expected_keys
        
        # Test from_dict
        agent2 = LocalAgentProcess.from_dict(data)
        assert agent2.name == agent.name
        assert agent2.pid == agent.pid
        assert agent2.port == agent.port
        assert agent2.log_file == agent.log_file
        assert agent2.started_at == agent.started_at
        assert agent2.config_path == agent.config_path

    def test_is_running_process_exists(self):
        """Test is_running when process exists."""
        # Use current process PID (should be running)
        agent = LocalAgentProcess(
            name="test-agent",
            pid=os.getpid(),
            port=8080
        )
        
        assert agent.is_running() is True

    def test_is_running_process_not_exists(self):
        """Test is_running when process doesn't exist."""
        # Use a PID that's very unlikely to exist
        agent = LocalAgentProcess(
            name="test-agent",
            pid=999999,
            port=8080
        )
        
        assert agent.is_running() is False


def test_manager_initialization():
    """Test manager initialization creates directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        assert manager.state_dir.exists()
        assert manager.logs_dir.exists()
        assert manager.state_file == temp_path / "local_agents.json"


def test_load_state_empty():
    """Test loading state when no state file exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        agents = manager._load_state()
        assert agents == []


def test_save_and_load_state():
    """Test saving and loading agent state."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        # Create test agents
        agent1 = LocalAgentProcess("agent1", os.getpid(), 8080)
        agent2 = LocalAgentProcess("agent2", 999999, 8081)  # Non-existent PID
        
        # Save state
        manager._save_state([agent1, agent2])
        
        # Load state (should only return running processes)
        agents = manager._load_state()
        
        # Only agent1 should be returned (agent2 has non-existent PID)
        assert len(agents) == 1
        assert agents[0].name == "agent1"
        assert agents[0].pid == os.getpid()


def test_get_agent_exists():
    """Test getting an existing agent."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
        manager._save_state([agent])
        
        found_agent = manager.get_agent("test-agent")
        assert found_agent is not None
        assert found_agent.name == "test-agent"


def test_get_agent_not_exists():
    """Test getting a non-existent agent."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        found_agent = manager.get_agent("non-existent")
        assert found_agent is None


def test_cleanup_stale_processes():
    """Test cleanup of stale processes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        # Create agents with different PIDs
        agent1 = LocalAgentProcess("agent1", os.getpid(), 8080)  # Running
        agent2 = LocalAgentProcess("agent2", 999999, 8081)       # Not running
        
        manager._save_state([agent1, agent2])
        
        # Cleanup stale processes
        manager.cleanup_stale_processes()
        
        # Only running agent should remain
        agents = manager._load_state()
        assert len(agents) == 1
        assert agents[0].name == "agent1"


def test_load_state_corrupted_json():
    """Test loading state with corrupted JSON file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        manager = LocalProcessManager(state_dir=temp_path)
        
        # Create corrupted JSON file
        with open(manager.state_file, 'w') as f:
            f.write("invalid json {")
        
        agents = manager._load_state()
        assert agents == []


def test_manager_default_state_dir():
    """Test manager with default state directory."""
    manager = LocalProcessManager()
    expected_dir = Path.cwd() / ".agentcore"
    assert manager.state_dir == expected_dir
    assert manager.state_file == expected_dir / "local_agents.json"
    assert manager.logs_dir == expected_dir / "logs"