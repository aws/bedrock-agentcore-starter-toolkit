"""
Graceful Degradation Manager - Monitors and manages system degradation.

This module implements graceful degradation monitoring and automatic
strategy application to maintain system stability under stress.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from .models import (
    SystemMetrics,
    AgentMetrics,
    DegradationLevel,
    TestStatus
)


logger = logging.getLogger(__name__)


@dataclass
class DegradationEvent:
    """Records a degradation event."""
    
    timestamp: datetime
    level: DegradationLevel
    previous_level: DegradationLevel
    trigger_reason: str
    metrics_snapshot: Dict[str, Any]
    strategy_applied: Optional[str] = None
    recovery_time: Optional[float] = None  # seconds


@dataclass
class DegradationThresholds:
    """Configurable thresholds for degradation detection."""
    
    # Error rate thresholds
    moderate_error_rate: float = 0.01  # 1%
    severe_error_rate: float = 0.05    # 5%
    critical_error_rate: float = 0.10  # 10%
    
    # Response time thresholds (ms)
    moderate_p99_latency: float = 5000
    severe_p99_latency: float = 10000
    critical_p99_latency: float = 20000
    
    # CPU utilization thresholds
    moderate_cpu: float = 0.80  # 80%
    severe_cpu: float = 0.90    # 90%
    critical_cpu: float = 0.95  # 95%
    
    # Memory utilization thresholds
    moderate_memory: float = 0.85  # 85%
    severe_memory: float = 0.92    # 92%
    critical_memory: float = 0.97  # 97%
    
    # Timeout rate thresholds
    moderate_timeout_rate: float = 0.02  # 2%
    severe_timeout_rate: float = 0.05    # 5%
    critical_timeout_rate: float = 0.10  # 10%
    
    # Agent health thresholds
    moderate_agent_health: float = 0.80
    severe_agent_health: float = 0.60
    critical_agent_health: float = 0.40


class GracefulDegradationManager:
    """
    Manages system degradation detection and response strategies.
    
    This class monitors system metrics, detects degradation levels,
    applies appropriate strategies, and tracks recovery.
    """
    
    def __init__(
        self,
        thresholds: Optional[DegradationThresholds] = None,
        check_interval_seconds: float = 5.0
    ):
        """
        Initialize graceful degradation manager.
        
        Args:
            thresholds: Custom degradation thresholds
            check_interval_seconds: How often to check for degradation
        """
        self.thresholds = thresholds or DegradationThresholds()
        self.check_interval = check_interval_seconds
        
        # Current state
        self.current_level = DegradationLevel.NONE
        self.previous_level = DegradationLevel.NONE
        self.degradation_start_time: Optional[datetime] = None
        
        # Monitoring
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # History
        self.degradation_history: List[DegradationEvent] = []
        self.strategy_callbacks: Dict[DegradationLevel, List[Callable]] = {
            DegradationLevel.MODERATE: [],
            DegradationLevel.SEVERE: [],
            DegradationLevel.CRITICAL: []
        }
        
        # Statistics
        self.total_degradation_events = 0
        self.total_recovery_events = 0
        self.total_degradation_time = 0.0
        
        logger.info("GracefulDegradationManager initialized")
    
    def register_strategy(
        self,
        level: DegradationLevel,
        callback: Callable[[DegradationEvent], None]
    ):
        """
        Register a degradation strategy callback.
        
        Args:
            level: Degradation level to trigger on
            callback: Function to call when level is reached
        """
        if level != DegradationLevel.NONE:
            self.strategy_callbacks[level].append(callback)
            logger.info(f"Registered strategy for {level.value}")
    
    async def start_monitoring(
        self,
        metrics_provider: Callable[[], SystemMetrics],
        agent_metrics_provider: Optional[Callable[[], Dict[str, AgentMetrics]]] = None
    ):
        """
        Start continuous degradation monitoring.
        
        Args:
            metrics_provider: Function that returns current SystemMetrics
            agent_metrics_provider: Optional function that returns agent metrics
        """
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(metrics_provider, agent_metrics_provider)
        )
        logger.info("Started degradation monitoring")
    
    async def stop_monitoring(self):
        """Stop degradation monitoring."""
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped degradation monitoring")
    
    async def _monitoring_loop(
        self,
        metrics_provider: Callable[[], SystemMetrics],
        agent_metrics_provider: Optional[Callable[[], Dict[str, AgentMetrics]]]
    ):
        """Main monitoring loop."""
        try:
            while self.is_monitoring:
                try:
                    # Get current metrics
                    system_metrics = metrics_provider()
                    agent_metrics = agent_metrics_provider() if agent_metrics_provider else {}
                    
                    # Detect degradation level
                    new_level = self.detect_degradation_level(system_metrics, agent_metrics)
                    
                    # Handle level changes
                    if new_level != self.current_level:
                        await self._handle_level_change(new_level, system_metrics, agent_metrics)
                    
                    # Check for recovery
                    if self.current_level != DegradationLevel.NONE and new_level == DegradationLevel.NONE:
                        await self._handle_recovery()
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
    
    def detect_degradation_level(
        self,
        system_metrics: SystemMetrics,
        agent_metrics: Optional[Dict[str, AgentMetrics]] = None
    ) -> DegradationLevel:
        """
        Detect current system degradation level.
        
        Args:
            system_metrics: Current system metrics
            agent_metrics: Optional agent metrics
            
        Returns:
            Detected degradation level
        """
        scores = {
            DegradationLevel.NONE: 0,
            DegradationLevel.MODERATE: 0,
            DegradationLevel.SEVERE: 0,
            DegradationLevel.CRITICAL: 0
        }
        
        # Check error rate
        if system_metrics.error_rate >= self.thresholds.critical_error_rate:
            scores[DegradationLevel.CRITICAL] += 3
        elif system_metrics.error_rate >= self.thresholds.severe_error_rate:
            scores[DegradationLevel.SEVERE] += 2
        elif system_metrics.error_rate >= self.thresholds.moderate_error_rate:
            scores[DegradationLevel.MODERATE] += 1
        
        # Check P99 latency
        if system_metrics.p99_response_time_ms >= self.thresholds.critical_p99_latency:
            scores[DegradationLevel.CRITICAL] += 3
        elif system_metrics.p99_response_time_ms >= self.thresholds.severe_p99_latency:
            scores[DegradationLevel.SEVERE] += 2
        elif system_metrics.p99_response_time_ms >= self.thresholds.moderate_p99_latency:
            scores[DegradationLevel.MODERATE] += 1
        
        # Check CPU utilization
        if system_metrics.cpu_utilization >= self.thresholds.critical_cpu:
            scores[DegradationLevel.CRITICAL] += 2
        elif system_metrics.cpu_utilization >= self.thresholds.severe_cpu:
            scores[DegradationLevel.SEVERE] += 2
        elif system_metrics.cpu_utilization >= self.thresholds.moderate_cpu:
            scores[DegradationLevel.MODERATE] += 1
        
        # Check memory utilization
        if system_metrics.memory_utilization >= self.thresholds.critical_memory:
            scores[DegradationLevel.CRITICAL] += 2
        elif system_metrics.memory_utilization >= self.thresholds.severe_memory:
            scores[DegradationLevel.SEVERE] += 2
        elif system_metrics.memory_utilization >= self.thresholds.moderate_memory:
            scores[DegradationLevel.MODERATE] += 1
        
        # Check timeout rate
        if system_metrics.timeout_rate >= self.thresholds.critical_timeout_rate:
            scores[DegradationLevel.CRITICAL] += 2
        elif system_metrics.timeout_rate >= self.thresholds.severe_timeout_rate:
            scores[DegradationLevel.SEVERE] += 1
        elif system_metrics.timeout_rate >= self.thresholds.moderate_timeout_rate:
            scores[DegradationLevel.MODERATE] += 1
        
        # Check agent health if available
        if agent_metrics:
            avg_health = sum(m.health_score for m in agent_metrics.values()) / len(agent_metrics)
            
            if avg_health <= self.thresholds.critical_agent_health:
                scores[DegradationLevel.CRITICAL] += 2
            elif avg_health <= self.thresholds.severe_agent_health:
                scores[DegradationLevel.SEVERE] += 1
            elif avg_health <= self.thresholds.moderate_agent_health:
                scores[DegradationLevel.MODERATE] += 1
        
        # Determine level based on scores
        if scores[DegradationLevel.CRITICAL] >= 3:
            return DegradationLevel.CRITICAL
        elif scores[DegradationLevel.SEVERE] >= 2:
            return DegradationLevel.SEVERE
        elif scores[DegradationLevel.MODERATE] >= 1:
            return DegradationLevel.MODERATE
        else:
            return DegradationLevel.NONE
    
    async def _handle_level_change(
        self,
        new_level: DegradationLevel,
        system_metrics: SystemMetrics,
        agent_metrics: Dict[str, AgentMetrics]
    ):
        """Handle degradation level change."""
        self.previous_level = self.current_level
        self.current_level = new_level
        
        # Determine trigger reason
        trigger_reason = self._determine_trigger_reason(system_metrics, agent_metrics)
        
        # Create degradation event
        event = DegradationEvent(
            timestamp=datetime.utcnow(),
            level=new_level,
            previous_level=self.previous_level,
            trigger_reason=trigger_reason,
            metrics_snapshot={
                'error_rate': system_metrics.error_rate,
                'p99_latency_ms': system_metrics.p99_response_time_ms,
                'cpu_utilization': system_metrics.cpu_utilization,
                'memory_utilization': system_metrics.memory_utilization,
                'timeout_rate': system_metrics.timeout_rate,
                'throughput_tps': system_metrics.throughput_tps
            }
        )
        
        # Log level change
        # Compare enum values by their order
        level_order = {
            DegradationLevel.NONE: 0,
            DegradationLevel.MODERATE: 1,
            DegradationLevel.SEVERE: 2,
            DegradationLevel.CRITICAL: 3
        }
        
        if level_order[new_level] > level_order[self.previous_level]:
            logger.warning(
                f"Degradation level increased: {self.previous_level.value} -> {new_level.value} "
                f"(Reason: {trigger_reason})"
            )
            self.total_degradation_events += 1
            
            if self.degradation_start_time is None:
                self.degradation_start_time = datetime.utcnow()
        else:
            logger.info(
                f"Degradation level decreased: {self.previous_level.value} -> {new_level.value}"
            )
        
        # Apply degradation strategy
        if new_level != DegradationLevel.NONE:
            strategy_name = await self._apply_degradation_strategy(new_level, event)
            event.strategy_applied = strategy_name
        
        # Record event
        self.degradation_history.append(event)
    
    def _determine_trigger_reason(
        self,
        system_metrics: SystemMetrics,
        agent_metrics: Dict[str, AgentMetrics]
    ) -> str:
        """Determine what triggered the degradation."""
        reasons = []
        
        if system_metrics.error_rate >= self.thresholds.moderate_error_rate:
            reasons.append(f"High error rate ({system_metrics.error_rate:.2%})")
        
        if system_metrics.p99_response_time_ms >= self.thresholds.moderate_p99_latency:
            reasons.append(f"High P99 latency ({system_metrics.p99_response_time_ms:.0f}ms)")
        
        if system_metrics.cpu_utilization >= self.thresholds.moderate_cpu:
            reasons.append(f"High CPU ({system_metrics.cpu_utilization:.1%})")
        
        if system_metrics.memory_utilization >= self.thresholds.moderate_memory:
            reasons.append(f"High memory ({system_metrics.memory_utilization:.1%})")
        
        if system_metrics.timeout_rate >= self.thresholds.moderate_timeout_rate:
            reasons.append(f"High timeout rate ({system_metrics.timeout_rate:.2%})")
        
        if agent_metrics:
            unhealthy_agents = [
                name for name, metrics in agent_metrics.items()
                if metrics.health_score < self.thresholds.moderate_agent_health
            ]
            if unhealthy_agents:
                reasons.append(f"Unhealthy agents: {', '.join(unhealthy_agents)}")
        
        return "; ".join(reasons) if reasons else "Unknown"
    
    async def _apply_degradation_strategy(
        self,
        level: DegradationLevel,
        event: DegradationEvent
    ) -> str:
        """Apply appropriate degradation strategy."""
        strategy_name = f"{level.value}_strategy"
        
        logger.info(f"Applying degradation strategy: {strategy_name}")
        
        # Call registered callbacks
        callbacks = self.strategy_callbacks.get(level, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in strategy callback: {e}")
        
        # Built-in strategies
        if level == DegradationLevel.MODERATE:
            await self._apply_moderate_strategy(event)
        elif level == DegradationLevel.SEVERE:
            await self._apply_severe_strategy(event)
        elif level == DegradationLevel.CRITICAL:
            await self._apply_critical_strategy(event)
        
        return strategy_name
    
    async def _apply_moderate_strategy(self, event: DegradationEvent):
        """Apply moderate degradation strategy."""
        logger.info("Moderate degradation strategy:")
        logger.info("  - Reducing non-critical operations")
        logger.info("  - Increasing monitoring frequency")
        logger.info("  - Preparing for potential escalation")
        
        # In real implementation:
        # - Reduce logging verbosity
        # - Disable non-essential features
        # - Increase cache TTL
        # - Reduce background job frequency
    
    async def _apply_severe_strategy(self, event: DegradationEvent):
        """Apply severe degradation strategy."""
        logger.warning("Severe degradation strategy:")
        logger.warning("  - Enabling fast-path processing")
        logger.warning("  - Reducing timeout values")
        logger.warning("  - Activating circuit breakers")
        logger.warning("  - Shedding low-priority load")
        
        # In real implementation:
        # - Enable simplified processing paths
        # - Reduce timeout values
        # - Activate circuit breakers
        # - Shed low-priority requests
        # - Increase connection pool sizes
    
    async def _apply_critical_strategy(self, event: DegradationEvent):
        """Apply critical degradation strategy."""
        logger.error("Critical degradation strategy:")
        logger.error("  - Activating emergency mode")
        logger.error("  - Aggressive load shedding")
        logger.error("  - Minimal processing only")
        logger.error("  - Alerting operations team")
        
        # In real implementation:
        # - Enable emergency mode
        # - Aggressive load shedding
        # - Minimal processing only
        # - Send critical alerts
        # - Prepare for potential shutdown
    
    async def _handle_recovery(self):
        """Handle recovery from degraded state."""
        if self.degradation_start_time:
            recovery_time = (datetime.utcnow() - self.degradation_start_time).total_seconds()
            self.total_recovery_events += 1
            self.total_degradation_time += recovery_time
            
            # Update last event with recovery time
            if self.degradation_history:
                self.degradation_history[-1].recovery_time = recovery_time
            
            logger.info(
                f"System recovered from {self.previous_level.value} degradation "
                f"after {recovery_time:.1f} seconds"
            )
            
            self.degradation_start_time = None
    
    def get_current_level(self) -> DegradationLevel:
        """Get current degradation level."""
        return self.current_level
    
    def is_degraded(self) -> bool:
        """Check if system is currently degraded."""
        return self.current_level != DegradationLevel.NONE
    
    def get_degradation_history(self) -> List[DegradationEvent]:
        """Get degradation event history."""
        return self.degradation_history.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get degradation statistics."""
        avg_recovery_time = (
            self.total_degradation_time / self.total_recovery_events
            if self.total_recovery_events > 0
            else 0.0
        )
        
        # Count events by level
        level_counts = {
            DegradationLevel.MODERATE: 0,
            DegradationLevel.SEVERE: 0,
            DegradationLevel.CRITICAL: 0
        }
        
        for event in self.degradation_history:
            if event.level in level_counts:
                level_counts[event.level] += 1
        
        return {
            'current_level': self.current_level.value,
            'is_degraded': self.is_degraded(),
            'is_monitoring': self.is_monitoring,
            'total_degradation_events': self.total_degradation_events,
            'total_recovery_events': self.total_recovery_events,
            'total_degradation_time_seconds': self.total_degradation_time,
            'average_recovery_time_seconds': avg_recovery_time,
            'events_by_level': {
                level.value: count for level, count in level_counts.items()
            },
            'degradation_start_time': (
                self.degradation_start_time.isoformat()
                if self.degradation_start_time
                else None
            )
        }
    
    def reset_statistics(self):
        """Reset degradation statistics."""
        self.degradation_history.clear()
        self.total_degradation_events = 0
        self.total_recovery_events = 0
        self.total_degradation_time = 0.0
        logger.info("Degradation statistics reset")
