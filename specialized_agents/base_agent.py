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
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.capabilities = capabilities
        self.config = config or {}
        
        self.status = AgentStatus.INITIALIZING
        self.metrics = AgentMetrics()
        self.message_handlers: Dict[str, Callable] = {}
        self.error_handlers: Dict[str, Callable] = {}
        
        # Performance tracking
        self._processing_times: List[float] = []
        self._max_processing_history = 1000
        
        logger.info(f"Initializing agent {self.agent_name} ({self.agent_id})")
    
    def initialize(self) -> bool:
        """
        Initialize the agent and prepare for operation.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            logger.info(f"Starting initialization for agent {self.agent_name}")
            
            # Perform agent-specific initialization
            if self._initialize_agent():
                self.status = AgentStatus.READY
                logger.info(f"Agent {self.agent_name} initialized successfully")
                return True
            else:
                self.status = AgentStatus.ERROR
                logger.error(f"Agent {self.agent_name} initialization failed")
                return False
                
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Error initializing agent {self.agent_name}: {str(e)}")
            return False
    
    @abstractmethod
    def _initialize_agent(self) -> bool:
        """
        Agent-specific initialization logic.
        
        Returns:
            bool: True if initialization successful
        """
        pass
    
    def process_request(self, request: Dict[str, Any]) -> AgentResponse:
        """
        Process a request with performance monitoring.
        
        Args:
            request: Request data to process
            
        Returns:
            AgentResponse: Response with results and metadata
        """
        start_time = time.time()
        
        try:
            if self.status != AgentStatus.READY:
                return AgentResponse(
                    success=False,
                    error_message=f"Agent not ready (status: {self.status.value})"
                )
            
            self.status = AgentStatus.PROCESSING
            self.metrics.requests_processed += 1
            
            # Process the request
            result = self._process_request(request)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(processing_time, success=True)
            
            self.status = AgentStatus.READY
            
            return AgentResponse(
                success=True,
                result=result,
                processing_time_ms=processing_time,
                metadata={
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._update_performance_metrics(processing_time, success=False)
            
            self.status = AgentStatus.READY  # Reset to ready after error
            
            logger.error(f"Error processing request in {self.agent_name}: {str(e)}")
            
            return AgentResponse(
                success=False,
                error_message=str(e),
                processing_time_ms=processing_time,
                metadata={
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
    
    @abstractmethod
    def _process_request(self, request: Dict[str, Any]) -> Any:
        """
        Agent-specific request processing logic.
        
        Args:
            request: Request data to process
            
        Returns:
            Any: Processing result
        """
        pass
    
    def send_message(self, message: AgentMessage) -> bool:
        """
        Send a message to another agent.
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if message sent successfully
        """
        try:
            # In a real implementation, this would use the agent communication system
            logger.info(f"Agent {self.agent_name} sending message to {message.recipient_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message from {self.agent_name}: {str(e)}")
            return False
    
    def handle_message(self, message: AgentMessage) -> Optional[AgentResponse]:
        """
        Handle incoming message from another agent.
        
        Args:
            message: Incoming message
            
        Returns:
            Optional[AgentResponse]: Response if required
        """
        try:
            handler = self.message_handlers.get(message.message_type)
            if handler:
                return handler(message)
            else:
                logger.warning(f"No handler for message type {message.message_type} in {self.agent_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error handling message in {self.agent_name}: {str(e)}")
            return AgentResponse(
                success=False,
                error_message=f"Error handling message: {str(e)}"
            )
    
    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Handler function
        """
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type {message_type} in {self.agent_name}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status and metrics.
        
        Returns:
            Dict containing status information
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "capabilities": [cap.value for cap in self.capabilities],
            "metrics": {
                "requests_processed": self.metrics.requests_processed,
                "success_rate": self.metrics.success_rate,
                "average_processing_time_ms": self.metrics.average_processing_time_ms,
                "peak_processing_time_ms": self.metrics.peak_processing_time_ms,
                "uptime_hours": self.metrics.uptime_hours,
                "last_activity": self.metrics.last_activity.isoformat() if self.metrics.last_activity else None
            },
            "config": self.config
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
        
        # Check success rate
        if self.metrics.success_rate < 95 and self.metrics.requests_processed > 10:
            health_status = "degraded"
            issues.append(f"Low success rate: {self.metrics.success_rate:.1f}%")
        
        # Check processing time
        if self.metrics.average_processing_time_ms > 5000:  # 5 seconds
            health_status = "degraded"
            issues.append(f"High processing time: {self.metrics.average_processing_time_ms:.1f}ms")
        
        return {
            "agent_id": self.agent_id,
            "health_status": health_status,
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
    
    def shutdown(self) -> bool:
        """
        Gracefully shutdown the agent.
        
        Returns:
            bool: True if shutdown successful
        """
        try:
            logger.info(f"Shutting down agent {self.agent_name}")
            self.status = AgentStatus.SHUTDOWN
            
            # Perform agent-specific cleanup
            self._cleanup_agent()
            
            logger.info(f"Agent {self.agent_name} shutdown complete")
            return True
            
        except Exception as e:
            logger.error(f"Error shutting down agent {self.agent_name}: {str(e)}")
            return False
    
    def _cleanup_agent(self) -> None:
        """Agent-specific cleanup logic."""
        pass
    
    def _update_performance_metrics(self, processing_time_ms: float, success: bool) -> None:
        """Update performance metrics with latest request data."""
        self.metrics.last_activity = datetime.now()
        
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        # Update processing time metrics
        self._processing_times.append(processing_time_ms)
        if len(self._processing_times) > self._max_processing_history:
            self._processing_times.pop(0)
        
        self.metrics.average_processing_time_ms = sum(self._processing_times) / len(self._processing_times)
        self.metrics.peak_processing_time_ms = max(self.metrics.peak_processing_time_ms, processing_time_ms)
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self.metrics = AgentMetrics()
        self._processing_times = []
        logger.info(f"Reset metrics for agent {self.agent_name}")
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """
        Check if agent has a specific capability.
        
        Args:
            capability: Capability to check
            
        Returns:
            bool: True if agent has the capability
        """
        return capability in self.capabilities