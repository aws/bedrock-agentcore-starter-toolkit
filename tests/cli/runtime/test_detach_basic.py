#!/usr/bin/env python3
"""Basic test for detach mode functionality."""

import subprocess
import sys
import time
from pathlib import Path

def test_detach_validation():
    """Test that detach validation works correctly."""
    print("🧪 Testing detach validation...")
    
    # Test --detach without --local (should fail)
    result = subprocess.run([
        sys.executable, "-m", "bedrock_agentcore_starter_toolkit.cli.cli",
        "launch", "--detach"
    ], capture_output=True, text=True)
    
    assert result.returncode != 0, "Should fail when --detach used without --local"
    assert "--detach can only be used with --local" in result.stdout, f"Unexpected error: stdout={result.stdout}, stderr={result.stderr}"
    print("✅ --detach validation works")
    
    # Test --log-file without --local (should fail)
    result = subprocess.run([
        sys.executable, "-m", "bedrock_agentcore_starter_toolkit.cli.cli",
        "launch", "--log-file", "test.log"
    ], capture_output=True, text=True)
    
    assert result.returncode != 0, "Should fail when --log-file used without --local"
    assert "--log-file can only be used with --local" in result.stdout, f"Unexpected error: stdout={result.stdout}, stderr={result.stderr}"
    print("✅ --log-file validation works")

def test_help_output():
    """Test that help output includes detach information."""
    print("🧪 Testing help output...")
    
    result = subprocess.run([
        sys.executable, "-m", "bedrock_agentcore_starter_toolkit.cli.cli",
        "launch", "--help"
    ], capture_output=True, text=True)
    
    assert result.returncode == 0, f"Help command failed: {result.stderr}"
    assert "--detach" in result.stdout, "Help should mention --detach"
    assert "--log-file" in result.stdout, "Help should mention --log-file"
    assert "Docker-style detached mode" in result.stdout, "Help should explain detached mode"
    print("✅ Help output includes detach information")

def test_local_process_manager():
    """Test LocalProcessManager basic functionality."""
    print("🧪 Testing LocalProcessManager...")
    
    from bedrock_agentcore_starter_toolkit.utils.runtime.local_process_manager import LocalProcessManager, LocalAgentProcess
    
    # Test basic instantiation
    manager = LocalProcessManager()
    assert manager.state_dir.exists(), "State directory should be created"
    assert manager.logs_dir.exists(), "Logs directory should be created"
    
    # Test agent process creation
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
    
    # Test serialization
    data = agent.to_dict()
    agent2 = LocalAgentProcess.from_dict(data)
    assert agent2.name == agent.name
    assert agent2.pid == agent.pid
    
    print("✅ LocalProcessManager basic functionality works")

def main():
    """Run all tests."""
    print("🚀 Running basic detach mode tests...\n")
    
    try:
        test_detach_validation()
        print()
        
        test_help_output()
        print()
        
        test_local_process_manager()
        print()
        
        print("🎉 All tests passed!")
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())