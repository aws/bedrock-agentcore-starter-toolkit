# Business Metrics Calculator

## Overview

The `BusinessMetricsCalculator` is a comprehensive module for calculating business value metrics for the fraud detection system. It provides accurate calculations for fraud detection effectiveness, cost analysis, ROI, and competitive benchmarking.

## Features

### 1. Fraud Detection Metrics
- **Detection Rate**: Percentage of transactions flagged as fraudulent
- **Accuracy**: Overall classification accuracy
- **Precision**: Accuracy of fraud predictions (true positives / all positives)
- **Recall**: Coverage of actual fraud (true positives / all actual fraud)
- **F1 Score**: Harmonic mean of precision and recall
- **False Positive/Negative Rates**: Error analysis

### 2. Cost Metrics
Calculates detailed AWS service costs including:
- **Lambda**: Function invocations and compute time
- **DynamoDB**: Read/write capacity units
- **Kinesis**: Shard hours and PUT operations
- **Bedrock**: AI model token usage
- **S3**: Storage and operations
- **CloudWatch**: Custom metrics and monitoring

### 3. ROI Metrics
- **Fraud Prevented Amount**: Total value of fraud blocked
- **Money Saved**: Net savings after operational costs
- **ROI Percentage**: Return on investment
- **Payback Period**: Time to recover implementation costs
- **Cost per Transaction**: Operational efficiency metric

### 4. Competitive Benchmarks
- **Performance Comparison**: Against industry averages
- **Improvement Percentages**: Quantified advantages
- **Unique Advantages**: Differentiating features
- **Market Position**: Leader/Challenger/Follower classification

## Usage

### Basic Usage

```python
from stress_testing.metrics.business_metrics_calculator import BusinessMetricsCalculator

calculator = BusinessMetricsCalculator()

# Calculate fraud detection metrics
fraud_metrics = calculator.calculate_fraud_detection_metrics(
    total_transactions=100000,
    fraud_detected=1900
)

print(f"Accuracy: {fraud_metrics['fraud_detection_accuracy']:.2%}")
print(f"Precision: {fraud_metrics['precision']:.2%}")
print(f"Recall: {fraud_metrics['recall']:.2%}")
```

### Cost Analysis

```python
# Calculate costs with estimated AWS usage
cost_breakdown = calculator.calculate_cost_metrics(
    total_transactions=100000,
    duration_hours=10.0
)

print(f"Total Cost: ${cost_breakdown.total_cost:.2f}")
print(f"Lambda: ${cost_breakdown.lambda_cost:.2f}")
print(f"Bedrock: ${cost_breakdown.bedrock_cost:.2f}")

# Or with explicit AWS usage data
cost_breakdown = calculator.calculate_cost_metrics(
    total_transactions=100000,
    duration_hours=10.0,
    lambda_invocations=500000,
    dynamodb_writes=300000,
    bedrock_input_tokens=50000000
)
```

### ROI Calculation

```python
roi_metrics = calculator.calculate_roi_metrics(
    total_transactions=500000,
    fraud_detected=9500,
    total_cost=12500.0,
    implementation_cost=50000.0
)

print(f"ROI: {roi_metrics['roi_percentage']:.1f}%")
print(f"Money Saved: ${roi_metrics['money_saved']:,.2f}")
print(f"Payback Period: {roi_metrics['payback_period_months']:.1f} months")
```

### Competitive Benchmarking

```python
benchmarks = calculator.generate_competitive_benchmarks(
    fraud_detection_accuracy=0.95,
    false_positive_rate=0.02,
    cost_per_transaction=0.025,
    avg_response_time_ms=250,
    uptime_percentage=99.97
)

print(f"Market Position: {benchmarks.market_position}")
print(f"Accuracy Improvement: {benchmarks.improvement_percentage['fraud_detection_accuracy']:.1f}%")
print(f"Cost Improvement: {benchmarks.improvement_percentage['cost_per_transaction']:.1f}%")
```

### Comprehensive Business Metrics

```python
from stress_testing.metrics.business_metrics_calculator import CostBreakdown

# Create cost breakdown
cost_breakdown = CostBreakdown(
    lambda_cost=150.0,
    dynamodb_cost=80.0,
    kinesis_cost=60.0,
    bedrock_cost=300.0,
    s3_cost=15.0,
    cloudwatch_cost=25.0,
    other_costs=70.0
)

# Calculate comprehensive metrics
business_metrics = calculator.calculate_business_metrics(
    total_transactions=100000,
    fraud_detected=1900,
    cost_breakdown=cost_breakdown,
    duration_hours=1.0,
    system_metrics=system_metrics  # Optional SystemMetrics object
)

print(f"Transactions: {business_metrics.transactions_processed:,}")
print(f"Fraud Detected: {business_metrics.fraud_detected:,}")
print(f"Accuracy: {business_metrics.fraud_detection_accuracy:.2%}")
print(f"Cost per Transaction: ${business_metrics.cost_per_transaction:.4f}")
print(f"ROI: {business_metrics.roi_percentage:.1f}%")
```

## Integration with MetricsCollector

The `BusinessMetricsCalculator` is integrated into the `MetricsCollector` for seamless use during stress testing:

```python
from stress_testing.metrics import MetricsCollector

collector = MetricsCollector()

# Collect business metrics (uses BusinessMetricsCalculator internally)
business_metrics = await collector.collect_business_metrics()

# Get competitive benchmarks
benchmarks = await collector.get_competitive_benchmarks()
```

## Configuration

### Custom Pricing

You can override default AWS pricing:

```python
custom_pricing = {
    'lambda_per_request': 0.0000003,
    'dynamodb_write_per_million': 2.0,
    'bedrock_claude_per_1k_input': 0.004
}

calculator = BusinessMetricsCalculator(pricing=custom_pricing)
```

### Custom Baseline

You can provide custom competitive baselines:

```python
custom_baseline = {
    'fraud_detection_accuracy': 0.90,
    'false_positive_rate': 0.08,
    'cost_per_transaction': 0.04,
    'avg_response_time_ms': 400,
    'uptime_percentage': 99.0
}

benchmarks = calculator.generate_competitive_benchmarks(
    fraud_detection_accuracy=0.95,
    false_positive_rate=0.02,
    cost_per_transaction=0.025,
    avg_response_time_ms=250,
    uptime_percentage=99.97,
    custom_baseline=custom_baseline
)
```

## Demo

Run the comprehensive demo to see all features:

```bash
python -m stress_testing.demo_business_metrics
```

## Testing

Run the test suite:

```bash
python -m pytest stress_testing/metrics/test_business_metrics_calculator.py -v
```

## Requirements Satisfied

This implementation satisfies the following requirements from the stress testing framework:

- **Requirement 13.2**: Calculate fraud detection rate and accuracy
- **Requirement 13.6**: Compute cost per transaction from AWS billing data
- **Requirement 13.7**: Calculate ROI metrics and money saved
- **Requirement 15.2**: Business value storytelling through data
- **Requirement 15.3**: Translate technical metrics to business language
- **Requirement 15.6**: TCO analysis vs traditional fraud detection systems

## Key Metrics

### Fraud Detection
- Detection Rate
- Accuracy, Precision, Recall, F1 Score
- False Positive/Negative Rates
- Confusion Matrix (TP, FP, TN, FN)

### Cost Analysis
- Per-service AWS costs
- Total operational cost
- Cost per transaction
- Cost breakdown by component

### ROI
- Fraud prevented amount
- Net money saved
- ROI percentage
- Annual ROI
- Payback period

### Competitive Position
- Performance vs baseline
- Cost vs baseline
- Improvement percentages
- Unique advantages
- Market position

## Architecture

```
BusinessMetricsCalculator
├── calculate_fraud_detection_metrics()
│   ├── Confusion matrix calculation
│   ├── Accuracy, precision, recall
│   └── F1 score and error rates
│
├── calculate_cost_metrics()
│   ├── Lambda cost calculation
│   ├── DynamoDB cost calculation
│   ├── Kinesis cost calculation
│   ├── Bedrock AI cost calculation
│   └── Other AWS services
│
├── calculate_roi_metrics()
│   ├── Fraud prevented calculation
│   ├── Net savings calculation
│   ├── ROI percentage
│   └── Payback period
│
├── generate_competitive_benchmarks()
│   ├── Performance comparison
│   ├── Improvement calculation
│   ├── Unique advantages
│   └── Market positioning
│
└── calculate_business_metrics()
    └── Comprehensive metrics combining all above
```

## Best Practices

1. **Use Explicit AWS Usage Data**: When available, provide explicit AWS usage metrics for more accurate cost calculations
2. **Include System Metrics**: Pass SystemMetrics for better customer impact scoring
3. **Provide Confusion Matrix**: When available, provide true positives, false positives, and false negatives for accurate fraud metrics
4. **Custom Baselines**: Use custom competitive baselines when comparing against specific competitors
5. **Regular Updates**: Update pricing and baseline data periodically to maintain accuracy

## Future Enhancements

- Real-time AWS billing API integration
- Historical trend analysis
- Predictive cost modeling
- Multi-region cost optimization
- Custom metric definitions
- Export to business intelligence tools
