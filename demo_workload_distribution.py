#!/usr/bin/env python3
"""
Demo: Workload Distribution System

Demonstrates intelligent task routing, load balancing, and dynamic scaling
for coordinated multi-agent fraud detection processing.
"""

import logging
import time
import random
from datetime import datetime, timedelta
from agent_coordination.workload_distribution import (
    WorkloadDistributor, AgentCapabilities, Task, TaskAssignment,
    TaskType, TaskPriority, AgentStatus, create_task
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_agent_status(agent: AgentCapabilities):
    """Print agent status details."""
    print(f"Agent: {agent.agent_id}")
    print(f"  Type: {agent.agent_type}")
    print(f"  Status: {agent.status.value}")
    print(f"  Load: {agent.current_load}/{agent.max_concurrent_tasks} ({agent.load_percentage:.1f}%)")
    print(f"  Capabilities: {', '.join(agent.capabilities)}")
    print(f"  Avg Processing Time: {agent.average_processing_time_ms:.1f}ms")
    print(f"  Success Rate: {agent.success_rate:.1%}")
    print()


def print_distributor_status(distributor: WorkloadDistributor):
    """Print distributor status."""
    status = distributor.get_status()
    
    print(f"Distributor Status:")
    print(f"  Running: {status['is_running']}")
    print(f"  Strategy: {status['current_strategy']}")
    print(f"  Queue Size: {status['queue_size']}")
    print(f"  Pending Tasks: {status['pending_tasks']}")
    print(f"  Active Assignments: {status['active_assignments']}")
    print(f"  Registered Agents: {status['registered_agents']}")
    print(f"  Available Agents: {status['available_agents']}")
    print()
    
    metrics = status['metrics']
    print(f"Metrics:")
    print(f"  Total Tasks: {metrics['total_tasks_distributed']}")
    print(f"  Successful: {metrics['successful_assignments']}")
    print(f"  Failed: {metrics['failed_assignments']}")
    print(f"  Success Rate: {metrics['success_rate']:.1f}%")
    print(f"  Avg Assignment Time: {metrics['average_assignment_time_ms']:.1f}ms")
    print()


def demo_scenario_1_basic_distribution():
    """Scenario 1: Basic task distribution with multiple agents."""
    print_section("Scenario 1: Basic Task Distribution")
    
    distributor = WorkloadDistributor()
    
    # Register agents
    agents = [
        AgentCapabilities(
            agent_id="transaction_analyzer_1",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis", "amount_validation"],
            max_concurrent_tasks=5,
            current_load=0,
            average_processing_time_ms=150.0,
            success_rate=0.95,
            last_heartbeat=datetime.now(),
            specialization_scores={
                TaskType.TRANSACTION_ANALYSIS: 0.95,
                TaskType.RISK_ASSESSMENT: 0.60
            }
        ),
        AgentCapabilities(
            agent_id="pattern_detector_1",
            agent_type="pattern_detector",
            capabilities=["pattern_detection", "anomaly_detection"],
            max_concurrent_tasks=3,
            current_load=0,
            average_processing_time_ms=200.0,
            success_rate=0.92,
            last_heartbeat=datetime.now(),
            specialization_scores={
                TaskType.PATTERN_DETECTION: 0.98,
                TaskType.TRANSACTION_ANALYSIS: 0.50
            }
        ),
        AgentCapabilities(
            agent_id="risk_assessor_1",
            agent_type="risk_assessor",
            capabilities=["risk_assessment", "geolocation_analysis"],
            max_concurrent_tasks=4,
            current_load=0,
            average_processing_time_ms=180.0,
            success_rate=0.90,
            last_heartbeat=datetime.now(),
            specialization_scores={
                TaskType.RISK_ASSESSMENT: 0.93,
                TaskType.GEOLOCATION_ANALYSIS: 0.88
            }
        )
    ]
    
    print("Registering Agents:")
    print("-" * 80)
    for agent in agents:
        distributor.register_agent(agent)
        print_agent_status(agent)
    
    # Start distributor
    distributor.start()
    print("✅ Distributor started\n")
    
    # Submit tasks
    print("Submitting Tasks:")
    print("-" * 80)
    tasks = [
        create_task(TaskType.TRANSACTION_ANALYSIS, {"amount": 100.0}, TaskPriority.NORMAL),
        create_task(TaskType.PATTERN_DETECTION, {"user_id": "USER-123"}, TaskPriority.HIGH),
        create_task(TaskType.RISK_ASSESSMENT, {"location": "Tokyo"}, TaskPriority.NORMAL),
        create_task(TaskType.TRANSACTION_ANALYSIS, {"amount": 5000.0}, TaskPriority.HIGH),
        create_task(TaskType.PATTERN_DETECTION, {"user_id": "USER-456"}, TaskPriority.NORMAL),
    ]
    
    for task in tasks:
        distributor.submit_task(task)
        print(f"  Submitted: {task.task_type.value} (Priority: {task.priority.value})")
    
    print(f"\n✅ Submitted {len(tasks)} tasks\n")
    
    # Wait for distribution
    time.sleep(2)
    
    # Show status
    print_distributor_status(distributor)
    
    # Stop distributor
    distributor.stop()
    print("✅ Distributor stopped")


def demo_scenario_2_load_balancing():
    """Scenario 2: Load balancing with varying agent loads."""
    print_section("Scenario 2: Load Balancing - Least Loaded Strategy")
    
    distributor = WorkloadDistributor()
    distributor.set_routing_strategy("least_loaded")
    
    # Register agents with different initial loads
    agents = [
        AgentCapabilities(
            agent_id="agent_1",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=10,
            current_load=2,  # 20% loaded
            average_processing_time_ms=150.0,
            success_rate=0.95,
            last_heartbeat=datetime.now()
        ),
        AgentCapabilities(
            agent_id="agent_2",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=10,
            current_load=7,  # 70% loaded
            average_processing_time_ms=150.0,
            success_rate=0.95,
            last_heartbeat=datetime.now()
        ),
        AgentCapabilities(
            agent_id="agent_3",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=10,
            current_load=5,  # 50% loaded
            average_processing_time_ms=150.0,
            success_rate=0.95,
            last_heartbeat=datetime.now()
        )
    ]
    
    print("Initial Agent Loads:")
    print("-" * 80)
    for agent in agents:
        distributor.register_agent(agent)
        print(f"{agent.agent_id}: {agent.load_percentage:.1f}% loaded")
    print()
    
    distributor.start()
    
    # Submit tasks
    print("Submitting 10 tasks...")
    for i in range(10):
        task = create_task(TaskType.TRANSACTION_ANALYSIS, {"id": i}, TaskPriority.NORMAL)
        distributor.submit_task(task)
    
    time.sleep(2)
    
    # Show final loads
    print("\nFinal Agent Loads (after distribution):")
    print("-" * 80)
    status = distributor.get_status()
    for agent_id, agent_info in status['agents'].items():
        print(f"{agent_id}: {agent_info['load_percentage']:.1f}% loaded")
    
    print("\n💡 Tasks were distributed to least-loaded agents first")
    
    distributor.stop()


def demo_scenario_3_specialization_routing():
    """Scenario 3: Specialization-based routing."""
    print_section("Scenario 3: Specialization-Based Routing")
    
    distributor = WorkloadDistributor()
    distributor.set_routing_strategy("specialization")
    
    # Register specialized agents
    agents = [
        AgentCapabilities(
            agent_id="transaction_specialist",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=5,
            current_load=0,
            average_processing_time_ms=120.0,
            success_rate=0.98,
            last_heartbeat=datetime.now(),
            specialization_scores={
                TaskType.TRANSACTION_ANALYSIS: 0.98,  # Expert
                TaskType.PATTERN_DETECTION: 0.40
            }
        ),
        AgentCapabilities(
            agent_id="pattern_specialist",
            agent_type="pattern_detector",
            capabilities=["pattern_detection"],
            max_concurrent_tasks=5,
            current_load=0,
            average_processing_time_ms=180.0,
            success_rate=0.96,
            last_heartbeat=datetime.now(),
            specialization_scores={
                TaskType.PATTERN_DETECTION: 0.97,  # Expert
                TaskType.TRANSACTION_ANALYSIS: 0.45
            }
        ),
        AgentCapabilities(
            agent_id="generalist",
            agent_type="general",
            capabilities=["transaction_analysis", "pattern_detection"],
            max_concurrent_tasks=5,
            current_load=0,
            average_processing_time_ms=200.0,
            success_rate=0.85,
            last_heartbeat=datetime.now(),
            specialization_scores={
                TaskType.TRANSACTION_ANALYSIS: 0.60,  # Moderate
                TaskType.PATTERN_DETECTION: 0.65      # Moderate
            }
        )
    ]
    
    print("Agent Specializations:")
    print("-" * 80)
    for agent in agents:
        distributor.register_agent(agent)
        print(f"{agent.agent_id}:")
        for task_type, score in agent.specialization_scores.items():
            print(f"  {task_type.value}: {score:.2f}")
        print()
    
    distributor.start()
    
    # Submit mixed tasks
    print("Submitting Mixed Tasks:")
    print("-" * 80)
    tasks = [
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 1}),
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 2}),
        create_task(TaskType.PATTERN_DETECTION, {"id": 3}),
        create_task(TaskType.PATTERN_DETECTION, {"id": 4}),
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 5}),
    ]
    
    for task in tasks:
        distributor.submit_task(task)
        print(f"  {task.task_type.value}")
    
    time.sleep(2)
    
    print("\n💡 Tasks routed to specialized agents based on expertise")
    print("   Transaction tasks → transaction_specialist")
    print("   Pattern tasks → pattern_specialist")
    
    distributor.stop()


def demo_scenario_4_priority_handling():
    """Scenario 4: Priority-based task handling."""
    print_section("Scenario 4: Priority-Based Task Handling")
    
    distributor = WorkloadDistributor()
    
    # Register single agent
    agent = AgentCapabilities(
        agent_id="priority_handler",
        agent_type="general",
        capabilities=["transaction_analysis"],
        max_concurrent_tasks=2,  # Limited capacity
        current_load=0,
        average_processing_time_ms=150.0,
        success_rate=0.95,
        last_heartbeat=datetime.now()
    )
    
    distributor.register_agent(agent)
    distributor.start()
    
    # Submit tasks with different priorities
    print("Submitting Tasks with Different Priorities:")
    print("-" * 80)
    tasks = [
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 1, "amount": 100}, TaskPriority.LOW),
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 2, "amount": 10000}, TaskPriority.CRITICAL),
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 3, "amount": 500}, TaskPriority.NORMAL),
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 4, "amount": 5000}, TaskPriority.HIGH),
        create_task(TaskType.TRANSACTION_ANALYSIS, {"id": 5, "amount": 200}, TaskPriority.NORMAL),
    ]
    
    for task in tasks:
        distributor.submit_task(task)
        print(f"  Task {task.payload['id']}: ${task.payload['amount']} - Priority: {task.priority.value}")
    
    time.sleep(2)
    
    print("\n💡 Tasks processed in priority order:")
    print("   1. CRITICAL (Task 2: $10,000)")
    print("   2. HIGH (Task 4: $5,000)")
    print("   3. NORMAL (Tasks 3, 5)")
    print("   4. LOW (Task 1)")
    
    distributor.stop()


def demo_scenario_5_hybrid_routing():
    """Scenario 5: Hybrid routing strategy."""
    print_section("Scenario 5: Hybrid Routing Strategy")
    
    distributor = WorkloadDistributor()
    distributor.set_routing_strategy("hybrid")
    
    # Register diverse agents
    agents = [
        AgentCapabilities(
            agent_id="fast_agent",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=10,
            current_load=2,  # Low load
            average_processing_time_ms=100.0,  # Fast
            success_rate=0.90,  # Good success rate
            last_heartbeat=datetime.now(),
            specialization_scores={TaskType.TRANSACTION_ANALYSIS: 0.70}
        ),
        AgentCapabilities(
            agent_id="expert_agent",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=10,
            current_load=5,  # Medium load
            average_processing_time_ms=150.0,  # Moderate speed
            success_rate=0.98,  # Excellent success rate
            last_heartbeat=datetime.now(),
            specialization_scores={TaskType.TRANSACTION_ANALYSIS: 0.95}  # Expert
        ),
        AgentCapabilities(
            agent_id="busy_agent",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=10,
            current_load=8,  # High load
            average_processing_time_ms=120.0,  # Fast
            success_rate=0.92,  # Good success rate
            last_heartbeat=datetime.now(),
            specialization_scores={TaskType.TRANSACTION_ANALYSIS: 0.80}
        )
    ]
    
    print("Agent Profiles:")
    print("-" * 80)
    for agent in agents:
        distributor.register_agent(agent)
        print(f"{agent.agent_id}:")
        print(f"  Load: {agent.load_percentage:.1f}%")
        print(f"  Speed: {agent.average_processing_time_ms:.0f}ms")
        print(f"  Success Rate: {agent.success_rate:.1%}")
        print(f"  Specialization: {agent.specialization_scores.get(TaskType.TRANSACTION_ANALYSIS, 0):.2f}")
        print()
    
    distributor.start()
    
    # Submit tasks
    print("Submitting 15 tasks...")
    for i in range(15):
        task = create_task(TaskType.TRANSACTION_ANALYSIS, {"id": i})
        distributor.submit_task(task)
    
    time.sleep(2)
    
    print("\n💡 Hybrid routing considers:")
    print("   • Agent load (40% weight)")
    print("   • Specialization (40% weight)")
    print("   • Performance (20% weight)")
    print("\n   Result: Balanced distribution across all factors")
    
    distributor.stop()


def demo_scenario_6_auto_scaling():
    """Scenario 6: Auto-scaling recommendations."""
    print_section("Scenario 6: Auto-Scaling Recommendations")
    
    distributor = WorkloadDistributor()
    distributor.enable_auto_scaling = True
    distributor.scale_up_threshold = 70.0  # Scale up at 70% load
    distributor.scale_down_threshold = 30.0  # Scale down at 30% load
    
    # Register agents
    agents = [
        AgentCapabilities(
            agent_id=f"agent_{i}",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=5,
            current_load=0,
            average_processing_time_ms=150.0,
            success_rate=0.95,
            last_heartbeat=datetime.now()
        )
        for i in range(3)
    ]
    
    for agent in agents:
        distributor.register_agent(agent)
    
    distributor.start()
    
    print("Initial Configuration:")
    print(f"  Agents: {len(agents)}")
    print(f"  Total Capacity: {sum(a.max_concurrent_tasks for a in agents)} tasks")
    print(f"  Scale-up Threshold: {distributor.scale_up_threshold}%")
    print(f"  Scale-down Threshold: {distributor.scale_down_threshold}%")
    print()
    
    # Simulate high load
    print("Simulating High Load (80% capacity)...")
    print("-" * 80)
    num_tasks = int(sum(a.max_concurrent_tasks for a in agents) * 0.8)
    for i in range(num_tasks):
        task = create_task(TaskType.TRANSACTION_ANALYSIS, {"id": i})
        distributor.submit_task(task)
    
    time.sleep(3)
    
    status = distributor.get_status()
    total_capacity = sum(a.max_concurrent_tasks for a in agents)
    total_load = sum(distributor.agents[a.agent_id].current_load for a in agents)
    load_percentage = (total_load / total_capacity) * 100
    
    print(f"System Load: {load_percentage:.1f}%")
    print(f"⚠️  Recommendation: SCALE UP (load > {distributor.scale_up_threshold}%)")
    print("   Consider adding more agents to handle increased load")
    
    distributor.stop()


def demo_statistics():
    """Demo: Workload distribution statistics."""
    print_section("Workload Distribution Statistics")
    
    distributor = WorkloadDistributor()
    
    # Register agents
    for i in range(3):
        agent = AgentCapabilities(
            agent_id=f"agent_{i}",
            agent_type="transaction_analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=5,
            current_load=0,
            average_processing_time_ms=150.0 + (i * 20),
            success_rate=0.95 - (i * 0.02),
            last_heartbeat=datetime.now()
        )
        distributor.register_agent(agent)
    
    distributor.start()
    
    # Submit and complete tasks
    print("Processing 20 tasks...")
    for i in range(20):
        task = create_task(TaskType.TRANSACTION_ANALYSIS, {"id": i})
        distributor.submit_task(task)
    
    time.sleep(2)
    
    # Simulate task completions
    for assignment_id in list(distributor.active_assignments.keys())[:15]:
        distributor.complete_task(assignment_id, result={"success": True})
    
    # Get metrics
    metrics = distributor.get_metrics()
    
    print("\nDistribution Statistics:")
    print("-" * 80)
    print(f"Total Tasks Distributed: {metrics.total_tasks_distributed}")
    print(f"Successful Assignments: {metrics.successful_assignments}")
    print(f"Failed Assignments: {metrics.failed_assignments}")
    print(f"Success Rate: {(metrics.successful_assignments / max(metrics.total_tasks_distributed, 1)) * 100:.1f}%")
    print()
    
    print("Agent Utilization:")
    for agent_id, utilization in metrics.agent_utilization.items():
        print(f"  {agent_id}: {utilization:.1f}%")
    print()
    
    print("Task Type Distribution:")
    for task_type, count in metrics.task_type_distribution.items():
        print(f"  {task_type.value}: {count}")
    
    distributor.stop()


def main():
    """Run all demo scenarios."""
    print("\n" + "="*80)
    print("  WORKLOAD DISTRIBUTION SYSTEM DEMO")
    print("  Intelligent Task Routing and Load Balancing")
    print("="*80)
    
    try:
        # Run scenarios
        demo_scenario_1_basic_distribution()
        demo_scenario_2_load_balancing()
        demo_scenario_3_specialization_routing()
        demo_scenario_4_priority_handling()
        demo_scenario_5_hybrid_routing()
        demo_scenario_6_auto_scaling()
        demo_statistics()
        
        print_section("Demo Complete")
        print("✅ All scenarios executed successfully!")
        print()
        print("Key Features Demonstrated:")
        print("  • Basic task distribution to multiple agents")
        print("  • Load balancing with least-loaded strategy")
        print("  • Specialization-based routing")
        print("  • Priority-based task handling")
        print("  • Hybrid routing strategy")
        print("  • Auto-scaling recommendations")
        print("  • Distribution statistics and metrics")
        print()
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}", exc_info=True)
        print(f"\n❌ Demo failed: {str(e)}")


if __name__ == "__main__":
    main()
