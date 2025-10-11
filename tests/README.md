# Fraud Detection System - Test Suite

## Overview

Comprehensive test suite for the AWS Bedrock-powered fraud detection system with AI agents. Tests cover integration, performance, load testing, and AI agent validation.

## Test Structure

```
tests/
├── test_integration.py          # Integration tests for agent coordination
├── test_load_performance.py     # Load and performance testing
├── test_ai_agent_validation.py  # AI agent capabilities validation
├── run_all_tests.py            # Test runner and orchestrator
└── README.md                    # This file
```

## Test Suites

### 1. Integration Tests (`test_integration.py`)

Tests agent coordination workflows, external tool integrations, memory system persistence, and streaming pipeline end-to-end.

**Test Classes:**
- `TestAgentCoordination` - Multi-agent coordination and communication
- `TestExternalToolIntegrations` - External API integrations with mocks
- `TestMemorySystemPersistence` - Memory storage and retrieval
- `TestStreamingPipeline` - Stream processing end-to-end

**Key Tests:**
- Multi-agent coordination and decision aggregation
- Conflict resolution between agents
- Workload distribution and load balancing
- Identity verification, fraud database, and geolocation integrations
- Transaction history and user profile storage
- Stream ingestion and event-driven responses

**Run Integration Tests:**
```bash
pytest tests/test_integration.py -v --asyncio-mode=auto
```

### 2. Load & Performance Tests (`test_load_performance.py`)

Tests system under high transaction volumes (1000+ TPS), validates auto-scaling behavior, measures response times, and tests system recovery.

**Test Classes:**
- `TestHighVolumeProcessing` - High-volume transaction processing
- `TestAutoScaling` - Auto-scaling behavior validation
- `TestResponseTimeOptimization` - Response time measurement
- `TestSystemRecovery` - Failure recovery testing

**Key Tests:**
- 1000 TPS sustained load testing
- Burst traffic handling (5000 transactions in 1 second)
- Concurrent user simulation (100 users)
- Scale-up and scale-down behavior
- Response time targets (avg < 500ms, P95 < 1s, P99 < 2s)
- Caching effectiveness
- Graceful degradation and circuit breaker
- Recovery after failures

**Run Performance Tests:**
```bash
# Run all performance tests
pytest tests/test_load_performance.py -v --asyncio-mode=auto

# Skip slow tests
pytest tests/test_load_performance.py -v --asyncio-mode=auto -m "not slow"

# Run stress test only
pytest tests/test_load_performance.py::test_stress_test -v --asyncio-mode=auto
```

### 3. AI Agent Validation (`test_ai_agent_validation.py`)

Tests reasoning quality across diverse fraud scenarios, validates explanation generation, tests decision accuracy, and verifies AWS AI agent compliance.

**Test Classes:**
- `TestReasoningQuality` - Reasoning across diverse scenarios
- `TestExplanationGeneration` - Explanation completeness and quality
- `TestDecisionAccuracy` - Decision accuracy and error rates
- `TestAWSAIAgentCompliance` - AWS Bedrock agent standards

**Key Tests:**
- Legitimate transaction reasoning
- Fraudulent transaction detection
- Ambiguous transaction handling
- Velocity fraud pattern detection
- Geographic anomaly detection
- Account takeover pattern recognition
- Chain-of-thought reasoning validation
- Explanation completeness and human-readability
- Evidence linking and confidence justification
- Decision accuracy (target: 70%+)
- False positive rate (target: < 30%)
- False negative rate (target: < 20%)
- Confidence calibration
- AWS agent response format compliance
- Traceability and audit trail

**Run AI Validation Tests:**
```bash
pytest tests/test_ai_agent_validation.py -v --asyncio-mode=auto
```

## Running Tests

### Quick Start

Run all tests:
```bash
python tests/run_all_tests.py
```

Run quick smoke tests:
```bash
python tests/run_all_tests.py --quick
```

Skip slow performance tests:
```bash
python tests/run_all_tests.py --skip-slow
```

### Run Specific Test Suite

```bash
# Integration tests only
python tests/run_all_tests.py --suite integration

# Performance tests only
python tests/run_all_tests.py --suite performance

# AI validation tests only
python tests/run_all_tests.py --suite ai-validation
```

### Run Individual Tests

```bash
# Run specific test file
pytest tests/test_integration.py -v

# Run specific test class
pytest tests/test_integration.py::TestAgentCoordination -v

# Run specific test method
pytest tests/test_integration.py::TestAgentCoordination::test_multi_agent_coordination -v

# Run tests matching pattern
pytest tests/ -k "test_fraud" -v
```

### Test Options

```bash
# Verbose output
pytest tests/ -v

# Show print statements
pytest tests/ -s

# Stop on first failure
pytest tests/ -x

# Run in parallel (requires pytest-xdist)
pytest tests/ -n auto

# Generate coverage report
pytest tests/ --cov=. --cov-report=html

# Generate JUnit XML report
pytest tests/ --junitxml=test-results.xml
```

## Test Requirements

### Python Dependencies

```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
```

### Optional Dependencies

```bash
# For parallel test execution
pip install pytest-xdist

# For test coverage
pip install pytest-cov coverage

# For HTML reports
pip install pytest-html
```

### Mock Services

Tests use mock services for external dependencies:
- Mock DynamoDB for memory storage
- Mock Kinesis for streaming
- Mock external APIs (identity verification, fraud database, geolocation)

Set `use_mock=True` in test fixtures to enable mocking.

## Test Configuration

### Environment Variables

```bash
# Set test environment
export TEST_ENV=test

# Enable debug logging
export LOG_LEVEL=DEBUG

# Use mock services
export USE_MOCK_SERVICES=true

# AWS region for tests
export AWS_REGION=us-east-1
```

### pytest.ini Configuration

Create `pytest.ini` in project root:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: integration tests
    performance: performance tests
    ai: AI validation tests
addopts = 
    -v
    --tb=short
    --strict-markers
```

## Performance Benchmarks

### Target Metrics

| Metric | Target | Acceptable |
|--------|--------|------------|
| Average Response Time | < 500ms | < 1s |
| P95 Response Time | < 1s | < 2s |
| P99 Response Time | < 2s | < 5s |
| Throughput | 1000+ TPS | 500+ TPS |
| Success Rate | 99%+ | 95%+ |
| Decision Accuracy | 80%+ | 70%+ |
| False Positive Rate | < 20% | < 30% |
| False Negative Rate | < 10% | < 20% |

### Load Test Scenarios

1. **Sustained Load**: 10,000 transactions over 10 seconds (1000 TPS)
2. **Burst Load**: 5,000 transactions in 1 second
3. **Concurrent Users**: 100 users, 10 transactions each
4. **Stress Test**: 30 seconds with varying load (1-2x base)

## Test Coverage

### Current Coverage

- **Integration Tests**: 45 test cases
- **Performance Tests**: 15 test cases
- **AI Validation Tests**: 25 test cases
- **Total**: 85+ test cases

### Coverage Goals

- Line Coverage: 80%+
- Branch Coverage: 70%+
- Function Coverage: 90%+

Generate coverage report:
```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      run: |
        python tests/run_all_tests.py --skip-slow
    
    - name: Generate coverage report
      run: |
        pytest tests/ --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Troubleshooting

### Common Issues

#### Issue: Tests fail with "Event loop is closed"

**Solution**: Ensure pytest-asyncio is installed and `asyncio_mode = auto` is set in pytest.ini

```bash
pip install pytest-asyncio
```

#### Issue: Mock services not working

**Solution**: Verify `use_mock=True` is set in fixtures

```python
@pytest.fixture
def memory_manager():
    return MemoryManager(use_mock=True)
```

#### Issue: Performance tests timeout

**Solution**: Increase timeout or skip slow tests

```bash
pytest tests/test_load_performance.py -m "not slow"
```

#### Issue: Import errors

**Solution**: Ensure project root is in PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

### Debug Mode

Run tests with debug output:

```bash
# Show all print statements
pytest tests/ -s

# Show full traceback
pytest tests/ --tb=long

# Drop into debugger on failure
pytest tests/ --pdb

# Enable debug logging
LOG_LEVEL=DEBUG pytest tests/ -s
```

## Best Practices

### Writing Tests

1. **Use descriptive test names**: `test_velocity_fraud_reasoning` not `test_1`
2. **One assertion per test**: Focus on single behavior
3. **Use fixtures**: Reuse setup code with pytest fixtures
4. **Mock external dependencies**: Don't rely on external services
5. **Test edge cases**: Include boundary conditions and error cases
6. **Keep tests fast**: Use mocks, avoid sleep(), optimize setup
7. **Make tests independent**: Each test should run in isolation
8. **Document test intent**: Add docstrings explaining what's being tested

### Test Organization

1. **Group related tests**: Use test classes for related functionality
2. **Use markers**: Tag tests with `@pytest.mark.slow`, `@pytest.mark.integration`
3. **Separate unit and integration**: Keep fast unit tests separate
4. **Create test utilities**: Share common test helpers
5. **Maintain test data**: Use fixtures for test data generation

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass before committing
3. Add tests for bug fixes
4. Update test documentation
5. Maintain test coverage above 80%

## Support

For test-related issues:
1. Check test output and error messages
2. Review test documentation
3. Check troubleshooting section
4. Enable debug logging
5. Run tests individually to isolate issues

## References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [AWS Bedrock Testing Best Practices](https://docs.aws.amazon.com/bedrock/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
