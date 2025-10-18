"""
Failure Injection - Simulates various failure scenarios.

Simplified version for fast-track demo.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Any, List, Optional

from .models import FailureScenario, FailureType, DegradationLevel


logger = logging.getLogger(__name__)


class FailureInjector:
    """Injects failures for resilience testing."""
    
    def __init__(self, resilience_validator=None):
        """Initialize failure injector.
        
        Args:
            resilience_validator: Optional ResilienceValidator for tracking recovery
        """
        self.active_failures: List[FailureScenario] = []
        self.is_running = False
        self.failure_history: List[Dict[str, Any]] = []
        self.resilience_validator = resilience_validator
        
        logger.info("FailureInjector initialized")
    
    async def start(self, failure_scenarios: List[FailureScenario], test_start_time: datetime):
        """
        Start failure injection based on scenarios.
        
        Args:
            failure_scenarios: List of failure scenarios to inject
            test_start_time: When the test started
        """
        if not failure_scenarios:
            logger.info("No failure scenarios to inject")
            return
        
        self.is_running = True
        logger.info(f"Starting failure injection with {len(failure_scenarios)} scenarios")
        
        # Schedule each failure
        tasks = []
        for scenario in failure_scenarios:
            task = asyncio.create_task(self._schedule_failure(scenario, test_start_time))
            tasks.append(task)
        
        # Wait for all failures to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop failure injection."""
        self.is_running = False
        self.active_failures.clear()
        logger.info("Failure injection stopped")
    
    async def _schedule_failure(self, scenario: FailureScenario, test_start_time: datetime):
        """Schedule a failure scenario."""
        try:
            # Wait until it's time to inject
            await asyncio.sleep(scenario.start_time_seconds)
            
            if not self.is_running:
                return
            
            logger.info(f"Injecting failure: {scenario.failure_type.value} for {scenario.duration_seconds}s")
            
            # Add to active failures
            self.active_failures.append(scenario)
            
            # Record in history
            self.failure_history.append({
                'failure_type': scenario.failure_type.value,
                'start_time': datetime.utcnow().isoformat(),
                'duration': scenario.duration_seconds,
                'severity': scenario.severity
            })
            
            # Register with resilience validator if available
            if self.resilience_validator:
                from .models import SystemMetrics
                # Create mock metrics for registration
                mock_metrics = SystemMetrics(
                    timestamp=datetime.utcnow(),
                    throughput_tps=1000.0,
                    requests_total=10000,
                    requests_successful=9990,
                    requests_failed=10,
                    avg_response_time_ms=150.0,
                    p50_response_time_ms=100.0,
                    p95_response_time_ms=300.0,
                    p99_response_time_ms=500.0,
                    max_response_time_ms=800.0,
                    error_rate=0.001,
                    timeout_rate=0.0,
                    cpu_utilization=0.60,
                    memory_utilization=0.70,
                    network_throughput_mbps=100.0
                )
                await self.resilience_validator.register_failure(scenario, mock_metrics)
            
            # Simulate failure for duration
            await self._inject_failure(scenario)
            await asyncio.sleep(scenario.duration_seconds)
            
            # Remove from active failures
            if scenario in self.active_failures:
                self.active_failures.remove(scenario)
            
            logger.info(f"Failure recovered: {scenario.failure_type.value}")
            
        except asyncio.CancelledError:
            logger.info(f"Failure injection cancelled: {scenario.failure_type.value}")
        except Exception as e:
            logger.error(f"Error in failure injection: {e}")
    
    async def _inject_failure(self, scenario: FailureScenario):
        """
        Inject a specific failure.
        
        Args:
            scenario: Failure scenario to inject
        """
        failure_type = scenario.failure_type
        
        if failure_type == FailureType.LAMBDA_CRASH:
            logger.warning(f"Simulating Lambda crash (severity: {scenario.severity})")
            # In real implementation, would trigger Lambda failures
            
        elif failure_type == FailureType.DYNAMODB_THROTTLE:
            logger.warning(f"Simulating DynamoDB throttling (severity: {scenario.severity})")
            # In real implementation, would reduce DynamoDB capacity
            
        elif failure_type == FailureType.NETWORK_LATENCY:
            latency_ms = scenario.parameters.get('latency_ms', 500)
            logger.warning(f"Simulating network latency: {latency_ms}ms")
            # In real implementation, would add network delays
            
        elif failure_type == FailureType.BEDROCK_RATE_LIMIT:
            logger.warning(f"Simulating Bedrock rate limiting (severity: {scenario.severity})")
            # In real implementation, would throttle Bedrock calls
            
        elif failure_type == FailureType.KINESIS_LAG:
            logger.warning(f"Simulating Kinesis lag (severity: {scenario.severity})")
            # In real implementation, would slow down Kinesis processing
            
        elif failure_type == FailureType.AGENT_TIMEOUT:
            logger.warning(f"Simulating agent timeouts (severity: {scenario.severity})")
            # In real implementation, would cause agent timeouts
            
        elif failure_type == FailureType.MEMORY_PRESSURE:
            logger.warning(f"Simulating memory pressure (severity: {scenario.severity})")
            # In real implementation, would increase memory usage
            
        elif failure_type == FailureType.CASCADING_FAILURE:
            logger.warning(f"Simulating cascading failure (severity: {scenario.severity})")
            # In real implementation, would trigger multiple failures
    
    def get_active_failures(self) -> List[FailureScenario]:
        """Get currently active failures."""
        return self.active_failures.copy()
    
    def get_degradation_level(self) -> DegradationLevel:
        """Calculate current system degradation level."""
        if not self.active_failures:
            return DegradationLevel.NONE
        
        # Calculate total severity
        total_severity = sum(f.severity for f in self.active_failures)
        
        if total_severity >= 2.0:
            return DegradationLevel.CRITICAL
        elif total_severity >= 1.0:
            return DegradationLevel.SEVERE
        elif total_severity >= 0.5:
            return DegradationLevel.MODERATE
        else:
            return DegradationLevel.NONE
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get failure injection statistics."""
        return {
            'is_running': self.is_running,
            'active_failures': len(self.active_failures),
            'total_failures_injected': len(self.failure_history),
            'degradation_level': self.get_degradation_level().value,
            'failure_history': self.failure_history
        }
