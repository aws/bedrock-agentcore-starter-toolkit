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


class TestLocalAgentProcessStop:
    """Test LocalAgentProcess stop functionality."""

    @patch('os.kill')
    def test_stop_not_running(self, mock_kill):
        """Test stopping a process that's not running."""
        agent = LocalAgentProcess("test-agent", 999999, 8080)
        
        # Mock is_running to return False
        with patch.object(agent, 'is_running', return_value=False):
            result = agent.stop()
            assert result is False
            mock_kill.assert_not_called()

    @patch('os.kill')
    @patch('time.sleep')
    def test_stop_graceful_shutdown(self, mock_sleep, mock_kill):
        """Test graceful process shutdown."""
        agent = LocalAgentProcess("test-agent", 12345, 8080)
        
        # Mock is_running to return True initially, then False after SIGTERM
        with patch.object(agent, 'is_running', side_effect=[True, False]):
            result = agent.stop()
            assert result is True
            mock_kill.assert_called_once_with(12345, 15)  # SIGTERM = 15

    @patch('os.kill')
    @patch('time.sleep')
    def test_stop_force_kill(self, mock_sleep, mock_kill):
        """Test force killing a process that doesn't respond to SIGTERM."""
        agent = LocalAgentProcess("test-agent", 12345, 8080)
        
        # Mock is_running to always return True (process doesn't respond to SIGTERM)
        with patch.object(agent, 'is_running', return_value=True):
            result = agent.stop()
            assert result is True
            # Should call SIGTERM first, then SIGKILL
            assert mock_kill.call_count == 2  # 1 SIGTERM + 1 SIGKILL
            mock_kill.assert_any_call(12345, 15)  # SIGTERM
            mock_kill.assert_any_call(12345, 9)   # SIGKILL

    @patch('os.kill', side_effect=OSError("Process not found"))
    def test_stop_process_not_found(self, mock_kill):
        """Test stopping a process that no longer exists."""
        agent = LocalAgentProcess("test-agent", 12345, 8080)
        
        with patch.object(agent, 'is_running', return_value=True):
            result = agent.stop()
            assert result is False


class TestLocalProcessManagerStartAgent:
    """Test LocalProcessManager start_agent functionality."""

    def test_start_agent_already_running(self):
        """Test starting an agent that's already running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Create a running agent
            agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
            manager._save_state([agent])
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            
            # Try to start the same agent again
            with pytest.raises(RuntimeError, match="Agent 'test-agent' is already running"):
                manager.start_agent("test-agent", mock_runtime, "test:latest", 8080)

    @patch('subprocess.Popen')
    @patch('boto3.Session')
    def test_start_agent_success(self, mock_session, mock_popen):
        """Test successfully starting an agent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            # Mock boto3 session and credentials
            mock_creds = Mock()
            mock_creds.get_frozen_credentials.return_value = Mock(
                access_key="test_key",
                secret_key="test_secret",
                token="test_token"
            )
            mock_session.return_value.get_credentials.return_value = mock_creds
            
            # Mock subprocess
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            # Start agent
            agent = manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080,
                env_vars={"TEST_VAR": "test_value"}
            )
            
            assert agent.name == "test-agent"
            assert agent.pid == 12345
            assert agent.port == 8080
            assert agent.log_file.endswith("test-agent.log")
            
            # Verify process was started with correct arguments
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            cmd = args[0]
            
            assert "docker" in cmd
            assert "run" in cmd
            assert "--rm" in cmd
            assert "-p" in cmd
            assert "8080:8080" in cmd
            assert "test:latest" in cmd
            assert "-e" in cmd
            assert "TEST_VAR=test_value" in cmd

    def test_start_agent_no_runtime(self):
        """Test starting an agent with no container runtime."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Mock runtime without local runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = False
            
            with pytest.raises(RuntimeError, match="No container runtime available"):
                manager.start_agent("test-agent", mock_runtime, "test:latest", 8080)

    @patch('boto3.Session')
    def test_start_agent_no_aws_credentials(self, mock_session):
        """Test starting an agent without AWS credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            
            # Mock boto3 session with no credentials
            mock_session.return_value.get_credentials.return_value = None
            
            with pytest.raises(RuntimeError, match="No AWS credentials found"):
                manager.start_agent("test-agent", mock_runtime, "test:latest", 8080)

    @patch('subprocess.Popen')
    @patch('boto3.Session')
    def test_start_agent_custom_log_file(self, mock_session, mock_popen):
        """Test starting an agent with custom log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            # Mock boto3 session and credentials
            mock_creds = Mock()
            mock_creds.get_frozen_credentials.return_value = Mock(
                access_key="test_key",
                secret_key="test_secret",
                token=None  # Test without token
            )
            mock_session.return_value.get_credentials.return_value = mock_creds
            
            # Mock subprocess
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            # Start agent with custom log file
            custom_log = temp_path / "custom.log"
            agent = manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080,
                log_file=str(custom_log)
            )
            
            assert agent.log_file == str(custom_log)

    @patch('boto3.Session', side_effect=ImportError("boto3 not available"))
    def test_start_agent_no_boto3(self, mock_session):
        """Test starting an agent without boto3 installed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            
            with pytest.raises(RuntimeError, match="boto3 is required for local mode"):
                manager.start_agent("test-agent", mock_runtime, "test:latest", 8080)


class TestLocalProcessManagerAdditional:
    """Test additional LocalProcessManager functionality."""

    @patch('subprocess.Popen')
    @patch('boto3.Session')
    def test_start_detached_process_success(self, mock_session, mock_popen):
        """Test the _start_detached_process method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            # Mock boto3 session and credentials
            mock_creds = Mock()
            mock_creds.get_frozen_credentials.return_value = Mock(
                access_key="test_key",
                secret_key="test_secret",
                token="test_token"
            )
            mock_session.return_value.get_credentials.return_value = mock_creds
            
            # Mock subprocess
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            # Test the method
            log_path = temp_path / "test.log"
            pid = manager._start_detached_process(
                runtime=mock_runtime,
                tag="test:latest",
                port=8080,
                env_vars={"TEST_VAR": "test_value"},
                log_path=log_path
            )
            
            assert pid == 12345
            mock_popen.assert_called_once()

    def test_save_state_error_handling(self):
        """Test error handling in _save_state method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Make the state file read-only to cause an error
            manager.state_file.touch()
            manager.state_file.chmod(0o444)
            
            # Create test agent
            agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
            
            # This should not raise an exception, just log an error
            try:
                manager._save_state([agent])
                # If we get here, the error was handled gracefully
                assert True
            except Exception:
                # If an exception is raised, the test fails
                assert False, "Expected error to be handled gracefully"
            finally:
                # Clean up - make file writable again
                manager.state_file.chmod(0o644)

    def test_load_state_with_invalid_agent_data(self):
        """Test loading state with invalid agent data raises TypeError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = LocalProcessManager(state_dir=temp_path)
            
            # Create state file with invalid agent data
            invalid_data = {
                "agents": [
                    {"name": "valid-agent", "pid": os.getpid(), "port": 8080},
                    {"name": "invalid-agent"},  # Missing required fields
                ]
            }
            
            with open(manager.state_file, 'w') as f:
                json.dump(invalid_data, f)
            
            # Should raise TypeError for invalid agent data
            with pytest.raises(TypeError):
                manager._load_state()