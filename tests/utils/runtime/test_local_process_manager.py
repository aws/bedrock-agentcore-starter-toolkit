#!/usr/bin/env python3
"""Tests for LocalProcessManager."""

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


class TestLocalProcessManager:
    """Test LocalProcessManager functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = LocalProcessManager(state_dir=self.temp_dir)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_manager_initialization(self):
        """Test manager initialization creates directories."""
        assert self.manager.state_dir.exists()
        assert self.manager.logs_dir.exists()
        assert self.manager.state_file == self.temp_dir / "local_agents.json"

    def test_load_state_empty(self):
        """Test loading state when no state file exists."""
        agents = self.manager._load_state()
        assert agents == []

    def test_save_and_load_state(self):
        """Test saving and loading agent state."""
        # Create test agents
        agent1 = LocalAgentProcess("agent1", os.getpid(), 8080)
        agent2 = LocalAgentProcess("agent2", 999999, 8081)  # Non-existent PID
        
        # Save state
        self.manager._save_state([agent1, agent2])
        
        # Load state (should only return running processes)
        agents = self.manager._load_state()
        
        # Only agent1 should be returned (agent2 has non-existent PID)
        assert len(agents) == 1
        assert agents[0].name == "agent1"
        assert agents[0].pid == os.getpid()

    def test_get_agent_exists(self):
        """Test getting an existing agent."""
        agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
        self.manager._save_state([agent])
        
        found_agent = self.manager.get_agent("test-agent")
        assert found_agent is not None
        assert found_agent.name == "test-agent"

    def test_get_agent_not_exists(self):
        """Test getting a non-existent agent."""
        found_agent = self.manager.get_agent("non-existent")
        assert found_agent is None

    def test_start_agent_duplicate_name(self):
        """Test starting agent with duplicate name fails."""
        # Create existing agent
        agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
        self.manager._save_state([agent])
        
        # Mock runtime
        mock_runtime = Mock()
        
        # Try to start agent with same name
        with pytest.raises(RuntimeError, match="Agent 'test-agent' is already running"):
            self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8081
            )

    @patch('subprocess.Popen')
    @patch('boto3.Session')
    def test_start_agent_success(self, mock_session, mock_popen):
        """Test successful agent start."""
        # Mock AWS credentials
        mock_credentials = Mock()
        mock_credentials.get_frozen_credentials.return_value = Mock(
            access_key="test-key",
            secret_key="test-secret",
            token="test-token"
        )
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock process (use current PID so it appears as running)
        mock_process = Mock()
        mock_process.pid = os.getpid()
        mock_popen.return_value = mock_process
        
        # Mock runtime
        mock_runtime = Mock()
        mock_runtime.has_local_runtime = True
        mock_runtime.runtime = "docker"
        
        # Start agent
        agent = self.manager.start_agent(
            name="test-agent",
            runtime=mock_runtime,
            tag="test:latest",
            port=8080,
            env_vars={"TEST": "value"}
        )
        
        assert agent.name == "test-agent"
        assert agent.pid == os.getpid()
        assert agent.port == 8080
        assert agent.log_file is not None
        
        # Verify process was started
        mock_popen.assert_called_once()
        
        # Verify state was saved
        agents = self.manager._load_state()
        assert len(agents) == 1
        assert agents[0].name == "test-agent"

    def test_start_agent_no_runtime(self):
        """Test starting agent without container runtime fails."""
        mock_runtime = Mock()
        mock_runtime.has_local_runtime = False
        
        with pytest.raises(RuntimeError, match="No container runtime available"):
            self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080
            )

    def test_cleanup_stale_processes(self):
        """Test cleanup of stale processes."""
        # Create agents with different PIDs
        agent1 = LocalAgentProcess("agent1", os.getpid(), 8080)  # Running
        agent2 = LocalAgentProcess("agent2", 999999, 8081)       # Not running
        
        self.manager._save_state([agent1, agent2])
        
        # Cleanup stale processes
        self.manager.cleanup_stale_processes()
        
        # Only running agent should remain
        agents = self.manager._load_state()
        assert len(agents) == 1
        assert agents[0].name == "agent1"