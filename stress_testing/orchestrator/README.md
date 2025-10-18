# Stress Test Orchestrator

The core orchestration module for the stress testing framework, providing comprehensive test execution management, metrics aggregation, and results storage.

## Components

### StressTestOrchestrator

Central coordinator for stress testing operations.

**Key Features:**
- Scenario loading and validation
- Test execution state machine (start, pause, resume, stop, complete)
- Lifecycle callback system
- Component dependency injection
- Real-time status tracking

**Usage:**
```python
from stress_testing.orchestrator import StressTestOrchestrator
from stress_testing.config import ScenarioBuilder

# Create orchestrator
orchestrator = StressTestOrchestrator()

# Load scenario
scenario = ScenarioBuilder.create_peak_load_scenario()
orchestrator.load_scenario(scenario)

# Start test
await orchestrator.start_test()

# Get status
status = orchestrator.get_current_status()

# Complete test
await orchestrator.complete_test(success=True)
```

### MetricsAggregator

Collects and aggregates metrics from multiple sources with real-time streaming.

**Key Features:**
- Circular buffering for time-series data
- Multiple metric source registration
- Real-time subscriber notifications
- Aggregation calculations (averages, percentiles, rates)
- Window-based metric analysis

**Usage:**
```python
from stress_testing.orchestrator import MetricsAggregator

# Create aggregator
aggregator = MetricsAggregator(buffer_size=1000, aggregation_interval_seconds=1.0)

# Register metric source
async def my_metric_source():
    return {'system': system_metrics, 'agents': agent_metrics}

aggregator.register_metric_source("my_source", my_metric_source)

# Subscribe to updates
async def my_subscriber(metrics):
    print(f"Current TPS: {metrics.current_tps}")

aggregator.subscribe(my_subscriber)

# Start collection
await aggregator.start_collection()

# Get aggregated metrics
aggregated = aggregator.calculate_aggregated_metrics(window_seconds=60)

# Stop collection
await aggregator.stop_collection()
```

### TestResultsStore

Persists and manages stress test results with comprehensive reporting.

**Key Features:**
- JSON-based result storage
- Multiple report formats (JSON, Markdown, HTML)
- Test run comparison
- Trend analysis
- Automated recommendations

**Usage:**
```python
from stress_testing.orchestrator import TestResultsStore

# Create store
store = TestResultsStore()

# Save results
results_path = store.save_test_results(test_results)

# Load results
results = store.load_test_results(test_id)

# Generate reports
json_report = store.generate_report(results, format='json')
markdown_report = store.generate_report(results, format='markdown')
html_report = store.generate_report(results, format='html')

# Compare test runs
comparison = store.compare_test_runs([test_id1, test_id2, test_id3])

# List all results
all_results = store.list_test_results(limit=10)
```

## State Machine

The orchestrator implements a robust state machine for test execution:

```
IDLE → VALIDATING → INITIALIZING → RUNNING ⇄ PAUSED → STOPPING → COMPLETED
                                      ↓
                                   FAILED
```

**States:**
- `IDLE`: No test running, ready to start
- `VALIDATING`: Validating scenario and configuration
- `INITIALIZING`: Setting up test components
- `RUNNING`: Test actively executing
- `PAUSED`: Test temporarily paused
- `STOPPING`: Test being stopped
- `COMPLETED`: Test finished successfully
- `FAILED`: Test failed

## Lifecycle Callbacks

Register callbacks for test lifecycle events:

```python
async def on_start(test_id, scenario):
    print(f"Test {test_id} started")

async def on_complete(test_id, success, results):
    print(f"Test {test_id} completed: {success}")

orchestrator.register_lifecycle_callback('on_start', on_start)
orchestrator.register_lifecycle_callback('on_complete', on_complete)
```

**Available Events:**
- `on_start`: Test execution started
- `on_pause`: Test paused
- `on_resume`: Test resumed
- `on_stop`: Test stopped
- `on_complete`: Test completed
- `on_error`: Error occurred

## Metrics Aggregation

The metrics aggregator supports various aggregation calculations:

### Averages
```python
aggregated = aggregator.calculate_aggregated_metrics(window_seconds=60)
avg_throughput = aggregated['throughput']['avg']
avg_response_time = aggregated['response_time']['avg']
```

### Percentiles
```python
# Percentiles are calculated from buffered response times
p95 = aggregated['response_time']['p95_avg']
p99 = aggregated['response_time']['p99_avg']
```

### Rates
```python
# Calculate rate of change
request_rate = aggregator.calculate_rate('requests', window_seconds=60)
```

### Historical Data
```python
# Get recent metrics
recent_system = aggregator.get_metrics_history('system', count=100)
recent_business = aggregator.get_metrics_history('business', count=100)
agent_history = aggregator.get_agent_metrics_history('agent_1', count=100)
```

## Report Formats

### JSON Report
Structured data for programmatic access:
```json
{
  "test_id": "test_20250118_123456_peak_load",
  "summary": {...},
  "metrics": {...},
  "success_criteria": {...},
  "issues": [...],
  "recommendations": [...]
}
```

### Markdown Report
Human-readable format with sections:
- Summary
- Metrics Summary (System, Business)
- Success Criteria
- Issues Detected
- Recommendations

### HTML Report
Professional web-viewable format with:
- Styled tables
- Color-coded indicators
- Responsive design

## Example

See `example_usage.py` for a complete working example demonstrating:
1. Component initialization and setup
2. Scenario loading and validation
3. Test execution lifecycle
4. Metrics collection and aggregation
5. Results storage and reporting

Run the example:
```bash
python -m stress_testing.orchestrator.example_usage
```

## Integration

The orchestrator integrates with other stress testing components:

```python
# Set up complete system
orchestrator = StressTestOrchestrator()
metrics_aggregator = MetricsAggregator()
results_store = TestResultsStore()

# Inject dependencies (when available)
orchestrator.set_components(
    load_generator=load_generator,
    metrics_aggregator=metrics_aggregator,
    dashboard_controller=dashboard_controller,
    failure_injector=failure_injector
)
```

## Directory Structure

```
stress_testing/orchestrator/
├── __init__.py                      # Module exports
├── stress_test_orchestrator.py     # Core orchestrator
├── metrics_aggregator.py           # Metrics aggregation
├── test_results_store.py           # Results storage
├── example_usage.py                # Usage example
└── README.md                        # This file
```

## Requirements

- Python 3.11+
- asyncio for async operations
- Standard library only (no external dependencies for core functionality)

## Next Steps

After implementing the orchestrator core, the next components to build are:

1. **Load Generator** (Task 3): Transaction generation and rate control
2. **Metrics Collector** (Task 4): AWS and agent metrics collection
3. **Failure Injector** (Task 5): Resilience testing
4. **Dashboard Integration** (Tasks 6-10): Real-time visualization

## Support

For questions or issues, refer to:
- Main stress testing README: `stress_testing/README.md`
- Design document: `.kiro/specs/stress-testing-framework/design.md`
- Task completion summary: `stress_testing/TASK_2_COMPLETION_SUMMARY.md`
