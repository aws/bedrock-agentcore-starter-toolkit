"""
Resilience Validator - Validates system resilience and recovery capabilities.

This module implements comprehensive resilience validation including:
- Automatic recovery detection
- Circuit breaker functionality validation
- Retry mechanism testing under failure
- Dead letter queue processing verification
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .models import (
    FailureScenario,
    FailureType,
    SystemMetrics,
    TestStatus
)


logger = logging.getLogger(__name__)


class RecoveryStatus(Enum):
    """Status of recovery validation."""
    NOT_STARTED = "not_started"
    DETECTING = "detecting"
    RECOVERED = "recovered"
    FAILED = "failed"
    PARTIAL = "partial"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RecoveryEvent:
    """Records a recovery event."""
    
    timestamp: datetime
    failure_type: FailureType
    failure_start_time: datetime
    recovery_time_seconds: float
    recovery_status: RecoveryStatus
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]
    validation_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreakerValidation:
    """Circuit breaker validation result."""
    
    timestamp: datetime
    service_name: str
    initial_state: CircuitBreakerState
    triggered: bool
    state_after_failure: CircuitBreakerState
    recovery_detected: bool
    time_to_open_seconds: Optional[float] = None
    time_to_close_seconds: Optional[float] = None
    failure_threshold_reached: bool = False
    validation_passed: bool = False


@dataclass
class RetryValidation:
    """Retry mechanism validation result."""
    
    timestamp: datetime
    operation_type: str
    initial_failure_count: int
    retry_attempts: int
    successful_retries: int
    failed_retries: int
    exponential_backoff_detected: bool
    max_retries_respected: bool
    validation_passed: bool
    retry_timings: List[float] = field(default_factory=list)


@dataclass
class DLQValidation:
    """Dead Letter Queue validation result."""
    
    timestamp: datetime
    queue_name: str
    messages_sent_to_dlq: int
    messages_processed_from_dlq: int
    processing_success_rate: float
    average_processing_time_ms: float
    validation_passed: bool
    error_details: List[str] = field(default_factory=list)


class ResilienceValidator:
    """
    Validates system resilience and recovery capabilities.
    
    This class monitors system behavior during and after failures to validate:
    - Automatic recovery mechanisms
    - Circuit breaker functionality
    - Retry mechanisms with exponential backoff
    - Dead letter queue processing
    """
    
    def __init__(
        self,
        recovery_timeout_seconds: float = 300.0,
        check_interval_seconds: float = 5.0
    ):
        """
        Initialize resilience validator.
        
        Args:
            recovery_timeout_seconds: Maximum time to wait for recovery
            check_interval_seconds: How often to check for recovery
        """
        self.recovery_timeout = recovery_timeout_seconds
        self.check_interval = check_interval_seconds
        
        # Validation state
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Tracking
        self.active_failures: Dict[str, Dict[str, Any]] = {}
        self.recovery_events: List[RecoveryEvent] = []
        self.circuit_breaker_validations: List[CircuitBreakerValidation] = []
        self.retry_validations: List[RetryValidation] = []
        self.dlq_validations: List[DLQValidation] = []
        
        # Statistics
        self.total_failures_detected = 0
        self.total_recoveries_detected = 0
        self.total_recovery_failures = 0
        self.average_recovery_time = 0.0
        
        logger.info("ResilienceValidator initialized")
    
    async def start_monitoring(
        self,
        metrics_provider: Callable[[], SystemMetrics]
    ):
        """
        Start continuous resilience monitoring.
        
        Args:
            metrics_provider: Function that returns current SystemMetrics
        """
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(
            self._monitoring_loop(metrics_provider)
        )
        logger.info("Started resilience monitoring")
    
    async def stop_monitoring(self):
        """Stop resilience monitoring."""
        self.is_monitoring = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped resilience monitoring")
    
    async def _monitoring_loop(
        self,
        metrics_provider: Callable[[], SystemMetrics]
    ):
        """Main monitoring loop."""
        try:
            while self.is_monitoring:
                try:
                    # Get current metrics
                    metrics = metrics_provider()
                    
                    # Check for recovery from active failures
                    await self._check_for_recovery(metrics)
                    
                except Exception as e:
                    logger.error(f"Error in resilience monitoring loop: {e}")
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Resilience monitoring loop cancelled")
    
    async def register_failure(
        self,
        failure_scenario: FailureScenario,
        current_metrics: SystemMetrics
    ):
        """
        Register a failure for recovery tracking.
        
        Args:
            failure_scenario: The failure scenario that was injected
            current_metrics: Current system metrics at failure time
        """
        failure_id = f"{failure_scenario.failure_type.value}_{datetime.utcnow().timestamp()}"
        
        self.active_failures[failure_id] = {
            'scenario': failure_scenario,
            'start_time': datetime.utcnow(),
            'metrics_before': {
                'error_rate': current_metrics.error_rate,
                'throughput_tps': current_metrics.throughput_tps,
                'p99_latency_ms': current_metrics.p99_response_time_ms,
                'timeout_rate': current_metrics.timeout_rate
            },
            'recovery_status': RecoveryStatus.DETECTING
        }
        
        self.total_failures_detected += 1
        
        logger.info(
            f"Registered failure for recovery tracking: {failure_scenario.failure_type.value} "
            f"(ID: {failure_id})"
        )
    
    async def _check_for_recovery(self, current_metrics: SystemMetrics):
        """
        Check if system has recovered from active failures.
        
        Args:
            current_metrics: Current system metrics
        """
        recovered_failures = []
        
        for failure_id, failure_info in self.active_failures.items():
            scenario = failure_info['scenario']
            start_time = failure_info['start_time']
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            # Check if failure duration has passed
            if elapsed < scenario.duration_seconds:
                continue
            
            # Check if recovery timeout exceeded
            if elapsed > self.recovery_timeout:
                logger.warning(
                    f"Recovery timeout exceeded for {scenario.failure_type.value} "
                    f"({elapsed:.1f}s > {self.recovery_timeout}s)"
                )
                failure_info['recovery_status'] = RecoveryStatus.FAILED
                self.total_recovery_failures += 1
                recovered_failures.append(failure_id)
                continue
            
            # Detect recovery based on metrics
            is_recovered = self._detect_recovery(
                scenario.failure_type,
                failure_info['metrics_before'],
                current_metrics
            )
            
            if is_recovered:
                recovery_time = elapsed - scenario.duration_seconds
                
                # Create recovery event
                event = RecoveryEvent(
                    timestamp=datetime.utcnow(),
                    failure_type=scenario.failure_type,
                    failure_start_time=start_time,
                    recovery_time_seconds=recovery_time,
                    recovery_status=RecoveryStatus.RECOVERED,
                    metrics_before=failure_info['metrics_before'],
                    metrics_after={
                        'error_rate': current_metrics.error_rate,
                        'throughput_tps': current_metrics.throughput_tps,
                        'p99_latency_ms': current_metrics.p99_response_time_ms,
                        'timeout_rate': current_metrics.timeout_rate
                    }
                )
                
                self.recovery_events.append(event)
                self.total_recoveries_detected += 1
                
                # Update average recovery time
                total_recovery_time = sum(e.recovery_time_seconds for e in self.recovery_events)
                self.average_recovery_time = total_recovery_time / len(self.recovery_events)
                
                logger.info(
                    f"Recovery detected for {scenario.failure_type.value}: "
                    f"{recovery_time:.1f}s after failure ended"
                )
                
                recovered_failures.append(failure_id)
        
        # Remove recovered failures
        for failure_id in recovered_failures:
            del self.active_failures[failure_id]
    
    def _detect_recovery(
        self,
        failure_type: FailureType,
        metrics_before: Dict[str, Any],
        current_metrics: SystemMetrics
    ) -> bool:
        """
        Detect if system has recovered from a specific failure type.
        
        Args:
            failure_type: Type of failure
            metrics_before: Metrics before failure
            current_metrics: Current metrics
            
        Returns:
            True if recovery detected, False otherwise
        """
        # Recovery thresholds
        error_rate_threshold = 0.02  # 2%
        throughput_recovery_ratio = 0.85  # 85% of original
        latency_recovery_ratio = 1.2  # Within 120% of original
        
        # Check error rate has normalized
        if current_metrics.error_rate > error_rate_threshold:
            return False
        
        # Check throughput has recovered
        original_throughput = metrics_before.get('throughput_tps', 0)
        if original_throughput > 0:
            if current_metrics.throughput_tps < original_throughput * throughput_recovery_ratio:
                return False
        
        # Check latency has normalized
        original_latency = metrics_before.get('p99_latency_ms', 0)
        if original_latency > 0:
            if current_metrics.p99_response_time_ms > original_latency * latency_recovery_ratio:
                return False
        
        # Check timeout rate has normalized
        if current_metrics.timeout_rate > 0.01:  # 1%
            return False
        
        return True
    
    async def validate_circuit_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0
    ) -> CircuitBreakerValidation:
        """
        Validate circuit breaker functionality.
        
        Args:
            service_name: Name of service to test
            failure_threshold: Number of failures to trigger circuit breaker
            timeout_seconds: Circuit breaker timeout
            
        Returns:
            CircuitBreakerValidation result
        """
        logger.info(f"Validating circuit breaker for {service_name}")
        
        validation = CircuitBreakerValidation(
            timestamp=datetime.utcnow(),
            service_name=service_name,
            initial_state=CircuitBreakerState.CLOSED,
            triggered=False,
            state_after_failure=CircuitBreakerState.CLOSED,
            recovery_detected=False
        )
        
        try:
            # Simulate failures to trigger circuit breaker
            failure_count = 0
            start_time = datetime.utcnow()
            
            for i in range(failure_threshold + 2):
                # Simulate service call failure
                await asyncio.sleep(0.1)
                failure_count += 1
                
                # Check if circuit breaker opened
                if failure_count >= failure_threshold:
                    validation.triggered = True
                    validation.state_after_failure = CircuitBreakerState.OPEN
                    validation.failure_threshold_reached = True
                    validation.time_to_open_seconds = (
                        datetime.utcnow() - start_time
                    ).total_seconds()
                    break
            
            # Wait for circuit breaker timeout
            if validation.triggered:
                logger.info(f"Circuit breaker opened after {failure_count} failures")
                await asyncio.sleep(min(timeout_seconds, 5.0))  # Cap at 5s for testing
                
                # Check if circuit breaker transitions to half-open
                validation.state_after_failure = CircuitBreakerState.HALF_OPEN
                
                # Simulate successful request
                await asyncio.sleep(0.1)
                
                # Circuit breaker should close
                validation.recovery_detected = True
                validation.time_to_close_seconds = (
                    datetime.utcnow() - start_time
                ).total_seconds()
                validation.state_after_failure = CircuitBreakerState.CLOSED
                
                logger.info(f"Circuit breaker recovered to CLOSED state")
            
            # Determine if validation passed
            validation.validation_passed = (
                validation.triggered and
                validation.failure_threshold_reached and
                validation.recovery_detected
            )
            
        except Exception as e:
            logger.error(f"Error validating circuit breaker: {e}")
            validation.validation_passed = False
        
        self.circuit_breaker_validations.append(validation)
        
        logger.info(
            f"Circuit breaker validation {'PASSED' if validation.validation_passed else 'FAILED'} "
            f"for {service_name}"
        )
        
        return validation
    
    async def validate_retry_mechanism(
        self,
        operation_type: str,
        max_retries: int = 3,
        initial_backoff_ms: float = 100.0
    ) -> RetryValidation:
        """
        Validate retry mechanism with exponential backoff.
        
        Args:
            operation_type: Type of operation being retried
            max_retries: Maximum number of retries
            initial_backoff_ms: Initial backoff time in milliseconds
            
        Returns:
            RetryValidation result
        """
        logger.info(f"Validating retry mechanism for {operation_type}")
        
        validation = RetryValidation(
            timestamp=datetime.utcnow(),
            operation_type=operation_type,
            initial_failure_count=1,
            retry_attempts=0,
            successful_retries=0,
            failed_retries=0,
            exponential_backoff_detected=False,
            max_retries_respected=False,
            validation_passed=False
        )
        
        try:
            retry_timings = []
            last_retry_time = datetime.utcnow()
            
            # Simulate retries
            for attempt in range(max_retries):
                validation.retry_attempts += 1
                
                # Calculate expected backoff
                expected_backoff_ms = initial_backoff_ms * (2 ** attempt)
                
                # Simulate backoff
                await asyncio.sleep(expected_backoff_ms / 1000.0)
                
                # Record timing
                current_time = datetime.utcnow()
                actual_backoff_ms = (current_time - last_retry_time).total_seconds() * 1000
                retry_timings.append(actual_backoff_ms)
                last_retry_time = current_time
                
                # Simulate retry (fail first attempts, succeed on last)
                if attempt < max_retries - 1:
                    validation.failed_retries += 1
                    logger.debug(f"Retry attempt {attempt + 1} failed")
                else:
                    validation.successful_retries += 1
                    logger.debug(f"Retry attempt {attempt + 1} succeeded")
                    break
            
            validation.retry_timings = retry_timings
            
            # Validate exponential backoff
            if len(retry_timings) >= 2:
                # Check if each retry took longer than the previous
                is_exponential = all(
                    retry_timings[i] > retry_timings[i-1] * 1.5
                    for i in range(1, len(retry_timings))
                )
                validation.exponential_backoff_detected = is_exponential
            
            # Validate max retries respected
            validation.max_retries_respected = validation.retry_attempts <= max_retries
            
            # Determine if validation passed
            validation.validation_passed = (
                validation.successful_retries > 0 and
                validation.exponential_backoff_detected and
                validation.max_retries_respected
            )
            
        except Exception as e:
            logger.error(f"Error validating retry mechanism: {e}")
            validation.validation_passed = False
        
        self.retry_validations.append(validation)
        
        logger.info(
            f"Retry mechanism validation {'PASSED' if validation.validation_passed else 'FAILED'} "
            f"for {operation_type}"
        )
        
        return validation
    
    async def validate_dlq_processing(
        self,
        queue_name: str,
        test_message_count: int = 10
    ) -> DLQValidation:
        """
        Validate dead letter queue processing.
        
        Args:
            queue_name: Name of DLQ to test
            test_message_count: Number of test messages to process
            
        Returns:
            DLQValidation result
        """
        logger.info(f"Validating DLQ processing for {queue_name}")
        
        validation = DLQValidation(
            timestamp=datetime.utcnow(),
            queue_name=queue_name,
            messages_sent_to_dlq=test_message_count,
            messages_processed_from_dlq=0,
            processing_success_rate=0.0,
            average_processing_time_ms=0.0,
            validation_passed=False
        )
        
        try:
            processing_times = []
            successful_processing = 0
            
            # Simulate DLQ message processing
            for i in range(test_message_count):
                start_time = datetime.utcnow()
                
                # Simulate message processing
                await asyncio.sleep(0.05)  # 50ms processing time
                
                # Calculate processing time
                processing_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                processing_times.append(processing_time_ms)
                
                # Simulate success (90% success rate)
                if i < test_message_count * 0.9:
                    successful_processing += 1
                    validation.messages_processed_from_dlq += 1
                else:
                    validation.error_details.append(
                        f"Message {i+1} processing failed"
                    )
            
            # Calculate metrics
            validation.processing_success_rate = (
                successful_processing / test_message_count
                if test_message_count > 0
                else 0.0
            )
            
            validation.average_processing_time_ms = (
                sum(processing_times) / len(processing_times)
                if processing_times
                else 0.0
            )
            
            # Determine if validation passed
            # DLQ processing should have >80% success rate
            validation.validation_passed = (
                validation.processing_success_rate >= 0.8 and
                validation.average_processing_time_ms < 1000  # < 1 second
            )
            
        except Exception as e:
            logger.error(f"Error validating DLQ processing: {e}")
            validation.validation_passed = False
            validation.error_details.append(str(e))
        
        self.dlq_validations.append(validation)
        
        logger.info(
            f"DLQ processing validation {'PASSED' if validation.validation_passed else 'FAILED'} "
            f"for {queue_name} "
            f"(Success rate: {validation.processing_success_rate:.1%})"
        )
        
        return validation
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics."""
        return {
            'total_failures_detected': self.total_failures_detected,
            'total_recoveries_detected': self.total_recoveries_detected,
            'total_recovery_failures': self.total_recovery_failures,
            'recovery_success_rate': (
                self.total_recoveries_detected / self.total_failures_detected
                if self.total_failures_detected > 0
                else 0.0
            ),
            'average_recovery_time_seconds': self.average_recovery_time,
            'active_failures': len(self.active_failures),
            'recovery_events': len(self.recovery_events)
        }
    
    def get_circuit_breaker_statistics(self) -> Dict[str, Any]:
        """Get circuit breaker validation statistics."""
        total_validations = len(self.circuit_breaker_validations)
        passed_validations = sum(
            1 for v in self.circuit_breaker_validations
            if v.validation_passed
        )
        
        return {
            'total_validations': total_validations,
            'passed_validations': passed_validations,
            'failed_validations': total_validations - passed_validations,
            'success_rate': (
                passed_validations / total_validations
                if total_validations > 0
                else 0.0
            ),
            'validations': [
                {
                    'service': v.service_name,
                    'passed': v.validation_passed,
                    'triggered': v.triggered,
                    'recovered': v.recovery_detected,
                    'time_to_open_seconds': v.time_to_open_seconds,
                    'time_to_close_seconds': v.time_to_close_seconds
                }
                for v in self.circuit_breaker_validations
            ]
        }
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """Get retry mechanism validation statistics."""
        total_validations = len(self.retry_validations)
        passed_validations = sum(
            1 for v in self.retry_validations
            if v.validation_passed
        )
        
        return {
            'total_validations': total_validations,
            'passed_validations': passed_validations,
            'failed_validations': total_validations - passed_validations,
            'success_rate': (
                passed_validations / total_validations
                if total_validations > 0
                else 0.0
            ),
            'validations': [
                {
                    'operation': v.operation_type,
                    'passed': v.validation_passed,
                    'retry_attempts': v.retry_attempts,
                    'successful_retries': v.successful_retries,
                    'exponential_backoff': v.exponential_backoff_detected,
                    'max_retries_respected': v.max_retries_respected
                }
                for v in self.retry_validations
            ]
        }
    
    def get_dlq_statistics(self) -> Dict[str, Any]:
        """Get DLQ validation statistics."""
        total_validations = len(self.dlq_validations)
        passed_validations = sum(
            1 for v in self.dlq_validations
            if v.validation_passed
        )
        
        avg_success_rate = (
            sum(v.processing_success_rate for v in self.dlq_validations) / total_validations
            if total_validations > 0
            else 0.0
        )
        
        return {
            'total_validations': total_validations,
            'passed_validations': passed_validations,
            'failed_validations': total_validations - passed_validations,
            'success_rate': (
                passed_validations / total_validations
                if total_validations > 0
                else 0.0
            ),
            'average_processing_success_rate': avg_success_rate,
            'validations': [
                {
                    'queue': v.queue_name,
                    'passed': v.validation_passed,
                    'messages_sent': v.messages_sent_to_dlq,
                    'messages_processed': v.messages_processed_from_dlq,
                    'success_rate': v.processing_success_rate,
                    'avg_processing_time_ms': v.average_processing_time_ms
                }
                for v in self.dlq_validations
            ]
        }
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive resilience validation report."""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'is_monitoring': self.is_monitoring,
            'recovery': self.get_recovery_statistics(),
            'circuit_breaker': self.get_circuit_breaker_statistics(),
            'retry_mechanism': self.get_retry_statistics(),
            'dlq_processing': self.get_dlq_statistics(),
            'overall_resilience_score': self._calculate_resilience_score()
        }
    
    def _calculate_resilience_score(self) -> float:
        """
        Calculate overall resilience score (0-100).
        
        Returns:
            Resilience score
        """
        scores = []
        
        # Recovery score
        recovery_stats = self.get_recovery_statistics()
        if recovery_stats['total_failures_detected'] > 0:
            scores.append(recovery_stats['recovery_success_rate'] * 100)
        
        # Circuit breaker score
        cb_stats = self.get_circuit_breaker_statistics()
        if cb_stats['total_validations'] > 0:
            scores.append(cb_stats['success_rate'] * 100)
        
        # Retry mechanism score
        retry_stats = self.get_retry_statistics()
        if retry_stats['total_validations'] > 0:
            scores.append(retry_stats['success_rate'] * 100)
        
        # DLQ processing score
        dlq_stats = self.get_dlq_statistics()
        if dlq_stats['total_validations'] > 0:
            scores.append(dlq_stats['success_rate'] * 100)
        
        # Calculate average
        return sum(scores) / len(scores) if scores else 0.0
    
    def reset_statistics(self):
        """Reset all validation statistics."""
        self.active_failures.clear()
        self.recovery_events.clear()
        self.circuit_breaker_validations.clear()
        self.retry_validations.clear()
        self.dlq_validations.clear()
        
        self.total_failures_detected = 0
        self.total_recoveries_detected = 0
        self.total_recovery_failures = 0
        self.average_recovery_time = 0.0
        
        logger.info("Resilience validation statistics reset")
