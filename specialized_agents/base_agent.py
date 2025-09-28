"""
Base Agent Architecture for Specialized Fraud Detection Agents

Provides the foundation for all specialized agents with common functionality,
communication protocols, and performance monitoring.
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent operational status."""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    SHUTDOWN = "shutdown"


class AgentCapability(Enum):
    """Agent capabilities for specialization."""
    TRANSACTION_ANALYSIS = "transaction_analysis"
    PATTERN_DETECTION = "pattern_detection"
    RISK_ASSESSMENT = "risk_assessment"
    COMPLIANCE_CHECKING = "compliance_checking"
    REAL_TIME_PROCESSING = "real_time_processing"
    BATCH_PROCESSING = "batch_processing"
    LEARNING_ADAPTATION = "learning_adaptation"


@dataclass
class AgentMetrics:
    """Agent performance metrics."""
    requests_processed: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    average_processing_time_ms: float = 0.0
    peak_processing_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    last_activity: Optional[datetime] = None
    error_count: int = 0
    throughput_per_second: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.requests_processed == 0:
            return 0.0
        return (self.successful_analyses / self.requests_processed) * 100
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.requests_processed == 0:
            return 0.0
        return (self.failed_analyses / self.requests_processed) * 100


@dataclass
class AgentConfiguration:
    """Agent configuration parameters."""
    agent_id: str
    agent_name: str
    version: str
    capabilities: List[AgentCapability]
    max_concurrent_requests: int = 10
    timeout_seconds: int = 30
    retry_attempts: int = 3
    enable_metrics: bool = True
    enable_logging: bool = True
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """Result of agent processing."""
    success: bool
    result_data: Dict[str, Any]
    processing_time_ms: float
    confidence_score: float
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all specialized fraud detection agents.
    
    Provides common functionality including:
    - Agent lifecycle management
    - Performance metrics tracking
    - Error handling and logging
    - Configuration management
    - Health monitoring
    """
    
    def __init__(self, config: AgentConfiguration):
        """
        Initialize the base agent.
        
        Args:
            config: Agent configuration parameters
        """
        self.config = config
        self.status = AgentStatus.INITIALIZING
        self.metrics = AgentMetrics()
        self.start_time = datetime.now()
        self.logger = logging.getLogger(f"{__name__}.{config.agent_name}")
        
        # Initialize agent-specific components
        self._initialize_agent()
        
        self.status = AgentStatus.READY
        self.logger.info(f"Agent {config.agent_name} initialized successfully")
    
    @abstractmethod
    def _initialize_agent(self) -> None:
        """Initialize agent-specific components. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def process_request(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """
        Process a request. Must be implemented by subclasses.
        
        Args:
            request_data: Input data for processing
            
        Returns:
            ProcessingResult with analysis results
        """
        pass
    
    def execute_with_metrics(self, request_data: Dict[str, Any]) -> ProcessingResult:
        """
        Execute request processing with metrics tracking.
        
        Args:
            request_data: Input data for processing
            
        Returns:
            ProcessingResult with analysis results
        """
        if self.status != AgentStatus.READY:
            return ProcessingResult(
                success=Fult with analysis results
        """
        if self.status != AgentStatus.READY:
            return ProcessingResult(
                success=False,
                result_data={},
                processing_time_ms=0.0,
                confidence_score=0.0,
                error_message=f"Agent not ready. Current status: {self.status.value}"
            )
        
        start_time = time.time()
        self.status = AgentStatus.PROCESSING
        self.metrics.requests_processed += 1
        
        try:
            # Process the request
            result = self.process_request(request_data)
            
            # Update metrics
            processing_time_ms = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time_ms
            
            if result.success:
                self.metrics.successful_analyses += 1
            else:
                self.metrics.failed_analyses += 1
            
            # Update performance metrics
            self._update_performance_metrics(processing_time_ms, result.success)
            
            self.status = AgentStatus.READY
            self.metrics.last_activity = datetime.now()
            
            return result
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            self.metrics.failed_analyses += 1
            self._update_performance_metrics(processing_time_ms, False)
            
            self.status = AgentStatus.READY
            self.logger.error(f"Error processing request: {str(e)}")
            
            return ProcessingResult(
                success=False,
                result_data={},
                processing_time_ms=processing_time_ms,
                confidence_score=0.0,
                error_message=str(e)
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status and metrics.
        
        Returns:
            Dict containing status information
        """
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "agent_id": self.config.agent_id,
            "agent_name": self.config.agent_name,
            "version": self.config.version,
            "status": self.status.value,
            "capabilities": [cap.value for cap in self.config.capabilities],
            "metrics": {
                "requests_processed": self.metrics.requests_processed,
                "successful_analyses": self.metrics.successful_analyses,
                "failed_analyses": self.metrics.failed_analyses,
                "success_rate": self.metrics.success_rate,
                "error_rate": self.metrics.error_rate,
                "average_processing_time_ms": self.metrics.average_processing_time_ms,
                "peak_processing_time_ms": self.metrics.peak_processing_time_ms,
                "uptime_seconds": uptime_seconds,
                "throughput_per_second": self.metrics.throughput_per_second,
                "last_activity": self.metrics.last_activity.isoformat() if self.metrics.last_activity else None
            },
            "configuration": {
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "timeout_seconds": self.config.timeout_seconds,
                "retry_attempts": self.config.retry_attempts
            }
        }
    
    def get_health_check(self) -> Dict[str, Any]:
        """
        Perform health check and return status.
        
        Returns:
            Dict containing health information
        """
        health_status = "healthy"
        issues = []
        
        # Check if agent is responsive
        if self.status == AgentStatus.ERROR:
            health_status = "unhealthy"
            issues.append("Agent in error state")
        elif self.status == AgentStatus.MAINTENANCE:
            health_status = "maintenance"
            issues.append("Agent in maintenance mode")
        
        # Check success rate
        if self.metrics.success_rate < 95 and self.metrics.requests_processed > 10:
            health_status = "degraded" if health_status == "healthy" else health_status
            issues.append(f"Low success rate: {self.metrics.success_rate:.1f}%")
        
        # Check processing time
        if self.metrics.average_processing_time_ms > 5000:  # 5 seconds
            health_status = "degraded" if health_status == "healthy" else health_status
            issues.append(f"High processing time: {self.metrics.average_processing_time_ms:.1f}ms")
        
        # Check if agent has been inactive
        if self.metrics.last_activity:
            inactive_minutes = (datetime.now() - self.metrics.last_activity).total_seconds() / 60
            if inactive_minutes > 60:  # 1 hour
                health_status = "degraded" if health_status == "healthy" else health_status
                issues.append(f"Agent inactive for {inactive_minutes:.1f} minutes")
        
        return {
            "agent_id": self.config.agent_id,
            "agent_name": self.config.agent_name,
            "health_status": health_status,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        }
    
    def shutdown(self) -> bool:
        """
        Gracefully shutdown the agent.
        
        Returns:
            bool: True if shutdown successful
        """
        try:
            self.logger.info(f"Shutting down agent {self.config.agent_name}")
            self.status = AgentStatus.SHUTDOWN
            
            # Perform agent-specific cleanup
            self._cleanup_agent()
            
            self.logger.info(f"Agent {self.config.agent_name} shutdown complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Error shutting down agent {self.config.agent_name}: {str(e)}")
            return False
    
    def _cleanup_agent(self) -> None:
        """Agent-specific cleanup logic. Override in subclasses if needed."""
        pass
    
    def _update_performance_metrics(self, processing_time_ms: float, success: bool) -> None:
        """Update performance metrics with latest request data."""
        # Update processing time metrics
        self._processing_times.append(processing_time_ms)
        
        # Keep only last 100 processing times for average calculation
        if len(self._processing_times) > 100:
            self._processing_times.pop(0)
        
        # Calculate average processing time
        if self._processing_times:
            self.metrics.average_processing_time_ms = sum(self._processing_times) / len(self._processing_times)
        
        # Update peak processing time
        self.metrics.peak_processing_time_ms = max(self.metrics.peak_processing_time_ms, processing_time_ms)
        
        # Calculate throughput (requests per second over last minute)
        now = datetime.now()
        self._request_timestamps.append(now)
        
        # Remove timestamps older than 1 minute
        one_minute_ago = now - timedelta(minutes=1)
        self._request_timestamps = [ts for ts in self._request_timestamps if ts > one_minute_ago]
        
        # Calculate throughput
        self.metrics.throughput_per_second = len(self._request_timestamps) / 60.0
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics = AgentMetrics()
        self._processing_times = []
        self._request_timestamps = []
        self.logger.info(f"Reset metrics for agent {self.config.agent_name}")
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """
        Check if agent has a specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            bool: True if agent has the capability
        """
        return capability in self.config.capabilities