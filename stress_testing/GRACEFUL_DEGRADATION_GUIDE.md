# Graceful Degradation Manager - Quick Reference Guide

## Overview
The Graceful Degradation Manager monitors system health and automatically applies mitigation strategies when degradation is detected.

## Quick Start

### 1. Basic Detection
```python
from stress_testing.graceful_degradation import GracefulDegradationManager
from stress_testing.models import SystemMetrics

# Create manager
manager = GracefulDegradationManager()

# Check current metrics
level = manager.detect_degradation_level(system_metrics)

if manager.is_degraded():
    print(f"System degraded to: {level.value}")
```

### 2. Continuous Monitoring
```python
# Define metrics provider
def get_metrics():
    return current_system_metrics

# Start monitoring
await manager.start_monitoring(get_metrics)

# Monitoring runs in background...
# Strategies are applied automatically

# Stop when done
await manager.stop_monitoring()
```

### 3. Custom Strategies
```python
def handle_moderate_degradation(event):
    """Custom handler for moderate degradation."""
    print(f"Degradation detected: {event.trigger_reason}")
    # Your custom mitigation logic here
    disable_non_critical_features()
    increase_cache_ttl()

# Register strategy
manager.register_strategy(
    DegradationLevel.MODERATE,
    handle_moderate_degradation
)
```

## Degradation Levels

### NONE (Healthy)
- Error rate < 1%
- P99 latency < 5s
- CPU < 80%
- Memory < 85%

### MODERATE
- Error rate 1-5%
- P99 latency 5-10s
- CPU 80-90%
- Memory 85-92%

**Built-in Strategy:**
- Reduce non-critical operations
- Increase monitoring frequency
- Prepare for escalation

### SEVERE
- Error rate 5-10%
- P99 latency 10-20s
- CPU 90-95%
- Memory 92-97%

**Built-in Strategy:**
- Enable fast-path processing
- Reduce timeout values
- Activate circuit breakers
- Shed low-priority load

### CRITICAL
- Error rate > 10%
- P99 latency > 20s
- CPU > 95%
- Memory > 97%

**Built-in Strategy:**
- Emergency mode
- Aggressive load shedding
- Minimal processing only
- Alert operations team

## Custom Thresholds

```python
from stress_testing.graceful_degradation import DegradationThresholds

# Define custom thresholds
custom = DegradationThresholds(
    moderate_error_rate=0.02,      # 2% instead of 1%
    severe_error_rate=0.08,        # 8% instead of 5%
    critical_error_rate=0.15,      # 15% instead of 10%
    moderate_p99_latency=8000,     # 8s instead of 5s
    severe_p99_latency=15000,      # 15s instead of 10s
    critical_p99_latency=30000     # 30s instead of 20s
)

# Create manager with custom thresholds
manager = GracefulDegradationManager(thresholds=custom)
```

## Statistics and Monitoring

```python
# Get current statistics
stats = manager.get_statistics()

print(f"Current level: {stats['current_level']}")
print(f"Is degraded: {stats['is_degraded']}")
print(f"Total events: {stats['total_degradation_events']}")
print(f"Recoveries: {stats['total_recovery_events']}")
print(f"Avg recovery time: {stats['average_recovery_time_seconds']:.1f}s")
print(f"Events by level: {stats['events_by_level']}")

# Get event history
history = manager.get_degradation_history()
for event in history:
    print(f"{event.timestamp}: {event.level.value} - {event.trigger_reason}")
    if event.recovery_time:
        print(f"  Recovered in {event.recovery_time:.1f}s")
```

## Integration Examples

### With Metrics Collector
```python
from stress_testing.metrics.metrics_collector import MetricsCollector

collector = MetricsCollector()
manager = GracefulDegradationManager()

# Use collector as metrics provider
await manager.start_monitoring(
    metrics_provider=collector.get_current_metrics,
    agent_metrics_provider=collector.get_agent_metrics
)
```

### With Stress Test Orchestrator
```python
class StressTestOrchestrator:
    def __init__(self):
        self.degradation_manager = GracefulDegradationManager()
        
        # Register custom strategies
        self.degradation_manager.register_strategy(
            DegradationLevel.SEVERE,
            self.handle_severe_degradation
        )
    
    async def run_test(self):
        # Start degradation monitoring
        await self.degradation_manager.start_monitoring(
            metrics_provider=self.get_current_metrics
        )
        
        # Run test...
        
        # Stop monitoring
        await self.degradation_manager.stop_monitoring()
        
        # Include degradation stats in report
        stats = self.degradation_manager.get_statistics()
        self.report['degradation_events'] = stats['total_degradation_events']
```

### With Dashboard API
```python
from flask import Flask, jsonify

app = Flask(__name__)
manager = GracefulDegradationManager()

@app.route('/api/health/degradation')
def get_degradation_status():
    return jsonify({
        'level': manager.get_current_level().value,
        'is_degraded': manager.is_degraded(),
        'statistics': manager.get_statistics()
    })

@app.route('/api/health/degradation/history')
def get_degradation_history():
    history = manager.get_degradation_history()
    return jsonify([
        {
            'timestamp': e.timestamp.isoformat(),
            'level': e.level.value,
            'previous_level': e.previous_level.value,
            'reason': e.trigger_reason,
            'recovery_time': e.recovery_time
        }
        for e in history[-20:]  # Last 20 events
    ])
```

## Advanced Usage

### Async Strategy Callbacks
```python
async def async_strategy(event):
    """Async strategy handler."""
    await notify_operations_team(event)
    await scale_up_resources()
    await enable_circuit_breakers()

manager.register_strategy(DegradationLevel.CRITICAL, async_strategy)
```

### Multiple Strategies per Level
```python
# Register multiple strategies for same level
manager.register_strategy(DegradationLevel.MODERATE, log_degradation)
manager.register_strategy(DegradationLevel.MODERATE, send_alert)
manager.register_strategy(DegradationLevel.MODERATE, adjust_rate_limits)

# All will be called when level is reached
```

### Custom Check Interval
```python
# Check every 2 seconds instead of default 5
manager = GracefulDegradationManager(check_interval_seconds=2.0)
```

### Reset Statistics
```python
# Reset all statistics and history
manager.reset_statistics()
```

## Best Practices

### 1. Tune Thresholds for Your Environment
```python
# Development: More lenient
dev_thresholds = DegradationThresholds(
    moderate_error_rate=0.05,
    severe_error_rate=0.10
)

# Production: Stricter
prod_thresholds = DegradationThresholds(
    moderate_error_rate=0.01,
    severe_error_rate=0.03
)
```

### 2. Register Strategies Early
```python
# Register all strategies before starting monitoring
manager.register_strategy(DegradationLevel.MODERATE, moderate_handler)
manager.register_strategy(DegradationLevel.SEVERE, severe_handler)
manager.register_strategy(DegradationLevel.CRITICAL, critical_handler)

await manager.start_monitoring(metrics_provider)
```

### 3. Monitor Recovery Times
```python
# Track recovery times to identify issues
stats = manager.get_statistics()
avg_recovery = stats['average_recovery_time_seconds']

if avg_recovery > 300:  # 5 minutes
    print("WARNING: Slow recovery times detected")
    investigate_root_cause()
```

### 4. Include in Test Reports
```python
# Always include degradation stats in test reports
test_results['degradation'] = {
    'events': manager.get_statistics(),
    'history': [
        {
            'time': e.timestamp.isoformat(),
            'level': e.level.value,
            'reason': e.trigger_reason
        }
        for e in manager.get_degradation_history()
    ]
}
```

### 5. Use with Circuit Breakers
```python
def severe_strategy(event):
    """Activate circuit breakers on severe degradation."""
    if 'High error rate' in event.trigger_reason:
        circuit_breaker.open()
    if 'High latency' in event.trigger_reason:
        reduce_timeout_values()

manager.register_strategy(DegradationLevel.SEVERE, severe_strategy)
```

## Troubleshooting

### Issue: False Positives
**Solution:** Adjust thresholds or increase check interval
```python
# More lenient thresholds
custom = DegradationThresholds(moderate_error_rate=0.02)

# Less frequent checks
manager = GracefulDegradationManager(check_interval_seconds=10.0)
```

### Issue: Missed Degradation
**Solution:** Lower thresholds or decrease check interval
```python
# Stricter thresholds
custom = DegradationThresholds(moderate_error_rate=0.005)

# More frequent checks
manager = GracefulDegradationManager(check_interval_seconds=1.0)
```

### Issue: Strategy Not Called
**Solution:** Verify registration and level detection
```python
# Add logging to verify
def debug_strategy(event):
    print(f"Strategy called: {event.level.value}")
    print(f"Reason: {event.trigger_reason}")

manager.register_strategy(DegradationLevel.MODERATE, debug_strategy)

# Check if level is actually detected
level = manager.detect_degradation_level(metrics)
print(f"Detected level: {level.value}")
```

## Running the Demo

```bash
# Run the comprehensive demo
python stress_testing/demo_graceful_degradation.py

# Output shows:
# - Basic detection of all levels
# - Continuous monitoring with recovery
# - Custom thresholds
# - History tracking
```

## Testing

```bash
# Run tests (requires pytest-asyncio)
pip install pytest pytest-asyncio
pytest stress_testing/test_graceful_degradation.py -v

# Run specific test
pytest stress_testing/test_graceful_degradation.py::test_detect_moderate_degradation -v
```

## API Reference

### GracefulDegradationManager

**Constructor:**
```python
GracefulDegradationManager(
    thresholds: Optional[DegradationThresholds] = None,
    check_interval_seconds: float = 5.0
)
```

**Methods:**
- `detect_degradation_level(system_metrics, agent_metrics=None) -> DegradationLevel`
- `register_strategy(level, callback)`
- `async start_monitoring(metrics_provider, agent_metrics_provider=None)`
- `async stop_monitoring()`
- `get_current_level() -> DegradationLevel`
- `is_degraded() -> bool`
- `get_degradation_history() -> List[DegradationEvent]`
- `get_statistics() -> Dict[str, Any]`
- `reset_statistics()`

### DegradationThresholds

**Attributes:**
- `moderate_error_rate: float = 0.01`
- `severe_error_rate: float = 0.05`
- `critical_error_rate: float = 0.10`
- `moderate_p99_latency: float = 5000`
- `severe_p99_latency: float = 10000`
- `critical_p99_latency: float = 20000`
- `moderate_cpu: float = 0.80`
- `severe_cpu: float = 0.90`
- `critical_cpu: float = 0.95`
- `moderate_memory: float = 0.85`
- `severe_memory: float = 0.92`
- `critical_memory: float = 0.97`

### DegradationEvent

**Attributes:**
- `timestamp: datetime`
- `level: DegradationLevel`
- `previous_level: DegradationLevel`
- `trigger_reason: str`
- `metrics_snapshot: Dict[str, Any]`
- `strategy_applied: Optional[str]`
- `recovery_time: Optional[float]`

## Support

For issues or questions:
1. Check the demo: `python stress_testing/demo_graceful_degradation.py`
2. Review tests: `stress_testing/test_graceful_degradation.py`
3. Read completion summary: `stress_testing/TASK_5_2_COMPLETION_SUMMARY.md`
