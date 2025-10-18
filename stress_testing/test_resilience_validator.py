"""
Tests for Resilience Validator.

This module tests the resilience validation functionality including:
- Automatic recovery detection
- Circuit breaker validation
- Retry mechanism testing
- Dead letter queue processing
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from .resilience_validator import (
    ResilienceValidator,
    RecoveryStatus,
    CircuitBreakerState
)
from .models import (
    FailureScenario,
    FailureType,
    SystemMetrics,
    LoadProfile
)


@pytest.fixture
def validator():
    """Create a resilience validator instance."""
    return ResilienceValidator(
        recovery_timeout_seconds=60.0,
        check_interval_seconds=1.0
    )


@pytest.fixture
def sample_metrics():
    """Create sample system metrics."""
    return SystemMetrics(
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


@pytest.fixture
def degraded_metrics():
    """Create degraded system metrics."""
    return SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=500.0,
        requests_total=5000,
        requests_successful=4250,
        requests_failed=750,
        avg_response_time_ms=800.0,
        p50_response_time_ms=600.0,
        p95_response_time_ms=1500.0,
        p99_response_time_ms=3000.0,
        max_response_time_ms=5000.0,
        error_rate=0.15,
        timeout_rate=0.05,
        cpu_utilization=0.95,
        memory_utilization=0.92,
        network_throughput_mbps=50.0
    )


@pytest.fixture
def failure_scenario():
    """Create a sample failure scenario."""
    return FailureScenario(
        failure_type=FailureType.LAMBDA_CRASH,
        start_time_seconds=5.0,
        duration_seconds=10.0,
        severity=0.8,
        parameters={}
    )


class TestResilienceValidator:
    """Test suite for ResilienceValidator."""
    
    def test_initialization(self, validator):
        """Test validator initialization."""
        assert validator is not None
        assert validator.recovery_timeout == 60.0
        assert validator.check_interval == 1.0
        assert not validator.is_monitoring
        assert len(validator.recovery_events) == 0
        assert validator.total_failures_detected == 0
    
    @pytest.mark.asyncio
    async def test_register_failure(self, validator, failure_scenario, sample_metrics):
        """Test failure registration."""
        await validator.register_failure(failure_scenario, sample_metrics)
        
        assert validator.total_failures_detected == 1
        assert len(validator.active_failures) == 1
        
        # Check failure info
        failure_id = list(validator.active_failures.keys())[0]
        failure_info = validator.active_failures[failure_id]
        
        assert failure_info['scenario'] == failure_scenario
        assert failure_info['recovery_status'] == RecoveryStatus.DETECTING
        assert 'metrics_before' in failure_info
    
    @pytest.mark.asyncio
    async def test_recovery_detection(self, validator, failure_scenario, degraded_metrics, sample_metrics):
        """Test automatic recovery detection."""
        # Register failure with degraded metrics
        await validator.register_failure(failure_scenario, degraded_metrics)
        
        # Simulate failure duration passing
        await asyncio.sleep(0.1)
        
        # Manually trigger recovery check with recovered metrics
        failure_id = list(validator.active_failures.keys())[0]
        validator.active_failures[failure_id]['start_time'] = (
            datetime.utcnow() - timedelta(seconds=failure_scenario.duration_seconds + 1)
        )
        
        # Check for recovery
        await validator._check_for_recovery(sample_metrics)
        
        # Verify recovery was detected
        assert len(validator.recovery_events) == 1
        assert validator.total_recoveries_detected == 1
        assert len(validator.active_failures) == 0
        
        # Check recovery event
        event = validator.recovery_events[0]
        assert event.failure_type == FailureType.LAMBDA_CRASH
        assert event.recovery_status == RecoveryStatus.RECOVERED
        assert event.recovery_time_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_validation(self, validator):
        """Test circuit breaker validation."""
        result = await validator.validate_circuit_breaker(
            service_name="test_service",
            failure_threshold=3,
            timeout_seconds=2.0
        )
        
        assert result is not None
        assert result.service_name == "test_service"
        assert result.triggered
        assert result.failure_threshold_reached
        assert result.recovery_detected
        assert result.validation_passed
        assert result.initial_state == CircuitBreakerState.CLOSED
        assert result.state_after_failure == CircuitBreakerState.CLOSED
        assert result.time_to_open_seconds is not None
        assert result.time_to_close_seconds is not None
    
    @pytest.mark.asyncio
    async def test_retry_mechanism_validation(self, validator):
        """Test retry mechanism validation."""
        result = await validator.validate_retry_mechanism(
            operation_type="database_query",
            max_retries=3,
            initial_backoff_ms=100.0
        )
        
        assert result is not None
        assert result.operation_type == "database_query"
        assert result.retry_attempts == 3
        assert result.successful_retries > 0
        assert result.exponential_backoff_detected
        assert result.max_retries_respected
        assert result.validation_passed
        assert len(result.retry_timings) > 0
    
    @pytest.mark.asyncio
    async def test_dlq_validation(self, validator):
        """Test DLQ processing validation."""
        result = await validator.validate_dlq_processing(
            queue_name="test_dlq",
            test_message_count=10
        )
        
        assert result is not None
        assert result.queue_name == "test_dlq"
        assert result.messages_sent_to_dlq == 10
        assert result.messages_processed_from_dlq > 0
        assert result.processing_success_rate >= 0.8
        assert result.average_processing_time_ms > 0
        assert result.validation_passed
    
    def test_recovery_statistics(self, validator):
        """Test recovery statistics."""
        stats = validator.get_recovery_statistics()
        
        assert 'total_failures_detected' in stats
        assert 'total_recoveries_detected' in stats
        assert 'total_recovery_failures' in stats
        assert 'recovery_success_rate' in stats
        assert 'average_recovery_time_seconds' in stats
        assert 'active_failures' in stats
        assert 'recovery_events' in stats
    
    def test_circuit_breaker_statistics(self, validator):
        """Test circuit breaker statistics."""
        stats = validator.get_circuit_breaker_statistics()
        
        assert 'total_validations' in stats
        assert 'passed_validations' in stats
        assert 'failed_validations' in stats
        assert 'success_rate' in stats
        assert 'validations' in stats
    
    def test_retry_statistics(self, validator):
        """Test retry mechanism statistics."""
        stats = validator.get_retry_statistics()
        
        assert 'total_validations' in stats
        assert 'passed_validations' in stats
        assert 'failed_validations' in stats
        assert 'success_rate' in stats
        assert 'validations' in stats
    
    def test_dlq_statistics(self, validator):
        """Test DLQ statistics."""
        stats = validator.get_dlq_statistics()
        
        assert 'total_validations' in stats
        assert 'passed_validations' in stats
        assert 'failed_validations' in stats
        assert 'success_rate' in stats
        assert 'average_processing_success_rate' in stats
        assert 'validations' in stats
    
    def test_comprehensive_report(self, validator):
        """Test comprehensive resilience report."""
        report = validator.get_comprehensive_report()
        
        assert 'timestamp' in report
        assert 'is_monitoring' in report
        assert 'recovery' in report
        assert 'circuit_breaker' in report
        assert 'retry_mechanism' in report
        assert 'dlq_processing' in report
        assert 'overall_resilience_score' in report
        
        # Score should be between 0 and 100
        assert 0 <= report['overall_resilience_score'] <= 100
    
    @pytest.mark.asyncio
    async def test_resilience_score_calculation(self, validator):
        """Test resilience score calculation."""
        # Run some validations
        await validator.validate_circuit_breaker("service1")
        await validator.validate_retry_mechanism("operation1")
        await validator.validate_dlq_processing("queue1")
        
        score = validator._calculate_resilience_score()
        
        # Score should be high since all validations should pass
        assert score >= 80.0
        assert score <= 100.0
    
    def test_reset_statistics(self, validator):
        """Test statistics reset."""
        # Add some data
        validator.total_failures_detected = 10
        validator.total_recoveries_detected = 8
        
        # Reset
        validator.reset_statistics()
        
        # Verify reset
        assert validator.total_failures_detected == 0
        assert validator.total_recoveries_detected == 0
        assert len(validator.recovery_events) == 0
        assert len(validator.circuit_breaker_validations) == 0
        assert len(validator.retry_validations) == 0
        assert len(validator.dlq_validations) == 0
    
    @pytest.mark.asyncio
    async def test_monitoring_lifecycle(self, validator, sample_metrics):
        """Test monitoring start and stop."""
        # Create metrics provider
        def metrics_provider():
            return sample_metrics
        
        # Start monitoring
        await validator.start_monitoring(metrics_provider)
        assert validator.is_monitoring
        assert validator.monitor_task is not None
        
        # Wait a bit
        await asyncio.sleep(0.5)
        
        # Stop monitoring
        await validator.stop_monitoring()
        assert not validator.is_monitoring
    
    @pytest.mark.asyncio
    async def test_recovery_timeout(self, validator, failure_scenario, degraded_metrics):
        """Test recovery timeout handling."""
        # Set short timeout
        validator.recovery_timeout = 1.0
        
        # Register failure
        await validator.register_failure(failure_scenario, degraded_metrics)
        
        # Simulate timeout by setting old start time
        failure_id = list(validator.active_failures.keys())[0]
        validator.active_failures[failure_id]['start_time'] = (
            datetime.utcnow() - timedelta(seconds=100)
        )
        
        # Check for recovery (should timeout)
        await validator._check_for_recovery(degraded_metrics)
        
        # Verify timeout was detected
        assert validator.total_recovery_failures == 1
        assert len(validator.active_failures) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
