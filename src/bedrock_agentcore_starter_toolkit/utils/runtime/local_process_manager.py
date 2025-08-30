"""Local process manager for detached agent execution."""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LocalAgentProcess:
    """Represents a local agent process."""
    
    def __init__(
        self,
        name: str,
        pid: int,
        port: int,
        log_file: Optional[str] = None,
        started_at: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        self.name = name
        self.pid = pid
        self.port = port
        self.log_file = log_file
        self.started_at = started_at or datetime.now(timezone.utc).isoformat()
        self.config_path = config_path
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "pid": self.pid,
            "port": self.port,
            "log_file": self.log_file,
            "started_at": self.started_at,
            "config_path": self.config_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LocalAgentProcess":
        """Create from dictionary."""
        return cls(**data)
    
    def is_running(self) -> bool:
        """Check if the process is still running."""
        try:
            # Send signal 0 to check if process exists
            os.kill(self.pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def stop(self) -> bool:
        """Stop the process gracefully."""
        if not self.is_running():
            return False
        
        try:
            # Try graceful shutdown first
            os.kill(self.pid, signal.SIGTERM)
            
            # Wait up to 10 seconds for graceful shutdown
            for _ in range(10):
                if not self.is_running():
                    return True
                time.sleep(1)
            
            # Force kill if still running
            os.kill(self.pid, signal.SIGKILL)
            return True
        except (OSError, ProcessLookupError):
            return False


class LocalProcessManager:
    """Manages local agent processes."""
    
    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or Path.cwd() / ".agentcore"
        self.state_file = self.state_dir / "local_agents.json"
        self.logs_dir = self.state_dir / "logs"
        
        # Ensure directories exist
        self.state_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    def _load_state(self) -> List[LocalAgentProcess]:
        """Load agent state from file."""
        if not self.state_file.exists():
            return []
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            agents = []
            for agent_data in data.get("agents", []):
                agent = LocalAgentProcess.from_dict(agent_data)
                # Only keep running processes
                if agent.is_running():
                    agents.append(agent)
            
            return agents
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load agent state: {e}")
            return []
    
    def _save_state(self, agents: List[LocalAgentProcess]) -> None:
        """Save agent state to file."""
        try:
            data = {
                "agents": [agent.to_dict() for agent in agents if agent.is_running()]
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save agent state: {e}")
    
    def start_agent(
        self,
        name: str,
        runtime,
        tag: str,
        port: int,
        env_vars: Optional[Dict] = None,
        log_file: Optional[str] = None,
        config_path: Optional[str] = None,
    ) -> LocalAgentProcess:
        """Start an agent in detached mode."""
        # Check if agent with same name is already running
        existing = self.get_agent(name)
        if existing and existing.is_running():
            raise RuntimeError(f"Agent '{name}' is already running (PID: {existing.pid})")
        
        # Determine log file path
        if log_file:
            log_path = Path(log_file)
            if not log_path.is_absolute():
                log_path = Path.cwd() / log_path
        else:
            log_path = self.logs_dir / f"{name}.log"
        
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Start the process in detached mode
        pid = self._start_detached_process(runtime, tag, port, env_vars, log_path)
        
        # Create agent process object
        agent = LocalAgentProcess(
            name=name,
            pid=pid,
            port=port,
            log_file=str(log_path),
            config_path=config_path,
        )
        
        # Save to state
        agents = self._load_state()
        agents.append(agent)
        self._save_state(agents)
        
        return agent
    
    def _start_detached_process(
        self,
        runtime,
        tag: str,
        port: int,
        env_vars: Optional[Dict],
        log_path: Path,
    ) -> int:
        """Start the actual detached process."""
        import time
        import boto3
        
        if not runtime.has_local_runtime:
            raise RuntimeError("No container runtime available for local run")
        
        # Build the container command (similar to run_local but for detached mode)
        container_name = f"{tag.split(':')[0]}-{int(time.time())}"
        cmd = [runtime.runtime, "run", "--rm", "-p", f"{port}:8080", "--name", container_name]
        
        # Add AWS credentials
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if not credentials:
                raise RuntimeError("No AWS credentials found. Please configure AWS credentials.")
            
            frozen_creds = credentials.get_frozen_credentials()
            cmd.extend(["-e", f"AWS_ACCESS_KEY_ID={frozen_creds.access_key}"])
            cmd.extend(["-e", f"AWS_SECRET_ACCESS_KEY={frozen_creds.secret_key}"])
            
            if frozen_creds.token:
                cmd.extend(["-e", f"AWS_SESSION_TOKEN={frozen_creds.token}"])
        
        except ImportError:
            raise RuntimeError("boto3 is required for local mode. Please install it.") from None
        
        # Add additional environment variables if provided
        if env_vars:
            for key, value in env_vars.items():
                cmd.extend(["-e", f"{key}={value}"])
        
        cmd.append(tag)
        
        # Open log file (path is validated and constructed safely)
        with open(log_path, 'w') as log_file:  # nosec B101 - log_path is validated
            # Start process in detached mode
            # Security: Using list of args (not shell=True) to prevent injection
            process = subprocess.Popen(  # nosec B603 - subprocess with list args is safe
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # Detach from parent session
                shell=False,  # Explicitly disable shell for security
            )
        
        return process.pid
    
    def get_agent(self, name: str) -> Optional[LocalAgentProcess]:
        """Get agent by name."""
        agents = self._load_state()
        for agent in agents:
            if agent.name == name:
                return agent
        return None
    
    def cleanup_stale_processes(self) -> None:
        """Remove stale processes from state."""
        agents = self._load_state()
        running_agents = [agent for agent in agents if agent.is_running()]
        self._save_state(running_agents)