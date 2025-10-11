"""
Agent Management Dashboard API

Backend API for real-time agent status monitoring, performance metrics visualization,
agent configuration, and coordination workflow visualization.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict


class AgentStatus(Enum):
    """Agent operational status"""
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    STARTING = "starting"
    STOPPING = "stopping"


class AgentType(Enum):
    """Types of specialized agents"""
    TRANSACTION_ANALYZER = "transaction_analyzer"
    PATTERN_DETECTOR = "pattern_detector"
    RISK_ASSESSOR = "risk_assessor"
    COMPLIANCE = "compliance"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""
    agent_id: str
    requests_processed: int
    average_response_time_ms: float
    success_rate: float
    error_count: int
    current_load: float  # 0.0 to 1.0
    uptime_seconds: int
    last_activity: str
    memory_usage_mb: float
    cpu_usage_percent: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class AgentInfo:
    """Complete agent information"""
    agent_id: str
    agent_name: str
    agent_type: str
    status: str
    version: str
    capabilities: List[str]
    configuration: Dict[str, Any]
    metrics: AgentMetrics
    health_score: float  # 0.0 to 1.0
    last_heartbeat: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['metrics'] = self.metrics.to_dict()
        return data


@dataclass
class CoordinationEvent:
    """Agent coordination event"""
    event_id: str
    timestamp: str
    event_type: str  # request, response, coordination, escalation
    source_agent: str
    target_agent: Optional[str]
    transaction_id: Optional[str]
    status: str
    duration_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class AgentDashboardAPI:
    """
    Backend API for Agent Management Dashboard providing real-time monitoring,
    performance metrics, configuration management, and coordination visualization.
    """
    
    def __init__(self):
        """Initialize the dashboard API"""
        self.agents: Dict[str, AgentInfo] = {}
        self.coordination_events: List[CoordinationEvent] = []
        self.performance_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.alerts: List[Dict[str, Any]] = []
        
        # Initialize with sample agents
        self._initialize_sample_agents()
    
    def _initialize_sample_agents(self):
        """Initialize sample agents for demonstration"""
        agents_config = [
            {
                "agent_id": "txn_analyzer_001",
                "agent_name": "Transaction Analyzer",
                "agent_type": AgentType.TRANSACTION_ANALYZER.value,
                "version": "1.2.0",
                "capabilities": ["real_time_processing", "velocity_detection", "amount_analysis"]
            },
            {
                "agent_id": "pattern_detector_001",
                "agent_name": "Pattern Detector",
                "agent_type": AgentType.PATTERN_DETECTOR.value,
                "version": "1.1.5",
                "capabilities": ["anomaly_detection", "behavioral_analysis", "trend_prediction"]
            },
            {
                "agent_id": "risk_assessor_001",
                "agent_name": "Risk Assessor",
                "agent_type": AgentType.RISK_ASSESSOR.value,
                "version": "1.3.2",
                "capabilities": ["multi_factor_scoring", "geographic_analysis", "temporal_analysis"]
            },
            {
                "agent_id": "compliance_001",
                "agent_name": "Compliance Agent",
                "agent_type": AgentType.COMPLIANCE.value,
                "version": "1.0.0",
                "capabilities": ["regulatory_checking", "audit_trail", "policy_enforcement"]
            },
            {
                "agent_id": "orchestrator_001",
                "agent_name": "Agent Orchestrator",
                "agent_type": AgentType.ORCHESTRATOR.value,
                "version": "2.0.1",
                "capabilities": ["coordination", "decision_aggregation", "workflow_management"]
            }
        ]
        
        for config in agents_config:
            metrics = AgentMetrics(
                agent_id=config["agent_id"],
                requests_processed=0,
                average_response_time_ms=0.0,
                success_rate=1.0,
                error_count=0,
                current_load=0.0,
                uptime_seconds=0,
                last_activity=datetime.now().isoformat(),
                memory_usage_mb=128.5,
                cpu_usage_percent=15.2
            )
            
            agent = AgentInfo(
                agent_id=config["agent_id"],
                agent_name=config["agent_name"],
                agent_type=config["agent_type"],
                status=AgentStatus.ACTIVE.value,
                version=config["version"],
                capabilities=config["capabilities"],
                configuration={
                    "max_concurrent_requests": 10,
                    "timeout_seconds": 30,
                    "retry_attempts": 3
                },
                metrics=metrics,
                health_score=1.0,
                last_heartbeat=datetime.now().isoformat()
            )
            
            self.agents[agent.agent_id] = agent
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """
        Get information about all agents
        
        Returns:
            List of agent information dictionaries
        """
        return [agent.to_dict() for agent in self.agents.values()]
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific agent
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information dictionary or None
        """
        agent = self.agents.get(agent_id)
        return agent.to_dict() if agent else None
    
    def update_agent_status(self, agent_id: str, status: AgentStatus) -> Dict[str, Any]:
        """
        Update agent status
        
        Args:
            agent_id: Agent identifier
            status: New status
            
        Returns:
            Updated agent information
        """
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        
        self.agents[agent_id].status = status.value
        self.agents[agent_id].last_heartbeat = datetime.now().isoformat()
        
        return {
            "success": True,
            "agent_id": agent_id,
            "status": status.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def update_agent_metrics(
        self,
        agent_id: str,
        requests_processed: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        success: Optional[bool] = None,
        load: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Update agent performance metrics
        
        Args:
            agent_id: Agent identifier
            requests_processed: Number of requests processed
            response_time_ms: Response time in milliseconds
            success: Whether the request was successful
            load: Current load (0.0 to 1.0)
            
        Returns:
            Update result
        """
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        
        agent = self.agents[agent_id]
        metrics = agent.metrics
        
        # Update metrics
        if requests_processed is not None:
            metrics.requests_processed += requests_processed
        
        if response_time_ms is not None:
            # Calculate rolling average
            total_time = metrics.average_response_time_ms * (metrics.requests_processed - 1)
            metrics.average_response_time_ms = (total_time + response_time_ms) / metrics.requests_processed
        
        if success is not None:
            if not success:
                metrics.error_count += 1
            # Recalculate success rate
            metrics.success_rate = (metrics.requests_processed - metrics.error_count) / metrics.requests_processed
        
        if load is not None:
            metrics.current_load = load
        
        metrics.last_activity = datetime.now().isoformat()
        
        # Update health score based on metrics
        agent.health_score = self._calculate_health_score(metrics)
        
        # Store in performance history
        self.performance_history[agent_id].append({
            "timestamp": datetime.now().isoformat(),
            "response_time": metrics.average_response_time_ms,
            "success_rate": metrics.success_rate,
            "load": metrics.current_load,
            "health_score": agent.health_score
        })
        
        # Keep only last 100 data points
        if len(self.performance_history[agent_id]) > 100:
            self.performance_history[agent_id] = self.performance_history[agent_id][-100:]
        
        return {
            "success": True,
            "agent_id": agent_id,
            "metrics": metrics.to_dict(),
            "health_score": agent.health_score
        }
    
    def _calculate_health_score(self, metrics: AgentMetrics) -> float:
        """Calculate agent health score from metrics"""
        # Weighted health score calculation
        success_weight = 0.4
        response_time_weight = 0.3
        load_weight = 0.2
        error_weight = 0.1
        
        # Success rate component (0-1)
        success_score = metrics.success_rate
        
        # Response time component (inverse, normalized)
        # Assume 100ms is excellent, 1000ms is poor
        response_score = max(0, 1 - (metrics.average_response_time_ms / 1000))
        
        # Load component (inverse - lower load is better)
        load_score = 1 - metrics.current_load
        
        # Error component (inverse)
        error_rate = metrics.error_count / max(metrics.requests_processed, 1)
        error_score = 1 - error_rate
        
        health_score = (
            success_score * success_weight +
            response_score * response_time_weight +
            load_score * load_weight +
            error_score * error_weight
        )
        
        return round(health_score, 3)
    
    def get_agent_metrics_history(
        self,
        agent_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get historical performance metrics for an agent
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of data points
            
        Returns:
            Historical metrics data
        """
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        
        history = self.performance_history[agent_id][-limit:]
        
        return {
            "success": True,
            "agent_id": agent_id,
            "data_points": len(history),
            "history": history
        }
    
    def update_agent_configuration(
        self,
        agent_id: str,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update agent configuration
        
        Args:
            agent_id: Agent identifier
            configuration: New configuration parameters
            
        Returns:
            Update result
        """
        if agent_id not in self.agents:
            return {"success": False, "error": "Agent not found"}
        
        agent = self.agents[agent_id]
        agent.configuration.update(configuration)
        
        # Log configuration change
        self._log_coordination_event(
            event_type="configuration_change",
            source_agent=agent_id,
            target_agent=None,
            transaction_id=None,
            status="completed",
            duration_ms=5.0
        )
        
        return {
            "success": True,
            "agent_id": agent_id,
            "configuration": agent.configuration,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_coordination_event(
        self,
        event_type: str,
        source_agent: str,
        target_agent: Optional[str] = None,
        transaction_id: Optional[str] = None,
        status: str = "completed",
        duration_ms: float = 0.0
    ) -> Dict[str, Any]:
        """
        Log an agent coordination event
        
        Args:
            event_type: Type of coordination event
            source_agent: Source agent ID
            target_agent: Target agent ID (if applicable)
            transaction_id: Associated transaction ID
            status: Event status
            duration_ms: Event duration in milliseconds
            
        Returns:
            Logged event information
        """
        return self._log_coordination_event(
            event_type, source_agent, target_agent,
            transaction_id, status, duration_ms
        )
    
    def _log_coordination_event(
        self,
        event_type: str,
        source_agent: str,
        target_agent: Optional[str],
        transaction_id: Optional[str],
        status: str,
        duration_ms: float
    ) -> Dict[str, Any]:
        """Internal method to log coordination event"""
        event = CoordinationEvent(
            event_id=f"evt_{int(time.time() * 1000)}",
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            source_agent=source_agent,
            target_agent=target_agent,
            transaction_id=transaction_id,
            status=status,
            duration_ms=duration_ms
        )
        
        self.coordination_events.append(event)
        
        # Keep only last 1000 events
        if len(self.coordination_events) > 1000:
            self.coordination_events = self.coordination_events[-1000:]
        
        return {
            "success": True,
            "event": event.to_dict()
        }
    
    def get_coordination_events(
        self,
        limit: int = 100,
        agent_id: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get coordination events with optional filtering
        
        Args:
            limit: Maximum number of events to return
            agent_id: Filter by agent ID
            transaction_id: Filter by transaction ID
            
        Returns:
            List of coordination events
        """
        events = self.coordination_events
        
        # Apply filters
        if agent_id:
            events = [
                e for e in events
                if e.source_agent == agent_id or e.target_agent == agent_id
            ]
        
        if transaction_id:
            events = [e for e in events if e.transaction_id == transaction_id]
        
        # Get most recent events
        events = events[-limit:]
        
        return {
            "success": True,
            "total_events": len(events),
            "events": [e.to_dict() for e in events]
        }
    
    def get_coordination_workflow(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get complete coordination workflow for a transaction
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Workflow visualization data
        """
        events = [
            e for e in self.coordination_events
            if e.transaction_id == transaction_id
        ]
        
        if not events:
            return {
                "success": False,
                "error": "No events found for transaction"
            }
        
        # Build workflow graph
        nodes = set()
        edges = []
        
        for event in events:
            nodes.add(event.source_agent)
            if event.target_agent:
                nodes.add(event.target_agent)
                edges.append({
                    "from": event.source_agent,
                    "to": event.target_agent,
                    "type": event.event_type,
                    "status": event.status,
                    "duration_ms": event.duration_ms,
                    "timestamp": event.timestamp
                })
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "nodes": list(nodes),
            "edges": edges,
            "total_events": len(events),
            "timeline": [e.to_dict() for e in sorted(events, key=lambda x: x.timestamp)]
        }
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get dashboard summary with key metrics
        
        Returns:
            Dashboard summary data
        """
        total_agents = len(self.agents)
        active_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.ACTIVE.value)
        error_agents = sum(1 for a in self.agents.values() if a.status == AgentStatus.ERROR.value)
        
        total_requests = sum(a.metrics.requests_processed for a in self.agents.values())
        total_errors = sum(a.metrics.error_count for a in self.agents.values())
        
        avg_health = sum(a.health_score for a in self.agents.values()) / total_agents if total_agents > 0 else 0
        avg_response_time = sum(a.metrics.average_response_time_ms for a in self.agents.values()) / total_agents if total_agents > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                "total": total_agents,
                "active": active_agents,
                "idle": sum(1 for a in self.agents.values() if a.status == AgentStatus.IDLE.value),
                "busy": sum(1 for a in self.agents.values() if a.status == AgentStatus.BUSY.value),
                "error": error_agents,
                "offline": sum(1 for a in self.agents.values() if a.status == AgentStatus.OFFLINE.value)
            },
            "performance": {
                "total_requests_processed": total_requests,
                "total_errors": total_errors,
                "overall_success_rate": (total_requests - total_errors) / total_requests if total_requests > 0 else 1.0,
                "average_health_score": round(avg_health, 3),
                "average_response_time_ms": round(avg_response_time, 2)
            },
            "coordination": {
                "total_events": len(self.coordination_events),
                "recent_events": len([e for e in self.coordination_events if self._is_recent(e.timestamp, minutes=5)])
            },
            "alerts": {
                "total": len(self.alerts),
                "critical": len([a for a in self.alerts if a.get("severity") == "critical"])
            }
        }
    
    def _is_recent(self, timestamp_str: str, minutes: int = 5) -> bool:
        """Check if timestamp is within recent minutes"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            return datetime.now() - timestamp < timedelta(minutes=minutes)
        except:
            return False
    
    def simulate_agent_activity(self):
        """Simulate agent activity for demonstration purposes"""
        import random
        
        for agent_id, agent in self.agents.items():
            # Simulate processing requests
            if agent.status == AgentStatus.ACTIVE.value:
                self.update_agent_metrics(
                    agent_id=agent_id,
                    requests_processed=random.randint(1, 5),
                    response_time_ms=random.uniform(50, 300),
                    success=random.random() > 0.05,  # 95% success rate
                    load=random.uniform(0.1, 0.8)
                )
