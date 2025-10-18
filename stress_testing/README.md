# Stress Testing Framework

Comprehensive stress testing framework for the AWS Bedrock AI Agent Fraud Detection System.

## Overview

This framework provides:
- High-volume load generation (up to 10,000+ TPS)
- Multi-agent coordination testing
- AWS infrastructure validation
- Real-time metrics collection and visualization
- Investor-grade presentation dashboards
- Failure injection and resilience testing

## Directory Structure

```
stress_testing/
├── __init__.py                 # Package initialization
├── models.py                   # Core data models and enums
├── config.py                   # Configuration management
├── orchestrator/               # Test orchestration
│   └── __init__.py
├── load_generator/             # Load generation
│   └── __init__.py
├── metrics/                    # Metrics collection
│   └── __init__.py
└── dashboards/                 # Visualization dashboards
    └── __init__.py
```

## Core Data Models

### Enums

- **TestStatus**: Test execution states (NOT_STARTED, RUNNING, COMPLETED, etc.)
- **LoadProfileType**: Load patterns (RAMP_UP, SUSTAINED, BURST, WAVE, CHAOS)
- **FailureType**: Failure injection types (LAMBDA_CRASH, DYNAMODB_THROTTLE, etc.)
- **DegradationLevel**: System degradation levels (NONE, MODERATE, SEVERE, CRITICAL)

### Configuration Models

- **StressTestConfig**: Main test configuration
- **LoadProfile**: Load generation pattern definition
- **TestScenario**: Complete test scenario with success criteria
- **FailureScenario**: Failure injection configuration

### Metrics Models

- **SystemMetrics**: System-level performance metrics
- **AgentMetrics**: Agent-specific metrics
- **BusinessMetrics**: Business value metrics
- **HeroMetrics**: Large-format presentation metrics

### Presentation Models

- **TransactionFlowNode**: Transaction flow visualization
- **CompetitiveBenchmarks**: Competitive comparison data
- **CostEfficiencyMetrics**: Cost tracking and optimization
- **ResilienceMetrics**: Resilience and recovery metrics
- **PresentationData**: Complete investor presentation data

## Quick Start

### Creating a Test Configuration

```python
from stress_testing.config import ConfigurationManager

# Create configuration manager
config_mgr = ConfigurationManager()

# Create default configuration
config = config_mgr.create_default_config(
    test_name="My Stress Test",
    target_tps=5000,
    duration_seconds=600
)

# Save configuration
config_mgr.save_config(config)
```

### Using Predefined Scenarios

```python
from stress_testing.config import ScenarioBuilder

# Create peak load scenario
scenario = ScenarioBuilder.create_peak_load_scenario()

# Create sustained load scenario
scenario = ScenarioBuilder.create_sustained_load_scenario()

# Create burst traffic scenario
scenario = ScenarioBuilder.create_burst_traffic_scenario()

# Create failure recovery scenario
scenario = ScenarioBuilder.create_failure_recovery_scenario()

# Create investor presentation scenario
scenario = ScenarioBuilder.create_investor_presentation_scenario()
```

### Working with Data Models

```python
from stress_testing.models import (
    StressTestConfig,
    LoadProfile,
    LoadProfileType,
    SystemMetrics,
    AgentMetrics,
    BusinessMetrics
)
from datetime import datetime

# Create load profile
load_profile = LoadProfile(
    profile_type=LoadProfileType.RAMP_UP,
    start_tps=0,
    peak_tps=5000,
    sustained_tps=3000
)

# Create system metrics
metrics = SystemMetrics(
    timestamp=datetime.utcnow(),
    throughput_tps=4523.5,
    requests_total=1000000,
    requests_successful=999500,
    requests_failed=500,
    avg_response_time_ms=245.3,
    p50_response_time_ms=180.0,
    p95_response_time_ms=450.0,
    p99_response_time_ms=850.0,
    max_response_time_ms=1200.0,
    error_rate=0.0005,
    timeout_rate=0.0001,
    cpu_utilization=0.75,
    memory_utilization=0.68,
    network_throughput_mbps=125.5
)
```

## Configuration Options

### StressTestConfig Parameters

- **test_id**: Unique test identifier
- **test_name**: Human-readable test name
- **target_tps**: Target transactions per second
- **duration_seconds**: Test duration
- **ramp_up_seconds**: Ramp-up period
- **num_workers**: Number of load generation workers
- **enable_failure_injection**: Enable failure injection
- **enable_presentation_mode**: Enable investor presentation mode
- **test_environment**: Target environment (dev/staging/production)

### Load Profile Types

1. **RAMP_UP**: Gradual increase from start_tps to peak_tps
2. **SUSTAINED**: Constant load at sustained_tps
3. **BURST**: Periodic bursts of high traffic
4. **WAVE**: Oscillating load pattern
5. **CHAOS**: Random, unpredictable load

## Predefined Test Scenarios

### 1. Peak Load Test
- **Target**: 10,000 TPS
- **Duration**: 30 minutes
- **Purpose**: Validate maximum capacity

### 2. Sustained Load Test
- **Target**: 2,000 TPS
- **Duration**: 2 hours
- **Purpose**: Validate stability and detect memory leaks

### 3. Burst Traffic Test
- **Target**: 10,000 TPS bursts
- **Duration**: 15 minutes
- **Purpose**: Validate auto-scaling and queue handling

### 4. Failure Recovery Test
- **Target**: 3,000 TPS with failures
- **Duration**: 45 minutes
- **Purpose**: Validate resilience and recovery

### 5. Investor Presentation
- **Target**: 8,000 TPS peak
- **Duration**: 10 minutes
- **Purpose**: Impressive demo for investors

## Requirements Mapping

This implementation addresses the following requirements:

- **Requirement 1.1**: High-volume load testing (5000+ TPS)
- **Requirement 1.2**: Sustained load testing (2000 TPS for 30 minutes)
- **Requirement 1.3**: Burst traffic handling (10,000 TPS bursts)
- **Requirement 1.4**: Concurrent user simulation (500+ users)
- **Requirement 1.5**: Auto-scaling validation

## Next Steps

1. Implement stress test orchestrator (task 2)
2. Build transaction load generator (task 3)
3. Implement metrics collection system (task 4)
4. Add failure injection framework (task 5)
5. Create dashboard integrations (tasks 6-10)

## License

Part of the AWS Bedrock AI Agent Fraud Detection System.
