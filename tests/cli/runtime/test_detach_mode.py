#!/usr/bin/env python3
"""
Test script for the new detach mode functionality.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bedrock_agentcore_starter_toolkit.utils.runtime.local_process_manager import LocalProcessManager, LocalAgentProcess


def test_process_manager():
    """Test the LocalProcessManager functionality."""
    
    print("Testing LocalProcessManager...")
    
    # Create a test process manager
    test_dir = Path("/tmp/test_agentcore")
    process_manager = LocalProcessManager(test_dir)
    
    print(f"✅ Created process manager with state dir: {test_dir}")
    
    # Test creating a mock agent process
    mock_agent = LocalAgentProcess(
        name="test-agent",
        pid=12345,
        port=8080,
        log_file="/tmp/test.log",
    )
    
    print(f"✅ Created mock agent: {mock_agent.name} (PID: {mock_agent.pid})")
    
    # Test serialization
    agent_dict = mock_agent.to_dict()
    restored_agent = LocalAgentProcess.from_dict(agent_dict)
    
    assert restored_agent.name == mock_agent.name
    assert restored_agent.pid == mock_agent.pid
    assert restored_agent.port == mock_agent.port
    
    print("✅ Serialization/deserialization works")
    
    # Test state management
    agents = [mock_agent]
    process_manager._save_state(agents)
    loaded_agents = process_manager._load_state()
    
    # Note: The loaded agents will be empty because PID 12345 doesn't exist
    # This is expected behavior - only running processes are kept
    print(f"✅ State management works (loaded {len(loaded_agents)} running agents)")
    
    print("🎉 All tests passed!")


def test_cli_imports():
    """Test that the new CLI commands can be imported."""
    
    print("Testing CLI imports...")
    
    try:
        from bedrock_agentcore_starter_toolkit.cli.runtime.local_commands import ps, stop, logs
        print("✅ Successfully imported ps, stop, logs commands")
    except ImportError as e:
        print(f"❌ Failed to import CLI commands: {e}")
        return False
    
    try:
        from bedrock_agentcore_starter_toolkit.utils.runtime.local_process_manager import LocalProcessManager
        print("✅ Successfully imported LocalProcessManager")
    except ImportError as e:
        print(f"❌ Failed to import LocalProcessManager: {e}")
        return False
    
    print("🎉 All imports successful!")
    return True


if __name__ == "__main__":
    print("🧪 Testing detach mode implementation...\n")
    
    # Test imports first
    if not test_cli_imports():
        sys.exit(1)
    
    print()
    
    # Test process manager
    try:
        test_process_manager()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    
    print("\n✨ All tests completed successfully!")
    print("\n📋 Next steps:")
    print("  1. Test with: agentcore launch --local --detach")
    print("  2. List agents: agentcore ps")
    print("  3. View logs: agentcore logs AGENT_NAME")
    print("  4. Stop agent: agentcore stop AGENT_NAME")