"""
Demo script for the Agent Management Dashboard

Demonstrates:
- Real-time agent status monitoring
- Performance metrics visualization
- Agent configuration management
- Coordination workflow visualization
"""

import time
import random
from datetime import datetime
from web_interface.agent_dashboard_api import (
    AgentDashboardAPI,
    AgentStatus,
    AgentType
)


def demo_dashboard_summary():
    """Demonstrate dashboard summary functionality"""
    print("=" * 70)
    print("AGENT DASHBOARD DEMO - DASHBOARD SUMMARY")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    summary = api.get_dashboard_summary()
    
    print(f"\n📊 DASHBOARD SUMMARY")
    print(f"   Timestamp: {summary['timestamp']}")
    
    print(f"\n   🤖 Agents:")
    agents = summary['agents']
    print(f"   • Total: {agents['total']}")
    print(f"   • Active: {agents['active']} ✓")
    print(f"   • Idle: {agents['idle']}")
    print(f"   • Busy: {agents['busy']}")
    print(f"   • Error: {agents['error']} ✗")
    print(f"   • Offline: {agents['offline']}")
    
    print(f"\n   📈 Performance:")
    perf = summary['performance']
    print(f"   • Total Requests: {perf['total_requests_processed']:,}")
    print(f"   • Total Errors: {perf['total_errors']}")
    print(f"   • Success Rate: {perf['overall_success_rate']:.2%}")
    print(f"   • Avg Health Score: {perf['average_health_score']:.3f}")
    print(f"   • Avg Response Time: {perf['average_response_time_ms']:.2f}ms")
    
    print(f"\n   🔄 Coordination:")
    coord = summary['coordination']
    print(f"   • Total Events: {coord['total_events']}")
    print(f"   • Recent Events (5min): {coord['recent_events']}")
    
    print(f"\n   🚨 Alerts:")
    alerts = summary['alerts']
    print(f"   • Total: {alerts['total']}")
    print(f"   • Critical: {alerts['critical']}")


def demo_agent_monitoring():
    """Demonstrate agent monitoring functionality"""
    print("\n" + "=" * 70)
    print("AGENT DASHBOARD DEMO - AGENT MONITORING")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    agents = api.get_all_agents()
    
    print(f"\n📋 MONITORING {len(agents)} AGENTS\n")
    
    for agent in agents:
        print(f"{'─' * 70}")
        print(f"🤖 {agent['agent_name']} ({agent['agent_id']})")
        print(f"   Type: {agent['agent_type'].replace('_', ' ').title()}")
        print(f"   Status: {agent['status'].upper()}")
        print(f"   Version: {agent['version']}")
        print(f"   Health Score: {agent['health_score']:.1%}")
        
        metrics = agent['metrics']
        print(f"\n   📊 Metrics:")
        print(f"   • Requests Processed: {metrics['requests_processed']:,}")
        print(f"   • Avg Response Time: {metrics['average_response_time_ms']:.2f}ms")
        print(f"   • Success Rate: {metrics['success_rate']:.2%}")
        print(f"   • Error Count: {metrics['error_count']}")
        print(f"   • Current Load: {metrics['current_load']:.1%}")
        print(f"   • Memory Usage: {metrics['memory_usage_mb']:.1f}MB")
        print(f"   • CPU Usage: {metrics['cpu_usage_percent']:.1f}%")
        
        print(f"\n   🔧 Capabilities:")
        for cap in agent['capabilities']:
            print(f"   • {cap.replace('_', ' ').title()}")
        
        print()


def demo_agent_activity_simulation():
    """Demonstrate simulated agent activity"""
    print("\n" + "=" * 70)
    print("AGENT DASHBOARD DEMO - ACTIVITY SIMULATION")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    print("\n🔄 Simulating agent activity for 10 seconds...")
    print("   (Updating metrics in real-time)\n")
    
    for i in range(10):
        # Simulate activity
        api.simulate_agent_activity()
        
        # Get updated summary
        summary = api.get_dashboard_summary()
        perf = summary['performance']
        
        print(f"   [{i+1}/10] Requests: {perf['total_requests_processed']:,} | "
              f"Success Rate: {perf['overall_success_rate']:.2%} | "
              f"Avg Response: {perf['average_response_time_ms']:.1f}ms")
        
        time.sleep(1)
    
    print("\n✅ Simulation complete!")
    
    # Show final state
    print("\n📊 Final Agent States:")
    agents = api.get_all_agents()
    for agent in agents:
        metrics = agent['metrics']
        print(f"   • {agent['agent_name']}: "
              f"{metrics['requests_processed']} requests, "
              f"{agent['health_score']:.1%} health, "
              f"{metrics['current_load']:.0%} load")


def demo_coordination_events():
    """Demonstrate coordination event tracking"""
    print("\n" + "=" * 70)
    print("AGENT DASHBOARD DEMO - COORDINATION EVENTS")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    # Log some coordination events
    print("\n📝 Logging coordination events...")
    
    events_to_log = [
        {
            "event_type": "request",
            "source_agent": "orchestrator_001",
            "target_agent": "txn_analyzer_001",
            "transaction_id": "tx_demo_001",
            "status": "completed",
            "duration_ms": 125.3
        },
        {
            "event_type": "response",
            "source_agent": "txn_analyzer_001",
            "target_agent": "orchestrator_001",
            "transaction_id": "tx_demo_001",
            "status": "completed",
            "duration_ms": 98.7
        },
        {
            "event_type": "coordination",
            "source_agent": "orchestrator_001",
            "target_agent": "risk_assessor_001",
            "transaction_id": "tx_demo_001",
            "status": "completed",
            "duration_ms": 87.2
        },
        {
            "event_type": "coordination",
            "source_agent": "orchestrator_001",
            "target_agent": "pattern_detector_001",
            "transaction_id": "tx_demo_001",
            "status": "completed",
            "duration_ms": 156.8
        },
        {
            "event_type": "escalation",
            "source_agent": "risk_assessor_001",
            "target_agent": "compliance_001",
            "transaction_id": "tx_demo_002",
            "status": "in_progress",
            "duration_ms": 0
        }
    ]
    
    for event_data in events_to_log:
        result = api.log_coordination_event(**event_data)
        if result['success']:
            event = result['event']
            print(f"   ✓ {event['event_type'].upper()}: "
                  f"{event['source_agent']} → {event['target_agent']} "
                  f"({event['duration_ms']:.1f}ms)")
    
    # Retrieve and display events
    print("\n📋 Recent Coordination Events:")
    result = api.get_coordination_events(limit=10)
    
    if result['success']:
        print(f"   Total events: {result['total_events']}\n")
        
        for event in result['events'][-5:]:  # Show last 5
            print(f"   [{event['timestamp'][:19]}]")
            print(f"   {event['event_type'].upper()}: "
                  f"{event['source_agent']} → {event['target_agent']}")
            print(f"   Transaction: {event['transaction_id']} | "
                  f"Status: {event['status']} | "
                  f"Duration: {event['duration_ms']:.1f}ms")
            print()


def demo_coordination_workflow():
    """Demonstrate coordination workflow visualization"""
    print("\n" + "=" * 70)
    print("AGENT DASHBOARD DEMO - COORDINATION WORKFLOW")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    # Get workflow for a transaction
    transaction_id = "tx_demo_001"
    print(f"\n🔍 Analyzing workflow for transaction: {transaction_id}\n")
    
    result = api.get_coordination_workflow(transaction_id)
    
    if result['success']:
        print(f"   Transaction ID: {result['transaction_id']}")
        print(f"   Total Events: {result['total_events']}")
        
        print(f"\n   🔗 Workflow Graph:")
        print(f"   Nodes (Agents): {', '.join(result['nodes'])}")
        
        print(f"\n   📊 Event Timeline:")
        for event in result['timeline']:
            arrow = "→" if event['target_agent'] else ""
            target = event['target_agent'] if event['target_agent'] else ""
            print(f"   • [{event['timestamp'][:19]}] "
                  f"{event['event_type'].upper()}: "
                  f"{event['source_agent']} {arrow} {target}")
            print(f"     Status: {event['status']} | Duration: {event['duration_ms']:.1f}ms")
    else:
        print(f"   ⚠️  {result['error']}")


def demo_agent_configuration():
    """Demonstrate agent configuration management"""
    print("\n" + "=" * 70)
    print("AGENT DASHBOARD DEMO - CONFIGURATION MANAGEMENT")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    agent_id = "txn_analyzer_001"
    
    # Get current configuration
    agent = api.get_agent(agent_id)
    print(f"\n⚙️  Current Configuration for {agent['agent_name']}:")
    for key, value in agent['configuration'].items():
        print(f"   • {key}: {value}")
    
    # Update configuration
    print(f"\n🔧 Updating configuration...")
    new_config = {
        "max_concurrent_requests": 15,
        "timeout_seconds": 45
    }
    
    result = api.update_agent_configuration(agent_id, new_config)
    
    if result['success']:
        print(f"   ✅ Configuration updated successfully")
        print(f"\n   Updated Configuration:")
        for key, value in result['configuration'].items():
            print(f"   • {key}: {value}")
    else:
        print(f"   ❌ Failed to update configuration: {result['error']}")


def demo_agent_status_changes():
    """Demonstrate agent status management"""
    print("\n" + "=" * 70)
    print("AGENT DASHBOARD DEMO - STATUS MANAGEMENT")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    agent_id = "pattern_detector_001"
    agent = api.get_agent(agent_id)
    
    print(f"\n🔄 Managing status for {agent['agent_name']}")
    print(f"   Current Status: {agent['status'].upper()}")
    
    # Simulate status changes
    status_sequence = [
        AgentStatus.BUSY,
        AgentStatus.ACTIVE,
        AgentStatus.IDLE
    ]
    
    print(f"\n   Simulating status changes:")
    for new_status in status_sequence:
        result = api.update_agent_status(agent_id, new_status)
        if result['success']:
            print(f"   • {agent['status'].upper()} → {new_status.value.upper()} ✓")
            time.sleep(0.5)
        agent['status'] = new_status.value
    
    print(f"\n   Final Status: {agent['status'].upper()}")


def demo_performance_history():
    """Demonstrate performance history tracking"""
    print("\n" + "=" * 70)
    print("AGENT DASHBOARD DEMO - PERFORMANCE HISTORY")
    print("=" * 70)
    
    api = AgentDashboardAPI()
    
    # Simulate some activity to generate history
    print("\n📊 Generating performance history...")
    for _ in range(5):
        api.simulate_agent_activity()
        time.sleep(0.2)
    
    # Get history for an agent
    agent_id = "risk_assessor_001"
    result = api.get_agent_metrics_history(agent_id, limit=10)
    
    if result['success']:
        agent = api.get_agent(agent_id)
        print(f"\n📈 Performance History for {agent['agent_name']}")
        print(f"   Data Points: {result['data_points']}\n")
        
        if result['history']:
            print(f"   {'Timestamp':<20} {'Response Time':<15} {'Success Rate':<15} {'Load':<10} {'Health'}")
            print(f"   {'-' * 75}")
            
            for entry in result['history'][-5:]:  # Show last 5
                timestamp = entry['timestamp'][:19]
                response_time = f"{entry['response_time']:.1f}ms"
                success_rate = f"{entry['success_rate']:.2%}"
                load = f"{entry['load']:.0%}"
                health = f"{entry['health_score']:.1%}"
                
                print(f"   {timestamp:<20} {response_time:<15} {success_rate:<15} {load:<10} {health}")


def main():
    """Run all agent dashboard demos"""
    print("🤖 AGENT MANAGEMENT DASHBOARD DEMONSTRATION")
    print("=" * 70)
    print("This demo showcases the agent management dashboard capabilities:")
    print("• Real-time agent status monitoring")
    print("• Performance metrics visualization")
    print("• Agent configuration management")
    print("• Coordination workflow visualization")
    print("=" * 70)
    
    try:
        demo_dashboard_summary()
        demo_agent_monitoring()
        demo_agent_activity_simulation()
        demo_coordination_events()
        demo_coordination_workflow()
        demo_agent_configuration()
        demo_agent_status_changes()
        demo_performance_history()
        
        print("\n" + "=" * 70)
        print("✅ AGENT DASHBOARD DEMO COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print("\nThe agent management dashboard demonstrated:")
        print("• ✓ Real-time monitoring of 5 specialized agents")
        print("• ✓ Performance metrics tracking and visualization")
        print("• ✓ Agent configuration management")
        print("• ✓ Coordination event logging and workflow visualization")
        print("• ✓ Health score calculation and monitoring")
        print("• ✓ Activity simulation and history tracking")
        
        print("\n" + "=" * 70)
        print("🌐 TO START THE WEB DASHBOARD:")
        print("=" * 70)
        print("\n   Run: python web_interface/dashboard_server.py")
        print("\n   Then open: http://127.0.0.1:5000")
        print("\n   The web interface provides:")
        print("   • Interactive real-time dashboard")
        print("   • Visual agent status cards")
        print("   • Performance charts and metrics")
        print("   • Coordination timeline visualization")
        print("   • Auto-refresh capability")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
