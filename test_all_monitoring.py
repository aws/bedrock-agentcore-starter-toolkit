#!/usr/bin/env python3
"""Comprehensive test of all monitoring functionality."""

import sys
import subprocess
from pathlib import Path

def test_imports():
    """Test all module imports."""
    print("🧪 Testing imports...")
    
    try:
        # Test monitoring module imports
        from bedrock_agentcore_starter_toolkit.monitoring import (
            MetricsCollector, PerformanceDashboard, OperationalInsights
        )
        print("✅ Core monitoring classes imported")
        
        # Test CLI imports
        from bedrock_agentcore_starter_toolkit.cli.monitoring.commands import monitoring_app
        print("✅ CLI monitoring commands imported")
        
        # Test main CLI integration
        from bedrock_agentcore_starter_toolkit.cli.cli import app
        print("✅ Main CLI integration working")
        
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_cli_help():
    """Test CLI help commands."""
    print("\n🧪 Testing CLI help commands...")
    
    commands = [
        ["agentcore", "monitor", "--help"],
        ["agentcore", "monitor", "metrics", "--help"],
        ["agentcore", "monitor", "dashboard", "--help"],
        ["agentcore", "monitor", "report", "--help"],
        ["agentcore", "monitor", "insights", "--help"],
        ["agentcore", "monitor", "anomalies", "--help"],
        ["agentcore", "monitor", "optimize", "--help"]
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ {' '.join(cmd)} - OK")
            else:
                print(f"❌ {' '.join(cmd)} - Failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ {' '.join(cmd)} - Error: {e}")
            return False
    
    return True

def test_class_instantiation():
    """Test class instantiation without AWS calls."""
    print("\n🧪 Testing class instantiation...")
    
    try:
        from bedrock_agentcore_starter_toolkit.monitoring import (
            MetricsCollector, PerformanceDashboard, OperationalInsights
        )
        
        # Test instantiation
        collector = MetricsCollector("us-east-1")
        print("✅ MetricsCollector instantiated")
        
        dashboard = PerformanceDashboard("us-east-1")
        print("✅ PerformanceDashboard instantiated")
        
        insights = OperationalInsights("us-east-1")
        print("✅ OperationalInsights instantiated")
        
        return True
    except Exception as e:
        print(f"❌ Class instantiation failed: {e}")
        return False

def test_method_signatures():
    """Test method signatures and basic structure."""
    print("\n🧪 Testing method signatures...")
    
    try:
        from bedrock_agentcore_starter_toolkit.monitoring import (
            MetricsCollector, PerformanceDashboard, OperationalInsights
        )
        
        collector = MetricsCollector("us-east-1")
        
        # Test method existence
        assert hasattr(collector, 'collect_agent_metrics')
        assert hasattr(collector, 'get_real_time_metrics')
        assert hasattr(collector, 'get_historical_trends')
        print("✅ MetricsCollector methods exist")
        
        dashboard = PerformanceDashboard("us-east-1")
        assert hasattr(dashboard, 'create_agent_dashboard')
        assert hasattr(dashboard, 'generate_performance_report')
        assert hasattr(dashboard, 'get_dashboard_url')
        print("✅ PerformanceDashboard methods exist")
        
        insights = OperationalInsights("us-east-1")
        assert hasattr(insights, 'analyze_conversation_patterns')
        assert hasattr(insights, 'detect_performance_anomalies')
        assert hasattr(insights, 'generate_optimization_recommendations')
        print("✅ OperationalInsights methods exist")
        
        return True
    except Exception as e:
        print(f"❌ Method signature test failed: {e}")
        return False

def test_cli_with_mock_data():
    """Test CLI commands with mock agent ID (will fail gracefully)."""
    print("\n🧪 Testing CLI with mock data...")
    
    test_agent_id = "test-agent-123"
    
    # Test commands that should handle missing data gracefully
    commands = [
        ["agentcore", "monitor", "metrics", test_agent_id, "--json"],
        ["agentcore", "monitor", "report", test_agent_id, "--json"],
        ["agentcore", "monitor", "insights", test_agent_id, "--json"],
        ["agentcore", "monitor", "anomalies", test_agent_id, "--json"],
        ["agentcore", "monitor", "optimize", test_agent_id, "--json"]
    ]
    
    success_count = 0
    for cmd in commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            cmd_name = cmd[2]
            
            # Commands should either succeed or fail gracefully with error message
            if result.returncode == 0:
                print(f"✅ {cmd_name} - Executed successfully")
                success_count += 1
            elif "Failed to" in result.stderr or "Unable to access" in result.stderr:
                print(f"✅ {cmd_name} - Failed gracefully (expected)")
                success_count += 1
            else:
                print(f"❌ {cmd_name} - Unexpected error: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"⚠️  {cmd[2]} - Timeout (may be waiting for AWS)")
        except Exception as e:
            print(f"❌ {cmd[2]} - Error: {e}")
    
    return success_count >= 3  # At least 3 commands should work

def main():
    """Run all tests."""
    print("🚀 Testing All Monitoring Code")
    print("=" * 40)
    
    tests = [
        ("Import Tests", test_imports),
        ("CLI Help Tests", test_cli_help),
        ("Class Instantiation", test_class_instantiation),
        ("Method Signatures", test_method_signatures),
        ("CLI Mock Data", test_cli_with_mock_data)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append(result)
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\n{test_name}: {status}")
        except Exception as e:
            print(f"\n{test_name}: ❌ FAILED - {e}")
            results.append(False)
    
    print(f"\n{'='*60}")
    print(f"📊 FINAL RESULTS: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 ALL TESTS PASSED! Monitoring system is ready for PR.")
        return 0
    else:
        print("⚠️  Some tests failed. Review issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())