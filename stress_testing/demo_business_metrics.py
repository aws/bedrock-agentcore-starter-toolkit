"""
Demo script for BusinessMetricsCalculator.

This script demonstrates the comprehensive business metrics calculation
capabilities including fraud detection, cost analysis, ROI, and competitive
benchmarking.
"""

import asyncio
from datetime import datetime

from src.metrics.business_metrics_calculator import (
    BusinessMetricsCalculator,
    CostBreakdown
)
from src.models import SystemMetrics


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_metrics(metrics: dict, indent: int = 0):
    """Print metrics in a formatted way."""
    prefix = "  " * indent
    for key, value in metrics.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_metrics(value, indent + 1)
        elif isinstance(value, float):
            if 'percentage' in key or 'rate' in key or 'score' in key:
                print(f"{prefix}{key}: {value:.2%}")
            elif 'cost' in key or 'amount' in key or 'saved' in key or 'money' in key:
                print(f"{prefix}{key}: ${value:,.2f}")
            else:
                print(f"{prefix}{key}: {value:,.2f}")
        elif isinstance(value, list):
            print(f"{prefix}{key}:")
            for item in value:
                print(f"{prefix}  - {item}")
        else:
            print(f"{prefix}{key}: {value:,}" if isinstance(value, int) else f"{prefix}{key}: {value}")


async def demo_fraud_detection_metrics():
    """Demo fraud detection metrics calculation."""
    print_section("Fraud Detection Metrics")
    
    calculator = BusinessMetricsCalculator()
    
    # Scenario: 100,000 transactions processed
    total_transactions = 100000
    fraud_detected = 1900  # 2% fraud rate, 95% detection accuracy
    
    print(f"Scenario: {total_transactions:,} transactions processed")
    print(f"Fraud detected: {fraud_detected:,}\n")
    
    # Calculate fraud detection metrics
    fraud_metrics = calculator.calculate_fraud_detection_metrics(
        total_transactions=total_transactions,
        fraud_detected=fraud_detected
    )
    
    print("Fraud Detection Performance:")
    print_metrics({
        'Detection Rate': fraud_metrics['fraud_detection_rate'],
        'Overall Accuracy': fraud_metrics['fraud_detection_accuracy'],
        'Precision': fraud_metrics['precision'],
        'Recall': fraud_metrics['recall'],
        'F1 Score': fraud_metrics['f1_score'],
        'False Positive Rate': fraud_metrics['false_positive_rate'],
        'False Negative Rate': fraud_metrics['false_negative_rate'],
    })
    
    print("\nConfusion Matrix:")
    print_metrics({
        'True Positives': fraud_metrics['true_positives'],
        'False Positives': fraud_metrics['false_positives'],
        'True Negatives': fraud_metrics['true_negatives'],
        'False Negatives': fraud_metrics['false_negatives'],
    })


async def demo_cost_metrics():
    """Demo cost metrics calculation."""
    print_section("Cost Analysis")
    
    calculator = BusinessMetricsCalculator()
    
    # Scenario: 100,000 transactions over 10 hours
    total_transactions = 100000
    duration_hours = 10.0
    
    print(f"Scenario: {total_transactions:,} transactions over {duration_hours} hours")
    print(f"Average TPS: {total_transactions / (duration_hours * 3600):.1f}\n")
    
    # Calculate with estimated AWS usage
    print("Cost Breakdown (Estimated AWS Usage):")
    cost_breakdown = calculator.calculate_cost_metrics(
        total_transactions=total_transactions,
        duration_hours=duration_hours
    )
    
    print_metrics({
        'Lambda': cost_breakdown.lambda_cost,
        'DynamoDB': cost_breakdown.dynamodb_cost,
        'Kinesis': cost_breakdown.kinesis_cost,
        'Bedrock (AI)': cost_breakdown.bedrock_cost,
        'S3': cost_breakdown.s3_cost,
        'CloudWatch': cost_breakdown.cloudwatch_cost,
        'Other': cost_breakdown.other_costs,
        'Total Cost': cost_breakdown.total_cost,
    })
    
    cost_per_txn = cost_breakdown.total_cost / total_transactions
    print(f"\nCost per Transaction: ${cost_per_txn:.4f}")
    
    # Calculate with explicit AWS usage
    print("\n" + "-" * 80)
    print("\nCost Breakdown (Explicit AWS Usage):")
    cost_breakdown_explicit = calculator.calculate_cost_metrics(
        total_transactions=total_transactions,
        duration_hours=duration_hours,
        lambda_invocations=500000,  # 5 per transaction
        lambda_gb_seconds=100000.0,
        dynamodb_writes=300000,  # 3 per transaction
        dynamodb_reads=500000,  # 5 per transaction
        kinesis_shards=3,
        kinesis_puts=100000,
        bedrock_input_tokens=50000000,  # 500 per transaction
        bedrock_output_tokens=20000000,  # 200 per transaction
        s3_puts=100000,
        custom_metrics=50
    )
    
    print_metrics({
        'Lambda': cost_breakdown_explicit.lambda_cost,
        'DynamoDB': cost_breakdown_explicit.dynamodb_cost,
        'Kinesis': cost_breakdown_explicit.kinesis_cost,
        'Bedrock (AI)': cost_breakdown_explicit.bedrock_cost,
        'S3': cost_breakdown_explicit.s3_cost,
        'CloudWatch': cost_breakdown_explicit.cloudwatch_cost,
        'Other': cost_breakdown_explicit.other_costs,
        'Total Cost': cost_breakdown_explicit.total_cost,
    })


async def demo_roi_metrics():
    """Demo ROI metrics calculation."""
    print_section("ROI Analysis")
    
    calculator = BusinessMetricsCalculator()
    
    # Scenario: Monthly operation
    total_transactions = 500000  # 500K transactions per month
    fraud_detected = 9500  # 2% fraud rate, 95% detection
    total_cost = 12500.0  # $12,500 monthly operational cost
    
    print(f"Scenario: Monthly Operation")
    print(f"Transactions: {total_transactions:,}")
    print(f"Fraud Detected: {fraud_detected:,}")
    print(f"Operational Cost: ${total_cost:,.2f}\n")
    
    roi_metrics = calculator.calculate_roi_metrics(
        total_transactions=total_transactions,
        fraud_detected=fraud_detected,
        total_cost=total_cost,
        implementation_cost=50000.0,  # $50K implementation
        monthly_maintenance_cost=5000.0  # $5K monthly maintenance
    )
    
    print("ROI Metrics:")
    print_metrics({
        'Fraud Prevented Amount': roi_metrics['fraud_prevented_amount'],
        'Money Saved (Net)': roi_metrics['money_saved'],
        'ROI Percentage': roi_metrics['roi_percentage'] / 100,
        'Annual ROI': roi_metrics['annual_roi_percentage'] / 100,
        'Payback Period': f"{roi_metrics['payback_period_months']:.1f} months",
        'Cost per Transaction': roi_metrics['cost_per_transaction'],
        'Value per Transaction': roi_metrics['value_per_transaction'],
    })
    
    print("\nInvestment Details:")
    print_metrics({
        'Implementation Cost': roi_metrics['implementation_cost'],
        'Monthly Operational Cost': total_cost,
        'Monthly Maintenance Cost': roi_metrics['monthly_maintenance_cost'],
    })


async def demo_competitive_benchmarks():
    """Demo competitive benchmark generation."""
    print_section("Competitive Benchmarking")
    
    calculator = BusinessMetricsCalculator()
    
    print("Our Performance vs Industry Average:\n")
    
    benchmarks = calculator.generate_competitive_benchmarks(
        fraud_detection_accuracy=0.95,
        false_positive_rate=0.02,
        cost_per_transaction=0.025,
        avg_response_time_ms=250,
        uptime_percentage=99.97
    )
    
    print("Performance Comparison:")
    print("\nOur Performance:")
    print_metrics(benchmarks.our_performance)
    
    print("\nIndustry Average:")
    print_metrics(benchmarks.competitor_avg)
    
    print("\nImprovement Over Competition:")
    for metric, improvement in benchmarks.improvement_percentage.items():
        print(f"  {metric}: {improvement:+.1f}%")
    
    print(f"\nMarket Position: {benchmarks.market_position.upper()}")
    
    print("\nUnique Advantages:")
    for advantage in benchmarks.unique_advantages:
        print(f"  ✓ {advantage}")


async def demo_comprehensive_business_metrics():
    """Demo comprehensive business metrics calculation."""
    print_section("Comprehensive Business Metrics")
    
    calculator = BusinessMetricsCalculator()
    
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
    
    # Create system metrics
    system_metrics = SystemMetrics(
        timestamp=datetime.utcnow(),
        throughput_tps=278.0,  # 100K transactions over 1 hour
        requests_total=100000,
        requests_successful=99500,
        requests_failed=500,
        avg_response_time_ms=250.0,
        p50_response_time_ms=200.0,
        p95_response_time_ms=400.0,
        p99_response_time_ms=600.0,
        max_response_time_ms=1200.0,
        error_rate=0.005,
        timeout_rate=0.001,
        cpu_utilization=0.65,
        memory_utilization=0.70,
        network_throughput_mbps=50.0
    )
    
    # Calculate comprehensive business metrics
    business_metrics = calculator.calculate_business_metrics(
        total_transactions=100000,
        fraud_detected=1900,
        cost_breakdown=cost_breakdown,
        duration_hours=1.0,
        system_metrics=system_metrics
    )
    
    print("Business Metrics Summary:\n")
    
    print("Transaction Metrics:")
    print_metrics({
        'Transactions Processed': business_metrics.transactions_processed,
        'Transactions per Second': business_metrics.transactions_per_second,
        'Fraud Detected': business_metrics.fraud_detected,
    })
    
    print("\nFraud Detection Performance:")
    print_metrics({
        'Detection Rate': business_metrics.fraud_detection_rate,
        'Detection Accuracy': business_metrics.fraud_detection_accuracy,
        'Fraud Prevented Amount': business_metrics.fraud_prevented_amount,
    })
    
    print("\nCost & ROI:")
    print_metrics({
        'Total Cost': business_metrics.total_cost,
        'Cost per Transaction': business_metrics.cost_per_transaction,
        'Money Saved': business_metrics.money_saved,
        'ROI Percentage': business_metrics.roi_percentage / 100,
        'Payback Period': f"{business_metrics.payback_period_months:.1f} months",
    })
    
    print("\nCustomer Impact:")
    print_metrics({
        'Customer Impact Score': business_metrics.customer_impact_score,
        'False Positive Impact': business_metrics.false_positive_impact,
    })
    
    print("\nCompetitive Position:")
    print_metrics({
        'Performance vs Baseline': f"{business_metrics.performance_vs_baseline:.2f}x",
        'Cost vs Baseline': f"{business_metrics.cost_vs_baseline:.2f}x",
    })
    
    print("\nAWS Cost Breakdown:")
    print_metrics(business_metrics.aws_cost_breakdown)


async def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("  BUSINESS METRICS CALCULATOR DEMONSTRATION")
    print("="*80)
    
    await demo_fraud_detection_metrics()
    await demo_cost_metrics()
    await demo_roi_metrics()
    await demo_competitive_benchmarks()
    await demo_comprehensive_business_metrics()
    
    print("\n" + "="*80)
    print("  Demo Complete!")
    print("="*80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
