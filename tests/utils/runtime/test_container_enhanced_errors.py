"""Tests for enhanced Docker error detection in ContainerRuntime."""

import pytest
import subprocess
from unittest.mock import patch, MagicMock

from bedrock_agentcore_starter_toolkit.utils.runtime.container import ContainerRuntime, RuntimeStatus


class TestEnhancedDockerErrorDetection:
    """Test enhanced Docker error detection for Issue #42."""

    def test_permission_denied_detection(self):
        """Test detection of Docker permission denied errors."""
        def mock_permission_denied(*args, **kwargs):
            if args[0] == ["docker", "version"]:
                result = MagicMock()
                result.returncode = 1
                result.stderr = "permission denied while trying to connect to the Docker daemon socket"
                result.stdout = ""
                return result
            return subprocess.run(*args, **kwargs)

        with patch('subprocess.run', side_effect=mock_permission_denied):
            runtime = ContainerRuntime.__new__(ContainerRuntime)
            status = runtime._detect_runtime_status("docker")
            
            assert not status.available
            assert status.error_type == "permission_denied"
            assert "Permission denied" in status.error_message
            assert "sudo usermod -aG docker" in status.error_message

    def test_daemon_not_running_detection(self):
        """Test detection of Docker daemon not running errors."""
        def mock_daemon_not_running(*args, **kwargs):
            if args[0] == ["docker", "version"]:
                result = MagicMock()
                result.returncode = 1
                result.stderr = "Cannot connect to the Docker daemon. Is the docker daemon running?"
                result.stdout = ""
                return result
            return subprocess.run(*args, **kwargs)

        with patch('subprocess.run', side_effect=mock_daemon_not_running):
            runtime = ContainerRuntime.__new__(ContainerRuntime)
            status = runtime._detect_runtime_status("docker")
            
            assert not status.available
            assert status.error_type == "daemon_not_running"
            assert "daemon is not running" in status.error_message
            assert "systemctl start docker" in status.error_message

    def test_not_installed_detection(self):
        """Test detection of Docker not installed errors."""
        def mock_not_installed(*args, **kwargs):
            if args[0] == ["docker", "version"]:
                raise FileNotFoundError("docker: command not found")
            return subprocess.run(*args, **kwargs)

        with patch('subprocess.run', side_effect=mock_not_installed):
            runtime = ContainerRuntime.__new__(ContainerRuntime)
            status = runtime._detect_runtime_status("docker")
            
            assert not status.available
            assert status.error_type == "not_found"
            assert "not installed" in status.error_message or "not in PATH" in status.error_message

    def test_successful_detection(self):
        """Test detection of working Docker."""
        def mock_working_docker(*args, **kwargs):
            if args[0] == ["docker", "version"]:
                result = MagicMock()
                result.returncode = 0
                result.stderr = ""
                result.stdout = "Docker version 20.10.0"
                return result
            return subprocess.run(*args, **kwargs)

        with patch('subprocess.run', side_effect=mock_working_docker):
            runtime = ContainerRuntime.__new__(ContainerRuntime)
            status = runtime._detect_runtime_status("docker")
            
            assert status.available
            assert status.error_type == "success"
            assert status.error_message == ""

    def test_enhanced_error_message_generation(self):
        """Test generation of enhanced error messages."""
        runtime = ContainerRuntime.__new__(ContainerRuntime)
        
        # Test permission denied scenario
        statuses = {
            "docker": RuntimeStatus(False, "permission_denied", 1, "Permission denied accessing docker. Try: sudo usermod -aG docker $USER && newgrp docker")
        }
        
        error_msg = runtime._generate_enhanced_error_message(statuses)
        
        assert "Container runtime detection failed:" in error_msg
        assert "Permission denied accessing docker" in error_msg
        assert "sudo usermod -aG docker" in error_msg
        assert "https://docs.docker.com/engine/install/" in error_msg

    def test_issue_42_main_scenario(self):
        """Test the main Issue #42 scenario: Docker installed but permission denied."""
        def mock_permission_denied(*args, **kwargs):
            if args[0] == ["docker", "version"]:
                result = MagicMock()
                result.returncode = 1
                result.stderr = "permission denied while trying to connect to the Docker daemon socket"
                result.stdout = ""
                return result
            return subprocess.run(*args, **kwargs)

        with patch('subprocess.run', side_effect=mock_permission_denied):
            with pytest.raises(RuntimeError) as exc_info:
                ContainerRuntime("docker")
            
            error_message = str(exc_info.value)
            
            # Verify it's NOT the old generic message
            assert "is not installed" not in error_message
            
            # Verify it IS the new specific message
            assert "Permission denied" in error_message
            assert "sudo usermod -aG docker" in error_message