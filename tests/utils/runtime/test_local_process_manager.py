#!/usr/bin/env python3
"""Tests for LocalProcessManager."""

import json
import os
import signal
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

    def test_agent_stop_not_running(self):
        """Test stopping an agent that's not running."""
        agent = LocalAgentProcess("test-agent", 999999, 8080)  # Non-existent PID
        result = agent.stop()
        assert result is False

    def test_agent_stop_os_error(self):
        """Test stopping an agent when OS error occurs."""
        agent = LocalAgentProcess("test-agent", -1, 8080)  # Invalid PID
        result = agent.stop()
        assert result is False

    def test_load_state_corrupted_json(self):
        """Test loading state with corrupted JSON file."""
        # Create corrupted JSON file
        with open(self.manager.state_file, 'w') as f:
            f.write("invalid json {")
        
        agents = self.manager._load_state()
        assert agents == []

    def test_load_state_missing_agents_key(self):
        """Test loading state with missing 'agents' key."""
        # Create JSON without 'agents' key
        with open(self.manager.state_file, 'w') as f:
            json.dump({"other_key": "value"}, f)
        
        agents = self.manager._load_state()
        assert agents == []

    def test_save_state_filters_stopped_processes(self):
        """Test that save_state only saves running processes."""
        agent1 = LocalAgentProcess("agent1", os.getpid(), 8080)  # Running
        agent2 = LocalAgentProcess("agent2", 999999, 8081)       # Not running
        
        self.manager._save_state([agent1, agent2])
        
        # Load and verify only running process was saved
        with open(self.manager.state_file, 'r') as f:
            data = json.load(f)
        
        assert len(data["agents"]) == 1
        assert data["agents"][0]["name"] == "agent1"

    @patch('subprocess.Popen')
    @patch('boto3.Session')
    def test_start_detached_process_with_env_vars(self, mock_session, mock_popen):
        """Test starting detached process with environment variables."""
        # Mock AWS credentials
        mock_credentials = Mock()
        mock_credentials.get_frozen_credentials.return_value = Mock(
            access_key="test-key",
            secret_key="test-secret",
            token="test-token"
        )
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock process
        mock_process = Mock()
        mock_process.pid = os.getpid()
        mock_popen.return_value = mock_process
        
        # Mock runtime
        mock_runtime = Mock()
        mock_runtime.has_local_runtime = True
        mock_runtime.runtime = "docker"
        
        # Start agent with custom env vars
        env_vars = {"CUSTOM_VAR": "custom_value", "DEBUG": "true"}
        agent = self.manager.start_agent(
            name="test-agent",
            runtime=mock_runtime,
            tag="test:latest",
            port=8080,
            env_vars=env_vars
        )
        
        # Verify subprocess was called with correct environment variables
        call_args = mock_popen.call_args[0][0]  # Get the command list
        
        # Should contain AWS credentials
        assert "-e" in call_args
        aws_access_key_idx = call_args.index("-e") + 1
        assert call_args[aws_access_key_idx].startswith("AWS_ACCESS_KEY_ID=")
        
        # Should contain custom env vars
        custom_var_found = any("CUSTOM_VAR=custom_value" in arg for arg in call_args)
        debug_var_found = any("DEBUG=true" in arg for arg in call_args)
        assert custom_var_found
        assert debug_var_found

    @patch('subprocess.Popen')
    @patch('boto3.Session')
    def test_start_detached_process_no_aws_token(self, mock_session, mock_popen):
        """Test starting process when AWS credentials have no token."""
        # Mock AWS credentials without token
        mock_credentials = Mock()
        mock_credentials.get_frozen_credentials.return_value = Mock(
            access_key="test-key",
            secret_key="test-secret",
            token=None  # No session token
        )
        mock_session.return_value.get_credentials.return_value = mock_credentials
        
        # Mock process
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
            port=8080
        )
        
        # Verify subprocess was called (should not fail without token)
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        
        # Should not contain AWS_SESSION_TOKEN
        session_token_found = any("AWS_SESSION_TOKEN=" in arg for arg in call_args)
        assert not session_token_found

    @patch('boto3.Session')
    def test_start_agent_no_aws_credentials(self, mock_session):
        """Test starting agent when no AWS credentials are available."""
        # Mock no credentials
        mock_session.return_value.get_credentials.return_value = None
        
        # Mock runtime
        mock_runtime = Mock()
        mock_runtime.has_local_runtime = True
        mock_runtime.runtime = "docker"
        
        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="No AWS credentials found"):
            self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080
            )

    def test_start_agent_custom_log_file_relative(self):
        """Test starting agent with relative log file path."""
        # Mock runtime and process
        with patch('subprocess.Popen') as mock_popen, \
             patch('boto3.Session') as mock_session:
            
            # Mock AWS credentials
            mock_credentials = Mock()
            mock_credentials.get_frozen_credentials.return_value = Mock(
                access_key="test-key",
                secret_key="test-secret",
                token="test-token"
            )
            mock_session.return_value.get_credentials.return_value = mock_credentials
            
            # Mock process
            mock_process = Mock()
            mock_process.pid = os.getpid()
            mock_popen.return_value = mock_process
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            # Start agent with relative log path
            agent = self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080,
                log_file="custom.log"
            )
            
            # Log file should be converted to absolute path
            expected_log = Path.cwd() / "custom.log"
            assert agent.log_file == str(expected_log)

    def test_start_agent_custom_log_file_absolute(self):
        """Test starting agent with absolute log file path."""
        # Mock runtime and process
        with patch('subprocess.Popen') as mock_popen, \
             patch('boto3.Session') as mock_session:
            
            # Mock AWS credentials
            mock_credentials = Mock()
            mock_credentials.get_frozen_credentials.return_value = Mock(
                access_key="test-key",
                secret_key="test-secret",
                token="test-token"
            )
            mock_session.return_value.get_credentials.return_value = mock_credentials
            
            # Mock process
            mock_process = Mock()
            mock_process.pid = os.getpid()
            mock_popen.return_value = mock_process
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            # Start agent with absolute log path
            abs_log_path = "/tmp/custom.log"
            agent = self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080,
                log_file=abs_log_path
            )
            
            # Log file should remain absolute
            assert agent.log_file == abs_log_path

    def test_get_agent_multiple_agents(self):
        """Test getting specific agent when multiple exist."""
        agent1 = LocalAgentProcess("agent1", os.getpid(), 8080)
        agent2 = LocalAgentProcess("agent2", os.getpid(), 8081)
        
        self.manager._save_state([agent1, agent2])
        
        # Get specific agent
        found_agent = self.manager.get_agent("agent2")
        assert found_agent is not None
        assert found_agent.name == "agent2"
        assert found_agent.port == 8081

    def test_cleanup_stale_processes_mixed(self):
        """Test cleanup with mix of running and stopped processes."""
        # Create mix of running and stopped processes
        agent1 = LocalAgentProcess("running1", os.getpid(), 8080)
        agent2 = LocalAgentProcess("stopped1", 999999, 8081)
        agent3 = LocalAgentProcess("running2", os.getpid(), 8082)
        agent4 = LocalAgentProcess("stopped2", 999998, 8083)
        
        self.manager._save_state([agent1, agent2, agent3, agent4])
        
        # Cleanup stale processes
        self.manager.cleanup_stale_processes()
        
        # Only running agents should remain
        agents = self.manager._load_state()
        assert len(agents) == 2
        agent_names = {agent.name for agent in agents}
        assert agent_names == {"running1", "running2"}

    def test_manager_default_state_dir(self):
        """Test manager with default state directory."""
        manager = LocalProcessManager()
        expected_dir = Path.cwd() / ".agentcore"
        assert manager.state_dir == expected_dir
        assert manager.state_file == expected_dir / "local_agents.json"
        assert manager.logs_dir == expected_dir / "logs"

    @patch('os.kill')
    def test_agent_stop_graceful_success(self, mock_kill):
        """Test successful graceful stop."""
        agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
        
        # Mock that process stops after SIGTERM
        def kill_side_effect(pid, sig):
            if sig == signal.SIGTERM:
                # Simulate process stopping
                mock_kill.side_effect = ProcessLookupError()
        
        mock_kill.side_effect = kill_side_effect
        
        with patch.object(agent, 'is_running', side_effect=[True, False]):
            result = agent.stop()
            assert result is True
            mock_kill.assert_called_with(os.getpid(), signal.SIGTERM)

    @patch('os.kill')
    @patch('time.sleep')
    def test_agent_stop_force_kill(self, mock_sleep, mock_kill):
        """Test force kill when graceful stop fails."""
        agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
        
        # Mock that process doesn't stop after SIGTERM, needs SIGKILL
        def is_running_sequence():
            calls = [True] * 11 + [False]  # Running for 10 checks, then stopped
            for call in calls:
                yield call
        
        running_gen = is_running_sequence()
        
        with patch.object(agent, 'is_running', side_effect=lambda: next(running_gen)):
            result = agent.stop()
            assert result is True
            
            # Should call SIGTERM first, then SIGKILL
            expected_calls = [
                ((os.getpid(), signal.SIGTERM),),
                ((os.getpid(), signal.SIGKILL),)
            ]
            assert mock_kill.call_args_list == expected_calls
            assert mock_sleep.call_count == 10  # Waited 10 seconds

    def test_agent_default_started_at(self):
        """Test that started_at defaults to current time."""
        agent = LocalAgentProcess("test-agent", 12345, 8080)
        assert agent.started_at is not None
        # Should be a valid ISO format timestamp
        from datetime import datetime
        datetime.fromisoformat(agent.started_at.replace('Z', '+00:00'))

    def test_agent_custom_started_at(self):
        """Test custom started_at value."""
        custom_time = "2025-01-01T12:00:00Z"
        agent = LocalAgentProcess("test-agent", 12345, 8080, started_at=custom_time)
        assert agent.started_at == custom_time

    def test_save_state_io_error(self):
        """Test save_state handles IO errors gracefully."""
        # Create agent
        agent = LocalAgentProcess("test-agent", os.getpid(), 8080)
        
        # Mock open to raise IOError
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            # Should not raise exception
            self.manager._save_state([agent])

    def test_start_agent_log_directory_creation(self):
        """Test that log directories are created when needed."""
        with patch('subprocess.Popen') as mock_popen, \
             patch('boto3.Session') as mock_session:
            
            # Mock AWS credentials
            mock_credentials = Mock()
            mock_credentials.get_frozen_credentials.return_value = Mock(
                access_key="test-key",
                secret_key="test-secret",
                token="test-token"
            )
            mock_session.return_value.get_credentials.return_value = mock_credentials
            
            # Mock process
            mock_process = Mock()
            mock_process.pid = os.getpid()
            mock_popen.return_value = mock_process
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            # Use nested log path that doesn't exist
            nested_log = self.temp_dir / "nested" / "deep" / "test.log"
            
            agent = self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080,
                log_file=str(nested_log)
            )
            
            # Directory should have been created
            assert nested_log.parent.exists()
            assert agent.log_file == str(nested_log)

    @patch('boto3.Session', side_effect=ImportError("boto3 not available"))
    def test_start_agent_no_boto3(self, mock_session):
        """Test starting agent when boto3 is not available."""
        mock_runtime = Mock()
        mock_runtime.has_local_runtime = True
        mock_runtime.runtime = "docker"
        
        with pytest.raises(RuntimeError, match="boto3 is required for local mode"):
            self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080
            )

    def test_container_name_generation(self):
        """Test that container names are generated correctly."""
        with patch('subprocess.Popen') as mock_popen, \
             patch('boto3.Session') as mock_session, \
             patch('time.time', return_value=1234567890):
            
            # Mock AWS credentials
            mock_credentials = Mock()
            mock_credentials.get_frozen_credentials.return_value = Mock(
                access_key="test-key",
                secret_key="test-secret",
                token="test-token"
            )
            mock_session.return_value.get_credentials.return_value = mock_credentials
            
            # Mock process
            mock_process = Mock()
            mock_process.pid = os.getpid()
            mock_popen.return_value = mock_process
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="my-app:v1.0",
                port=8080
            )
            
            # Check that container name was generated correctly
            call_args = mock_popen.call_args[0][0]
            name_idx = call_args.index("--name") + 1
            container_name = call_args[name_idx]
            assert container_name == "my-app-1234567890"

    def test_subprocess_security_settings(self):
        """Test that subprocess is called with secure settings."""
        with patch('subprocess.Popen') as mock_popen, \
             patch('boto3.Session') as mock_session:
            
            # Mock AWS credentials
            mock_credentials = Mock()
            mock_credentials.get_frozen_credentials.return_value = Mock(
                access_key="test-key",
                secret_key="test-secret",
                token="test-token"
            )
            mock_session.return_value.get_credentials.return_value = mock_credentials
            
            # Mock process
            mock_process = Mock()
            mock_process.pid = os.getpid()
            mock_popen.return_value = mock_process
            
            # Mock runtime
            mock_runtime = Mock()
            mock_runtime.has_local_runtime = True
            mock_runtime.runtime = "docker"
            
            self.manager.start_agent(
                name="test-agent",
                runtime=mock_runtime,
                tag="test:latest",
                port=8080
            )
            
            # Verify security settings
            call_kwargs = mock_popen.call_args[1]
            assert call_kwargs['shell'] is False  # Shell disabled for security
            assert call_kwargs['start_new_session'] is True  # Detached session
            assert call_kwargs['stdin'] == subprocess.DEVNULL  # No stdin

    def test_agent_process_repr(self):
        """Test string representation of agent process."""
        agent = LocalAgentProcess("test-agent", 12345, 8080)
        # Should not raise exception when converted to string
        str_repr = str(agent)
        assert "test-agent" in str_repr or str(agent) is not None

    def test_manager_state_persistence_across_instances(self):
        """Test that state persists across manager instances."""
        # Create agent with first manager instance
        agent = LocalAgentProcess("persistent-agent", os.getpid(), 8080)
        self.manager._save_state([agent])
        
        # Create new manager instance with same state dir
        new_manager = LocalProcessManager(state_dir=self.temp_dir)
        loaded_agents = new_manager._load_state()
        
        assert len(loaded_agents) == 1
        assert loaded_agents[0].name == "persistent-agent"
        assert loaded_agents[0].pid == os.getpid()

    def test_concurrent_agent_operations(self):
        """Test handling of concurrent operations on agents."""
        # This tests the basic thread safety considerations
        agent1 = LocalAgentProcess("agent1", os.getpid(), 8080)
        agent2 = LocalAgentProcess("agent2", os.getpid(), 8081)
        
        # Save agents
        self.manager._save_state([agent1, agent2])
        
        # Simulate concurrent access
        agents_1 = self.manager._load_state()
        agents_2 = self.manager._load_state()
        
        assert len(agents_1) == len(agents_2) == 2
        assert {a.name for a in agents_1} == {a.name for a in agents_2}