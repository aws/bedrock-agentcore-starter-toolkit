"""
Demo script for Agent Metrics Collection.

Demonstrates the integration with AgentDashboardAPI and comprehensive
agent metrics collection including coordination efficiency and workload distribution.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent_dashboard_api import AgentDashboardAPI
from src.metrics.agent_metrics_collector import AgentMetricsCollector
from src.metrics.metrics_collector import MetricsCollector


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def print_metrics(data: dict, indent: int = 0):
    """Pretty print metrics data."""
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_metrics(value, indent + 1)
        elif isinstance(value, list):
            print(f"{prefix}{key}: [{len(value)} items]")
            if len(value) > 0 and isinstance(value[0], dict):
                for i, item in enumerate(value[:3]):  # Show first 3 items
                    print(f"{prefix}  [{i}]:")
                    print_metrics(item, indent + 2)
                if len(value) > 3:
                    print(f"{prefix}  ... and {len(value) - 3} more")
        else:
            if isinstance(value, float):
                print(f"{prefix}{key}: {value:.4f}")
            else:
                print(f"{prefix}{key}: {value}")


async def demo_agent_metrics_collection():
    """Demonstrate agent metrics collection."""
    
    print_section("Agent Metrics Collection Demo")
    print("This demo showcases the integration with AgentDashboardAPI")
    print("and comprehensive agent metrics collection.\n")
    
    # Initialize AgentDashboardAPI
    print("1. Initializing AgentDashboardAPI...")
    agent_api = AgentDashboardAPI()
    print(f"   ✓ Initialized with {len(agent_api.agents)} agents\n")
    
    # Initialize AgentMetricsCollector
    print("2. Initializing AgentMetricsCollector...")
    collector = AgentMetricsCollector(agent_api)
    print("   ✓ Collector initialized\n")
    
    # Simulate some agent activity
    print("3. Simulating agent activity...")
    for _ in range(5):
        agent_api.simulate_agent_activity()
        
        # Log some coordination events
        agent_api.log_coordination_event(
            event_type="coordination",
            source_agent="txn_analyzer_001",
            target_agent="pattern_detector_001",
            transaction_id=f"txn_{_}",
            status="completed",
            duration_ms=50.0 + (_ * 10)
        )
    print("   ✓ Simulated 5 rounds of activity\n")
    
    # Collect agent metrics
    print_section("Collecting Agent Metrics")
    agent_metrics = await collector.collect_agent_metrics()
    
    print(f"Collected metrics from {len(agent_metrics)} agents:\n")
    for metrics in agent_metrics:
        print(f"  Agent: {metrics.agent_name} ({metrics.agent_id})")
        print(f"    Status: {metrics.status}")
        print(f"    Health Score: {metrics.health_score:.3f}")
        print(f"    Requests Processed: {metrics.requests_processed}")
        print(f"    Avg Response Time: {metrics.avg_response_time_ms:.2f}ms")
        print(f"    Success Rate: {metrics.success_rate:.2%}")
        print(f"    Current Load: {metrics.current_load:.2%}")
        print()
    
    # Calculate coordination efficiency
    print_section("Coordination Efficiency Metrics")
    coordination = await collector.calculate_coordination_efficiency()
    
    print("Coordination Efficiency Analysis:\n")
    print_metrics(coordination)
    
    # Track workload distribution
    print_section("Workload Distribution Analysis")
    workload = await collector.track_workload_distribution()
    
    print("Workload Distribution Metrics:\n")
    print_metrics(workload)
    
    # Get comprehensive metrics
    print_section("Comprehensive Agent Metrics")
    all_metrics = await collector.get_all_metrics()
    
    print("Summary Statistics:\n")
    print_metrics(all_metrics['summary'])
    
    print("\nCoordination Efficiency:\n")
    print_metrics(all_metrics['coordination_efficiency'])
    
    print("\nWorkload Distribution:\n")
    print_metrics(all_metrics['workload_distribution'])
    
    # Get performance summary for specific agent
    print_section("Individual Agent Performance Summary")
    summary = await collector.get_agent_performance_summary("txn_analyzer_001")
    
    if summary:
        print("Transaction Analyzer Performance:\n")
        print_metrics(summary)
    
    # Demonstrate metrics history
    print_section("Metrics History")
    
    # Collect metrics a few more times to build history
    print("Collecting metrics over time...")
    for i in range(5):
        agent_api.simulate_agent_activity()
        await collector.collect_agent_metrics()
        await asyncio.sleep(0.1)
    
    history = collector.get_metrics_history("txn_analyzer_001", limit=10)
    print(f"\nHistory for Transaction Analyzer:")
    print(f"  Data Points: {history['data_points']}")
    print(f"  Latest Metrics:")
    if history['history']:
        latest = history['history'][-1]
        print_metrics(latest, indent=2)
    
    # Integration with MetricsCollector
    print_section("Integration with MetricsCollector")
    
    print("Initializing MetricsCollector with AgentDashboardAPI...")
    metrics_collector = MetricsCollector(agent_api)
    print("   ✓ MetricsCollector initialized\n")
    
    print("Collecting all metrics through MetricsCollector...")
    all_metrics_via_collector = await metrics_collector.collect_all_metrics()
    
    print("\nSystem Metrics:")
    print(f"  Throughput: {all_metrics_via_collector['system'].throughput_tps:.2f} TPS")
    print(f"  Requests Total: {all_metrics_via_collector['system'].requests_total}")
    
    print("\nAgent Metrics:")
    print(f"  Number of Agents: {len(all_metrics_via_collector['agents'])}")
    for agent in all_metrics_via_collector['agents'][:2]:  # Show first 2
        print(f"  - {agent.agent_name}: {agent.requests_processed} requests, "
              f"{agent.health_score:.3f} health")
    
    print("\nBusiness Metrics:")
    print(f"  Transactions Processed: {all_metrics_via_collector['business'].transactions_processed}")
    print(f"  Fraud Detected: {all_metrics_via_collector['business'].fraud_detected}")
    print(f"  Money Saved: ${all_metrics_via_collector['business'].money_saved:,.2f}")
    
    # Get coordination and workload through MetricsCollector
    print("\nGetting coordination efficiency through MetricsCollector...")
    coordination_via_collector = await metrics_collector.get_coordination_efficiency()
    print(f"  Coordination Events: {coordination_via_collector['total_coordination_events']}")
    print(f"  Efficiency Score: {coordination_via_collector['coordination_efficiency_score']:.4f}")
    
    print("\nGetting workload distribution through MetricsCollector...")
    workload_via_collector = await metrics_collector.get_workload_distribution()
    print(f"  Average Load: {workload_via_collector['avg_load']:.2%}")
    print(f"  Load Imbalance: {workload_via_collector['load_imbalance_percentage']:.2f}%")
    print(f"  Is Balanced: {workload_via_collector['is_balanced']}")
    
    # Final summary
    print_section("Demo Complete")
    print("✓ Successfully demonstrated agent metrics collection")
    print("✓ Integration with AgentDashboardAPI verified")
    print("✓ Coordination efficiency calculation working")
    print("✓ Workload distribution tracking functional")
    print("✓ MetricsCollector integration complete")
    print("\nThe agent metrics collection system is ready for stress testing!")


async def main():
    """Main entry point."""
    try:
        await demo_agent_metrics_collection()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
