#!/usr/bin/env python3
"""Test script for the new monitoring functionality."""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bedrock_agentcore_starter_toolkit.monitoring import (
    MetricsCollector,
    PerformanceDashboard, 
    OperationalInsights
)


def test_metrics_collector():
    """Test MetricsCollector functionality."""
    print("🧪 Testing MetricsCollector...")
    
    try:
        collector = MetricsCollector("us-east-1")
        
        # Test with a dummy agent ID
        test_agent_id = "test-agent-123"
        
        # This will likely return empty data since the agent doesn't exist
        # but should not crash
        metrics = collector.collect_agent_metrics(test_agent_id, hours=1)
        
        print(f"✅ MetricsCollector working - got metrics structure: {list(metrics.keys())}")
        
        # Test real-time metrics
        real_time = collector.get_real_time_metrics(test_agent_id)
        print(f"✅ Real-time metrics working - structure: {list(real_time.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ MetricsCollector failed: {e}")
        return False


def test_performance_dashboard():
    """Test PerformanceDashboard functionality."""
    print("\n🧪 Testing PerformanceDashboard...")
    
    try:
        dashboard = PerformanceDashboard("us-east-1")
        
        test_agent_id = "test-agent-123"
        
        # Test dashboard URL generation (doesn't create actual dashboard)
        url = dashboard.get_dashboard_url(test_agent_id)
        print(f"✅ Dashboard URL generation working: {url}")
        
        # Test performance report generation
        report = dashboard.generate_performance_report(test_agent_id, hours=1)
        print(f"✅ Performance report working - structure: {list(report.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ PerformanceDashboard failed: {e}")
        return False


def test_operational_insights():
    """Test OperationalInsights functionality."""
    print("\n🧪 Testing OperationalInsights...")
    
    try:
        insights = OperationalInsights("us-east-1")
        
        test_agent_id = "test-agent-123"
        
        # Test conversation analysis
        patterns = insights.analyze_conversation_patterns(test_agent_id, hours=1)
        print(f"✅ Conversation analysis working - structure: {list(patterns.keys())}")
        
        # Test anomaly detection
        anomalies = insights.detect_performance_anomalies(test_agent_id, days=1)
        print(f"✅ Anomaly detection working - structure: {list(anomalies.keys())}")
        
        # Test optimization recommendations
        recommendations = insights.generate_optimization_recommendations(test_agent_id)
        print(f"✅ Optimization recommendations working - structure: {list(recommendations.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ OperationalInsights failed: {e}")
        return False


def test_cli_integration():
    """Test CLI integration."""
    print("\n🧪 Testing CLI integration...")
    
    try:
        # Test import of CLI commands
        from bedrock_agentcore_starter_toolkit.cli.monitoring.commands import monitoring_app
        print("✅ CLI monitoring commands imported successfully")
        
        # Test main CLI integration
        from bedrock_agentcore_starter_toolkit.cli.cli import app
        print("✅ Main CLI integration working")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI integration failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Testing Bedrock AgentCore Monitoring System\n")
    
    tests = [
        test_metrics_collector,
        test_performance_dashboard,
        test_operational_insights,
        test_cli_integration
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! Monitoring system is ready.")
        print("\n📋 Next steps:")
        print("1. Install the package: pip install -e .")
        print("2. Test CLI commands: agentcore monitor --help")
        print("3. Try with real agent: agentcore monitor metrics <your-agent-id>")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())