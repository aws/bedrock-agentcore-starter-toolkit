"""
Demo script for enhanced agent dashboard with stress testing features.

This script demonstrates the new stress testing enhancements to the agent dashboard:
- Stress test metrics section
- Agent health indicators with color-coding
- Real-time load percentage displays
- Response time tracking per agent
- Alert indicators for agent issues
- Workload distribution visualization
- Coordination efficiency metrics
- Coordination workflow visualization with bottleneck detection
"""

import sys
import os
import time
import random
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent_dashboard_api import AgentDashboardAPI, AgentStatus


def simulate_stress_test_activity(api: AgentDashboardAPI, duration_seconds: int = 60):
    """
    Simulate stress test activity on agents.
    
    Args:
        api: AgentDashboardAPI instance
        duration_seconds: Duration to run simulation
    """
    print(f"\n{'='*80}")
    print("AGENT DASHBOARD STRESS TEST SIMULATION")
    print(f"{'='*80}\n")
    
    print(f"Simulating stress test activity for {duration_seconds} seconds...")
    print("Watch the agent dashboard at: http://localhost:5000/agent_dashboard.html\n")
    
    start_time = time.time()
    iteration = 0
    
    while time.time() - start_time < duration_seconds:
        iteration += 1
        elapsed = time.time() - start_time
        
        print(f"\n[{elapsed:.1f}s] Iteration {iteration}")
        print("-" * 80)
        
        # Simulate varying load patterns
        load_multiplier = 1.0 + 0.5 * abs(time.time() % 20 - 10) / 10  # Wave pattern
        
        for agent_id, agent in api.agents.items():
            # Simulate processing requests with varying load
            requests = random.randint(5, 20) * int(load_multiplier)
            response_time = random.uniform(50, 400) * load_multiplier
            success = random.random() > 0.02  # 98% success rate
            load = min(0.95, random.uniform(0.3, 0.8) * load_multiplier)
            
            # Update agent metrics
            api.update_agent_metrics(
                agent_id=agent_id,
                requests_processed=requests,
                response_time_ms=response_time,
                success=success,
                load=load
            )
            
            # Simulate coordination events
            if random.random() > 0.5:
                api.log_coordination_event(
                    event_type=random.choice(['request', 'response', 'coordination']),
                    source_agent=agent_id,
                    target_agent=random.choice(list(api.agents.keys())),
                    transaction_id=f"tx_{int(time.time() * 1000)}",
                    status='completed' if random.random() > 0.05 else 'in_progress',
                    duration_ms=response_time
                )
            
            print(f"  {agent.agent_name:25s} | Load: {load*100:5.1f}% | "
                  f"Response: {response_time:6.1f}ms | Health: {agent.health_score*100:5.1f}%")
        
        # Get and display stress test metrics
        stress_metrics = api.get_stress_test_metrics()
        print(f"\n  Stress Test Summary:")
        print(f"    Healthy Agents: {stress_metrics['summary']['healthy_agents']}/{stress_metrics['summary']['total_agents']}")
        print(f"    Avg Load: {stress_metrics['summary']['avg_load']*100:.1f}%")
        print(f"    Avg Response: {stress_metrics['summary']['avg_response_time']:.1f}ms")
        print(f"    Coordination Efficiency: {stress_metrics['coordination_efficiency']['success_rate']*100:.1f}%")
        
        # Display workload distribution
        print(f"\n  Workload Distribution:")
        for agent_id, dist in stress_metrics['workload_distribution'].items():
            print(f"    {dist['agent_name']:25s}: {dist['percentage']:5.1f}% ({dist['requests']} requests)")
        
        time.sleep(2)  # Update every 2 seconds
    
    print(f"\n{'='*80}")
    print("SIMULATION COMPLETE")
    print(f"{'='*80}\n")


def demonstrate_stress_test_endpoints(api: AgentDashboardAPI):
    """
    Demonstrate the new stress test API endpoints.
    
    Args:
        api: AgentDashboardAPI instance
    """
    print(f"\n{'='*80}")
    print("STRESS TEST API ENDPOINTS DEMONSTRATION")
    print(f"{'='*80}\n")
    
    # 1. Get stress test metrics
    print("1. Get Stress Test Metrics")
    print("-" * 80)
    stress_metrics = api.get_stress_test_metrics()
    print(f"   Timestamp: {stress_metrics['timestamp']}")
    print(f"   Total Agents: {stress_metrics['summary']['total_agents']}")
    print(f"   Healthy Agents: {stress_metrics['summary']['healthy_agents']}")
    print(f"   Average Load: {stress_metrics['summary']['avg_load']*100:.1f}%")
    print(f"   Total Requests: {stress_metrics['summary']['total_requests']}")
    
    # 2. Get agent performance under load
    print("\n2. Get Agent Performance Under Load")
    print("-" * 80)
    agent_id = list(api.agents.keys())[0]
    perf = api.get_agent_performance_under_load(agent_id)
    if perf['success']:
        print(f"   Agent: {perf['agent_name']}")
        print(f"   Current Load: {perf['current_metrics']['load']*100:.1f}%")
        print(f"   Response Time: {perf['current_metrics']['response_time_ms']:.1f}ms")
        print(f"   Health Score: {perf['current_metrics']['health_score']*100:.1f}%")
        print(f"   Trends:")
        print(f"     Response Time: {perf['trends']['response_time_trend']:+.1f}ms")
        print(f"     Load: {perf['trends']['load_trend']:+.3f}")
        print(f"     Health: {perf['trends']['health_trend']:+.3f}")
    
    # 3. Get workload distribution details
    print("\n3. Get Workload Distribution Details")
    print("-" * 80)
    workload = api.get_workload_distribution_details()
    print(f"   Balance Score: {workload['balance_metrics']['balance_score']*100:.1f}%")
    print(f"   Total Requests: {workload['balance_metrics']['total_requests']}")
    print(f"   Distribution:")
    for dist in workload['distribution'][:3]:  # Show first 3
        print(f"     {dist['agent_name']:25s}: {dist['request_percentage']:5.1f}% "
              f"(Load: {dist['current_load']*100:5.1f}%)")
    
    # 4. Get coordination efficiency metrics
    print("\n4. Get Coordination Efficiency Metrics")
    print("-" * 80)
    coord = api.get_coordination_efficiency_metrics()
    print(f"   Total Events: {coord['total_events']}")
    
    if coord['total_events'] > 0:
        print(f"   Success Rate: {coord['overall_success_rate']*100:.1f}%")
        print(f"   Avg Coordination Time: {coord['avg_coordination_time_ms']:.1f}ms")
        print(f"   Efficiency Score: {coord['efficiency_score']*100:.1f}%")
        print(f"   Agents Involved: {coord['agents_involved']}")
        
        if coord.get('event_types'):
            print(f"   Event Types:")
            for event_type, metrics in coord['event_types'].items():
                print(f"     {event_type:20s}: {metrics['count']} events, "
                      f"{metrics['success_rate']*100:.0f}% success, "
                      f"{metrics['avg_duration_ms']:.0f}ms avg")
    else:
        print(f"   No coordination events yet (will be generated during simulation)")
    
    print(f"\n{'='*80}\n")


def main():
    """Main demo function."""
    print("\n" + "="*80)
    print("ENHANCED AGENT DASHBOARD DEMO")
    print("Stress Testing Features")
    print("="*80)
    
    # Initialize API
    api = AgentDashboardAPI()
    
    # Simulate some initial activity
    print("\nGenerating initial activity...")
    for _ in range(10):
        api.simulate_agent_activity()
        time.sleep(0.1)
    
    # Demonstrate API endpoints
    demonstrate_stress_test_endpoints(api)
    
    # Ask user if they want to run live simulation
    print("\nThe agent dashboard has been enhanced with the following features:")
    print("  ✓ Stress test metrics section with key performance indicators")
    print("  ✓ Color-coded health status indicators with real-time updates")
    print("  ✓ Real-time load percentage displays with visual meters")
    print("  ✓ Response time tracking per agent with performance indicators")
    print("  ✓ Alert indicators for agent issues (high load, errors, slow response)")
    print("  ✓ Workload distribution visualization with bar charts")
    print("  ✓ Coordination efficiency metrics with event type breakdown")
    print("  ✓ Coordination workflow visualization with bottleneck detection")
    
    print("\nTo view the enhanced dashboard:")
    print("  1. Start the dashboard server:")
    print("     python web_interface/dashboard_server.py")
    print("  2. Open in browser:")
    print("     http://localhost:5000/agent_dashboard.html")
    
    response = input("\nWould you like to run a live stress test simulation? (y/n): ")
    
    if response.lower() == 'y':
        duration = input("Enter simulation duration in seconds (default: 60): ")
        try:
            duration = int(duration) if duration else 60
        except ValueError:
            duration = 60
        
        simulate_stress_test_activity(api, duration)
        
        # Final summary
        print("\nFinal Stress Test Summary:")
        print("-" * 80)
        summary = api.get_dashboard_summary()
        print(f"Total Requests Processed: {summary['performance']['total_requests_processed']:,}")
        print(f"Overall Success Rate: {summary['performance']['overall_success_rate']*100:.2f}%")
        print(f"Average Health Score: {summary['performance']['average_health_score']*100:.1f}%")
        print(f"Average Response Time: {summary['performance']['average_response_time_ms']:.1f}ms")
        print(f"Active Agents: {summary['agents']['active']}/{summary['agents']['total']}")
        print(f"Coordination Events: {summary['coordination']['total_events']}")
    
    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
