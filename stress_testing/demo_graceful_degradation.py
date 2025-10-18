"""
Demo script for Graceful Degradation Manager.

This script demonstrates the graceful degradation monitoring capabilities.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from stress_testing.graceful_degradation import (
    GracefulDegradationManager,
    DegradationThresholds,
    DegradationEvent
)
from stress_testing.models import SystemMetrics, DegradationLevel


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_metrics(
    error_rate: float,
    p99_latency: float,
    cpu: float,
    memory: float,
    timeout_rate: float = 0.001
) -> SystemMetrics:
    """Create system metrics with specified values."""
    return SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=1000.0,
        requests_total=10000,
        requests_successful=int(10000 * (1 - error_rate)),
        requests_failed=int(10000 * error_rate),
        avg_response_time_ms=p99_latency * 0.3,
        p50_response_time_ms=p99_latency * 0.2,
        p95_response_time_ms=p99_latency * 0.8,
        p99_response_time_ms=p99_latency,
        max_response_time_ms=p99_latency * 1.5,
        error_rate=error_rate,
        timeout_rate=timeout_rate,
        cpu_utilization=cpu,
        memory_utilization=memory,
        network_throughput_mbps=100.0
    )


async def demo_basic_detection():
    """Demonstrate basic degradation detection."""
    logger.info("=" * 60)
    logger.info("Demo 1: Basic Degradation Detection")
    logger.info("=" * 60)
    
    manager = GracefulDegradationManager()
    
    # Test healthy system
    logger.info("\n1. Testing healthy system...")
    healthy = create_metrics(
        error_rate=0.001,
        p99_latency=500.0,
        cpu=0.50,
        memory=0.60
    )
    level = manager.detect_degradation_level(healthy)
    logger.info(f"   Detected level: {level.value}")
    
    # Test moderate degradation
    logger.info("\n2. Testing moderate degradation...")
    moderate = create_metrics(
        error_rate=0.015,  # 1.5%
        p99_latency=5500.0,
        cpu=0.85,
        memory=0.87
    )
    level = manager.detect_degradation_level(moderate)
    logger.info(f"   Detected level: {level.value}")
    
    # Test severe degradation
    logger.info("\n3. Testing severe degradation...")
    severe = create_metrics(
        error_rate=0.06,  # 6%
        p99_latency=12000.0,
        cpu=0.92,
        memory=0.94
    )
    level = manager.detect_degradation_level(severe)
    logger.info(f"   Detected level: {level.value}")
    
    # Test critical degradation
    logger.info("\n4. Testing critical degradation...")
    critical = create_metrics(
        error_rate=0.12,  # 12%
        p99_latency=25000.0,
        cpu=0.97,
        memory=0.98
    )
    level = manager.detect_degradation_level(critical)
    logger.info(f"   Detected level: {level.value}")


async def demo_monitoring_with_recovery():
    """Demonstrate continuous monitoring with degradation and recovery."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 2: Continuous Monitoring with Recovery")
    logger.info("=" * 60)
    
    manager = GracefulDegradationManager(check_interval_seconds=1.0)
    
    # Simulate changing metrics
    current_metrics = [create_metrics(0.001, 500.0, 0.50, 0.60)]
    
    def metrics_provider():
        return current_metrics[0]
    
    # Register strategy callbacks
    def on_moderate(event: DegradationEvent):
        logger.warning(f"   >>> MODERATE strategy triggered: {event.trigger_reason}")
    
    def on_severe(event: DegradationEvent):
        logger.error(f"   >>> SEVERE strategy triggered: {event.trigger_reason}")
    
    def on_critical(event: DegradationEvent):
        logger.critical(f"   >>> CRITICAL strategy triggered: {event.trigger_reason}")
    
    manager.register_strategy(DegradationLevel.MODERATE, on_moderate)
    manager.register_strategy(DegradationLevel.SEVERE, on_severe)
    manager.register_strategy(DegradationLevel.CRITICAL, on_critical)
    
    # Start monitoring
    logger.info("\nStarting monitoring...")
    await manager.start_monitoring(metrics_provider)
    
    # Scenario: Healthy -> Moderate -> Severe -> Recovery
    logger.info("\n1. System starts healthy...")
    await asyncio.sleep(2)
    
    logger.info("\n2. System degrades to MODERATE...")
    current_metrics[0] = create_metrics(0.015, 5500.0, 0.85, 0.87)
    await asyncio.sleep(3)
    
    logger.info("\n3. System degrades to SEVERE...")
    current_metrics[0] = create_metrics(0.06, 12000.0, 0.92, 0.94)
    await asyncio.sleep(3)
    
    logger.info("\n4. System recovers to healthy...")
    current_metrics[0] = create_metrics(0.001, 500.0, 0.50, 0.60)
    await asyncio.sleep(3)
    
    # Stop monitoring
    await manager.stop_monitoring()
    
    # Show statistics
    logger.info("\n" + "-" * 60)
    logger.info("Final Statistics:")
    stats = manager.get_statistics()
    logger.info(f"  Total degradation events: {stats['total_degradation_events']}")
    logger.info(f"  Total recovery events: {stats['total_recovery_events']}")
    logger.info(f"  Average recovery time: {stats['average_recovery_time_seconds']:.1f}s")
    logger.info(f"  Events by level: {stats['events_by_level']}")


async def demo_custom_thresholds():
    """Demonstrate custom degradation thresholds."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 3: Custom Thresholds")
    logger.info("=" * 60)
    
    # Create custom thresholds (more lenient)
    custom_thresholds = DegradationThresholds(
        moderate_error_rate=0.05,   # 5% instead of 1%
        severe_error_rate=0.10,     # 10% instead of 5%
        critical_error_rate=0.20,   # 20% instead of 10%
        moderate_p99_latency=10000,
        severe_p99_latency=20000,
        critical_p99_latency=40000
    )
    
    manager = GracefulDegradationManager(thresholds=custom_thresholds)
    
    # Test with metrics that would be severe with default thresholds
    logger.info("\nTesting with 6% error rate and 12s P99 latency...")
    logger.info("(Would be SEVERE with default thresholds)")
    
    metrics = create_metrics(
        error_rate=0.06,
        p99_latency=12000.0,
        cpu=0.70,
        memory=0.75
    )
    
    level = manager.detect_degradation_level(metrics)
    logger.info(f"With custom thresholds: {level.value}")


async def demo_degradation_history():
    """Demonstrate degradation history tracking."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 4: Degradation History Tracking")
    logger.info("=" * 60)
    
    manager = GracefulDegradationManager(check_interval_seconds=0.5)
    
    current_metrics = [create_metrics(0.001, 500.0, 0.50, 0.60)]
    
    def metrics_provider():
        return current_metrics[0]
    
    await manager.start_monitoring(metrics_provider)
    
    # Create multiple degradation events
    logger.info("\nSimulating multiple degradation events...")
    
    await asyncio.sleep(1)
    logger.info("  Event 1: Moderate degradation")
    current_metrics[0] = create_metrics(0.015, 5500.0, 0.85, 0.87)
    await asyncio.sleep(2)
    
    logger.info("  Event 2: Recovery")
    current_metrics[0] = create_metrics(0.001, 500.0, 0.50, 0.60)
    await asyncio.sleep(2)
    
    logger.info("  Event 3: Severe degradation")
    current_metrics[0] = create_metrics(0.06, 12000.0, 0.92, 0.94)
    await asyncio.sleep(2)
    
    logger.info("  Event 4: Recovery")
    current_metrics[0] = create_metrics(0.001, 500.0, 0.50, 0.60)
    await asyncio.sleep(2)
    
    await manager.stop_monitoring()
    
    # Show history
    logger.info("\n" + "-" * 60)
    logger.info("Degradation History:")
    history = manager.get_degradation_history()
    for i, event in enumerate(history, 1):
        logger.info(f"\n  Event {i}:")
        logger.info(f"    Time: {event.timestamp.strftime('%H:%M:%S')}")
        logger.info(f"    Level: {event.previous_level.value} -> {event.level.value}")
        logger.info(f"    Reason: {event.trigger_reason}")
        if event.recovery_time:
            logger.info(f"    Recovery time: {event.recovery_time:.1f}s")


async def main():
    """Run all demos."""
    logger.info("\n" + "=" * 60)
    logger.info("GRACEFUL DEGRADATION MANAGER DEMO")
    logger.info("=" * 60)
    
    try:
        await demo_basic_detection()
        await demo_monitoring_with_recovery()
        await demo_custom_thresholds()
        await demo_degradation_history()
        
        logger.info("\n" + "=" * 60)
        logger.info("All demos completed successfully!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"\nError during demo: {e}", exc_info=True)


if __name__ == '__main__':
    asyncio.run(main())
