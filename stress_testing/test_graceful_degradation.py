"""
Tests for Graceful Degradation Manager.
"""

import asyncio
import pytest
from datetime import datetime

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from src.graceful_degradation import (
    GracefulDegradationManager,
    DegradationThresholds,
    DegradationEvent
)
from src.models import (
    SystemMetrics,
    AgentMetrics,
    DegradationLevel
)


@pytest.fixture
def manager():
    """Create a degradation manager for testing."""
    return GracefulDegradationManager(check_interval_seconds=0.1)


@pytest.fixture
def healthy_metrics():
    """Create healthy system metrics."""
    return SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=1000.0,
        requests_total=10000,
        requests_successful=9990,
        requests_failed=10,
        avg_response_time_ms=100.0,
        p50_response_time_ms=80.0,
        p95_response_time_ms=200.0,
        p99_response_time_ms=500.0,
        max_response_time_ms=1000.0,
        error_rate=0.001,
        timeout_rate=0.0005,
        cpu_utilization=0.50,
        memory_utilization=0.60,
        network_throughput_mbps=100.0
    )


@pytest.fixture
def moderate_degraded_metrics():
    """Create moderately degraded system metrics."""
    return SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=800.0,
        requests_total=10000,
        requests_successful=9900,
        requests_failed=100,
        avg_response_time_ms=500.0,
        p50_response_time_ms=400.0,
        p95_response_time_ms=2000.0,
        p99_response_time_ms=5500.0,
        max_response_time_ms=8000.0,
        error_rate=0.015,  # 1.5% - above moderate threshold
        timeout_rate=0.01,
        cpu_utilization=0.85,  # Above moderate threshold
        memory_utilization=0.87,  # Above moderate threshold
        network_throughput_mbps=150.0
    )


@pytest.fixture
def severe_degraded_metrics():
    """Create severely degraded system metrics."""
    return SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=500.0,
        requests_total=10000,
        requests_successful=9500,
        requests_failed=500,
        avg_response_time_ms=2000.0,
        p50_response_time_ms=1500.0,
        p95_response_time_ms=8000.0,
        p99_response_time_ms=12000.0,
        max_response_time_ms=20000.0,
        error_rate=0.06,  # 6% - above severe threshold
        timeout_rate=0.04,
        cpu_utilization=0.92,  # Above severe threshold
        memory_utilization=0.94,  # Above severe threshold
        network_throughput_mbps=200.0
    )


@pytest.fixture
def critical_degraded_metrics():
    """Create critically degraded system metrics."""
    return SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=200.0,
        requests_total=10000,
        requests_successful=9000,
        requests_failed=1000,
        avg_response_time_ms=5000.0,
        p50_response_time_ms=4000.0,
        p95_response_time_ms=15000.0,
        p99_response_time_ms=25000.0,
        max_response_time_ms=40000.0,
        error_rate=0.12,  # 12% - above critical threshold
        timeout_rate=0.08,
        cpu_utilization=0.97,  # Above critical threshold
        memory_utilization=0.98,  # Above critical threshold
        network_throughput_mbps=250.0
    )


def test_initialization(manager):
    """Test manager initialization."""
    assert manager.current_level == DegradationLevel.NONE
    assert not manager.is_monitoring
    assert len(manager.degradation_history) == 0


def test_detect_healthy_system(manager, healthy_metrics):
    """Test detection of healthy system."""
    level = manager.detect_degradation_level(healthy_metrics)
    assert level == DegradationLevel.NONE


def test_detect_moderate_degradation(manager, moderate_degraded_metrics):
    """Test detection of moderate degradation."""
    level = manager.detect_degradation_level(moderate_degraded_metrics)
    assert level == DegradationLevel.MODERATE


def test_detect_severe_degradation(manager, severe_degraded_metrics):
    """Test detection of severe degradation."""
    level = manager.detect_degradation_level(severe_degraded_metrics)
    assert level == DegradationLevel.SEVERE


def test_detect_critical_degradation(manager, critical_degraded_metrics):
    """Test detection of critical degradation."""
    level = manager.detect_degradation_level(critical_degraded_metrics)
    assert level == DegradationLevel.CRITICAL


def test_detect_with_agent_metrics(manager, healthy_metrics):
    """Test degradation detection with agent metrics."""
    # Healthy agents
    agent_metrics = {
        'agent1': AgentMetrics(
            agent_id='agent1',
            agent_name='Agent 1',
            timestamp=datetime.utcnow(),
            requests_processed=1000,
            avg_response_time_ms=100.0,
            p95_response_time_ms=200.0,
            p99_response_time_ms=300.0,
            success_rate=0.99,
            error_count=10,
            timeout_count=5,
            current_load=0.5,
            concurrent_requests=50,
            health_score=0.95
        ),
        'agent2': AgentMetrics(
            agent_id='agent2',
            agent_name='Agent 2',
            timestamp=datetime.utcnow(),
            requests_processed=1000,
            avg_response_time_ms=110.0,
            p95_response_time_ms=210.0,
            p99_response_time_ms=310.0,
            success_rate=0.98,
            error_count=20,
            timeout_count=8,
            current_load=0.6,
            concurrent_requests=60,
            health_score=0.90
        )
    }
    
    level = manager.detect_degradation_level(healthy_metrics, agent_metrics)
    assert level == DegradationLevel.NONE
    
    # Unhealthy agents - need to be below severe threshold (0.60)
    agent_metrics['agent1'].health_score = 0.50
    agent_metrics['agent2'].health_score = 0.50
    
    level = manager.detect_degradation_level(healthy_metrics, agent_metrics)
    # With avg health of 0.50, should trigger severe degradation
    assert level in [DegradationLevel.MODERATE, DegradationLevel.SEVERE]


def test_custom_thresholds():
    """Test custom degradation thresholds."""
    custom_thresholds = DegradationThresholds(
        moderate_error_rate=0.02,
        severe_error_rate=0.08,
        critical_error_rate=0.15
    )
    
    manager = GracefulDegradationManager(thresholds=custom_thresholds)
    
    metrics = SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=1000.0,
        requests_total=10000,
        requests_successful=9700,
        requests_failed=300,
        avg_response_time_ms=100.0,
        p50_response_time_ms=80.0,
        p95_response_time_ms=200.0,
        p99_response_time_ms=500.0,
        max_response_time_ms=1000.0,
        error_rate=0.03,  # Between moderate and severe
        timeout_rate=0.001,
        cpu_utilization=0.50,
        memory_utilization=0.60,
        network_throughput_mbps=100.0
    )
    
    level = manager.detect_degradation_level(metrics)
    assert level == DegradationLevel.MODERATE


def test_strategy_registration(manager):
    """Test strategy callback registration."""
    callback_called = []
    
    def moderate_callback(event: DegradationEvent):
        callback_called.append('moderate')
    
    def severe_callback(event: DegradationEvent):
        callback_called.append('severe')
    
    manager.register_strategy(DegradationLevel.MODERATE, moderate_callback)
    manager.register_strategy(DegradationLevel.SEVERE, severe_callback)
    
    assert len(manager.strategy_callbacks[DegradationLevel.MODERATE]) == 1
    assert len(manager.strategy_callbacks[DegradationLevel.SEVERE]) == 1


@pytest.mark.asyncio
async def test_monitoring_lifecycle(manager, healthy_metrics):
    """Test monitoring start and stop."""
    metrics_provider = lambda: healthy_metrics
    
    # Start monitoring
    await manager.start_monitoring(metrics_provider)
    assert manager.is_monitoring
    
    # Let it run briefly
    await asyncio.sleep(0.3)
    
    # Stop monitoring
    await manager.stop_monitoring()
    assert not manager.is_monitoring


@pytest.mark.asyncio
async def test_degradation_detection_during_monitoring(
    manager,
    healthy_metrics,
    moderate_degraded_metrics
):
    """Test degradation detection during monitoring."""
    current_metrics = [healthy_metrics]
    
    def metrics_provider():
        return current_metrics[0]
    
    # Start monitoring
    await manager.start_monitoring(metrics_provider)
    
    # Wait for initial check
    await asyncio.sleep(0.2)
    assert manager.current_level == DegradationLevel.NONE
    
    # Change to degraded metrics
    current_metrics[0] = moderate_degraded_metrics
    
    # Wait for detection
    await asyncio.sleep(0.3)
    assert manager.current_level == DegradationLevel.MODERATE
    assert len(manager.degradation_history) > 0
    
    # Stop monitoring
    await manager.stop_monitoring()


@pytest.mark.asyncio
async def test_recovery_detection(
    manager,
    healthy_metrics,
    moderate_degraded_metrics
):
    """Test recovery detection."""
    current_metrics = [moderate_degraded_metrics]
    
    def metrics_provider():
        return current_metrics[0]
    
    # Start monitoring with degraded metrics
    await manager.start_monitoring(metrics_provider)
    await asyncio.sleep(0.2)
    
    assert manager.current_level == DegradationLevel.MODERATE
    assert manager.degradation_start_time is not None
    
    # Recover to healthy
    current_metrics[0] = healthy_metrics
    await asyncio.sleep(0.3)
    
    assert manager.current_level == DegradationLevel.NONE
    assert manager.total_recovery_events == 1
    assert manager.degradation_start_time is None
    
    # Stop monitoring
    await manager.stop_monitoring()


def test_statistics(manager):
    """Test statistics tracking."""
    stats = manager.get_statistics()
    
    assert stats['current_level'] == DegradationLevel.NONE.value
    assert not stats['is_degraded']
    assert stats['total_degradation_events'] == 0
    assert stats['total_recovery_events'] == 0


def test_reset_statistics(manager, moderate_degraded_metrics):
    """Test statistics reset."""
    # Create some history
    manager.detect_degradation_level(moderate_degraded_metrics)
    manager.total_degradation_events = 5
    manager.total_recovery_events = 3
    
    # Reset
    manager.reset_statistics()
    
    stats = manager.get_statistics()
    assert stats['total_degradation_events'] == 0
    assert stats['total_recovery_events'] == 0
    assert len(manager.degradation_history) == 0


def test_is_degraded(manager):
    """Test is_degraded check."""
    assert not manager.is_degraded()
    
    manager.current_level = DegradationLevel.MODERATE
    assert manager.is_degraded()
    
    manager.current_level = DegradationLevel.SEVERE
    assert manager.is_degraded()
    
    manager.current_level = DegradationLevel.CRITICAL
    assert manager.is_degraded()
    
    manager.current_level = DegradationLevel.NONE
    assert not manager.is_degraded()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
