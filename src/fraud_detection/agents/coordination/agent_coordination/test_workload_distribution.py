"""
Unit tests for Workload Distribution System.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.workload_distribution import (
    WorkloadDistributor, AgentCapabilities, Task, TaskAssignment,
    TaskType, TaskPriority, AgentStatus, create_task
)


@pytest.fixture
def workload_distributor():
    """Create workload distributor for testing."""
    return WorkloadDistributor(max_queue_size=100)


@pytest.fixture
def sample_agent():
    """Create sample agent capabilities."""
    return AgentCapabilities(
        agent_id="test_agent_1",
        agent_type="transaction_analyzer",
        capabilities=["transaction_analysis", "risk_assessment"],
        max_concurrent_tasks=5,
        current_load=0,
        average_processing_time_ms=200.0,
        success_rate=0.95,
        last_heartbeat=datetime.now(),
        specialization_scores={
            TaskType.TRANSACTION_ANALYSIS: 0.9,
            TaskType.RISK_ASSESSMENT: 0.8
        }
    )


@pytest.fixture
def sample_task():
    """Create sample task."""
    return create_task(
        task_type=TaskType.TRANSACTION_ANALYSIS,
        payload={"transaction_id": "txn_123", "amount": 100.0},
        priority=TaskPriority.NORMAL,
        required_capabilities=["transaction_analysis"]
    )


class TestWorkloadDistributor:
    """Test cases for WorkloadDistributor."""
    
    def test_distributor_initialization(self, workload_distributor):
        """Test workload distributor initialization."""
        assert workload_distributor.max_queue_size == 100
        assert len(workload_distributor.agents) == 0
        assert workload_distributor.current_strategy == "hybrid"
        assert workload_distributor.is_running is False
    
    def test_register_agent(self, workload_distributor, sample_agent):
        """Test agent registration."""
        success = workload_distributor.register_agent(sample_agent)
        
        assert success is True
        assert sample_agent.agent_id in workload_distributor.agents
        assert sample_agent.agent_id in workload_distributor.agent_task_queues
        assert len(workload_distributor.agents) == 1
    
    def test_unregister_agent(self, workload_distributor, sample_agent):
        """Test agent unregistration."""
        # Register first
        workload_distributor.register_agent(sample_agent)
        
        # Then unregister
        success = workload_distributor.unregister_agent(sample_agent.agent_id)
        
        assert success is True
        assert sample_agent.agent_id not in workload_distributor.agents
        assert sample_agent.agent_id not in workload_distributor.agent_task_queues
    
    def test_submit_task(self, workload_distributor, sample_task):
        """Test task submission."""
        success = workload_distributor.submit_task(sample_task)
        
        assert success is True
        assert sample_task.task_id in workload_distributor.pending_tasks
        assert workload_distributor.task_queue.qsize() == 1
        assert workload_distributor.metrics.total_tasks_distributed == 1
    
    def test_update_agent_status(self, workload_distributor, sample_agent):
        """Test agent status updates."""
        workload_distributor.register_agent(sample_agent)
        
        # Update status
        workload_distributor.update_agent_status(
            sample_agent.agent_id, 
            AgentStatus.BUSY, 
            current_load=3
        )
        
        agent = workload_distributor.agents[sample_agent.agent_id]
        assert agent.status == AgentStatus.BUSY
        assert agent.current_load == 3
    
    def test_complete_task(self, workload_distributor, sample_agent, sample_task):
        """Test task completion."""
        # Register agent and submit task
        workload_distributor.register_agent(sample_agent)
        workload_distributor.submit_task(sample_task)
        
        # Manually create assignment for testing
        assignment = TaskAssignment(
            assignment_id="test_assignment",
            task=sample_task,
            agent_id=sample_agent.agent_id,
            assigned_at=datetime.now(),
            started_at=datetime.now()
        )
        
        workload_distributor.active_assignments["test_assignment"] = assignment
        workload_distributor.agents[sample_agent.agent_id].current_load = 1
        
        # Complete task
        result = {"decision": "approve", "confidence": 0.9}
        success = workload_distributor.complete_task("test_assignment", result=result)
        
        assert success is True
        assert "test_assignment" not in workload_distributor.active_assignments
        assert "test_assignment" in workload_distributor.completed_assignments
        assert workload_distributor.agents[sample_agent.agent_id].current_load == 0
    
    def test_routing_strategies(self, workload_distributor):
        """Test different routing strategies."""
        # Create multiple agents with different characteristics
        agent1 = AgentCapabilities(
            agent_id="agent_1",
            agent_type="analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=5,
            current_load=1,  # 20% load
            average_processing_time_ms=100.0,
            success_rate=0.95,
            last_heartbeat=datetime.now(),
            specialization_scores={TaskType.TRANSACTION_ANALYSIS: 0.9}
        )
        
        agent2 = AgentCapabilities(
            agent_id="agent_2",
            agent_type="analyzer",
            capabilities=["transaction_analysis"],
            max_concurrent_tasks=5,
            current_load=3,  # 60% load
            average_processing_time_ms=150.0,
            success_rate=0.90,
            last_heartbeat=datetime.now(),
            specialization_scores={TaskType.TRANSACTION_ANALYSIS: 0.7}
        )
        
        workload_distributor.register_agent(agent1)
        workload_distributor.register_agent(agent2)
        
        task = create_task(TaskType.TRANSACTION_ANALYSIS, {"test": "data"})
        
        # Test least loaded routing
        workload_distributor.set_routing_strategy("least_loaded")
        selected_agent = workload_distributor._select_agent(task)
        assert selected_agent == "agent_1"  # Lower load
        
        # Test specialization routing
        workload_distributor.set_routing_strategy("specialization")
        selected_agent = workload_distributor._select_agent(task)
        assert selected_agent == "agent_1"  # Higher specialization
        
        # Test performance routing
        workload_distributor.set_routing_strategy("performance")
        selected_agent = workload_distributor._select_agent(task)
        assert selected_agent == "agent_1"  # Better performance
    
    def test_agent_capabilities_properties(self, sample_agent):
        """Test agent capabilities properties."""
        # Test load percentage
        sample_agent.current_load = 2
        assert sample_agent.load_percentage == 40.0  # 2/5 * 100
        
        # Test availability
        assert sample_agent.is_available is True
        
        sample_agent.current_load = 5  # At capacity
        assert sample_agent.is_available is False
        
        sample_agent.status = AgentStatus.OFFLINE
        assert sample_agent.is_available is False
        
        # Test specialization score
        score = sample_agent.get_specialization_score(TaskType.TRANSACTION_ANALYSIS)
        assert score == 0.9
        
        score = sample_agent.get_specialization_score(TaskType.PATTERN_DETECTION)
        assert score == 0.5  # Default
    
    def test_task_assignment_properties(self, sample_task, sample_agent):
        """Test task assignment properties."""
        assignment = TaskAssignment(
            assignment_id="test_assignment",
            task=sample_task,
            agent_id=sample_agent.agent_id,
            assigned_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now() + timedelta(milliseconds=100)
        )
        
        # Test processing time calculation
        processing_time = assignment.processing_time_ms
        assert processing_time is not None
        assert processing_time >= 100.0
        
        # Test completion status
        assert assignment.is_completed is True
        
        # Test incomplete assignment
        incomplete_assignment = TaskAssignment(
            assignment_id="incomplete",
            task=sample_task,
            agent_id=sample_agent.agent_id,
            assigned_at=datetime.now()
        )
        
        assert incomplete_assignment.is_completed is False
        assert incomplete_assignment.processing_time_ms is None
    
    def test_get_status(self, workload_distributor, sample_agent, sample_task):
        """Test getting distributor status."""
        workload_distributor.register_agent(sample_agent)
        workload_distributor.submit_task(sample_task)
        
        status = workload_distributor.get_status()
        
        assert "is_running" in status
        assert "current_strategy" in status
        assert "queue_size" in status
        assert "registered_agents" in status
        assert "metrics" in status
        assert "agents" in status
        
        assert status["registered_agents"] == 1
        assert status["queue_size"] == 1
        assert sample_agent.agent_id in status["agents"]
    
    def test_get_metrics(self, workload_distributor, sample_agent):
        """Test getting metrics."""
        workload_distributor.register_agent(sample_agent)
        
        metrics = workload_distributor.get_metrics()
        
        assert hasattr(metrics, 'total_tasks_distributed')
        assert hasattr(metrics, 'successful_assignments')
        assert hasattr(metrics, 'failed_assignments')
        assert hasattr(metrics, 'agent_utilization')
        
        assert sample_agent.agent_id in metrics.agent_utilization
    
    def test_set_routing_strategy(self, workload_distributor):
        """Test setting routing strategy."""
        # Test valid strategy
        success = workload_distributor.set_routing_strategy("least_loaded")
        assert success is True
        assert workload_distributor.current_strategy == "least_loaded"
        
        # Test invalid strategy
        success = workload_distributor.set_routing_strategy("invalid_strategy")
        assert success is False
        assert workload_distributor.current_strategy == "least_loaded"  # Unchanged
    
    def test_task_priority_ordering(self):
        """Test task priority ordering in queue."""
        high_priority_task = create_task(
            TaskType.TRANSACTION_ANALYSIS,
            {"urgent": True},
            priority=TaskPriority.HIGH
        )
        
        low_priority_task = create_task(
            TaskType.PATTERN_DETECTION,
            {"routine": True},
            priority=TaskPriority.LOW
        )
        
        # High priority should be "less than" low priority for queue ordering
        assert high_priority_task < low_priority_task
    
    def test_start_stop_distributor(self, workload_distributor):
        """Test starting and stopping the distributor."""
        # Start distributor
        workload_distributor.start()
        assert workload_distributor.is_running is True
        
        # Stop distributor
        workload_distributor.stop()
        assert workload_distributor.is_running is False
    
    def test_round_robin_routing(self, workload_distributor):
        """Test round-robin routing strategy."""
        # Create multiple agents
        agent1 = AgentCapabilities(
            agent_id="agent_1", agent_type="test", capabilities=[],
            max_concurrent_tasks=5, current_load=0, average_processing_time_ms=100.0,
            success_rate=0.9, last_heartbeat=datetime.now()
        )
        
        agent2 = AgentCapabilities(
            agent_id="agent_2", agent_type="test", capabilities=[],
            max_concurrent_tasks=5, current_load=0, average_processing_time_ms=100.0,
            success_rate=0.9, last_heartbeat=datetime.now()
        )
        
        workload_distributor.register_agent(agent1)
        workload_distributor.register_agent(agent2)
        
        task = create_task(TaskType.TRANSACTION_ANALYSIS, {"test": "data"})
        
        # Test round-robin selection
        workload_distributor.set_routing_strategy("round_robin")
        
        # Should alternate between agents
        selected1 = workload_distributor._select_agent(task)
        selected2 = workload_distributor._select_agent(task)
        
        assert selected1 != selected2
        assert selected1 in ["agent_1", "agent_2"]
        assert selected2 in ["agent_1", "agent_2"]


class TestCreateTask:
    """Test cases for create_task function."""
    
    def test_create_task_basic(self):
        """Test basic task creation."""
        task = create_task(
            TaskType.RISK_ASSESSMENT,
            {"user_id": "user_123", "amount": 500.0}
        )
        
        assert task.task_type == TaskType.RISK_ASSESSMENT
        assert task.priority == TaskPriority.NORMAL
        assert task.payload["user_id"] == "user_123"
        assert task.payload["amount"] == 500.0
        assert task.task_id is not None
        assert isinstance(task.created_at, datetime)
    
    def test_create_task_with_options(self):
        """Test task creation with all options."""
        task = create_task(
            task_type=TaskType.COMPLIANCE_CHECK,
            payload={"document_id": "doc_456"},
            priority=TaskPriority.HIGH,
            required_capabilities=["compliance", "document_analysis"],
            estimated_duration_ms=2000.0
        )
        
        assert task.task_type == TaskType.COMPLIANCE_CHECK
        assert task.priority == TaskPriority.HIGH
        assert task.required_capabilities == ["compliance", "document_analysis"]
        assert task.estimated_duration_ms == 2000.0


class TestTaskAssignment:
    """Test cases for TaskAssignment class."""
    
    def test_assignment_creation(self, sample_task, sample_agent):
        """Test task assignment creation."""
        assignment = TaskAssignment(
            assignment_id="assign_123",
            task=sample_task,
            agent_id=sample_agent.agent_id,
            assigned_at=datetime.now()
        )
        
        assert assignment.assignment_id == "assign_123"
        assert assignment.task == sample_task
        assert assignment.agent_id == sample_agent.agent_id
        assert assignment.started_at is None
        assert assignment.completed_at is None
        assert assignment.is_completed is False


if __name__ == "__main__":
    pytest.main([__file__])