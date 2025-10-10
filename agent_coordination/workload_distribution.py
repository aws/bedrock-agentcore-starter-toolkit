"""
Workload Distribution System

Provides intelligent task routing, load balancing, and dynamic scaling
for coordinated multi-agent fraud detection processing.
"""

import logging
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from queue import Queue, PriorityQueue, Empty
import uuid

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that can be distributed."""
    TRANSACTION_ANALYSIS = "transaction_analysis"
    PATTERN_DETECTION = "pattern_detection"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_CHECK = "compliance_check"
    IDENTITY_VERIFICATION = "identity_verification"
    GEOLOCATION_ANALYSIS = "geolocation_analysis"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AgentStatus(Enum):
    """Agent availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class Task:
    """Task to be distributed to agents."""
    task_id: str
    task_type: TaskType
    priority: TaskPriority
    payload: Dict[str, Any]
    created_at: datetime
    deadline: Optional[datetime] = None
    required_capabilities: List[str] = field(default_factory=list)
    estimated_duration_ms: float = 1000.0
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue ordering."""
        return self.priority.value > other.priority.value


@dataclass
class AgentCapabilities:
    """Agent capabilities and performance metrics."""
    agent_id: str
    agent_type: str
    capabilities: List[str]
    max_concurrent_tasks: int
    current_load: int
    average_processing_time_ms: float
    success_rate: float
    last_heartbeat: datetime
    status: AgentStatus = AgentStatus.AVAILABLE
    specialization_scores: Dict[TaskType, float] = field(default_factory=dict)
    performance_history: List[float] = field(default_factory=list)
    
    @property
    def load_percentage(self) -> float:
        """Calculate current load as percentage."""
        return (self.current_load / self.max_concurrent_tasks) * 100 if self.max_concurrent_tasks > 0 else 0
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available for new tasks."""
        return (self.status == AgentStatus.AVAILABLE and 
                self.current_load < self.max_concurrent_tasks)
    
    def get_specialization_score(self, task_type: TaskType) -> float:
        """Get specialization score for a task type."""
        return self.specialization_scores.get(task_type, 0.5)


@dataclass
class TaskAssignment:
    """Task assignment to an agent."""
    assignment_id: str
    task: Task
    agent_id: str
    assigned_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def processing_time_ms(self) -> Optional[float]:
        """Calculate processing time in milliseconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if assignment is completed."""
        return self.completed_at is not None


@dataclass
class LoadBalancingMetrics:
    """Metrics for load balancing performance."""
    total_tasks_distributed: int = 0
    successful_assignments: int = 0
    failed_assignments: int = 0
    average_assignment_time_ms: float = 0.0
    average_queue_wait_time_ms: float = 0.0
    agent_utilization: Dict[str, float] = field(default_factory=dict)
    task_type_distribution: Dict[TaskType, int] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class WorkloadDistributor:
    """
    Intelligent workload distribution system for multi-agent coordination.
    
    Features:
    - Task routing based on agent specialization
    - Dynamic load balancing
    - Auto-scaling recommendations
    - Performance monitoring and optimization
    """
    
    def __init__(self, max_queue_size: int = 10000):
        """
        Initialize workload distributor.
        
        Args:
            max_queue_size: Maximum size of task queue
        """
        self.max_queue_size = max_queue_size
        
        # Task management
        self.task_queue = PriorityQueue(maxsize=max_queue_size)
        self.pending_tasks: Dict[str, Task] = {}
        self.active_assignments: Dict[str, TaskAssignment] = {}
        self.completed_assignments: Dict[str, TaskAssignment] = {}
        
        # Agent management
        self.agents: Dict[str, AgentCapabilities] = {}
        self.agent_task_queues: Dict[str, Queue] = {}
        
        # Load balancing
        self.routing_strategies = {
            "round_robin": self._round_robin_routing,
            "least_loaded": self._least_loaded_routing,
            "specialization": self._specialization_routing,
            "performance": self._performance_routing,
            "hybrid": self._hybrid_routing
        }
        self.current_strategy = "hybrid"
        self.round_robin_index = 0
        
        # Metrics and monitoring
        self.metrics = LoadBalancingMetrics()
        self.performance_history = []
        
        # Configuration
        self.enable_auto_scaling = True
        self.scale_up_threshold = 80.0  # Load percentage
        self.scale_down_threshold = 30.0
        self.heartbeat_timeout = 60  # seconds
        
        # Threading
        self.is_running = False
        self.distributor_thread = None
        self.monitor_thread = None
        
        logger.info("Workload distributor initialized")
    
    def register_agent(self, agent_capabilities: AgentCapabilities) -> bool:
        """
        Register an agent with the distributor.
        
        Args:
            agent_capabilities: Agent capabilities and configuration
            
        Returns:
            True if registration successful
        """
        try:
            agent_id = agent_capabilities.agent_id
            self.agents[agent_id] = agent_capabilities
            self.agent_task_queues[agent_id] = Queue()
            
            logger.info(f"Registered agent {agent_id} with capabilities: {agent_capabilities.capabilities}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_capabilities.agent_id}: {str(e)}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the distributor.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if unregistration successful
        """
        try:
            if agent_id in self.agents:
                # Reassign active tasks from this agent
                self._reassign_agent_tasks(agent_id)
                
                # Remove agent
                del self.agents[agent_id]
                if agent_id in self.agent_task_queues:
                    del self.agent_task_queues[agent_id]
                
                logger.info(f"Unregistered agent {agent_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {str(e)}")
            return False
    
    def submit_task(self, task: Task) -> bool:
        """
        Submit a task for distribution.
        
        Args:
            task: Task to be distributed
            
        Returns:
            True if task was queued successfully
        """
        try:
            # Add to pending tasks
            self.pending_tasks[task.task_id] = task
            
            # Add to priority queue
            self.task_queue.put_nowait(task)
            
            # Update metrics
            self.metrics.total_tasks_distributed += 1
            self.metrics.task_type_distribution[task.task_type] = \
                self.metrics.task_type_distribution.get(task.task_type, 0) + 1
            
            logger.debug(f"Queued task {task.task_id} of type {task.task_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit task {task.task_id}: {str(e)}")
            return False
    
    def start(self) -> None:
        """Start the workload distributor."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start distributor thread
        self.distributor_thread = threading.Thread(target=self._distribution_loop, daemon=True)
        self.distributor_thread.start()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Workload distributor started")
    
    def stop(self) -> None:
        """Stop the workload distributor."""
        self.is_running = False
        
        if self.distributor_thread:
            self.distributor_thread.join(timeout=5)
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("Workload distributor stopped")
    
    def update_agent_status(self, agent_id: str, status: AgentStatus, current_load: int = None) -> None:
        """
        Update agent status and load.
        
        Args:
            agent_id: Agent identifier
            status: New agent status
            current_load: Current task load (optional)
        """
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = status
            agent.last_heartbeat = datetime.now()
            
            if current_load is not None:
                agent.current_load = current_load
            
            logger.debug(f"Updated agent {agent_id} status to {status.value}")
    
    def complete_task(self, assignment_id: str, result: Dict[str, Any] = None, error: str = None) -> bool:
        """
        Mark a task assignment as completed.
        
        Args:
            assignment_id: Assignment identifier
            result: Task result (if successful)
            error: Error message (if failed)
            
        Returns:
            True if completion was processed successfully
        """
        try:
            if assignment_id not in self.active_assignments:
                logger.warning(f"Assignment {assignment_id} not found in active assignments")
                return False
            
            assignment = self.active_assignments[assignment_id]
            assignment.completed_at = datetime.now()
            assignment.result = result
            assignment.error = error
            
            # Update agent load
            agent_id = assignment.agent_id
            if agent_id in self.agents:
                self.agents[agent_id].current_load -= 1
            
            # Move to completed assignments
            self.completed_assignments[assignment_id] = assignment
            del self.active_assignments[assignment_id]
            
            # Remove from pending tasks
            if assignment.task.task_id in self.pending_tasks:
                del self.pending_tasks[assignment.task.task_id]
            
            # Update metrics
            if error:
                self.metrics.failed_assignments += 1
            else:
                self.metrics.successful_assignments += 1
                
                # Update agent performance
                if assignment.processing_time_ms:
                    agent = self.agents[agent_id]
                    agent.performance_history.append(assignment.processing_time_ms)
                    if len(agent.performance_history) > 100:
                        agent.performance_history = agent.performance_history[-100:]
                    
                    agent.average_processing_time_ms = statistics.mean(agent.performance_history)
            
            logger.debug(f"Completed assignment {assignment_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete assignment {assignment_id}: {str(e)}")
            return False
    
    def get_metrics(self) -> LoadBalancingMetrics:
        """Get current load balancing metrics."""
        # Update agent utilization
        for agent_id, agent in self.agents.items():
            self.metrics.agent_utilization[agent_id] = agent.load_percentage
        
        self.metrics.last_updated = datetime.now()
        return self.metrics
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed distributor status."""
        metrics = self.get_metrics()
        
        return {
            "is_running": self.is_running,
            "current_strategy": self.current_strategy,
            "queue_size": self.task_queue.qsize(),
            "pending_tasks": len(self.pending_tasks),
            "active_assignments": len(self.active_assignments),
            "registered_agents": len(self.agents),
            "available_agents": len([a for a in self.agents.values() if a.is_available]),
            "metrics": {
                "total_tasks_distributed": metrics.total_tasks_distributed,
                "successful_assignments": metrics.successful_assignments,
                "failed_assignments": metrics.failed_assignments,
                "success_rate": (metrics.successful_assignments / max(metrics.total_tasks_distributed, 1)) * 100,
                "average_assignment_time_ms": metrics.average_assignment_time_ms,
                "agent_utilization": metrics.agent_utilization
            },
            "agents": {
                agent_id: {
                    "status": agent.status.value,
                    "load_percentage": agent.load_percentage,
                    "capabilities": agent.capabilities,
                    "average_processing_time_ms": agent.average_processing_time_ms
                }
                for agent_id, agent in self.agents.items()
            }
        }
    
    def set_routing_strategy(self, strategy: str) -> bool:
        """
        Set the task routing strategy.
        
        Args:
            strategy: Routing strategy name
            
        Returns:
            True if strategy was set successfully
        """
        if strategy in self.routing_strategies:
            self.current_strategy = strategy
            logger.info(f"Set routing strategy to {strategy}")
            return True
        
        logger.warning(f"Unknown routing strategy: {strategy}")
        return False
    
    def _distribution_loop(self) -> None:
        """Main distribution loop."""
        while self.is_running:
            try:
                # Get next task from queue
                try:
                    task = self.task_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Find best agent for task
                agent_id = self._select_agent(task)
                
                if agent_id:
                    # Assign task to agent
                    assignment = self._assign_task(task, agent_id)
                    if assignment:
                        logger.debug(f"Assigned task {task.task_id} to agent {agent_id}")
                    else:
                        # Re-queue task if assignment failed
                        self.task_queue.put_nowait(task)
                else:
                    # No available agent, re-queue task
                    self.task_queue.put_nowait(task)
                    time.sleep(0.1)  # Brief pause to avoid busy waiting
                
            except Exception as e:
                logger.error(f"Error in distribution loop: {str(e)}")
                time.sleep(1)
    
    def _monitoring_loop(self) -> None:
        """Monitoring and maintenance loop."""
        while self.is_running:
            try:
                # Check agent heartbeats
                self._check_agent_heartbeats()
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Check for auto-scaling needs
                if self.enable_auto_scaling:
                    self._check_auto_scaling()
                
                # Clean up old completed assignments
                self._cleanup_old_assignments()
                
                time.sleep(10)  # Run every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(10)
    
    def _select_agent(self, task: Task) -> Optional[str]:
        """Select the best agent for a task."""
        strategy_func = self.routing_strategies.get(self.current_strategy, self._hybrid_routing)
        return strategy_func(task)
    
    def _round_robin_routing(self, task: Task) -> Optional[str]:
        """Round-robin agent selection."""
        available_agents = [agent_id for agent_id, agent in self.agents.items() if agent.is_available]
        
        if not available_agents:
            return None
        
        # Select next agent in round-robin fashion
        agent_id = available_agents[self.round_robin_index % len(available_agents)]
        self.round_robin_index += 1
        
        return agent_id
    
    def _least_loaded_routing(self, task: Task) -> Optional[str]:
        """Select agent with lowest current load."""
        available_agents = [(agent_id, agent) for agent_id, agent in self.agents.items() if agent.is_available]
        
        if not available_agents:
            return None
        
        # Sort by load percentage
        available_agents.sort(key=lambda x: x[1].load_percentage)
        
        return available_agents[0][0]
    
    def _specialization_routing(self, task: Task) -> Optional[str]:
        """Select agent based on specialization for task type."""
        available_agents = [(agent_id, agent) for agent_id, agent in self.agents.items() if agent.is_available]
        
        if not available_agents:
            return None
        
        # Sort by specialization score for this task type
        available_agents.sort(key=lambda x: x[1].get_specialization_score(task.task_type), reverse=True)
        
        return available_agents[0][0]
    
    def _performance_routing(self, task: Task) -> Optional[str]:
        """Select agent based on performance metrics."""
        available_agents = [(agent_id, agent) for agent_id, agent in self.agents.items() if agent.is_available]
        
        if not available_agents:
            return None
        
        # Calculate performance score (lower processing time and higher success rate is better)
        def performance_score(agent):
            time_score = 1.0 / (agent.average_processing_time_ms + 1)  # Avoid division by zero
            success_score = agent.success_rate
            return time_score * success_score
        
        available_agents.sort(key=lambda x: performance_score(x[1]), reverse=True)
        
        return available_agents[0][0]
    
    def _hybrid_routing(self, task: Task) -> Optional[str]:
        """Hybrid routing combining multiple factors."""
        available_agents = [(agent_id, agent) for agent_id, agent in self.agents.items() if agent.is_available]
        
        if not available_agents:
            return None
        
        # Calculate composite score
        def composite_score(agent):
            load_score = 1.0 - (agent.load_percentage / 100.0)  # Lower load is better
            specialization_score = agent.get_specialization_score(task.task_type)
            performance_score = agent.success_rate / (agent.average_processing_time_ms + 1)
            
            # Weighted combination
            return (load_score * 0.4 + specialization_score * 0.4 + performance_score * 0.2)
        
        available_agents.sort(key=lambda x: composite_score(x[1]), reverse=True)
        
        return available_agents[0][0]
    
    def _assign_task(self, task: Task, agent_id: str) -> Optional[TaskAssignment]:
        """Assign a task to an agent."""
        try:
            assignment_id = str(uuid.uuid4())
            assignment = TaskAssignment(
                assignment_id=assignment_id,
                task=task,
                agent_id=agent_id,
                assigned_at=datetime.now()
            )
            
            # Update agent load
            if agent_id in self.agents:
                self.agents[agent_id].current_load += 1
            
            # Store assignment
            self.active_assignments[assignment_id] = assignment
            
            # Add to agent's task queue
            if agent_id in self.agent_task_queues:
                self.agent_task_queues[agent_id].put_nowait(assignment)
            
            return assignment
            
        except Exception as e:
            logger.error(f"Failed to assign task {task.task_id} to agent {agent_id}: {str(e)}")
            return None
    
    def _reassign_agent_tasks(self, agent_id: str) -> None:
        """Reassign tasks from an unavailable agent."""
        # Find active assignments for this agent
        agent_assignments = [
            assignment for assignment in self.active_assignments.values()
            if assignment.agent_id == agent_id and not assignment.is_completed
        ]
        
        for assignment in agent_assignments:
            # Increment retry count
            assignment.task.retry_count += 1
            
            if assignment.task.retry_count <= assignment.task.max_retries:
                # Re-queue task for reassignment
                self.task_queue.put_nowait(assignment.task)
                logger.info(f"Re-queued task {assignment.task.task_id} from unavailable agent {agent_id}")
            else:
                # Mark as failed
                assignment.completed_at = datetime.now()
                assignment.error = f"Max retries exceeded after agent {agent_id} became unavailable"
                self.completed_assignments[assignment.assignment_id] = assignment
                logger.warning(f"Task {assignment.task.task_id} failed after max retries")
            
            # Remove from active assignments
            if assignment.assignment_id in self.active_assignments:
                del self.active_assignments[assignment.assignment_id]
    
    def _check_agent_heartbeats(self) -> None:
        """Check agent heartbeats and mark stale agents as offline."""
        current_time = datetime.now()
        timeout_threshold = timedelta(seconds=self.heartbeat_timeout)
        
        for agent_id, agent in self.agents.items():
            if (current_time - agent.last_heartbeat) > timeout_threshold:
                if agent.status != AgentStatus.OFFLINE:
                    logger.warning(f"Agent {agent_id} heartbeat timeout, marking as offline")
                    agent.status = AgentStatus.OFFLINE
                    self._reassign_agent_tasks(agent_id)
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        # Calculate average assignment time
        recent_assignments = [
            assignment for assignment in self.completed_assignments.values()
            if assignment.completed_at and 
            (datetime.now() - assignment.completed_at).total_seconds() < 300  # Last 5 minutes
        ]
        
        if recent_assignments:
            assignment_times = [
                assignment.processing_time_ms for assignment in recent_assignments
                if assignment.processing_time_ms
            ]
            
            if assignment_times:
                self.metrics.average_assignment_time_ms = statistics.mean(assignment_times)
    
    def _check_auto_scaling(self) -> None:
        """Check if auto-scaling recommendations should be made."""
        if not self.agents:
            return
        
        # Calculate overall system load
        total_capacity = sum(agent.max_concurrent_tasks for agent in self.agents.values())
        total_load = sum(agent.current_load for agent in self.agents.values())
        
        if total_capacity > 0:
            system_load_percentage = (total_load / total_capacity) * 100
            
            if system_load_percentage > self.scale_up_threshold:
                logger.info(f"High system load detected: {system_load_percentage:.1f}% - consider scaling up")
            elif system_load_percentage < self.scale_down_threshold:
                logger.info(f"Low system load detected: {system_load_percentage:.1f}% - consider scaling down")
    
    def _cleanup_old_assignments(self) -> None:
        """Clean up old completed assignments."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        old_assignments = [
            assignment_id for assignment_id, assignment in self.completed_assignments.items()
            if assignment.completed_at and assignment.completed_at < cutoff_time
        ]
        
        for assignment_id in old_assignments:
            del self.completed_assignments[assignment_id]
        
        if old_assignments:
            logger.debug(f"Cleaned up {len(old_assignments)} old assignments")


def create_task(
    task_type: TaskType,
    payload: Dict[str, Any],
    priority: TaskPriority = TaskPriority.NORMAL,
    required_capabilities: List[str] = None,
    estimated_duration_ms: float = 1000.0
) -> Task:
    """
    Create a new task for distribution.
    
    Args:
        task_type: Type of task
        payload: Task data
        priority: Task priority
        required_capabilities: Required agent capabilities
        estimated_duration_ms: Estimated processing time
        
    Returns:
        Task instance
    """
    return Task(
        task_id=str(uuid.uuid4()),
        task_type=task_type,
        priority=priority,
        payload=payload,
        created_at=datetime.now(),
        required_capabilities=required_capabilities or [],
        estimated_duration_ms=estimated_duration_ms
    )