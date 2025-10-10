"""
Tool Integrator for External API Management

Provides seamless integration with external APIs and services for fraud detection,
including identity verification, fraud databases, geolocation services, and more.
"""

import logging
import time
import json
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """External tool status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    MAINTENANCE = "maintenance"


class ToolType(Enum):
    """Types of external tools."""
    IDENTITY_VERIFICATION = "identity_verification"
    FRAUD_DATABASE = "fraud_database"
    GEOLOCATION = "geolocation"
    CURRENCY_API = "currency_api"
    SANCTIONS_CHECK = "sanctions_check"
    CREDIT_BUREAU = "credit_bureau"
    DEVICE_FINGERPRINT = "device_fingerprint"


@dataclass
class ToolConfiguration:
    """Configuration for external tool integration."""
    tool_id: str
    tool_name: str
    tool_type: ToolType
    base_url: str
    api_key: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    custom_headers: Dict[str, str] = field(default_factory=dict)
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResponse:
    """Response from external tool."""
    success: bool
    data: Dict[str, Any]
    response_time_ms: float
    tool_id: str
    timestamp: datetime
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolMetrics:
    """Metrics for external tool usage."""
    tool_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    rate_limit_hits: int = 0
    last_request_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return (self.cache_hits / total_cache_requests) * 100


class ExternalTool(ABC):
    """Abstract base class for external tool integrations."""
    
    def __init__(self, config: ToolConfiguration):
        """Initialize external tool."""
        self.config = config
        self.status = ToolStatus.AVAILABLE
        self.metrics = ToolMetrics(tool_id=config.tool_id)
        self.cache = {}
        self.rate_limit_tracker = {}
        
        # Configure HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        if config.api_key:
            self.session.headers.update({"Authorization": f"Bearer {config.api_key}"})
        self.session.headers.update(config.custom_headers)
        
        logger.info(f"Initialized external tool: {config.tool_name}")
    
    @abstractmethod
    def call_api(self, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Make API call to external service. Must be implemented by subclasses."""
        pass
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows request."""
        now = datetime.now()
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        
        if minute_key not in self.rate_limit_tracker:
            self.rate_limit_tracker[minute_key] = 0
        
        # Clean old entries
        cutoff_time = now - timedelta(minutes=2)
        self.rate_limit_tracker = {
            k: v for k, v in self.rate_limit_tracker.items()
            if datetime.strptime(k, "%Y-%m-%d %H:%M") > cutoff_time
        }
        
        if self.rate_limit_tracker[minute_key] >= self.config.rate_limit_per_minute:
            self.metrics.rate_limit_hits += 1
            return False
        
        self.rate_limit_tracker[minute_key] += 1
        return True
    
    def _get_cache_key(self, endpoint: str, data: Dict[str, Any]) -> str:
        """Generate cache key for request."""
        cache_data = {
            "endpoint": endpoint,
            "data": data,
            "tool_id": self.config.tool_id
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[ToolResponse]:
        """Get cached response if available and not expired."""
        if not self.config.enable_caching or cache_key not in self.cache:
            return None
        
        cached_item = self.cache[cache_key]
        if datetime.now() - cached_item["timestamp"] > timedelta(seconds=self.config.cache_ttl_seconds):
            del self.cache[cache_key]
            return None
        
        self.metrics.cache_hits += 1
        response = cached_item["response"]
        response.cached = True
        return response
    
    def _cache_response(self, cache_key: str, response: ToolResponse) -> None:
        """Cache successful response."""
        if self.config.enable_caching and response.success:
            self.cache[cache_key] = {
                "response": response,
                "timestamp": datetime.now()
            }
    
    def _update_metrics(self, response: ToolResponse) -> None:
        """Update tool metrics."""
        self.metrics.total_requests += 1
        self.metrics.last_request_time = datetime.now()
        
        if response.success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        # Update average response time
        if self.metrics.total_requests == 1:
            self.metrics.average_response_time_ms = response.response_time_ms
        else:
            self.metrics.average_response_time_ms = (
                (self.metrics.average_response_time_ms * (self.metrics.total_requests - 1) + 
                 response.response_time_ms) / self.metrics.total_requests
            )
        
        if not response.cached:
            self.metrics.cache_misses += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get tool status and metrics."""
        return {
            "tool_id": self.config.tool_id,
            "tool_name": self.config.tool_name,
            "tool_type": self.config.tool_type.value,
            "status": self.status.value,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.success_rate,
                "average_response_time_ms": self.metrics.average_response_time_ms,
                "cache_hit_rate": self.metrics.cache_hit_rate,
                "rate_limit_hits": self.metrics.rate_limit_hits,
                "last_request_time": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None
            },
            "configuration": {
                "base_url": self.config.base_url,
                "timeout_seconds": self.config.timeout_seconds,
                "rate_limit_per_minute": self.config.rate_limit_per_minute,
                "caching_enabled": self.config.enable_caching
            }
        }


class ToolIntegrator:
    """
    Central manager for external tool integrations.
    
    Provides unified interface for:
    - Tool registration and management
    - Request routing and load balancing
    - Error handling and fallback mechanisms
    - Performance monitoring and optimization
    """
    
    def __init__(self):
        """Initialize tool integrator."""
        self.tools: Dict[str, ExternalTool] = {}
        self.tool_types: Dict[ToolType, List[str]] = {}
        self.fallback_chains: Dict[str, List[str]] = {}
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Tool Integrator initialized")
    
    def register_tool(self, tool: ExternalTool) -> bool:
        """
        Register an external tool.
        
        Args:
            tool: ExternalTool instance to register
            
        Returns:
            bool: True if registration successful
        """
        try:
            tool_id = tool.config.tool_id
            tool_type = tool.config.tool_type
            
            self.tools[tool_id] = tool
            
            if tool_type not in self.tool_types:
                self.tool_types[tool_type] = []
            self.tool_types[tool_type].append(tool_id)
            
            # Initialize circuit breaker
            self.circuit_breakers[tool_id] = {
                "state": "closed",  # closed, open, half_open
                "failure_count": 0,
                "last_failure_time": None,
                "failure_threshold": 5,
                "recovery_timeout": 60  # seconds
            }
            
            logger.info(f"Registered tool: {tool.config.tool_name} ({tool_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool.config.tool_name}: {str(e)}")
            return False
    
    def set_fallback_chain(self, primary_tool_id: str, fallback_tool_ids: List[str]) -> None:
        """
        Set fallback chain for a tool.
        
        Args:
            primary_tool_id: Primary tool ID
            fallback_tool_ids: List of fallback tool IDs in order of preference
        """
        self.fallback_chains[primary_tool_id] = fallback_tool_ids
        logger.info(f"Set fallback chain for {primary_tool_id}: {fallback_tool_ids}")
    
    def call_tool(
        self, 
        tool_id: str, 
        endpoint: str, 
        data: Dict[str, Any],
        use_fallback: bool = True
    ) -> ToolResponse:
        """
        Call external tool with fallback support.
        
        Args:
            tool_id: Tool identifier
            endpoint: API endpoint to call
            data: Request data
            use_fallback: Whether to use fallback tools on failure
            
        Returns:
            ToolResponse with results
        """
        # Try primary tool
        response = self._call_single_tool(tool_id, endpoint, data)
        
        # If primary failed and fallback is enabled, try fallback tools
        if not response.success and use_fallback and tool_id in self.fallback_chains:
            logger.warning(f"Primary tool {tool_id} failed, trying fallbacks")
            
            for fallback_id in self.fallback_chains[tool_id]:
                if fallback_id in self.tools:
                    fallback_response = self._call_single_tool(fallback_id, endpoint, data)
                    if fallback_response.success:
                        fallback_response.metadata["used_fallback"] = True
                        fallback_response.metadata["primary_tool"] = tool_id
                        return fallback_response
        
        return response
    
    def call_tool_by_type(
        self, 
        tool_type: ToolType, 
        endpoint: str, 
        data: Dict[str, Any]
    ) -> ToolResponse:
        """
        Call any available tool of specified type.
        
        Args:
            tool_type: Type of tool to call
            endpoint: API endpoint to call
            data: Request data
            
        Returns:
            ToolResponse with results
        """
        if tool_type not in self.tool_types or not self.tool_types[tool_type]:
            return ToolResponse(
                success=False,
                data={},
                response_time_ms=0.0,
                tool_id="none",
                timestamp=datetime.now(),
                error_message=f"No tools available for type {tool_type.value}"
            )
        
        # Try tools in order of availability
        for tool_id in self.tool_types[tool_type]:
            if self._is_tool_available(tool_id):
                response = self._call_single_tool(tool_id, endpoint, data)
                if response.success:
                    return response
        
        # If all tools failed, return last response
        return self._call_single_tool(self.tool_types[tool_type][-1], endpoint, data)
    
    def _call_single_tool(self, tool_id: str, endpoint: str, data: Dict[str, Any]) -> ToolResponse:
        """Call a single external tool."""
        if tool_id not in self.tools:
            return ToolResponse(
                success=False,
                data={},
                response_time_ms=0.0,
                tool_id=tool_id,
                timestamp=datetime.now(),
                error_message=f"Tool {tool_id} not found"
            )
        
        tool = self.tools[tool_id]
        
        # Check circuit breaker
        if not self._check_circuit_breaker(tool_id):
            return ToolResponse(
                success=False,
                data={},
                response_time_ms=0.0,
                tool_id=tool_id,
                timestamp=datetime.now(),
                error_message=f"Tool {tool_id} circuit breaker is open"
            )
        
        try:
            response = tool.call_api(endpoint, data)
            
            # Update circuit breaker
            if response.success:
                self._reset_circuit_breaker(tool_id)
            else:
                self._record_failure(tool_id)
            
            return response
            
        except Exception as e:
            self._record_failure(tool_id)
            return ToolResponse(
                success=False,
                data={},
                response_time_ms=0.0,
                tool_id=tool_id,
                timestamp=datetime.now(),
                error_message=f"Tool call failed: {str(e)}"
            )
    
    def _is_tool_available(self, tool_id: str) -> bool:
        """Check if tool is available."""
        if tool_id not in self.tools:
            return False
        
        tool = self.tools[tool_id]
        return (tool.status == ToolStatus.AVAILABLE and 
                self._check_circuit_breaker(tool_id))
    
    def _check_circuit_breaker(self, tool_id: str) -> bool:
        """Check circuit breaker state."""
        if tool_id not in self.circuit_breakers:
            return True
        
        breaker = self.circuit_breakers[tool_id]
        
        if breaker["state"] == "closed":
            return True
        elif breaker["state"] == "open":
            # Check if recovery timeout has passed
            if (breaker["last_failure_time"] and 
                datetime.now() - breaker["last_failure_time"] > timedelta(seconds=breaker["recovery_timeout"])):
                breaker["state"] = "half_open"
                return True
            return False
        elif breaker["state"] == "half_open":
            return True
        
        return False
    
    def _record_failure(self, tool_id: str) -> None:
        """Record failure for circuit breaker."""
        if tool_id not in self.circuit_breakers:
            return
        
        breaker = self.circuit_breakers[tool_id]
        breaker["failure_count"] += 1
        breaker["last_failure_time"] = datetime.now()
        
        if breaker["failure_count"] >= breaker["failure_threshold"]:
            breaker["state"] = "open"
            logger.warning(f"Circuit breaker opened for tool {tool_id}")
    
    def _reset_circuit_breaker(self, tool_id: str) -> None:
        """Reset circuit breaker on success."""
        if tool_id not in self.circuit_breakers:
            return
        
        